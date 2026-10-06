"""
Problem Details (RFC 9457) van de laad-API
==========================================
Eén plek voor de probleemtypen uit `docs/api/laden/README.md#probleemtypen`: code, titel en
de `type`-URL. Fouten per regel (`Fout`) hebben `resource`, `regel` en `veld`; de waarde uit
de regel wordt nooit herhaald (geen brondata in foutmeldingen of in de database).
"""

from __future__ import annotations

from dataclasses import dataclass

TYPE_BASIS = "https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/docs/api/laden/README.md#"
MEDIATYPE = "application/problem+json"
MAX_FOUTEN = 1000  # zoveel fouten bewaart en toont een levering (openapi: Levering.fouten maxItems)

TITELS = {
    # Uit de specificatie (README, Probleemtypen)
    "levering-afgekeurd": "Levering afgekeurd",
    "formaat-ongeldig": "Formaat ongeldig",
    "mediatype-past-niet": "Mediatype past niet bij het profiel",
    "schema-ongeldig": "Schema ongeldig",
    "gebied-onbekend": "Gebied bestaat niet",
    "gebiedstype-onbekend": "Gebiedstype bestaat niet",
    "indicator-onbekend": "Indicator bestaat niet",
    "jaar-ongeldig": "Jaar ongeldig",
    "dubbele-sleutel": "Dubbele sleutel",
    "waarde-buiten-bereik": "Waarde buiten bereik",
    "n-ontbreekt": "n ontbreekt",
    "n-onder-drempel": "n onder de drempel",
    "crs-niet-ondersteund": "CRS niet ondersteund",
    "geometrie-ongeldig": "Geometrie ongeldig",
    "aantal-niet-plausibel": "Aantal regels niet plausibel",
    "relatie-in-gebruik": "Relatie in gebruik",
    "idempotency-key-hergebruikt": "Idempotency-Key hergebruikt",
    "levering-loopt": "Levering loopt nog",
    "profiel-vast": "Profiel ligt vast",
    "versie-meerdere-leveringen": "Versie bestaat uit meerdere leveringen",
    # HTTP-niveau
    "ongeldig-verzoek": "Ongeldig verzoek",
    "registratie-ongeldig": "Registratie ongeldig",
    "dataset-bestaat": "Dataset bestaat al",
    "niet-gevonden": "Niet gevonden",
    "niet-geauthenticeerd": "Niet geauthenticeerd",
    "geen-toegang": "Geen toegang",
    "te-groot": "Te groot",
    "te-veel-verzoeken": "Te veel verzoeken",
    "niet-beschikbaar": "Tijdelijk niet beschikbaar",
    "serverfout": "Serverfout",
}

HTTP_CODE = {400: "ongeldig-verzoek", 401: "niet-geauthenticeerd", 403: "geen-toegang", 404: "niet-gevonden",
             405: "ongeldig-verzoek", 409: "levering-loopt", 413: "te-groot", 415: "mediatype-past-niet",
             422: "registratie-ongeldig", 429: "te-veel-verzoeken", 503: "niet-beschikbaar", 500: "serverfout"}


@dataclass(frozen=True)
class Fout:
    """Eén fout in een levering (regel, of de hele levering als regel None is)."""
    code: str
    melding: str
    resource: str | None = None
    regel: int | None = None
    veld: str | None = None

    def als_probleem(self) -> dict:
        p = {"type": TYPE_BASIS + self.code, "code": self.code, "title": TITELS.get(self.code, self.code),
             "detail": self.melding}
        for k in ("resource", "regel", "veld"):
            if getattr(self, k) is not None:
                p[k] = getattr(self, k)
        return p


def probleem(status: int, code: str, detail: str, **extra) -> dict:
    """Problem Details-document (zonder interne details)."""
    p = {"type": TYPE_BASIS + code, "code": code, "title": TITELS.get(code, code), "status": status,
         "detail": detail}
    p.update({k: v for k, v in extra.items() if v is not None})
    return p


class Probleem(Exception):
    """Fout die als Problem Details naar de client gaat (status, code, detail, extensies)."""

    def __init__(self, status: int, code: str, detail: str, headers: dict | None = None, **extra):
        super().__init__(detail)
        self.status, self.code, self.detail, self.headers, self.extra = status, code, detail, headers or {}, extra

    def document(self, instance: str | None = None) -> dict:
        return probleem(self.status, self.code, self.detail, instance=instance, **self.extra)
