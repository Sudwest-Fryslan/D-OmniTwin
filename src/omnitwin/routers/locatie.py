"""
Eigen buurt via postcode/adres of locatie (#336).

POST /api/locatie/buurt  {"adres": "8601 CR"}  of  {"lat": 53.03, "lon": 5.66}
→ {"gebied_id": "BU19000101", "naam": "Sneek binnen de grachten"}

De viewer gebruikt dit als de assistent vraagt welke buurt 'mijn buurt' is. Het adres of de locatie
gaat in de body (niet in de URL of de logregel), wordt niet bewaard en alleen doorgegeven aan de
PDOK Locatieserver (services/locatie.py). 404 als de buurt niet bij deze installatie hoort.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.grenzen import beperk_locatie
from omnitwin.services import locatie
from omnitwin.services.chat_datavraag import laad_gebieden

router = APIRouter(prefix="/api/locatie", tags=["Locatie"])


class BuurtVraag(BaseModel):
    adres: Optional[str] = Field(None, max_length=200, description="Postcode of adres, bijv. '8601 CR' of 'Marktstraat 15 Sneek'")
    lat: Optional[float] = Field(None, description="Breedtegraad (WGS84), alleen na toestemming van de gebruiker")
    lon: Optional[float] = Field(None, description="Lengtegraad (WGS84)")

    @model_validator(mode="after")
    def adres_of_locatie(self):
        if self.adres is None and (self.lat is None or self.lon is None):
            raise ValueError("geef een adres of een locatie (lat en lon)")
        return self


class BuurtAntwoord(BaseModel):
    gebied_id: str
    naam: str


@router.post("/buurt", response_model=BuurtAntwoord, dependencies=[Depends(beperk_locatie)])
def buurt(vraag: BuurtVraag, db: Session = Depends(get_db)):
    """De buurt bij een postcode/adres of locatie, als die bij deze installatie hoort."""
    if vraag.adres is not None:
        if not locatie.geldig_adres(vraag.adres):
            raise HTTPException(422, "Vul een postcode (bijv. 8601 CR) of een straat met huisnummer in.")
    elif not locatie.in_nederland(vraag.lat, vraag.lon):
        raise HTTPException(422, "Deze locatie ligt niet in Nederland.")
    try:
        gevonden = (locatie.buurt_bij_adres(vraag.adres) if vraag.adres is not None
                    else locatie.buurt_bij_punt(vraag.lat, vraag.lon))
    except locatie.LocatieFout:
        raise HTTPException(503, "De PDOK Locatieserver is nu niet bereikbaar. Selecteer je buurt op de kaart.")
    if not gevonden:
        raise HTTPException(404, "Geen buurt gevonden. Controleer de postcode of het adres, of selecteer je buurt op de kaart.")
    per_id = {g["id"]: g for g in laad_gebieden(db)}
    gebied = per_id.get(gevonden["buurtcode"])
    if not gebied:
        raise HTTPException(404, f"{gevonden['buurtnaam']} hoort niet bij de gebieden van deze installatie. "
                                 "Selecteer een buurt op de kaart.")
    return BuurtAntwoord(gebied_id=gebied["id"], naam=gebied["naam"])
