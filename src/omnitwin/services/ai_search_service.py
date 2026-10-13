"""
AI-zoeken naar indicatoren (#233): begrippen, woorden uit de naam en betekenis (embeddings) samen.

De rangschikking zelf staat in services/zoektaal.py (zonder database of model te testen); deze
service haalt de indicatoren en de gelijkenissen uit de database (pgvector) en voegt de
beschrijvende velden toe.

AI-usecase C (#307): het embeddingmodel alleen als C is vrijgegeven. Dicht: alleen begrippen
(db/stuurdata/synoniemen.json) en woorden uit de naam, zonder aanroep van het model; elke zoekactie
(ook een geweigerde) komt in het AI-logboek (#313).
"""

import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin import ai_logboek, ai_vrijgave
from omnitwin.services import zoektaal

logger = logging.getLogger(__name__)

# Model per proces (embedding_model.gedeeld_model); None = (nog) niet geladen of niet beschikbaar
_model = None


class AISearchService:
    """Service voor zoeken in de indicatoren met gewone taal."""

    def __init__(self, db: Session, functie: str = "Zoeken"):
        self.db = db
        self.functie = functie  # naam in het AI-logboek
        self.zonder_betekenis = False  # True na een zoekactie met usecase C dicht

    def _ensure_model(self):
        global _model
        if _model is None:
            try:
                from omnitwin.services.logging_service import AppLogger
                from omnitwin.services.embedding_model import MODEL_ID, MODEL_REVISIE, gedeeld_model

                AppLogger.info(
                    f"Initialiseren van AISearch model ({MODEL_ID}@{MODEL_REVISIE[:8]})...", category="SERVER"
                )
                _model = gedeeld_model()
            except Exception as e:
                logger.error(f"Fout bij laden van AI model: {e}")

    def _gelijkenissen(self, query_text: str) -> Dict[str, float]:
        """Cosinusgelijkenis van de vraag met elke indicator met een embedding van het huidige model."""
        from omnitwin.services import embedding_model

        vector = _model.encode(embedding_model.VRAAG_VOORVOEGSEL + query_text, normalize_embeddings=True).tolist()
        rows = self.db.execute(
            text("""
            SELECT CAST(e.indicator_uuid AS text), 1 - (e.embedding <=> CAST(:vector AS vector))
            FROM indicator_embeddings e
            JOIN indicatoren i ON i.uuid = e.indicator_uuid AND i.is_actief = true
            WHERE e.model_naam = :model
        """),
            {"vector": vector, "model": embedding_model.MODEL_NAAM},
        ).fetchall()
        return {r[0]: float(r[1]) for r in rows}

    def search_indicators(self, query_text: str, limit: int = 5, zonder_ai: bool = False) -> List[Dict[str, Any]]:
        """
        Zoekt de indicatoren die bij een vraag passen, de beste eerst.

        Per resultaat: score (0-1, zie services/zoektaal.py), relevantie ('sterk' of 'matig') en
        redenen (begrip, naam, betekenis). Alleen resultaten binnen MAX_AFSTAND van de beste;
        een lege lijst als niets goed genoeg past. Er wordt niet op ontologie_status gefilterd
        (#139); ontologie_status en gevalideerd staan erbij.

        zonder_ai: alleen trefwoorden (ook na een mislukte logregel: fail-closed, #313).
        """
        from omnitwin.services import embedding_model

        gelijkenis: Dict[str, float] = {}
        self.zonder_betekenis = zonder_ai or not ai_vrijgave.poort(ai_vrijgave.C, self.functie, taak=query_text)
        if not self.zonder_betekenis:
            self._ensure_model()
            if _model is None:
                ai_logboek.schrijf(
                    ai_vrijgave.C,
                    self.functie,
                    ai_logboek.FOUT,
                    taak=query_text,
                    model=embedding_model.MODEL_ID,
                    modelversie=embedding_model.MODEL_REVISIE,
                    foutmelding="Embeddingmodel niet geladen",
                )
                return [{"error": "AI model niet geladen"}]
            gelijkenis = self._gelijkenissen(query_text)
        rows = self.db.execute(
            text("""
            SELECT DISTINCT ON (i.uuid)
                CAST(i.uuid AS text), i.naam,
                COALESCE(NULLIF(i.ontologische_beschrijving, ''), NULLIF(i.beschrijving_ai, ''), i.omschrijving),
                COALESCE(vkh.titel_naam, i.categorie), vkh.thema_naam, vkh.onderdeel_naam,
                i.ontologie_status, i.eenheid, i.score_type
            FROM indicatoren i
            LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            WHERE i.is_actief = true
            ORDER BY i.uuid
        """)
        ).fetchall()
        meta = {r[0]: r for r in rows}
        onder, boven = zoektaal.relatieve_grenzen(
            gelijkenis, embedding_model.GELIJKENIS_MARGE_ONDER, embedding_model.GELIJKENIS_MARGE_BOVEN
        )
        # tekst: kompaspad en beschrijving, voor woorden die niet in de naam staan (#233)
        rangen = zoektaal.rangschik(
            query_text,
            [
                {"uuid": u, "naam": r[1], "tekst": " ".join(x for x in (r[3], r[4], r[5], r[2]) if x)}
                for u, r in meta.items()
            ],
            gelijkenis,
            zoektaal.laad_begrippen(),
            onder,
            boven,
            limit=limit,
        )

        uit = []
        for rang in rangen:
            _, naam, beschrijving, categorie, thema, onderdeel, status, eenheid, score_type = meta[rang.uuid]
            uit.append(
                {
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
                    "ai": not self.zonder_betekenis,  # #312: het embeddingmodel deed mee (usecase C)
                }
            )
        if not self.zonder_betekenis and not ai_logboek.schrijf(
            ai_vrijgave.C,
            self.functie,
            ai_logboek.UITGEVOERD,
            taak=query_text,
            bronnen=[r["uuid"] for r in uit],
            model=embedding_model.MODEL_ID,
            modelversie=embedding_model.MODEL_REVISIE,
            resultaat=f"{len(uit)} resultaten",
        ):
            # Fail-closed: niet gelogd = geen resultaat op betekenis, wel op trefwoorden
            return self.search_indicators(query_text, limit, zonder_ai=True)
        return uit
