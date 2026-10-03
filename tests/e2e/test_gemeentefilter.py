"""
E2E (#140): een opgeslagen gemeentefilter is zichtbaar en te wissen.

Scenario uit de bug: de chat zette het filter op Leeuwarden (0080) terwijl de sample
alleen buurten van Súdwest-Fryslân (1900) bevat. Het filter bleef in localStorage
staan en de kaart bleef leeg, zonder uitleg.

Zelfstandig: eigen browser-fixture, zodat de test ook draait zonder de gedeelde
conftest uit de E2E-suite. Draaien: zie tests/e2e/README.md (Playwright-container), bijv.

    OMNITWIN_BASE_URL=http://traefik pytest -m e2e tests/e2e/test_gemeentefilter.py
"""

import os
import re

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")

# Onboarding overslaan en een gemeentefilter klaarzetten, zoals na een klik in de chat
_INIT = """
(code) => {
  try {
    if (sessionStorage.getItem('e2e-140-init')) return;  // alleen bij de eerste paginalading
    sessionStorage.setItem('e2e-140-init', '1');
    localStorage.setItem('omnitwin_welcomed', '1');
    for (const k of ['omnitwin_tt_indicator', 'omnitwin_tt_buurt', 'omnitwin_tt_kompas', 'omnitwin_tt_ai']) {
      localStorage.setItem(k, '1');
    }
    localStorage.setItem('omnitwin-gemeente', code);
  } catch (e) {}
}
"""


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = p.chromium.launch(
            headless=os.environ.get("E2E_HEADED") != "1",
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
        )
        yield b
        b.close()


def _maak_leeg(route):
    """Kaartdata (geo en attributen) voor deze gemeente leeg teruggeven, zoals bij een gemeente zonder gebieden."""
    r = route.fetch()
    try:
        data = r.json()
    except ValueError:
        route.fulfill(response=r)
        return
    if isinstance(data, dict):
        for k in ("features", "data"):
            if isinstance(data.get(k), list):
                data[k] = []
    elif isinstance(data, list):
        data = []
    route.fulfill(response=r, json=data)


def _open_met_filter(browser, code, zonder_gebieden=False):
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="nl-NL")
    context.add_init_script(f"({_INIT})('{code}')")
    if zonder_gebieden:
        # Sinds #236 heeft elke Friese gemeente buurten (open data); een gemeente zonder gebieden
        # simuleren we door de kaartdata met dit filter leeg te maken. Getest wordt de uitleg en
        # het wissen in de frontend (#140), niet de data.
        context.route(re.compile(rf".*gemeente_code={code}.*"), _maak_leeg)
    page = context.new_page()
    page.set_default_timeout(20_000)
    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => window.state && window.state.deckgl"
        " && document.querySelectorAll('#gebiedstype-select option').length > 1",
        timeout=60_000,
    )
    return context, page


def _laad_buurten(page):
    knop = page.get_by_role("button", name="Kaartconfiguratie", exact=True)
    if "active" not in (knop.get_attribute("class") or ""):
        knop.click()
    page.locator("#gebiedstype-select").select_option(label="CBS Buurten")
    toon = page.locator("#toon-kaart-btn")
    expect(toon).to_be_enabled(timeout=30_000)
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok):
        toon.click()
    page.wait_for_function(
        "() => !!(window.state.currentData && Array.isArray(window.state.currentData.features))",
        timeout=30_000,
    )


def _aantal_gebieden(page) -> int:
    return page.evaluate("() => window.state.currentData ? window.state.currentData.features.length : -1")


def test_filter_zonder_gebieden_toont_melding_en_wissen_herstelt_kaart(browser):
    context, page = _open_met_filter(browser, "0080", zonder_gebieden=True)  # Leeuwarden, kaartdata leeg gemaakt
    try:
        chip = page.locator("#gemeente-filter-chip")
        expect(chip).to_be_visible()
        expect(chip).to_contain_text("Leeuwarden")

        _laad_buurten(page)
        assert _aantal_gebieden(page) == 0
        expect(chip).to_contain_text("Geen gebieden in gemeente Leeuwarden")

        with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok):
            page.get_by_role("button", name="Gemeentefilter Leeuwarden wissen").click()
        page.wait_for_function(
            "() => window.state.currentData && window.state.currentData.features.length > 0",
            timeout=30_000,
        )
        expect(chip).to_be_hidden()
        assert page.evaluate("() => localStorage.getItem('omnitwin-gemeente')") == ""
        assert page.locator("#gemeente-input").input_value() == "Alle gemeenten"

        # Na herladen blijft het filter weg
        page.reload(wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_function("() => window.state && window.state.deckgl", timeout=60_000)
        expect(page.locator("#gemeente-filter-chip")).to_be_hidden()
    finally:
        context.close()


def test_geldig_filter_toont_chip_met_gemeentenaam(browser):
    context, page = _open_met_filter(browser, "1900")
    try:
        _laad_buurten(page)
        assert _aantal_gebieden(page) > 0
        chip = page.locator("#gemeente-filter-chip")
        expect(chip).to_be_visible()
        expect(chip).to_contain_text("Gemeente: Súdwest-Fryslân")
        expect(chip).not_to_have_class(re.compile(r"\bleeg\b"))
    finally:
        context.close()
