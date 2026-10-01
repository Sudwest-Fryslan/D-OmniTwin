from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import logging

# sentence-transformers (en daarmee torch) wordt pas in _ensure_model geïmporteerd,
# zodat het importeren van deze module de start van de app niet vertraagt.
# Global model instance for reuse
_model = None

logger = logging.getLogger(__name__)

class AISearchService:
    """Service voor semantisch zoeken in de indicator ontologie."""

    def __init__(self, db: Session):
        self.db = db
        self._ensure_model()

    def _ensure_model(self):
        global _model
        if _model is None:
            try:
                from services.logging_service import AppLogger
                from services.embedding_model import MODEL_ID, MODEL_REVISIE, laad_model
                AppLogger.info(f"Initialiseren van AISearch model ({MODEL_ID}@{MODEL_REVISIE[:8]})...", category="SERVER")
                _model = laad_model()
            except Exception as e:
                logger.error(f"Fout bij laden van AI model: {e}")

    def search_indicators(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Zoekt naar de meest relevante indicatoren op basis van een tekstquery.
        Gebruikt Cosine Similarity via pgvector.
        Prefereert menselijk gevalideerde beschrijvingen boven AI-gegenereerde.
        Er wordt niet op ontologie_status gefilterd: ook concepten worden gevonden
        (#139). Per resultaat staan ontologie_status en gevalideerd erbij.
        """
        if _model is None:
            return [{"error": "AI model niet geladen"}]

        # 1. Query vectoriseren
        query_vector = _model.encode(query_text).tolist()

        # 2. Database query met pgvector cosine distance (<=>)
        # COALESCE: gevalideerde beschrijving > AI beschrijving > standaard omschrijving
        sql_query = text("""
            SELECT 
                i.uuid, 
                i.naam, 
                COALESCE(
                    NULLIF(i.ontologische_beschrijving, ''),
                    NULLIF(i.beschrijving_ai, ''),
                    i.omschrijving
                ) as beschrijving,
                COALESCE(vkh.titel_naam, i.categorie) as categorie,
                vkh.thema_naam,
                vkh.onderdeel_naam,
                i.ontologie_status,
                i.eenheid,
                i.score_type,
                (e.embedding <=> CAST(:vector AS vector)) as distance
            FROM indicatoren i
            JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
            LEFT JOIN v_kompas_hierarchie vkh
                ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
            WHERE i.is_actief = true
            ORDER BY distance ASC
            LIMIT :limit
        """)

        results = self.db.execute(sql_query, {
            "vector": query_vector,
            "limit": limit
        }).fetchall()

        # 3. Formateren van resultaten
        search_results = []
        for row in results:
            uuid, naam, beschrijving, categorie, thema_naam, onderdeel_naam, ontologie_status, eenheid, score_type, distance = row
            # Score is 1 - distance voor Cosine Similarity
            score = 1 - float(distance)
            
            search_results.append({
                "uuid": str(uuid),
                "naam": naam,
                "beschrijving": beschrijving,
                "categorie": categorie,
                "thema_naam": thema_naam,
                "onderdeel_naam": onderdeel_naam,
                "ontologie_status": ontologie_status or "draft",
                "gevalideerd": ontologie_status == "goedgekeurd_mens",
                "eenheid": eenheid,
                "score_type": score_type,
                "score": round(score, 4)
            })

        return search_results
