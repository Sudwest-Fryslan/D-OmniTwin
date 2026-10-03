"""
Gebiedsmonitor Service Layer
=============================
Business logic en database queries voor Gebiedsmonitor API endpoints.

Gebruik parameterized queries voor dynamic filtering op basis van indicator selectie.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import numpy as np


from omnitwin.services.kompas_service import KompasScoringService

class GebiedsmonitorService:
    """Service class voor Gebiedsmonitor data operaties"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scoring = KompasScoringService()
    
    # ... (skipping unchanged methods) ...

    # ========================================================================
    # Kaart Data (GeoJSON)
    # ========================================================================
    
    def get_kaart_attributes(
        self,
        gebiedstype_id: str,
        indicator_uuid: Optional[str] = None,
        show_all: bool = False,
        gemeente_code: Optional[str] = None,
        jaar: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Haal attribuut data op voor kaartvisualisatie (ZONDER geometry).
        Ontworpen voor de Hybride "Lego" architectuur.
        """
        from omnitwin.services.color_scale_service import ColorScaleService
        from omnitwin.services.logging_service import AppLogger
        
        AppLogger.debug(f"get_kaart_attributes executing for gebiedstype {gebiedstype_id}", category="KAART")
        
        # 1. Base Query: Zonder geometry!
        query_base = """
            SELECT 
                g.id, 
                g.naam, 
                g.gebiedstype_id,
                i.waarde as indicator_waarde,
                i.jaar,
                i.bron,
                ind.naam as indicator_naam,
                ind.code as indicator_code,
                ind.eenheid,
                COALESCE(ind.score_type, '+/+') as score_type
            FROM gebieden g
        """
        
        # 2. Join Logic
        if indicator_uuid:
            if jaar is not None:
                join_type = "LEFT JOIN" if show_all else "INNER JOIN"
                query_base += f"""
                    {join_type} (
                        SELECT gebied_id, indicator_uuid, waarde, jaar, bron 
                        FROM gebied_data 
                        WHERE indicator_uuid = CAST(:indicator_uuid AS uuid) 
                        AND jaar = :jaar
                        AND COALESCE(scenario_id, 'current') = 'current'
                    ) i ON g.id = i.gebied_id
                    LEFT JOIN indicatoren ind ON ind.uuid = CAST(:indicator_uuid AS uuid)
                """
            else:
                join_type = "LEFT JOIN" if show_all else "INNER JOIN"
                query_base += f"""
                    {join_type} vw_gebied_indicator_actueel i 
                        ON g.id = i.gebied_id AND i.indicator_uuid = CAST(:indicator_uuid AS uuid)
                    LEFT JOIN indicatoren ind ON ind.uuid = CAST(:indicator_uuid AS uuid)
                """
        else:
            # placeholders for no indicator
            query_base += """
                CROSS JOIN (SELECT NULL as waarde, NULL as jaar, NULL as bron) i
                CROSS JOIN (SELECT NULL as naam, NULL as code, NULL as eenheid, '+/+' as score_type) ind
            """

        # 3. Filters
        query_base += " WHERE g.gebiedstype_id = CAST(:gebiedstype_id AS uuid)"
        
        if gemeente_code:
            query_base += " AND g.gemeente_code = :gemeente_code"
        
        # 4. Execute
        params = {
            "gebiedstype_id": gebiedstype_id,
            "indicator_uuid": indicator_uuid
        }
        if gemeente_code:
            params["gemeente_code"] = gemeente_code
        if jaar is not None:
            params["jaar"] = jaar
            
        result = self.db.execute(text(query_base), params)
        rows = [dict(row._mapping) for row in result]
        
        # 5. Calculate Colors using ColorScaleService
        color_service = ColorScaleService(self.db)
        all_values = [float(r["indicator_waarde"]) for r in rows if r["indicator_waarde"] is not None] if indicator_uuid else []
        
        color_ramp = []
        breaks = []
        nodata_color = "#94A3B8"  # Default grey
        
        if indicator_uuid and len(all_values) > 0:
            color_ramp, breaks, nodata_color = color_service.compute_colors_for_data(
                all_values, indicator_uuid
            )
        
        data_dict = {}
        for row in rows:
            color = nodata_color
            if row["indicator_waarde"] is not None and len(color_ramp) > 0:
                color = color_service.get_color_for_value(
                    float(row["indicator_waarde"]), color_ramp, breaks, nodata_color
                )
            elif indicator_uuid and not show_all:
                continue 
                
            data_dict[str(row["id"])] = {
                "indicator_waarde": float(row["indicator_waarde"]) if row["indicator_waarde"] is not None else None,
                "color": color,
                "heeft_data": row["indicator_waarde"] is not None,
                "jaar": row["jaar"],
                "bron": row["bron"]
            }
            
        features_with_data = sum(1 for props in data_dict.values() if props["heeft_data"])

        count_query = "SELECT COUNT(*) FROM gebieden WHERE gebiedstype_id = CAST(:gebiedstype_id AS uuid)"
        count_params = {"gebiedstype_id": gebiedstype_id}
        if gemeente_code:
            count_query += " AND gemeente_code = :gemeente_code"
            count_params["gemeente_code"] = gemeente_code

        total_in_database = self.db.execute(text(count_query), count_params).scalar() or 0

        return {
            "metadata": {
                "count": len(data_dict),
                "method": "hybrid_attributes_only",
                "color_ramp": color_ramp if indicator_uuid else [],
                "nodata_color": nodata_color,
                "total_features": total_in_database,
                "features_with_data": features_with_data,
                "indicator_naam": rows[0]["indicator_naam"] if rows and indicator_uuid else None,
                "indicator_code": rows[0]["indicator_code"] if rows and indicator_uuid else None,
                "eenheid": rows[0]["eenheid"] if rows and indicator_uuid else None,
                "score_type": rows[0]["score_type"] if rows and indicator_uuid else None,
                # #161: bij één unieke waarde is er geen spreiding om te kleuren
                "aantal_unieke_waarden": len(set(all_values)),
                "legenda_melding": (
                    "Alle gebieden hebben dezelfde waarde: geen kleurverschil."
                    if len(set(all_values)) == 1 and len(all_values) > 1 else None
                ),
            },
            "data": data_dict
        }

    
    def get_gebiedstypes(self) -> List[Dict[str, Any]]:
        """
        Haal alle gebiedstypes op met aantal gebieden.
        
        Note: Gebruikt nu vw_gebied_kaart_basis om het aantal 'zichtbare'
        gebieden te tellen (dus zonder water).
        """
        query = text("""
            SELECT 
                gt.id,
                gt.naam,
                gt.code,
                gt.beschrijving,
                gt.bron,
                gt.niveau,
                COUNT(DISTINCT g.id) as aantal_gebieden
            FROM gebiedstypes gt
            LEFT JOIN vw_gebied_kaart_basis g ON gt.id = g.gebiedstype_id
            GROUP BY gt.id, gt.naam, gt.code, gt.beschrijving, gt.bron, gt.niveau
            ORDER BY gt.naam
        """)
        
        result = self.db.execute(query)
        return [dict(row._mapping) for row in result]
    
    # ========================================================================
    # Gebieden
    # ========================================================================
    
    def get_gebieden(
        self, 
        gebiedstype_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Haal gebieden op met optional filter op gebiedstype.
        
        Args:
            gebiedstype_id: UUID van gebiedstype (optioneel)
            limit: Aantal resultaten
            offset: Paginatie offset
            
        Returns:
            Dict met total count en lijst van gebieden
        """
        # Count query
        count_query = text("""
            SELECT COUNT(*) as total
            FROM gebieden g
            WHERE (:gebiedstype_id IS NULL OR g.gebiedstype_id = CAST(:gebiedstype_id AS uuid))
              AND g.actief = true
        """)
        
        total = self.db.execute(
            count_query, 
            {"gebiedstype_id": gebiedstype_id}
        ).scalar()
        
        # Data query
        data_query = text("""
            SELECT 
                g.id,
                g.naam,
                gt.naam as gebiedstype_naam,
                CASE WHEN gd.gebied_id IS NOT NULL THEN true ELSE false END as heeft_data,
                COUNT(DISTINCT gd.indicator_uuid) as aantal_indicatoren
            FROM gebieden g
            INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            LEFT JOIN gebied_data gd ON g.id = gd.gebied_id
            WHERE (:gebiedstype_id IS NULL OR g.gebiedstype_id = CAST(:gebiedstype_id AS uuid))
              AND g.actief = true
            GROUP BY g.id, g.naam, gt.naam, gd.gebied_id
            ORDER BY g.naam
            LIMIT :limit OFFSET :offset
        """)
        
        result = self.db.execute(
            data_query,
            {
                "gebiedstype_id": gebiedstype_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        gebieden = [dict(row._mapping) for row in result]
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "gebieden": gebieden
        }
    
    def get_gebied_detail(self, gebied_id: str) -> Optional[Dict[str, Any]]:
        """
        Haal details van een specifiek gebied op inclusief alle indicator waarden.
        
        Args:
            gebied_id: ID van het gebied
            
        Returns:
            Dict met gebied info en indicatoren, of None als niet gevonden
        """
        # Gebied info
        gebied_query = text("""
            SELECT 
                g.id,
                g.naam,
                gt.id as gebiedstype_id,
                gt.naam as gebiedstype_naam,
                gt.code as gebiedstype_code,
                ST_X(g.geom_centroid) as centroid_x,
                ST_Y(g.geom_centroid) as centroid_y,
                g.metadata
            FROM gebieden g
            INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.id = :gebied_id
              AND g.actief = true
        """)
        
        gebied_result = self.db.execute(
            gebied_query,
            {"gebied_id": gebied_id}
        ).fetchone()
        
        if not gebied_result:
            return None
        
        gebied_dict = dict(gebied_result._mapping)
        
        # Indicator waarden (alleen meest recente jaar per indicator)
        indicatoren_query = text("""
            SELECT DISTINCT ON (i.uuid)
                i.uuid,
                i.naam,
                i.code,
                i.eenheid,
                gd.waarde,
                gd.jaar,
                gd.datum,
                gd.bron
            FROM gebied_data gd
            INNER JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            WHERE gd.gebied_id = :gebied_id AND i.is_actief = true
            ORDER BY i.uuid, gd.jaar DESC
        """)
        
        indicatoren_result = self.db.execute(
            indicatoren_query,
            {"gebied_id": gebied_id}
        )
        
        indicatoren = [dict(row._mapping) for row in indicatoren_result]
        
        return {
            "gebied": {
                "id": gebied_dict["id"],
                "naam": gebied_dict["naam"],
                "gebiedstype": {
                    "id": str(gebied_dict["gebiedstype_id"]),
                    "naam": gebied_dict["gebiedstype_naam"],
                    "code": gebied_dict["gebiedstype_code"]
                },
                "centroid": {
                    "x": float(gebied_dict["centroid_x"]) if gebied_dict["centroid_x"] else None,
                    "y": float(gebied_dict["centroid_y"]) if gebied_dict["centroid_y"] else None
                } if gebied_dict["centroid_x"] and gebied_dict["centroid_y"] else None,
                "metadata": gebied_dict["metadata"]
            },
            "indicatoren": indicatoren
        }
    
    # ========================================================================
    # Indicatoren
    # ========================================================================
    
    def get_indicatoren(
        self, 
        gebiedstype_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Haal indicatoren op, optioneel gefilterd op gebiedstype.
        UPDATED: Toont ALLE indicatoren, ook zonder data.
        
        Args:
            gebiedstype_id: UUID van gebiedstype (optioneel)
            
        Returns:
            List van indicatoren met metadata
        """
        if gebiedstype_id:
            # Met gebiedstype filter: toon ALLE indicatoren, sorteer op coverage
            query = text("""
                SELECT 
                    i.uuid,
                    i.naam,
                    i.code,
                    i.omschrijving,
                    i.eenheid,
                    i.categorie,
                    COALESCE(COUNT(DISTINCT CASE 
                        WHEN g.gebiedstype_id = CAST(:gebiedstype_id AS uuid) 
                        THEN gd.gebied_id 
                    END), 0) as aantal_gebieden_met_data,
                    COALESCE(COUNT(DISTINCT gd.id), 0) as aantal_metingen,
                    MAX(gd.jaar) as nieuwste_jaar
                FROM indicatoren i
                LEFT JOIN gebied_data gd ON i.uuid = gd.indicator_uuid
                LEFT JOIN gebieden g ON gd.gebied_id = g.id
                WHERE i.status IN ('O', 'C') AND i.is_actief = true
                GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
                ORDER BY 
                    COUNT(DISTINCT CASE 
                        WHEN g.gebiedstype_id = CAST(:gebiedstype_id AS uuid) 
                        THEN gd.gebied_id 
                    END) DESC NULLS LAST,
                    i.naam
            """)
            
            result = self.db.execute(query, {"gebiedstype_id": gebiedstype_id})
        else:
            # Zonder filter: alle operationele indicatoren
            query = text("""
                SELECT 
                    i.uuid,
                    i.naam,
                    i.code,
                    i.omschrijving,
                    i.eenheid,
                    i.categorie,
                    COUNT(DISTINCT gd.id) as aantal_metingen
                FROM indicatoren i
                LEFT JOIN gebied_data gd ON i.uuid = gd.indicator_uuid
                WHERE i.status IN ('O', 'C') AND i.is_actief = true
                GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
                ORDER BY i.naam
            """)
            
            result = self.db.execute(query)
        
        return [dict(row._mapping) for row in result]
    

