"""
AI-zoeken naar indicatoren (#233): begrippen, woorden uit de naam en betekenis (embeddings) samen.

De rangschikking zelf staat in services/zoektaal.py (zonder database of model te testen); deze
service haalt de indicatoren en de gelijkenissen uit de database (pgvector) en voegt de
beschrijvende velden toe.
"""
import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin.services import zoektaal

logger = logging.getLogger(__name__)

# Model per proces (embedding_model.gedeeld_model); None = (nog) niet geladen of niet beschikbaar
_model = None


class AISearchService:
    """Service voor zoeken in de indicatoren met gewone taal."""

    def __init__(self, db: Session):
        self.db = db
        self._ensure_model()

    def _ensure_model(self):
        global _model
        if _model is None:
            try:
                from omnitwin.services.logging_service import AppLogger
                from omnitwin.services.embedding_model import MODEL_ID, MODEL_REVISIE, gedeeld_model
                AppLogger.info(f"Initialiseren van AISearch model ({MODEL_ID}@{MODEL_REVISIE[:8]})...", category="SERVER")
                _model = gedeeld_model()
            except Exception as e:
                logger.error(f"Fout bij laden van AI model: {e}")

    def _gelijkenissen(self, query_text: str) -> Dict[str, float]:
        """Cosinusgelijkenis van de vraag met elke indicator met een embedding van het huidige model."""
        from omnitwin.services import embedding_model
        vector = _model.encode(embedding_model.VRAAG_VOORVOEGSEL + query_text, normalize_embeddings=True).tolist()
        rows = self.db.execute(text("""
            SELECT CAST(e.indicator_uuid AS text), 1 - (e.embedding <=> CAST(:vector AS vector))
            FROM indicator_embeddings e
            JOIN indicatoren i ON i.uuid = e.indicator_uuid AND i.is_actief = true
            WHERE e.model_naam = :model
        """), {"vector": vector, "model": embedding_model.MODEL_NAAM}).fetchall()
        return {r[0]: float(r[1]) for r in rows}

    def search_indicators(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Zoekt de indicatoren die bij een vraag passen, de beste eerst.

        Per resultaat: score (0-1, zie services/zoektaal.py), relevantie ('sterk' of 'matig') en
        redenen (begrip, naam, betekenis). Alleen resultaten binnen MAX_AFSTAND van de beste;
        een lege lijst als niets goed genoeg past. Er wordt niet op ontologie_status gefilterd
        (#139); ontologie_status en gevalideerd staan erbij.
        """
        if _model is None:
            return [{"error": "AI model niet geladen"}]
        from omnitwin.services import embedding_model

        gelijkenis = self._gelijkenissen(query_text)
        rows = self.db.execute(text("""
            SELECT DISTINCT ON (i.uuid)
                CAST(i.uuid AS text), i.naam,
                COALESCE(NULLIF(i.ontologische_beschrijving, ''), NULLIF(i.beschrijving_ai, ''), i.omschrijving),
                COALESCE(vkh.titel_naam, i.categorie), vkh.thema_naam, vkh.onderdeel_naam,
                i.ontologie_status, i.eenheid, i.score_type
            FROM indicatoren i
            LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            WHERE i.is_actief = true
            ORDER BY i.uuid
        """)).fetchall()
        meta = {r[0]: r for r in rows}
        onder, boven = zoektaal.relatieve_grenzen(
            gelijkenis, embedding_model.GELIJKENIS_MARGE_ONDER, embedding_model.GELIJKENIS_MARGE_BOVEN)
        rangen = zoektaal.rangschik(query_text, [{"uuid": u, "naam": r[1]} for u, r in meta.items()],
                                    gelijkenis, zoektaal.laad_begrippen(), onder, boven, limit=limit)

        uit = []
        for rang in rangen:
            _, naam, beschrijving, categorie, thema, onderdeel, status, eenheid, score_type = meta[rang.uuid]
            uit.append({
                "uuid": rang.uuid,
                "naam": naam,
                "beschrijving": beschrijving,
                "categorie": categorie,
                "thema_naam": thema,
                "onderdeel_naam": onderdeel,
                "ontologie_status": status or "draft",
                "gevalideerd": status == "goedgekeurd_mens",
                "eenheid": eenheid,
                "score_type": score_type,
                "score": rang.score,
                "relevantie": rang.relevantie,
                "redenen": rang.redenen,
            })
        return uit
