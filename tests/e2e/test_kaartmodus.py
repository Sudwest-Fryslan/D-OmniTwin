"""
TC-01-004 — Kaartmodus: percentielklasse, label A–E (#256), werkelijke waarde, uit (#255).
TC-02-003 — Klimaat Kompas met labels A–E (#256).

docs/testcases/01-kaartmodule/TC-01-004_kaartmodus.md,
docs/testcases/02-kompas-detail/TC-02-003_klimaat-labels.md
"""

from playwright.sync_api import expect

from e2e_helpers import (
    BOLSWARD_ZUIDOOST, TRAAG_MS, klik, laad_buurtenkaart, open_kompas, open_paneel, selecteer_buurt_via_app,
    traag_ms, wacht_op_selectie,
)

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
    # klik(): pas klikken als de renderer weer vlot tekent (na het hertekenen van de kaart, #212)
    if not verwacht_verzoek:
        klik(page, knop)
        return
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok
                              and (("modus=percentiel" in r.url) == percentiel)):
        klik(page, knop)


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


def test_tc_01_004_label_ae(app_page):
    """TC-01-004 stap 5 (#256): kaartmodus Label A–E, legenda A–E met de melding
    'voorlopige drempels (kwintielen)', label per buurt in de data."""
    page = app_page
    laad_buurtenkaart(page)
    kies_indicator(page, INDICATOR)
    open_paneel(page, "Legenda")
    klassen = page.locator("#legenda-klassen li")

    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok
                              and "modus=label" in r.url, timeout=TRAAG_MS):
        page.locator("#kaart-modus label", has_text="Label A–E").click()
    expect(klassen).to_have_count(5)
    expect(klassen.first).to_contain_text("label A (gunstigst)")
    expect(klassen.last).to_contain_text("label E (ongunstigst)")
    expect(page.locator("#legenda-klassen")).to_have_attribute("data-modus", "label")
    expect(page.locator("#legenda-hints .legenda-melding")).to_contain_text("Voorlopige drempels (kwintielen)")
    label = page.evaluate(
        "(id) => window.state.currentData.features.find(f => (f.id || f.properties.id) === id).properties.label",
        BOLSWARD_ZUIDOOST,
    )
    assert label in ("A", "B", "C", "D", "E"), label

    # terug naar werkelijke waarde (voor de volgende test in dezelfde browser)
    kies_modus(page, "Werkelijke waarde")
    expect(page.locator("#legenda-klassen")).to_have_attribute("data-modus", "waarde")
    assert page.console_fouten == [], "\n".join(page.console_fouten)


def test_tc_02_003_klimaat_kompas_labels(app_page):
    """TC-02-003 (#256): het Klimaat Kompas is gevuld en toont labels A–E per indicator en
    thema, met een legenda en de melding 'voorlopige drempels (kwintielen)'."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, BOLSWARD_ZUIDOOST)
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST])
    open_kompas(page, "Indicatordekking")

    with page.expect_response(lambda r: "/api/kompas/" in r.url and f"/gebied/{BOLSWARD_ZUIDOOST}" in r.url and r.ok,
                              timeout=TRAAG_MS):
        page.locator("#custom-select-trigger").click()
        page.locator("#custom-options .custom-option", has_text="Klimaat Kompas").click()
    info = page.locator("#kompas-info")
    expect(info).to_contain_text("Configuratie: Klimaat Kompas", timeout=TRAAG_MS)
    expect(info).to_contain_text("Kleur: label A–E")
    expect(info.locator(".kompas-labels li")).to_have_count(5)
    expect(info.locator(".kompas-label-melding")).to_contain_text("Voorlopige drempels (kwintielen)")
    page.wait_for_function(
        "() => document.querySelectorAll('#kompas-container path.kompas-arc-path').length >= 6"
    )
    labels = page.evaluate(
        "() => window.kompasViz.root.descendants().filter(d => d.data.label)"
        ".map(d => [d.data.type, d.data.name, d.data.label])"
    )
    themas = {naam for soort, naam, _ in labels if soort == "thema"}
    assert "Hittestress" in themas, labels
    assert any(soort == "indicator" for soort, _, _ in labels), labels
    assert all(lbl in ("A", "B", "C", "D", "E") for _, _, lbl in labels)
    # het label staat ook als letter in het zonnediagram ('B · Hittestress')
    assert page.evaluate(
        "() => [...document.querySelectorAll('#kompas-container text')]"
        r".some(t => /^[A-E]\s*·/.test(t.textContent.trim()))"
    )

    assert page.console_fouten == [], "\n".join(page.console_fouten)
