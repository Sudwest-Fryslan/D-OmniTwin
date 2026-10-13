"""
API-endpoints voor de terugmeldvoorziening (#311).

- POST /api/meldingen (Publiek, met in-memory rate-limit en honeypot):
  Inzenden van feedback door gebruikers op data, AI, techniek of suggesties.
- GET/PATCH /api/admin/meldingen (Beveiligd met vereis_admin):
  Beheeroverzicht, filtering en statusafhandeling door functioneel beheer.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.grenzen import beperk_meldingen
from omnitwin.routers.auth import vereis_admin
from omnitwin.services import meldingen as meldingen_service

router = APIRouter(prefix="/api/meldingen", tags=["Meldingen"])
admin_router = APIRouter(prefix="/api/admin/meldingen", tags=["Meldingen Beheer"], dependencies=[Depends(vereis_admin)])

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class MeldingInvoer(BaseModel):
    type: Literal["data", "ai", "systeem", "overig"]
    onderwerp: str = Field(..., min_length=1, max_length=120, description="Kort onderwerp van de melding")
    toelichting: str = Field(..., min_length=1, max_length=4000, description="Uitgebreide toelichting")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contextuele metadata (buurt, indicator, etc.)")
    melder_email: Optional[str] = Field(
        default=None, pattern=EMAIL_REGEX, description="Optioneel e-mailadres voor terugkoppeling"
    )
    website: Optional[str] = Field(default=None, description="Honeypot-veld voor spambots; moet leeg blijven")


class MeldingWijziging(BaseModel):
    status: Optional[Literal["nieuw", "doorgestuurd_naar_bron", "in_behandeling", "afgehandeld", "afgewezen"]] = None
    notitie_beheer: Optional[str] = Field(default=None, max_length=4000)


def _wie(gebruiker: dict) -> str:
    return str(gebruiker.get("username") or gebruiker.get("user_id") or "onbekend")[:200]


# ── Publiek meldpunt ──────────────────────────────────────────────────────────


@router.post("", status_code=201, dependencies=[Depends(beperk_meldingen)])
def meld(invoer: MeldingInvoer, db: Session = Depends(get_db)):
    """
    Dient een nieuwe melding in.
    Beveiligd tegen bots met een verborgen honeypot-veld en in-memory IP rate limiting.
    """
    # Honeypot: bots vullen verborgen velden vaak in. Doe alsof het gelukt is zonder op te slaan.
    if invoer.website and invoer.website.strip():
        return {"id": uuid.uuid4().hex, "status": "ontvangen"}

    try:
        melding = meldingen_service.maak_melding(
            db=db,
            type_=invoer.type,
            onderwerp=invoer.onderwerp,
            toelichting=invoer.toelichting,
            context_data=invoer.context,
            melder_email=str(invoer.melder_email) if invoer.melder_email else None,
        )
        return {"id": melding["id"], "status": "ontvangen"}
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Beheerder endpoints ───────────────────────────────────────────────────────


@admin_router.get("")
def overzicht(
    status: Optional[str] = Query(None, description="Filter op status"),
    type: Optional[str] = Query(None, description="Filter op type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Haalt meldingen op met status- en typefilters inclusief paginering en tellingen."""
    try:
        return meldingen_service.zoek_meldingen(
            db=db,
            status=status,
            type_=type,
            limit=limit,
            offset=offset,
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.get("/{id}")
def detail(id: uuid.UUID, db: Session = Depends(get_db)):
    """Haalt één melding op inclusief volledige context en beheergeschiedenis."""
    melding = meldingen_service.haal_melding(db=db, melding_id=id)
    if not melding:
        raise HTTPException(status_code=404, detail="Melding niet gevonden.")
    return melding


@admin_router.patch("/{id}")
def werk_bij(
    id: uuid.UUID,
    wijziging: MeldingWijziging,
    gebruiker: dict = Depends(vereis_admin),
    db: Session = Depends(get_db),
):
    """
    Past de status of beheerdernotitie van een melding aan.
    Wist conform AVG automatisch het e-mailadres wanneer de status 'afgehandeld' of 'afgewezen' wordt.
    """
    try:
        return meldingen_service.werk_melding_bij(
            db=db,
            melding_id=id,
            status=wijziging.status,
            notitie_beheer=wijziging.notitie_beheer,
            beheerder=_wie(gebruiker),
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=404, detail=str(e))
