"""
CBS Kerncijfers-bronpakket (init_data/cbs, #159): mapping per jaar compleet, codes bestaan in
de geometrie 2024, jaar = peiljaar, en geen dubbele indicatoren. Geen stack en geen netwerk nodig.
"""

import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
CBS = ROOT / "init_data" / "cbs"
SAMPLE = ROOT / "init_data" / "sample" / "2_brondata" / "sample_indicatoren.csv"


def _script():
    spec = importlib.util.spec_from_file_location(
        "download_cbs_kerncijfers", ROOT / "init_data" / "scripts" / "download_cbs_kerncijfers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _script()


@pytest.fixture(scope="module")
def rijen():
    with open(CBS / "kerncijfers_fryslan.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def package():
    return json.loads((CBS / "datapackage.json").read_text(encoding="utf-8"))


def test_tabellen_vanaf_2019_aaneengesloten():
    jaren = sorted(S.TABELLEN)
    assert jaren[0] == 2019 and jaren == list(range(2019, jaren[-1] + 1))
    assert len(set(S.TABELLEN.values())) == len(S.TABELLEN), "tabel-ID dubbel"


def test_mapping_per_jaar_compleet():
    for naam, per_jaar in S.MAPPING.items():
        assert naam in S.INDICATOREN, f"{naam}: geen UUID"
        jaren = set(per_jaar) | S.NIET_GEPUBLICEERD.get(naam, set())
        assert jaren == set(S.TABELLEN), f"{naam}: jaren zonder kolom: {sorted(set(S.TABELLEN) - jaren)}"
        assert not set(per_jaar) & S.NIET_GEPUBLICEERD.get(naam, set())
    for naam, a in S.AFGELEID.items():
        assert a["teller"] in S.MAPPING and a["noemer"] in S.MAPPING


def test_package_beschrijft_mapping(package):
    for jaar, tabel in S.TABELLEN.items():
        t = package["tabellen"][str(jaar)]
        assert t["tabel"] == tabel and t["peiljaar"] == jaar
        assert t["titel"] == f"Kerncijfers wijken en buurten {jaar}", "TableInfos-titel past niet bij het peiljaar"
    for naam, per_jaar in S.MAPPING.items():
        kolommen = package["indicatoren"][naam]["kolommen"]
        assert {int(j) for j in kolommen} == set(per_jaar), f"{naam}: CSV gemaakt met een andere mapping"


def test_codes_bestaan_in_geometrie_2024(rijen):
    codes = set(S.geometrie_codes())
    los = {r["gebied_id"] for r in rijen} - codes
    assert not los, f"Buurtcodes niet in de geometrie {S.GEOMETRIE_JAAR}: {sorted(los)[:10]}"


def test_jaar_is_peiljaar(rijen):
    fout = [r for r in rijen
            if r["bron_tabel"] != S.TABELLEN.get(int(r["jaar"]))
            or r["bron"] != f"CBS Kerncijfers wijken en buurten {r['jaar']} ({r['bron_tabel']})"]
    assert not fout, f"{len(fout)} rijen met jaar ≠ peiljaar, bijv. {fout[0]}"


def test_geen_dubbele_indicatoren_of_rijen(rijen):
    naam_uuid, uuid_naam = defaultdict(set), defaultdict(set)
    sleutels = set()
    for r in rijen:
        naam_uuid[r["indicator_naam"]].add(r["indicator_uuid"])
        uuid_naam[r["indicator_uuid"]].add(r["indicator_naam"])
        k = (r["gebied_id"], r["indicator_uuid"], r["jaar"], r["scenario_id"])
        assert k not in sleutels, f"dubbele rij {k}"
        sleutels.add(k)
    assert all(len(v) == 1 for v in naam_uuid.values()), "naam met meerdere UUID's"
    assert all(len(v) == 1 for v in uuid_naam.values()), "UUID met meerdere namen"


def test_zelfde_uuids_als_sample_en_sample_is_deelverzameling(rijen):
    with open(SAMPLE, encoding="utf-8") as f:
        sample = list(csv.DictReader(f))
    sample_uuid = {}
    for r in sample:
        sample_uuid.setdefault(r["indicator_naam"], set()).add(r["indicator_uuid"])
    for naam, (u, *_rest) in S.INDICATOREN.items():
        assert sample_uuid.get(naam, {u}) == {u}, f"{naam}: andere UUID in de sample: {sample_uuid[naam]}"

    gebieden = {r["gebied_id"] for r in sample}
    verwacht = {(r["gebied_id"], r["indicator_uuid"], r["jaar"], r["waarde"]) for r in rijen
                if r["gebied_id"] in gebieden}
    cbs = {(r["gebied_id"], r["indicator_uuid"], r["jaar"], r["waarde"]) for r in sample
           if r["bron"].startswith("CBS Kerncijfers")}
    assert cbs == verwacht, "CBS-rijen in de sample wijken af van init_data/cbs (draai --alleen-sample)"
    assert not [r for r in sample if r["bron"] == "Kerncijfers wijken en buurten 2023"], \
        "verkeerd gelabelde Kerncijfers (2021 als 2023) nog in de sample"


def test_afgeleid_uit_zelfde_jaar(rijen):
    w = {(r["gebied_id"], r["indicator_naam"], r["jaar"]): float(r["waarde"]) for r in rijen}
    for (g, naam, jaar), v in w.items():
        if naam != "65+ jaar (%)":
            continue
        t, n = w[(g, "65+ jaar", jaar)], w[(g, "Inwoners", jaar)]
        assert abs(v - t / n * 100) < 0.051, f"{g} {jaar}: {v} ≠ {t}/{n}"


def test_bolsward_noord_heeft_reeks(rijen):
    jaren = defaultdict(set)
    for r in rijen:
        if r["gebied_id"] == "BU19000001":
            jaren[r["indicator_naam"]].add(int(r["jaar"]))
    assert len(jaren["Inwoners"]) >= 5 and len(jaren["65+ jaar (%)"]) >= 5
