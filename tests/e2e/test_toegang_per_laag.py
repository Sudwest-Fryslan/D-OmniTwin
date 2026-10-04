"""
Toegang per laag en bron (#254, use case rechten-per-laag, TC-07-024), in een echte browser: zonder
inloggen staan de interne voorbeeldlaag en -indicator (DEMODATA) niet in de lagenlijst en de
indicatorkeuze; na inloggen als lezer wel, met het label "intern".

Alleen met Keycloak aan, VIEWER_TOEGANG=open en het demo-account `gebruiker`/`gebruiker`
(OMNITWIN_OMGEVING=demo); anders overgeslagen. OMNITWIN_BASE_URL moet het publieke adres zijn (gelijk
aan de host in OIDC_ISSUER), dus niet http://traefik: draai de Playwright-container met
`--network host` en OMNITWIN_BASE_URL=http://localhost:<poort>.
"""

import os
import re

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
LAAG = "DEMODATA: interne voorbeeldlaag (buurten)"
INDICATOR = "DEMODATA: interne voorbeeldindicator"
OPEN_LAAG = "BAG Woonplaatsen"


def _stack():
    import requests
    try:
        config = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=30).json()
        open_ = requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=30,
                             allow_redirects=False).status_code == 200
        return config, open_
    except (requests.RequestException, ValueError):
        return {}, False


@pytest.fixture(scope="module")
def lezer():
    config, open_ = _stack()
    if not config.get("oidc") or not open_:
        pytest.skip("Keycloak niet aan of viewer dicht (VIEWER_TOEGANG=inloggen)")
    if not config.get("demo"):
        pytest.skip("geen demo-omgeving: geen lezer gebruiker/gebruiker")
    return {"id": "gebruiker", "geheim": "gebruiker"}


@pytest.fixture
def pagina(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="nl-NL")
    context.add_init_script("try { localStorage.setItem('omnitwin_welcomed', '1'); } catch (e) {}")
    page = context.new_page()
    page.set_default_timeout(60_000)
    yield page
    context.close()


def _lijsten(page):
    """Lagenlijst en indicatorkeuze (CBS Buurten) zoals de viewer ze toont: {laag: intern?}, {optie}."""
    # Pollen op een vast interval, niet per animatieframe: met software-WebGL komen frames soms
    # seconden na elkaar (zie e2e_helpers.py)
    page.wait_for_function(
        "() => Array.isArray(window.state && window.state.externeKaartlagen)"
        " && document.querySelectorAll('#gebiedstype-select option').length > 1", polling=250)
    page.evaluate("""() => { const s = document.getElementById('gebiedstype-select');
        const o = [...s.options].find(o => o.textContent.trim() === 'CBS Buurten');
        s.value = o.value; s.dispatchEvent(new Event('change', {bubbles: true})); }""")
    page.wait_for_function("() => document.querySelectorAll('#indicator-select option').length > 1", polling=250)
    lagen = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#externe-lagen-list .externe-laag-item')]
        .map(i => [i.querySelector('.layer-naam').textContent, !!i.querySelector('.label-intern')]))""")
    opties = page.evaluate("() => [...document.querySelectorAll('#indicator-select option')].map(o => o.textContent)")
    return lagen, opties


def test_anoniem_geen_interne_laag_of_indicator(lezer, pagina):
    pagina.goto(f"{BASE_URL}/")
    lagen, opties = _lijsten(pagina)
    assert OPEN_LAAG in lagen and not lagen[OPEN_LAAG], lagen
    assert LAAG not in lagen, lagen
    assert not any(INDICATOR in o for o in opties)
    assert not any(o.endswith("· intern") for o in opties)


def test_na_inloggen_interne_laag_en_indicator_met_label(lezer, pagina):
    pagina.goto(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/")
    pagina.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
    pagina.locator("#username").fill(lezer["id"])
    pagina.locator("#password").fill(lezer["geheim"])
    pagina.locator("#kc-login").click()
    pagina.wait_for_url(f"{BASE_URL}/")

    lagen, opties = _lijsten(pagina)
    assert lagen.get(LAAG) is True, f"interne laag met label ontbreekt: {lagen}"
    assert lagen.get(OPEN_LAAG) is False
    intern = [o for o in opties if INDICATOR in o]
    assert intern and intern[0].endswith("· intern"), intern
