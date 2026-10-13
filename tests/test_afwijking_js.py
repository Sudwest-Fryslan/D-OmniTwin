"""
Unittest voor static/js/core/afwijking.js (#323): de kleur van een afwijking in de
Kompas-benchmark volgt de polariteit van de indicator. Draait de JavaScript met
Node; zonder Node wordt de test overgeslagen.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

AFWIJKING_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "core" / "afwijking.js"

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden"),
]


def duiding(diff, richting):
    script = (
        f"const m = require({json.dumps(str(AFWIJKING_JS))});"
        f"process.stdout.write(JSON.stringify(m.afwijkingDuiding({json.dumps(diff)}, {json.dumps(richting)})));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "diff,richting,kleur,oordeel",
    [
        (5, "hoger_is_beter", "--color-success", "gunstig"),
        (-5, "hoger_is_beter", "--color-danger", "ongunstig"),
        (5, "lager_is_beter", "--color-danger", "ongunstig"),
        (-5, "lager_is_beter", "--color-success", "gunstig"),
        (5, "neutraal", "--text-secondary", "neutraal"),
        (-5, None, "--text-secondary", "neutraal"),
        (0, "hoger_is_beter", "--text-secondary", "gelijk"),
    ],
)
def test_kleur_volgt_polariteit(diff, richting, kleur, oordeel):
    assert duiding(diff, richting) == {"kleur": kleur, "oordeel": oordeel}


def test_kompas_benchmark_gebruikt_de_duiding():
    """De benchmarktabel kleurt niet meer vast rood bij een hogere waarde."""
    kompas = (AFWIJKING_JS.parents[1] / "kompas.js").read_text(encoding="utf-8")
    assert "afwijkingDuiding(diff, meta?.richting)" in kompas
    index = (AFWIJKING_JS.parents[3] / "templates" / "index.html").read_text(encoding="utf-8")
    assert index.index("core/afwijking.js") < index.index("js/kompas.js")
