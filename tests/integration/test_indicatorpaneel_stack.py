"""
Integratietest indicatorpaneel, CSV-export en eigen voorkeuren (#258) tegen een draaiende stack.

- Paneel en CSV voor de indicator van de use case hittestress op Bolsward-Zuidoost (BU19000002):
  eenheid, bron, gemeentegemiddelde, en de CSV als UTF-8 met BOM, puntkomma en decimale komma.
- /api/mijn: anoniem 401; ingelogd via het Keycloak-formulier als de demo-accounts `gebruiker` en
  `admin` (OMNITWIN_OMGEVING=demo): eigen favorieten, die van een ander niet te zien of te verwijderen,
  kaartpositie bewaren en terugkrijgen. Zonder demo-omgeving met Keycloak worden die overgeslagen.

    OMNITWIN_BASE_URL=http://localhost:8128 pytest -m integration tests/integration/test_indicatorpaneel.py
"""

import csv
import html
import io
import os
import re
from http.cookiejar import DefaultCookiePolicy
from urllib.parse import urlsplit

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
BOLSWARD_ZUIDOOST = "BU19000002"
INDICATOR = "Stedelijk hitte-eiland effect"  # use case hittestress
HTML = {"Accept": "text/html,application/xhtml+xml"}

try:
    _config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT)
except requests.RequestException as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)
CONFIG = _config.json() if _config.status_code == 200 else {}
DICHT = os.environ.get("VIEWER_TOEGANG", "open").strip().lower() not in ("", "open")


@pytest.fixture(autouse=True, scope="module")
def _secure_cookies_op_localhost():
    """Keycloak zet zijn cookies met `Secure`; een browser stuurt ze ook naar http://localhost."""
    with pytest.MonkeyPatch.context() as mp:
        if urlsplit(BASE_URL).hostname in ("localhost", "127.0.0.1"):
            mp.setattr(DefaultCookiePolicy, "return_ok_secure", lambda self, cookie, request: True)
        yield


