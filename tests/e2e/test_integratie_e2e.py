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
import os
import re
from pathlib import Path

import pytest
from e2e_helpers import (
    BOLSWARD_ZUIDOOST,
    KOUDUM,
    WORKUM,
    aantal_kaartgebieden,
    geschaald,
    klik_buurt_op_kaart,
    klik_chatactie,
    kompas_namen,
    laad_buurtenkaart,
    open_indicator_in_kompas,
    open_kompas,
    open_paneel,
    selecteer_buurt_via_app,
    traag_ms,
    verplaats_kompasvenster_rechts,
    wacht_op_kaartdata,
    wacht_op_selectie,
    wacht_op_zonnediagram,
)
from playwright.sync_api import expect


def _chat_actie(page, label_regex):
    knop = page.locator("#chat-messages .chat-actie-btn").filter(has_text=re.compile(label_regex)).last
    klik_chatactie(page, knop, label_regex)
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
    _open_assistent(page)
    page.locator("#chat-input").fill("help")
    page.get_by_role("button", name="Vraag versturen").click()
    _chat_actie(page, r"Beleidsadviseur")
    expect(page.locator("#chat-messages .chat-narrative").last).to_contain_text("IJsselmeerkust")

    # 2. Scenario-acties: buurten tonen, gemeente Súdwest-Fryslân, Kompas openen
    _chat_actie(page, r"Toon: Buurten")
    wacht_op_kaartdata(page)
    _chat_actie(page, r"Gemeente: Súdwest-Fryslân")
    expect(page.locator("#gemeente-info")).to_contain_text("Súdwest-Fryslân")
    page.wait_for_function("() => window.state.currentGemeenteCode === '1900'")
    wacht_op_kaartdata(page)
    _chat_actie(page, r"Open het D-Omni Kompas")
    expect(page.locator("#dock-panel-kompas")).to_be_visible()

    # Assistent/dock sluiten en venster opzij slepen (indien zwevend)
    if page.locator("#dock-panel-chat").is_visible():
        page.locator("#dock-btn-close").click()
    verplaats_kompasvenster_rechts(page)

    # 3. Selecteer de eerste kern op de kaart (echte klik) → Kompas laadt het gebied. Scenariotest:
    # de kaartklik zelf toetst TC-01-001; lukt die hier niet, dan als laatste redmiddel pick + onClick
    klik_buurt_op_kaart(page, WORKUM, terugval=True)
    wacht_op_selectie(page, [WORKUM])
    expect(page.locator("#selection-badge")).to_contain_text("Workum")
    expect(page.locator("#kompas-info")).to_contain_text("Workum", timeout=traag_ms())
    wacht_op_zonnediagram(page)

    # 6/9. Vergelijkingskern toevoegen → Kompas toont het gemiddelde (benchmark)
    selecteer_buurt_via_app(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM])
    expect(page.locator("#kompas-info")).to_contain_text("Gemiddelde van 2 gebieden", timeout=traag_ms())
    expect(page.locator("#kompas-info")).to_contain_text("Workum, Koudum")
    wacht_op_zonnediagram(page)

    # ── Fase 3 — Wonen (stap 7-9) ────────────────────────────────────────────
    open_indicator_in_kompas(page, "Wonen", "Gemiddeld energielabel")
    expect(page.locator("#details-trend")).to_have_text("Vergelijking")
    expect(page.locator("#details-value")).to_contain_text("⌀")

    # ── Fase 4 — Sociaal domein (stap 10) ────────────────────────────────────
    page.locator("#kompas-reset").click()
    expect(page.locator("#kompas-details-panel")).not_to_be_visible()
    expect(page.locator("#kompas-breadcrumb")).to_contain_text("Start")
    wacht_op_zonnediagram(page)
    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    expect(page.locator("#details-bron")).to_contain_text("Kerncijfers")

    # Indicator uit het Kompas kleurt de kaart in (Kompas → kaart-sync)
    page.wait_for_function(
        "() => window.state.currentData && window.state.currentData.metadata"
        " && window.state.currentData.metadata.indicator_naam === 'Participatiewet totaal'",
        timeout=traag_ms(),
    )

    assert page.console_fouten == [], "\n".join(page.console_fouten)


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
        timeout=traag_ms(),
    )
    page.locator("#dock-btn-close").click()
    op_kaart = aantal_kaartgebieden(page)

    open_paneel(page, "Exporteren")
    csv_knop = page.locator("#export-csv-btn")
    expect(csv_knop).to_be_enabled()
    with page.expect_download() as dl:
        csv_knop.click()
    pad = tmp_path / "export.csv"
    dl.value.save_as(pad)
    rijen = list(csv.DictReader(io.StringIO(pad.read_text(encoding="utf-8"))))
    assert len(rijen) == op_kaart >= 13, (len(rijen), op_kaart)  # elke buurt op de kaart, met de testbuurten
    assert {"naam", "indicator_waarde", "bron", "jaar"} <= set(rijen[0]), rijen[0].keys()
    workum = next(r for r in rijen if r["naam"] == "Workum")
    assert "Kerncijfers" in workum["bron"] and re.fullmatch(r"(19|20)\d{2}", workum["jaar"])


