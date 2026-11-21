"""Unit tests voor drieluik-navigatie, vaste randtabs en samengevoegde docks (#525)."""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "templates" / "index.html"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
APP_JS = ROOT / "static" / "js" / "app.js"
MIJN_JS = ROOT / "static" / "js" / "mijn.js"


class _TabNavParser(HTMLParser):
    """Verzamel knoppen binnen #left-tab-bar en #right-tab-bar plus element-ID-posities."""

    def __init__(self) -> None:
        super().__init__()
        self._in_nav: str | None = None
        self.left_tabs: list[dict[str, str]] = []
        self.right_tabs: list[dict[str, str]] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        el_id = attr_map.get("id")
        if el_id:
            self.ids.append(el_id)

        if tag == "nav" and el_id in {"left-tab-bar", "right-tab-bar"}:
            self._in_nav = el_id
        elif tag == "button" and self._in_nav is not None:
            entry = {
                "panel": attr_map.get("data-panel", ""),
                "role": attr_map.get("role", ""),
                "controls": attr_map.get("aria-controls", ""),
            }
            if self._in_nav == "left-tab-bar":
                self.left_tabs.append(entry)
            else:
                self.right_tabs.append(entry)

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self._in_nav is not None:
            self._in_nav = None


def _parse_index() -> tuple[str, _TabNavParser]:
    html = INDEX_HTML.read_text(encoding="utf-8")
    parser = _TabNavParser()
    parser.feed(html)
    return html, parser


def test_randtabs_en_drieluik_structuur():
    """Links 3 randtabs, rechts 4 randtabs, geen oude losse tabs of role='tab' op randtabs."""
    html, parser = _parse_index()

    assert [t["panel"] for t in parser.left_tabs] == ["controls", "legenda", "favorieten"]
    assert [t["panel"] for t in parser.right_tabs] == ["kompas", "chat", "rapport", "info"]

    for tab in parser.left_tabs + parser.right_tabs:
        assert tab["role"] == "", f"Randtab {tab['panel']} mag geen role='tab' hebben (Playwright button-selector)"
        assert tab["controls"], f"Randtab {tab['panel']} mist aria-controls"

    assert 'data-panel="layers"' not in html
    assert 'data-panel="export"' not in html
    assert "tab-label" not in html
    assert "panel-layers" not in parser.ids
    assert "panel-kompas" not in parser.ids

    # Floating window behoudt alle 4 tabs
    assert re.findall(r'data-float-tab="([^"]+)"', html) == ["kompas", "chat", "rapport", "info"]


def test_samengevoegde_panelen_en_sectievolgorde():
    """Legenda bevat 3 secties in volgorde, Rapport & Export zijn gecombineerd, Favorieten staat links."""
    html, parser = _parse_index()

    legenda_idx = parser.ids.index("legenda-indicator-sectie")
    externe_idx = parser.ids.index("externe-lagen-sectie")
    basemap_idx = parser.ids.index("basemap-sectie")
    assert legenda_idx < externe_idx < basemap_idx

    dock_rapport_idx = parser.ids.index("dock-panel-rapport")
    rapport_idx = parser.ids.index("panel-rapport")
    export_idx = parser.ids.index("panel-export")
    info_idx = parser.ids.index("dock-panel-info")
    assert dock_rapport_idx < rapport_idx < export_idx < info_idx

    favorieten_panel_idx = parser.ids.index("panel-favorieten")
    mijn_fav_idx = parser.ids.index("mijn-favorieten")
    rechter_dock_idx = parser.ids.index("rechter-dock")
    assert favorieten_panel_idx < mijn_fav_idx < rechter_dock_idx
    assert html.count('id="mijn-favorieten"') == 1


def test_css_randtab_tokens_en_checkbox_fix():
    """CSS bevat compacte randtab-tokens, schermrand-docks (left/right: 0), gesplitste breedtes en checkbox-fix."""
    css = STYLES_CSS.read_text(encoding="utf-8")

    assert "--randtab-width: 48px;" in css
    assert "--randtab-header-inset:" in css
    assert "--randtab-body-inset:" in css
    assert "--left-dock-width: clamp(380px, 24vw, 440px);" in css
    assert "--dock-width: clamp(440px, 30vw, 560px);" in css
    assert "width: 215px;" not in css
    assert ".form-group label.checkbox-label" in css
    assert ".externe-laag-item" in css
    assert ".externe-laag-item .externe-laag-label" in css

    panel_match = re.search(r"\.panel-container\s*\{([^}]+)\}", css)
    assert panel_match is not None
    panel_body = panel_match.group(1)
    assert "top: 80px;" in panel_body
    assert "left: 0;" in panel_body
    assert "width: var(--left-dock-width);" in panel_body

    dock_match = re.search(r"(?<!\.rechter-dock )\.rechter-dock\s*\{([^}]+)\}", css)
    assert dock_match is not None
    dock_body = dock_match.group(1)
    assert "top: 80px;" in dock_body
    assert "right: 0;" in dock_body
    assert "width: var(--dock-width);" in dock_body


def test_app_js_geen_hardcoded_dock_breedtes_en_heeft_aliassen():
    """app.js gebruikt geen oude 360/420 px constanten en ondersteunt layers/export aliassen."""
    js = APP_JS.read_text(encoding="utf-8")

    assert "? 360 : 0" not in js
    assert "? 420 : 0" not in js
    assert "if (panelId === 'layers') return 'legenda';" in js
    assert "if (panelId === 'export') return 'rapport';" in js


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_routing_helpers_en_viewport_berekening_met_node():
    """Node-evaluatie van normaliseerPanelId en pastBeideDocksNaastElkaar over viewports."""
    js = APP_JS.read_text(encoding="utf-8")
    match = re.search(
        r"(// Navigation & Dock Routing Constants \(#525\).*?window\.pastBeideDocksNaastElkaar = pastBeideDocksNaastElkaar;)",
        js,
        re.DOTALL,
    )
    assert match is not None, "Routing-constanten en helpers niet gevonden in app.js"

    script = f"""
const window = {{ innerWidth: 1280 }};
{match.group(1)}
console.log(JSON.stringify({{
  layers: normaliseerPanelId('layers'),
  exportTab: normaliseerPanelId('export'),
  controls: normaliseerPanelId('controls'),
  w900: pastBeideDocksNaastElkaar(900),
  w1200: pastBeideDocksNaastElkaar(1200),
  w1280: pastBeideDocksNaastElkaar(1280),
  w1366: pastBeideDocksNaastElkaar(1366),
  w1400: pastBeideDocksNaastElkaar(1400),
  w1600: pastBeideDocksNaastElkaar(1600),
  w1920: pastBeideDocksNaastElkaar(1920),
}}));
"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)
    assert res == {
        "layers": "legenda",
        "exportTab": "rapport",
        "controls": "controls",
        "w900": False,
        "w1200": False,
        "w1280": True,
        "w1366": True,
        "w1400": True,
        "w1600": True,
        "w1920": True,
    }


def test_mijn_js_lokaal_en_favorieten_tab():
    """mijn.js ondersteunt lokale favorieten voor gasten en opent linkertab favorieten."""
    js = MIJN_JS.read_text(encoding="utf-8")

    assert "omnitwin_favorieten_lokaal" in js
    assert '[data-panel="favorieten"]' in js
    assert "openLinkerPanel('favorieten')" in js
    assert "if (!ingelogd()) return;" in js
