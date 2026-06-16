"""
Gemeenten API Router
Endpoints voor gemeente selectie en filtering
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from src.database import get_db

router = APIRouter(prefix="/api", tags=["Gemeenten"])


# ========================================================================
# PYDANTIC SCHEMAS
# ========================================================================

class GemeenteBase(BaseModel):
    """Gemeente basis response"""
    id: Optional[str] = None
    code: str
    naam: str
    provincie: str
    is_eiland: bool = False


class GemeenteListResponse(BaseModel):
    """Lijst van gemeenten response"""
    gemeenten: List[GemeenteBase]
    totaal: int
    provincie_filter: Optional[str] = None


class GebiedListItem(BaseModel):
    """Gebied binnen gemeente"""
    id: str
    naam: str
    type: str


class GebiedenResponse(BaseModel):
    """Gebieden binnen gemeente response"""
    gemeente_code: str
    gemeente_naam: str
    gebieden: List[GebiedListItem]
    totaal: int


class GebiedenZoekResponse(BaseModel):
    """Zoekresultaten voor gebieden (typeahead)"""
    gebieden: List[GebiedListItem]
    totaal: int


# ========================================================================
# ENDPOINTS
# ========================================================================

@router.get("/gebieden/zoek", response_model=GebiedenZoekResponse)
async def zoek_gebieden(
    q: str = Query(..., min_length=2, description="Zoekterm (naam of code)"),
    limit: int = Query(15, le=50),
    db: Session = Depends(get_db)
):
    """
    Full-text zoeken op gebiedsnaam of ID — voor typeahead, geen gemeente vereist.

    **Args:**
    - `q`: Zoekterm (minimaal 2 tekens)
    - `limit`: Max resultaten (default 15, max 50)

    **Returns:**
    - `gebieden`: Lijst van matchende gebieden
    - `totaal`: Aantal resultaten
    """
    query = text("""
        SELECT g.id, g.naam, gt.code as type
        FROM gebieden g
        JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
        WHERE g.actief = true
          AND gt.code IN ('CBS_BUURT', 'CBS_WIJK')
          AND (g.naam ILIKE :q OR g.id ILIKE :q)
        ORDER BY g.naam
        LIMIT :limit
    """)
    result = db.execute(query, {"q": f"%{q}%", "limit": limit})
    gebieden = [GebiedListItem(id=r.id, naam=r.naam, type=r.type) for r in result]
    return GebiedenZoekResponse(gebieden=gebieden, totaal=len(gebieden))


@router.get("/gemeenten", response_model=GemeenteListResponse)
async def get_gemeenten(
    provincie: Optional[str] = Query(None, description="Filter op provincie (bijv. 'Fryslân')"),
    db: Session = Depends(get_db)
):
    """
    Haal alle beschikbare gemeenten op
    
    **Args:**
    - `provincie`: Optionele filter op provincie naam
    
    **Returns:**
    - `gemeenten`: Lijst van gemeente objecten met code, naam, provincie
    - `totaal`: Aantal gemeenten
    
    **Gebruik:**
    ```javascript
    const response = await fetch('/api/gemeenten');
    const { gemeenten } = await response.json();
    // Vul dropdown met gemeenten
    ```
    """
    if provincie:
        query = text("""
            SELECT id, code, naam, provincie, is_eiland 
            FROM gemeenten 
            WHERE provincie = :provincie
            ORDER BY naam
        """)
        result = db.execute(query, {"provincie": provincie})
    else:
        query = text("""
            SELECT id, code, naam, provincie, is_eiland 
            FROM gemeenten 
            ORDER BY provincie, naam
        """)
        result = db.execute(query)
    
    gemeenten = [
        GemeenteBase(
            id=str(row.id) if getattr(row, 'id', None) else None,
            code=row.code,
            naam=row.naam,
            provincie=row.provincie,
            is_eiland=row.is_eiland
        )
        for row in result
    ]
    
    return GemeenteListResponse(
        gemeenten=gemeenten,
        totaal=len(gemeenten),
        provincie_filter=provincie
    )


@router.get("/gemeenten/{gemeente_code}", response_model=GemeenteBase)
async def get_gemeente(
    gemeente_code: str,
    db: Session = Depends(get_db)
):
    """
    Haal details op voor specifieke gemeente
    
    **Args:**
    - `gemeente_code`: 4-cijferige CBS gemeente code
    
    **Returns:**
    - Gemeente object met code, naam, provincie
    """
    query = text("""
        SELECT id, code, naam, provincie, is_eiland 
        FROM gemeenten 
        WHERE code = :code
    """)
    result = db.execute(query, {"code": gemeente_code}).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Gemeente met code {gemeente_code} niet gevonden"
        )
    
    return GemeenteBase(
        id=str(result.id) if getattr(result, 'id', None) else None,
        code=result.code,
        naam=result.naam,
        provincie=result.provincie,
        is_eiland=result.is_eiland
    )


@router.get("/gebieden", response_model=GebiedenResponse)
async def get_gebieden(
    gemeente_code: str = Query(..., description="CBS gemeente code (bijv. '1900')"),
    type: Optional[str] = Query(None, description="Filter op gebiedstype (bijv. 'CBS_BUURT')"),
    db: Session = Depends(get_db)
):
    """
    Haal gebieden op binnen een gemeente
    
    **Args:**
    - `gemeente_code`: CBS gemeente code (verplicht)
    - `type`: Optionele filter op gebiedstype
    
    **Returns:**
    - List van gebieden met id, naam, type
    
    **Gebruik:**
    Na gemeente selectie, update kaart:
    ```javascript
    const response = await fetch(`/api/gebieden?gemeente_code=${code}`);
    const { gebieden } = await response.json();
    // Laad gebieden op kaart
    ```
    """
    # Haal gemeente info
    gemeente_query = text("SELECT naam FROM gemeenten WHERE code = :code")
    gemeente = db.execute(gemeente_query, {"code": gemeente_code}).fetchone()
    
    if not gemeente:
        raise HTTPException(
            status_code=404,
            detail=f"Gemeente met code {gemeente_code} niet gevonden"
        )
    
    # Build gebieden query
    if type:
        query = text("""
            SELECT g.id, g.naam, gt.code as type
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.gemeente_code = :gemeente_code
              AND gt.code = :type
              AND g.actief = true
            ORDER BY g.naam
        """)
        result = db.execute(query, {"gemeente_code": gemeente_code, "type": type})
    else:
        query = text("""
            SELECT g.id, g.naam, gt.code as type
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.gemeente_code = :gemeente_code
              AND g.actief = true
            ORDER BY gt.code, g.naam
        """)
        result = db.execute(query, {"gemeente_code": gemeente_code})
    
    gebieden = [
        GebiedListItem(id=row.id, naam=row.naam, type=row.type)
        for row in result
    ]
    
    return GebiedenResponse(
        gemeente_code=gemeente_code,
        gemeente_naam=gemeente.naam,
        gebieden=gebieden,
        totaal=len(gebieden)
    )
