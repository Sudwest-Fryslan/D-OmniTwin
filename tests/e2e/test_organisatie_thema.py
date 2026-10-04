"""
Thema wisselen in het beheerscherm (#253): na opslaan heeft de kopbalk van de viewer de kleuren van
het nieuwe thema (na een gewone herlaadactie), en het voorbeeld op de pagina wisselt live mee.

Inloggen als beheerder, in deze volgorde:
1. met Keycloak en testaccounts (OMNITWIN_TESTACCOUNTS=1 en KEYCLOAK_ADMIN_PASSWORD, zoals
   test_beheer_keycloak_login.py): een tijdelijk account met rol `beheerder`;
2. met Keycloak in een demo-omgeving (OMNITWIN_OMGEVING=demo): het demo-account `admin`/`admin`;
3. zonder Keycloak: lokaal met ADMIN_USER/ADMIN_PASSWORD (in demo `admin`/`admin`).
Met Keycloak moet OMNITWIN_BASE_URL het publieke adres zijn (de host uit OIDC_ISSUER).
De test zet de instelling na afloop terug (import van de export van vóór de test).
"""

import os
import re

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
UC = "organisatie-e2e"


def _config():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=30)
        return r.json() if r.status_code == 200 else {}
    except requests.RequestException:
        return {}


@pytest.fixture(scope="module")
def inlog(tmp_path_factory):
    """(soort, gebruikersnaam, wachtwoord) van een beheerder; soort = keycloak of lokaal."""
    config = _config()
    if not config:
        pytest.skip("stack niet bereikbaar")
    if config.get("oidc"):
        if os.environ.get("OMNITWIN_TESTACCOUNTS") == "1" and (
                os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")):
            from omnitwin import testaccounts as ta
            beheer = ta.KeycloakBeheer(kc=f"{BASE_URL}/auth")
            pad = tmp_path_factory.mktemp("accounts") / "accounts.json"
            uc = {"actoren": [{"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]}]}
            acc = ta.maak(UC, uc, beheer=beheer, pad=pad)["beheerder"]
            yield "keycloak", acc["id"], acc["geheim"]
            ta.opruimen(UC, beheer=beheer, pad=pad)
            return
        if config.get("demo"):
            yield "keycloak", "admin", "admin"
            return
        pytest.skip("Keycloak aan: testaccounts of een demo-omgeving nodig")
    wachtwoord = os.environ.get("ADMIN_PASSWORD") or ("admin" if config.get("demo") else None)
    if not wachtwoord:
        pytest.skip("ADMIN_PASSWORD onbekend")
    yield "lokaal", os.environ.get("ADMIN_USER", "admin"), wachtwoord


@pytest.fixture
def beheer(browser, inlog):
    """Ingelogde browsercontext in het beheerscherm; zet na afloop de organisatie terug."""
    soort, naam, wachtwoord = inlog
    context = browser.new_context(viewport={"width": 1400, "height": 1000}, locale="nl-NL", color_scheme="light")
    page = context.new_page()
    page.set_default_timeout(20_000)
    page.goto(f"{BASE_URL}/admin/login")
    if soort == "keycloak":
        page.get_by_role("link", name="Inloggen met Keycloak").click()
        page.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
        page.locator("#username").fill(naam)
        page.locator("#password").fill(wachtwoord)
        page.locator("#kc-login").click()
    else:
        page.get_by_label("Gebruikersnaam").fill(naam)
        page.get_by_label("Wachtwoord").fill(wachtwoord)
        page.get_by_role("button", name="Aanmelden").click()
    page.wait_for_url(f"{BASE_URL}/admin/dashboard")

    export = context.request.get(f"{BASE_URL}/api/organisatie/export")
    assert export.ok, export.text()
    origineel = export.json()
    yield page
    terug = context.request.post(f"{BASE_URL}/api/organisatie/import", data=origineel)
    assert terug.ok, terug.text()
    context.close()


def _rgb(hexkleur: str) -> str:
    h = hexkleur.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def _kopbalk(context) -> tuple[str, list]:
    """(achtergrond van de kopbalk, themabestanden) van de viewer, in licht (color_scheme light).

    In een eigen tabblad zonder de JavaScript van de viewer: de kopbalk komt uit de template en de
    CSS (themabestand van de server), en de kaart zou zonder GPU minutenlang CPU vragen."""
    viewer = context.new_page()
    try:
        viewer.route(re.compile(r"/static/(js|vendor)/.*\.js(\?.*)?$"), lambda route: route.abort())
        viewer.goto(f"{BASE_URL}/", wait_until="load")
        return viewer.evaluate("""() => [
            getComputedStyle(document.querySelector('header.header')).backgroundImage,
            [...document.querySelectorAll('link[href^="/static/css/themes/"]')].map(l => l.getAttribute('href'))]""")
    finally:
        viewer.close()


def test_thema_wisselen_kopbalk_viewer_verandert(beheer):
    from playwright.sync_api import expect

    page = beheer
    themas = page.context.request.get(f"{BASE_URL}/api/organisatie/themas").json()
    huidig = page.context.request.get(f"{BASE_URL}/api/organisatie").json()["thema"]
    nieuw = next(t for t in themas if t["naam"] != huidig)
    voor, _ = _kopbalk(page.context)

    page.goto(f"{BASE_URL}/admin/organisatie", wait_until="domcontentloaded")
    expect(page.get_by_role("radio", name=re.compile(huidig))).to_be_checked()
    page.get_by_role("radio", name=re.compile(nieuw["naam"])).check()
    # Live voorbeeld in licht en donker met de kopkleuren van het nieuwe thema
    for modus in ("licht", "donker"):
        start = nieuw["kleuren"][modus]["--d-omnitwin-header-background-color-start"]
        expect(page.get_by_test_id(f"voorbeeld-{modus}-kopbalk")).to_have_css(
            "background-image", re.compile(re.escape(_rgb(start))))
    page.get_by_role("button", name="Opslaan").click()
    expect(page.get_by_role("status").filter(has_text="Opgeslagen")).to_be_visible()

    na, bestanden = _kopbalk(page.context)
    start = nieuw["kleuren"]["licht"]["--d-omnitwin-header-background-color-start"]
    assert bestanden == [f'/static/css/themes/{nieuw["naam"]}.css']
    assert _rgb(start) in na, (na, start)
    assert na != voor

    # Het beheerscherm laadt na een herlaadactie ook het nieuwe themabestand
    page.goto(f"{BASE_URL}/admin/organisatie", wait_until="domcontentloaded")
    expect(page.locator(f'link[data-thema="{nieuw["naam"]}"]')).to_have_count(1)
