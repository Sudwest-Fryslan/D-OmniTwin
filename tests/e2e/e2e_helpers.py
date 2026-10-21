"""
Hulpfuncties voor de E2E-tests: kaart laden, buurten selecteren (echte canvasklik
of via de klik-handler van de app) en het Kompas-zonnediagram bedienen.

De app publiceert `window.state` (kaartstaat, deck.gl-instantie) en
`window.kompasViz` (Kompas); daarop steunen de hulpfuncties.
"""

import json
import math
import os
import re
import time
import warnings

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Wachttijd voor trage stappen (kaartdata, Kompas). CI-runners zonder GPU: E2E_TIMEOUT_MS hoger zetten.
# Wordt bij gebruik geschaald met de gemeten traagheid van de renderer: gebruik traag_ms().
TRAAG_MS = int(os.environ.get("E2E_TIMEOUT_MS", "30000"))

# Testbuurten van de demo-use cases (usecases/*/usecase.json, data.gebieden). Sinds #236 laadt een
# verse installatie alle CBS-buurten van Fryslân; de tests vergelijken daarom niet met een vast aantal,
# maar eisen dat deze buurten erbij zijn.
BOLSWARD_ZUIDOOST = "BU19000002"
WORKUM = "BU19000200"
HINDELOOPEN = "BU19000202"
KOUDUM = "BU19000300"
TESTBUURTEN = [
    "BU19000001",
    "BU19000002",
    "BU19000004",
    "BU19000108",
    "BU19000200",
    "BU19000202",
    "BU19000300",
    "BU19000301",
    "BU19000400",
    "BU19000401",
    "BU19001200",
    "BU19001300",
    "BU19002017",
]


# ── Traagheid van de renderer (#212) ─────────────────────────────────────────
# De browser rendert WebGL in software (SwiftShader) en deelt de CPU met alles wat er verder
# op de machine draait. Onder CPU-druk (andere containers, `docker run --cpus=2`) duurt
# hetzelfde tekenwerk vele malen langer, en vaste wachttijden die in rust ruim zijn, lopen af.
# Daarom meet elke testpagina bij het openen hoe lang een vaste kleine WebGL-taak duurt
# (tekenen + readPixels, mediaan van 5) en schalen de wachttijden mee: geschaald(ms).
# Gemeten op een laptop met 8 cores (#212): vrij ±17 ms, --cpus=2 ±90 ms, --cpus=2 met
# andere last 110-190 ms. Picks en kaartklikken vertragen in dezelfde orde (5-10x).

_BENCH_JS = """
() => {
  const c = document.createElement('canvas'); c.width = 64; c.height = 64;
  const gl = c.getContext('webgl'); if (!gl) return null;
  const sh = (t, s) => { const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x); return x; };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, 'attribute vec2 a; void main(){gl_Position=vec4(a,0.,1.);}'));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, 'precision mediump float; void main(){gl_FragColor=vec4(1.);}'));
  gl.linkProgram(p); gl.useProgram(p);
  // 20.000 kleine driehoeken: vooral vertexwerk, zoals de gebiedenlaag
  const N = 20000, v = new Float32Array(N * 6);
  for (let i = 0; i < v.length; i++) v[i] = Math.sin(Math.floor(i / 6) * 12.9898) * 0.9 + (i % 6) * 0.004;
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, v, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const px = new Uint8Array(4);
  const teken = () => { gl.drawArrays(gl.TRIANGLES, 0, N * 3); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); };
  teken();  // shader compileren valt buiten de meting
  const tijden = [];
  for (let i = 0; i < 5; i++) { const t0 = performance.now(); teken(); tijden.push(performance.now() - t0); }
  const e = gl.getExtension('WEBGL_lose_context'); if (e) e.loseContext();
  return tijden.sort((a, b) => a - b)[2];
}
"""
# Duur van de taak hierboven zonder andere last (Playwright-container zonder CPU-grens, 8 cores),
# naar beneden afgerond: de factor wordt liever iets te groot dan te klein.
# Overschrijfbaar met E2E_BENCH_REFERENTIE_MS.
_BENCH_REFERENTIE_MS = float(os.environ.get("E2E_BENCH_REFERENTIE_MS", "15"))
# Bovengrens: ook een vastgelopen test moet binnen redelijke tijd falen.
_MAX_TRAAGHEID = float(os.environ.get("E2E_MAX_TRAAGHEID", "6"))
_traagheid = 1.0
# Alle metingen van deze sessie (ms, factor), voor het overzicht na de run (conftest).
traagheidsmetingen = []


