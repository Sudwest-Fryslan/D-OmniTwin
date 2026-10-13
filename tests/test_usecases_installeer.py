"""
Use-case-uitvoerder, installeren en testen (omnitwin.usecases): zonder laad-API een melding,
één ingang voor demopakketten en laad-API-use cases, en wat er naar de API gaat. Geen stack:
de API is een nepobject.
"""

import json
from pathlib import Path

import pytest

from omnitwin import usecases as uc

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


class NepApi:
    basis = "http://nep"

    def __init__(self):
        self.aanroepen = []

    def registreer(self, reg):
        self.aanroepen.append(("registreer", reg["id"], sorted(reg)))

    def lever(self, ds_id, pad, route="laden", alleen_valideren=False):
        self.aanroepen.append(("lever", ds_id, Path(pad).name, route))
        return {"http": 200, "status": "gepubliceerd", "versie": 1}

    def beheer(self, pad_api, bestand):
        self.aanroepen.append(("beheer", pad_api, Path(bestand).name))
        return {"http": 200}


@pytest.fixture
def fixture_usecases(tmp_path):
    root = tmp_path / "usecases"
    map_ = root / "voorbeeld"
    (map_ / "datasets").mkdir(parents=True)
    defs = {
        "indicatoren": [{"id": "00000000-0000-4000-8000-000000000001", "naam": "X", "status": "O"}],
        "gebiedstypen": [{"id": "00000000-0000-4000-8000-0000000000a1", "naam": "CBS buurten", "actief": True}],
        "relaties": [],
    }
    (map_ / "definities.json").write_text(json.dumps(defs), encoding="utf-8")
    reg = json.loads(
        (ROOT / "usecases" / "swf-adapter-fme" / "datasets" / "swf-monitor-definities.json").read_text(encoding="utf-8")
    )
    reg["bron"] = {"adapter": "usecase-bestand", "pad": "definities.json"}
    (map_ / "datasets" / "swf-monitor-definities.json").write_text(json.dumps(reg), encoding="utf-8")
    (map_ / "usecase.json").write_text(
        json.dumps(
            {
                "naam": "voorbeeld",
                "versie": "0.1.0",
                "titel": "Voorbeeld",
                "vraag": "?",
                "gebruiker": "test",
                "status": "ontwerp",
                "afhankelijk_van": [],
                "rechten": [],
                "controles": [{"type": "viewer", "stap": "x", "verwacht": "y"}],
                "datasets": [
                    {
                        "id": "swf-monitor-definities",
                        "route": "compat",
                        "registratie": "datasets/swf-monitor-definities.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "oud").mkdir()
    (root / "oud" / "usecase.json").write_text(json.dumps({"naam": "oud", "titel": "Oud"}), encoding="utf-8")
    return uc.lees_usecases(root)


def test_zonder_laad_api_een_melding(fixture_usecases, monkeypatch, capsys):
    monkeypatch.setattr(uc, "laad_api_beschikbaar", lambda basis=None: False)
    oud = []
    monkeypatch.setattr(uc, "oude_route", oud.extend)
    res = uc.installeer(["oud", "voorbeeld"], ucs=fixture_usecases, ook_ontwerp=True)
    assert oud == ["oud"]
    assert res == {"voorbeeld": "laad-API nog niet beschikbaar"}
    assert "laad-API nog niet beschikbaar" in capsys.readouterr().out
    assert uc.test("voorbeeld", ucs=fixture_usecases) is None


def test_ontwerp_wordt_bij_installeren_overgeslagen(fixture_usecases, monkeypatch, capsys):
    monkeypatch.setattr(uc, "laad_api_beschikbaar", lambda basis=None: True)
    monkeypatch.setattr(uc, "oude_route", lambda namen, **kw: None)
    assert uc.installeer(["voorbeeld"], ucs=fixture_usecases, api=NepApi()) == {}
    assert "voorbeeld: overgeslagen (status ontwerp)" in capsys.readouterr().out


def test_installeren_registreert_en_levert_via_compat(fixture_usecases, monkeypatch, tmp_path):
    monkeypatch.setattr(uc, "laad_api_beschikbaar", lambda basis=None: True)
    monkeypatch.setattr(uc, "oude_route", lambda namen, **kw: None)
    api = NepApi()
    res = uc.installeer(["voorbeeld"], ucs=fixture_usecases, api=api, uit=tmp_path, ook_ontwerp=True)
    assert res["voorbeeld"]["swf-monitor-definities"][0]["status"] == "gepubliceerd"
    assert api.aanroepen == [
        ("registreer", "swf-monitor-definities", ["beschrijving", "bronId", "id", "laadprofiel"]),
        ("lever", "swf-monitor-definities", "definities.json", "compat"),
    ]


def test_test_voert_controles_uit(fixture_usecases, monkeypatch):
    monkeypatch.setattr(uc, "laad_api_beschikbaar", lambda basis=None: True)
    monkeypatch.setattr(uc, "oude_route", lambda namen, **kw: None)
    uit = uc.test("voorbeeld", ucs=fixture_usecases, api=NepApi())
    assert uit[0]["resultaat"] == "overgeslagen" and "viewer" in uit[0]["melding"]


def test_bestanden_van_map(tmp_path):
    (tmp_path / "waarden").mkdir()
    for n in ("b.json", "a.json", "c.txt"):
        (tmp_path / "waarden" / n).write_text("[]", encoding="utf-8")
    assert [p.name for p in uc.bestanden_van([tmp_path / "waarden", tmp_path / "x.zip"])] == [
        "a.json",
        "b.json",
        "x.zip",
    ]


def test_token_vraagt_machineclient(monkeypatch):
    monkeypatch.delenv("OMNITWIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("OMNITWIN_CLIENT_SECRET", raising=False)
    with pytest.raises(uc.UseCaseFout, match="OMNITWIN_CLIENT_ID"):
        uc.token("http://nep")


def test_laad_api_niet_bereikbaar():
    assert uc.laad_api_beschikbaar("http://127.0.0.1:9") is False


def _variant_usecase(tmp_path, met_intern):
    """Use case met demodata als standaardbron en een variant 'intern' met als_beschikbaar (#236)."""
    root = tmp_path / "usecases"
    map_ = root / "demo"
    (map_ / "datasets").mkdir(parents=True)
    rij = "gebied_code,indicator_uuid,jaar,waarde,bron\nBU19000002,00000000-0000-4000-8000-000000000001,2024,{w},{b}\n"
    (map_ / "demo.csv").write_text(rij.format(w=1, b="DEMODATA"), encoding="utf-8")
    intern = tmp_path / "intern"
    intern.mkdir()
    if met_intern:
        (intern / "echt.csv").write_text(rij.format(w=42, b="intern"), encoding="utf-8")
    ds = {
        "id": "demo-waarden",
        "beschrijving": {"dct:title": "Demo", "dct:type": "demodata"},
        "laadprofiel": {"profiel": "waarnemingen"},
        "bron": {"adapter": "usecase-bestand", "pad": "demo.csv"},
        "bewerkingen": [{"getal": ["jaar", "waarde"]}],
        "levering": {"formaat": "datapackage", "bestand": "demo.zip"},
        "varianten": {
            "intern": {
                "als_beschikbaar": True,
                "bron": {"adapter": "lokaal-bestand", "pad": "${SWF_DUMP_DIR}/echt.csv"},
                "beschrijving": {"dct:type": "brondata"},
            }
        },
    }
    (map_ / "datasets" / "demo-waarden.json").write_text(json.dumps(ds), encoding="utf-8")
    (map_ / "usecase.json").write_text(
        json.dumps(
            {
                "naam": "demo",
                "versie": "0.1.0",
                "titel": "Demo",
                "datasets": [{"id": "demo-waarden", "route": "laden", "registratie": "datasets/demo-waarden.json"}],
            }
        ),
        encoding="utf-8",
    )
    return uc.lees_usecases(root)["demo"], {"SWF_DUMP_DIR": str(intern)}


@pytest.mark.parametrize(
    "met_intern,waarde,variant,soort", [(True, "42", "intern", "brondata"), (False, "1", None, "demodata")]
)
def test_variant_als_beschikbaar_anders_de_standaardbron(tmp_path, met_intern, waarde, variant, soort):
    import zipfile

    u, env = _variant_usecase(tmp_path, met_intern)
    paden, rapport = uc.maak_levering(u, u["datasets"][0], tmp_path / "uit", bron_env=env)
    assert rapport["variant"] == variant
    with zipfile.ZipFile(paden[0]) as z:
        import csv

        assert next(csv.DictReader(z.read("waarnemingen.csv").decode().splitlines()))["waarde"] == waarde
        assert json.loads(z.read("dcat.jsonld"))["dct:type"] == soort


def test_variant_bron_en_stappen_worden_gecontroleerd(tmp_path):
    u, _ = _variant_usecase(tmp_path, False)
    d = uc.lees_dataset(u, u["datasets"][0])
    d["varianten"]["intern"]["bron"] = {"adapter": "lokaal-bestand", "pad": "/etc/passwd"}
    (u["_map"] / "datasets" / "demo-waarden.json").write_text(json.dumps(d), encoding="utf-8")
    fouten = uc.dataset_fouten(u, u["datasets"][0])
    assert any("varianten.intern.bron" in f for f in fouten)


def test_inrichting_van_demo_met_datasets_na_de_laad_api(tmp_path, monkeypatch):
    """Een demopakket met `datasets` (ook leeg) krijgt na de laad-API alleen zijn inrichting."""
    root = tmp_path / "usecases"
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "usecase.json").write_text(
        json.dumps(
            {
                "naam": "demo",
                "versie": "0.1.0",
                "titel": "Demo",
                "datasets": [],
                "data": {"indicatoren": [{"naam": "X", "richting": "neutraal"}]},
            }
        ),
        encoding="utf-8",
    )
    aanroepen = []
    monkeypatch.setattr(
        uc, "oude_route", lambda namen, alleen_inrichting=False: aanroepen.append((namen, alleen_inrichting))
    )
    uc.installeer(["demo"], ucs=uc.lees_usecases(root), api=NepApi())
    assert aanroepen == [([], False), (["demo"], True)]


def test_mislukt_telt_fouten_en_afkeuringen_niet_overgeslagen():
    res = {
        "a": {"x": "overgeslagen: geen netwerk", "y": [{"status": "gepubliceerd", "http": 201}]},
        "b": {
            "z": "fout: RuntimeError: kapot",
            "w": [{"status": "afgekeurd", "http": 422}],
            "v": [{"status": "overgeslagen", "http": 501}],
        },
        "c": "laad-API nog niet beschikbaar",
    }
    assert uc.mislukt(res) == ["b/z", "b/w"]
