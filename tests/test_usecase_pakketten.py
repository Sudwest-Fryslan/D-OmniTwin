"""
Use-casepakketten (usecases/<naam>/usecase.json) zijn geldig en dekken samen de
hele bronbibliotheek: alle data hoort bij een use case. Geen stack nodig.
"""

import csv
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
BRON = ROOT / "init_data" / "sample" / "2_brondata"
PAKKETTEN = sorted((ROOT / "usecases").glob("*/usecase.json"))
RICHTINGEN = {"hoger_is_beter", "lager_is_beter", "neutraal"}


def bron_gebieden():
    geo = json.loads((BRON / "sample_buurten.geojson").read_text(encoding="utf-8"))
    return {f["properties"]["id"] for f in geo["features"]}


def bron_indicatoren():
    with open(BRON / "sample_indicatoren.csv", encoding="utf-8") as f:
        return {r["indicator_naam"] for r in csv.DictReader(f)}


@pytest.mark.parametrize("pad", PAKKETTEN, ids=lambda p: p.parent.name)
def test_pakket_is_geldig(pad):
    uc = json.loads(pad.read_text(encoding="utf-8"))
    for veld in ("id", "titel", "persona", "data", "inrichting", "ai_zoekvraag", "verwacht"):
        assert veld in uc, f"{pad.parent.name}: veld '{veld}' ontbreekt"
    assert (pad.parent / "README.md").exists(), f"{pad.parent.name}: README.md (stappen) ontbreekt"

    data = uc["data"]
    assert data["focus"] in data["gebieden"]
    onbekend = set(data["gebieden"]) - bron_gebieden()
    assert not onbekend, f"{pad.parent.name}: gebieden niet in de bronbibliotheek: {onbekend}"

    namen = bron_indicatoren()
    for ind in data["indicatoren"]:
        assert ind["richting"] in RICHTINGEN, f"{ind['naam']}: onbekende richting {ind['richting']}"
        assert ind["naam"] in namen, f"{pad.parent.name}: indicator '{ind['naam']}' niet in de bronbibliotheek"
    for afg in data.get("afgeleid", []):
        assert {afg["teller"], afg["noemer"]} <= namen, f"{afg['naam']}: teller of noemer onbekend"


def test_alle_brondata_hoort_bij_een_use_case():
    gedekt = set()
    for pad in PAKKETTEN:
        gedekt |= set(json.loads(pad.read_text(encoding="utf-8"))["data"]["gebieden"])
    los = bron_gebieden() - gedekt
    assert not los, f"Gebieden in de bronbibliotheek zonder use case: {sorted(los)}"


def test_use_case_ids_uniek():
    ids = [json.loads(p.read_text(encoding="utf-8"))["id"] for p in PAKKETTEN]
    assert len(ids) == len(set(ids)), f"Dubbele use-case-id's: {ids}"
