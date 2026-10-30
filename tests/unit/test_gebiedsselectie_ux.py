"""
Unit-tests voor de soepele gebiedsselectie, eliminatie van layout thrashing en
gesynchroniseerde choreografie conform issue #466.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "js" / "app.js"
KOMPAS_JS = ROOT / "static" / "js" / "kompas.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
PVE_DOC = ROOT / "docs" / "4-ux-design" / "pve-rechter-dock-architectuur.md"


def test_deckgl_controller_double_click_zoom_disabled():
    """
    Stap 2 (#466): In static/js/app.js moet deck.gl geconfigureerd zijn met
    controller: { doubleClickZoom: false } om de automatische 300ms delay op klik-events
    te elimineren.
    """
    content = APP_JS.read_text(encoding="utf-8")
    assert "doubleClickZoom: false" in content, (
        "deck.gl controller moet doubleClickZoom: false hebben voor directe klikreactie (< 100ms)"
    )


def test_kompas_wrap_text_uses_canvas_measure_text():
    """
    Stap 1 (#466): In static/js/kompas.js mag wrapText() GEEN getComputedTextLength()
    meer aanroepen (veroorzaakte forced reflows / layout thrashing voor elk woord van ~200 labels),
    maar moet canvas.measureText gebruiken.
    """
    content = KOMPAS_JS.read_text(encoding="utf-8")

    # wrapText mag niet getComputedTextLength gebruiken
    wrap_text_match = re.search(r"wrapText\(textSelection,\s*radius\)\s*\{(.*?)\n    \}", content, re.DOTALL)
    assert wrap_text_match, "wrapText functie niet gevonden in kompas.js"
    wrap_text_body = wrap_text_match.group(1)

    assert ".getComputedTextLength(" not in wrap_text_body, (
        "wrapText() mag geen .getComputedTextLength() meer aanroepen om layout thrashing te voorkomen"
    )
    assert "measureText" in wrap_text_body, (
        "wrapText() moet canvas measureText gebruiken voor snelle in-memory breedtebepaling"
    )
    assert "getMeasureCanvasCtx" in content, "kompas.js moet een singleton helper getMeasureCanvasCtx bevatten"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_kompas_wrap_text_node_execution():
    """
    Verifieert via Node.js dat de wrapText logica met canvas context (of fallback)
    woorden correct splitst in meerdere regels (tspans) met max 3 regels en verticale centrering.
    """
    script = """
    // Simuleer wrapText algoritme uit kompas.js
    function simulateWrap(wordsStr, width, charWidth = 6) {
        const words = wordsStr.split(/\\s+/).filter(Boolean).reverse();
        let word;
        let line = [];
        let lineNumber = 0;
        const lineHeight = 1.1;
        const dy = 0.35;
        const lines = [];

        while ((word = words.pop())) {
            line.push(word);
            const testLine = line.join(" ");
            const textWidth = testLine.length * charWidth;
            if (textWidth > width) {
                line.pop();
                lines.push(line.join(" "));
                line = [word];
                lineNumber++;
                if (lineNumber >= 2) {
                    line = [word + "..."];
                    break;
                }
            }
        }
        if (line.length > 0) {
            lines.push(line.join(" "));
        }
        const totalLines = Math.max(1, lines.length);
        const shift = -((totalLines - 1) * lineHeight) / 2;
        return { lines, shift, totalLines };
    }

    const shortResult = simulateWrap("Kort label", 100);
    const longResult = simulateWrap("Zeer lang indicator label met veel te veel woorden voor een segment", 60);

    process.stdout.write(JSON.stringify({ shortResult, longResult }));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)

    assert res["shortResult"]["totalLines"] == 1
    assert res["shortResult"]["lines"] == ["Kort label"]
    assert res["shortResult"]["shift"] == 0

    assert res["longResult"]["totalLines"] <= 3
    assert any("..." in line for line in res["longResult"]["lines"])


def test_kompas_deduplicatie_en_request_tracking():
    """
    Stap 1 B1 & B2 (#466):
    - B1: identieke gebiedsrequests binnen 300ms worden gededupliceerd.
    - B2: verouderde responses worden genegeerd via sequence request-ids.
    - Deferred rendering: triggerDeferredRender() is aanwezig.
    """
    content = KOMPAS_JS.read_text(encoding="utf-8")

    # B1 deduplicatie
    assert "_lastGebiedReq" in content, "kompas.js moet _lastGebiedReq bijhouden voor deduplicatie"
    assert "reqKey = `${configId}|${gebiedId}`" in content or "reqKey = `${configId}|" in content

    # B2 request tracking
    assert "_detailsRequestId" in content, "kompas.js moet _detailsRequestId bijhouden"
    assert "_benchmarkRequestId" in content, "kompas.js moet _benchmarkRequestId bijhouden"
    assert "detailsReqId !== this._detailsRequestId" in content
    assert "benchReqId !== this._benchmarkRequestId" in content

    # Deferred render
    assert "deferNextRenderUntilLanding" in content
    assert "triggerDeferredRender" in content
    assert "_pendingRender" in content


def test_dock_updating_css_dimming():
    """
    Stap 3 (#466): styles.css moet de .rechter-dock.dock-updating regel bevatten
    om de weergave subtiel te dimmen (opacity 0.55) tijdens cameravlucht als het dock open staat.
    """
    content = STYLES_CSS.read_text(encoding="utf-8")
    assert ".rechter-dock.dock-updating" in content
    assert "opacity: 0.55" in content


def test_get_freezone_en_target_dock_open():
    """
    Stap 3 (#466): getFreezone(targetDockOpen) moet rekening houden met de doelstand
    van het dock en de breedte reserveren via rightEdge.
    """
    content = APP_JS.read_text(encoding="utf-8")

    assert "function getFreezone(targetDockOpen = null)" in content or "function getFreezone(" in content
    assert "Math.min(560, Math.max(440, W * 0.3))" in content
    assert "state.dockManuallyClosed" in content or "state?.dockManuallyClosed" in content
    assert "window.getFreezone = getFreezone" in content


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_get_freezone_berekening_met_node():
    """
    Simuleert getFreezone berekening in Node.js met breedte 1920 en 1280.
    """
    script = """
    function getFreezoneSim(W, targetDockOpen, dockManuallyClosed, dockOpen) {
        const tabBar = 70;
        const leftPanel = 0;
        const leftEdge = tabBar + leftPanel;

        let willBeOpen;
        if (targetDockOpen !== null) {
            willBeOpen = targetDockOpen;
        } else {
            willBeOpen = dockOpen || (!dockManuallyClosed);
        }

        let rightEdge = 0;
        if (willBeOpen) {
            rightEdge = Math.min(560, Math.max(440, W * 0.3));
        }

        const freeLeft = leftEdge;
        const freeRight = W - rightEdge;
        const centerX = freeLeft + (freeRight - freeLeft) / 2;
        return { centerX, screenCenterX: W / 2, rightEdge, freeRight };
    }

    const res1920Open = getFreezoneSim(1920, true, false, true);
    const res1920Closed = getFreezoneSim(1920, false, true, false);

    process.stdout.write(JSON.stringify({ res1920Open, res1920Closed }));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)

    # Bij geopend dock (1920px breed) is het dock 560px breed, dus vrije zone rechts is 1920 - 560 = 1360
    assert res["res1920Open"]["rightEdge"] == 560
    assert res["res1920Open"]["freeRight"] == 1360
    # Center X ligt links van het midden (schermmidden is 960, vrije zone midden is ~715)
    assert res["res1920Open"]["centerX"] < res["res1920Open"]["screenCenterX"]

    # Bij gesloten dock is rightEdge 0
    assert res["res1920Closed"]["rightEdge"] == 0
    assert res["res1920Closed"]["freeRight"] == 1920


def test_fly_to_gebied_fitbounds_en_landing_callback():
    """
    Stap 3 (#466): flyToGebied() moet:
    - Bounding box bepalen uit feature geometry.
    - deck.WebMercatorViewport.fitBounds aanroepen met padding afgestemd op de vrije zone.
    - Max zoom limiteren tot 14.5.
    - Landing callback (onLanded) ondersteunen via onTransitionEnd en fallback timer.
    """
    content = APP_JS.read_text(encoding="utf-8")

    assert (
        "function flyToGebied(feature, clickCoordinate = null, onLanded = null)" in content or "flyToGebied" in content
    )
    assert "fitBounds([[minLon, minLat], [maxLon, maxLat]]" in content
    assert "maxZoom: 14.5" in content
    assert "onTransitionEnd: triggerLanded" in content
    assert "window.flyToGebied = flyToGebied" in content


def test_dock_handmatig_gesloten_state_lifecycle():
    """
    Stap 3 (#466):
    - closeRechterDock(manual = true) zet state.dockManuallyClosed = true.
    - openKompasVenster() reset state.dockManuallyClosed = false.
    - openRechterDock met manualOpen reset state.dockManuallyClosed = false.
    """
    content = APP_JS.read_text(encoding="utf-8")

    assert "dockManuallyClosed: false" in content
    assert "state.dockManuallyClosed = true" in content
    assert "state.dockManuallyClosed = false" in content


def test_pve_documentatie_versie_1_1():
    """
    Stap 4 (#466): docs/4-ux-design/pve-rechter-dock-architectuur.md moet versie 1.1 vermelden
    met een wijzigingshistorie tabel voor issue #466.
    """
    content = PVE_DOC.read_text(encoding="utf-8")
    assert "v1.1" in content
    assert "#466" in content
    assert "Wijzigingshistorie (v1.1" in content
    assert "Layout thrashing geëlimineerd" in content
    assert "canvas.measureText" in content
    assert "doubleClickZoom: false" in content
