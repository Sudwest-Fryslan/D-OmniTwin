"""
De eigen organisatie als instellingsdata op een verse stack (#231, ADR 0007).

Een verse installatie krijgt Súdwest-Fryslân uit db/stuurdata/organisatie.sql; de
viewer, de rapporten en het Kompas zien er voor SWF hetzelfde uit als voorheen.
Draaien: zie tests/integration/test_sample_stack.py.
"""

import os
import re

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30

SWF_LOGOS = [
    ("/static/images/SWF-logo.png", "Gemeente Súdwest-Fryslân"),
    ("/static/images/Logo_Tytsjerksteradiel.png", "Gemeente Tytsjerksteradiel"),
    ("/static/images/LOGO-GEMEENTE-LEEUWARDEN.png", "Gemeente Leeuwarden"),
    ("/static/images/DF-LOGO-1-1000x1000-TBG.png", "Datafryslân"),
]


def test_api_organisatie_geeft_swf():
    r = requests.get(f"{BASE_URL}/api/organisatie", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    org = r.json()
    assert org["code"] == "swf"
    assert org["naam"] == "Gemeente Súdwest-Fryslân"
    assert org["korte_naam"] == "SWF"
    assert org["gemeente_codes"] == ["1900"]
    assert org["standaard_gemeente_code"] == "1900"
    assert org["benchmark_provincie"] == "Fryslân"
    assert org["contact_email"] == "geo-groep@sudwestfryslan.nl"
    assert org["thema"] == "swf"
    assert [(l["pad"], l["naam"]) for l in org["logos"]] == SWF_LOGOS


def test_footer_logos_zoals_voorheen():
    html = requests.get(f"{BASE_URL}/", timeout=TIMEOUT).text
    footer = html[html.index('<footer class="footer">') : html.index("</footer>")]
    imgs = re.findall(r'<img src="([^"]+)" alt="([^"]*)" class="footer-logo" title="([^"]*)">', footer)
    assert [(src, alt) for src, alt, _ in imgs] == SWF_LOGOS
    for src, _ in SWF_LOGOS:
        assert requests.get(f"{BASE_URL}{src}", timeout=TIMEOUT).status_code == 200, src


def test_kompas_standaard_is_configuratie_1():
    std = requests.get(f"{BASE_URL}/api/kompas/standaard/hierarchie", timeout=TIMEOUT)
    een = requests.get(f"{BASE_URL}/api/kompas/1/hierarchie", timeout=TIMEOUT)
    assert std.status_code == 200 and een.status_code == 200
    assert std.json()["config_id"] == 1
    assert std.json()["hierarchie"] == een.json()["hierarchie"]


def _buurt_ids(n=3):
    r = requests.get(
        f"{BASE_URL}/api/data/gebieden",
        # Buurten van de eigen gemeente; sinds #236 staan alle Friese buurten in een verse installatie
        params={"select": "id,gemeente_code", "id": "like.BU*", "gemeente_code": "eq.1900", "limit": str(n)},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    rijen = r.json()
    assert rijen and all(g["gemeente_code"] == "1900" for g in rijen)
    return [g["id"] for g in rijen]


def test_rapport_zonder_gemeente_gebruikt_eigen_gemeente():
    """Zonder gemeente_code is de referentie de gemeente van de organisatie (SWF), zoals voorheen met '1900'."""
    ids = _buurt_ids()
    zonder = requests.post(
        f"{BASE_URL}/api/report/multi-gebied", json={"gebied_ids": ids, "referentie": "gemeente"}, timeout=TIMEOUT
    )
    met = requests.post(
        f"{BASE_URL}/api/report/multi-gebied",
        json={"gebied_ids": ids, "referentie": "gemeente", "gemeente_code": "1900"},
        timeout=TIMEOUT,
    )
    assert zonder.status_code == 200, zonder.text
    assert met.status_code == 200, met.text
    assert zonder.json()["referentie_label"] == "⌀ Gemeente Súdwest-Fryslân"
    assert zonder.json() == met.json()

    thema = requests.post(
        f"{BASE_URL}/api/report/thema-analyse", json={"gebied_ids": ids, "referentie": "gemeente"}, timeout=TIMEOUT
    )
    assert thema.status_code == 200, thema.text
    assert thema.json()["referentie_label"] == "⌀ Gemeente Súdwest-Fryslân"
