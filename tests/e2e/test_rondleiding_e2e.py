"""Browser-E2E-tests voor de interactieve rondleiding en welkomstmodal (#442).

Toetst:
1. De rondleiding start niet vanzelf; start via #tour-start-btn (?), doorloopt 4 stappen met
   drie-regelige uitleg (Wat zie je / Wat betekent het / Probeer het), selecteert een voorbeeldbuurt,
   sluit met Escape zonder dat de actieve indicator verloren gaat, ruimt de voorbeeldselectie op en
   zet de focus terug op de startknop.
2. De rondleiding is ook te starten via #chat-start-tour-btn in de D-Omni Assistent.
3. De welkomstmodal biedt 2 primaire ingangen ('Mijn buurt opzoeken' met gemockte POST /api/locatie/buurt
   en 'Start rondleiding (1 min)'), naast 'Handleiding' en 'Overslaan'.
"""

from __future__ import annotations

import json

import pytest
from e2e_helpers import WORKUM, laad_buurtenkaart, wacht_op_selectie
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_rondleiding_vier_stappen_voorbeeldbuurt_escape_behoudt_indicator_en_focus(app_page):
    """? opent de 4-staps spotlight-tour; Escape sluit zonder de actieve indicator te wissen."""
    page = app_page
    laad_buurtenkaart(page)

    # Tour start nooit automatisch
    expect(page.locator("#spotlight-tour-overlay")).to_have_count(0)

    indicator_voor = page.evaluate("() => window.state && window.state.currentIndicator")
    assert indicator_voor, "Startkaart moet een actieve indicator hebben (#443)"
    assert page.evaluate("() => window.state.selectedGebiedIds.size") == 0

    # Start via de vaste ?-knop in de linker navigatiebalk
    tour_knop = page.locator("#tour-start-btn")
    expect(tour_knop).to_be_visible()
    tour_knop.click()

    popover = page.locator("#spotlight-popover")
    expect(popover).to_be_visible()
    expect(page.locator("#spotlight-step-counter")).to_have_text("Stap 1 van 4")
    expect(page.locator("#spotlight-step-title")).to_contain_text("1. De kaart")

    # Drie-regelige uitleg aanwezig + voorbeeldbuurt automatisch geselecteerd
    expect(page.locator("#spotlight-wat")).not_to_be_empty()
    expect(page.locator("#spotlight-betekent")).to_contain_text("Voorbeeld:")
    expect(page.locator("#spotlight-probeer")).not_to_be_empty()
    assert page.evaluate("() => window.state.selectedGebiedIds.size") == 1
    expect(page.locator("#open-rapport-btn")).to_be_enabled()

    # Stap 2 -> 3 -> 4 via Volgende
    page.locator("#spotlight-next-btn").click()
    expect(page.locator("#spotlight-step-counter")).to_have_text("Stap 2 van 4")
    expect(page.locator("#spotlight-step-title")).to_contain_text("2. Indicator")

    page.locator("#spotlight-next-btn").click()
    expect(page.locator("#spotlight-step-counter")).to_have_text("Stap 3 van 4")
    expect(page.locator("#spotlight-step-title")).to_contain_text("3. Het D-Omni Kompas")

    page.locator("#spotlight-next-btn").click()
    expect(page.locator("#spotlight-step-counter")).to_have_text("Stap 4 van 4")
    expect(page.locator("#spotlight-next-btn")).to_have_text("Klaar")

    # Escape sluit de tour, behoudt de actieve indicator, ruimt de voorbeeldbuurt op en geeft focus terug
    page.keyboard.press("Escape")
    expect(popover).to_be_hidden()

    indicator_na = page.evaluate("() => window.state && window.state.currentIndicator")
    assert indicator_na == indicator_voor, "Escape tijdens de rondleiding mag de actieve indicator niet wissen"
    assert page.evaluate("() => window.state.selectedGebiedIds.size") == 0
    assert page.evaluate("() => document.activeElement && document.activeElement.id") == "tour-start-btn"


def test_rondleiding_start_vanuit_assistent_chip(app_page):
    """De actieknop 'Geef me een rondleiding' in het welkomstbericht van de Assistent start de tour."""
    page = app_page
    laad_buurtenkaart(page)

    page.locator("#chat-toggle-btn").click()
    chip = page.locator("#chat-start-tour-btn")
    expect(chip).to_be_visible()
    chip.click()

    expect(page.locator("#spotlight-popover")).to_be_visible()
    expect(page.locator("#spotlight-step-counter")).to_have_text("Stap 1 van 4")

    page.locator("#spotlight-skip-btn").click()
    expect(page.locator("#spotlight-popover")).to_be_hidden()


def test_welkomstmodal_mijn_buurt_met_gemockte_locatie(app_page_fresh):
    """'Mijn buurt opzoeken' in de welkomstmodal zoekt via /api/locatie/buurt en selecteert de buurt."""
    page = app_page_fresh

    def mock_locatie(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"gebied_id": WORKUM, "naam": "Workum"}),
        )

    page.route("**/api/locatie/buurt", mock_locatie)

    modal = page.get_by_role("dialog", name="Welkom bij D-OmniTwin")
    expect(modal).to_be_visible()

    buurt_knop = page.locator("#welcome-btn-buurt")
    expect(buurt_knop).to_be_visible()
    expect(page.locator("#welcome-btn-tour")).to_be_visible()

    buurt_knop.click()
    form = page.locator("#welcome-buurtkiezer-wrap form.chat-buurtkiezer")
    expect(form).to_be_visible()

    form.locator("input").fill("8711 AA")
    form.locator("button[type='submit']").click()

    expect(modal).to_be_hidden()
    wacht_op_selectie(page, [WORKUM])
