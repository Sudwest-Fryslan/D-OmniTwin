"""
Unittest voor static/js/core/escape.js (#65): de centrale escaping van API- en
DB-data in de frontend. Draait de JavaScript met Node; zonder Node wordt de
test overgeslagen.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ESCAPE_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "core" / "escape.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")


def run_js(functie, waarden):
    """Roep functie uit escape.js aan voor elke waarde; geeft de resultaten terug."""
    script = (
        f"const m = require({json.dumps(str(ESCAPE_JS))});"
        f"const invoer = {json.dumps(waarden)};"
        f"process.stdout.write(JSON.stringify(invoer.map(m.{functie})));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_escape_html_tekens():
    assert run_js("escapeHtml", ['<img src=x onerror="alert(1)">']) == [
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    ]
    assert run_js("escapeHtml", ["Tom & Jerry's `x`"]) == ["Tom &amp; Jerry&#39;s &#96;x&#96;"]


def test_escape_html_gewone_tekst_en_getallen():
    assert run_js("escapeHtml", ["Bolsward-Zuidoost", 42, 3.5]) == ["Bolsward-Zuidoost", "42", "3.5"]


def test_escape_html_leeg():
    assert run_js("escapeHtml", [None, ""]) == ["", ""]


def test_safe_url():
    urls = [
        "https://opendata.cbs.nl/statline",
        "http://example.org",
        "/static/x.svg",
        "javascript:alert(1)",
        " JavaScript:alert(1)",
        "java\tscript:alert(1)",
        "data:text/html,<b>x</b>",
        None,
    ]
    assert run_js("safeUrl", urls) == [
        "https://opendata.cbs.nl/statline",
        "http://example.org",
        "/static/x.svg",
        "",
        "",
        "",
        "",
        "",
    ]
