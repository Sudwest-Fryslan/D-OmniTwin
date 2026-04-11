from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from src.database import get_db
from services.gebiedsmonitor_service import GebiedsmonitorService

router = APIRouter(
    prefix="/api/v2/kaart",
    tags=["Kaart V2 (Backend Simplification)"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{gebiedstype_id}")
def get_kaart_data_v2(
    gebiedstype_id: str,
    indicator_uuid: Optional[str] = Query(None, description="Optioneel: Indicator UUID voor kleuring"),
    show_all: bool = Query(False, description="Toon ook gebieden zonder data"),
    db: Session = Depends(get_db)
):
    """
    Haal kaartdata op (V2: Gebruikt SQL Views).
    """
    try:
        service = GebiedsmonitorService(db)
        # Note: We need to implement get_kaart_data_v2 in the service first
        return service.get_kaart_data_v2(gebiedstype_id, indicator_uuid, show_all)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
