"""
Integratietest inloggen in de beheeromgeving via Keycloak (#251, ADR 0008).

Tegen een draaiende stack met profiel keycloak en OIDC_ISSUER gezet. Maakt twee testgebruikers aan
in realm omnitwin (rol `beheerder` en rol `lezer`, via omnitwin.testaccounts, #223), en ruimt ze op.

- bearer-token met rol beheerder: 200 op een beheerroute; met lezer: 403; zonder token: 401;
- lokaal inloggen staat uit (tenzij LOKAAL_INLOGGEN=true: noodtoegang);
- de browserflow (authorization code + PKCE) met het inlogformulier van Keycloak, de sessie in het
  cookie, verversen na het verlopen van het access token, intrekken (gebruiker uitgeschakeld) en
  uitloggen bij Keycloak.

Overgeslagen zonder Keycloak/OIDC, zonder OMNITWIN_TESTACCOUNTS=1 of zonder toegang tot de admin-API
van Keycloak (KEYCLOAK_ADMIN_PASSWORD, of KEYCLOAK_ADMIN_CLIENT_ID/SECRET). Het verversen heeft de
database nodig (DATABASE_*, zoals test_admin_auth.py).

OMNITWIN_BASE_URL moet het adres zijn waarop Keycloak ook de issuer zet (OIDC_ISSUER zonder
/auth/realms/omnitwin): de browserflow volgt de redirects naar dat adres.

    OMNITWIN_BASE_URL=http://localhost OMNITWIN_TESTACCOUNTS=1 KEYCLOAK_ADMIN_PASSWORD=... \\
    OMNITWIN_TESTACCOUNTS_BESTAND=/tmp/accounts.json pytest -m integration tests/integration/test_beheer_keycloak.py
"""

import html
import os
import re
from http.cookiejar import DefaultCookiePolicy
from urllib.parse import urlsplit

import pytest
import requests

from omnitwin import testaccounts as ta

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "omnitwin")
TIMEOUT = 30
UC = "beheer-login"  # prefix uc-beheer-login-, opgeruimd met testaccounts.opruimen
BEHEERROUTE = f"{BASE_URL}/api/admin/health"

try:
    _config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT)
except requests.RequestException as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)
if _config.status_code != 200 or not _config.json().get("oidc"):
    pytest.skip("OIDC niet aan in de backend (OIDC_ISSUER, profiel keycloak)", allow_module_level=True)
CONFIG = _config.json()
if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1" or os.environ.get("OMNITWIN_OMGEVING", "").lower() == "productie":
    pytest.skip("testaccounts niet toegestaan (OMNITWIN_TESTACCOUNTS=1, niet in productie)", allow_module_level=True)
