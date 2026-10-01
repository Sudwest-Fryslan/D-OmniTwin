from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from collections import defaultdict
import difflib
import re

from omnitwin.fouten import GebruikersFout
from omnitwin.services.llm_service import LLMService
from omnitwin.services.logging_service import AppLogger

class DeduplicatieService:
    def __init__(self, db: Session):
        self.db = db

    def get_kandidaten(self) -> List[Dict[str, Any]]:
        """
        Vindt potentiele duplicaten op basis van naam-gelijkenis (substring, pg_trgm)
        en semantische gelijkenis (pgvector).
        """
        # We halen eerst alle actieve indicatoren op voor hun metadata, inclusief broodkruimels
        query_all = text("""
            SELECT i.uuid, i.naam, i.bron, i.categorie, i.omschrijving,
                   array_agg(DISTINCT COALESCE(k.titel_naam, '?') || ' > ' || COALESCE(k.thema_naam, '?') || ' > ' || COALESCE(k.onderdeel_naam, '?')) FILTER (WHERE k.indicator_uuid IS NOT NULL) as broodkruimels
            FROM indicatoren i
            LEFT JOIN v_kompas_hierarchie k ON i.uuid = k.indicator_uuid
            WHERE i.is_actief = true
            GROUP BY i.uuid, i.naam, i.bron, i.categorie, i.omschrijving
        """)
        indicatoren_rows = self.db.execute(query_all).fetchall()
        ind_dict = {str(row.uuid): dict(row._mapping) for row in indicatoren_rows}
        
        # Converteer eventuele None arrays naar lege lijsten voor JSON serialisatie
        for key in ind_dict:
            if ind_dict[key].get('broodkruimels') is None:
                ind_dict[key]['broodkruimels'] = []
        
        # SQL query die alle matches vindt via trgm en embeddings
        # Drempelfilter in SQL voorkomt dat we tienduizenden irrelevante paren ophalen
        # NOT EXISTS filtert paren die als uitzondering zijn gemarkeerd
        query_pairs = text("""
            SELECT 
                i1.uuid as u1, 
                i2.uuid as u2,
                similarity(i1.naam::text, i2.naam::text) as trgm_sim,
                (e1.embedding <=> e2.embedding) as vec_dist
            FROM indicatoren i1
            JOIN indicatoren i2 ON i1.id < i2.id
            LEFT JOIN indicator_embeddings e1 ON i1.uuid = e1.indicator_uuid
            LEFT JOIN indicator_embeddings e2 ON i2.uuid = e2.indicator_uuid
            WHERE i1.is_actief = true AND i2.is_actief = true
              AND (
                similarity(i1.naam::text, i2.naam::text) > 0.4
                OR (e1.embedding <=> e2.embedding) < 0.3
              )
              AND NOT EXISTS (
                SELECT 1 FROM deduplicatie_uitzonderingen du
                WHERE (du.indicator_uuid_1 = i1.uuid AND du.indicator_uuid_2 = i2.uuid)
                   OR (du.indicator_uuid_1 = i2.uuid AND du.indicator_uuid_2 = i1.uuid)
              )
        """)
        
        pairs = self.db.execute(query_pairs).fetchall()
        
        
        def clean_name(name):
            # Verwijder veelvoorkomende ruis
            n = name.lower()
            n = re.sub(r'\b(aantal|percentage|perc\.|totaal|definitief|voorlopig)\b', '', n)
            n = re.sub(r'[()\-\.,]', ' ', n)
            return ' '.join(n.split())
            
        edges = []
        for row in pairs:
            u1, u2, trgm_sim, vec_dist = str(row.u1), str(row.u2), row.trgm_sim, row.vec_dist
            
            is_match = False
            # 1. Trigram check (via database)
            if trgm_sim is not None and trgm_sim > 0.6:
                is_match = True
                
            # 2. Vector check (via database)
            if vec_dist is not None and vec_dist < 0.15:
                is_match = True
                
            # 3. Substring & Difflib check (via Python)
            if not is_match and u1 in ind_dict and u2 in ind_dict:
                name1 = clean_name(ind_dict[u1]['naam'])
                name2 = clean_name(ind_dict[u2]['naam'])
                
                if len(name1) > 4 and len(name2) > 4:
                    if name1 in name2 or name2 in name1:
                        is_match = True
                    else:
                        sim = difflib.SequenceMatcher(None, name1, name2).ratio()
                        if sim > 0.70:
                            is_match = True
                            
            if is_match:
                edges.append((u1, u2))
                
        # Groepeer connected components
        adj = defaultdict(list)
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)
            
        visited = set()
        candidates = []
        
        # LLMService eenmalig instantiëren (voorkomt N+1 DB queries voor config)
        llm = LLMService(self.db)
        
        for node in adj.keys():
            if node not in visited:
                # BFS
                queue = [node]
                visited.add(node)
                comp = []
                while queue:
                    curr = queue.pop(0)
                    if curr in ind_dict:
                        comp.append(ind_dict[curr])
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                if len(comp) > 1:
                    eval_result = llm.validate_duplicates(comp)
                    
                    if eval_result.get("is_duplicaat"):
                        candidates.append({
                            "groep_id": str(comp[0]['uuid']),
                            "ai_advies": eval_result.get("ai_advies", "Bevestigd door AI."),
                            "indicatoren": comp
                        })
                    
        return candidates

    def merge_indicatoren(self, primary_uuid: str, duplicate_uuids: List[str], actie: str) -> Dict[str, Any]:
        """
        Merged of groepeert indicatoren.
        Actie: 'exact_duplicaat' (is_actief=false) of 'groepeer_bronnen' (hoofd_indicator_id)
        """
        # Controleer of primary bestaat
        check_query = text("SELECT id, naam FROM indicatoren WHERE uuid = CAST(:uuid AS UUID)")
        primary_row = self.db.execute(check_query, {"uuid": primary_uuid}).fetchone()
        
        if not primary_row:
            raise GebruikersFout("Primary indicator niet gevonden")
        
        primary_id = primary_row[0]
        primary_naam = primary_row[1]
            
        success_count = 0
        for dup_uuid in duplicate_uuids:
            if actie == "exact_duplicaat":
                update_query = text("""
                    UPDATE indicatoren 
                    SET is_actief = false, vervangen_door_id = :primary_id
                    WHERE uuid = CAST(:dup_uuid AS UUID)
                """)
                self.db.execute(update_query, {"primary_id": primary_id, "dup_uuid": dup_uuid})
                success_count += 1
            elif actie == "groepeer_bronnen":
                update_query = text("""
                    UPDATE indicatoren 
                    SET hoofd_indicator_id = :primary_id
                    WHERE uuid = CAST(:dup_uuid AS UUID)
                """)
                self.db.execute(update_query, {"primary_id": primary_id, "dup_uuid": dup_uuid})
                success_count += 1
                
        self.db.commit()
        
        # Audit trail: log de merge actie
        AppLogger.info(
            f"Deduplicatie merge: actie='{actie}', primary='{primary_naam}' ({primary_uuid}), "
            f"verwerkt={success_count} duplicaten ({', '.join(duplicate_uuids)})",
            category="DATA_KWALITEIT"
        )
        
        return {
            "status": "success",
            "actie": actie,
            "primary_uuid": primary_uuid,
            "verwerkt_aantal": success_count
        }

    def markeer_uitzondering(self, indicator_uuids: List[str]) -> Dict[str, Any]:
        """
        Markeert alle paar-combinaties van de gegeven UUIDs als 'geen duplicaat'.
        Deze paren worden bij toekomstige scans uitgefilterd.
        """
        from itertools import combinations
        
        paren = list(combinations(sorted(indicator_uuids), 2))
        ingevoegd = 0
        
        for uuid_1, uuid_2 in paren:
            insert_query = text("""
                INSERT INTO deduplicatie_uitzonderingen (indicator_uuid_1, indicator_uuid_2)
                VALUES (CAST(:u1 AS UUID), CAST(:u2 AS UUID))
                ON CONFLICT (indicator_uuid_1, indicator_uuid_2) DO NOTHING
            """)
            self.db.execute(insert_query, {"u1": uuid_1, "u2": uuid_2})
            ingevoegd += 1
        
        self.db.commit()
        
        AppLogger.info(
            f"Deduplicatie uitzondering: {len(indicator_uuids)} indicatoren gemarkeerd als 'geen duplicaat' ({ingevoegd} paren)",
            category="DATA_KWALITEIT"
        )
        
        return {
            "status": "success",
            "paren_gemarkeerd": ingevoegd
        }
