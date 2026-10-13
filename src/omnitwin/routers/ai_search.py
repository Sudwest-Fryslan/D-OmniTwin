from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.services.ai_search_service import AISearchService

router = APIRouter(prefix="/api/ai", tags=["AI Search & Intelligence"])


def get_service(db: Session = Depends(get_db)) -> AISearchService:
    """Dependency injection voor AISearchService"""
    return AISearchService(db, functie="Kompas-zoeken")


@router.get("/kompas/search", response_model=list[dict[str, Any]])
def search_kompas(
    q: str = Query(..., min_length=2, description="De zoekterm of vraag"),
    limit: int = Query(10, ge=1, le=20),
    service: AISearchService = Depends(get_service),
):
    """
    Zoekt indicatoren in het Kompas bij een vraag in gewone taal: begrippen, naam en betekenis.
    Betekenis (embeddingmodel) alleen met AI-usecase C open (#307); anders op trefwoorden en synoniemen.
    """
    return service.search_indicators(q, limit=limit)


@router.get("/health")
def health_check():
    """Health check voor AI-zoeken, met de status van het embeddingmodel (#118)."""
    from omnitwin.services import embedding_model

    return {"status": "healthy", "service": "AI Search API", "embedding_model": embedding_model.status()}
