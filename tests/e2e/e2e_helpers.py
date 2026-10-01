"""
Hulpfuncties voor de E2E-tests: kaart laden, buurten selecteren (echte canvasklik
of via de klik-handler van de app) en het Kompas-zonnediagram bedienen.

De app publiceert `window.state` (kaartstaat, deck.gl-instantie) en
`window.kompasViz` (Kompas); daarop steunen de hulpfuncties.
"""

import json
import os
import time
import warnings

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Wachttijd voor trage stappen (kaartdata, Kompas). CI-runners zonder GPU: E2E_TIMEOUT_MS hoger zetten.
TRAAG_MS = int(os.environ.get("E2E_TIMEOUT_MS", "30000"))

# Buurten uit de sample dataset (init_data/sample/2_brondata/sample_buurten.geojson)
BOLSWARD_ZUIDOOST = "BU19000002"
WORKUM = "BU19000200"
HINDELOOPEN = "BU19000202"
KOUDUM = "BU19000300"
AANTAL_SAMPLE_BUURTEN = 13


# ── Wachten op toestand (#194) ───────────────────────────────────────────────
# In CI rendert de browser in software (SwiftShader). Het compileren van WebGL-shaders
# (MapLibre en deck.gl, bij elke nieuwe laag of kaartstijl-laag) blokkeert dan de
# hoofdthread seconden per shader; na het laden van de kaart komt er tot een minuut lang
# soms maar eens per 5-20 s een animatieframe. Playwright toetst vóór een klik of het
# element 'stabiel' is over opeenvolgende animatieframes en hangt in die periode zonder
# verdere melding ("waiting for element to be visible, enabled and stable").
# Wachten op de klok is daar wankel; wacht op een toestand. Let op: page.wait_for_function
# pollt standaard per animatieframe; de helpers hieronder pollen op een vast interval.

_POLL_MS = 100
_VLOT_MS = 250  # een frame binnen deze tijd na het vorige: de renderer loopt weer


def wacht_op_frames(page: Page, aantal: int = 5, timeout: int = TRAAG_MS):
    """Wacht tot de renderer weer vlot tekent: `aantal` animatieframes achter elkaar, elk
    binnen _VLOT_MS na het vorige (geen shadercompilatie of ander lang werk ertussen)."""
    page.evaluate(
        """([n, vlot]) => {
            const t = window.__e2eFrames = {n: 0};
            let vorige = performance.now();
            const tel = (nu) => {
                t.n = (nu - vorige < vlot) ? t.n + 1 : 0;
                vorige = nu;
                if (t.n < n) requestAnimationFrame(tel);
            };
            requestAnimationFrame(tel);
        }""",
        [aantal, _VLOT_MS],
    )
    page.wait_for_function(
        "(n) => window.__e2eFrames && window.__e2eFrames.n >= n", arg=aantal, polling=_POLL_MS, timeout=timeout
    )


def klik(page: Page, knop: Locator):
    """Locator.click, pas als de renderer weer vlot tekent (zie boven)."""
    expect(knop).to_be_visible()
    wacht_op_frames(page)
    knop.click()


def wacht_op_kaart_in_rust(page: Page, timeout: int = TRAAG_MS):
    """Camera staat stil: de viewState verandert niet meer over twee getekende frames."""
    eind = time.monotonic() + timeout / 1000
    lees = "() => JSON.stringify(window.state.currentViewState)"
    while True:
        voor = page.evaluate(lees)
        wacht_op_frames(page, timeout=max(1, int((eind - time.monotonic()) * 1000)))
        if page.evaluate(lees) == voor:
            return
        if time.monotonic() > eind:
            raise AssertionError("kaartcamera komt niet tot stilstand")


def klik_en_bevestig(page: Page, knop: Locator, aangekomen_js: str, omschrijving: str, pogingen: int = 2):
    """Klik op een knop zodra die zichtbaar en ingeschakeld is en de renderer weer frames
    tekent, en toets daarna of de klik aankwam (`aangekomen_js` wordt waar). Kwam de klik
    niet aan (klik-time-out of geen effect), dan nog één keer; dat wordt als waarschuwing
    gelogd. Alleen geschikt voor knoppen waarvan een tweede klik geen kwaad kan of die na
    een geslaagde klik niet meer klikbaar zijn."""
    for poging in range(pogingen):
        expect(knop).to_be_visible()
        expect(knop).to_be_enabled()
        wacht_op_frames(page)
        try:
            knop.click()
        except PlaywrightTimeoutError:
            if page.evaluate(aangekomen_js):
                return  # klik kwam toch nog aan
            if poging == pogingen - 1:
                raise
            warnings.warn(f"klik op {omschrijving} niet uitgevoerd (poging {poging + 1}), opnieuw")
            continue
        try:
            page.wait_for_function(aangekomen_js, polling=_POLL_MS, timeout=10_000)
            return
        except PlaywrightTimeoutError:
            warnings.warn(f"klik op {omschrijving} niet aangekomen (poging {poging + 1}), opnieuw")
    raise AssertionError(f"klik op {omschrijving} komt niet aan")


