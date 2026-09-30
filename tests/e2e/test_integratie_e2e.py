"""
TC-06-001 — E2E Beleidsadviseur IJsselmeerkust (docs/testcases/06-integratie-e2e).

Aangepast aan de sample dataset: Makkum zit er niet in, dus het pad loopt via
Workum (stap 3) en Koudum als vergelijkingskern (stap 6/9). De onboarding loopt
via de D-Omni Assistent: 'help' → profiel Beleidsadviseur → actieknoppen
(Buurten, gemeente Súdwest-Fryslân, Kompas openen). Het scenario is
deterministisch (geen LLM nodig).
"""

import csv
import io
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

from e2e_helpers import (
    AANTAL_SAMPLE_BUURTEN, KOUDUM, WORKUM,
    klik_buurt_op_kaart, kompas_namen, laad_buurtenkaart, open_indicator_in_kompas, open_kompas,
    open_paneel, selecteer_buurt_via_app, verplaats_kompasvenster_rechts, wacht_op_kaartdata, wacht_op_selectie, wacht_op_zonnediagram,
)


def _chat_actie(page, label_regex):
    knop = page.locator("#chat-messages .chat-actie-btn").filter(has_text=re.compile(label_regex)).last
    expect(knop).to_be_visible()
    knop.click()
    expect(knop).to_have_class(re.compile(r"actie-activated"))


def test_tc_06_001_beleidsadviseur_ijsselmeerkust(app_page_fresh, tmp_path: Path):
    """TC-06-001 fase 1, 3 en 4 (stap 1-3, 6-10), aangepast: Workum/Koudum i.p.v. Makkum."""
    page = app_page_fresh

    # ── Fase 1 — Oriëntatie ──────────────────────────────────────────────────
    # 1. App opent; nieuwe bezoeker krijgt de welkomstmodal
    modal = page.get_by_role("dialog", name="Welkom bij D-OmniTwin")
    expect(modal).to_be_visible()
    page.locator("#welcome-skip-btn").click()
    expect(modal).to_be_hidden()

    # Assistent: help → profielkeuze → Beleidsadviseur
    page.get_by_role("button", name="D-Omni Assistent", exact=True).click()
    expect(page.locator("#chat-panel")).to_have_class(re.compile(r"\bopen\b"))
    page.locator("#chat-input").fill("help")
    page.get_by_role("button", name="Vraag versturen").click()
    _chat_actie(page, r"Beleidsadviseur")
    expect(page.locator("#chat-messages .chat-narrative").last).to_contain_text("IJsselmeerkust")

    # 2. Scenario-acties: buurten tonen, gemeente Súdwest-Fryslân, Kompas openen
    _chat_actie(page, r"Toon: Buurten")
    wacht_op_kaartdata(page, AANTAL_SAMPLE_BUURTEN)
    _chat_actie(page, r"Gemeente: Súdwest-Fryslân")
    expect(page.locator("#gemeente-info")).to_contain_text("Súdwest-Fryslân")
    page.wait_for_function("() => window.state.currentGemeenteCode === '1900'")
    wacht_op_kaartdata(page, AANTAL_SAMPLE_BUURTEN)
    _chat_actie(page, r"Open het D-Omni Kompas")
    expect(page.locator("#kompas-window")).to_be_visible()

    # Assistent sluiten en Kompas-venster opzij slepen zodat de kaart vrij is
    page.get_by_role("button", name="Assistent sluiten").click()
    verplaats_kompasvenster_rechts(page)

    # 3. Selecteer de eerste kern op de kaart (echte klik) → Kompas laadt het gebied
    klik_buurt_op_kaart(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    expect(page.locator("#selection-badge")).to_contain_text("Workum")
    expect(page.locator("#kompas-info")).to_contain_text("Workum", timeout=30_000)
    wacht_op_zonnediagram(page)

    # 6/9. Vergelijkingskern toevoegen → Kompas toont het gemiddelde (benchmark)
    selecteer_buurt_via_app(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM])
    expect(page.locator("#kompas-info")).to_contain_text("Gemiddelde van 2 gebieden", timeout=30_000)
    expect(page.locator("#kompas-info")).to_contain_text("Workum, Koudum")
    wacht_op_zonnediagram(page)

    # ── Fase 3 — Wonen (stap 7-9) ────────────────────────────────────────────
    open_indicator_in_kompas(page, "Wonen", "Gemiddeld energielabel")
    expect(page.locator("#details-trend")).to_have_text("Vergelijking")
    expect(page.locator("#details-value")).to_contain_text("⌀")

    # ── Fase 4 — Sociaal domein (stap 10) ────────────────────────────────────
    page.locator("#kompas-reset").click()
    wacht_op_zonnediagram(page)
    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    expect(page.locator("#details-bron")).to_contain_text("Kerncijfers")

    # Indicator uit het Kompas kleurt de kaart in (Kompas → kaart-sync)
    page.wait_for_function(
        "() => window.state.currentData && window.state.currentData.metadata"
        " && window.state.currentData.metadata.indicator_naam === 'Participatiewet totaal'",
        timeout=30_000,
    )

    assert page.console_fouten == [], "\n".join(page.console_fouten)


