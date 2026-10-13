"""Unit tests voor venster-isolatie (Issue #46).

Borgt dat:
1. Alle window.open() aanroepen in app.js, chat.js, melden.js en index.html
   'noopener,noreferrer' meekrijgen als 3e argument, zodat geopende rapporten
   en externe pagina's in een eigen thread draaien en window.print() de hoofdapp niet bevriest.
2. Alle target="_blank" links in HTML-templates rel="noopener noreferrer" bevatten.
"""

import re
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_app_js_window_open_heeft_noopener_noreferrer():
    """Borgt dat alle window.open aanroepen in app.js voorzien zijn van noopener,noreferrer."""
    app_js = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

    # Vind alle window.open aanroepen
    matches = re.findall(r"window\.open\(([^;]+)\)", app_js)
    assert len(matches) > 0, "Geen window.open gevonden in app.js"

    for match in matches:
        assert "noopener" in match, f"window.open mist noopener in app.js: {match}"
        assert "noreferrer" in match, f"window.open mist noreferrer in app.js: {match}"


def test_chat_js_window_open_heeft_noopener_noreferrer():
    """Borgt dat alle window.open aanroepen in chat.js voorzien zijn van noopener,noreferrer."""
    chat_js = (ROOT / "static" / "js" / "chat.js").read_text(encoding="utf-8")

    matches = re.findall(r"window\.open\(([^;]+)\)", chat_js)
    assert len(matches) > 0, "Geen window.open gevonden in chat.js"

    for match in matches:
        assert "noopener" in match, f"window.open mist noopener in chat.js: {match}"
        assert "noreferrer" in match, f"window.open mist noreferrer in chat.js: {match}"


def test_melden_js_window_open_heeft_noopener_noreferrer():
    """Borgt dat fallback window.open in melden.js voorzien is van noopener,noreferrer."""
    melden_js = (ROOT / "static" / "js" / "core" / "melden.js").read_text(encoding="utf-8")

    matches = re.findall(r"window\.open\(([^;]+)\)", melden_js)
    assert len(matches) > 0, "Geen window.open gevonden in melden.js"

    for match in matches:
        assert "noopener" in match, f"window.open mist noopener in melden.js: {match}"
        assert "noreferrer" in match, f"window.open mist noreferrer in melden.js: {match}"


def test_templates_index_html_window_open_heeft_noopener_noreferrer():
    """Borgt dat window.open in templates/index.html voorzien is van noopener,noreferrer."""
    index_html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    matches = re.findall(r"window\.open\(([^;]+)\)", index_html)
    assert len(matches) > 0, "Geen window.open gevonden in index.html"

    for match in matches:
        assert "noopener" in match, f"window.open mist noopener in index.html: {match}"
        assert "noreferrer" in match, f"window.open mist noreferrer in index.html: {match}"


def test_html_target_blank_heeft_noopener_noreferrer():
    """Borgt dat alle target='_blank' links in templates/index.html rel='noopener noreferrer' hebben."""
    index_html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    # Zoek naar alle <a> tags met target="_blank"
    a_tags = re.findall(r"<a\s+[^>]*target=[\"']_blank[\"'][^>]*>", index_html, re.IGNORECASE)
    assert len(a_tags) > 0, "Geen <a> tags met target=_blank gevonden in index.html"

    for tag in a_tags:
        assert 'rel="noopener noreferrer"' in tag or "rel='noopener noreferrer'" in tag, (
            f"Link met target=_blank mist rel='noopener noreferrer': {tag}"
        )
