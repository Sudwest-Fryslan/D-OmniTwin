"""Unit tests voor interactieve suggestie-chips en contextuele kaartsturing in D-Omni Assistent (#445)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "templates" / "index.html"
CHAT_JS = ROOT / "static" / "js" / "chat.js"
APP_JS = ROOT / "static" / "js" / "app.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"


def _extract_js_function(bron: str, naam: str) -> str:
    """Extraheert een top-level function-declaratie met gebalanceerde accolades."""
    m = re.search(rf"function\s+{re.escape(naam)}\s*\(", bron)
    assert m, f"Functie {naam} niet gevonden"
    start = m.start()
    paren_close = bron.index(")", m.end())
    brace_start = bron.index("{", paren_close)
    diepte = 0
    in_str: str | None = None
    escaped = False
    for idx in range(brace_start, len(bron)):
        ch = bron[idx]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
        elif ch == "{":
            diepte += 1
        elif ch == "}":
            diepte -= 1
            if diepte == 0:
                return bron[start : idx + 1]
    raise AssertionError(f"Geen sluitende accolade voor {naam}")


def _run_chat_js(expressie: str):
    bron = CHAT_JS.read_text(encoding="utf-8")
    code = "\n\n".join(
        [
            _extract_js_function(bron, "kortChatLabel"),
            _extract_js_function(bron, "bouwStartSuggestieChips"),
            _extract_js_function(bron, "bouwVervolgChips"),
            f"console.log(JSON.stringify(({expressie})));",
        ]
    )
    proc = subprocess.run(
        ["node", "-e", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_html_bevat_contextbalk_startchips_rondleiding_en_cachebust():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="chat-context-bar"' in html
    assert 'id="chat-start-chips"' in html
    assert 'id="chat-start-tour-btn"' in html
    assert re.search(r'src="/static/js/kompas\.js\?v=\d+"', html)
    assert re.search(r'src="/static/js/chat\.js\?v=\d+"', html)
    assert re.search(r'src="/static/js/app\.js\?v=\d+"', html)


def test_css_bevat_suggestie_chips_met_thematokens_en_focusring():
    css = STYLES_CSS.read_text(encoding="utf-8")
    for selector in (".chat-context-bar", ".chat-context-pill", ".chat-suggestie-chip", ".chat-vervolg-chips"):
        assert selector in css
    sectie = css[css.index("/* --- #445: Contextbalk") :]
    assert ":focus-visible" in sectie
    sectie_zonder_commentaar = re.sub(r"/\*.*?\*/", "", sectie, flags=re.DOTALL)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", sectie_zonder_commentaar), (
        "Geen vaste hexkleuren in #445 CSS (WCAG/thema's)"
    )


def test_chat_js_geen_hardcoded_plaatsnamen_en_juiste_eventbus_koppeling():
    chat = CHAT_JS.read_text(encoding="utf-8")
    app = APP_JS.read_text(encoding="utf-8")

    # ADR 0007: geen hardcoded gemeenten/buurten in chat.js
    for verboden in ("Sneek", "Bolsward", "Súdwest-Fryslân", "energielabels"):
        assert verboden.lower() not in chat.lower(), f"Hardcoded voorbeeld '{verboden}' hoort niet in chat.js"

    # EventBus-koppelingen
    assert "window.EventBus.emit('MAAK_RAPPORT'" in chat
    assert "window.EventBus.on('MAAK_RAPPORT'" in app
    assert "window.EventBus?.emit('INDICATOR_CLEARED')" in app
    assert "window.EventBus?.emit('GEMEENTE_GEWIJZIGD'" in app
    assert "window.chatPanel?.refreshContext?.()" in app
    assert "huidige_gemeente_code" in chat

    # Bugfix: geen dubbele escapeHtml() op plain-text .title
    assert "chip.title = `Bekijk '${escapeHtml(" not in chat


def test_startchips_met_indicator_en_geselecteerde_buurt():
    chips = _run_chat_js(
        """
        bouwStartSuggestieChips({
            indicatorUuid: '11111111-1111-1111-1111-111111111111',
            indicatorNaam: 'Bevolkingsdichtheid',
            gebiedIds: ['BU00010001'],
            gebiedNamen: ['Centrum-Noord'],
            gemeenteCode: '0001',
            gemeenteNaam: 'Voorbeeldstad',
        })
        """
    )
    types = [c["type"] for c in chips]
    assert types == ["VRAAG", "VRAAG", "OPEN_KOMPAS", "MAAK_RAPPORT"]
    assert "Centrum-Noord" in chips[0]["label"]
    assert chips[0]["extraContext"]["gebruik_actieve_indicator"] is True
    # Datavraag mag niet starten met 'Toon' (dat blokkeert _NAVIGATIE in chat_datavraag.py)
    assert chips[1]["vraag"] == "Welke 5 buurten in Voorbeeldstad scoren het laagst op Bevolkingsdichtheid?"
    assert chips[1]["extraContext"]["negeer_kaartselectie"] is True
    assert chips[3]["gebiedIds"] == ["BU00010001"]


def test_startchips_met_alleen_actieve_indicator():
    chips = _run_chat_js(
        """
        bouwStartSuggestieChips({
            indicatorUuid: '22222222-2222-2222-2222-222222222222',
            indicatorNaam: 'Afstand tot koelte',
            gebiedIds: [],
            gebiedNamen: [],
        })
        """
    )
    types = [c["type"] for c in chips]
    assert types == ["VRAAG", "VRAAG", "BEKIJK_IN_KOMPAS"]
    assert chips[0]["vraag"].startswith("Welke 5 buurten scoren het laagst op ")
    assert chips[1]["vraag"].startswith("Welke 5 buurten scoren het hoogst op ")
    assert chips[2]["indicatorUuid"] == "22222222-2222-2222-2222-222222222222"


def test_startchips_met_alleen_gebied_en_leeg():
    met_gebied = _run_chat_js(
        """
        bouwStartSuggestieChips({
            gebiedIds: ['BU00010001', 'BU00010002'],
            gebiedNamen: ['Noord', 'Zuid'],
        })
        """
    )
    assert [c["type"] for c in met_gebied] == ["OPEN_KOMPAS", "MAAK_RAPPORT", "VRAAG"]
    assert "2 gebieden" in met_gebied[0]["label"]

    leeg = _run_chat_js("bouwStartSuggestieChips({})")
    assert [c["type"] for c in leeg] == ["VRAAG", "OPEN_KOMPAS"]
    assert leeg[0]["vraag"] == "Wat kan jij?"


def test_vervolgchips_vullen_ontbrekende_acties_aan_zonder_duplicaten():
    # Niet-datavraag met gevonden indicator + geselecteerde buurt op kaart
    chips = _run_chat_js(
        """
        bouwVervolgChips(
            {
                intent: 'ZOEK_INDICATOREN',
                acties: [{ type: 'TOON_OP_KAART', label: 'Toon: Groen' }],
                indicatoren: [{ uuid: '33333333-3333-3333-3333-333333333333', naam: 'Oppervlakte groen' }],
            },
            { gebiedIds: ['BU00010001'] }
        )
        """
    )
    assert [c["type"] for c in chips] == ["OPEN_KOMPAS", "MAAK_RAPPORT"]

    # Datavraag met reeds aanwezige OPEN_KOMPAS + MAAK_RAPPORT + TOON_OP_KAART krijgt 1 rangorde-vervolgvraag
    datavraag_chips = _run_chat_js(
        """
        bouwVervolgChips(
            {
                intent: 'DATAVRAAG',
                acties: [
                    { type: 'TOON_OP_KAART', label: 'Toon' },
                    { type: 'OPEN_KOMPAS', label: 'Kompas' },
                    { type: 'MAAK_RAPPORT', label: 'Rapport' },
                ],
                indicatoren: [{ uuid: '33333333-3333-3333-3333-333333333333', naam: 'Oppervlakte groen' }],
                debug: { gebieden_bron: 'kaart' },
            },
            { gebiedIds: ['BU00010001'] }
        )
        """
    )
    assert [c["type"] for c in datavraag_chips] == ["VRAAG"]
    assert datavraag_chips[0]["extraContext"]["negeer_kaartselectie"] is True

    # Onboarding en vraag_buurt krijgen geen overbodige vervolgchips
    assert _run_chat_js("bouwVervolgChips({ intent: 'HELP_ONBOARDING' }, { gebiedIds: ['BU1'] })") == []
    assert _run_chat_js("bouwVervolgChips({ intent: 'DATAVRAAG', vraag_buurt: true }, { gebiedIds: ['BU1'] })") == []


def test_startchips_meervoud_werkwoord_en_kompas_dubbele_laad_preventie():
    meervoud = _run_chat_js(
        """
        bouwStartSuggestieChips({
            indicatorUuid: '11111111-1111-1111-1111-111111111111',
            indicatorNaam: 'Bevolkingsdichtheid',
            gebiedIds: ['BU00010001', 'BU00010002'],
            gebiedNamen: ['Noord', 'Zuid'],
        })
        """
    )
    assert meervoud[0]["label"].startswith("📊 Hoe scoren 2 gebieden op ")

    kompas = (ROOT / "static" / "js" / "kompas.js").read_text(encoding="utf-8")
    app = APP_JS.read_text(encoding="utf-8")
    chat = CHAT_JS.read_text(encoding="utf-8")
    assert "heeftSelectieGeladen(" in kompas
    assert "_loadingSelectionKey" in kompas
    assert "window.openRechterDock('kompas', false)" in kompas
    assert "navigateToIndicator(data.uuid, { syncNaarKaart: false })" in kompas
    assert "bron === 'kompas-bekijken'" in app
    assert "bron: 'kompas-bekijken'" in chat
    assert "heeftSelectieGeladen" in app
    assert "rechterDockBody.scrollTop = 0" in app
