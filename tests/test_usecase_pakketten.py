"""
Demo-use cases (TC-06-*) en de sample: de data komt via de laad-API uit de datasets van de
afhankelijkheden (open bronnen; wat nog niet open is, gemarkeerd als demodata), niet uit
directe databasevulling (#236). Geen stack en geen netwerk nodig.
"""

import csv
import json
from pathlib import Path

import pytest

from omnitwin import usecases as uc

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "init_data" / "sample" / "2_brondata" / "sample_indicatoren.csv"
DEFINITIES = ROOT / "db" / "stuurdata" / "indicatoren.csv"
UCS = uc.lees_usecases()
# Demopakketten: de verouderde velden (persona, data, inrichting) voor de inrichting en de verwachting
DEMO = sorted(n for n, u in UCS.items() if "persona" in u)
RICHTINGEN = {"hoger_is_beter", "lager_is_beter", "neutraal"}
OPEN_ADAPTERS = {"cbs-odata", "cbs-statline", "wcs-zonaal", "wfs", "download"}


def cbs_recept():
    return json.loads((ROOT / "init_data" / "cbs" / "datapackage.json").read_text(encoding="utf-8"))["indicatoren"]


def definities():
    """naam -> uuid: de stuurdata (db/stuurdata/indicatoren.csv) en het CBS-recept."""
    with open(DEFINITIES, encoding="utf-8") as f:
        uit = {r["naam"]: r["uuid"] for r in csv.DictReader(f)}
    uit.update({n: i["uuid"] for n, i in cbs_recept().items()})
    return uit


def geleverde_uuids(naam):
    """{uuid: (use case, dataset, adapter)} die de datasets van deze use case leveren."""
    u = UCS[naam]
    uit = {}
    for ds in u.get("datasets", []):
        d = uc.lees_dataset(u, ds)
        adapter = d["bron"]["adapter"]
        if adapter == "cbs-odata":
            for i in cbs_recept().values():
                uit[i["uuid"]] = (naam, d["id"], adapter)
        for stap in d.get("bewerkingen", []):
            if stap.get("waarde_map", {}).get("naar") == "indicator_uuid":
                uit.update({v: (naam, d["id"], adapter) for v in stap["waarde_map"]["map"].values()})
            if "indicator_uuid" in stap.get("constant", {}):
                uit[stap["constant"]["indicator_uuid"]] = (naam, d["id"], adapter)
            if stap.get("filter", {}).get("veld") == "indicator_uuid":
                uit.update({v: (naam, d["id"], adapter) for v in stap["filter"]["in"]})
    return uit


def geleverd_voor(naam):
    """Alles wat de use case en zijn afhankelijkheden leveren."""
    uit = {}
    for n in uc.volgorde([naam], UCS):
        uit.update(geleverde_uuids(n))
    return uit


def sample_rijen():
    with open(SAMPLE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("naam", DEMO)
def test_demo_use_case_is_volledig_en_actief(naam):
    u = UCS[naam]
    assert "datasets" in u, f"{naam}: data komt via de laad-API (datasets, eventueel leeg, en afhankelijk_van)"
    assert u["status"] == "actief"
    assert not uc.valideer_manifest(u, naam)
    assert u["data"]["focus"] in u["data"]["gebieden"]
    assert "afgeleid" not in u["data"], "afgeleide indicatoren komen uit het CBS-recept, niet uit directe databasevulling"
    assert "extra_data" not in u["data"], "downloadbare data hoort in een dataset met een bronadapter"
    assert not (u["_map"] / "data").exists(), "geen eigen waarden.csv: data via datasets"


@pytest.mark.parametrize("naam", DEMO)
def test_elke_indicator_komt_uit_een_dataset_van_een_afhankelijkheid(naam):
    defs, geleverd = definities(), geleverd_voor(naam)
    for ind in UCS[naam]["data"]["indicatoren"]:
        assert ind["richting"] in RICHTINGEN, f"{ind['naam']}: onbekende richting {ind['richting']}"
        assert ind["naam"] in defs, f"{naam}: indicator '{ind['naam']}' heeft geen definitie"
        assert defs[ind["naam"]] in geleverd, f"{naam}: '{ind['naam']}' wordt door geen dataset geleverd"


@pytest.mark.parametrize("naam", DEMO)
def test_controles_vragen_naar_geleverde_indicatoren(naam):
    geleverd = geleverd_voor(naam)
    for c in UCS[naam]["controles"]:
        if c["type"] == "api" and c.get("uuid"):
            assert c["uuid"] in geleverd, f"{naam}: controle op {c['uuid']} die niemand levert"


def test_sample_bevat_alleen_wat_nog_niet_open_is_of_geen_adapter_heeft():
    """Wat een open-bron-adapter levert (CBS, RIVM, Politie, WCS), staat niet meer in de sample."""
    open_ = {}
    for n in UCS:
        open_.update({k: v for k, v in geleverde_uuids(n).items() if v[2] in OPEN_ADAPTERS})
    dubbel = {r["indicator_naam"] for r in sample_rijen() if r["indicator_uuid"] in open_}
    assert not dubbel, f"in de sample, maar te downloaden via een adapter: {sorted(dubbel)}"


def test_alle_sampledata_hoort_bij_een_dataset():
    gedekt = geleverde_uuids("sample-bronbibliotheek")
    los = {r["indicator_naam"] for r in sample_rijen() if r["indicator_uuid"] not in gedekt}
    assert not los, f"indicatoren in de sample zonder dataset: {sorted(los)}"


def test_demodata_is_gemarkeerd():
    """Demodata is herkenbaar: in de bron van elke waarde en in de DCAT van de dataset."""
    u = UCS["sample-bronbibliotheek"]
    intern = next(uc.lees_dataset(u, d) for d in u["datasets"] if d["id"] == "sample-intern-demodata")
    assert intern["beschrijving"]["dct:type"] == "demodata"
    assert "plaatsvervanger" in intern["beschrijving"]["dct:description"]
    assert intern["varianten"]["intern"]["als_beschikbaar"] is True
    assert "${SWF_" in intern["varianten"]["intern"]["bron"].get("omschrijving", "") or \
        intern["varianten"]["intern"]["bron"]["adapter"] == "swf-dump"
    intern_uuids = set(next(s["filter"]["in"] for s in intern["bewerkingen"] if "filter" in s))
    for r in sample_rijen():
        if r["indicator_uuid"] in intern_uuids or r["gebied_id"] == "BU19000002":
            assert r["bron"].startswith("DEMODATA"), f"{r['gebied_id']} {r['indicator_naam']}: niet gemarkeerd"
        else:
            assert "DEMO" not in r["bron"].upper(), f"{r['gebied_id']} {r['indicator_naam']}: onterecht demodata"


def test_definities_uniek_en_compleet():
    with open(DEFINITIES, encoding="utf-8") as f:
        rijen = list(csv.DictReader(f))
    assert len({r["uuid"] for r in rijen}) == len(rijen)
    assert len({r["naam"] for r in rijen}) == len(rijen)
    namen = {r["indicator_naam"] for r in sample_rijen()}
    assert namen <= {r["naam"] for r in rijen}
    for r in rijen:
        assert r["bron"], f"{r['naam']}: herkomst ontbreekt"
        assert r["interpretatie_logica"] in {"pos_is_pos", "-/+", "N/A"}


def test_use_case_ids_uniek():
    ids = [u["id"] for u in UCS.values() if u.get("id")]
    assert len(ids) == len(set(ids)), f"Dubbele use-case-id's: {ids}"
