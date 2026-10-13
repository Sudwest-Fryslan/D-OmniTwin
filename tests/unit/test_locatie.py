"""
Unit tests voor de eigen buurt via postcode/adres of locatie (#336): PDOK Locatieserver (gemockt),
validatie en de koppeling aan de gebieden van de installatie. Geen netwerk, geen database.
Alleen openbare adressen (gemeentehuis Sneek) of fictieve waarden.
"""

import pytest
import requests
from fastapi import HTTPException
from pydantic import ValidationError

from omnitwin.routers import locatie as router
from omnitwin.services import locatie

pytestmark = pytest.mark.unit


class Antwoord:
    def __init__(self, docs=None, status=200):
        self._docs, self.status_code = docs or [], status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return {"response": {"numFound": len(self._docs), "docs": self._docs}}


def nep_get(docs=None, status=200, vangst=None):
    def get(url, params=None, timeout=None):
        if vangst is not None:
            vangst.append((url, params))
        return Antwoord(docs, status)

    return get


# ── services/locatie.py ──────────────────────────────────────────────────────


def test_adres_geeft_buurtcode_van_eerste_adres():
    vangst = []
    uit = locatie.buurt_bij_adres(
        "Marktstraat 15 Sneek",
        get=nep_get([{"buurtcode": "BU19000101", "buurtnaam": "Sneek binnen de grachten"}], vangst=vangst),
    )
    assert uit == {"buurtcode": "BU19000101", "buurtnaam": "Sneek binnen de grachten"}
    url, params = vangst[0]
    assert url.endswith("/free") and params["fq"] == "type:adres" and params["rows"] == 1


def test_locatie_zoekt_omgekeerd_op_buurt():
    vangst = []
    uit = locatie.buurt_bij_punt(
        53.0329,
        5.6603,
        get=nep_get([{"identificatie": "BU19000101", "buurtnaam": "Sneek binnen de grachten"}], vangst=vangst),
    )
    assert uit["buurtcode"] == "BU19000101"
    url, params = vangst[0]
    assert url.endswith("/reverse") and params["type"] == "buurt"


def test_geen_of_vreemde_treffer_is_none():
    assert locatie.buurt_bij_adres("9999 ZZ", get=nep_get([])) is None
    assert locatie.buurt_bij_adres("9999 ZZ", get=nep_get([{"buurtcode": "WK190001"}])) is None


def test_buurtcode_met_letters():
    """CBS-buurtcodes bevatten soms letters (Amsterdam: BU0363AE02)."""
    uit = locatie.buurt_bij_adres("1012 JS", get=nep_get([{"buurtcode": "BU0363AE02", "buurtnaam": "Oude Kerk e.o."}]))
    assert uit["buurtcode"] == "BU0363AE02"


def test_pdok_fout_geeft_locatiefout_zonder_adres_in_de_melding():
    with pytest.raises(locatie.LocatieFout) as e:
        locatie.buurt_bij_adres("Marktstraat 15 Sneek", get=nep_get(status=503))
    assert "Marktstraat" not in str(e.value)

    def kapot(*a, **k):
        raise requests.ConnectionError("Marktstraat 15 Sneek")

    with pytest.raises(locatie.LocatieFout) as e:
        locatie.buurt_bij_adres("Marktstraat 15 Sneek", get=kapot)
    assert "Marktstraat" not in str(e.value)


@pytest.mark.parametrize(
    "adres,goed",
    [
        ("8601 CR", True),
        ("Marktstraat 15 Sneek", True),
        ("8601", True),
        ("Sneek", False),
        ("", False),
        ("1" * 201, False),
    ],
)
def test_geldig_adres(adres, goed):
    assert locatie.geldig_adres(adres) is goed


def test_in_nederland():
    assert locatie.in_nederland(53.03, 5.66)
    assert not locatie.in_nederland(48.85, 2.35)  # Parijs


# ── routers/locatie.py ───────────────────────────────────────────────────────

GEBIEDEN = [{"id": "BU19000101", "naam": "Sneek binnen de grachten", "gemeente_code": "1900", "gebiedstype_id": "b"}]


@pytest.fixture
def installatie(monkeypatch):
    monkeypatch.setattr(router, "laad_gebieden", lambda db: GEBIEDEN)


def test_adres_geeft_gebied_van_de_installatie(installatie, monkeypatch):
    monkeypatch.setattr(
        locatie, "buurt_bij_adres", lambda a: {"buurtcode": "BU19000101", "buurtnaam": "Sneek binnen de grachten"}
    )
    uit = router.buurt(router.BuurtVraag(adres="8601 CR"), db=None)
    assert (uit.gebied_id, uit.naam) == ("BU19000101", "Sneek binnen de grachten")


def test_locatie_geeft_gebied_van_de_installatie(installatie, monkeypatch):
    monkeypatch.setattr(
        locatie, "buurt_bij_punt", lambda lat, lon: {"buurtcode": "BU19000101", "buurtnaam": "Sneek binnen de grachten"}
    )
    assert router.buurt(router.BuurtVraag(lat=53.03, lon=5.66), db=None).gebied_id == "BU19000101"


def test_buurt_buiten_de_installatie_is_404(installatie, monkeypatch):
    monkeypatch.setattr(locatie, "buurt_bij_adres", lambda a: {"buurtcode": "BU03630000", "buurtnaam": "Burgwallen"})
    with pytest.raises(HTTPException) as e:
        router.buurt(router.BuurtVraag(adres="1012 AB"), db=None)
    assert e.value.status_code == 404 and "Burgwallen" in e.value.detail


def test_niets_gevonden_is_404_en_pdok_weg_is_503(installatie, monkeypatch):
    monkeypatch.setattr(locatie, "buurt_bij_adres", lambda a: None)
    with pytest.raises(HTTPException) as e:
        router.buurt(router.BuurtVraag(adres="9999 ZZ"), db=None)
    assert e.value.status_code == 404

    def weg(a):
        raise locatie.LocatieFout("ConnectionError")

    monkeypatch.setattr(locatie, "buurt_bij_adres", weg)
    with pytest.raises(HTTPException) as e:
        router.buurt(router.BuurtVraag(adres="8601 CR"), db=None)
    assert e.value.status_code == 503


def test_ongeldige_invoer(installatie):
    with pytest.raises(ValidationError):
        router.BuurtVraag()  # adres of locatie verplicht
    with pytest.raises(ValidationError):
        router.BuurtVraag(lat=53.0)  # lon ontbreekt
    with pytest.raises(HTTPException) as e:
        router.buurt(router.BuurtVraag(adres="Sneek"), db=None)
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        router.buurt(router.BuurtVraag(lat=48.85, lon=2.35), db=None)
    assert e.value.status_code == 422
