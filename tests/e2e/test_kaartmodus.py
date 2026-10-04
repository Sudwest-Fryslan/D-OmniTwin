"""
TC-01-004 — Kaartmodus: percentielklasse, werkelijke waarde, uit (#255).

docs/testcases/01-kaartmodule/TC-01-004_kaartmodus.md
"""

from playwright.sync_api import expect

from e2e_helpers import BOLSWARD_ZUIDOOST, laad_buurtenkaart, open_paneel, traag_ms

INDICATOR = "Stedelijk hitte-eiland effect"  # use case hittestress


def kies_indicator(page, naam):
    """De indicatorkeuze is een eigen dropdown; de onderliggende select via de app zetten."""
    open_paneel(page, "Kaartconfiguratie")
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url
                              and "indicator_uuid" in r.url and r.ok):
        page.evaluate(
            """(naam) => { const s = document.getElementById('indicator-select');
                const o = [...s.options].find(o => o.text.startsWith(naam));
                if (!o) throw new Error('indicator ontbreekt: ' + naam);
                s.value = o.value; s.dispatchEvent(new Event('change'));
                document.getElementById('toon-kaart-btn').click(); }""",
            naam,
        )
    page.wait_for_function(
        "() => window.state.currentData && window.state.currentData.metadata"
        " && window.state.currentData.metadata.indicator_naam",
        timeout=traag_ms(),
    )


def kies_modus(page, label, verwacht_verzoek=True, percentiel=False):
    knop = page.locator("#kaart-modus label", has_text=label)
    if not verwacht_verzoek:
        knop.click()
        return
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok
                              and (("modus=percentiel" in r.url) == percentiel)):
        knop.click()


def test_tc_01_004_kaartmodus(app_page):
    """TC-01-004 stap 1-4: werkelijke waarde (bereik in de legenda), percentielklasse
    (8 klassen, klasse per buurt), uit (grijs, melding) en terug."""
    page = app_page
    laad_buurtenkaart(page)
    kies_indicator(page, INDICATOR)
    open_paneel(page, "Legenda")
    klassen = page.locator("#legenda-klassen li")

    # 1. Standaard: werkelijke waarde, klassen met bereik en eenheid
    expect(page.locator('#kaart-modus input[value="waarde"]')).to_be_checked()
    expect(page.locator("#legenda-modus-uit")).to_be_hidden()
    expect(klassen.first).to_be_visible()
    expect(page.locator("#legenda-klassen")).to_contain_text("°C")
    assert page.evaluate("() => window.state.currentData.metadata.modus") == "waarde"

    # 2. Percentielklasse: 8 klassen, elke buurt met data een klasse 1-8
    kies_modus(page, "Percentielklasse", percentiel=True)
    expect(klassen).to_have_count(8)
    expect(klassen.first).to_contain_text("klasse 1: 0–12,5% (ongunstigst)")
    expect(klassen.last).to_contain_text("klasse 8: 87,5–100% (gunstigst)")
    expect(page.locator("#color-gradient-bar")).to_be_hidden()
    klasse = page.evaluate(
        "(id) => window.state.currentData.features.find(f => (f.id || f.properties.id) === id).properties.klasse",
        BOLSWARD_ZUIDOOST,
    )
    assert isinstance(klasse, int) and 1 <= klasse <= 8, klasse

    # 3. Uit: geen klassen, wel een melding; de indicator blijft gekozen
    kies_modus(page, "Uit", verwacht_verzoek=False)
    expect(page.locator("#legenda-modus-uit")).to_be_visible()
    expect(klassen).to_have_count(0)
    assert page.evaluate("() => window.state.kaartModus") == "uit"
    assert page.evaluate("() => window.state.currentIndicator")

    # 4. Terug naar werkelijke waarde
    kies_modus(page, "Werkelijke waarde")
    expect(page.locator("#legenda-modus-uit")).to_be_hidden()
    expect(klassen.first).to_be_visible()
    expect(page.locator("#legenda-klassen")).to_have_attribute("data-modus", "waarde")

    assert page.console_fouten == [], "\n".join(page.console_fouten)
