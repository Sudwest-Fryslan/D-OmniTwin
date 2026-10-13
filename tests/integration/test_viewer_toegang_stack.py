"""
Integratietest toegang tot de viewer (#266, ADR 0009) tegen een draaiende stack.

Wat de stack doet, volgt uit VIEWER_TOEGANG (geef dezelfde waarde mee als in .env, bijv. met
`--env-file .env`):

- `open` (standaard): anoniem 200 op `/`, de API's van de backend, `/api/data` en `/api/geo`;
- `inloggen`: anoniem 302 (pagina) of 401 (API's, ook PostgREST en pg_featureserv via forwardAuth);
  ingelogd via het Keycloak-formulier met rol `lezer`: 200. Open paden blijven open.

Het inloggen als lezer gebruikt het demo-account `gebruiker`/`gebruiker` (OMNITWIN_OMGEVING=demo), of
anders een testaccount (OMNITWIN_TESTACCOUNTS=1 en KEYCLOAK_ADMIN_PASSWORD, zoals
test_beheer_keycloak.py). OMNITWIN_BASE_URL moet het publieke adres zijn (de host uit OIDC_ISSUER).

    OMNITWIN_BASE_URL=http://localhost:8120 VIEWER_TOEGANG=inloggen \\
    pytest -m integration tests/integration/test_viewer_toegang.py
"""

import html
import os
import re
from http.cookiejar import DefaultCookiePolicy
from urllib.parse import urlsplit

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30


@pytest.fixture(autouse=True, scope="module")
def _secure_cookies_op_localhost():
    """Keycloak zet zijn cookies met `Secure`. Een browser stuurt die ook naar http://localhost (een
    'potentially trustworthy origin'); requests niet. Op localhost doet de test het als een browser."""
    with pytest.MonkeyPatch.context() as mp:
        if urlsplit(BASE_URL).hostname in ("localhost", "127.0.0.1"):
            mp.setattr(DefaultCookiePolicy, "return_ok_secure", lambda self, cookie, request: True)
        yield


def sessie():
    return requests.Session()


DICHT = os.environ.get("VIEWER_TOEGANG", "open").strip().lower() not in ("", "open")
HTML = {"Accept": "text/html,application/xhtml+xml"}

# Data-API's die de viewer gebruikt: backend, PostgREST en pg_featureserv (ook de /v1-routers)
DATA_API = [
    "/api/kompas/configuraties",
    "/api/gebiedsmonitor/gebieden?limit=1",
    "/api/visualisatie/paletten",
    "/api/data/gebiedstypes?limit=1",
    "/api/data/v1/gebiedstypes?limit=1",
    "/api/geo/collections",
    "/api/geo/v1/collections",
    "/docs",
]
ALTIJD_OPEN = ["/health", "/static/css/styles.css", "/api/admin/auth/config", "/api/organisatie", "/admin/login"]

try:
    _config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT)
except requests.RequestException as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)
CONFIG = _config.json() if _config.status_code == 200 else {}


def _status(pad, sessie=None, **kw):
    return (sessie or requests).get(f"{BASE_URL}{pad}", timeout=TIMEOUT, allow_redirects=False, **kw).status_code


@pytest.mark.parametrize("pad", ALTIJD_OPEN)
def test_open_paden_altijd_open(pad):
    assert _status(pad) == 200, pad


# ------------------------------------------------------------------ open


@pytest.mark.skipif(DICHT, reason="VIEWER_TOEGANG=inloggen")
@pytest.mark.parametrize("pad", ["/", *DATA_API])
def test_open_anoniem_200(pad):
    assert _status(pad, headers=HTML if pad == "/" else {}) == 200, pad


@pytest.mark.skipif(DICHT, reason="VIEWER_TOEGANG=inloggen")
def test_open_forwardauth_laat_door():
    assert _status("/api/viewer/toegang") == 204


@pytest.mark.skipif(DICHT or not CONFIG.get("oidc"), reason="alleen bij open met Keycloak")
def test_open_kop_een_knop_beheer():
    # Anoniem: geen aparte inlogknop; "Beheer" leidt naar het inloggen
    r = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
    assert 'id="inloggen"' not in r.text and 'id="uitloggen"' not in r.text and 'id="admin-btn"' in r.text


# ------------------------------------------------------------------ inloggen


@pytest.mark.skipif(not DICHT, reason="VIEWER_TOEGANG=open")
def test_dicht_pagina_naar_keycloak():
    r = requests.get(f"{BASE_URL}/", headers=HTML, timeout=TIMEOUT, allow_redirects=False)
    assert r.status_code == 302
    verwacht = "/api/admin/auth/oidc/login?terug=/" if CONFIG.get("oidc") else "/admin/login"
    assert r.headers["location"] == verwacht


