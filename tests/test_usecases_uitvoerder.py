"""
Use-case-uitvoerder (omnitwin.usecases): manifesten, afhankelijkheden, index, en
`controleer` op een kleine fixture-use-case. Geen stack, geen netwerk; frictionless,
fiona en shapely zijn niet nodig.
"""

import json
import shutil
from pathlib import Path

import pytest

from omnitwin import usecases as uc
from omnitwin.laden.registratie import laad_openapi

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
ALLE = uc.lees_usecases()
MET_DATASETS = {n: u for n, u in ALLE.items() if "datasets" in u}


def m(naam, *afh, status=None, versie="0.1.0"):
    u = {"naam": naam, "titel": naam, "versie": versie, "afhankelijk_van": list(afh)}
    if status:
        u["status"] = status
    return u


def ucs(*manifesten):
    return {u["naam"]: u for u in manifesten}


# ---------------------------------------------------------------- volgorde en plan

def test_volgorde_afhankelijkheden_eerst_en_elk_een_keer():
    s = ucs(m("a"), m("b", "a"), m("c", "a", "b"), m("d", "c", "b"))
    assert uc.volgorde(["d"], s) == ["a", "b", "c", "d"]
    assert uc.volgorde(["b", "d", "a"], s) == ["a", "b", "c", "d"]


def test_volgorde_volgt_de_volgorde_van_afhankelijk_van():
    s = ucs(m("x"), m("y"), m("top", "y", "x"))
    assert uc.volgorde(["top"], s) == ["y", "x", "top"]


def test_cyclus_geeft_fout():
    s = ucs(m("a", "c"), m("b", "a"), m("c", "b"))
    with pytest.raises(uc.UseCaseFout, match="cyclus"):
        uc.volgorde(["a"], s)


def test_onbekende_naam_geeft_fout():
    with pytest.raises(uc.UseCaseFout, match="onbekende use case 'bestaat-niet'"):
        uc.volgorde(["a"], ucs(m("a", "bestaat-niet")))


def test_versie_eis():
    s = ucs(m("basis", versie="0.2.1"), m("ok", {"naam": "basis", "versie": ">=0.2.0,<1.0.0"}),
            m("te-nieuw", {"naam": "basis", "versie": ">=0.3.0"}))
    assert uc.volgorde(["ok"], s) == ["basis", "ok"]
    with pytest.raises(uc.UseCaseFout, match="vraagt basis >=0.3.0"):
        uc.volgorde(["te-nieuw"], s)


@pytest.mark.parametrize("versie,eis,ok", [
    ("0.1.0", ">=0.1.0", True), ("0.1.0", ">0.1.0", False), ("1.2.3", "1.2.3", True), ("1.2.3", "==1.2", False),
    ("0.9.9", "<1.0.0", True), ("1.0.0", ">=0.1,<1", False), ("2.0.0", None, True),
])
def test_voldoet(versie, eis, ok):
    assert uc.voldoet(versie, eis) is ok


def test_extern_nog_niet_ondersteund():
    s = ucs(m("a", {"naam": "x", "bron": "https://github.com/voorbeeld/usecases", "versie": "v1.0.0"}))
    with pytest.raises(uc.UseCaseFout, match="externe use cases nog niet ondersteund"):
        uc.volgorde(["a"], s)


def test_ontwerp_en_afhankelijken_overgeslagen_optioneel_niet():
    s = ucs(m("api", status="ontwerp"), m("hangt-af", "api"), m("los"),
            m("optioneel", {"naam": "api", "optioneel": True}), m("indirect", "hangt-af"))
    orde, over = uc.plan([], s, alle=True)
    assert orde == ["los", "optioneel"]
    assert over == {"api": "status ontwerp", "hangt-af": "hangt af van api (overgeslagen)",
                    "indirect": "hangt af van hangt-af (overgeslagen)"}


def test_boom():
    s = ucs(m("a"), m("b", "a"), m("c", "b", {"naam": "a", "optioneel": True}))
    assert uc.boom("c", s).splitlines() == ["c 0.1.0", "└── b 0.1.0", "    └── a 0.1.0", "└── a 0.1.0 (optioneel)"]


# ---------------------------------------------------------------- de use cases in de repo

@pytest.mark.parametrize("naam", sorted(ALLE))
def test_manifest_geldig(naam):
    fouten = uc.valideer_manifest(ALLE[naam], naam)
    assert not fouten, "\n".join(fouten)


def test_namen_en_ids_uniek_en_gelijk_aan_map():
    ids = [u["id"] for u in ALLE.values() if "id" in u]
    assert len(ids) == len(set(ids)), ids
    for naam, u in ALLE.items():
        assert u.get("naam", naam) == naam


