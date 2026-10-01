"""
Toegankelijkheid (WCAG 2.1, #67): focusbeheer in dialogen en "minder beweging".

- Rapportkeuze-modal (representatieve modale dialoog): role="dialog" met naam,
  focus gaat erin en blijft erin (Tab/Shift+Tab), Escape sluit, focus terug naar
  de knop die de dialoog opende.
- Kompas-venster (niet-modaal): focus gaat erin, Escape sluit, focus terug.
- prefers-reduced-motion: reduce → de deck.gl-camera springt zonder overgang en
  het zonnediagram zoomt zonder D3-transitie. Een controletest zonder die
  instelling laat zien dat de overgang er normaal wel is.
"""

from playwright.sync_api import expect

from e2e_helpers import (
    WORKUM,
    klik_kompas_segment, laad_buurtenkaart, open_kompas, open_paneel, selecteer_buurt_via_app,
    wacht_op_selectie,
)

FOCUS_IN = "(sel) => { const d = document.querySelector(sel); return !!d && d.contains(document.activeElement); }"


def _focus_id(page):
    return page.evaluate("() => document.activeElement && document.activeElement.id")


def test_rapportdialoog_focus_vasthouden_escape_en_focus_terug(app_page):
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])

    open_paneel(page, "Rapport")
    knop = page.locator("#open-rapport-btn")
    expect(knop).to_be_enabled()
    knop.focus()
    page.keyboard.press("Enter")  # openen met het toetsenbord

    dialoog = page.locator("#rapport-type-modal [role='dialog']")
    expect(dialoog).to_be_visible()
    expect(dialoog).to_have_attribute("aria-modal", "true")
    expect(dialoog).to_have_accessible_name("Kies Rapport Type")
    sel = "#rapport-type-modal [role='dialog']"
    page.wait_for_function(FOCUS_IN, arg=sel)

    # Tab blijft binnen de dialoog, ook voorbij de laatste knop
    knoppen = dialoog.locator("button")
    aantal = knoppen.count()
    assert aantal >= 3
    for _ in range(aantal + 2):
        page.keyboard.press("Tab")
        assert page.evaluate(FOCUS_IN, sel), "focus verliet de modale dialoog bij Tab"

    # Shift+Tab vanaf de eerste knop gaat naar de laatste (Annuleren)
    knoppen.first.focus()
    page.keyboard.press("Shift+Tab")
    assert page.evaluate(FOCUS_IN, sel)
    expect(knoppen.last).to_be_focused()

    # Escape sluit en zet de focus terug op de knop
    page.keyboard.press("Escape")
    expect(page.locator("#rapport-type-modal")).to_have_count(0)
    expect(knop).to_be_focused()


def test_kompasvenster_escape_en_focus_terug(app_page):
    page = app_page
    open_paneel(page, "D-Omni Kompas")
    knop = page.locator("#open-kompas-btn")
    knop.focus()
    page.keyboard.press("Enter")

    venster = page.locator("#kompas-window")
    expect(venster).to_be_visible()
    expect(venster).to_have_attribute("role", "dialog")
    expect(venster).to_have_accessible_name("D-Omni Kompas")
    page.wait_for_function(FOCUS_IN, arg="#kompas-window")

    page.keyboard.press("Escape")
    expect(venster).to_be_hidden()
    expect(knop).to_be_focused()


# ── prefers-reduced-motion ───────────────────────────────────────────────────

# Registreert de camera-overgangen die de app via setProps({viewState}) aanvraagt.
# (props.viewState achteraf lezen werkt niet: deck.gl overschrijft die na de overgang.)
_REGISTREER_CAMERA = """() => {
  const d = window.state.deckgl;
  window.__camera = [];
  if (d.__cameraGeregistreerd) return;
  const orig = d.setProps.bind(d);
  d.setProps = (p) => {
    if (p && p.viewState && 'transitionDuration' in p.viewState) {
      window.__camera.push({ duur: p.viewState.transitionDuration || 0,
                             interpolator: !!p.viewState.transitionInterpolator });
    }
    return orig(p);
  };
  d.__cameraGeregistreerd = true;
}"""


def _camera(page):
    return page.evaluate("() => window.__camera")


def test_camera_met_overgang_zonder_reduced_motion(app_page):
    """Controle: zonder de instelling vliegt de camera (FlyToInterpolator, duur > 0)."""
    page = app_page
    assert page.evaluate("() => window.A11y.prefersReducedMotion()") is False
    page.evaluate(_REGISTREER_CAMERA)
    laad_buurtenkaart(page)
    camera = _camera(page)
    assert any(c["duur"] > 0 and c["interpolator"] for c in camera), camera


def test_reduced_motion_camera_springt_en_kompas_zonder_transitie(app_page_reduced_motion):
    page = app_page_reduced_motion
    assert page.evaluate("() => window.A11y.prefersReducedMotion()") is True

    # fitBounds na het laden van de kaart
    page.evaluate(_REGISTREER_CAMERA)
    laad_buurtenkaart(page)
    camera = _camera(page)
    assert camera and all(c["duur"] == 0 and not c["interpolator"] for c in camera), camera

    # flyToGebied na het kiezen van een buurt
    page.evaluate(_REGISTREER_CAMERA)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    page.wait_for_function("() => window.__camera.length > 0")
    camera = _camera(page)
    assert all(c["duur"] == 0 and not c["interpolator"] for c in camera), camera

    # Kompas: inzoomen op een thema zonder D3-transitie
    open_kompas(page, "Workum")
    thema = page.evaluate(
        "() => window.kompasViz.root.children.find(c => c.children && c.children.length).data.name"
    )
    klik_kompas_segment(page, thema)
    expect(page.locator("#kompas-breadcrumb")).to_contain_text(thema)
    page.wait_for_timeout(150)  # ruim onder de normale 750 ms
    klaar = page.evaluate(
        """() => [...document.querySelectorAll('#kompas-container path.kompas-arc-path')]
              .map(p => p.__data__)
              .filter(d => d && d.target && window.kompasViz.arcVisible(d.target))
              .every(d => ['x0', 'x1', 'y0', 'y1'].every(k => Math.abs(d.current[k] - d.target[k]) < 1e-9))"""
    )
    assert klaar, "zonnediagram staat 150 ms na de klik nog niet op de eindstand"
