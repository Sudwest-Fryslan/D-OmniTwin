"""
GET /api/organisatie: de eigen organisatie van deze instantie (#231, ADR 0007).

Publiek en alleen-lezen: naam, gemeentecode(s) van het eigen gebied,
standaard-benchmarkgebied, contactpunt en logo's. Frontend en beheer lezen hier
"de eigen gemeente" in plaats van een vaste code. Geen geheimen.

Gaat later op in de catalogus-API (``/api/catalogus/v1``, zie
docs/2-architectuur/api-landschap.md) als beschrijving van de aanbieder.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.services.organisatie import lees_organisatie

router = APIRouter(prefix="/api/organisatie", tags=["Organisatie"])


class Logo(BaseModel):
    pad: str
    naam: Optional[str] = None
    rol: str = "partner"  # "eigen" of "partner"


class Organisatie(BaseModel):
    code: str
    naam: str
    korte_naam: Optional[str] = None
    oin: Optional[str] = None
    gemeente_codes: List[str]
    standaard_gemeente_code: Optional[str] = None
    benchmark_provincie: Optional[str] = None
    contact_email: Optional[str] = None
    thema: str = "d-omnitwin"  # huisstijl (NLDS-thema), static/css/themes/<thema>.css
    logos: List[Logo]


@router.get("", response_model=Organisatie)
def get_organisatie(db: Session = Depends(get_db)):
    """De organisatie van deze instantie (één instantie = één organisatie)."""
    org = lees_organisatie(db)
    if org is None:
        raise HTTPException(status_code=404, detail="Organisatie van deze instantie is niet ingericht")
    return org
