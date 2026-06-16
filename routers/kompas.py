"""
Kompas API Router
Endpoints voor multi-kompas configuratie systeem
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database import get_db
from schemas.kompas import (
    KompasConfiguratiesResponse,
    HierarchieResponse,
    GebiedKompasResponse,
    IndicatorPathResponse
)
from services.kompas_service import KompasService

router = APIRouter(prefix="/api/kompas", tags=["Kompas"])


@router.get("/configuraties", response_model=KompasConfiguratiesResponse)
async def get_configuraties(db: Session = Depends(get_db)):
    """
    Haal alle actieve kompas configuraties op met statistieken
    
    **Returns:**
    - `configuraties`: Lijst van configuraties met counts (themas, onderdelen, indicatoren)
    - `standaard_config_id`: ID van standaard configuratie
    
    **Gebruik:**
    ```javascript
    const response = await fetch('/api/kompas/configuraties');
    const { configuraties, standaard_config_id } = await response.json();
    ```
    """
    service = KompasService(db)
    
    configs = service.get_configuraties()
    standaard_id = service.get_standaard_config_id()
    
    if not configs:
        raise HTTPException(
            status_code=404, 
            detail="Geen actieve kompas configuraties gevonden"
        )
    
    return {
        "configuraties": configs,
        "standaard_config_id": standaard_id
    }


@router.get("/{config_id}/hierarchie", response_model=HierarchieResponse)
async def get_hierarchie(
    config_id: int,
    db: Session = Depends(get_db)
):
    """
    Haal hiërarchie op voor specifiek kompas (zonder gebied data)
    
    **Args:**
    - `config_id`: ID van kompas configuratie
    
    **Returns:**
    - Geneste JSON tree voor D3.js partition layout
    - 4 niveaus: Titel → Thema → Onderdeel → Indicator
    
    **Gebruik:**
    Render lege sunburst (zonder waarden) om structuur te tonen:
    ```javascript
    const response = await fetch('/api/kompas/1/hierarchie');
    const data = await response.json();
    renderSunburst(data.hierarchie);
    ```
    """
    service = KompasService(db)
    result = service.get_hierarchie(config_id)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Kompas configuratie {config_id} niet gevonden of niet actief"
        )
    
    return result


@router.get("/{config_id}/gebied/{gebied_id}", response_model=GebiedKompasResponse)
async def get_gebied_kompas(
    config_id: int,
    gebied_id: str,
    db: Session = Depends(get_db)
):
    """
    Haal kompas data voor specifiek gebied op (met waarden en kleuren)
    
    **Args:**
    - `config_id`: ID van kompas configuratie
    - `gebied_id`: UUID van gebied
    
    **Returns:**
    - Hiërarchie tree met indicator waarden ingevuld
    - Kleuren berekend via scoring regels
    - Coverage percentage (hoeveel indicatoren hebben data)
    
    **Gebruik:**
    Na gebied click op kaart:
    ```javascript
    const response = await fetch(`/api/kompas/1/gebied/${gebiedId}`);
    const data = await response.json();
    renderSunburst(data.hierarchie);  // Met kleuren!
    ```
    """
    service = KompasService(db)
    result = service.get_gebied_kompas(config_id, gebied_id)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Geen data gevonden voor gebied {gebied_id} in configuratie {config_id}"
        )
    
    return result


@router.get("/{config_id}/indicator/{indicator_uuid}", response_model=IndicatorPathResponse)
async def get_indicator_path(
    config_id: int,
    indicator_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Haal hiërarchie pad op voor specifieke indicator (breadcrumb trail)
    
    **Args:**
    - `config_id`: ID van kompas configuratie
    - `indicator_uuid`: UUID van indicator
    
    **Returns:**
    - `path`: Array van niveau namen ["Titel", "Thema", "Onderdeel", "Indicator"]
    - `full_path_string`: String representatie "Titel > Thema > Onderdeel > Indicator"
    - `indicator_details`: Volledige indicator metadata
    
    **Gebruik:**
    Voor breadcrumb navigatie:
    ```javascript
    const response = await fetch(`/api/kompas/1/indicator/${uuid}`);
    const { path, full_path_string } = await response.json();
    updateBreadcrumb(path);
    ```
    """
    service = KompasService(db)
    result = service.get_indicator_path(config_id, indicator_uuid)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Indicator {indicator_uuid} niet gevonden in configuratie {config_id}"
        )
    
    return result


@router.get("/{config_id}/history/{gebied_id}/{indicator_uuid}")
async def get_indicator_history(
    config_id: int,
    gebied_id: str, 
    indicator_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Haal tijdreeks data op voor indicator/gebied combinatie (Line Chart)
    """
    service = KompasService(db)
    result = service.get_indicator_history(config_id, gebied_id, indicator_uuid)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail="Geen historie gevonden"
        )
    
    return result



@router.get("/indicator/{indicator_uuid}/top-buurten")
async def get_top_buurten(
    indicator_uuid: str,
    gebied_id: Optional[str] = Query(None),
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Haal Top N positief + Top N negatief afwijkende buurten op voor een indicator.
    
    **Args:**
    - `indicator_uuid`: UUID van indicator
    - `gebied_id`: Optioneel UUID van het gebied om de buurten te filteren op de gemeente van dit gebied
    - `limit`: Aantal buurten per richting (default 3, max 10)
    
    **Returns:**
    - `indicator_naam`, `eenheid`, `referentie_gemiddelde`
    - `top_positief`: Buurten met hoogste Z-score
    - `top_negatief`: Buurten met laagste Z-score
    """
    service = KompasService(db)
    result = service.get_top_afwijkende_buurten(indicator_uuid, limit, gebied_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Geen data gevonden voor indicator {indicator_uuid}"
        )
    
    return result


# ========================================================================
# FUTURE ENDPOINTS (voor admin panel - later)
# ========================================================================

# @router.post("/configuraties")
# async def create_configuratie(...):
#     """Maak nieuwe kompas configuratie aan (admin only)"""
#     pass

# @router.put("/configuraties/{config_id}")
# async def update_configuratie(...):
#     """Update bestaande configuratie (admin only)"""
#     pass

# @router.delete("/configuraties/{config_id}")
# async def delete_configuratie(...):
#     """Verwijder configuratie (admin only)"""
#     pass
