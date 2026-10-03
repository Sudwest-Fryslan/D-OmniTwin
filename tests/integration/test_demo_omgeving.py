"""
Integratietest demo-omgeving (#245) tegen een draaiende stack met Keycloak (profiel keycloak, OIDC_ISSUER).

- `OMNITWIN_OMGEVING=demo`: inloggen via het Keycloak-formulier met `admin`/`admin` geeft beheerrechten
  in de beheeromgeving, `gebruiker`/`gebruiker` niet (alleen lezer); de rollen kloppen; de demobalk
  staat in de viewer en `GET /api/admin/auth/config` meldt `demo`.
- Elke andere omgeving: `admin`/`admin` en `gebruiker`/`gebruiker` werken niet in Keycloak, en er is
  geen demobalk.

Met KEYCLOAK_ADMIN_PASSWORD controleert hij de rollen ook via de admin-API.

    OMNITWIN_BASE_URL=http://localhost:8120 pytest -m integration tests/integration/test_demo_omgeving.py
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

try:
    _config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT)
except requests.RequestException as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)
CONFIG = _config.json() if _config.status_code == 200 else {}
if not CONFIG.get("oidc"):
    pytest.skip("OIDC niet aan in de backend (OIDC_ISSUER, profiel keycloak)", allow_module_level=True)
DEMO = bool(CONFIG.get("demo"))


def inloggen_beheer(naam, wachtwoord):
    """Als een browser: beheer -> Keycloak-formulier. Geeft (sessie, laatste antwoord)."""
    s = sessie()
    r = s.get(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/admin/dashboard", timeout=TIMEOUT)
    assert "kc-form-login" in r.text, r.url
    actie = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', r.text).group(1))
    r = s.post(actie, data={"username": naam, "password": wachtwoord, "credentialId": ""}, timeout=TIMEOUT)
    return s, r


def _me(s):
    return s.get(f"{BASE_URL}/api/admin/auth/me", timeout=TIMEOUT).json()


@pytest.mark.skipif(not DEMO, reason="alleen bij OMNITWIN_OMGEVING=demo")
def test_demo_admin_is_beheerder():
    s, r = inloggen_beheer("admin", "admin")
    assert r.url == f"{BASE_URL}/admin/dashboard", r.url
    me = _me(s)
    assert me["authenticated"] and me["user"]["is_admin"] is True and me["user"]["username"] == "admin"
    assert s.get(f"{BASE_URL}/api/admin/health", timeout=TIMEOUT).status_code == 200


@pytest.mark.skipif(not DEMO, reason="alleen bij OMNITWIN_OMGEVING=demo")
def test_demo_gebruiker_is_lezer():
    s, r = inloggen_beheer("gebruiker", "gebruiker")
    assert r.url == f"{BASE_URL}/admin/login", r.url   # ingelogd, maar geen beheer
    me = _me(s)
    assert me["authenticated"] and me["user"]["is_admin"] is False
    assert s.get(f"{BASE_URL}/api/admin/health", timeout=TIMEOUT).status_code == 403


@pytest.mark.skipif(not DEMO, reason="alleen bij OMNITWIN_OMGEVING=demo")
def test_demo_balk_in_viewer():
    r = requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=TIMEOUT, allow_redirects=False)
    if r.status_code == 302:   # VIEWER_TOEGANG=inloggen
        s, _ = inloggen_beheer("gebruiker", "gebruiker")
        r = s.get(f"{BASE_URL}/", timeout=TIMEOUT)
    assert "Demo-omgeving — standaardwachtwoorden, niet voor productie" in r.text


@pytest.mark.skipif(not DEMO or not os.environ.get("KEYCLOAK_ADMIN_PASSWORD"),
                    reason="alleen bij demo met toegang tot de admin-API van Keycloak")
def test_demo_rollen_in_keycloak():
    from omnitwin import omgeving
    from omnitwin.testaccounts import KeycloakBeheer
    beheer = KeycloakBeheer(kc=f"{BASE_URL}/auth")
    for naam, (_, rollen) in omgeving.DEMO_ACCOUNTS.items():
        g = beheer._verzoek("GET", "/users", params={"username": naam, "exact": "true"}).json()[0]
        assert omgeving.is_demo_account(g), naam
        echt = {r["name"] for r in beheer._verzoek("GET", f"/users/{g['id']}/role-mappings/realm/composite").json()}
        assert set(rollen) <= echt, (naam, echt)
        if naam == "gebruiker":
            assert not {"beheerder", "gebruikersbeheerder"} & echt
    assert beheer._verzoek("GET", "").json()["passwordPolicy"] == omgeving.DEMO_BELEID


@pytest.mark.skipif(DEMO, reason="alleen buiten de demo-omgeving")
@pytest.mark.parametrize("naam", ["admin", "gebruiker"])
def test_buiten_demo_geen_standaardaccounts(naam):
    s, r = inloggen_beheer(naam, naam)
    assert "kc-form-login" in r.text, r.url      # formulier opnieuw: ongeldige inloggegevens
    assert not s.cookies.get("session_token")
    assert _me(s)["authenticated"] is False


@pytest.mark.skipif(DEMO, reason="alleen buiten de demo-omgeving")
def test_buiten_demo_geen_demobalk():
    r = requests.get(f"{BASE_URL}/admin/login", timeout=TIMEOUT)
    assert r.status_code == 200
    assert CONFIG.get("demo") is False
    v = requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=TIMEOUT, allow_redirects=False)
    if v.status_code == 200:
        assert "Demo-omgeving" not in v.text
