"""
Kompas Service Layer
Business logic voor multi-kompas configuratie systeem
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json


class KompasService:
    """Service voor Kompas hiërarchie en data queries"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scoring = KompasScoringService()
    
    def get_configuraties(self) -> List[Dict[str, Any]]:
        """
        Haal alle actieve configuraties op met statistieken
        
        Returns: List van configuratie dicts met counts
        """
        query = text("""
            SELECT 
                id, naam, beschrijving, is_standaard, is_actief, icoon,
                aantal_themas, aantal_onderdelen, aantal_indicatoren, aantal_scoring_regels
            FROM v_kompas_config_stats
        """)
        
        result = self.db.execute(query)
        return [dict(row._mapping) for row in result]
    
    def get_standaard_config_id(self) -> int:
        """Haal ID op van standaard configuratie"""
        query = text("""
            SELECT id FROM kompas_configuraties 
            WHERE is_standaard = TRUE AND is_actief = TRUE
            LIMIT 1
        """)
        
        result = self.db.execute(query).fetchone()
        return result[0] if result else 1
    
    def get_hierarchie(self, config_id: int) -> Dict[str, Any]:
        """
        Build complete hiërarchie tree voor D3.js sunburst
        
        Args:
            config_id: ID van kompas configuratie
        
        Returns: Dict met config info + hierarchie tree
        """
        # Haal config info op
        config_query = text("""
            SELECT id, naam, icoon 
            FROM kompas_configuraties 
            WHERE id = :config_id AND is_actief = TRUE
        """)
        config_row = self.db.execute(config_query, {"config_id": config_id}).fetchone()
        
        if not config_row:
            return None
        
        # Haal hiërarchie data op
        hierarchy_query = text("""
            SELECT 
                titel_id, titel_naam, titel_kleur,
                thema_id, thema_naam,
                onderdeel_id, onderdeel_naam,
                indicator_uuid, indicator_naam,
                is_actueel, weging
            FROM v_kompas_hierarchie
            WHERE config_id = :config_id
            ORDER BY titel_id, thema_id, onderdeel_id, indicator_naam
        """)
        
        rows = self.db.execute(hierarchy_query, {"config_id": config_id}).fetchall()
        
        # Build tree
        tree = self._build_tree_from_rows(rows)
        
        # Count total indicators
        indicator_count = len([r for r in rows if r.indicator_uuid])
        
        return {
            "config_id": config_row.id,
            "config_naam": config_row.naam,
            "config_icoon": config_row.icoon,
            "hierarchie": tree,
            "total_indicators": indicator_count,
            "last_updated": datetime.now()
        }
    
    def get_gebied_kompas(self, config_id: int, gebied_id: str) -> Optional[Dict[str, Any]]:
        """
        Haal kompas data voor één gebied op (met waarden + kleuren)
        
        Args:
            config_id: ID van kompas configuratie
            gebied_id: UUID van gebied
        
        Returns: Dict met hierarchie + waarden ingevuld
        """
        # Check of gebied bestaat
        gebied_query = text("""
            SELECT id, naam FROM gebieden WHERE id = :gebied_id LIMIT 1
        """)
        gebied_row = self.db.execute(gebied_query, {"gebied_id": gebied_id}).fetchone()
        
        if not gebied_row:
            return None
        
        # Haal basis hiërarchie op
        hierarchie_data = self.get_hierarchie(config_id)
        if not hierarchie_data:
            return None
        
        # Haal ALLE indicatoren op die in dit kompas zitten
        # LEFT JOIN LATERAL voor meest recente jaar (MAX) per indicator
        data_query = text("""
            SELECT 
                i.uuid as indicator_uuid,
                i.naam as indicator_naam,
                gd.waarde,
                gd.jaar,
                COALESCE(sr.score_type, i.score_type) as score_type,
                sr.inverse,
                sr.thresholds,
                COALESCE(sr.eenheid, i.eenheid) AS eenheid
            FROM kompas_indicator_mapping kim
            JOIN indicatoren i ON kim.indicator_uuid = i.uuid
            LEFT JOIN LATERAL (
                SELECT waarde, jaar 
                FROM gebied_data
                WHERE indicator_uuid = i.uuid 
                  AND gebied_id = :gebied_id
                ORDER BY jaar DESC
                LIMIT 1
            ) gd ON true
            LEFT JOIN kompas_indicator_scoring_regels sr 
                ON i.uuid = sr.indicator_uuid 
                AND sr.config_id = :config_id
            WHERE kim.config_id = :config_id
        """)
        
        data_rows = self.db.execute(data_query, {
            "config_id": config_id,
            "gebied_id": gebied_id
        }).fetchall()
        
        # Converteer naar dict voor makkelijke lookup
        # Indicatoren zonder data krijgen None als waarde
        data_map = {}
        for row in data_rows:
            # FIX: Check of thresholds al een list is of nog een string
            thresholds = None
            if row.thresholds:
                if isinstance(row.thresholds, str):
                    thresholds = json.loads(row.thresholds)
                else:
                    thresholds = row.thresholds
            
            data_map[str(row.indicator_uuid)] = {
                "waarde": float(row.waarde) if row.waarde is not None else None,
                "score_type": row.score_type,
                "inverse": row.inverse,
                "thresholds": thresholds,
                "eenheid": row.eenheid
            }
        
        # Haal percentiel thresholds op voor ALLE indicatoren (bulk query)
        bulk_thresholds = self._get_bulk_percentiles()
        
        # Enrich hierarchie met waarden en kleuren
        enriched_tree = self._enrich_tree_with_values(
            hierarchie_data["hierarchie"], 
            data_map,
            bulk_thresholds=bulk_thresholds 
        )
        
        # Bereken coverage
        total_indicators = hierarchie_data["total_indicators"]
        coverage_pct = (len(data_map) / total_indicators * 100) if total_indicators > 0 else 0
        
        return {
            "gebied_id": gebied_id,
            "gebied_naam": gebied_row.naam,
            "config_id": config_id,
            "config_naam": hierarchie_data["config_naam"],
            "hierarchie": enriched_tree,
            "coverage_percentage": round(coverage_pct, 1),
            "laatste_update": datetime.now()
        }
        
    def _get_bulk_percentiles(self) -> Dict[str, List[float]]:
        """
        Bereken 12.5% stap thresholds voor alle indicatoren
        Gebruikt PostgreSQL PERCENTILE_CONT voor performance
        """
        # We willen 7 split points voor 8 bins: 12.5, 25, 37.5, 50, 62.5, 75, 87.5
        query = text("""
            SELECT 
                indicator_uuid,
                PERCENTILE_CONT(ARRAY[0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]) 
                WITHIN GROUP (ORDER BY waarde) as thresholds
            FROM gebied_data
            WHERE waarde IS NOT NULL
            GROUP BY indicator_uuid
        """)
        
        results = self.db.execute(query).fetchall()
        
        # Convert to dict
        threshold_map = {}
        for row in results:
            if row.thresholds:
                threshold_map[str(row.indicator_uuid)] = list(row.thresholds)
        return threshold_map
    
    def get_indicator_path(self, config_id: int, indicator_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Haal hiërarchie pad op voor specifieke indicator (breadcrumb)
        
        Returns: {"path": ["Titel", "Thema", "Onderdeel", "Indicator"], ...}
        """
        query = text("""
            SELECT 
                titel_naam, thema_naam, onderdeel_naam, indicator_naam,
                titel_kleur, is_actueel, weging
            FROM v_kompas_hierarchie
            WHERE config_id = :config_id AND indicator_uuid = :uuid::uuid
            LIMIT 1
        """)
        
        row = self.db.execute(query, {
            "config_id": config_id,
            "uuid": indicator_uuid
        }).fetchone()
        
        if not row:
            return None
        
        path = [row.titel_naam, row.thema_naam, row.onderdeel_naam, row.indicator_naam]
        
        return {
            "config_id": config_id,
            "indicator_uuid": indicator_uuid,
            "path": path,
            "full_path_string": " > ".join(path),
            "indicator_details": dict(row._mapping)
        }
    
    def get_indicator_history(self, config_id: int, gebied_id: str, indicator_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Haal historische data op voor een indicator in een gebied (voor time-series chart)
        
        Args:
            config_id: ID van kompas configuratie (voor verificatie/context)
            gebied_id: UUID van gebied
            indicator_uuid: UUID van indicator
            
        Returns: Dict met indicator info en list van history points
        """
        # 1. Haal indicator metadata
        meta_query = text("""
            SELECT 
                i.naam, i.eenheid, i.bron, i.omschrijving
            FROM indicatoren i
            WHERE i.uuid = CAST(:uuid AS UUID)
        """)
        meta = self.db.execute(meta_query, {"uuid": indicator_uuid}).fetchone()
        
        if not meta:
            return None
            
        # 2. Haal data points (gebied_data) - gebruik jaar
        history_query = text("""
            SELECT 
                jaar, 
                waarde, 
                bron,
                updated_at
            FROM gebied_data
            WHERE indicator_uuid = CAST(:uuid AS UUID)
              AND gebied_id = :gebied_id
              AND jaar IS NOT NULL
            ORDER BY jaar ASC
        """)
        
        history_rows = self.db.execute(history_query, {
            "uuid": indicator_uuid,
            "gebied_id": gebied_id
        }).fetchall()
        
        # Format history
        history = []
        for row in history_rows:
            history.append({
                "jaar": row.jaar,
                "waarde": float(row.waarde),
                "bron": row.bron or meta.bron,
                "datum": row.updated_at.strftime("%Y-%m-%d") if row.updated_at else None
            })
            
        # 3. Haal gebied naam
        gebied_query = text("SELECT naam FROM gebieden WHERE id = :id")
        gebied = self.db.execute(gebied_query, {"id": gebied_id}).fetchone()
        
        return {
            "bron": meta.bron,
            "definitie": meta.omschrijving or "Geen beschrijving beschikbaar.",
            "eenheid": meta.eenheid,
            "indicator": {
                "uuid": indicator_uuid,
                "naam": meta.naam,
                "eenheid": meta.eenheid,
                "bron": meta.bron
            },
            "gebied": {
                "id": gebied_id,
                "naam": gebied.naam if gebied else "Onbekend"
            },
            "history": history
        }

    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _build_tree_from_rows(self, rows: List) -> Dict[str, Any]:
        """
        Build geneste hiërarchie tree van flat database rows
        
        Returns: KompasNode compatible dict
        """
        if not rows:
            return {"name": "Root", "children": []}
        
        # Group by titel
        titels = {}
        for row in rows:
            if not row.titel_id:
                continue
            
            titel_id = row.titel_id
            if titel_id not in titels:
                titels[titel_id] = {
                    "name": row.titel_naam,
                    "type": "titel",
                    "color": row.titel_kleur,
                    "children": {}
                }
            
            # Group by thema binnen titel
            if row.thema_id:
                thema_id = row.thema_id
                if thema_id not in titels[titel_id]["children"]:
                    titels[titel_id]["children"][thema_id] = {
                        "name": row.thema_naam,
                        "type": "thema",
                        "children": {}
                    }
                
                # Group by onderdeel binnen thema
                if row.onderdeel_id:
                    onderdeel_id = row.onderdeel_id
                    if onderdeel_id not in titels[titel_id]["children"][thema_id]["children"]:
                        titels[titel_id]["children"][thema_id]["children"][onderdeel_id] = {
                            "name": row.onderdeel_naam,
                            "type": "onderdeel",
                            "children": []
                        }
                    
                    # Add indicator
                    if row.indicator_uuid:
                        titels[titel_id]["children"][thema_id]["children"][onderdeel_id]["children"].append({
                            "name": row.indicator_naam,
                            "type": "indicator",
                            "uuid": str(row.indicator_uuid),
                            "value": None,  # Wordt later ingevuld
                            "color": None
                        })
        
        # Convert nested dicts to lists
        root_children = []
        for titel in titels.values():
            titel_node = {
                "name": titel["name"],
                "type": titel["type"],
                "color": titel["color"],
                "children": []
            }
            
            for thema in titel["children"].values():
                thema_node = {
                    "name": thema["name"],
                    "type": thema["type"],
                    "children": []
                }
                
                for onderdeel in thema["children"].values():
                    # Children zijn al een list van indicators
                    thema_node["children"].append(onderdeel)
                
                titel_node["children"].append(thema_node)
            
            root_children.append(titel_node)
        
        return {
            "name": "Root",
            "type": "root",
            "children": root_children
        }
    
    def _enrich_tree_with_values(self, tree: Dict, data_map: Dict[str, Dict], bulk_thresholds: Dict[str, List[float]] = None, current_titel: str = None) -> Dict:
        """
        Recursively voeg waarden en kleuren toe aan tree nodes
        
        Args:
            tree: Hiërarchie tree dict
            data_map: Dict[indicator_uuid] -> {waarde, score_type, ...}
            bulk_thresholds: Map van indicator uuid naar 7 percentile values
            current_titel: Naam van de huidige hoofdtitel (context)
        
        Returns: Enriched tree
        """
        enriched = tree.copy()
        
        # Track titel context
        if enriched.get("type") == "titel":
            current_titel = enriched.get("name")
        
        # Pass context down via temporary private prop
        enriched["_context_titel"] = current_titel
        
        # Als dit een indicator is, vul waarde + kleur in
        if enriched.get("type") == "indicator" and enriched.get("uuid"):
            uuid = enriched["uuid"]
            if uuid in data_map:
                data = data_map[uuid]
                waarde = data["waarde"]
                
                # Altijd eenheid tonen (ook bij NULL)
                enriched["eenheid"] = data.get("eenheid")
                
                if waarde is not None:
                    # Indicator heeft data
                    enriched["value"] = waarde
                    
                    # Haal percentiel thresholds uit bulk cache
                    thresholds = bulk_thresholds.get(uuid) if bulk_thresholds else None
                    
                    # Bereken kleur via scoring service
                    enriched["color"] = self.scoring.get_color_for_value(
                        value=waarde,
                        score_type=data.get("score_type") or "positive_ascending",
                        thresholds=thresholds, # Use percentiles!
                        inverse=data.get("inverse", False),
                        context=current_titel
                    )
                else:
                    enriched["value"] = None
                    enriched["color"] = "#94A3B8"  # Grijs voor geen data
            else:
                enriched["value"] = None
                enriched["color"] = "#94A3B8"
                enriched["eenheid"] = None
        
        # Recursief voor children
        if "children" in enriched and enriched["children"]:
            enriched["children"] = [
                self._enrich_tree_with_values(child, data_map, bulk_thresholds, current_titel) 
                for child in enriched["children"]
            ]
        
        return enriched


    def get_top_afwijkende_buurten(self, indicator_uuid: str, limit: int = 3, gebied_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Bereken Z-scores voor alle CBS-buurten en retourneer Top N positief + Top N negatief.
        
        Args:
            indicator_uuid: UUID van de indicator
            limit: Aantal buurten per richting (default 3)
            gebied_id: Optioneel, UUID van het gebied om de buurten te filteren op de gemeente van dit gebied
        
        Returns: Dict met top_positief en top_negatief lijsten, of None
        """
        
        # 1. Bepaal de gemeente_code filter indien gebied_id is meegegeven
        gemeente_filter = ""
        params = {"uuid": indicator_uuid}
        
        if gebied_id:
            gem_query = text("SELECT gemeente_code FROM gebieden WHERE id = :gebied_id")
            gem_res = self.db.execute(gem_query, {"gebied_id": gebied_id}).fetchone()
            if gem_res and gem_res.gemeente_code:
                gemeente_filter = "AND g.gemeente_code = :gemeente_code"
                params["gemeente_code"] = gem_res.gemeente_code
        
        query = text(f"""
            WITH buurt_type AS (
                SELECT id FROM gebiedstypes WHERE LOWER(naam) LIKE '%buurt%' LIMIT 1
            ),
            meest_recent AS (
                SELECT MAX(gd.jaar) as jaar
                FROM gebied_data gd
                JOIN gebieden g ON gd.gebied_id = g.id
                CROSS JOIN buurt_type bt
                WHERE gd.indicator_uuid = :uuid AND g.gebiedstype_id = bt.id AND LOWER(g.naam) NOT LIKE 'wijk %' {gemeente_filter}
            ),
            ref_stats AS (
                SELECT 
                    AVG(gd.waarde) as avg_val, 
                    STDDEV_SAMP(gd.waarde) as std_val
                FROM gebied_data gd
                JOIN gebieden g ON gd.gebied_id = g.id
                CROSS JOIN meest_recent mr
                CROSS JOIN buurt_type bt
                WHERE gd.indicator_uuid = :uuid 
                  AND g.gebiedstype_id = bt.id
                  AND LOWER(g.naam) NOT LIKE 'wijk %'
                  AND gd.jaar = mr.jaar
                  {gemeente_filter}
            )
            SELECT 
                g.id as buurt_id, 
                g.naam as buurt_naam,
                gd.waarde,
                gd.jaar,
                rs.avg_val as gemiddelde,
                (gd.waarde - rs.avg_val) / NULLIF(rs.std_val, 0) as z_score
            FROM gebied_data gd
            JOIN gebieden g ON gd.gebied_id = g.id
            CROSS JOIN ref_stats rs
            CROSS JOIN meest_recent mr
            CROSS JOIN buurt_type bt
            WHERE gd.indicator_uuid = :uuid 
              AND g.gebiedstype_id = bt.id
              AND gd.jaar = mr.jaar 
              AND rs.std_val > 0
              AND LOWER(g.naam) NOT LIKE 'wijk %'
              {gemeente_filter}
            ORDER BY ABS((gd.waarde - rs.avg_val) / NULLIF(rs.std_val, 0)) DESC
        """)
        
        rows = self.db.execute(query, params).fetchall()
        if not rows:
            return None
        
        # Haal indicator metadata op
        meta_query = text("""
            SELECT i.naam, COALESCE(sr.eenheid, i.eenheid) as eenheid
            FROM indicatoren i
            LEFT JOIN kompas_indicator_scoring_regels sr ON i.uuid = sr.indicator_uuid
            WHERE i.uuid = :uuid
            LIMIT 1
        """)
        meta = self.db.execute(meta_query, {"uuid": indicator_uuid}).fetchone()
        
        positief = []
        negatief = []
        
        for row in rows:
            entry = {
                "buurt_id": row.buurt_id,
                "buurt_naam": row.buurt_naam,
                "waarde": round(float(row.waarde), 2),
                "z_score": round(float(row.z_score), 2)
            }
            if row.z_score > 0 and len(positief) < limit:
                positief.append(entry)
            elif row.z_score < 0 and len(negatief) < limit:
                negatief.append(entry)
            
            if len(positief) >= limit and len(negatief) >= limit:
                break
        
        # 2. Return payload with context
        context_naam = "Alle gemeenten"
        if gebied_id and gem_res and gem_res.gemeente_code:
            # We already have gemeente_code, let's get the naam of that gemeente
            naam_query = text("SELECT naam FROM gemeenten WHERE code = :code")
            naam_res = self.db.execute(naam_query, {"code": gem_res.gemeente_code}).fetchone()
            if naam_res:
                context_naam = naam_res.naam
        
        return {
            "indicator_naam": meta.naam if meta else "",
            "eenheid": (meta.eenheid or "") if meta else "",
            "referentie_gemiddelde": round(float(rows[0].gemiddelde), 2) if rows else 0,
            "context_naam": context_naam,
            "top_positief": positief,
            "top_negatief": negatief
        }

class KompasScoringService:
    """Service voor kleurberekening op basis van scoring regels"""
    
    # 8-bin Scales
    PALETTE_NORMAL = [
        "#D73027", "#F46D43", "#FDAE61", "#FEE08B", 
        "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850"
    ]
    
    # Blue scale (Dark -> Light) for Samenstelling
    # Dark Blue (#08306B) -> Light Blue (#F7FBFF)
    PALETTE_BLUE = [
        "#08306B", "#08519C", "#2171B5", "#4292C6",
        "#6BAED6", "#9ECAE1", "#C6DBEF", "#DEEBF7"
    ]

    COLOR_MAP = {
        "green": "#22C55E",
        "yellow": "#FBBF24",
        "orange": "#F97316",
        "red": "#EF4444",
        "gray": "#94A3B8"
    }
    
    def get_color_for_value(
        self, 
        value: float,
        score_type: str = "positive_ascending",
        thresholds: Optional[List[float]] = None,
        inverse: bool = False,
        context: Optional[str] = None
    ) -> str:
        """
        Bepaal kleur obv percentiel thresholds (8 bins).
        """
        # 1. Determine Palette
        palette = self.PALETTE_NORMAL
        if context and "samenstelling" in context.lower():
            palette = self.PALETTE_BLUE
            
        # 2. Threshold Binning (Percentiles)
        if thresholds and len(thresholds) == 7:
            # thresholds = [p12.5, p25, p37.5, p50, p62.5, p75, p87.5]
            bin_idx = 0
            for i, t in enumerate(thresholds):
                if value < t:
                    bin_idx = i
                    break
            else:
                bin_idx = 7
                
            # Inverse logic
            # +/+ : Normal (high = green)
            # +/- : Reverse (high = red)
            # -/- : Reverse (low = green, high = red)
            # -/+ : Normal (low = red, high = green)
            should_reverse = score_type in ['+/-', '-/-', '-=-'] or score_type == "positive_descending" or inverse
            if should_reverse:
                bin_idx = 7 - bin_idx
                
            return palette[bin_idx]

        # 3. Fallback: Interpolation (Legacy or no data)
        return self.COLOR_MAP["gray"]

    def _interpolate_hex(self, hex1: str, hex2: str, t: float) -> str:
        # Legacy method kept for compatibility if needed, but unused in new logic
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"
        
    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        if max_val == min_val: return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

