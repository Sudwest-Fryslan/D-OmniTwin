"""
Kompas API Router
Endpoints voor multi-kompas configuratie systeem
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from omnitwin import toegang
from omnitwin.database import get_db
from omnitwin.schemas.kompas import (
    KompasConfiguratiesResponse,
    HierarchieResponse,
    GebiedKompasResponse,
    IndicatorPathResponse
)
from omnitwin.services.kompas_service import KompasService


# ─── Pydantic Models (Sprint 18 Track C) ────────────────────────────────────

class BenchmarkGroep(BaseModel):
    naam: str = Field(..., description="Naam van de woonplaats/kern")
    buurt_ids: List[str] = Field(..., min_length=1, description="CBS buurt-IDs in deze groep")

class BenchmarkRequest(BaseModel):
    groepen: List[BenchmarkGroep] = Field(..., min_length=1, max_length=8)
    gemeente_code: Optional[str] = Field(None, description="Gemeente code voor referentie")


router = APIRouter(prefix="/api/kompas", tags=["Kompas"])


@router.get("/configuraties", response_model=KompasConfiguratiesResponse)
def get_configuraties(db: Session = Depends(get_db)):
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


# Vóór /{config_id}/hierarchie: anders matcht "standaard" daar en geeft het een 422.
@router.get("/standaard/hierarchie", response_model=HierarchieResponse)
def get_standaard_hierarchie(db: Session = Depends(get_db)):
    """
    Hiërarchie van de standaard-kompasconfiguratie van deze instantie
    (`kompas_configuraties.is_standaard`), zonder een vaste ID aan te nemen (#231).
    Zelfde antwoord als `/api/kompas/{config_id}/hierarchie` met de standaard-ID.
    """
    service = KompasService(db)
    config_id = service.get_standaard_config_id()
    result = service.get_hierarchie(config_id)
    if not result:
        raise HTTPException(status_code=404, detail="Geen actieve standaard-kompasconfiguratie")
    return result


@router.get("/{config_id}/hierarchie", response_model=HierarchieResponse)
def get_hierarchie(
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
def get_gebied_kompas(
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


@router.get("/{config_id}/selectie")
def get_selectie_kompas(
    config_id: int,
    gebied_id: List[str] = Query(..., min_length=1, max_length=500,
                                 description="Gebied-ID's van de selectie (herhaal de parameter)"),
    db: Session = Depends(get_db)
):
    """
    Percentielklassen over een selectie van gebieden (#255).

    Alleen bij een kompasprofiel met classificatie `percentiel_8`: elke node (indicator,
    onderdeel, thema, kwadrant) krijgt `klasse` (1-8, 8 = gunstigst) en `klasse_kleur`,
    volgens dezelfde aggregatieregel als voor één gebied. Bij `label_ae` (#256) labels A-E
    (`label`, `klasse` = labelscore 5 = A .. 1 = E), met dezelfde regel. Bij `zscore` zonder klassen.
    """
    service = KompasService(db)
    result = service.get_selectie_kompas(config_id, gebied_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Kompas configuratie {config_id} niet gevonden of niet actief")
    return result


@router.get("/{config_id}/indicator/{indicator_uuid}", response_model=IndicatorPathResponse)
def get_indicator_path(
    config_id: int,
    indicator_uuid: UUID,  # ongeldige UUID: 422 (#203)
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
    toegang.vereis_indicator(db, indicator_uuid)  # interne indicator zonder rol: 401/403 (#254)
    service = KompasService(db)
    result = service.get_indicator_path(config_id, str(indicator_uuid))
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Indicator {indicator_uuid} niet gevonden in configuratie {config_id}"
        )
    
    return result


@router.get("/{config_id}/history/{gebied_id}/{indicator_uuid}")
def get_indicator_history(
    config_id: int,
    gebied_id: str, 
    indicator_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Haal tijdreeks data op voor indicator/gebied combinatie (Line Chart)
    """
    toegang.vereis_indicator(db, indicator_uuid)  # #254
    service = KompasService(db)
    result = service.get_indicator_history(config_id, gebied_id, str(indicator_uuid))
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail="Geen historie gevonden"
        )
    
    return result



@router.get("/indicator/{indicator_uuid}/top-buurten")
def get_top_buurten(
    indicator_uuid: UUID,
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
    toegang.vereis_indicator(db, indicator_uuid)  # #254
    service = KompasService(db)
    result = service.get_top_afwijkende_buurten(str(indicator_uuid), limit, gebied_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Geen data gevonden voor indicator {indicator_uuid}"
        )
    
    return result


# ─── Sprint 18 Track C: Benchmark vergelijking ──────────────────────────────

@router.post("/{config_id}/benchmark")
def get_benchmark(
    config_id: int,
    payload: BenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Benchmark vergelijking: per groep (woonplaats/kern) gemiddelde waarden
    voor alle indicatoren, plus optioneel het gemeentegemiddelde als referentie.

    **Body:**
    ```json
    {
        "groepen": [
            {"naam": "Makkum", "buurt_ids": ["BU19000100", "BU19000101"]},
            {"naam": "Workum", "buurt_ids": ["BU19000200"]}
        ],
        "gemeente_code": "1900"
    }
    ```
    """
    service = KompasService(db)
    groepen_dicts = [g.model_dump() for g in payload.groepen]
    result = service.get_benchmark(config_id, groepen_dicts, payload.gemeente_code)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Geen benchmark data gevonden"
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
