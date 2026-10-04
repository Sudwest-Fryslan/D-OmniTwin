"""
Integratietest toegang per laag en bron (#254, ADR 0010) tegen een draaiende stack met de use case
rechten-per-laag (interne laag, indicator en waarden; DEMODATA) en VIEWER_TOEGANG=open.

- anoniem: interne data niet in de lijsten (FastAPI, PostgREST), directe aanroep 401, ook met een
  zelf meegestuurde header X-Omnitwin-Toegang; openbare data ongewijzigd;
- lezer (BFF-sessie via het Keycloak-formulier) en beheerder (X-Admin-Key): alles, 200;
- ingelogd zonder rol (bearer-token van een machineclient zonder lezer): 403.

De lezer is het demo-account `gebruiker`/`gebruiker` (OMNITWIN_OMGEVING=demo) of een testaccount
(OMNITWIN_TESTACCOUNTS=1 en KEYCLOAK_ADMIN_PASSWORD). OMNITWIN_BASE_URL moet het publieke adres zijn
(de host uit OIDC_ISSUER). ADMIN_API_KEY uit .env (`--env-file .env`) voor de beheerder.

    OMNITWIN_BASE_URL=http://localhost:8122 pytest -m integration tests/integration/test_toegang_per_laag.py
"""

import html
import os
import re
from http.cookiejar import DefaultCookiePolicy
from urllib.parse import quote, urlsplit

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
U_INTERN = "e36c5cab-2e36-4be0-bd8f-ade7924975a6"          # DEMODATA: interne voorbeeldindicator
U_OPEN = "bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c"            # Afstand tot koele plek (sample, openbaar)
BUURTEN = "afba67cb-6b38-4723-9c95-102a22d5b38a"
LAAG_INTERN = "DEMODATA: interne voorbeeldlaag (buurten)"
HTML = {"Accept": "text/html,application/xhtml+xml"}

try:
    _config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT)
except requests.RequestException as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)
CONFIG = _config.json() if _config.status_code == 200 else {}
if os.environ.get("VIEWER_TOEGANG", "open").strip().lower() not in ("", "open"):
    pytest.skip("VIEWER_TOEGANG=inloggen: anoniem ziet dan niets (test_viewer_toegang.py)", allow_module_level=True)


def _interne_laag_id():
    """Id van de interne laag (via de beheerder), of overslaan als de use case niet geïnstalleerd is."""
    key = os.environ.get("ADMIN_API_KEY")
    if not key:
        pytest.skip("ADMIN_API_KEY ontbreekt (--env-file .env)")
    r = requests.get(f"{BASE_URL}/api/data/v1/externe_kaartlagen?naam=eq.{quote(LAAG_INTERN, safe='')}&select=id",
                     headers={"X-Admin-Key": key}, timeout=TIMEOUT)
    if r.status_code != 200 or not r.json():
        pytest.skip("use case rechten-per-laag niet geïnstalleerd")
    return r.json()[0]["id"]


@pytest.fixture(scope="module")
def laag_id():
    return _interne_laag_id()


@pytest.fixture(scope="module")
def beheerder():
    s = requests.Session()
    s.headers["X-Admin-Key"] = os.environ.get("ADMIN_API_KEY", "")
    return s


def paden(laag_id):
    """(pad, soort): soort lijst = 200 zonder de interne items, soort direct = 401 anoniem."""
    return {
        "indicator_postgrest": f"/api/data/v1/indicatoren?uuid=eq.{U_INTERN}&select=uuid,toegang",
        "waarden_postgrest": f"/api/data/v1/gebied_data?indicator_uuid=eq.{U_INTERN}&select=waarde,toegang",
        "actueel_postgrest": f"/api/data/v1/vw_gebied_indicator_actueel?indicator_uuid=eq.{U_INTERN}",
        "laag_postgrest": f"/api/data/externe_kaartlagen?naam=eq.{quote(LAAG_INTERN, safe='')}&select=id,toegang",
        "kaart_direct": f"/api/gebiedsmonitor/kaart_data/{BUURTEN}?indicator_uuid={U_INTERN}",
        "visualisatie_direct": f"/api/visualisatie/config/{U_INTERN}",
        "laag_direct": f"/api/externe-lagen/{laag_id}/features",
    }


# ------------------------------------------------------------------ anoniem

def test_anoniem_lijsten_zonder_intern(laag_id):
    p = paden(laag_id)
    for naam in ("indicator_postgrest", "waarden_postgrest", "actueel_postgrest", "laag_postgrest"):
        r = requests.get(f"{BASE_URL}{p[naam]}", timeout=TIMEOUT)
        assert r.status_code == 200 and r.json() == [], (naam, r.status_code, r.text[:200])
    lagen = requests.get(f"{BASE_URL}/api/externe-lagen", timeout=TIMEOUT).json()["lagen"]
    assert lagen and all(l["toegang"] == "openbaar" for l in lagen)
    rpc = requests.get(f"{BASE_URL}/api/data/rpc/get_indicatoren_stats?p_gebiedstype_id={BUURTEN}", timeout=TIMEOUT)
    assert rpc.status_code == 200 and U_INTERN not in {i["uuid"] for i in rpc.json()}
    assert U_INTERN not in requests.get(f"{BASE_URL}/api/gebiedsmonitor/indicatoren", timeout=TIMEOUT).text
    assert U_INTERN not in requests.get(f"{BASE_URL}/api/kompas/standaard/hierarchie", timeout=TIMEOUT).text


