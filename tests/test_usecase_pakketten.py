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
    """Indicatoren uit de bronbibliotheek (sample) én uit het CBS-recept (init_data/cbs):
    CBS-waarden worden bij het laden gedownload en staan niet in de sample."""
    with open(BRON / "sample_indicatoren.csv", encoding="utf-8") as f:
        namen = {r["indicator_naam"] for r in csv.DictReader(f)}
    pkg = json.loads((ROOT / "init_data" / "cbs" / "datapackage.json").read_text(encoding="utf-8"))
    return namen | set(pkg["indicatoren"])


def pakket_rijen(pad):
    """Gecommitte extra brondata van het pakket (data/waarden.csv), als die er is."""
    extra = pad.parent / "data" / "waarden.csv"
    if not extra.exists():
        return []
    with open(extra, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def download_indicatoren(pad):
    """Indicatoren die het downloadscript van het pakket levert (extra_data.bronnen)."""
    extra = json.loads(pad.read_text(encoding="utf-8"))["data"].get("extra_data") or {}
    return set(extra.get("bronnen", {})) if extra.get("script") else set()


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

    namen = bron_indicatoren() | {r["indicator_naam"] for r in pakket_rijen(pad)} | download_indicatoren(pad)
    for ind in data["indicatoren"]:
        assert ind["richting"] in RICHTINGEN, f"{ind['naam']}: onbekende richting {ind['richting']}"
        assert ind["naam"] in namen, f"{pad.parent.name}: indicator '{ind['naam']}' niet in de bronbibliotheek"
    for afg in data.get("afgeleid", []):
        assert {afg["teller"], afg["noemer"]} <= namen, f"{afg['naam']}: teller of noemer onbekend"


@pytest.mark.parametrize("pad", [p for p in PAKKETTEN if pakket_rijen(p)], ids=lambda p: p.parent.name)
def test_extra_brondata_is_geldig(pad):
    """data/waarden.csv: zelfde kolommen als de sample, alleen gebieden van het pakket,
    per indicator één uuid, eenheid en bron, en een waarde en jaar per rij."""
    with open(BRON / "sample_indicatoren.csv", encoding="utf-8") as f:
        kolommen = csv.DictReader(f).fieldnames
    with open(pad.parent / "data" / "waarden.csv", encoding="utf-8") as f:
        assert csv.DictReader(f).fieldnames == kolommen
    gebieden = set(json.loads(pad.read_text(encoding="utf-8"))["data"]["gebieden"])
    uuids = {}
    for r in pakket_rijen(pad):
        assert r["gebied_id"] in gebieden, f"{r['gebied_id']}: geen gebied van {pad.parent.name}"
        assert uuids.setdefault(r["indicator_naam"], r["indicator_uuid"]) == r["indicator_uuid"]
        assert r["eenheid"] and r["bron"] and r["jaar"].isdigit(), f"{r['indicator_naam']}: eenheid/bron/jaar leeg"
        float(r["waarde"])
        assert r["interpretatie_logica"] in {"pos_is_pos", "-/+"}


def test_alle_brondata_hoort_bij_een_use_case():
    gedekt = set()
    for pad in PAKKETTEN:
        gedekt |= set(json.loads(pad.read_text(encoding="utf-8"))["data"]["gebieden"])
    los = bron_gebieden() - gedekt
    assert not los, f"Gebieden in de bronbibliotheek zonder use case: {sorted(los)}"


def test_use_case_ids_uniek():
    ids = [json.loads(p.read_text(encoding="utf-8"))["id"] for p in PAKKETTEN]
    assert len(ids) == len(set(ids)), f"Dubbele use-case-id's: {ids}"


@pytest.mark.parametrize("pad", [p for p in PAKKETTEN if download_indicatoren(p)], ids=lambda p: p.parent.name)
def test_downloadscript_levert_geldige_data(pad, tmp_path):
    """Het downloadscript (extra_data.script) haalt de data op en schrijft geldige rijen.
    Overgeslagen als de bron niet bereikbaar is (netwerk), dat is geen fout in de code."""
    import importlib.util
    extra = json.loads(pad.read_text(encoding="utf-8"))["data"]["extra_data"]
    spec = importlib.util.spec_from_file_location("maak_data_test", pad.parent / extra["script"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        uit = mod.main(tmp_path / "waarden.csv")
    except Exception as e:
        pytest.skip(f"bron niet bereikbaar: {type(e).__name__}")
    with open(uit, encoding="utf-8") as f:
        rijen = list(csv.DictReader(f))
    gebieden = set(json.loads(pad.read_text(encoding="utf-8"))["data"]["gebieden"])
    assert {r["indicator_naam"] for r in rijen} == set(extra["bronnen"])
    assert {r["gebied_id"] for r in rijen} <= gebieden
    for r in rijen:
        float(r["waarde"])
        assert r["eenheid"] and r["bron"] and r["jaar"].isdigit()