def meet_traagheid(page: Page) -> float:
    """Meet de renderer en zet de schaalfactor voor de wachttijden (minstens 1). De last op de
    machine wisselt binnen een test; daarom geldt de hoogste factor van de laatste drie metingen."""
    global _traagheid
    ms = page.evaluate(_BENCH_JS)
    factor = min(_MAX_TRAAGHEID, max(1.0, ms / _BENCH_REFERENTIE_MS)) if ms else 1.0
    traagheidsmetingen.append((ms, factor))
    _traagheid = max(f for _, f in traagheidsmetingen[-3:])
    return _traagheid


def traagheid() -> float:
    return _traagheid


def geschaald(ms: float) -> int:
    """Wachttijd die in rust ruim is, geschaald met de gemeten traagheid van de renderer."""
    return int(ms * _traagheid)


def traag_ms() -> int:
    """Wachttijd voor trage stappen (TRAAG_MS), geschaald."""
    return geschaald(TRAAG_MS)


# Standaardwachttijden van een pagina en van expect() (E2E_EXPECT_TIMEOUT_MS), vóór schaling
PAGINA_TIMEOUT_MS = 20_000
EXPECT_TIMEOUT_MS = int(os.environ.get("E2E_EXPECT_TIMEOUT_MS", "15000"))


def stel_wachttijden_in(page: Page) -> float:
    """Na de eerste paginalading: renderer meten en de standaardwachttijden van de pagina en
    van expect() schalen. Geeft de factor terug."""
    factor = meet_traagheid(page)
    page.set_default_timeout(geschaald(PAGINA_TIMEOUT_MS))
    expect.set_options(timeout=geschaald(EXPECT_TIMEOUT_MS))
    return factor


# ── Basiskaart (#212) ────────────────────────────────────────────────────────
# De tegels van de PDOK-basiskaart tekent MapLibre in een eigen WebGL-context, ook in software.
# Na elke camerabeweging komen er tegels binnen en tekent MapLibre tientallen frames (inladen,
# vervagen), wat onder CPU-druk de deck.gl-renderer en daarmee kaartklikken en wachttijden
# vertraagt (gemeten: laden van de buurtenkaart 93 s met, 15 s zonder tegels bij --cpus=2).
# Geen test gaat over de inhoud van de basiskaart; de tegels worden daarom beantwoord met een
# lege tegel (HTTP 204). Stijl, glyphs en sprites laden gewoon. Tests die de basiskaart wel nodig
# hebben: marker `basiskaart`. E2E_BASISKAART=1 laat de tegels altijd door.
_BASISKAART_TEGELS = re.compile(r"^https://api\.pdok\.nl/.*/tiles/")


def zonder_basiskaarttegels(context):
    """Lege tegels voor de PDOK-basiskaart in deze browsercontext (zie boven)."""
    if os.environ.get("E2E_BASISKAART") == "1":
        return
    context.route(_BASISKAART_TEGELS, lambda route: route.fulfill(status=204, body=b""))


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
# Een frame binnen deze tijd na het vorige: de renderer loopt weer. Ruim boven een gewoon
# (ook traag) frame, ruim onder de gaten van seconden tijdens shadercompilatie.
_VLOT_MS = 1000


def wacht_op_frames(page: Page, aantal: int = 3, timeout: int = None):
    """Wacht tot de renderer weer vlot tekent: `aantal` animatieframes achter elkaar, elk
    binnen _VLOT_MS na het vorige (geen shadercompilatie of ander lang werk ertussen)."""
    timeout = timeout or traag_ms()
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


def wacht_op_kaart_in_rust(page: Page, timeout: int = None):
    """Camera staat stil: de viewState verandert niet meer over twee getekende frames."""
    timeout = timeout or traag_ms()
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
            page.wait_for_function(aangekomen_js, polling=_POLL_MS, timeout=geschaald(10_000))
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
    expect(knop).to_be_enabled(timeout=traag_ms())  # pas na het laden van de indicatoren
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok):
        klik(page, knop)
    wacht_op_kaartdata(page)