def klik_chatactie(page: Page, knop: Locator, omschrijving: str):
    """Klik op een actieknop in de chat. Een geslaagde klik zet de klasse 'actie-activated'
    (en pointer-events: none), dus een herhaalde klik kan alleen volgen op een gemiste."""
    knop.evaluate("(el) => { window.__e2eKnop = el; }")
    klik_en_bevestig(page, knop, "() => window.__e2eKnop.classList.contains('actie-activated')", omschrijving)


# ── Kaart ────────────────────────────────────────────────────────────────────

def open_paneel(page: Page, aria_label: str):
    """Open een zijpaneel via de tabbalk (laat een al open paneel open)."""
    knop = page.get_by_role("button", name=aria_label, exact=True)
    if "active" not in (knop.get_attribute("class") or ""):
        klik(page, knop)
    page.wait_for_function(
        "(label) => document.querySelector(`.tab-button[aria-label=\"${label}\"]`).classList.contains('active')",
        arg=aria_label,
    )


def laad_buurtenkaart(page: Page):
    """Kaartconfiguratie: gebiedstype CBS Buurten kiezen en 'Toon op kaart'."""
    open_paneel(page, "Kaartconfiguratie")
    page.locator("#gebiedstype-select").select_option(label="CBS Buurten")
    knop = page.locator("#toon-kaart-btn")
    expect(knop).to_be_enabled(timeout=TRAAG_MS)  # pas na het laden van de indicatoren
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok):
        klik(page, knop)
    wacht_op_kaartdata(page)


def wacht_op_kaartdata(page: Page, aantal: int = AANTAL_SAMPLE_BUURTEN):
    page.wait_for_function(
        "(n) => window.state.currentData && window.state.currentData.features.length === n"
        " && window.state.deckgl.props.layers.some(l => l.id.startsWith('gebieden-layer-'))",
        arg=aantal,
        timeout=TRAAG_MS,
    )


def selectie(page: Page) -> list:
    return page.evaluate("() => [...window.state.selectedGebiedIds]")


def wacht_op_selectie(page: Page, ids):
    page.wait_for_function(
        "(ids) => { const s = [...window.state.selectedGebiedIds].sort();"
        " return JSON.stringify(s) === JSON.stringify([...ids].sort()); }",
        arg=list(ids),
    )


def selectie_overlay_aanwezig(page: Page) -> bool:
    return page.evaluate(
        "() => window.state.deckgl.props.layers.some(l => l && l.id === 'selection-overlay-layer')"
    )


# Zoekt een schermpunt binnen de buurt waar (1) deck.gl de buurt pickt en (2) het
# bovenste DOM-element bij de kaart hoort (niet afgedekt door paneel, badge, ...).
_KLIKPUNT_JS = """
(gebiedId) => {
  const s = window.state;
  const deckgl = s.deckgl;
  const f = s.currentData && s.currentData.features.find(f => (f.id || f.properties.id) === gebiedId);
  if (!f) return null;
  const vp = deckgl.getViewports()[0];
  const canvas = deckgl.getCanvas ? deckgl.getCanvas() : deckgl.canvas;
  const rect = canvas.getBoundingClientRect();
  const kaart = document.getElementById('map');
  const pts = [];
  const plat = (a) => (typeof a[0] === 'number') ? pts.push(vp.project(a)) : a.forEach(plat);
  plat(f.geometry.coordinates);
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const kandidaten = [];
  const N = 24;
  for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) {
    const x = x0 + (x1 - x0) * i / N, y = y0 + (y1 - y0) * j / N;
    kandidaten.push([x, y, (x - cx) ** 2 + (y - cy) ** 2]);
  }
  kandidaten.sort((a, b) => a[2] - b[2]);
  for (const [x, y] of kandidaten) {
    if (x < 5 || y < 5 || x > rect.width - 5 || y > rect.height - 5) continue;
    const info = deckgl.pickObject({ x, y, radius: 0 });
    const o = info && info.object;
    if (!o || (o.id || (o.properties && o.properties.id)) !== gebiedId) continue;
    const el = document.elementFromPoint(rect.left + x, rect.top + y);
    if (!el || !kaart.contains(el)) continue;
    return { x: rect.left + x, y: rect.top + y };
  }
  return null;
}
"""