def test_alle_afhankelijkheden_oplosbaar():
    uc.volgorde(sorted(ALLE), ALLE)


def test_swf_gebiedsmonitor_neemt_alle_swf_use_cases_mee_in_de_goede_volgorde():
    orde = uc.volgorde(["swf-gebiedsmonitor"], ALLE)
    assert {n for n in ALLE if n.startswith("swf-")} == set(orde) - {"cbs-gebiedsindelingen"}
    for eerder, later in [("swf-definities", "swf-gebiedsindelingen"), ("swf-gebiedsindelingen", "swf-kompasprofiel"),
                          ("swf-kompasprofiel", "swf-basismonitor-waarden"), ("swf-basismonitor-waarden", "swf-kaartlagen")]:
        assert orde.index(eerder) < orde.index(later)


def test_demopakketten_blijven_laden():
    """Geen gedragswijziging voor laad_usecase.py --alle: de vijf demopakketten, in dezelfde volgorde."""
    orde, _ = uc.plan([], ALLE, alle=True)
    oud = [n for n in orde if "datasets" not in ALLE[n]]
    assert oud == sorted(n for n, u in ALLE.items() if "datasets" not in u and u.get("status") != "ontwerp")
    assert not [n for n in orde if "datasets" in ALLE[n]], "laad-API-use cases met status ontwerp horen overgeslagen"


@pytest.mark.parametrize("naam", sorted(MET_DATASETS))
def test_datasets_geldig(naam):
    spec = laad_openapi()
    u = MET_DATASETS[naam]
    for ds in u["datasets"]:
        fouten = uc.dataset_fouten(u, ds, spec)
        assert not fouten, "\n".join(fouten)


def test_zelfde_dataset_zelfde_registratie():
    """Een dataset die in meer use cases voorkomt (bijv. swf-monitor-waarden), heeft overal dezelfde registratie."""
    gezien = {}
    for u in MET_DATASETS.values():
        for ds in u["datasets"]:
            if not ds.get("registratie"):
                continue
            reg = uc.registratie_voor_api(uc.lees_dataset(u, ds))
            if ds["id"] in gezien:
                assert reg == gezien[ds["id"]][1], f"{ds['id']}: registratie in {u['naam']} wijkt af van {gezien[ds['id']][0]}"
            else:
                gezien[ds["id"]] = (u["naam"], reg)


def test_geen_code_in_use_cases():
    for naam, u in ALLE.items():
        assert not uc.bestandsfouten(u["_map"], naam)


def test_bestandscontrole_keurt_code_af(tmp_path):
    map_ = tmp_path / "voorbeeld"
    (map_ / "bewijs").mkdir(parents=True)
    for f in ("usecase.json", "README.md", "mapping.csv", "bewijs/kaart.png", "bewijs/README.md"):
        (map_ / f).write_text("x", encoding="utf-8")
    assert uc.bestandsfouten(map_) == []
    for f in ("maak_levering.py", "run.sh", "tool.ps1", "bewijs/x.js", "zonder_extensie"):
        (map_ / f).write_text("x", encoding="utf-8")
    fouten = uc.bestandsfouten(map_)
    assert len(fouten) == 5 and all("niet toegestaan" in f for f in fouten)


def test_index_actueel():
    assert uc.werk_index_bij(controleer=True), "python -m omnitwin.usecases index"


def test_registratievoorbeelden_uit_de_specificatie_zijn_geldig():
    from omnitwin.laden.registratie import valideer_registratie
    spec = laad_openapi()
    for naam in ("RegistratieWaarnemingen", "RegistratieKaartlaag"):
        assert valideer_registratie(spec["components"]["examples"][naam]["value"], spec) == []
    fout = {"id": "X", "beschrijving": {"@type": "dcat:Dataset"}, "laadprofiel": {"profiel": "kaartlaag"}}
    fouten = valideer_registratie(fout, spec)
    assert any("patroon" in f for f in fouten) and any("dct:title" in f for f in fouten) and any("featureTabel" in f for f in fouten)


# ---------------------------------------------------------------- controleer (fixture zonder netwerk en zonder GDAL)

DEFINITIES = {
    "indicatoren": [{"id": "00000000-0000-4000-8000-000000000001", "naam": "Voorbeeld", "status": "A",
                     "begingeldigheid": "2024-11-20 00:00"}],
    "gebiedstypen": [{"id": "00000000-0000-4000-8000-0000000000a1", "naam": "CBS buurten", "actief": True}],
    "relaties": [{"indicator_id": "00000000-0000-4000-8000-000000000001", "gebiedstype_id": "00000000-0000-4000-8000-0000000000a1"}],
}


