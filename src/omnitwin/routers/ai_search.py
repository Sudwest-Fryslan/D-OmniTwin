from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from omnitwin.database import get_db
from omnitwin.services.ai_search_service import AISearchService
from typing import List, Dict, Any

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Search & Intelligence"]
)

def get_service(db: Session = Depends(get_db)) -> AISearchService:
    """Dependency injection voor AISearchService"""
    return AISearchService(db)

@router.get("/kompas/search", response_model=List[Dict[str, Any]])
def search_kompas(
    q: str = Query(..., min_length=2, description="De zoekterm of vraag"),
    limit: int = Query(10, ge=1, le=20),
    service: AISearchService = Depends(get_service)
):
    """
    Zoekt semantisch naar indicatoren in het Kompas op basis van een natuurlijke taal query.
    """
    try:
        results = service.search_indicators(q, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check voor AI-zoeken, met de status van het embeddingmodel (#118)."""
    from omnitwin.services import embedding_model
    return {"status": "healthy", "service": "AI Search API",
            "embedding_model": embedding_model.status()}