@pytest.mark.parametrize("naam", ["kaart_direct", "visualisatie_direct", "laag_direct"])
def test_anoniem_directe_aanroep_401(laag_id, naam):
    r = requests.get(f"{BASE_URL}{paden(laag_id)[naam]}", timeout=TIMEOUT)
    assert r.status_code == 401, (naam, r.status_code, r.text[:200])
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "niet-ingelogd"


def test_anoniem_interne_collectie_401():
    """pg_featureserv: een collectie van een interne kaartlaag (laag.<featureTabel>) via de forwardAuth."""
    r = requests.get(f"{BASE_URL}/api/geo/v1/collections/laag.demo_intern_laag/items?limit=1", timeout=TIMEOUT)
    assert r.status_code == 401
    assert requests.get(f"{BASE_URL}/api/geo/v1/collections", timeout=TIMEOUT).status_code == 200


def test_zelf_meegestuurde_header_telt_niet(laag_id):
    """Traefik vervangt X-Omnitwin-Toegang door die van de forwardAuth (authResponseHeaders)."""
    r = requests.get(f"{BASE_URL}{paden(laag_id)['indicator_postgrest']}",
                     headers={"X-Omnitwin-Toegang": "intern"}, timeout=TIMEOUT)
    assert r.status_code == 200 and r.json() == []


def test_openbare_data_ongewijzigd():
    r = requests.get(f"{BASE_URL}/api/data/v1/gebied_data?indicator_uuid=eq.{U_OPEN}&select=waarde,toegang&limit=5",
                     timeout=TIMEOUT)
    assert r.status_code == 200 and r.json() and all(w["toegang"] == "openbaar" for w in r.json())
    kaart = requests.get(f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{BUURTEN}?indicator_uuid={U_OPEN}", timeout=TIMEOUT)
    assert kaart.status_code == 200 and kaart.json()
    assert requests.get(f"{BASE_URL}/api/kompas/1/gebied/BU19000002", timeout=TIMEOUT).status_code == 200


# ------------------------------------------------------------------ beheerder (X-Admin-Key) en lezer (sessie)

def _alles_zichtbaar(s, laag_id):
    p = paden(laag_id)
    for naam in ("indicator_postgrest", "waarden_postgrest", "actueel_postgrest", "laag_postgrest"):
        r = s.get(f"{BASE_URL}{p[naam]}", timeout=TIMEOUT)
        assert r.status_code == 200 and r.json(), (naam, r.status_code, r.text[:200])
    for naam in ("kaart_direct", "visualisatie_direct", "laag_direct"):
        r = s.get(f"{BASE_URL}{p[naam]}", timeout=TIMEOUT)
        assert r.status_code == 200, (naam, r.status_code, r.text[:200])
    assert s.get(f"{BASE_URL}{p['indicator_postgrest']}", timeout=TIMEOUT).json()[0]["toegang"] == "intern"
    lagen = s.get(f"{BASE_URL}/api/externe-lagen", timeout=TIMEOUT).json()["lagen"]
    assert laag_id in {l["id"] for l in lagen}


def test_beheerder_ziet_alles(beheerder, laag_id):
    _alles_zichtbaar(beheerder, laag_id)


@pytest.fixture(autouse=True, scope="module")
def _secure_cookies_op_localhost():
    """Keycloak zet zijn cookies met `Secure`; een browser stuurt die ook naar http://localhost."""
    with pytest.MonkeyPatch.context() as mp:
        if urlsplit(BASE_URL).hostname in ("localhost", "127.0.0.1"):
            mp.setattr(DefaultCookiePolicy, "return_ok_secure", lambda self, cookie, request: True)
        yield


@pytest.fixture(scope="module")
def lezer_sessie():
    if not CONFIG.get("oidc"):
        pytest.skip("Keycloak staat niet aan")
    if not CONFIG.get("demo"):
        pytest.skip("geen demo-omgeving: geen lezer gebruiker/gebruiker")
    s = requests.Session()
    r = s.get(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/", headers=HTML, timeout=TIMEOUT)
    assert "kc-form-login" in r.text, r.url
    actie = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
    r = s.post(actie, data={"username": "gebruiker", "password": "gebruiker", "credentialId": ""}, headers=HTML,
               timeout=TIMEOUT)
    assert r.status_code == 200 and r.url == f"{BASE_URL}/", (r.status_code, r.url)
    yield s
    s.post(f"{BASE_URL}/api/admin/auth/logout", timeout=TIMEOUT)


def test_lezer_ziet_alles(lezer_sessie, laag_id):
    _alles_zichtbaar(lezer_sessie, laag_id)


def test_lezer_geen_beheer(lezer_sessie):
    assert lezer_sessie.get(f"{BASE_URL}/api/admin/health", timeout=TIMEOUT).status_code == 403


# ------------------------------------------------------------------ ingelogd zonder rol: 403

def test_token_zonder_rol_403(laag_id):
    """Een machineclient zonder lezer of beheerder (OMNITWIN_CLIENT_ID met alleen laadrollen)."""
    from omnitwin import usecases as uc
    if not (os.environ.get("OMNITWIN_CLIENT_ID") and os.environ.get("OMNITWIN_CLIENT_SECRET")):
        pytest.skip("geen machineclient (OMNITWIN_CLIENT_ID, OMNITWIN_CLIENT_SECRET)")
    token = uc.token(BASE_URL)
    ik = requests.get(f"{BASE_URL}/api/oidc/ik", headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT).json()
    if {"lezer", "beheerder"} & set(ik.get("rollen", [])):
        pytest.skip("de machineclient heeft lezer of beheerder")
    r = requests.get(f"{BASE_URL}{paden(laag_id)['kaart_direct']}", headers={"Authorization": f"Bearer {token}"},
                     timeout=TIMEOUT)
    assert r.status_code == 403 and r.json()["code"] == "geen-toegang"
