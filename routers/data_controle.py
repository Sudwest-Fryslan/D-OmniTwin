from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from services.data_controle_service import DataControleService
from typing import List, Dict, Any
from pydantic import BaseModel
from services.deduplicatie_service import DeduplicatieService

class MergeRequest(BaseModel):
    primary_uuid: str
    duplicate_uuids: List[str]
    actie: str  # 'exact_duplicaat' of 'groepeer_bronnen'
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

def get_dedup_service(db: Session = Depends(get_db)) -> DeduplicatieService:
    return DeduplicatieService(db)

@router.get("/deduplicatie/kandidaten", response_model=List[Dict[str, Any]])
async def get_dedup_kandidaten(
    service: DeduplicatieService = Depends(get_dedup_service)
):
    """Haalt potentiele dubbele indicatoren op (Sprint 21 Data Kwaliteit)"""
    try:
        return service.get_kandidaten()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deduplicatie/merge", response_model=Dict[str, Any])
async def merge_indicatoren(
    req: MergeRequest,
    service: DeduplicatieService = Depends(get_dedup_service)
):
    """Merged of deactiveert dubbele indicatoren (Sprint 21)"""
    if req.actie not in ["exact_duplicaat", "groepeer_bronnen"]:
        raise HTTPException(status_code=400, detail="Ongeldige actie")
    try:
        return service.merge_indicatoren(req.primary_uuid, req.duplicate_uuids, req.actie)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
