"""
TC-01-00x — Kaartmodule (docs/testcases/01-kaartmodule).

Afwijking van de testdata: de sample dataset bevat geen Makkum. Waar de testcase
Makkum noemt, gebruiken we Workum/Koudum/Hindeloopen (ook IJsselmeerkust).
"""

import pytest
from playwright.sync_api import expect

from e2e_helpers import (
    HINDELOOPEN, KOUDUM, WORKUM,
    klik_buurt_op_kaart, laad_buurtenkaart, open_kompas, open_paneel, selecteer_buurt_via_app,
    selectie, selectie_overlay_aanwezig, wacht_op_selectie, zoom_kaart,
)


# ── TC-01-001 Enkelvoudige gebiedsselectie ───────────────────────────────────

def test_tc_01_001_gebiedsselectie(app_page):
    """TC-01-001 stap 1-5: kaart laden, buurt aanklikken (echte canvasklik), badge en
    details, tweede klik vervangt de selectie, deselecteren via de badge, geen consolefouten."""
    page = app_page

    # 1. Kaart laadt volledig
    laad_buurtenkaart(page)
    expect(page.locator("#map canvas").first).to_be_visible()

    # 2. Klik op een buurtpolygoon → highlight (gouden selectierand)
    klik_buurt_op_kaart(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    assert selectie_overlay_aanwezig(page), "geen selectie-highlight op de kaart"

    # 3. Selectiebadge en gebiedsdetails tonen de naam
    badge = page.locator("#selection-badge")
    expect(badge).to_be_visible()
    expect(badge).to_contain_text("Workum")
    expect(page.locator("#gebied-details")).to_contain_text("Workum")
    expect(page.locator("#gebied-details")).to_contain_text("Indicatoren")

    # 4. Klik op een tweede gebied (normale klik) → vervangt de selectie
    klik_buurt_op_kaart(page, KOUDUM)
    wacht_op_selectie(page, [KOUDUM])
    expect(badge).to_contain_text("Koudum")
    expect(page.locator("#gebied-details")).to_contain_text("Koudum")

    # 5. Deselecteren via de badge → kaart neutraal
    badge.get_by_text("✕", exact=True).click()  # midden van de badge is de knop "3D Panden"
    wacht_op_selectie(page, [])
    expect(badge).to_be_hidden()
    assert not selectie_overlay_aanwezig(page)
    expect(page.locator("#gebied-empty-state")).to_be_visible()

    assert page.console_fouten == [], "\n".join(page.console_fouten)


# ── TC-01-002 Meervoudige selectie ───────────────────────────────────────────

def test_tc_01_002a_meervoudige_klikselectie(app_page):
    """TC-01-002 A stap 1-7: Shift+klik op drie kernen, overzicht in badge, Kompas
    toont het gemiddelde, één gebied deselecteren, alles wissen. Controleert ook
    dat de selectie stabiel blijft bij zoomen."""
    page = app_page
    laad_buurtenkaart(page)

    # 1-3. Shift+klik voegt toe (geen camerasprong bij multi-select)
    klik_buurt_op_kaart(page, WORKUM, shift=True)
    wacht_op_selectie(page, [WORKUM])
    klik_buurt_op_kaart(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM])
    klik_buurt_op_kaart(page, HINDELOOPEN, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM, HINDELOOPEN])

    # 4. Selectie-indicator toont alle drie
    badge = page.locator("#selection-badge")
    expect(badge).to_contain_text("3 gebieden geselecteerd")
    open_paneel(page, "Rapport")
    rapport = page.locator("#rapport-gebied-info")
    for naam in ("Workum", "Koudum", "Hindeloopen"):
        expect(rapport).to_contain_text(naam)

    # Stabiel bij zoomen (acceptatiecriterium)
    zoom_kaart(page, 300)
    assert sorted(selectie(page)) == sorted([WORKUM, KOUDUM, HINDELOOPEN])

    # 5. Kompas: benchmark/gemiddelde van de drie gebieden
    open_kompas(page, "Gemiddelde van 3 gebieden")

    # 6. Eén gebied deselecteren (Shift+klik op een geselecteerd gebied)
    selecteer_buurt_via_app(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, HINDELOOPEN])
    expect(badge).to_contain_text("2 gebieden geselecteerd")
    expect(page.locator("#kompas-info")).to_contain_text("Gemiddelde van 2 gebieden")

    # 7. Hele selectie wissen
    badge.get_by_text("✕", exact=True).click()  # midden van de badge is de knop "3D Panden"
    wacht_op_selectie(page, [])
    expect(badge).to_be_hidden()
    assert not selectie_overlay_aanwezig(page)


@pytest.mark.skip(reason="TC-01-002 B: polygoon-/lassoselectie is nog niet geïmplementeerd (geen tekenmodus in de UI)")
def test_tc_01_002b_polygoonselectie():
    """TC-01-002 B: selectie via polygoontekening."""


