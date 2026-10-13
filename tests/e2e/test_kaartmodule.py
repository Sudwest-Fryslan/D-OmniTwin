"""
TC-01-00x — Kaartmodule (docs/testcases/01-kaartmodule).

Afwijking van de testdata: de sample dataset bevat geen Makkum. Waar de testcase
Makkum noemt, gebruiken we Workum/Koudum/Hindeloopen (ook IJsselmeerkust).
"""

import time

import pytest
from playwright.sync_api import expect

from e2e_helpers import (
    HINDELOOPEN,
    KOUDUM,
    WORKUM,
    klik,
    klik_buurt_op_kaart,
    laad_buurtenkaart,
    open_kompas,
    open_paneel,
    selecteer_buurt_via_app,
    selectie,
    selectie_overlay_aanwezig,
    wacht_op_selectie,
    zoom_kaart,
    geschaald,
    traag_ms,
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
    badge.get_by_role("button", name="Selectie wissen").click()
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
    badge.get_by_role("button", name="Selectie wissen").click()
    wacht_op_selectie(page, [])
    expect(badge).to_be_hidden()
    assert not selectie_overlay_aanwezig(page)


@pytest.mark.skip(reason="TC-01-002 B: polygoon-/lassoselectie is nog niet geïmplementeerd (geen tekenmodus in de UI)")
def test_tc_01_002b_polygoonselectie():
    """TC-01-002 B: selectie via polygoontekening."""


# ── TC-01-003 Alternatieve gebiedslagen ──────────────────────────────────────


@pytest.mark.skip(
    reason="TC-01-003 A: omgevingsvisie-deelgebieden zitten niet in de sample dataset "
    "en zijn geen externe kaartlaag in de sample-stuurdata"
)
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
    with page.expect_response(
        lambda r: f"/api/externe-lagen/{laag['id']}/features" in r.url, timeout=geschaald(120_000)
    ) as resp:
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
            "(naam) => window.state.selectedGroepen.some(g => g.naam === naam)", arg=naam, timeout=traag_ms()
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


@pytest.mark.basiskaart
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


# ── #79 Kaart en selectie ────────────────────────────────────────────────────

# Bounding box van alle geladen gebieden in schermcoördinaten, plus de camera.
_BBOX_SCHERM_JS = """
() => {
  const s = window.state;
  const vp = s.deckgl.getViewports()[0];
  const xs = [], ys = [];
  const plat = (a) => (typeof a[0] === 'number') ? (xs.push(a[0]), ys.push(a[1])) : a.forEach(plat);
  s.currentData.features.forEach(f => plat(f.geometry.coordinates));
  const hoeken = [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]].map(p => vp.project(p));
  const v = s.currentViewState;
  const kaart = document.getElementById('map').getBoundingClientRect();
  const paneel = document.querySelector('.panel-container.open');
  return {
    links: paneel ? paneel.getBoundingClientRect().right - kaart.left : 0,
    x0: Math.min(hoeken[0][0], hoeken[1][0]), x1: Math.max(hoeken[0][0], hoeken[1][0]),
    y0: Math.min(hoeken[0][1], hoeken[1][1]), y1: Math.max(hoeken[0][1], hoeken[1][1]),
    breedte: vp.width, hoogte: vp.height,
    camera: [v.longitude, v.latitude, v.zoom],
  };
}
"""


def _camera_in_rust(page, timeout: float = None):
    """Schermpositie van de gebieden zodra de camera stilstaat (fly-to klaar)."""
    # Software-WebGL kan frames honderden ms laten haperen: eis 1,5 s stilstand
    eind = time.monotonic() + (timeout or traag_ms() / 1000)
    vorige, stil = None, 0
    while time.monotonic() < eind:
        nu = page.evaluate(_BBOX_SCHERM_JS)
        if vorige and all(abs(a - b) < 1e-6 for a, b in zip(nu["camera"], vorige["camera"])):
            stil += 1
            if stil >= 3:
                return nu
        else:
            stil = 0
        vorige = nu
        page.wait_for_timeout(500)
    raise AssertionError(f"camera kwam niet tot rust: {vorige}")


def test_kaart_zoomt_in_op_geladen_gebieden(app_page):
    """#79: na het laden zoomt de kaart in op de gebieden (fitBounds via viewState),
    helemaal zichtbaar naast het geopende linkerpaneel."""
    page = app_page
    # Eerst uitzoomen zoals een gebruiker: het beginbeeld is al Fryslân en sinds #236 staan alle
    # CBS-buurten van Fryslân op de kaart, dus zonder uitzoomen valt er niets in te zoomen.
    for _ in range(3):
        zoom_kaart(page, 600)
    start, stil = None, 0
    for _ in range(40):  # camera in rust (zelfde zoom over 1,5 s)
        nu = page.evaluate("() => ({ ...window.state.currentViewState })")
        stil = stil + 1 if start and abs(nu["zoom"] - start["zoom"]) < 1e-6 else 0
        start = nu
        if stil >= 3:
            break
        page.wait_for_timeout(500)
    laad_buurtenkaart(page)
    # Na het laden van de laag: eerste tekenbeurt (shadercompilatie in software-WebGL) en de
    # camera-animatie van 1 s. Onder CPU-druk kan dat tientallen seconden duren: TRAAG_MS (#212)
    page.wait_for_function(
        "(z) => window.state.currentViewState.zoom > z + 1", arg=start["zoom"], polling=100, timeout=traag_ms()
    )
    b = _camera_in_rust(page)

    assert b["camera"][2] > start["zoom"] + 1, f"niet ingezoomd: {b['camera']} (start {start})"
    links = b["links"]
    assert b["x0"] >= links - 5 and b["x1"] <= b["breedte"] + 5, f"buiten beeld horizontaal: {b}, paneel tot {links}"
    assert b["y0"] >= -5 and b["y1"] <= b["hoogte"] + 5, f"buiten beeld verticaal: {b}"
    # Gebieden vullen een behoorlijk deel van de vrije ruimte (echt ingezoomd, niet alleen verschoven)
    assert (b["x1"] - b["x0"]) > 0.4 * (b["breedte"] - links) or (b["y1"] - b["y0"]) > 0.4 * b["hoogte"], b

    # Nogmaals 'Toon op kaart' met hetzelfde gebiedstype: camera blijft staan
    zoom_kaart(page, 300)
    voor = _camera_in_rust(page)["camera"]
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok):
        page.locator("#toon-kaart-btn").click()
    page.wait_for_timeout(1500)
    na = _camera_in_rust(page)["camera"]
    assert na == pytest.approx(voor), f"camera verspringt bij herladen: {voor} → {na}"