@pytest.mark.skipif(not DICHT, reason="VIEWER_TOEGANG=open")
@pytest.mark.parametrize("pad", ["/rapport", "/rapport/benchmark"])
def test_dicht_rapport_naar_inloggen(pad):
    """Rapporten staan in de web-container (#408); forwardAuth viewer-pagina stuurt naar het inloggen."""
    r = requests.get(f"{BASE_URL}{pad}", headers=HTML, timeout=TIMEOUT, allow_redirects=False)
    assert r.status_code == 302, pad
    verwacht = "/api/admin/auth/oidc/login?terug=/" if CONFIG.get("oidc") else "/admin/login"
    assert r.headers["location"].endswith(verwacht), r.headers["location"]


@pytest.mark.skipif(not DICHT, reason="VIEWER_TOEGANG=open")
@pytest.mark.parametrize("pad", DATA_API)
def test_dicht_anoniem_api_401(pad):
    r = requests.get(f"{BASE_URL}{pad}", timeout=TIMEOUT, allow_redirects=False)
    assert r.status_code == 401, (pad, r.status_code, r.text[:200])
    assert r.headers["content-type"].startswith("application/problem+json"), pad
    # Ook bij de weigering via forwardAuth de security-headers van Traefik
    assert "content-security-policy" in {k.lower() for k in r.headers}, pad


@pytest.mark.skipif(not DICHT, reason="VIEWER_TOEGANG=open")
def test_dicht_ongeldig_token_401():
    r = requests.get(
        f"{BASE_URL}/api/data/gebiedstypes?limit=1", headers={"Authorization": "Bearer a.b.c"}, timeout=TIMEOUT
    )
    assert r.status_code == 401


def _lezer():
    """(gebruikersnaam, wachtwoord, opruimen) van een account met alleen de rol lezer."""
    if CONFIG.get("demo"):
        return "gebruiker", "gebruiker", None
    if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1" or not (
        os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")
    ):
        pytest.skip("geen lezer: geen demo-omgeving en geen testaccounts (OMNITWIN_TESTACCOUNTS=1)")
    import tempfile
    from pathlib import Path

    from omnitwin import testaccounts as ta

    beheer = ta.KeycloakBeheer(kc=f"{BASE_URL}/auth")
    pad = Path(tempfile.mkdtemp()) / "accounts.json"
    uit = ta.maak(
        "viewer-toegang",
        {"actoren": [{"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}]},
        beheer=beheer,
        pad=pad,
    )["lezer"]
    return uit["id"], uit["geheim"], lambda: ta.opruimen("viewer-toegang", beheer=beheer, pad=pad)


def inloggen_viewer(naam, wachtwoord):
    """Als een browser: / -> Keycloak-formulier -> callback -> terug op de kaart."""
    s = sessie()
    r = s.get(f"{BASE_URL}/", headers=HTML, timeout=TIMEOUT)
    assert "kc-form-login" in r.text, r.url
    actie = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
    r = s.post(
        actie, data={"username": naam, "password": wachtwoord, "credentialId": ""}, headers=HTML, timeout=TIMEOUT
    )
    return s, r


@pytest.fixture(scope="module")
def lezer_sessie():
    if not DICHT or not CONFIG.get("oidc"):
        pytest.skip("alleen bij VIEWER_TOEGANG=inloggen met Keycloak")
    naam, wachtwoord, opruimen = _lezer()
    try:
        s, r = inloggen_viewer(naam, wachtwoord)
        assert r.status_code == 200 and r.url == f"{BASE_URL}/", (r.status_code, r.url)
        yield s, naam
    finally:
        if opruimen:
            opruimen()


def test_dicht_lezer_ziet_kaart_met_naam(lezer_sessie):
    s, naam = lezer_sessie
    r = s.get(f"{BASE_URL}/", headers=HTML, timeout=TIMEOUT)
    assert r.status_code == 200 and 'id="map"' in r.text
    assert 'id="uitloggen"' in r.text and f">{naam}<" in r.text


@pytest.mark.parametrize("pad", DATA_API)
def test_dicht_lezer_api_200(lezer_sessie, pad):
    s, _ = lezer_sessie
    assert _status(pad, s) == 200, pad


def test_dicht_lezer_geen_beheer(lezer_sessie):
    s, _ = lezer_sessie
    assert _status("/api/admin/health", s) == 403


def test_dicht_uitloggen_terug_naar_kaart(lezer_sessie):
    s, _ = lezer_sessie
    uit = s.post(f"{BASE_URL}/api/admin/auth/logout?terug=/", timeout=TIMEOUT).json()
    assert "post_logout_redirect_uri=" + requests.utils.quote(f"{BASE_URL}/", safe="") in uit["uitlog_url"]
    s.get(uit["uitlog_url"], timeout=TIMEOUT, allow_redirects=False)
    assert _status("/api/kompas/configuraties", s) == 401
