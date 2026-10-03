"""Het beeldmerk is geldige XML en de header kan het via <use> met thema-tokens tekenen (#249)."""

import re
import xml.dom.minidom
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "static" / "images" / "beeldmerk.svg"


def test_beeldmerk_is_geldige_xml():
    # '--' in een XML-commentaar maakt het bestand ongeldig: dan tekent de browser niets
    xml.dom.minidom.parse(str(SVG))


def test_beeldmerk_heeft_groep_voor_use_en_tokens():
    tekst = SVG.read_text(encoding="utf-8")
    assert re.search(r'<g\s+id="beeldmerk"', tekst)
    for token in ("vlak", "lijn", "kern"):
        assert f"var(--d-omnitwin-beeldmerk-{token}," in tekst


def test_header_tekent_beeldmerk_via_use():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert '<use href="/static/images/beeldmerk.svg#beeldmerk">' in html


@pytest.mark.parametrize("thema", ["d-omnitwin", "swf"])
def test_thema_zet_beeldmerk_tokens(thema):
    css = (ROOT / "static" / "css" / "themes" / f"{thema}.css").read_text(encoding="utf-8")
    for token in ("vlak", "lijn", "kern"):
        assert f"--d-omnitwin-beeldmerk-{token}:" in css
