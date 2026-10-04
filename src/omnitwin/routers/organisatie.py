"""
De eigen organisatie van deze instantie (#231, #253, ADR 0007).

- ``GET /api/organisatie``: publiek en alleen-lezen: naam, gemeentecode(s) van het eigen gebied,
  standaard-benchmarkgebied, contactpunt, thema en logo's. Frontend en beheer lezen hier "de eigen
  gemeente" in plaats van een vaste code. Geen geheimen.
- Instellen (alleen beheerder, ``vereis_admin``: sessie, bearer met rol ``beheerder`` of
  ``X-Admin-Key``): ``PUT /api/organisatie``, ``GET /api/organisatie/themas``,
  ``GET /api/organisatie/logos``, en export/import als JSON (``GET /export``, ``POST /import``),
  zodat een andere instantie de instelling kan overnemen (mesh, ADR 0007). Elke wijziging komt in de
  auditlog (categorie ADMIN: wie en wat).

Gaat later op in de catalogus-API (``/api/catalogus/v1``, zie
docs/2-architectuur/api-landschap.md) als beschrijving van de aanbieder.
"""
import datetime as dt
import re
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.routers.auth import vereis_admin
from omnitwin.services import organisatie as org_service
from omnitwin.services.logging_service import AppLogger
from omnitwin.services.organisatie import beeldmerk_svg, lees_organisatie
from omnitwin.version import __version__

router = APIRouter(prefix="/api/organisatie", tags=["Organisatie"])

EXPORT_FORMAAT = "d-omnitwin/organisatie"
EXPORT_VERSIE = 1


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


# ── Invoer (PUT en import) ──────────────────────────────────────────────────

_CODE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_GEMEENTECODE = re.compile(r"^\d{4}$")
_OIN = re.compile(r"^\d{20}$")
# Praktische controle (geen volledige RFC 5322): één @, geen spaties, een punt in het domein
_EMAIL = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[A-Za-z]{2,}$")
_STUURTEKENS = re.compile(r"[\x00-\x1f\x7f]")


def _tekst(waarde: Optional[str], veld: str, maximum: int, verplicht: bool = False) -> Optional[str]:
    if waarde is None:
        if verplicht:
            raise ValueError(f"{veld} is verplicht")
        return None
    waarde = waarde.strip()
    if not waarde:
        if verplicht:
            raise ValueError(f"{veld} is verplicht")
        return None
    if len(waarde) > maximum:
        raise ValueError(f"{veld} is langer dan {maximum} tekens")
    if _STUURTEKENS.search(waarde):
        raise ValueError(f"{veld} bevat stuurtekens")
    return waarde


class LogoInvoer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pad: str
    naam: Optional[str] = None
    rol: Literal["eigen", "partner"] = "partner"

    @field_validator("pad")
    @classmethod
    def _pad(cls, v: str) -> str:
        if org_service.logo_bestand(v) is None:
            raise ValueError("logo moet een bestaande afbeelding onder /static/images/ zijn")
        return v

    @field_validator("naam")
    @classmethod
    def _naam(cls, v: Optional[str]) -> Optional[str]:
        return _tekst(v, "naam van het logo", 200)


