from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import logging

# Note: We import sentence-transformers here, but we should handle the case where it's not installed
# In a production environment, you might want to load the model once at startup.
try:
    from sentence_transformers import SentenceTransformer
    # Global model instance for reuse
    _model = None
except ImportError:
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
                AppLogger.info("Initialiseren van AISearch model (all-MiniLM-L6-v2)...", category="SERVER")
                _model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Fout bij laden van AI model: {e}")

    def search_indicators(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Zoekt naar de meest relevante indicatoren op basis van een tekstquery.
        Gebruikt Cosine Similarity via pgvector.
        Prefereert menselijk gevalideerde beschrijvingen boven AI-gegenereerde.
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
                i.categorie,
                i.ontologie_status,
                i.eenheid,
                i.score_type,
                (e.embedding <=> CAST(:vector AS vector)) as distance
            FROM indicatoren i
            JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
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
            uuid, naam, beschrijving, categorie, ontologie_status, eenheid, score_type, distance = row
            # Score is 1 - distance voor Cosine Similarity
            score = 1 - float(distance)
            
            search_results.append({
                "uuid": str(uuid),
                "naam": naam,
                "beschrijving": beschrijving,
                "categorie": categorie,
                "ontologie_status": ontologie_status or "draft",
                "eenheid": eenheid,
                "score_type": score_type,
                "score": round(score, 4)
            })

        return search_results
