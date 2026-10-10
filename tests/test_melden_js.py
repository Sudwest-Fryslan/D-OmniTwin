"""
Unittest voor static/js/core/melden.js (#312): het generieke meldmechanisme van de viewer. Draait
de JavaScript met Node, zoals tests/test_escape_html.py; zonder Node wordt de test overgeslagen.
"""
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

MELDEN_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "core" / "melden.js"

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden"),
]


def meld_url(melding, plek=None):
    script = (
        f"const m = require({json.dumps(str(MELDEN_JS))});"
        f"process.stdout.write(m.meldUrl({json.dumps(melding)}, {json.dumps(plek)}));"
    )
    return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True,
                          encoding="utf-8").stdout


def test_vooringevuld_issue_met_usecase_soort_en_resultaat():
    url = meld_url({"onderwerp": "ai", "usecase": "A", "vraag": "Hoe groen is Bolsward?",
                    "resultaat": "x" * 3000, "bronnen": ["Groen (%)"], "pagina": "Viewer"})
    deel = urlsplit(url)
    assert f"{deel.scheme}://{deel.netloc}{deel.path}" == "https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/new"
    q = parse_qs(deel.query)
    assert q["title"] == ["Melding AI-resultaat (usecase A)"]
    body = q["body"][0]
    for tekst in ("AI-fout", "Systeemfout", "A – Assistent", "Hoe groen is Bolsward?", "Groen (%)",
                  "geen persoonsgegevens"):
        assert tekst in body
    assert len(body) < 1600  # resultaat ingekort


def test_meldplek_van_de_instantie_en_mailto():
    assert meld_url({"onderwerp": "ai", "usecase": "C"}, "https://meld.voorbeeld.nl/form").startswith(
        "https://meld.voorbeeld.nl/form?title=")
    assert meld_url({"onderwerp": "ai", "usecase": "C"}, "mailto:ai@voorbeeld.nl").startswith(
        "mailto:ai@voorbeeld.nl?subject=")


def test_geen_onveilige_meldplek():
    assert meld_url({"onderwerp": "ai"}, "javascript:alert(1)").startswith("https://github.com/")