@pytest.fixture
def fixture_usecases(tmp_path):
    root = tmp_path / "usecases"
    map_ = root / "voorbeeld-adapter"
    (map_ / "datasets").mkdir(parents=True)
    (map_ / "definities.json").write_text(json.dumps(DEFINITIES), encoding="utf-8")
    (map_ / "README.md").write_text("# voorbeeld", encoding="utf-8")
    reg = json.loads((ROOT / "usecases" / "swf-adapter-fme" / "datasets" / "swf-monitor-definities.json").read_text(encoding="utf-8"))
    reg["bron"] = {"adapter": "usecase-bestand", "pad": "definities.json"}
    (map_ / "datasets" / "swf-monitor-definities.json").write_text(json.dumps(reg), encoding="utf-8")
    (map_ / "usecase.json").write_text(json.dumps({
        "naam": "voorbeeld-adapter", "versie": "0.1.0", "titel": "Voorbeeld", "vraag": "?", "gebruiker": "test",
        "status": "ontwerp", "afhankelijk_van": [], "rechten": [],
        "datasets": [{"id": "swf-monitor-definities", "route": "compat", "registratie": "datasets/swf-monitor-definities.json"}],
        "controles": [{"type": "aantal", "dataset": "swf-monitor-definities", "resource": "indicatoren", "gelijk": 1},
                      {"type": "bewerking", "dataset": "swf-monitor-definities", "reden": "status: A → O", "gelijk": 1},
                      {"type": "api", "pad": "/api/data/v1/indicatoren"}]}), encoding="utf-8")
    return root


def test_controleer_maakt_en_valideert_de_levering(fixture_usecases, tmp_path):
    s = uc.lees_usecases(fixture_usecases)
    r = uc.controleer("voorbeeld-adapter", tmp_path / "uit", s)
    assert r["manifest"] == []
    d = r["datasets"]["swf-monitor-definities"]
    assert d["status"] == "ok", d
    assert d["leveringen"][0]["geldig"] and d["leveringen"][0]["aantallen"]["indicatoren"] == 1
    assert [c["resultaat"] for c in r["controles"]] == ["ok", "ok", "alleen-api"]
    assert r["geldig"]
    geleverd = json.loads((tmp_path / "uit" / "swf-monitor-definities" / "definities.json").read_text(encoding="utf-8"))
    assert geleverd["indicatoren"][0]["status"] == "O"


def test_controleer_variant_ruw_wordt_afgekeurd(fixture_usecases, tmp_path):
    r = uc.controleer("voorbeeld-adapter", tmp_path / "uit", uc.lees_usecases(fixture_usecases), variant="ruw")
    d = r["datasets"]["swf-monitor-definities"]
    assert d["status"] == "fout" and "onbekende status" in d["leveringen"][0]["fouten"][0]
    assert not r["geldig"]


def test_controleer_ontbrekende_bron_is_overgeslagen(fixture_usecases, tmp_path, monkeypatch):
    monkeypatch.delenv("SWF_DUMP_DIR", raising=False)
    reg_pad = fixture_usecases / "voorbeeld-adapter" / "datasets" / "swf-monitor-definities.json"
    reg = json.loads(reg_pad.read_text(encoding="utf-8"))
    reg["bron"] = {"adapter": "swf-dump", "export": "definities"}
    reg_pad.write_text(json.dumps(reg), encoding="utf-8")
    r = uc.controleer("voorbeeld-adapter", tmp_path / "uit", uc.lees_usecases(fixture_usecases), bron_env={})
    assert r["datasets"]["swf-monitor-definities"]["status"].startswith("overgeslagen: SWF_DUMP_DIR")
    assert r["geldig"] and r["controles"][0]["resultaat"] == "overgeslagen"


def test_controleer_keurt_code_in_de_map_af(fixture_usecases, tmp_path):
    shutil.copy(__file__, fixture_usecases / "voorbeeld-adapter" / "maak_levering.py")
    r = uc.controleer("voorbeeld-adapter", tmp_path / "uit", uc.lees_usecases(fixture_usecases))
    assert any("maak_levering.py" in f for f in r["manifest"]) and not r["geldig"]


def test_laad_usecase_slaat_laad_api_use_cases_over(capsys):
    import sys
    sys.path.insert(0, str(ROOT / "init_data" / "scripts"))
    pytest.importorskip("psycopg2")
    import laad_usecase
    namen = laad_usecase.pakketten([], True)
    assert namen == sorted(n for n, u in ALLE.items() if "datasets" not in u)
    assert "swf-definities: overgeslagen (status ontwerp)" in capsys.readouterr().out