def wacht_op_kaartdata(page: Page, gebied_ids=tuple(TESTBUURTEN)):
    """Kaartdata geladen en getekend, met (minstens) deze buurten erin."""
    page.wait_for_function(
        "(ids) => { const d = window.state.currentData; if (!d) return false;"
        " const op = new Set(d.features.map(f => f.id || f.properties.id));"
        " return ids.every(i => op.has(i))"
        " && window.state.deckgl.props.layers.some(l => l.id.startsWith('gebieden-layer-')); }",
        arg=list(gebied_ids),
        polling=_POLL_MS,
        timeout=traag_ms(),
    )


def aantal_kaartgebieden(page: Page) -> int:
    return page.evaluate("() => window.state.currentData.features.length")


def selectie(page: Page) -> list:
    return page.evaluate("() => [...window.state.selectedGebiedIds]")


def wacht_op_selectie(page: Page, ids):
    page.wait_for_function(
        "(ids) => { const s = [...window.state.selectedGebiedIds].sort();"
        " return JSON.stringify(s) === JSON.stringify([...ids].sort()); }",
        arg=list(ids),
        polling=_POLL_MS,
    )


def selectie_overlay_aanwezig(page: Page) -> bool:
    return page.evaluate("() => window.state.deckgl.props.layers.some(l => l && l.id === 'selection-overlay-layer')")