@pytest.mark.xfail(strict=True, reason="TC-06-001 stap 13-14: CSV-export is kapot — exportCSV() zet de CSV "
                                       "onge-encodeerd in een data-URI, waardoor de '#' van kleurcodes de inhoud "
                                       "afkapt (alleen de kopregel blijft over)")
def test_tc_06_001_fase5_export_bronvermelding(app_page, tmp_path: Path):
    """TC-06-001 stap 13-14: tabelexport (CSV) van de ingekleurde kaart bevat per buurt
    de waarde met bron en peildatum."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    open_kompas(page, "Workum")
    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    page.wait_for_function(
        "() => window.state.currentData && window.state.currentData.metadata"
        " && window.state.currentData.metadata.indicator_naam === 'Participatiewet totaal'",
        timeout=30_000,
    )
    page.get_by_role("button", name="Kompasvenster sluiten").click()

    open_paneel(page, "Exporteren")
    csv_knop = page.locator("#export-csv-btn")
    expect(csv_knop).to_be_enabled()
    with page.expect_download() as dl:
        csv_knop.click()
    pad = tmp_path / "export.csv"
    dl.value.save_as(pad)
    rijen = list(csv.DictReader(io.StringIO(pad.read_text(encoding="utf-8"))))
    assert len(rijen) == AANTAL_SAMPLE_BUURTEN
    assert {"naam", "indicator_waarde", "bron", "jaar"} <= set(rijen[0]), rijen[0].keys()
    workum = next(r for r in rijen if r["naam"] == "Workum")
    assert "Kerncijfers" in workum["bron"] and re.fullmatch(r"(19|20)\d{2}", workum["jaar"])


@pytest.mark.xfail(strict=True, reason="TC-06-001 fase 2: thema Verkeer heeft in de sample geen indicatoren "
                                       "(bereikbaarheid/afstand OV ontbreekt)")
def test_tc_06_001_fase2_verkeer_bereikbaarheid(app_page):
    """TC-06-001 stap 4-6: indicator bereikbaarheid/afstand OV vindbaar onder Verkeer."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    open_kompas(page, "Workum")
    verkeer = page.evaluate(
        "() => window.kompasViz.root.descendants().find(d => d.data.name === 'Verkeer')"
        ".descendants().filter(d => d.data.uuid).map(d => d.data.name)"
    )
    assert verkeer, f"geen indicatoren onder Verkeer (Kompas: {len(kompas_namen(page))} knopen)"


@pytest.mark.skip(reason="TC-06-001 stap 11-12 en acceptatiecriterium 'zonder uitleg': kernniveau-detail, "
                         "historische trend en begrijpelijkheid vergen handmatige review "
                         "(trend: zie TC-02-002 xfail)")
def test_tc_06_001_handmatige_review():
    """TC-06-001 stap 11-12 en gebruikersbeleving."""


@pytest.mark.skip(reason="TC-06-001 stap 13 (PDF-rapport): gebiedsdossier gebruikt de LLM; "
                         "niet deterministisch in de sample-stack")
def test_tc_06_001_pdf_rapport():
    """TC-06-001 stap 13: PDF-rapport genereren."""
