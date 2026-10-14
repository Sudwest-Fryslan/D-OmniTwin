"""
Maakt de screenshots voor docs/overzicht.md (docs/images/) reproduceerbaar opnieuw.

Draait tegen een stack met de sample dataset en richt zich op Bolsward
(Bolsward-Zuidoost bevat demodata). Vaste venstergrootte en licht thema,
zodat de beelden na elke UI-wijziging opnieuw gemaakt kunnen worden:

    docker run --rm --network d-omnitwin_default -v "$PWD":/work -w /work \
        -e OMNITWIN_BASE_URL=http://traefik -e ADMIN_USER=admin -e ADMIN_PASSWORD=... \
        mcr.microsoft.com/playwright/python:v1.63.0-noble \
        sh -c "pip install -q playwright==1.63.0 && python scripts/docs/maak_screenshots.py"

Zonder ADMIN_PASSWORD wordt het beheerscherm overgeslagen.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
UIT = Path(__file__).resolve().parents[2] / "docs" / "images"
VIEWPORT = {"width": 1440, "height": 860}
BOLSWARD = {"longitude": 5.535, "latitude": 53.063, "zoom": 13.1}


def wacht_op_kaart(page):
    page.wait_for_function("() => window.state && window.state.deckgl", timeout=60000)
    page.wait_for_timeout(1500)


def zet_beeld(page, longitude, latitude, zoom):
    page.evaluate(
        """([lon, lat, z]) => {
            state.currentViewState = {...state.currentViewState, longitude: lon, latitude: lat,
                                      zoom: z, pitch: 0, bearing: 0, transitionDuration: 0};
            state.deckgl.setProps({viewState: state.currentViewState});
        }""",
        [longitude, latitude, zoom],
    )
    page.wait_for_timeout(4000)  # achtergrondkaart (PDOK) laden


def kaart_met_indicator(page):
    page.goto(f"{BASE}/", wait_until="networkidle")
    wacht_op_kaart(page)
    skip = page.get_by_role("button", name="Overslaan — direct naar de kaart")
    if skip.count():
        skip.click()
    page.locator("#gebiedstype-select, select").first.select_option(label="CBS Buurten")
    page.wait_for_timeout(2500)
    # via JS: het paneel staat buiten beeld zolang het dicht is
    page.evaluate("""() => {
        [...document.querySelectorAll('.accordion-header')].find(e => e.textContent.includes('Klimaat')).click();
        [...document.querySelectorAll('.indicator-item')].find(e => e.textContent.includes('koele plek')).click();
    }""")
    page.wait_for_timeout(4000)
    verberg_tips(page)
    zet_beeld(page, **BOLSWARD)


def verberg_tips(page):
    page.evaluate("() => document.getElementById('contextual-tooltip-close')?.click()")
    page.add_style_tag(content="#contextual-tooltip { display: none !important; }")


def selecteer_bolsward_zuidoost(page):
    page.evaluate(
        """() => {
            const layer = state.deckgl.props.layers.find(l => l && l.props && l.props.pickable && l.props.data);
            const data = layer.props.data.features || layer.props.data;
            const f = data.find(x => (x.properties.id || x.properties.gebied_id) === 'BU19000002');
            layer.props.onClick({object: f, coordinate: null});
        }"""
    )
    page.wait_for_timeout(3000)


def main():
    UIT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, locale="nl-NL", color_scheme="light")
        page = ctx.new_page()

        kaart_met_indicator(page)
        page.screenshot(path=str(UIT / "kaart-bolsward.jpg"), type="jpeg", quality=82)
        print("kaart-bolsward.jpg")

        selecteer_bolsward_zuidoost(page)
        zet_beeld(page, **BOLSWARD)
        page.evaluate("() => window.openKompasVenster && window.openKompasVenster()")
        page.wait_for_selector(".floating-window", state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(UIT / "kompas-bolsward-zuidoost.jpg"), type="jpeg", quality=82)
        print("kompas-bolsward-zuidoost.jpg")

        page.locator("#kompas-window .btn-close").click()
        page.get_by_role("button", name="D-Omni Assistent").click()
        chat = page.locator("#chat-input")
        chat.fill("Ik ben beleidsadviseur")
        chat.press("Enter")
        page.get_by_text("Open het D-Omni Kompas").last.wait_for(timeout=60000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(UIT / "chat-beleidsadviseur.jpg"), type="jpeg", quality=82)
        print("chat-beleidsadviseur.jpg")

        wachtwoord = os.environ.get("ADMIN_PASSWORD")
        if wachtwoord:
            page.goto(f"{BASE}/admin/login")
            page.get_by_label("Gebruikersnaam").fill(os.environ.get("ADMIN_USER", "admin"))
            page.get_by_label("Wachtwoord").fill(wachtwoord)
            page.get_by_role("button", name="Aanmelden").click()
            page.wait_for_url("**/admin/dashboard", timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(UIT / "beheer-dashboard.jpg"), type="jpeg", quality=82)
            print("beheer-dashboard.jpg")
        browser.close()


if __name__ == "__main__":
    main()
