"""
E2E (#149): een datavraag per use case in de chat, in de browser.

Per use case met een datavraag (usecases/*/usecase.json, persona.vraag):
- het antwoord verschijnt met een bronlabel (AI-gegenereerd of Rule-based) en een bronregel;
- de knoppen Toon op kaart, Open Kompas en Rapport staan eronder;
- 'Toon op kaart' selecteert de gebieden uit het antwoord en zet de indicator op de kaart;
- het antwoord noemt de verwachte buurten (alleen gecontroleerd met E2E_LLM=1, want
  de vaste tekst zonder model noemt ze altijd).

Zelfstandig (eigen browser-fixture). Draaien in de Playwright-container, zie tests/e2e/README.md:

    OMNITWIN_BASE_URL=http://traefik pytest -m e2e tests/e2e/test_chat_datavragen.py

Een lokaal model kan traag zijn: E2E_LLM_TIMEOUT (seconden, standaard 300).
"""

import json
import os
import re
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect

from e2e_helpers import TRAAG_MS, klik_chatactie, wacht_op_kaart_in_rust  # noqa: E402

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
LLM_TIMEOUT_MS = int(os.environ.get("E2E_LLM_TIMEOUT", "300")) * 1000
ROOT = Path(__file__).resolve().parents[2]

DATAVRAAG = re.compile(r"\b(welke buurt|hoe staat het|waar\b.*\b(grootst|meeste|verst))", re.IGNORECASE)


def laad_usecases():
    uit = {}
    for f in sorted((ROOT / "usecases").glob("*/usecase.json")):
        u = json.loads(f.read_text(encoding="utf-8"))
        if "datasets" in u:  # use case via de laad-API (status ontwerp), geen demopakket
            continue
        if DATAVRAAG.search(u["persona"]["vraag"]):
            uit[f"{u['id']} {f.parent.name}"] = u
    return uit


USE_CASES = laad_usecases()
# TC-06-004, de demo-kernvraag: geen vraagpatroon, wel gebied + indicator
USE_CASES["TC-06-004 hoe-groen"] = {
    "persona": {"vraag": "Hoe groen is Bolsward-Zuidoost?"},
    "verwacht": {"verwacht": "Bolsward-Zuidoost"},
    "data": {"gebieden": {"BU19000002": "Bolsward-Zuidoost"}},
}

