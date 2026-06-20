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
from typing import Optional

from src.database import get_db
from services.gebiedsmonitor_service import GebiedsmonitorService
from schemas.gebiedsmonitor import (
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
async def get_gebiedstypes(
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
async def get_gebieden(
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
async def get_gebied_detail(
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
async def get_indicatoren(
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


@router.get("/kaart/{gebiedstype_id}", response_model=GeoJSONFeatureCollection)
async def get_kaart_data(
    gebiedstype_id: str,
    indicator_uuid: Optional[str] = Query(
        None, 
        description="OPTIONEEL: UUID van indicator om te visualiseren"
    ),
    show_all: bool = Query(
        False,
        description="Als True, toon ook gebieden zonder data (grijze kleur op kaart)"
    ),
    gemeente_code: Optional[str] = Query(
        None,
        description="Filter op gemeente (CBS code, bijv. '1900' voor Súdwest-Fryslân)"
    ),
    jaar: Optional[int] = Query(
        None,
        description="OPTIONEEL: Specifiek jaar voor historische weergave op kaart"
    ),
    service: GebiedsmonitorService = Depends(get_service)
):
    """
    Haal GeoJSON data op voor kaartvisualisatie met deck.gl.
    
    **BELANGRIJK:** Dit endpoint gebruikt dynamic filtering.
    Default worden ALLEEN gebieden getoond die data hebben voor de geselecteerde indicator.
    
    **Voorbeeld:**
    - `/kaart/{cbs_uuid}?indicator_uuid={inwoners_uuid}` → 154 buurten (16% van 965)
    - `/kaart/{cbs_uuid}?indicator_uuid={inwoners_uuid}&show_all=true` → Alle 965 buurten
    - `/kaart/{cbs_uuid}?gemeente_code=1900` → Alleen Súdwest-Fryslân gebieden
    
    Args:
        gebiedstype_id: UUID van gebiedstype (CBS Buurten, Welstandsgebieden, etc.)
        indicator_uuid: UUID van indicator om te visualiseren (VERPLICHT)
        show_all: Toon ook gebieden zonder data (default: False)
        gemeente_code: Filter op gemeente CBS code (optioneel)
    
    Returns:
        GeoJSON FeatureCollection met:
        - geometry: MultiPolygon in WGS84 (EPSG:4326) voor deck.gl
        - properties: gebied info + indicator waarde voor 3D extrusie en kleur
        - metadata: statistieken over aantal features
    
    **Frontend gebruik:**
    ```javascript
    const response = await fetch(`/api/gebiedsmonitor/kaart/${typeId}?indicator_uuid=${indicatorId}&gemeente_code=1900`);
    const geojson = await response.json();
    
    // GeoJsonLayer configuratie
    new GeoJsonLayer({
      data: geojson,
      getFillColor: d => getColor(d.properties.indicator_waarde),
      getElevation: d => d.properties.indicator_waarde * heightScale
    })
    ```
    """
    try:
        geojson = service.get_kaart_data(
            gebiedstype_id=gebiedstype_id,
            indicator_uuid=indicator_uuid,
            show_all=show_all,
            gemeente_code=gemeente_code,
            jaar=jaar
        )
        return geojson
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating kaart data: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint voor Gebiedsmonitor API.
    """
    return {
        "status": "healthy",
        "service": "Gebiedsmonitor API",
        "version": "1.0.0"
    }
