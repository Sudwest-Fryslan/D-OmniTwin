"""
Eigen buurt via postcode/adres of locatie (#336).

POST /api/locatie/buurt  {"adres": "8601 CR"}  of  {"lat": 53.03, "lon": 5.66}
→ {"gebied_id": "BU19000101", "naam": "Sneek binnen de grachten"}

De viewer gebruikt dit als de assistent vraagt welke buurt 'mijn buurt' is. Het adres of de locatie
gaat in de body (niet in de URL of de logregel), wordt niet bewaard en alleen doorgegeven aan de
PDOK Locatieserver (services/locatie.py). 404 als de buurt niet bij deze installatie hoort.
"""

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.grenzen import beperk_locatie
from omnitwin.services import locatie
from omnitwin.services.chat_datavraag import laad_gebieden, normaliseer, plaats_van, voorkeur_gebiedstype

router = APIRouter(prefix="/api/locatie", tags=["Locatie"])

_WATER_NAMEN = {"buitenwater", "groot binnenwater"}


class BuurtVraag(BaseModel):
    adres: str | None = Field(
        None,
        max_length=200,
        description="Postcode, adres of buurtnaam, bijv. '8601 CR', 'Marktstraat 15 Sneek' of 'It Stiselplak'",
    )
    lat: float | None = Field(None, description="Breedtegraad (WGS84), alleen na toestemming van de gebruiker")
    lon: float | None = Field(None, description="Lengtegraad (WGS84)")

    @model_validator(mode="after")
    def adres_of_locatie(self):
        if self.adres is None and (self.lat is None or self.lon is None):
            raise ValueError("geef een adres of een locatie (lat en lon)")
        return self


class BuurtAntwoord(BaseModel):
    gebied_id: str
    naam: str
    gemeente_code: str | None = None
    gebiedstype_id: str | None = None


def zoek_buurt_op_naam(zoekterm: str, gebieden: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """Zoek deterministisch een buurt op naam (exact, buurtdeel, woonplaats/prefix of substring)."""
    q = normaliseer(zoekterm)
    if len(q) < 3:
        return None

    voorkeur_type = voorkeur_gebiedstype(gebieden)
    kandidaten = [
        g
        for g in gebieden
        if (g.get("gebiedstype_id") == voorkeur_type or str(g.get("id", "")).startswith("BU"))
        and normaliseer(g.get("naam") or "") not in _WATER_NAMEN
    ]

    treffers: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
    for g in kandidaten:
        naam = g.get("naam") or ""
        norm = normaliseer(naam)
        if not norm:
            continue
        if norm == q:
            rang = (0, 0, len(norm), str(g.get("id") or ""))
        else:
            is_buitengebied = 1 if norm.startswith(("verspreide huizen ", "buitengebied ")) else 0
            plaats = normaliseer(plaats_van(naam))
            if norm.endswith(f" {q}"):
                tier = 1
            elif plaats == q or norm.startswith(f"{q} "):
                tier = 2
            elif len(q) >= 4 and q in norm:
                tier = 3
            else:
                continue
            rang = (is_buitengebied, tier, len(norm), str(g.get("id") or ""))
        treffers.append((rang, g))

    if not treffers:
        return None
    treffers.sort(key=lambda item: item[0])
    return treffers[0][1]


def _naar_antwoord(gebied: dict[str, Any]) -> BuurtAntwoord:
    return BuurtAntwoord(
        gebied_id=gebied["id"],
        naam=gebied["naam"],
        gemeente_code=gebied.get("gemeente_code"),
        gebiedstype_id=gebied.get("gebiedstype_id"),
    )


@router.post("/buurt", response_model=BuurtAntwoord, dependencies=[Depends(beperk_locatie)])
def buurt(vraag: BuurtVraag, db: Session = Depends(get_db)):
    """De buurt bij een postcode/adres, buurtnaam of locatie, als die bij deze installatie hoort."""
    if vraag.adres is None and not locatie.in_nederland(vraag.lat, vraag.lon):
        raise HTTPException(422, "Deze locatie ligt niet in Nederland.")

    gebieden = laad_gebieden(db)
    per_id = {g["id"]: g for g in gebieden}

    if vraag.adres is not None:
        if not locatie.geldig_adres(vraag.adres):
            op_naam = zoek_buurt_op_naam(vraag.adres, gebieden)
            if op_naam:
                return _naar_antwoord(op_naam)
            raise HTTPException(
                422,
                "Vul een postcode (bijv. 8601 CR), een straat met huisnummer of een bestaande buurtnaam in.",
            )
        try:
            gevonden = locatie.buurt_bij_adres(vraag.adres)
        except locatie.LocatieFout:
            raise HTTPException(503, "De PDOK Locatieserver is nu niet bereikbaar. Selecteer je buurt op de kaart.")
        if not gevonden:
            op_naam = zoek_buurt_op_naam(vraag.adres, gebieden)
            if op_naam:
                return _naar_antwoord(op_naam)
            raise HTTPException(
                404,
                "Geen buurt gevonden. Controleer de postcode of het adres, of selecteer je buurt op de kaart.",
            )
    else:
        try:
            gevonden = locatie.buurt_bij_punt(vraag.lat, vraag.lon)
        except locatie.LocatieFout:
            raise HTTPException(503, "De PDOK Locatieserver is nu niet bereikbaar. Selecteer je buurt op de kaart.")
        if not gevonden:
            raise HTTPException(
                404,
                "Geen buurt gevonden. Controleer de postcode of het adres, of selecteer je buurt op de kaart.",
            )

    gebied = per_id.get(gevonden["buurtcode"])
    if not gebied:
        raise HTTPException(
            404,
            f"{gevonden['buurtnaam']} hoort niet bij de gebieden van deze installatie. Selecteer een buurt op de kaart.",
        )
    return _naar_antwoord(gebied)