def inloggen(naam, wachtwoord):
    """Als een browser: inloggen via Keycloak en terug naar de kaart; geeft de sessie."""
    s = requests.Session()
    r = s.get(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/", headers=HTML, timeout=TIMEOUT)
    assert "kc-form-login" in r.text, r.url
    actie = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
    r = s.post(
        actie, data={"username": naam, "password": wachtwoord, "credentialId": ""}, headers=HTML, timeout=TIMEOUT
    )
    assert r.status_code == 200 and r.url.rstrip("/") == BASE_URL, (r.status_code, r.url)
    return s


@pytest.fixture(scope="module")
def anoniem():
    if DICHT:
        pytest.skip("VIEWER_TOEGANG=inloggen: de data-API's vragen dan zelf al een login")
    return requests.Session()


@pytest.fixture(scope="module")
def indicator(anoniem):
    r = anoniem.get(
        f"{BASE_URL}/api/data/indicatoren",
        params={"select": "uuid,naam,eenheid", "naam": f"eq.{INDICATOR}"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    if not r.json():
        pytest.skip(f"indicator {INDICATOR} niet geladen (use case hittestress)")
    return r.json()[0]


@pytest.fixture(scope="module")
def buurten(anoniem):
    r = anoniem.get(
        f"{BASE_URL}/api/data/gebieden",
        params={"select": "gebiedstype_id", "id": f"eq.{BOLSWARD_ZUIDOOST}"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200 and r.json(), r.text
    return r.json()[0]["gebiedstype_id"]


# ── Paneel en CSV ────────────────────────────────────────────────────────────


def test_paneel_met_eenheid_bron_en_gemeentegemiddelde(anoniem, indicator):
    r = anoniem.get(
        f"{BASE_URL}/api/gebiedsmonitor/indicatorpaneel",
        params={"indicator_uuid": indicator["uuid"], "gebied_ids": BOLSWARD_ZUIDOOST},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["indicator"]["naam"] == INDICATOR and d["indicator"]["eenheid"] == indicator["eenheid"]
    assert d["bronnen"], "geen bron"
    g = d["gebieden"][0]
    assert g["id"] == BOLSWARD_ZUIDOOST and g["status"] == "gemeten" and isinstance(g["waarde"], float)
    gm = d["gemeentegemiddelden"][0]
    assert gm["gemeenteCode"] == "1900" and gm["jaar"] == g["jaar"]
    assert gm["aantalGebieden"] > 1 and isinstance(gm["waarde"], float)


def test_paneel_zonder_selectie_alleen_gemiddelde(anoniem, indicator, buurten):
    r = anoniem.get(
        f"{BASE_URL}/api/gebiedsmonitor/indicatorpaneel",
        timeout=TIMEOUT,
        params={
            "indicator_uuid": indicator["uuid"],
            "gebiedstype_id": buurten,
            "gemeente_code": "1900",
            "gebieden": "false",
        },
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["gebieden"] == [] and d["gemeentegemiddelden"][0]["gemeenteCode"] == "1900"


def test_paneel_ongeldige_invoer(anoniem, indicator):
    url = f"{BASE_URL}/api/gebiedsmonitor/indicatorpaneel"
    assert anoniem.get(url, params={"indicator_uuid": "geen-uuid"}, timeout=TIMEOUT).status_code == 422
    assert (
        anoniem.get(
            url, params={"indicator_uuid": indicator["uuid"], "gebied_ids": "BU1;x"}, timeout=TIMEOUT
        ).status_code
        == 400
    )
    onbekend = "00000000-0000-4000-8000-000000000000"
    assert anoniem.get(url, params={"indicator_uuid": onbekend}, timeout=TIMEOUT).status_code == 400


def test_csv_formaat(anoniem, indicator):
    r = anoniem.get(
        f"{BASE_URL}/api/gebiedsmonitor/indicatorpaneel.csv",
        params={"indicator_uuid": indicator["uuid"], "gebied_ids": f"{BOLSWARD_ZUIDOOST},BU19000001"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv") and "charset=utf-8" in r.headers["content-type"]
    assert re.match(r'attachment; filename="indicator-[\w-]+-\d{4}-\d{2}-\d{2}\.csv"', r.headers["content-disposition"])
    assert r.content[:3] == b"\xef\xbb\xbf", "geen BOM"
    rijen = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert rijen[0] == ["gebied-code", "gebied-naam", "indicator", "jaar", "waarde", "eenheid", "bron", "status"]
    bolsward = next(x for x in rijen if x[0] == BOLSWARD_ZUIDOOST)
    assert bolsward[2] == INDICATOR and bolsward[7] == "gemeten" and bolsward[6]
    assert "." not in bolsward[4] and re.fullmatch(r"-?\d+(,\d+)?", bolsward[4]), bolsward[4]
    gemiddelde = [x for x in rijen if x[7] == "gemeentegemiddelde"]
    assert gemiddelde and gemiddelde[0][0] == "1900"
    # Waarde in de CSV = waarde in het paneel (zelfde rijen)
    paneel = anoniem.get(
        f"{BASE_URL}/api/gebiedsmonitor/indicatorpaneel",
        params={"indicator_uuid": indicator["uuid"], "gebied_ids": BOLSWARD_ZUIDOOST},
        timeout=TIMEOUT,
    ).json()
    assert float(bolsward[4].replace(",", ".")) == pytest.approx(paneel["gebieden"][0]["waarde"], abs=1e-6)


# ── /api/mijn ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "methode, pad, body",
    [
        ("get", "/api/mijn/favorieten", None),
        ("post", "/api/mijn/favorieten", {"naam": "x", "gebiedIds": [BOLSWARD_ZUIDOOST]}),
        ("delete", "/api/mijn/favorieten/7b1c6f2e-1d1a-4c1e-9c43-6a4b7a0f3c11", None),
        ("get", "/api/mijn/instellingen", None),
        ("put", "/api/mijn/instellingen", {"kaartpositie": {"longitude": 5.5, "latitude": 53, "zoom": 10}}),
    ],
)
def test_mijn_anoniem_401(methode, pad, body):
    r = getattr(requests, methode)(f"{BASE_URL}{pad}", timeout=TIMEOUT, **({"json": body} if body else {}))
    assert r.status_code == 401, (pad, r.status_code, r.text[:200])


@pytest.fixture(scope="module")
def twee_gebruikers():
    if not (CONFIG.get("oidc") and CONFIG.get("demo")):
        pytest.skip("alleen met Keycloak in de demo-omgeving (accounts gebruiker en admin)")
    return inloggen("gebruiker", "gebruiker"), inloggen("admin", "admin")


def _opruimen(s, naam):
    for f in s.get(f"{BASE_URL}/api/mijn/favorieten", timeout=TIMEOUT).json()["favorieten"]:
        if f["naam"] == naam:
            s.delete(f"{BASE_URL}/api/mijn/favorieten/{f['id']}", timeout=TIMEOUT)


def test_favorieten_alleen_eigen(twee_gebruikers, buurten):
    gebruiker, admin = twee_gebruikers
    naam = "Integratietest #258"
    _opruimen(gebruiker, naam)
    try:
        r = gebruiker.post(
            f"{BASE_URL}/api/mijn/favorieten",
            timeout=TIMEOUT,
            json={"naam": naam, "gebiedIds": [BOLSWARD_ZUIDOOST, "BU19000001"], "gebiedstypeId": buurten},
        )
        assert r.status_code == 201, r.text
        fav = r.json()
        assert fav["gebiedIds"] == [BOLSWARD_ZUIDOOST, "BU19000001"] and fav["gebiedstypeId"] == buurten
        # Zelfde naam nog eens: vervangen (200), niet dubbel
        r = gebruiker.post(
            f"{BASE_URL}/api/mijn/favorieten", timeout=TIMEOUT, json={"naam": naam, "gebiedIds": [BOLSWARD_ZUIDOOST]}
        )
        assert r.status_code == 200 and r.json()["id"] == fav["id"]
        eigen = gebruiker.get(f"{BASE_URL}/api/mijn/favorieten", timeout=TIMEOUT).json()["favorieten"]
        assert [f["naam"] for f in eigen].count(naam) == 1

        # Een ander ziet hem niet en kan hem niet verwijderen
        anders = admin.get(f"{BASE_URL}/api/mijn/favorieten", timeout=TIMEOUT).json()["favorieten"]
        assert fav["id"] not in {f["id"] for f in anders}
        assert admin.delete(f"{BASE_URL}/api/mijn/favorieten/{fav['id']}", timeout=TIMEOUT).status_code == 404

        assert gebruiker.delete(f"{BASE_URL}/api/mijn/favorieten/{fav['id']}", timeout=TIMEOUT).status_code == 204
        assert gebruiker.delete(f"{BASE_URL}/api/mijn/favorieten/{fav['id']}", timeout=TIMEOUT).status_code == 404
    finally:
        _opruimen(gebruiker, naam)


def test_favoriet_ongeldig_400(twee_gebruikers):
    gebruiker, _ = twee_gebruikers
    for body in (
        {"naam": " ", "gebiedIds": [BOLSWARD_ZUIDOOST]},
        {"naam": "x", "gebiedIds": []},
        {"naam": "x", "gebiedIds": ["BU 1"]},
    ):
        r = gebruiker.post(f"{BASE_URL}/api/mijn/favorieten", json=body, timeout=TIMEOUT)
        assert r.status_code == 400, (body, r.status_code, r.text)


def test_kaartpositie_per_gebruiker(twee_gebruikers):
    gebruiker, admin = twee_gebruikers
    positie = {"longitude": 5.525, "latitude": 53.06, "zoom": 13.5, "pitch": 0, "bearing": 0}
    r = gebruiker.put(f"{BASE_URL}/api/mijn/instellingen", json={"kaartpositie": positie}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    assert gebruiker.get(f"{BASE_URL}/api/mijn/instellingen", timeout=TIMEOUT).json()["kaartpositie"] == positie
    assert admin.get(f"{BASE_URL}/api/mijn/instellingen", timeout=TIMEOUT).json()["kaartpositie"] != positie
    r = gebruiker.put(
        f"{BASE_URL}/api/mijn/instellingen", json={"kaartpositie": {**positie, "zoom": 99}}, timeout=TIMEOUT
    )
    assert r.status_code in (400, 422)


def test_viewer_weet_dat_je_ingelogd_bent(twee_gebruikers):
    gebruiker, _ = twee_gebruikers
    assert '<meta name="omnitwin-ingelogd" content="1">' in gebruiker.get(f"{BASE_URL}/", timeout=TIMEOUT).text
    assert '<meta name="omnitwin-ingelogd" content="0">' in requests.get(f"{BASE_URL}/", timeout=TIMEOUT).text
