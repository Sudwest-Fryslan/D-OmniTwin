from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from services.data_controle_service import DataControleService
from typing import List, Dict, Any

router = APIRouter(
    prefix="/api/data-controle",
    tags=["Data Controle & Lineage"]
)

def get_service(db: Session = Depends(get_db)) -> DataControleService:
    """Dependency injection voor DataControleService"""
    return DataControleService(db)

@router.get("/run", response_model=List[Dict[str, Any]])
async def run_all_checks(
    service: DataControleService = Depends(get_service)
):
    """
    Voert data lineage checks uit voor alle indicatoren die een bron_systeem_api hebben.
    """
    try:
        results = service.batch_run_all()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check/{indicator_uuid}", response_model=Dict[str, Any])
async def check_single_indicator(
    indicator_uuid: str,
    service: DataControleService = Depends(get_service)
):
    """
    Voert een data check uit voor één specifieke indicator op basis van UUID.
    """
    result = service.run_indicator_check(indicator_uuid)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/health")
async def health_check():
    """Simple health check for Data Controle API."""
    return {"status": "healthy", "service": "Data Controle API"}
