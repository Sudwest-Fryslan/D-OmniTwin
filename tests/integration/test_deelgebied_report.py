"""
Woonplaats- en deelgebiedsanalyse (Sjabloon F, POST /api/report/deelgebied).

Stond als tests/test_deelgebied_report.py in collect_ignore en draaide daardoor
nooit (#202). Nu via HTTP tegen de verse stack, op de Bolsward-buurten uit de
sample (zoals tests/integration/test_usecases.py).

Draaien: zie tests/integration/test_sample_stack.py (zelfde stack en omgeving).
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
BOLSWARD = ["BU19000001", "BU19000002", "BU19000004"]
KWADRANTEN = [
    "Kwaliteit fysieke leefomgeving",
    "Kwaliteit sociale leefomgeving",
    "Kwaliteit van leven",
    "Samenstelling",
]


def deelgebied(**payload):
    return requests.post(f"{BASE_URL}/api/report/deelgebied", json=payload, timeout=TIMEOUT)


@pytest.fixture(scope="module")
def rapport():
    r = deelgebied(gebied_ids=BOLSWARD, deelgebied_naam="Bolsward", referentie="gemeente")
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    return r.json()


def test_kop_en_kwadranten(rapport):
    assert rapport["deelgebied_naam"] == "Bolsward"
    assert rapport["referentie_modus"] == "gemeente"
    assert rapport["totaal_buurten"] == 3
    assert rapport["buurten_met_data"] == 3
    assert [k["kwadrant_naam"] for k in rapport["kwadranten"]] == KWADRANTEN


def test_methodologie_gewogen_gemiddelde(rapport):
    methodologie = rapport["methodologie"]
    assert methodologie["aggregatie"] == "gewogen_gemiddelde"
    assert methodologie["totaal_inwoners_gebied"] > 0
    assert "scoringtype_disclaimer" in methodologie
    assert "statistisch_effect" in methodologie


def test_indicatoren_met_buurt_drilldown(rapport):
    items = [
        ind
        for kwadrant in rapport["kwadranten"]
        for thema in kwadrant["themas"]
        for ind in thema["top10_aandachtspunten"] + thema["top10_kansen"]
    ]
    assert items, "geen enkele indicator in de top-10's"
    ind = items[0]
    for veld in ("gewogen_waarde", "ref_gemiddelde", "z_score", "buurten_drilldown"):
        assert veld in ind, veld
    assert ind["buurten_drilldown"], "lege drilldown"
    for veld in ("buurt_naam", "inwoners", "buurt_z_score", "verschil"):
        assert veld in ind["buurten_drilldown"][0], veld


def test_referentie_fryslan():
    r = deelgebied(gebied_ids=BOLSWARD, referentie="fryslan")
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    data = r.json()
    assert data["referentie_modus"] == "fryslan"
    assert "Fryslân" in data["referentie_label"]


def test_onbekende_buurt_geeft_400():
    assert deelgebied(gebied_ids=["ONBEKEND_001"]).status_code == 400
