"""
TC-02-00x — Kompas detail (docs/testcases/02-kompas-detail).

Navigatie via echte klikken op het zonnediagram (thema → indicator). Afwijking van
de testdata: Makkum zit niet in de sample dataset; we gebruiken Workum en Koudum.

Stappen die een ontbrekende functie of ontbrekende data toetsen staan als xfail
(strict): gaan ze onverwacht slagen, dan moet de testcase-status bijgewerkt worden.
Subjectieve stappen (begrijpelijkheid van uitleg) staan als skip.
"""

import re

import pytest
from playwright.sync_api import expect

from e2e_helpers import (
    KOUDUM, WORKUM,
    kompas_namen, laad_buurtenkaart, open_indicator_in_kompas, open_kompas, selecteer_buurt_via_app,
    wacht_op_selectie, wacht_op_vergelijkingsgrafiek,
)

JAARTAL = re.compile(r"^(19|20)\d{2}$")


def _kompas_voor(page, *gebied_ids):
    laad_buurtenkaart(page)
    for i, gid in enumerate(gebied_ids):
        selecteer_buurt_via_app(page, gid, shift=i > 0)
    wacht_op_selectie(page, list(gebied_ids))
    if len(gebied_ids) == 1:
        open_kompas(page, "Indicatordekking")
    else:
        open_kompas(page, f"Gemiddelde van {len(gebied_ids)} gebieden")


# ── TC-02-001 Wonen ──────────────────────────────────────────────────────────

def test_tc_02_001_wonen_indicatoren(app_page):
    """TC-02-001 stap 1-3: thema Wonen in het Kompas, indicator met waarde,
    bronvermelding en peildatum zichtbaar."""
    page = app_page
    _kompas_voor(page, WORKUM)
    expect(page.locator("#kompas-info")).to_contain_text("Workum")

    # 1-2. Thema Wonen → indicator (betaalbaarheid ontbreekt in de sample; energielabel wel)
    open_indicator_in_kompas(page, "Wonen", "Gemiddeld energielabel")
    waarde = page.locator("#details-value").inner_text().strip()
    assert waarde not in ("", "-"), f"geen waarde voor indicator: {waarde!r}"

    # 3. Bron en peildatum
    expect(page.locator("#details-bron")).to_have_text(re.compile(r"\S"))
    assert page.locator("#details-bron").inner_text().strip() != "-"
    expect(page.locator("#details-jaar")).to_have_text(JAARTAL)

    assert page.console_fouten == [], "\n".join(page.console_fouten)


def test_tc_02_001_benchmark_twee_gebieden(app_page):
    """TC-02-001 stap 5: tweede gebied (Koudum) toevoegen → vergelijking in het detailpaneel."""
    page = app_page
    _kompas_voor(page, WORKUM, KOUDUM)
    open_indicator_in_kompas(page, "Wonen", "Gemiddeld energielabel")
    expect(page.locator("#details-trend")).to_have_text("Vergelijking")
    expect(page.locator("#details-value")).to_contain_text("⌀")
    wacht_op_vergelijkingsgrafiek(page, ["Workum", "Koudum"])


@pytest.mark.skip(reason="TC-02-001 stap 4: begrijpelijkheid van de Z-score-uitleg is een subjectieve reviewstap (handmatig)")
def test_tc_02_001_uitleg_zscore():
    """TC-02-001 stap 4: uitleg van de Z-score voor de eindgebruiker."""


@pytest.mark.xfail(strict=True, reason="TC-02-001 stap 6: sample dataset heeft één meetmoment per indicator")
def test_tc_02_001_historische_trend(app_page):
    """TC-02-001 stap 6: tijdreeks (≥ 3 jaar) zichtbaar."""
    page = app_page
    _kompas_voor(page, WORKUM)
    open_indicator_in_kompas(page, "Wonen", "Gemiddeld energielabel")
    expect(page.locator("#timeslider-container")).to_be_visible(timeout=5_000)


@pytest.mark.xfail(strict=True, reason="TC-02-001 stap 7 / NM-001: indicator starterswoningen ontbreekt")
def test_tc_02_001_starterswoningen(app_page):
    """TC-02-001 stap 7: aparte KPI starterswoningen in het Kompas."""
    page = app_page
    _kompas_voor(page, WORKUM)
    assert any("starter" in n.lower() for n in kompas_namen(page))


# ── TC-02-002 Sociaal domein ─────────────────────────────────────────────────

def test_tc_02_002_participatiewet(app_page):
    """TC-02-002 stap 1-2: participatiewet-indicator vindbaar via Rondkomen, met waarde,
    bron en peildatum, op buurtniveau."""
    page = app_page
    _kompas_voor(page, WORKUM)

    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    assert page.locator("#details-value").inner_text().strip() not in ("", "-")
    expect(page.locator("#details-bron")).to_contain_text("Kerncijfers")
    expect(page.locator("#details-jaar")).to_have_text(JAARTAL)
    # 2. Aggregatieniveau: data is per CBS-buurt geladen
    expect(page.locator("#kompas-info")).to_contain_text("Workum")

    assert page.console_fouten == [], "\n".join(page.console_fouten)


def test_tc_02_002_drilldown_kernen(app_page):
    """TC-02-002 stap 4: vergelijking per kern (Workum, Koudum) voor participatiewet."""
    page = app_page
    _kompas_voor(page, WORKUM, KOUDUM)
    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    expect(page.locator("#details-trend")).to_have_text("Vergelijking")
    wacht_op_vergelijkingsgrafiek(page, ["Workum", "Koudum"])


@pytest.mark.xfail(strict=True, reason="TC-02-002 stap 3: sample dataset heeft één meetmoment per indicator")
def test_tc_02_002_trendlijn(app_page):
    """TC-02-002 stap 3: trendlijn met ≥ 2 meetmomenten."""
    page = app_page
    _kompas_voor(page, WORKUM)
    open_indicator_in_kompas(page, "Rondkomen", "Participatiewet totaal")
    expect(page.locator("#timeslider-container")).to_be_visible(timeout=5_000)


@pytest.mark.skip(reason="TC-02-002 stap 5: vroegsignalering/drempelwaarden bestaan nog niet; "
                         "beoordeling van kleurcodering is handmatig")
def test_tc_02_002_vroegsignalering():
    """TC-02-002 stap 5: drempelwaarden of signaleringslogica."""


@pytest.mark.xfail(strict=True, reason="TC-02-002 stap 6-7 / NM-001: circulaire landbouw en toerisme ontbreken")
def test_tc_02_002_ontbrekende_indicatoren(app_page):
    """TC-02-002 stap 6-7: indicatoren circulaire landbouw en toerisme-initiatieven."""
    page = app_page
    _kompas_voor(page, WORKUM)
    namen = [n.lower() for n in kompas_namen(page)]
    assert any("circulair" in n for n in namen) and any("toeris" in n for n in namen)