def test_chatactie_open_kompas_laadt_selectie(app_page):
    """#79: de chatactie 'Open het D-Omni Kompas' laadt de huidige selectie in het
    Kompas, net als de knop 'Open Kompas Venster' in het Kompas-paneel."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM, shift=True)
    selecteer_buurt_via_app(page, KOUDUM, shift=True)
    wacht_op_selectie(page, [WORKUM, KOUDUM])
    _open_assistent(page)
    expect(page.locator("#dock-panel-kompas")).to_be_hidden()
    page.locator("#chat-input").fill("help")
    page.get_by_role("button", name="Vraag versturen").click()
    _chat_actie(page, r"Beleidsadviseur")
    _chat_actie(page, r"Open het D-Omni Kompas")

    expect(page.locator("#dock-panel-kompas")).to_be_visible()
    expect(page.locator("#kompas-info")).to_contain_text("Gemiddelde van 2 gebieden", timeout=traag_ms())
    expect(page.locator("#kompas-info")).to_contain_text("Workum, Koudum")
    wacht_op_zonnediagram(page)
    assert page.console_fouten == [], "\n".join(page.console_fouten)


def test_tc_06_001_fase2_verkeer_bereikbaarheid(app_page):
    """TC-06-001 stap 4-6: indicator bereikbaarheid/afstand OV vindbaar onder Verkeer."""
    page = app_page
    laad_buurtenkaart(page)
    selecteer_buurt_via_app(page, WORKUM)
    wacht_op_selectie(page, [WORKUM])
    open_kompas(page, "Workum")
    # Alle knopen 'Verkeer' samen: met de SWF-inrichting (#288) kan het thema op meer plekken staan
    verkeer = page.evaluate(
        "() => window.kompasViz.root.descendants().filter(d => d.data.name === 'Verkeer')"
        ".flatMap(v => v.descendants().filter(d => d.data.uuid).map(d => d.data.name))"
    )
    assert verkeer, f"geen indicatoren onder Verkeer (Kompas: {len(kompas_namen(page))} knopen)"


@pytest.mark.skip(
    reason="TC-06-001 stap 11-12 en acceptatiecriterium 'zonder uitleg': kernniveau-detail, "
    "historische trend en begrijpelijkheid vergen handmatige review "
    "(trend: zie TC-02-002 xfail)"
)
def test_tc_06_001_handmatige_review():
    """TC-06-001 stap 11-12 en gebruikersbeleving."""


@pytest.mark.skip(
    reason="TC-06-001 stap 13 (PDF-rapport): gebiedsdossier gebruikt de LLM; niet deterministisch in de sample-stack"
)
def test_tc_06_001_pdf_rapport():
    """TC-06-001 stap 13: PDF-rapport genereren."""


# ── TC-06-004 — Chat (AI) en beleidsadviseur, Bolsward-Zuidoost ─────────────

# Lokaal model op CPU: een chatantwoord kan minuten duren
LLM_TIMEOUT_MS = int(os.environ.get("E2E_LLM_TIMEOUT", "300")) * 1000
_NL_WOORDEN = {
    "de",
    "het",
    "een",
    "en",
    "van",
    "in",
    "is",
    "dat",
    "op",
    "voor",
    "met",
    "niet",
    "zijn",
    "te",
    "er",
    "je",
    "ik",
    "wordt",
    "deze",
    "als",
    "ook",
    "om",
    "bij",
    "naar",
}
_LLM_FOUTEN = ("Error contacting", "LLM-server", "Generatie mislukt", "Fout bij")


def _selecteer_bolsward_zuidoost(page):
    laad_buurtenkaart(page)
    klik_buurt_op_kaart(page, BOLSWARD_ZUIDOOST, terugval=True)  # scenariotest, zie TC-06-001 stap 3
    wacht_op_selectie(page, [BOLSWARD_ZUIDOOST])
    expect(page.locator("#selection-badge")).to_contain_text("Bolsward-Zuidoost")


def _open_assistent(page):
    page.get_by_role("button", name="D-Omni Assistent", exact=True).click()
    expect(page.locator("#rechter-dock")).not_to_have_class(re.compile(r"\bcollapsed\b"))
    expect(page.locator("#dock-panel-chat")).to_be_visible()


def _vraag(page, tekst, timeout=30_000):
    """Stel een vraag in de Assistent; geeft (JSON-antwoord, laatste assistent-bericht) terug."""
    page.locator("#chat-input").fill(tekst)
    with page.expect_response(
        lambda r: r.url.endswith("/api/chat") and r.request.method == "POST", timeout=timeout
    ) as resp:
        page.get_by_role("button", name="Vraag versturen").click()
    assert resp.value.ok, f"/api/chat gaf {resp.value.status}"
    data = resp.value.json()
    bericht = page.locator("#chat-messages .chat-message-assistant").last
    expect(bericht.locator(".chat-message-bubble")).to_be_visible()
    return data, bericht


def test_tc_06_004a_chat_ai_hoe_groen(app_page):
    """TC-06-004 stap 1-4 (LLM-afhankelijk): AI-antwoord met label, disclaimer en kaartactie.

    Inhoud en acties kiest het model; de test toetst alleen de vorm. Geeft de chat de
    niet-LLM-terugval (debug.mode != intelligent_dispatcher), dan wordt de stap overgeslagen."""
    page = app_page
    _selecteer_bolsward_zuidoost(page)
    _open_assistent(page)

    data, bericht = _vraag(page, "Hoe groen is Bolsward-Zuidoost?", timeout=LLM_TIMEOUT_MS)
    mode = (data.get("debug") or {}).get("mode")
    narrative = data.get("narrative") or ""
    if mode != "intelligent_dispatcher" or any(f in narrative for f in _LLM_FOUTEN):
        pytest.skip(
            f"TC-06-004 stap 2-4: geen LLM-antwoord (debug.mode={mode!r}, "
            f"narrative: {narrative[:120]!r}); LLM niet geconfigureerd of gaf geen geldige JSON"
        )

    # Herkomst zichtbaar: label AI met de waarschuwing, verklaring en melden (#312)
    label = bericht.locator('.ai-label[data-usecase="A"]')
    expect(label).to_contain_text("onjuist of onvolledig")
    expect(label.get_by_role("link", name=re.compile("Meer informatie"))).to_be_visible()
    expect(label.get_by_role("link", name=re.compile("Melden"))).to_be_visible()

    # Kort Nederlands antwoord
    expect(bericht.locator(".chat-narrative")).to_have_text(narrative.strip())
    woorden = re.findall(r"[\wÀ-ÿ'-]+", narrative.lower())
    assert woorden, "leeg antwoord"
    assert len({w for w in woorden if w in _NL_WOORDEN}) >= 2, f"lijkt geen Nederlands: {narrative[:200]}"

    # Minstens één kaartactie die naar het geselecteerde gebied verwijst
    kaartacties = [a for a in data.get("acties", []) if a.get("type") == "TOON_OP_KAART"]
    assert kaartacties, f"geen TOON_OP_KAART-actie: {data.get('acties')}"
    assert any(
        "Bolsward" in (a.get("label") or "") or BOLSWARD_ZUIDOOST in (a.get("indicator_uuid") or "")
        for a in kaartacties
    ), f"geen kaartactie voor Bolsward-Zuidoost: {kaartacties}"
    expect(bericht.locator('.chat-actie-btn[data-type="TOON_OP_KAART"]').first).to_be_visible()


def test_tc_06_004bc_beleidsadviseur_kompas(app_page):
    """TC-06-004 stap 5-8 (deterministisch): scenario Beleidsadviseur en Kompas voor Bolsward-Zuidoost."""
    page = app_page
    _selecteer_bolsward_zuidoost(page)
    _open_assistent(page)

    # 5-6. Vrije tekst triggert het scenario (trefwoord 'beleidsadviseur'), geen LLM
    data, bericht = _vraag(page, "Ik ben beleidsadviseur")
    assert (data.get("debug") or {}).get("mode") == "deterministic_scenario", data.get("debug")
    expect(bericht.locator(".chat-narrative")).to_contain_text("IJsselmeerkust")
    expect(bericht.locator(".ai-label")).to_have_count(0)
    knoppen = bericht.locator(".chat-actie-btn")
    expect(knoppen).to_have_count(3)
    for label in ("Toon: Buurten", "Gemeente: Súdwest-Fryslân", "Open het D-Omni Kompas"):
        expect(knoppen.filter(has_text=label)).to_have_count(1)

    # 7-8. Kompas openen vanuit de chat → venster met het geselecteerde gebied
    _chat_actie(page, r"Open het D-Omni Kompas")
    expect(page.locator("#dock-panel-kompas")).to_be_visible()
    expect(page.locator("#kompas-info")).to_contain_text("Bolsward-Zuidoost", timeout=geschaald(30_000))
    # De dekking hangt van de vulling af (met de SWF-inrichting 98,8%): getoond en hoog
    expect(page.locator("#kompas-info")).to_contain_text(re.compile(r"Indicatordekking: (9\d|100)(\.\d+)?%"))
    wacht_op_zonnediagram(page)

    assert page.console_fouten == [], "\n".join(page.console_fouten)