def klikpunt_buurt(page: Page, gebied_id: str, timeout: float = 15.0):
    """Schermcoördinaat binnen de buurt, pas als de camera stilstaat (fly-to/fitBounds klaar)."""
    eind = time.monotonic() + timeout
    vorige = None
    while time.monotonic() < eind:
        punt = page.evaluate(_KLIKPUNT_JS, gebied_id)
        if punt and vorige and abs(punt["x"] - vorige["x"]) < 1 and abs(punt["y"] - vorige["y"]) < 1:
            return punt
        vorige = punt
        page.wait_for_timeout(400)
    raise AssertionError(f"Geen klikbaar punt gevonden voor {gebied_id} binnen {timeout}s")


def zoom_kaart(page: Page, delta_y: int):
    """Scrollwiel boven het rechterdeel van de kaart (positief = uitzoomen)."""
    kaart = page.locator("#map").bounding_box()
    page.mouse.move(kaart["x"] + kaart["width"] * 0.7, kaart["y"] + kaart["height"] / 2)
    page.mouse.wheel(0, delta_y)
    page.wait_for_timeout(600)


def _vind_klikpunt(page: Page, gebied_id: str):
    for poging in range(4):
        try:
            return klikpunt_buurt(page, gebied_id, timeout=6.0 if poging < 3 else 15.0)
        except AssertionError:
            if poging == 3:
                raise
            zoom_kaart(page, 400)


def klik_buurt_op_kaart(page: Page, gebied_id: str, shift: bool = False):
    """Echte muisklik op het kaartcanvas binnen de buurt (optioneel met Shift).

    Ligt de buurt buiten beeld (bijv. na de camerasprong naar een eerder gekozen
    buurt), dan zoomt de test eerst uit zoals een gebruiker dat zou doen.
    Verandert de selectie niet binnen enkele seconden, dan klikt de test nog eens
    (een gemiste klik laat de selectie ongewijzigd, dus opnieuw klikken is veilig);
    dat wordt als waarschuwing gelogd."""
    voor = sorted(selectie(page))
    for poging in range(3):
        punt = _vind_klikpunt(page, gebied_id)
        if shift:
            page.keyboard.down("Shift")
        try:
            page.mouse.click(punt["x"], punt["y"])
        finally:
            if shift:
                page.keyboard.up("Shift")
        try:
            page.wait_for_function(
                "(voor) => JSON.stringify([...window.state.selectedGebiedIds].sort()) !== JSON.stringify(voor)",
                arg=voor, timeout=4_000,
            )
            return
        except Exception:
            warnings.warn(f"kaartklik op {gebied_id} niet geregistreerd (poging {poging + 1}), opnieuw")
    raise AssertionError(f"kaartklik op {gebied_id} wijzigt de selectie niet")


def selecteer_buurt_via_app(page: Page, gebied_id: str, shift: bool = False):
    """Selectie via de onClick-handler van de gebiedenlaag (zelfde codepad als een klik)."""
    page.evaluate(
        """([gebiedId, shift]) => {
            const s = window.state;
            const laag = s.deckgl.props.layers.find(l => l && l.id.startsWith('gebieden-layer-'));
            const f = s.currentData.features.find(f => (f.id || f.properties.id) === gebiedId);
            if (!laag || !f) throw new Error('laag of buurt niet gevonden: ' + gebiedId);
            laag.props.onClick({ object: f, coordinate: null }, { srcEvent: { shiftKey: shift } });
        }""",
        [gebied_id, shift],
    )


# ── Kompas ───────────────────────────────────────────────────────────────────

