from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataControleService:
    """Service voor het beheren van data lineage en het controleren van bron-updates."""

    def __init__(self, db: Session):
        self.db = db

    def check_cbs_odata_update(self, dataset_id: str, endpoint: str = "opendata.cbs.nl") -> Dict[str, Any]:
        """
        Checkt de CBS OData API v4 op de 'Modified' datum van een dataset.

        Args:
            dataset_id: De code van de CBS dataset (bijv. '85984NED', '50150NED')
            endpoint: 'opendata.cbs.nl' of 'dataderden.cbs.nl'

        Returns:
            Dict met update status en datums.
        """
        url = f"https://{endpoint}/ODataApi/OData/{dataset_id}/TableInfos"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if "value" in data and len(data["value"]) > 0:
                info = data["value"][0]
                modified_str = info.get("Modified")
                return {"source": "CBS", "dataset": dataset_id, "modified_at_source": modified_str, "status": "success"}
            return {"status": "error", "message": "Geen TableInfos gevonden voor dataset"}
        except Exception as e:
            logger.error(f"Error checking CBS dataset {dataset_id}: {e}")
            return {
                "status": "error",
                "message": "Bron niet bereikbaar of onverwacht antwoord (details in de serverlog)",
            }

    def resolve_source_url(self, bron_systeem: Optional[str], bron_ref: Optional[str]) -> Optional[str]:
        """Genereert de catalogus URL voor een bronsysteem."""
        if not bron_systeem or not bron_ref:
            return None
        s = bron_systeem.upper()
        if s in ["CBS_ODATA", "CBS ODATA"]:
            return f"https://opendata.cbs.nl/#/CBS/nl/dataset/{bron_ref}/table"
        elif s in ["RIVM_STATLINE", "POLITIE_DATA"]:
            return (
                f"https://opendata.cbs.nl/#/CBS/nl/dataset/{bron_ref}/table"
                if "NED" in bron_ref.upper()
                else "https://www.volksgezondheidenzorg.info/"
            )
        elif s == "BAG_API":
            return "https://bag.basisregistraties.overheid.nl/"
        elif s == "OV_API":
            return "https://openov.nl/"
        return None

    def run_indicator_check(self, indicator_uuid: str) -> Dict[str, Any]:
        """
        Voert een data lineage check uit voor een specifieke indicator.
        Updates de 'laatste_check_datum' en eventueel 'laatste_update_bron'.
        """
        # 1. Haal indicator info op
        query = text("""
            SELECT uuid, naam, bron_systeem_api, bron_tabel_referentie, laatste_update_bron, laatste_check_datum 
            FROM indicatoren 
            WHERE uuid = :uuid
        """)
        indicator = self.db.execute(query, {"uuid": indicator_uuid}).fetchone()

        if not indicator:
            return {"error": "Indicator niet gevonden"}

        uuid, naam, bron_systeem, bron_ref, laatste_update_db, laatste_check_db = indicator

        url = self.resolve_source_url(bron_systeem, bron_ref)

        result = {
            "uuid": str(uuid),
            "naam": naam,
            "bron_systeem": bron_systeem,
            "bron_referentie": bron_ref,
            "bron_url": url,
            "checked_at": datetime.now().isoformat(),
            "has_update": False,
            "status": "actueel",
        }

        # 2. Voer OData check uit indien van toepassing
        if bron_systeem and bron_ref:
            bs = bron_systeem.upper()
            endpoint = "dataderden.cbs.nl" if bs in ["RIVM_STATLINE", "POLITIE_DATA"] else "opendata.cbs.nl"

            if bs in ["CBS_ODATA", "CBS ODATA", "RIVM_STATLINE", "POLITIE_DATA"]:
                cbs_result = self.check_cbs_odata_update(bron_ref, endpoint)
                if cbs_result["status"] == "success":
                    modified_at_source = cbs_result.get("modified_at_source")
                    result["modified_at_source"] = modified_at_source

                    if modified_at_source:
                        result["has_update"] = False  # synchroon na check

                        update_query = text("""
                            UPDATE indicatoren 
                            SET laatste_check_datum = CURRENT_TIMESTAMP,
                                laatste_update_bron = :mod_date
                            WHERE uuid = :uuid
                        """)
                        self.db.execute(update_query, {"uuid": uuid, "mod_date": modified_at_source})
            else:
                update_query = text("""
                    UPDATE indicatoren 
                    SET laatste_check_datum = CURRENT_TIMESTAMP 
                    WHERE uuid = :uuid
                """)
                self.db.execute(update_query, {"uuid": uuid})

        self.db.commit()
        return result

    def batch_run_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Run checks for indicators that have a source system defined (batched)."""
        query = text("""
            SELECT uuid 
            FROM indicatoren 
            WHERE bron_systeem_api IS NOT NULL AND is_actief = true
            ORDER BY laatste_check_datum ASC NULLS FIRST
            LIMIT :limit
        """)
        uuids = self.db.execute(query, {"limit": limit}).fetchall()

        results = []
        for (u_id,) in uuids:
            results.append(self.run_indicator_check(u_id))

        return results

    def herbereken_statistieken(self, indicator_uuids: List[str]) -> Dict[str, Any]:
        """Herbereken min_waarde en max_waarde voor de gegeven indicatoren op basis van gebied_data."""
        if not indicator_uuids:
            return {"status": "success", "message": "Geen indicatoren opgegeven."}

        try:
            # For each indicator, calculate min and max from gebied_data
            for uuid in indicator_uuids:
                query = text("""
                    WITH stats AS (
                        SELECT MIN(waarde) as min_w, MAX(waarde) as max_w
                        FROM gebied_data
                        WHERE indicator_uuid = :uuid
                    )
                    UPDATE indicatoren
                    SET min_waarde = stats.min_w, max_waarde = stats.max_w
                    FROM stats
                    WHERE uuid = :uuid
                """)
                self.db.execute(query, {"uuid": uuid})
            self.db.commit()
            return {"status": "success", "message": f"{len(indicator_uuids)} indicatoren herrekend."}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error herbereken_statistieken: {e}")
            return {"status": "error", "message": "Herberekenen mislukt (details in de serverlog)"}

    def genereer_ontologie(self, indicator_uuids: List[str]) -> Dict[str, Any]:
        """Trigger AI ontologie generatie voor indicatoren."""
        if not indicator_uuids:
            return {"status": "success", "message": "Geen indicatoren opgegeven."}

        try:
            for uuid in indicator_uuids:
                query = text("""
                    UPDATE indicatoren
                    SET ontologie_status = 'draft',
                        ontologische_beschrijving = '[AI Generatie in behandeling] Ontologie wordt bepaald...'
                    WHERE uuid = :uuid
                """)
                self.db.execute(query, {"uuid": uuid})
            self.db.commit()
            return {
                "status": "success",
                "message": f"Ontologie-generatie gestart voor {len(indicator_uuids)} indicatoren.",
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error genereer_ontologie: {e}")
            return {"status": "error", "message": "Ontologie-generatie mislukt (details in de serverlog)"}