if not (os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")):
    pytest.skip("geen toegang tot de admin-API van Keycloak", allow_module_level=True)


@pytest.fixture(autouse=True, scope="module")
def _secure_cookies_op_localhost():
    """Keycloak zet zijn cookies met `Secure`. Een browser stuurt die ook naar http://localhost (een
    'potentially trustworthy origin'); requests niet. Op localhost doet de test het als een browser."""
    with pytest.MonkeyPatch.context() as mp:
        if urlsplit(BASE_URL).hostname in ("localhost", "127.0.0.1"):
            mp.setattr(DefaultCookiePolicy, "return_ok_secure", lambda self, cookie, request: True)
        yield


@pytest.fixture(scope="module")
def beheer():
    return ta.KeycloakBeheer(kc=f"{BASE_URL}/auth", realm_=REALM)


@pytest.fixture(scope="module")
def accounts(beheer, tmp_path_factory):
    pad = tmp_path_factory.mktemp("accounts") / "accounts.json"
    uc = {
        "actoren": [
            {"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]},
            {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]},
        ]
    }
    uit = ta.maak(UC, uc, beheer=beheer, pad=pad)
    yield uit
    ta.opruimen(UC, beheer=beheer, pad=pad)


def _token(account):
    url = f"{BASE_URL}/auth/realms/{REALM}/protocol/openid-connect/token"
    return ta.token(account, ta.loginclient(UC), url)


# ------------------------------------------------------------------ bearer-token op beheerroutes


def test_bearer_beheerder_200(accounts):
    r = requests.get(BEHEERROUTE, headers={"Authorization": f"Bearer {_token(accounts['beheerder'])}"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]


def test_bearer_lezer_403(accounts):
    r = requests.get(BEHEERROUTE, headers={"Authorization": f"Bearer {_token(accounts['lezer'])}"}, timeout=TIMEOUT)
    assert r.status_code == 403


def test_zonder_token_401():
    assert requests.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 401


def test_ongeldig_token_401():
    r = requests.get(BEHEERROUTE, headers={"Authorization": "Bearer abc.def.ghi"}, timeout=TIMEOUT)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Bearer")


# ------------------------------------------------------------------ lokaal inloggen


def test_lokaal_inloggen_uit_tenzij_noodtoegang():
    noodtoegang = os.environ.get("LOKAAL_INLOGGEN", "").lower() in ("1", "true", "ja", "yes", "on")
    assert CONFIG["lokaal"] is noodtoegang and CONFIG["noodtoegang"] is noodtoegang
    r = requests.post(
        f"{BASE_URL}/api/admin/auth/login", data={"username": "admin", "password": "onjuist"}, timeout=TIMEOUT
    )
    assert r.status_code == (401 if noodtoegang else 403)


def test_config_linkt_naar_keycloak():
    assert CONFIG["gebruikersbeheer_url"].endswith(f"/auth/admin/{REALM}/console/")
    assert CONFIG["account_url"].endswith(f"/auth/realms/{REALM}/account")


# ------------------------------------------------------------------ browserflow


def inloggen(account):
    """Als een browser: beheer -> Keycloak-formulier -> callback -> sessiecookie."""
    s = requests.Session()
    r = s.get(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/admin/indicatoren", timeout=TIMEOUT)
    assert r.status_code == 200 and "kc-form-login" in r.text, r.url
    actie = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
    r = s.post(
        actie, data={"username": account["id"], "password": account["geheim"], "credentialId": ""}, timeout=TIMEOUT
    )
    return s, r


@pytest.fixture
def beheerder_sessie(accounts):
    s, r = inloggen(accounts["beheerder"])
    assert r.url == f"{BASE_URL}/admin/indicatoren", r.url
    return s


def test_inloggen_als_beheerder(beheerder_sessie):
    s = beheerder_sessie
    assert s.cookies.get("session_token")
    me = s.get(f"{BASE_URL}/api/admin/auth/me", timeout=TIMEOUT).json()
    assert me["authenticated"] and me["user"]["is_admin"] is True and me["user"]["bron"] == "oidc"
    assert me["user"]["username"] == "uc-beheer-login-beheerder"
    assert s.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 200


def test_inloggen_als_lezer_geen_beheer(accounts):
    s, r = inloggen(accounts["lezer"])
    assert r.url == f"{BASE_URL}/admin/login"
    me = s.get(f"{BASE_URL}/api/admin/auth/me", timeout=TIMEOUT).json()
    assert me["authenticated"] and me["user"]["is_admin"] is False
    assert s.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 403


def test_uitloggen_bij_keycloak(beheerder_sessie):
    s = beheerder_sessie
    uit = s.post(f"{BASE_URL}/api/admin/auth/logout", timeout=TIMEOUT).json()
    assert uit["uitlog_url"].startswith(f"{BASE_URL}/auth/realms/{REALM}/protocol/openid-connect/logout?")
    assert "id_token_hint=" in uit["uitlog_url"]
    r = s.get(uit["uitlog_url"], timeout=TIMEOUT)
    assert r.url == f"{BASE_URL}/admin/login"
    assert s.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 401
    # Ook de sessie bij Keycloak is weg: opnieuw inloggen vraagt weer het formulier
    r = s.get(f"{BASE_URL}/api/admin/auth/oidc/login", timeout=TIMEOUT)
    assert "kc-form-login" in r.text


@pytest.fixture
def db():
    psycopg2 = pytest.importorskip("psycopg2")
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DATABASE_HOST", "localhost"),
            port=int(os.environ.get("DATABASE_PORT", 5432)),
            dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
            user=os.environ.get("DATABASE_USER", "omnitwin_user"),
            password=os.environ.get("DATABASE_PASSWORD", ""),
            connect_timeout=5,
        )
    except psycopg2.OperationalError as e:
        pytest.skip(f"database niet bereikbaar: {e}")
    conn.autocommit = True
    yield conn
    conn.close()


def _laat_token_verlopen(db, naam):
    with db.cursor() as cur:
        cur.execute(
            "UPDATE oidc_sessies SET token_verloopt = now() - interval '1 minute' "
            "WHERE gebruikersnaam = %s RETURNING token_verloopt",
            (naam,),
        )
        assert cur.rowcount >= 1


def test_verversen_en_intrekken(beheerder_sessie, beheer, db):
    s, naam = beheerder_sessie, "uc-beheer-login-beheerder"
    _laat_token_verlopen(db, naam)
    assert s.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 200  # ververst met het refresh token
    with db.cursor() as cur:
        # Alleen de sessie van dit verzoek is ververst; die van eerdere tests niet
        cur.execute("SELECT bool_or(token_verloopt > now()) FROM oidc_sessies WHERE gebruikersnaam = %s", (naam,))
        assert cur.fetchone()[0] is True
    # Gebruiker uitgeschakeld in Keycloak: bij het volgende verversen is de sessie weg
    gid = beheer._verzoek("GET", "/users", params={"username": naam, "exact": "true"}).json()[0]["id"]
    beheer._verzoek("PUT", f"/users/{gid}", json={"enabled": False})
    try:
        _laat_token_verlopen(db, naam)
        assert s.get(BEHEERROUTE, timeout=TIMEOUT).status_code == 401
    finally:
        beheer._verzoek("PUT", f"/users/{gid}", json={"enabled": True})
