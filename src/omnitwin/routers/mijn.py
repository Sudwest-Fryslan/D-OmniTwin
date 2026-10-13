"""
Eigen voorkeuren van de ingelogde gebruiker (#258): favorieten en laatste kaartpositie.

GET    /api/mijn/favorieten          eigen favorieten (gebiedenselecties met een naam)
POST   /api/mijn/favorieten          bewaren; zelfde naam = vervangen (201 nieuw, 200 vervangen)
DELETE /api/mijn/favorieten/{id}     eigen favoriet verwijderen (404 als hij niet van jou is)
GET    /api/mijn/instellingen        laatste kaartpositie
PUT    /api/mijn/instellingen        laatste kaartpositie bewaren

Alleen ingelogd (sessie van de viewer, via Keycloak of lokaal; ook een bearer-token): anders 401.
Interne API van de viewer (api-landschap: viewer), dus met de sessie van de BFF (ADR 0008/0009) en
niet met `vereis_rol`. Sleutel = `sub` (of `lokaal:<id>`), zie omnitwin.services.gebruikersvoorkeuren.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.services.gebruikersvoorkeuren import Voorkeuren, eigenaar_van

router = APIRouter(prefix="/api/mijn", tags=["Mijn voorkeuren"])


def voorkeuren(request: Request, db: Session = Depends(get_db)) -> Voorkeuren:
    from omnitwin.routers.auth import huidige_gebruiker

    try:
        gebruiker = huidige_gebruiker(request, db)
    except HTTPException:
        gebruiker = None
    eigenaar = eigenaar_van(gebruiker)
    if not eigenaar:
        raise HTTPException(status_code=401, detail="Log in om favorieten en instellingen te bewaren.")
    return Voorkeuren(db, eigenaar)


class Kaartpositie(BaseModel):
    longitude: float
    latitude: float
    zoom: float
    pitch: float | None = None
    bearing: float | None = None


class Instellingen(BaseModel):
    kaartpositie: Kaartpositie | None = None


class NieuweFavoriet(BaseModel):
    naam: str = Field(..., max_length=200)
    gebiedIds: list[str] = Field(..., max_length=5000)
    gebiedstypeId: UUID | None = None


def _fout(e: GebruikersFout):
    raise HTTPException(status_code=400, detail=str(e))


@router.get("/instellingen")
def lees_instellingen(v: Voorkeuren = Depends(voorkeuren)):
    return v.instellingen()


@router.put("/instellingen")
def zet_instellingen(body: Instellingen, v: Voorkeuren = Depends(voorkeuren)):
    try:
        return v.zet_instellingen(body.kaartpositie.model_dump(exclude_none=True) if body.kaartpositie else None)
    except GebruikersFout as e:
        _fout(e)


@router.get("/favorieten")
def lees_favorieten(v: Voorkeuren = Depends(voorkeuren)):
    return {"favorieten": v.favorieten()}


@router.post("/favorieten", status_code=201)
def bewaar_favoriet(body: NieuweFavoriet, response: Response, v: Voorkeuren = Depends(voorkeuren)):
    try:
        favoriet, nieuw = v.bewaar_favoriet(
            body.naam, body.gebiedIds, str(body.gebiedstypeId) if body.gebiedstypeId else None
        )
    except GebruikersFout as e:
        _fout(e)
    if not nieuw:
        response.status_code = 200
    return favoriet


@router.delete("/favorieten/{favoriet_id}", status_code=204)
def verwijder_favoriet(favoriet_id: UUID, v: Voorkeuren = Depends(voorkeuren)):
    if not v.verwijder_favoriet(str(favoriet_id)):
        raise HTTPException(status_code=404, detail="Favoriet niet gevonden.")
    return Response(status_code=204)