def test_selectiebadge_knoppen(app_page):
    """#79: de selectiebadge heeft de naam als label en twee losse knoppen,
    '3D-panden' (toggle) en 'Selectie wissen'. Klikken op de naam doet niets;
    wissen werkt ook met het toetsenbord."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])

    badge = page.locator("#selection-badge")
    expect(badge).to_be_visible()
    naam = badge.locator("#selection-badge-naam")
    expect(naam).to_have_text("Workum")
    panden = badge.get_by_role("button", name="3D-panden")
    wissen = badge.get_by_role("button", name="Selectie wissen")
    expect(panden).to_have_attribute("aria-pressed", "false")
    expect(wissen).to_be_visible()

    # Label en knoppen overlappen niet; de wisknop staat rechts
    b_naam, b_panden, b_wissen = (l.bounding_box() for l in (naam, panden, wissen))
    assert b_naam["x"] + b_naam["width"] <= b_panden["x"] <= b_panden["x"] + b_panden["width"] <= b_wissen["x"]

    # Klik op de naam: selectie blijft, geen 3D-panden (klik(): pas als de renderer vlot tekent, #212)
    klik(page, naam)
    page.wait_for_timeout(500)
    assert selectie(page) == [WORKUM]
    assert page.evaluate("() => window.state.show3DBuildings") is False
    expect(panden).to_have_attribute("aria-pressed", "false")

    # Bijwerken van de badge (tweede gebied erbij) houdt dezelfde knoppen
    selecteer_buurt_via_app(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM])
    expect(naam).to_contain_text("2 gebieden geselecteerd")
    expect(panden).to_be_visible()

    # Wissen via het toetsenbord
    wissen.focus()
    page.keyboard.press("Enter")
    wacht_op_selectie(page, [])
    expect(badge).to_be_hidden()
    assert page.console_fouten == [], "\n".join(page.console_fouten)