_INIT = """
() => {
  try {
    localStorage.setItem('omnitwin_welcomed', '1');
    for (const k of ['omnitwin_tt_indicator', 'omnitwin_tt_buurt', 'omnitwin_tt_kompas', 'omnitwin_tt_ai']) {
      localStorage.setItem(k, '1');
    }
    localStorage.removeItem('omnitwin-gemeente');
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


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="nl-NL")
    context.add_init_script(f"({_INIT})()")
    pg = context.new_page()
    pg.set_default_timeout(20_000)
    pg.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    pg.wait_for_function(
        "() => window.state && window.state.deckgl && window.chatPanel"
        " && document.querySelectorAll('#gebiedstype-select option').length > 1",
        timeout=60_000,
    )
    yield pg
    context.close()


@pytest.mark.parametrize("uc", USE_CASES)
def test_datavraag_in_de_chat(page, uc):
    u = USE_CASES[uc]
    page.locator("#chat-toggle-btn").click()
    invoer = page.locator("#chat-input")
    invoer.fill(u["persona"]["vraag"])
    with page.expect_response(lambda r: r.url.endswith("/api/chat") and r.request.method == "POST",
                              timeout=LLM_TIMEOUT_MS) as resp:
        invoer.press("Enter")
    data = resp.value.json()
    assert data["intent"] == "DATAVRAAG", data

    bericht = page.locator(".chat-message-assistant").last
    expect(bericht.locator(".chat-narrative")).to_have_text(data["narrative"])
    expect(bericht.locator(".chat-source-badge")).to_have_text(re.compile("AI-gegenereerd|Rule-based"))
    if data["debug"].get("llm_gebruikt"):
        expect(bericht.locator(".chat-disclaimer")).to_be_visible()
    expect(bericht.locator(".chat-bronregel")).to_contain_text("Bron:")
    for b in data["bronnen"]:
        expect(bericht.locator(".chat-bronregel")).to_contain_text(b["indicator"])

    for label in ("Toon op kaart", "Open Kompas", "Rapport"):
        expect(bericht.locator(".chat-actie-btn", has_text=label).first).to_be_visible()

    if os.environ.get("E2E_LLM") == "1":
        for naam in u["data"]["gebieden"].values():
            if re.search(rf"\b{re.escape(naam)}\b(?!-)", u["verwacht"]["verwacht"]):
                assert naam in data["narrative"], f"{uc}: {naam} ontbreekt in: {data['narrative']}"

    # De kaart beweegt zonder klik mee: indicatorlaag, selectie en ingezoomd op de gebieden
    ka = data["kaart_actie"]
    page.wait_for_function(
        "([uuid, n]) => window.state.currentIndicator === uuid && window.state.selectedGebiedIds.size === n",
        arg=[ka["indicator_uuid"], len(ka["gebied_ids"])],
        timeout=60_000,
    )
    expect(page.locator("#selection-badge")).to_be_visible()
    # Inzoom-animatie: de camera beweegt alleen op animatieframes. In CI (software-WebGL)
    # blokkeert shadercompilatie na het laden van een laag de renderer soms tientallen
    # seconden; daarom de wachttijd voor trage stappen (TRAAG_MS) en een vast pollinterval (#194)
    page.wait_for_function("() => (window.state.currentViewState?.zoom || 0) >= 11", polling=100, timeout=TRAAG_MS)
    wacht_op_kaart_in_rust(page)
    camera = page.evaluate("""(ids) => {
        const set = new Set(ids); let x0 = 180, x1 = -180, y0 = 90, y1 = -90;
        const walk = a => { if (typeof a[0] === 'number') { x0 = Math.min(x0, a[0]); x1 = Math.max(x1, a[0]);
            y0 = Math.min(y0, a[1]); y1 = Math.max(y1, a[1]); } else a.forEach(walk); };
        window.state.currentData.features.filter(f => set.has(f.properties.id)).forEach(f => walk(f.geometry.coordinates));
        const v = window.state.currentViewState;
        return { lon: v.longitude, lat: v.latitude, zoom: v.zoom, bbox: [x0, y0, x1, y1] };
    }""", ka["gebied_ids"])
    x0, y0, x1, y1 = camera["bbox"]
    marge_x, marge_y = (x1 - x0) * 1.5 + 0.02, (y1 - y0) * 1.5 + 0.02  # vrije zone naast panelen
    assert x0 - marge_x <= camera["lon"] <= x1 + marge_x and y0 - marge_y <= camera["lat"] <= y1 + marge_y, camera
    assert camera["zoom"] >= 11, f"niet ingezoomd: {camera}"

    # Toon op kaart: gebieden geselecteerd en indicator op de kaart
    toon = next(a for a in data["acties"] if a["type"] == "TOON_OP_KAART")
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok, timeout=60_000):
        # Niet direct klikken: na het meebewegen van de kaart kan de renderer in CI (software-
        # WebGL) even geen frames tekenen, en dan hangt Playwrights stabiliteitscheck (#194)
        klik_chatactie(page, bericht.locator(".chat-actie-btn", has_text="Toon op kaart").first, "Toon op kaart")
    page.wait_for_function(
        "([uuid, n]) => window.state.currentIndicator === uuid && window.state.selectedGebiedIds.size === n",
        arg=[toon["indicator_uuid"], len(toon["gebied_ids"])],
        timeout=30_000,
    )
    geselecteerd = page.evaluate("() => [...window.state.selectedGebiedIds].sort()")
    assert geselecteerd == sorted(toon["gebied_ids"])


def test_vraag_van_eduard_toont_relevantie_als_woord(page):
    """#233: 'hoeveel % is bejaard bij mij in de buurt?' met Bolsward-Zuidoost als eigen buurt:
    het cijfer voor die buurt, de indicator als onderbouwing en relevantie als woord, geen percentage."""
    page.locator("#chat-toggle-btn").click()
    with page.expect_response(lambda r: r.url.endswith("/api/chat") and r.request.method == "POST",
                              timeout=LLM_TIMEOUT_MS) as resp:
        page.evaluate("() => window.chatPanel.sendVraag('hoeveel % is bejaard bij mij in de buurt?',"
                      " {huidig_gebied_id: 'BU19000002', geen_llm: true})")
    data = resp.value.json()
    assert data["intent"] == "DATAVRAAG", data
    bericht = page.locator(".chat-message-assistant").last
    expect(bericht.locator(".chat-narrative")).to_contain_text("Bolsward-Zuidoost: ")
    expect(bericht.locator(".chat-indicatoren-label")).to_have_text("Onderbouwing: 2 indicatoren")
    expect(bericht.locator(".chat-ind-naam")).to_have_text(["65+ jaar (%)", "80 jaar of ouder (%)"])
    expect(bericht.locator(".chat-ind-score")).to_have_text(["sterk", "sterk"])