# Klikpunt binnen een buurt (#212). Vroeger werd een raster van punten één voor één met
# deck.pickObject() getoetst. Elke pick tekent de hele gebiedenlaag opnieuw in een pickbuffer;
# onder CPU-druk kost dat 0,2-2 s per punt (en de eerste pick na het laden van de laag, met het
# compileren van de pickshaders, 20-50 s), zodat een buurt aan de rand na 15 s nog geen punt had.
# Nu: de punten worden op de CPU getoetst (punt-in-polygoon op de geprojecteerde ringen, niet
# afgedekt volgens document.elementFromPoint), gesorteerd op afstand tot de rand van de buurt
# (zo ver mogelijk naar binnen, dus ongevoelig voor een halve pixel camerabeweging). Alleen
# het gekozen punt wordt daarna één keer met deck.pickObject() bevestigd.
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
  const g = f.geometry;
  const polygonen = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
  const ringen = [];
  for (const p of polygonen) for (const r of p) ringen.push(r.map(c => vp.project(c)));
  const pts = ringen.flat();
  if (!pts.length) return null;
  const M = 5;  // niet op de rand van het canvas klikken
  const x0 = Math.max(Math.min(...pts.map(p => p[0])), M), x1 = Math.min(Math.max(...pts.map(p => p[0])), rect.width - M);
  const y0 = Math.max(Math.min(...pts.map(p => p[1])), M), y1 = Math.min(Math.max(...pts.map(p => p[1])), rect.height - M);
  if (!(x0 < x1 && y0 < y1)) return [];
  const binnen = (x, y) => {  // even-oneven-regel over alle ringen (gaten tellen mee)
    let b = false;
    for (const r of ringen) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) b = !b;
    }
    return b;
  };
  const randafstand = (x, y) => {
    let d = Math.min(x - M, rect.width - M - x, y - M, rect.height - M - y);
    for (const r of ringen) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [ax, ay] = r[j], [bx, by] = r[i];
      const dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy;
      const t = l ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l)) : 0;
      d = Math.min(d, Math.hypot(x - ax - t * dx, y - ay - t * dy));
    }
    return d;
  };
  const N = 32, kandidaten = [];
  for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) {
    const x = x0 + (x1 - x0) * i / N, y = y0 + (y1 - y0) * j / N;
    if (!binnen(x, y)) continue;
    const el = document.elementFromPoint(rect.left + x, rect.top + y);
    if (!el || !kaart.contains(el)) continue;  // afgedekt door paneel, badge, venster, ...
    kandidaten.push({ x: rect.left + x, y: rect.top + y, lx: x, ly: y, marge: randafstand(x, y) });
  }
  kandidaten.sort((a, b) => b.marge - a.marge);
  return kandidaten.slice(0, 3);
}
"""

# Bevestiging: pickt deck.gl op dit punt (canvascoördinaten) de buurt?
_PICK_JS = """
([gebiedId, x, y]) => {
  const info = window.state.deckgl.pickObject({ x, y, radius: 0 });
  const o = info && info.object;
  return !!o && (o.id || (o.properties && o.properties.id)) === gebiedId;
}
"""


def klikpunt_buurt(page: Page, gebied_id: str, timeout: float = None):
    """Schermcoördinaat binnen de buurt, zo ver mogelijk van de rand, als de camera stilstaat
    (zelfde punt over een ronde vlotte frames) en deck.gl daar de buurt pickt.
    None als de buurt niet onafgedekt in beeld is (dan zoomt de aanroeper uit)."""
    eind = time.monotonic() + (timeout or geschaald(15_000) / 1000)
    vorige = None
    while True:
        kandidaten = page.evaluate(_KLIKPUNT_JS, gebied_id)
        if kandidaten is None:
            raise AssertionError(f"{gebied_id} staat niet in de kaartdata")
        if not kandidaten:
            return None
        punt = kandidaten[0]
        if vorige and abs(punt["x"] - vorige["x"]) < 1 and abs(punt["y"] - vorige["y"]) < 1:
            for k in kandidaten:
                if page.evaluate(_PICK_JS, [gebied_id, k["lx"], k["ly"]]):
                    return k
        vorige = punt
        resterend = int((eind - time.monotonic()) * 1000)
        if resterend <= 0:
            raise AssertionError(
                f"Geen klikbaar punt gevonden voor {gebied_id} binnen "
                f"{timeout or geschaald(15_000) / 1000:.0f}s (laatste kandidaat {punt})"
            )
        try:
            wacht_op_frames(page, timeout=resterend)
        except PlaywrightTimeoutError:
            pass


def zoom_kaart(page: Page, delta_y: int):
    """Scrollwiel boven het vrije middendeel van de kaart (positief = uitzoomen)."""
    kaart = page.locator("#map").bounding_box()
    page.mouse.move(kaart["x"] + kaart["width"] * 0.5, kaart["y"] + kaart["height"] / 2)
    page.mouse.wheel(0, delta_y)
    page.wait_for_timeout(600)


def _vind_klikpunt(page: Page, gebied_id: str):
    """Klikpunt in de buurt; ligt die buiten beeld (bijv. na de camerasprong naar een eerder
    gekozen buurt), dan zoomt de test uit zoals een gebruiker dat zou doen."""
    for poging in range(4):
        punt = klikpunt_buurt(page, gebied_id)
        if punt:
            return punt
        if poging < 3:
            zoom_kaart(page, 400)
            wacht_op_camera_in_rust(page)
    raise AssertionError(
        f"Geen klikbaar punt gevonden voor {gebied_id}: niet onafgedekt in beeld, ook niet na uitzoomen"
    )


def wacht_op_camera_in_rust(page: Page, timeout: float = None):
    """Camera (viewState) gelijk over twee rondes van vlotte frames: een fly-to is klaar. Een klik
    tijdens een cameratransitie onderbreekt die en selecteert niets."""
    eind = time.monotonic() + (timeout or traag_ms() / 1000)
    vorige, gelijk = None, 0
    while time.monotonic() < eind:
        wacht_op_frames(page, timeout=max(1, int((eind - time.monotonic()) * 1000)))
        nu = page.evaluate(
            "() => { const v = window.state.currentViewState || {};"
            " return [v.longitude, v.latitude, v.zoom, v.pitch, v.bearing]; }"
        )
        gelijk = gelijk + 1 if nu == vorige else 0
        if gelijk >= 2:
            return
        vorige = nu
        page.wait_for_timeout(300)


# Waarom een echte kaartklik onder CPU-druk verloren gaat (#212, gemeten):
# deck.gl herkent een klik met de tap-herkenner van mjolnir.js (een port van hammer.js). Die
# eist dat pointerdown en pointerup binnen 250 ms na elkaar *verwerkt* worden; de tijd is
# Date.now() op het moment van verwerken, niet de tijdstempel van de gebeurtenis. Bij
# pointerdown doet deck.gl synchroon een pick (de gebiedenlaag opnieuw tekenen in een
# pickbuffer). Met software-WebGL onder CPU-druk duurt die pick 0,25-2,5 s; pointerup wordt pas
# daarna verwerkt, de tap-herkenner ziet een 'lange druk' en er volgt geen click, hoe kort de
# knop ook was ingedrukt. Opnieuw klikken helpt dan niet: elke pick duurt zo lang.
#
# De test meet daarom per klik wanneer pointerdown en pointerup binnenkomen en of mjolnir een
# click gaf. Viel de klik weg omdat de verwerking langer duurde dan de tapdrempel, dan wordt de
# tijdsdrempel van de click-herkenner voor deze testpagina verruimd (met een waarschuwing) en
# volgt een nieuwe echte klik. Alle andere voorwaarden blijven: echte muisgebeurtenissen op het
# canvas, op dezelfde plek (positiedrempel 9 px), pick door deck.gl en de onClick-handler van de
# gebiedenlaag. Alleen de tijd die de renderer zelf verbruikt telt niet meer als 'lang ingedrukt'.
_KLIKPROBE_JS = """
() => {
  const d = window.state.deckgl;
  if (!d.__e2eKlik) {
    const p = d.__e2eKlik = {};
    const kaart = document.getElementById('map');
    kaart.addEventListener('pointerdown', () => { p.down = Date.now(); }, true);
    kaart.addEventListener('pointerup', () => { p.up = Date.now(); }, true);
    d.eventManager.on('click', () => { p.klik = true; });
  }
  Object.assign(d.__e2eKlik, { down: null, up: null, klik: false });
  return d.eventManager.manager.get('click').options.time;
}
"""

# Uitkomst van een kaartklik: selectie gewijzigd, of zeker dat er geen (passende) click kwam.
_KLIKUITKOMST_JS = """
(voor) => {
  if (JSON.stringify([...window.state.selectedGebiedIds].sort()) !== JSON.stringify(voor)) return 'selectie';
  const p = window.state.deckgl.__e2eKlik;
  if (p.up && Date.now() - p.up > 1000) return p.klik ? 'click-zonder-selectie' : 'geen-click';
  return false;
}
"""

# Laatste redmiddel: dezelfde pick als deck.gl bij een klik, en de onClick-handler van de laag.
_KLIK_VIA_PICK_JS = """
([gebiedId, x, y, shift]) => {
  const s = window.state;
  const info = s.deckgl.pickObject({ x, y, radius: 0 });
  const o = info && info.object;
  if (!o || (o.id || (o.properties && o.properties.id)) !== gebiedId) return false;
  const laag = s.deckgl.props.layers.find(l => l && l.id.startsWith('gebieden-layer-'));
  laag.props.onClick(info, { srcEvent: { shiftKey: shift } });
  return true;
}
"""

_MAX_TAPDREMPEL_MS = 30_000


def klik_buurt_op_kaart(page: Page, gebied_id: str, shift: bool = False, terugval: bool = False):
    """Echte muisklik op het kaartcanvas binnen de buurt (optioneel met Shift).

    Ligt de buurt buiten beeld, dan zoomt de test eerst uit. Valt een klik weg doordat de
    renderer pointerdown en pointerup te ver uit elkaar verwerkt (zie boven), dan wordt de
    tapdrempel voor deze pagina verruimd en volgt een nieuwe echte klik; dat en elke andere
    herhaling wordt als waarschuwing gelogd. Een gemiste klik laat de selectie ongewijzigd,
    dus opnieuw klikken is veilig.

    terugval=True: lukt het na alle pogingen niet met een echte klik, dan als laatste redmiddel
    dezelfde pick + onClick-handler als deck.gl bij een klik (met een waarschuwing). Niet
    gebruiken in tests die de kaartklik zelf toetsen (TC-01-001, TC-01-002 A)."""
    voor = sorted(selectie(page))
    punt = None
    for poging in range(4):
        wacht_op_camera_in_rust(page)
        punt = _vind_klikpunt(page, gebied_id)
        # Eerst erheen bewegen en de hover-pick en -hertekening afwachten, zodat de klik zelf
        # niet ook nog op die hertekening hoeft te wachten
        page.mouse.move(punt["x"], punt["y"])
        wacht_op_frames(page)
        tapdrempel = page.evaluate(_KLIKPROBE_JS)
        if shift:
            page.keyboard.down("Shift")
        try:
            page.mouse.click(punt["x"], punt["y"])
        finally:
            if shift:
                page.keyboard.up("Shift")
        try:
            uitkomst = page.wait_for_function(
                _KLIKUITKOMST_JS, arg=voor, polling=_POLL_MS, timeout=geschaald(15_000)
            ).json_value()
        except PlaywrightTimeoutError:
            uitkomst = "geen-pointerup"
        if uitkomst == "selectie":
            return
        p = page.evaluate("() => window.state.deckgl.__e2eKlik")
        verwerking = (p["up"] - p["down"]) if p["up"] and p["down"] else None
        if uitkomst == "geen-click" and verwerking and verwerking > tapdrempel:
            nieuw = min(_MAX_TAPDREMPEL_MS, max(2_000, math.ceil(verwerking * 3 / 1000) * 1000))
            page.evaluate("(t) => window.state.deckgl.eventManager.manager.get('click').set({ time: t })", nieuw)
            warnings.warn(
                f"kaartklik op {gebied_id}: pointerdown en pointerup {verwerking} ms na elkaar verwerkt "
                f"(pick bij pointerdown), boven de tapdrempel van {tapdrempel} ms; tapdrempel voor deze "
                f"testpagina verruimd naar {nieuw} ms (poging {poging + 1})"
            )
        else:
            warnings.warn(
                f"kaartklik op {gebied_id} niet geregistreerd: {uitkomst}, verwerking "
                f"{verwerking} ms, tapdrempel {tapdrempel} ms (poging {poging + 1}), opnieuw"
            )
    if terugval and punt:
        warnings.warn(
            f"kaartklik op {gebied_id} na 4 echte klikken niet aangekomen; laatste redmiddel: "
            "pick + onClick-handler van de gebiedenlaag"
        )
        if page.evaluate(_KLIK_VIA_PICK_JS, [gebied_id, punt["lx"], punt["ly"], shift]):
            page.wait_for_function(
                "(voor) => JSON.stringify([...window.state.selectedGebiedIds].sort()) !== JSON.stringify(voor)",
                arg=voor,
                polling=_POLL_MS,
            )
            return
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
    """Sleep het Kompas-venster aan de titelbalk naar de rechterrand (vrij zicht op de kaart, indien zwevend)."""
    venster = page.locator("#kompas-window")
    if not venster.is_visible():
        return
    kop_loc = page.locator("#kompas-window .floating-window-header h3")
    if not kop_loc.is_visible():
        return
    kop = kop_loc.bounding_box()
    if not kop:
        return
    start_x, start_y = kop["x"] + 20, kop["y"] + kop["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + 2000, start_y, steps=10)  # venster wordt binnen het scherm begrensd
    page.mouse.up()


def open_kompas(page: Page, verwacht_in_info: str):
    """Kompas openen via het rechter dock of de tabbalk; wacht tot het dock de selectie toont."""
    dock = page.locator("#rechter-dock")
    if "collapsed" in (dock.get_attribute("class") or "") or not page.locator("#dock-panel-kompas").is_visible():
        open_paneel(page, "D-Omni Kompas")
    expect(page.locator("#dock-panel-kompas")).to_be_visible()
    expect(page.locator("#kompas-info")).to_contain_text(verwacht_in_info, timeout=traag_ms())
    wacht_op_zonnediagram(page)


def wacht_op_zonnediagram(page: Page):
    page.wait_for_function(
        "() => document.querySelectorAll('#kompas-container path.kompas-arc-path').length > 10", polling=_POLL_MS
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


def klik_kompas_segment(page: Page, naam: str, timeout: float = None):
    """Echte muisklik op een segment van het zonnediagram (na afloop van zoomanimaties).

    De klik is aangekomen als het Kompas dat segment als huidige knoop heeft (zowel bij
    inzoomen op een thema als bij het openen van een indicator). Zo niet, dan opnieuw
    (bijv. als een herteken van het diagram de klik onderschepte); als waarschuwing gelogd.
    Er wordt na de klik niet op het einde van de zoomtransitie gewacht: tests die de
    transitie zelf toetsen (reduced motion) moeten die nog kunnen zien.
    De wachttijd is TRAAG_MS (geschaald): het wachten omvat ook het wachten op de renderer."""
    timeout = timeout or traag_ms() / 1000
    for poging in range(3):
        punt = _segmentpunt(page, naam, timeout)
        page.mouse.click(punt["x"], punt["y"])
        try:
            page.wait_for_function(
                "(naam) => window.kompasViz.currentNode && window.kompasViz.currentNode.data.name === naam",
                arg=naam,
                polling=_POLL_MS,
                timeout=geschaald(5_000),
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
        polling=_POLL_MS,
    )
    expect(page.locator("#kompas-trend-chart")).to_be_visible()


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)