class OrganisatieInvoer(BaseModel):
    """De instelling zoals de beheerder hem zet (en zoals hij in een export staat)."""
    model_config = ConfigDict(extra="forbid")

    code: str
    naam: str
    korte_naam: Optional[str] = None
    oin: Optional[str] = None
    gemeente_codes: List[str] = Field(default_factory=list, max_length=50)
    # Optioneel: de standaardgemeente; komt vooraan in gemeente_codes (de eerste is de standaard)
    standaard_gemeente_code: Optional[str] = None
    benchmark_provincie: Optional[str] = None
    contact_email: Optional[str] = None
    thema: str = org_service.STANDAARD_THEMA
    logos: List[LogoInvoer] = Field(default_factory=list, max_length=20)

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        if not _CODE.fullmatch(v or ""):
            raise ValueError("code: alleen a-z, 0-9 en -, maximaal 32 tekens")
        return v

    @field_validator("naam")
    @classmethod
    def _naam(cls, v: str) -> str:
        return _tekst(v, "naam", 200, verplicht=True)  # type: ignore[return-value]

    @field_validator("korte_naam")
    @classmethod
    def _korte_naam(cls, v: Optional[str]) -> Optional[str]:
        return _tekst(v, "korte naam", 50)

    @field_validator("benchmark_provincie")
    @classmethod
    def _provincie(cls, v: Optional[str]) -> Optional[str]:
        return _tekst(v, "benchmarkprovincie", 100)

    @field_validator("oin")
    @classmethod
    def _oin(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip() or None
        if v is not None and not _OIN.fullmatch(v):
            raise ValueError("OIN bestaat uit 20 cijfers")
        return v

    @field_validator("contact_email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip() or None
        if v is not None and (len(v) > 254 or not _EMAIL.fullmatch(v)):
            raise ValueError("contact_email is geen geldig e-mailadres")
        return v

    @field_validator("gemeente_codes")
    @classmethod
    def _gemeente_codes(cls, v: List[str]) -> List[str]:
        uit: List[str] = []
        for code in v:
            if not isinstance(code, str) or not _GEMEENTECODE.fullmatch(code):
                raise ValueError(f"gemeentecode {code!r}: vier cijfers (CBS), bijvoorbeeld 0080")
            if code not in uit:
                uit.append(code)
        return uit

    @field_validator("thema")
    @classmethod
    def _thema(cls, v: str) -> str:
        if not org_service.thema_bestaat(v):
            raise ValueError(f"thema {v!r} bestaat niet in static/css/themes/")
        return v

    @model_validator(mode="after")
    def _standaard_vooraan(self) -> "OrganisatieInvoer":
        std = self.standaard_gemeente_code
        if std is not None:
            if std not in self.gemeente_codes:
                raise ValueError("standaard_gemeente_code moet in gemeente_codes staan")
            self.gemeente_codes = [std] + [c for c in self.gemeente_codes if c != std]
        self.standaard_gemeente_code = self.gemeente_codes[0] if self.gemeente_codes else None
        return self

    def als_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d.pop("standaard_gemeente_code", None)
        return d


class OrganisatieExport(BaseModel):
    """Exportbestand: de instelling met een kop, zodat een andere instantie hem kan overnemen."""
    model_config = ConfigDict(extra="ignore")

    formaat: Literal["d-omnitwin/organisatie"]
    versie: Literal[1]
    organisatie: OrganisatieInvoer


class Thema(BaseModel):
    naam: str
    titel: str
    # WCAG 2.1 AA volgens het kopcommentaar van het thema ("@wcag-aa: ja|nee", #284); None = onbekend
    wcag_aa: Optional[bool] = None
    kleuren: Dict[str, Dict[str, str]]  # {"licht": {token: "#hex"}, "donker": {...}}


# ── Lezen (publiek) ─────────────────────────────────────────────────────────

@router.get("", response_model=Organisatie)
def get_organisatie(db: Session = Depends(get_db)):
    """De organisatie van deze instantie (één instantie = één organisatie)."""
    org = lees_organisatie(db)
    if org is None:
        raise HTTPException(status_code=404, detail="Organisatie van deze instantie is niet ingericht")
    return org


@router.get("/beeldmerk.svg", include_in_schema=False)
def get_beeldmerk(db: Session = Depends(get_db)):
    """Beeldmerk in de kleuren van het organisatiethema, als favicon (#249)."""
    return Response(beeldmerk_svg(lees_organisatie(db)), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-cache"})


# ── Instellen (beheerder, #253) ─────────────────────────────────────────────

def _audit(gebruiker: dict, actie: str, wijzigingen: Dict[str, Any]) -> None:
    """Auditregel: wie (sub/gebruikersnaam, nooit e-mail of tokens) en wat."""
    wie = gebruiker.get("username")
    sub = gebruiker.get("onderwerp")
    velden = ", ".join(sorted(wijzigingen)) or "geen wijzigingen"
    AppLogger.info(
        f"Organisatie {actie} door '{wie}'" + (f" sub={sub}" if sub else "") + f": {velden}",
        category="ADMIN", user_id=str(gebruiker.get("user_id")) if gebruiker.get("user_id") is not None else None,
        extra={"actie": f"organisatie.{actie}", "wie": wie, "sub": sub, "bron": gebruiker.get("type"),
               "wijzigingen": wijzigingen},
    )


def _zet(db: Session, invoer: OrganisatieInvoer, gebruiker: dict, actie: str) -> Dict[str, Any]:
    nieuw = invoer.als_dict()
    oud = lees_organisatie(db)
    org_service.schrijf_organisatie(db, nieuw)
    _audit(gebruiker, actie, org_service.wijzigingen(oud, nieuw))
    return lees_organisatie(db) or {}


@router.put("", response_model=Organisatie)
def put_organisatie(invoer: OrganisatieInvoer, db: Session = Depends(get_db),
                    gebruiker: dict = Depends(vereis_admin)):
    """Organisatie en thema instellen. Ongeldige invoer (onbekend thema, logo buiten
    /static/images/, e-mail, gemeentecode) geeft 422; er verandert dan niets."""
    return _zet(db, invoer, gebruiker, "bijgewerkt")


@router.get("/themas", response_model=List[Thema])
def get_themas(_: dict = Depends(vereis_admin)):
    """De thema's in static/css/themes, met titel en voorbeeldkleuren (licht en donker)."""
    return org_service.themas()


@router.get("/logos", response_model=List[str])
def get_logos(_: dict = Depends(vereis_admin)):
    """Afbeeldingen onder /static/images/ die als footer-logo gekozen kunnen worden (geen uploads)."""
    return org_service.beschikbare_logos()


@router.get("/export")
def export_organisatie(db: Session = Depends(get_db), _: dict = Depends(vereis_admin)):
    """De instelling als JSON-bestand, om in een andere instantie te importeren (mesh, ADR 0007).
    Bevat geen geheimen; logo's en thema verwijzen naar bestanden die de andere instantie ook moet hebben."""
    org = lees_organisatie(db)
    if org is None:
        raise HTTPException(status_code=404, detail="Organisatie van deze instantie is niet ingericht")
    org.pop("standaard_gemeente_code", None)
    body = {
        "formaat": EXPORT_FORMAAT,
        "versie": EXPORT_VERSIE,
        "d_omnitwin_versie": __version__,
        "geexporteerd_op": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "organisatie": org,
    }
    return JSONResponse(body, headers={
        "Content-Disposition": f'attachment; filename="organisatie-{org["code"]}.json"',
        "Cache-Control": "no-store",
    })


@router.post("/import", response_model=Organisatie)
def import_organisatie(export: OrganisatieExport, db: Session = Depends(get_db),
                       gebruiker: dict = Depends(vereis_admin)):
    """Een export van (een andere) instantie overnemen. Zelfde validatie als PUT: een thema of
    logo dat hier niet bestaat geeft 422."""
    return _zet(db, export.organisatie, gebruiker, "geimporteerd")
