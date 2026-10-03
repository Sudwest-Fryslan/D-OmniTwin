"""
Gebiedsmonitor API Router
==========================
FastAPI endpoints voor Gebiedsmonitor data met deck.gl 3D visualisatie.

Endpoints:
- GET /gebiedstypes - Lijst van gebiedstypes
- GET /gebieden - Lijst van gebieden (met paginatie)
- GET /gebieden/{id} - Details van een gebied
- GET /indicatoren - Lijst van indicatoren
- GET /kaart/{type_id} - GeoJSON voor kaartvisualisatie
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from uuid import UUID

from omnitwin.database import get_db
from omnitwin.version import __version__
from omnitwin.services.gebiedsmonitor_service import GebiedsmonitorService
from omnitwin.schemas.gebiedsmonitor import (
    GebiedstypesListResponse,
    GebiedenListResponse,
    GebiedDetailResponse,
    IndicatorenListResponse,
    GeoJSONFeatureCollection
)

router = APIRouter(
    prefix="/api/gebiedsmonitor",
    tags=["Gebiedsmonitor"]
)


# ============================================================================
# Helper function
# ============================================================================

def get_service(db: Session = Depends(get_db)) -> GebiedsmonitorService:
    """Dependency injection voor service"""
    return GebiedsmonitorService(db)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/gebiedstypes", response_model=GebiedstypesListResponse)
def get_gebiedstypes(
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal alle beschikbare gebiedstypes op.
    
    Returns:
        Lijst van gebiedstypes met aantal gebieden per type
    """
    gebiedstypes = service.get_gebiedstypes()
    return {"gebiedstypes": gebiedstypes}


@router.get("/gebieden", response_model=GebiedenListResponse)
def get_gebieden(
    gebiedstype_id: Optional[str] = Query(None, description="Filter op gebiedstype UUID"),
    limit: int = Query(50, ge=1, le=500, description="Aantal resultaten"),
    offset: int = Query(0, ge=0, description="Paginatie offset"),
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal gebieden op met optional filtering en paginatie.
    
    Args:
        gebiedstype_id: Optional UUID van gebiedstype om op te filteren
        limit: Maximaal aantal resultaten (1-500)
        offset: Aantal records om over te slaan voor paginatie
    
    Returns:
        Lijst van gebieden met pagination metadata
    """
    result = service.get_gebieden(
        gebiedstype_id=gebiedstype_id,
        limit=limit,
        offset=offset
    )
    return result


@router.get("/gebieden/{gebied_id}", response_model=GebiedDetailResponse)
def get_gebied_detail(
    gebied_id: str,
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal gedetailleerde informatie op van een specifiek gebied,
    inclusief alle indicator waarden.
    
    Args:
        gebied_id: ID van het gebied (bijv. "BU19000000")
    
    Returns:
        Gebied details met alle indicator data
        
    Raises:
        HTTPException 404: Als gebied niet gevonden
    """
    result = service.get_gebied_detail(gebied_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Gebied met ID '{gebied_id}' niet gevonden"
        )
    
    return result


@router.get("/indicatoren", response_model=IndicatorenListResponse)
def get_indicatoren(
    gebiedstype_id: Optional[str] = Query(
        None, 
        description="Filter indicatoren die data hebben voor dit gebiedstype"
    ),
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal beschikbare indicatoren op.
    
    Als gebiedstype_id is opgegeven, worden alleen indicatoren getoond
    die data hebben voor dat specifieke gebiedstype.
    
    Args:
        gebiedstype_id: Optional UUID van gebiedstype
    
    Returns:
        Lijst van indicatoren met metadata over beschikbaarheid
    """
    indicatoren = service.get_indicatoren(gebiedstype_id=gebiedstype_id)
    return {"indicatoren": indicatoren}


@router.get("/kaart_data/{gebiedstype_id}", response_model=Dict[str, Any])
def get_kaart_attributes(
    gebiedstype_id: UUID,  # ongeldige UUID: 422 (#203)
    indicator_uuid: Optional[UUID] = Query(
        None, 
        description="OPTIONEEL: UUID van indicator om te visualiseren"
    ),
    show_all: bool = Query(
        False, 
        description="True = toon ook gebieden zonder data (grijs)"
    ),
    gemeente_code: Optional[str] = Query(
        None,
        description="Filter op specifieke gemeente"
    ),
    jaar: Optional[int] = Query(
        None,
        description="Optioneel: Specifiek jaar"
    ),
    modus: str = Query(
        "waarde",
        pattern="^(waarde|percentiel)$",
        description="waarde = kleur naar de werkelijke waarde; percentiel = percentielklasse 1-8 binnen de referentiegroep (#255)"
    ),
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal attribuut-data en berekende kleuren op voor kaartvisualisatie (Hybride aanpak).
    Retourneert een dictionary waarbij de keys de gebied_id's zijn, en de values
    kleuren, meetwaarden en overige attributen bevatten. (GEEN geometrie)
    """
    # Fouten gaan naar de centrale foutafhandeling: geen SQL of exceptietekst naar buiten (#203)
    return service.get_kaart_attributes(
        gebiedstype_id=str(gebiedstype_id),
        indicator_uuid=str(indicator_uuid) if indicator_uuid else None,
        show_all=show_all,
        gemeente_code=gemeente_code,
        jaar=jaar,
        modus=modus,
    )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
def health_check():
    """
    Simple health check endpoint voor Gebiedsmonitor API.
    """
    return {
        "status": "healthy",
        "service": "Gebiedsmonitor API",
        "version": __version__
    }
