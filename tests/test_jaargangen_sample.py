"""
Jaargangen van de sample tegen de buurtgeometrie (#119).

Faalt alleen als een gebied_id in sample_indicatoren.csv niet in
sample_buurten.geojson bestaat. De jaargang per indicator wordt alleen
gerapporteerd (pytest -s toont de lijst).
"""

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "init_data" / "scripts"))

from jaargang_controle import (  # noqa: E402
    controleer_jaargangen,
    format_jaren,
    geometrie_codes,
    geometrie_jaar_sample,
)

pytestmark = pytest.mark.unit

SAMPLE = ROOT / "init_data" / "sample" / "2_brondata"


def _controle():
    codes = geometrie_codes(SAMPLE / "sample_buurten.geojson")
    with open(SAMPLE / "sample_indicatoren.csv", encoding="utf-8") as f:
        return controleer_jaargangen(csv.DictReader(f), codes, geometrie_jaar_sample())


def test_geometrie_jaar_vastgelegd():
    assert geometrie_jaar_sample() == 2024


def test_alle_gebied_ids_bestaan_in_geometrie():
    ontbrekend, jaren, afwijkend = _controle()

    # Rapportage, geen assert: jaargang per indicator
    print(f"\nGeometrie-jaargang: {geometrie_jaar_sample()}")
    for naam, js in sorted(jaren.items()):
        markering = "  (>2 jaar van geometrie)" if naam in afwijkend else ""
        print(f"  {naam}: {format_jaren(js)}{markering}")

    assert not ontbrekend, f"gebied_id's zonder geometrie: {sorted(ontbrekend)}"


def test_controle_vindt_ontbrekende_code_en_oude_jaargang():
    rijen = [
        {"gebied_id": "BU00000001", "indicator_naam": "A", "jaar": "2024"},
        {"gebied_id": "BU99999999", "indicator_naam": "A", "jaar": "2024"},
        {"gebied_id": "BU00000001", "indicator_naam": "B", "jaar": "2019"},
    ]
    ontbrekend, jaren, afwijkend = controleer_jaargangen(rijen, {"BU00000001"}, 2024)
    assert ontbrekend == {"BU99999999": 1}
    assert jaren == {"A": {2024}, "B": {2019}}
    assert afwijkend == {"B": 2019}
