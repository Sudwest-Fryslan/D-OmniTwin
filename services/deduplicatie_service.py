from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import difflib

class DeduplicatieService:
    def __init__(self, db: Session):
        self.db = db

    def get_kandidaten(self) -> List[Dict[str, Any]]:
        """
        Vindt potentiele duplicaten op basis van naam-gelijkenis in Python.
        """
        # Haal alle actieve indicatoren op
        query = text("""
            SELECT uuid, naam, bron, categorie, omschrijving
            FROM indicatoren
            WHERE is_actief = true
            ORDER BY naam
        """)
        indicatoren = self.db.execute(query).fetchall()
        
        candidates = []
        visited = set()
        
        for i in range(len(indicatoren)):
            if i in visited:
                continue
                
            ind1 = indicatoren[i]
            group = [dict(ind1._mapping)]
            
            for j in range(i + 1, len(indicatoren)):
                if j in visited:
                    continue
                    
                ind2 = indicatoren[j]
                
                # Check similarity using difflib
                similarity = difflib.SequenceMatcher(None, ind1.naam.lower(), ind2.naam.lower()).ratio()
                
                if similarity > 0.85:
                    group.append(dict(ind2._mapping))
                    visited.add(j)
                    
            if len(group) > 1:
                # Calculate AI Reason stub (in real scenario call Ollama)
                ai_reason = "Deze indicatoren hebben een zeer vergelijkbare naam."
                if any(g['bron'] != group[0]['bron'] for g in group):
                    ai_reason += " Let op: Ze komen uit verschillende bronnen."
                
                candidates.append({
                    "groep_id": str(ind1.uuid),
                    "ai_advies": ai_reason,
                    "indicatoren": group
                })
                
        return candidates

    def merge_indicatoren(self, primary_uuid: str, duplicate_uuids: List[str], actie: str) -> Dict[str, Any]:
        """
        Merged of groepeert indicatoren.
        Actie: 'exact_duplicaat' (is_actief=false) of 'groepeer_bronnen' (hoofd_indicator_id)
        """
        # Controleer of primary bestaat
        check_query = text("SELECT id FROM indicatoren WHERE uuid = CAST(:uuid AS UUID)")
        primary_id = self.db.execute(check_query, {"uuid": primary_uuid}).scalar()
        
        if not primary_id:
            raise ValueError("Primary indicator niet gevonden")
            
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
        
        return {
            "status": "success",
            "actie": actie,
            "primary_uuid": primary_uuid,
            "verwerkt_aantal": success_count
        }
