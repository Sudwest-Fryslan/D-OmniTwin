"""
Indicatorpaneel, CSV-export en favorieten in de browser (#258).

1. Anoniem: indicator op de kaart, twee buurten selecteren, tabblad Indicator: eenheid, bron,
   gemeentegemiddelde en een staafdiagram met twee staven; CSV downloaden (BOM, puntkomma, komma).
   Geen favorietenblok zonder login.
2. Ingelogd als demo-account `gebruiker` (OMNITWIN_OMGEVING=demo, Keycloak aan): selectie bewaren als
   favoriet, pagina opnieuw laden, favoriet staat er en selecteert dezelfde buurten; de kaartpositie
   komt terug. Zonder demo-omgeving met Keycloak overgeslagen. OMNITWIN_BASE_URL moet dan het publieke
   adres zijn (de host uit OIDC_ISSUER).
"""

import re

import pytest
from playwright.sync_api import expect

from e2e_helpers import (
    BOLSWARD_ZUIDOOST,
    TRAAG_MS,
    WORKUM,
    klik,
    klik_en_bevestig,
    laad_buurtenkaart,
    open_paneel,
    selecteer_buurt_via_app,
    wacht_op_selectie,
)

BASE_URL = __import__("os").environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
INDICATOR = "Stedelijk hitte-eiland effect"  # use case hittestress
FAVORIET = "E2E Bolsward en Workum"


def kies_indicator(page, naam):
    open_paneel(page, "Kaartconfiguratie")
    with page.expect_response(lambda r: "/api/gebiedsmonitor/indicatorpaneel" in r.url and r.ok, timeout=TRAAG_MS):
        page.evaluate(
            """(naam) => { const s = document.getElementById('indicator-select');
                const o = [...s.options].find(o => o.text.startsWith(naam));
                if (!o) throw new Error('indicator ontbreekt: ' + naam);
                s.value = o.value; s.dispatchEvent(new Event('change'));
                document.getElementById('toon-kaart-btn').click(); }""",
            naam,
        )


def selecteer_twee(page):
    """Eerst de ene buurt (en wachten tot de klik verwerkt is), dan met Shift de tweede."""
    selecteer_buurt_via_app(page, BOLSWARD_ZUIDOOST)
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST])
    with page.expect_response(
        lambda r: "/api/gebiedsmonitor/indicatorpaneel" in r.url and "gebied_ids=" in r.url and "%2C" in r.url and r.ok,
        timeout=TRAAG_MS,
    ):
        selecteer_buurt_via_app(page, WORKUM, shift=True)
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST, WORKUM])


def test_indicatorpaneel_staafdiagram_en_csv(app_page, tmp_path):
    page = app_page
    laad_buurtenkaart(page)
    kies_indicator(page, INDICATOR)
    selecteer_twee(page)
    open_paneel(page, "Indicator")

    expect(page.locator("#ip-naam")).to_contain_text(INDICATOR)
    expect(page.locator("#ip-eenheid")).to_have_text("°C")
    expect(page.locator("#ip-bronnen li").first).to_be_visible()
    expect(page.locator("#ip-gemiddelde")).to_contain_text("Súdwest-Fryslân")
    expect(page.locator("#ip-grafiek")).to_be_visible()
    staven = page.evaluate("""() => { const c = Chart.getChart(document.getElementById('ip-grafiek'));
        return { labels: c.data.labels, waarden: c.data.datasets[0].data, gem: c.data.datasets[1].data }; }""")
    assert len(staven["labels"]) == 2 and all(isinstance(w, (int, float)) for w in staven["waarden"]), staven
    assert all(isinstance(w, (int, float)) for w in staven["gem"]), staven

    # Zonder login geen favorietenblok
    expect(page.locator("#mijn-favorieten")).to_be_hidden()

    # CSV
    href = page.locator("#ip-csv").get_attribute("href")
    assert "indicatorpaneel.csv" in href and "gebied_ids=" in href
    with page.expect_download() as download:
        klik(page, page.locator("#ip-csv"))
    pad = tmp_path / "paneel.csv"
    download.value.save_as(pad)
    inhoud = pad.read_bytes()
    assert inhoud[:3] == b"\xef\xbb\xbf"
    regels = inhoud.decode("utf-8-sig").splitlines()
    assert regels[0] == "gebied-code;gebied-naam;indicator;jaar;waarde;eenheid;bron;status"
    bolsward = next(r for r in regels if r.startswith(BOLSWARD_ZUIDOOST + ";")).split(";")
    assert bolsward[7] == "gemeten" and re.fullmatch(r"-?\d+(,\d+)?", bolsward[4]), bolsward
    assert any(r.endswith(";gemeentegemiddelde") for r in regels)
    assert download.value.suggested_filename.startswith("indicator-")

    assert page.console_fouten == [], "\n".join(page.console_fouten)


