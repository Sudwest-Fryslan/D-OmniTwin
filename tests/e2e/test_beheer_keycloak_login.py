"""
Inloggen in de beheeromgeving via het formulier van Keycloak (#251), in een echte browser.

Alleen met Keycloak aan (profiel keycloak, OIDC_ISSUER) en testaccounts toegestaan
(OMNITWIN_TESTACCOUNTS=1 en KEYCLOAK_ADMIN_PASSWORD, zoals tests/integration/test_beheer_keycloak.py);
anders overgeslagen. OMNITWIN_BASE_URL moet het publieke adres zijn (gelijk aan de host in
OIDC_ISSUER), want de browser volgt de redirects naar Keycloak.
"""

import os
import re

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
UC = "beheer-e2e"


def _config():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=30)
        return r.json() if r.status_code == 200 else {}
    except requests.RequestException:
        return {}


@pytest.fixture(scope="module")
def beheerder(tmp_path_factory):
    if not _config().get("oidc"):
        pytest.skip("Keycloak/OIDC niet aan in de backend")
    if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1" or not (
            os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")):
        pytest.skip("testaccounts niet toegestaan (OMNITWIN_TESTACCOUNTS=1 en toegang tot de admin-API)")
    from omnitwin import testaccounts as ta
    beheer = ta.KeycloakBeheer(kc=f"{BASE_URL}/auth")
    pad = tmp_path_factory.mktemp("accounts") / "accounts.json"
    uc = {"actoren": [{"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]}]}
    yield ta.maak(UC, uc, beheer=beheer, pad=pad)["beheerder"]
    ta.opruimen(UC, beheer=beheer, pad=pad)


@pytest.fixture
def pagina(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="nl-NL")
    page = context.new_page()
    page.set_default_timeout(20_000)
    yield page
    context.close()


def test_inloggen_en_uitloggen_via_keycloak(beheerder, pagina):
    from playwright.sync_api import expect

    pagina.goto(f"{BASE_URL}/admin/login")
    pagina.get_by_role("link", name="Inloggen met Keycloak").click()

    # Het formulier van Keycloak (realm omnitwin)
    pagina.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
    pagina.locator("#username").fill(beheerder["id"])
    pagina.locator("#password").fill(beheerder["geheim"])
    pagina.locator("#kc-login").click()

    pagina.wait_for_url(f"{BASE_URL}/admin/dashboard")
    knop = pagina.get_by_role("button", name=re.compile(beheerder["id"]))
    expect(knop).to_be_visible()

    knop.click()
    expect(pagina.get_by_role("link", name=re.compile("Gebruikers en rollen beheren"))).to_have_attribute(
        "href", re.compile(r"/auth/admin/omnitwin/console/$"))
    pagina.get_by_role("button", name="Uitloggen").click()

    # Uitgelogd bij Keycloak en terug op de inlogpagina
    pagina.wait_for_url(f"{BASE_URL}/admin/login")
    expect(pagina.get_by_role("link", name="Inloggen met Keycloak")).to_be_visible()
    pagina.get_by_role("link", name="Inloggen met Keycloak").click()
    expect(pagina.locator("#kc-login")).to_be_visible()
