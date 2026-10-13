"""
Viewer achter Keycloak-login (#266), in een echte browser: bij VIEWER_TOEGANG=inloggen stuurt de kaart
door naar het formulier van Keycloak; na inloggen als lezer zie je de kaart en je naam in de kop.

Alleen als de stack dicht staat (anoniem `/` geeft een redirect) en er een lezer is: het demo-account
`gebruiker`/`gebruiker` (OMNITWIN_OMGEVING=demo) of een testaccount (OMNITWIN_TESTACCOUNTS=1 en
KEYCLOAK_ADMIN_PASSWORD); anders overgeslagen. Met de standaard (open) slaat hij zichzelf over.
OMNITWIN_BASE_URL moet het publieke adres zijn (gelijk aan de host in OIDC_ISSUER).
"""

import os
import re

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
UC = "viewer-e2e"


def _stack():
    import requests

    try:
        config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=30).json()
        dicht = (
            requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=30, allow_redirects=False).status_code
            == 302
        )
        return config, dicht
    except (requests.RequestException, ValueError):
        return {}, False


@pytest.fixture(scope="module")
def lezer(tmp_path_factory):
    config, dicht = _stack()
    if not config.get("oidc") or not dicht:
        pytest.skip("viewer niet dicht (VIEWER_TOEGANG=open) of Keycloak niet aan")
    if config.get("demo"):
        yield {"id": "gebruiker", "geheim": "gebruiker"}
        return
    if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1" or not (
        os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")
    ):
        pytest.skip("geen lezer: geen demo-omgeving en geen testaccounts")
    from omnitwin import testaccounts as ta

    beheer = ta.KeycloakBeheer(kc=f"{BASE_URL}/auth")
    pad = tmp_path_factory.mktemp("accounts") / "accounts.json"
    uc = {"actoren": [{"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}]}
    yield ta.maak(UC, uc, beheer=beheer, pad=pad)["lezer"]
    ta.opruimen(UC, beheer=beheer, pad=pad)


@pytest.fixture
def pagina(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="nl-NL")
    context.add_init_script("try { localStorage.setItem('omnitwin_welcomed', '1'); } catch (e) {}")
    page = context.new_page()
    page.set_default_timeout(30_000)
    yield page
    context.close()


def test_inloggen_via_keycloak_en_kaart_zien(lezer, pagina):
    from playwright.sync_api import expect

    pagina.goto(f"{BASE_URL}/")
    # Zonder sessie: het formulier van Keycloak
    pagina.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
    pagina.locator("#username").fill(lezer["id"])
    pagina.locator("#password").fill(lezer["geheim"])
    pagina.locator("#kc-login").click()

    # Terug op de kaart, met de gebruikersnaam en uitloggen in de kop
    pagina.wait_for_url(f"{BASE_URL}/")
    expect(pagina.locator("#account-naam")).to_have_text(lezer["id"])
    expect(pagina.locator("#uitloggen")).to_be_visible()
    expect(pagina.locator("#map canvas").first).to_be_visible()
    # De kaart haalt data op: de gebiedstypes uit PostgREST (/api/data, via forwardAuth)
    antwoord = pagina.request.get(f"{BASE_URL}/api/data/gebiedstypes?limit=1")
    assert antwoord.status == 200

    # Uitloggen: via Keycloak terug naar de kaart, en die vraagt weer het formulier
    pagina.locator("#uitloggen").click()
    pagina.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
    expect(pagina.locator("#kc-login")).to_be_visible()