def verplaats_kompasvenster_rechts(page: Page):
    """Sleep het Kompas-venster aan de titelbalk naar de rechterrand (vrij zicht op de kaart)."""
    kop = page.locator("#kompas-window .floating-window-header h3").bounding_box()
    start_x, start_y = kop["x"] + 20, kop["y"] + kop["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + 2000, start_y, steps=10)  # venster wordt binnen het scherm begrensd
    page.mouse.up()

def open_kompas(page: Page, verwacht_in_info: str):
    """Kompas-paneel → 'Open Kompas'; wacht tot het venster de selectie toont."""
    open_paneel(page, "D-Omni Kompas")
    klik(page, page.locator("#open-kompas-btn"))
    expect(page.locator("#kompas-window")).to_be_visible()
    expect(page.locator("#kompas-info")).to_contain_text(verwacht_in_info, timeout=TRAAG_MS)
    wacht_op_zonnediagram(page)


def wacht_op_zonnediagram(page: Page):
    page.wait_for_function(
        "() => document.querySelectorAll('#kompas-container path.kompas-arc-path').length > 10"
    )


# Middelpunt (arc-centroid) van een segment in schermcoördinaten, alleen als het
# segment zichtbaar is, daar ook bovenop ligt en er geen d3-transitie (zoom) loopt.
_SEGMENT_JS = """
(naam) => {
  const kv = window.kompasViz;
  const container = document.getElementById('kompas-container');
  // d3 zet __transition op elk element met een lopende of geplande transitie
  if ([...container.querySelectorAll('*')].some(n => n.__transition)) return null;
  const paths = [...container.querySelectorAll('path.kompas-arc-path')];
  const el = paths.find(p => p.__data__ && p.__data__.data.name === naam);
  if (!el) return null;
  const d = el.__data__;
  if (!kv.arcVisible(d.current) || el.getAttribute('pointer-events') === 'none') return null;
  const [cx, cy] = kv.arc.centroid(d.current);
  const svg = el.ownerSVGElement;
  const pt = svg.createSVGPoint();
  pt.x = cx; pt.y = cy;
  const s = pt.matrixTransform(el.getScreenCTM());
  if (document.elementFromPoint(s.x, s.y) !== el) return null;
  return { x: s.x, y: s.y };
}
"""


def _segmentpunt(page: Page, naam: str, timeout: float):
    """Klikpunt van een segment zodra het zonnediagram stilstaat: geen lopende transitie
    en dezelfde positie na een reeks vlot getekende frames."""
    eind = time.monotonic() + timeout
    vorige = None
    while time.monotonic() < eind:
        punt = page.evaluate(_SEGMENT_JS, naam)
        if punt and vorige and abs(punt["x"] - vorige["x"]) < 0.5 and abs(punt["y"] - vorige["y"]) < 0.5:
            return punt
        vorige = punt
        try:
            wacht_op_frames(page, timeout=max(1, int((eind - time.monotonic()) * 1000)))
        except PlaywrightTimeoutError:
            break
    raise AssertionError(f"Kompas-segment '{naam}' niet klikbaar binnen {timeout}s")


def klik_kompas_segment(page: Page, naam: str, timeout: float = TRAAG_MS / 1000):
    """Echte muisklik op een segment van het zonnediagram (na afloop van zoomanimaties).

    De klik is aangekomen als het Kompas dat segment als huidige knoop heeft (zowel bij
    inzoomen op een thema als bij het openen van een indicator). Zo niet, dan opnieuw
    (bijv. als een herteken van het diagram de klik onderschepte); als waarschuwing gelogd.
    Er wordt na de klik niet op het einde van de zoomtransitie gewacht: tests die de
    transitie zelf toetsen (reduced motion) moeten die nog kunnen zien.
    De wachttijd is TRAAG_MS: het wachten omvat nu ook het wachten op de renderer."""
    for poging in range(3):
        punt = _segmentpunt(page, naam, timeout)
        page.mouse.click(punt["x"], punt["y"])
        try:
            page.wait_for_function(
                "(naam) => window.kompasViz.currentNode && window.kompasViz.currentNode.data.name === naam",
                arg=naam, polling=_POLL_MS, timeout=5_000,
            )
            return
        except PlaywrightTimeoutError:
            warnings.warn(f"klik op Kompas-segment '{naam}' niet aangekomen (poging {poging + 1}), opnieuw")
    raise AssertionError(f"klik op Kompas-segment '{naam}' komt niet aan")


def kompas_namen(page: Page) -> list:
    """Alle knoopnamen in de geladen Kompas-hiërarchie."""
    return page.evaluate("() => window.kompasViz.root.descendants().map(d => d.data.name)")


def open_indicator_in_kompas(page: Page, thema: str, indicator: str):
    """Zoom in op een thema en open de details van een indicator."""
    klik_kompas_segment(page, thema)
    expect(page.locator("#kompas-breadcrumb")).to_contain_text(thema)
    klik_kompas_segment(page, indicator)
    expect(page.locator("#kompas-details-panel")).to_be_visible()
    expect(page.locator("#details-title")).to_have_text(indicator)
    # Metadata geladen (placeholder 'Gegevens laden...' verdwenen)
    expect(page.locator("#details-definitie")).not_to_contain_text("Gegevens laden")


def wacht_op_vergelijkingsgrafiek(page: Page, namen):
    """Kompas-detailpaneel toont de staafgrafiek met één staaf per geselecteerd gebied."""
    page.wait_for_function(
        "(namen) => { const c = window.kompasViz.trendChart;"
        " return c && namen.every(n => c.data.labels.includes(n)); }",
        arg=list(namen),
    )
    expect(page.locator("#kompas-trend-chart")).to_be_visible()


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)
