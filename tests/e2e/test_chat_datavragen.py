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

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
LLM_TIMEOUT_MS = int(os.environ.get("E2E_LLM_TIMEOUT", "300")) * 1000
ROOT = Path(__file__).resolve().parents[2]

DATAVRAAG = re.compile(r"\b(welke buurt|hoe staat het|waar\b.*\b(grootst|meeste|verst))", re.IGNORECASE)


def laad_usecases():
    uit = {}
    for f in sorted((ROOT / "usecases").glob("*/usecase.json")):
        u = json.loads(f.read_text(encoding="utf-8"))
        if DATAVRAAG.search(u["persona"]["vraag"]):
            uit[f"{u['id']} {f.parent.name}"] = u
    return uit


USE_CASES = laad_usecases()

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

    # Toon op kaart: gebieden geselecteerd en indicator op de kaart
    toon = next(a for a in data["acties"] if a["type"] == "TOON_OP_KAART")
    with page.expect_response(lambda r: "/api/gebiedsmonitor/kaart_data/" in r.url and r.ok, timeout=60_000):
        bericht.locator(".chat-actie-btn", has_text="Toon op kaart").first.click()
    page.wait_for_function(
        "([uuid, n]) => window.state.currentIndicator === uuid && window.state.selectedGebiedIds.size === n",
        arg=[toon["indicator_uuid"], len(toon["gebied_ids"])],
        timeout=30_000,
    )
    geselecteerd = page.evaluate("() => [...window.state.selectedGebiedIds].sort()")
    assert geselecteerd == sorted(toon["gebied_ids"])
