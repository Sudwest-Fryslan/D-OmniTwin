"""Unit-tests voor de interactieve rondleiding en instaphulp (#442).

Controleert zonder browser dat:
1. Alle stapankers (#id of [data-panel="x"]) in static/js/core/rondleiding.js bestaan in templates/index.html.
2. Elke stap de drie-regelige duidingsstructuur (wat, betekent, probeer) bevat en geen organisatie-hardcodes heeft.
3. buurtkiezer.js en rondleiding.js vóór chat.js en app.js worden geladen in templates/index.html.
4. De herhaalbare instapknoppen (#info-tour-btn, #chat-start-tour-btn) en de 2-ingangen welkomstmodal aanwezig zijn, losse #tour-start-btn weg is (#532), en verweesde startOnboarding/ONBOARDING_ACTION weg zijn.
5. #panel-rapport geen misleidende 'Directe AI analyse' of 'Genereer AI Rapport' meer toont.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "templates" / "index.html"
RONDLEIDING_JS = ROOT / "static" / "js" / "core" / "rondleiding.js"
BUURTKIEZER_JS = ROOT / "static" / "js" / "core" / "buurtkiezer.js"
APP_JS = ROOT / "static" / "js" / "app.js"
CHAT_JS = ROOT / "static" / "js" / "chat.js"


def test_rondleiding_stapankers_bestaan_in_index_html():
    """Elke selector in RONDLEIDING_STAPPEN moet een geldig element in templates/index.html hebben."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    js = RONDLEIDING_JS.read_text(encoding="utf-8")

    ankers_blokken = re.findall(r"ankers:\s*\[(.*?)\],\s*$", js, re.MULTILINE)
    assert len(ankers_blokken) == 4, f"Verwacht 4 stappen met ankers, gevonden: {len(ankers_blokken)}"

    for blok in ankers_blokken:
        selectors = re.findall(r"'([^']+)'", blok)
        assert selectors, f"Lege ankerlijst in: {blok}"
        for sel in selectors:
            if sel.startswith("#"):
                el_id = sel[1:]
                assert re.search(rf'\bid=["\']{re.escape(el_id)}["\']', html), (
                    f"Anker {sel} uit rondleiding.js bestaat niet in templates/index.html"
                )
            elif m := re.fullmatch(r'\[data-panel="([a-z0-9_-]+)"\]', sel):
                panel = m.group(1)
                assert re.search(rf'\bdata-panel=["\']{re.escape(panel)}["\']', html), (
                    f"Anker {sel} uit rondleiding.js bestaat niet in templates/index.html"
                )
            else:
                pytest.fail(
                    f"Anker {sel!r} moet de vorm '#id' of '[data-panel=\"x\"]' hebben voor statische verificatie"
                )


def test_rondleiding_stappen_hebben_drie_regels_en_geen_hardcodes():
    """Elke stap heeft titel, wat, betekent en probeer, zonder organisatie- of aantal-hardcodes."""
    js = RONDLEIDING_JS.read_text(encoding="utf-8")

    for veld in ("id:", "titel:", "ankers:", "wat:", "betekent:", "probeer:"):
        aantal = len(re.findall(rf"\b{re.escape(veld)}", js))
        assert aantal >= 4, f"Veld {veld} moet in alle 4 stappen voorkomen (gevonden: {aantal})"

    for verboden in ("Fryslân", "Súdwest", "SWF", "235"):
        assert verboden.lower() not in js.lower(), f"Hardcode {verboden!r} mag niet in rondleiding.js staan"


def test_scripts_en_knoppen_aanwezig_in_index_html():
    """buurtkiezer.js en rondleiding.js laden vóór chat.js en app.js; alle instapknoppen bestaan."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    pos_a11y = html.find("/static/js/core/a11y.js")
    pos_buurt = html.find("/static/js/core/buurtkiezer.js")
    pos_rond = html.find("/static/js/core/rondleiding.js")
    pos_chat = html.find("/static/js/chat.js")
    pos_app = html.find("/static/js/app.js")

    assert -1 not in (pos_a11y, pos_buurt, pos_rond, pos_chat, pos_app)
    assert pos_a11y < pos_buurt < pos_rond < pos_chat < pos_app

    for verplicht_id in (
        "welcome-btn-buurt",
        "welcome-btn-tour",
        "welcome-btn-help",
        "welcome-skip-btn",
        "welcome-buurtkiezer-wrap",
        "info-tour-btn",
        "chat-start-tour-btn",
    ):
        assert f'id="{verplicht_id}"' in html, f"Element #{verplicht_id} ontbreekt in templates/index.html"

    assert 'id="tour-start-btn"' not in html, "Losse vraagtekenknop #tour-start-btn mag niet meer voorkomen (#532)"


def test_gedeelde_buurtkiezer_en_verweesde_onboarding_opgeruimd():
    """chat.js en app.js gebruiken allebei window.BuurtKiezer; startOnboarding en ONBOARDING_ACTION zijn weg."""
    assert BUURTKIEZER_JS.exists()
    chat_js = CHAT_JS.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "window.BuurtKiezer.maak" in chat_js
    assert "window.BuurtKiezer.maak" in app_js

    for tekst in (app_js, html):
        assert "startOnboarding" not in tekst
        assert "ONBOARDING_ACTION" not in tekst


def test_rapportpaneel_bevat_geen_misleidende_ai_claim():
    """#panel-rapport claimt niet langer 'Directe AI analyse' of 'Genereer AI Rapport'."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "Directe AI analyse" not in html
    assert "Genereer AI Rapport" not in html
    assert 'id="open-rapport-btn"' in html