# ── Favorieten na inloggen ──────────────────────────────────────────────────

_ZONDER_ONBOARDING = """
try {
  localStorage.setItem('omnitwin_welcomed', '1');
  for (const k of ['omnitwin_tt_indicator', 'omnitwin_tt_buurt', 'omnitwin_tt_kompas', 'omnitwin_tt_ai'])
    localStorage.setItem(k, '1');
  localStorage.setItem('omnitwin-gemeente', '1900');
} catch (e) {}
"""


def _demo_met_keycloak():
    import requests

    try:
        c = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=30).json()
    except (requests.RequestException, ValueError):
        return False
    return bool(c.get("oidc") and c.get("demo"))


def _klaar(page):
    page.wait_for_function(
        "() => window.state && window.state.deckgl && window.kompasViz && window.kompasViz.currentConfigId"
        " && document.querySelectorAll('#gebiedstype-select option').length > 1",
        timeout=60_000,
    )


@pytest.fixture
def ingelogd(browser):
    if not _demo_met_keycloak():
        pytest.skip("alleen met Keycloak in de demo-omgeving (account gebruiker/gebruiker)")
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="nl-NL")
    context.add_init_script(_ZONDER_ONBOARDING)
    page = context.new_page()
    page.set_default_timeout(30_000)
    page.goto(f"{BASE_URL}/api/admin/auth/oidc/login?terug=/", wait_until="domcontentloaded")
    page.wait_for_url(re.compile(r"/auth/realms/.+/protocol/openid-connect/auth"))
    page.locator("#username").fill("gebruiker")
    page.locator("#password").fill("gebruiker")
    page.locator("#kc-login").click()
    page.wait_for_url(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=TRAAG_MS)
    _klaar(page)
    yield page
    # Opruimen: favoriet weg (ook als de test halverwege faalde)
    page.evaluate(
        """async (naam) => {
        const r = await fetch('/api/mijn/favorieten'); if (!r.ok) return;
        for (const f of (await r.json()).favorieten)
            if (f.naam === naam) await fetch('/api/mijn/favorieten/' + f.id, { method: 'DELETE' }); }""",
        FAVORIET,
    )
    context.close()


def test_favoriet_bewaren_na_inloggen(ingelogd):
    page = ingelogd
    expect(page.locator("#account-naam")).to_have_text("gebruiker")
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, BOLSWARD_ZUIDOOST)
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST])
    selecteer_buurt_via_app(page, WORKUM, shift=True)
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST, WORKUM])

    # Knop in de selectiebalk opent Info & Start met het naamveld
    klik(page, page.locator("#selection-bewaar-btn"))
    expect(page.locator("#mijn-favorieten")).to_be_visible()
    page.locator("#mijn-favoriet-naam").fill(FAVORIET)
    klik_en_bevestig(
        page,
        page.locator("#mijn-bewaar-selectie"),
        f"() => document.getElementById('mijn-favorieten-lijst').textContent.includes({FAVORIET!r})",
        "Bewaar selectie",
    )
    expect(page.locator("#mijn-favorieten-lijst")).to_contain_text(f"{FAVORIET} (2)")

    # Kaartpositie bewaren (anders bij het verlaten van de pagina)
    page.evaluate("""() => { window.zetKaartPositie({ longitude: 5.52, latitude: 53.06, zoom: 12.5, pitch: 0, bearing: 0 });
        window.mijnVoorkeuren.bewaarPositie(false); }""")
    page.wait_for_timeout(1000)

    # Opnieuw laden: favoriet staat er nog, de kaart opent op de bewaarde positie
    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=TRAAG_MS)  # software-WebGL: traag
    _klaar(page)
    page.wait_for_function(
        "() => Math.abs(window.state.currentViewState.zoom - 12.5) < 0.01"
        " && Math.abs(window.state.currentViewState.longitude - 5.52) < 1e-4",
        timeout=TRAAG_MS,
    )
    open_paneel(page, "Info & Start")
    knop = page.locator(".mijn-favoriet-open", has_text=FAVORIET)
    klik_en_bevestig(page, knop, "() => window.state.selectedGebiedIds.size === 2", f"favoriet {FAVORIET}")
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST, WORKUM])

    # Verwijderen
    klik(page, page.get_by_role("button", name=f"Favoriet {FAVORIET} verwijderen"))
    expect(page.locator(".mijn-favoriet-open", has_text=FAVORIET)).to_have_count(0)