# ── TC-01-003 Alternatieve gebiedslagen ──────────────────────────────────────

@pytest.mark.skip(reason="TC-01-003 A: omgevingsvisie-deelgebieden zitten niet in de sample dataset "
                         "en zijn geen externe kaartlaag in de sample-stuurdata")
def test_tc_01_003a_omgevingsvisie():
    """TC-01-003 A: Omgevingsvisie SWF als selectieframe."""


def test_tc_01_003b_bag_woonplaatsen(app_page):
    """TC-01-003 B stap 1-5: BAG-woonplaatsen (externe WFS-laag van PDOK) als selectieframe.
    Woonplaats Workum en Koudum selecteren hun CBS-buurten; het Kompas toont de
    vergelijking; laag uitzetten laat de selectie intact.
    Vereist internettoegang naar service.pdok.nl (anders skip)."""
    page = app_page
    laad_buurtenkaart(page)

    # 1. Kaartlagen → BAG Woonplaatsen aanzetten
    open_paneel(page, "Kaartlagen")
    laag = page.evaluate("() => window.state.externeKaartlagen.find(l => l.naam === 'BAG Woonplaatsen')")
    assert laag, "externe kaartlaag 'BAG Woonplaatsen' ontbreekt in de sample-stuurdata"
    toggle = page.locator(f"#toggle-externe-laag-{laag['id']}")
    with page.expect_response(lambda r: f"/api/externe-lagen/{laag['id']}/features" in r.url,
                              timeout=120_000) as resp:
        page.locator(f"label:has(#toggle-externe-laag-{laag['id']})").click()
    if not resp.value.ok:
        pytest.skip(f"PDOK WFS niet bereikbaar vanuit de backend (HTTP {resp.value.status})")
    expect(toggle).to_be_checked()
    page.wait_for_function(
        "(id) => window.state.deckgl.props.layers.some(l => l && l.id === `externe-laag-${id}`)",
        arg=laag["id"],
    )

    # 2-4. Woonplaats Workum en daarna Koudum selecteren (onClick van de externe laag)
    for naam in ("Workum", "Koudum"):
        page.evaluate(
            """([id, naam]) => {
                const laag = window.state.deckgl.props.layers.find(l => l && l.id === `externe-laag-${id}`);
                const f = window.state.externeKaartlaagData[id].geojson.features
                    .find(f => f.properties.woonplaats === naam);
                if (!f) throw new Error('woonplaats niet gevonden: ' + naam);
                laag.props.onClick({ object: f });
            }""",
            [laag["id"], naam],
        )
        page.wait_for_function(
            "(naam) => window.state.selectedGroepen.some(g => g.naam === naam)", arg=naam, timeout=30_000
        )

    groepen = page.evaluate("() => window.state.selectedGroepen")
    per_naam = {g["naam"]: g["buurtIds"] for g in groepen}
    assert WORKUM in per_naam["Workum"]
    assert KOUDUM in per_naam["Koudum"]
    expect(page.locator("#selection-badge")).to_contain_text("Workum, Koudum")

    # Kompas aggregeert de geselecteerde buurten
    open_kompas(page, "Workum")

    # 5. Laag uitzetten: overlay weg, selectie blijft
    open_paneel(page, "Kaartlagen")
    page.locator(f"label:has(#toggle-externe-laag-{laag['id']})").click()
    expect(toggle).not_to_be_checked()
    page.wait_for_function(
        "(id) => !window.state.deckgl.props.layers.some(l => l && l.id === `externe-laag-${id}`)",
        arg=laag["id"],
    )
    assert len(page.evaluate("() => window.state.selectedGroepen")) == 2


@pytest.mark.skip(reason="TC-01-003 C: woonbeleid-gebieden zijn nog niet beschikbaar (dataset aan te leveren)")
def test_tc_01_003c_woonbeleid():
    """TC-01-003 C: Woonbeleid-gebieden als selectieframe."""


# ── Kaart-export (vervangt het oude script tests/test_canvas.py) ─────────────

def test_kaart_canvas_exporteerbaar(app_page, tmp_path):
    """Kaartcanvassen zijn niet 'tainted' (CORS van de basiskaart) en de screenshot-export
    levert een PNG op. Voorheen handmatig getoetst met tests/test_canvas.py."""
    page = app_page
    laad_buurtenkaart(page)
    resultaten = page.evaluate(
        """() => [...document.querySelectorAll('#map canvas')].map(c => {
            try { return c.toDataURL('image/png').length; } catch (e) { return 'FOUT: ' + e; }
        })"""
    )
    assert resultaten and all(isinstance(r, int) and r > 1000 for r in resultaten), resultaten

    open_paneel(page, "Exporteren")
    with page.expect_download() as dl:
        page.locator("#export-screenshot-btn").click()
    pad = tmp_path / "kaart.png"
    dl.value.save_as(pad)
    assert pad.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
