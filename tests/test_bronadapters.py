"""
Bronadapters en bewerkingen (omnitwin.bronadapters): veilige paden en domeinen, de
declaratieve bewerkingen, lezen en schrijven. Geen netwerk. Wat shapely, fiona of
frictionless nodig heeft, wordt overgeslagen als dat pakket ontbreekt.
"""

import csv
import io
import json
import zipfile

import pytest

from omnitwin import bronadapters as ba
from omnitwin.bronadapters.bewerkingen import BewerkingFout, naam_van, snake, voer_uit
from omnitwin.bronadapters.schrijvers import schrijf

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- paden en domeinen

def test_veilig_pad_alleen_onder_toegestane_map(tmp_path):
    (tmp_path / "sub").mkdir()
    assert ba.veilig_pad("${SWF_DOCS_DIR}/sub/a.gpkg", {"SWF_DOCS_DIR": str(tmp_path)}) == (tmp_path / "sub" / "a.gpkg").resolve()
    with pytest.raises(ba.BronFout, match="buiten"):
        ba.veilig_pad("${SWF_DOCS_DIR}/../geheim.txt", {"SWF_DOCS_DIR": str(tmp_path)})
    with pytest.raises(ba.BronFout, match="geen toegestane map"):
        ba.veilig_pad("${HOME}/.ssh/id_rsa", {"HOME": str(tmp_path)})
    with pytest.raises(ba.BronFout, match="moet beginnen"):
        ba.veilig_pad("/etc/passwd")


def test_map_niet_gezet_is_geen_bron(monkeypatch):
    monkeypatch.delenv("SWF_GEO_DIR", raising=False)
    with pytest.raises(ba.GeenBron):
        ba.veilig_pad("${SWF_GEO_DIR}/x.gpkg", {})


def test_repo_is_toegestaan():
    assert ba.veilig_pad("${REPO}/data-upload/Deelgebieden_omgevingsvisie.gpkg").exists()


@pytest.mark.parametrize("url,ok", [
    ("https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0", True),
    ("https://opendata.cbs.nl/ODataApi/odata/85984NED", True),
    ("http://service.pdok.nl/x", False),
    ("https://voorbeeld.org/x.gpkg", False),
    ("https://service.pdok.nl.voorbeeld.org/x", False),
])
def test_alleen_https_van_allowlist(url, ok, monkeypatch):
    monkeypatch.delenv("OMNITWIN_BRON_DOMEINEN", raising=False)
    if ok:
        assert ba.controleer_url(url) == url
    else:
        with pytest.raises(ba.BronFout):
            ba.controleer_url(url)


def test_allowlist_uit_te_breiden(monkeypatch):
    monkeypatch.setenv("OMNITWIN_BRON_DOMEINEN", "geo.voorbeeld.nl")
    assert ba.controleer_url("https://geo.voorbeeld.nl/wfs")


def test_onbekende_adapter():
    with pytest.raises(ba.BronFout, match="onbekende adapter"):
        ba.haal({"adapter": "shell", "cmd": "rm -rf /"}, {})


def test_usecase_bestand_alleen_json_csv_in_de_use_case(tmp_path):
    (tmp_path / "m.json").write_text('[{"a": 1}]', encoding="utf-8")
    assert ba.haal({"adapter": "usecase-bestand", "pad": "m.json"}, {"usecase_map": tmp_path}) == {"data": [{"a": 1}]}
    for pad in ("../m.json", "script.py"):
        with pytest.raises(ba.BronFout):
            ba.haal({"adapter": "usecase-bestand", "pad": pad}, {"usecase_map": tmp_path})


def test_swf_dump(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "api_backup_dump.json").write_text(json.dumps({"indicatoren": [{"id": "x"}], "gebiedstypen": [], "relaties": []}), encoding="utf-8")
    (tmp_path / "output" / "api_data_dump.json").write_text(json.dumps([{"indicator_id": "x", "jaar": 2020}]), encoding="utf-8")
    ctx = {"bronnen": {"SWF_DUMP_DIR": str(tmp_path)}}
    assert ba.haal({"adapter": "swf-dump", "export": "definities"}, ctx)["indicatoren"] == [{"id": "x"}]
    assert ba.haal({"adapter": "swf-dump", "export": "waarden"}, ctx) == {"waarden": [{"indicator_id": "x", "jaar": 2020}]}
    with pytest.raises(ba.BronFout):
        ba.haal({"adapter": "swf-dump", "export": "alles"}, ctx)


def test_lokaal_csv(tmp_path):
    (tmp_path / "l.csv").write_text("﻿Title,Indicator \nA,B\n", encoding="utf-8")
    t = ba.haal({"adapter": "lokaal-bestand", "pad": "${SWF_DUMP_DIR}/l.csv"}, {"bronnen": {"SWF_DUMP_DIR": str(tmp_path)}})
    assert t == {"data": [{"Title": "A", "Indicator": "B"}]}


# ---------------------------------------------------------------- bewerkingen

RIJEN = [
    {"indicator_id": "i1", "gebiedstype_id": "g-ws", "gebieds_id": 728, "jaar": 2020, "waarde": 1.5, "status": "A"},
    {"indicator_id": "i1", "gebiedstype_id": "g-bu", "gebieds_id": "BU19000002", "jaar": 0, "waarde": 2, "status": "O"},
    {"indicator_id": "i2", "gebiedstype_id": "g-bu", "gebieds_id": "BU19009997", "jaar": 2021, "waarde": 3, "status": "C"},
]


def bewerk(stappen, rijen=None, **kw):
    t, r = voer_uit({"t": [dict(x) for x in (rijen or RIJEN)]}, stappen, **kw)
    return t["t"], r


def test_afwijzen_filter_en_rapport():
    rijen, rapport = bewerk([
        {"filter": {"veld": "gebiedstype_id", "in": ["g-ws", "g-bu"]}},
        {"id": "jaar-0", "afwijzen": {"veld": "jaar", "gelijk": 0, "reden": "jaar-ongeldig"}},
        {"afwijzen": {"veld": "gebieds_id", "in": ["BU19009997"], "reden": "gebied-onbekend"}}])
    assert len(rijen) == 1 and rapport == {"gefilterd": 0, "jaar-ongeldig": 1, "gebied-onbekend": 1}


def test_variant_slaat_stap_over():
    rijen, rapport = bewerk([{"id": "jaar-0", "afwijzen": {"veld": "jaar", "gelijk": 0}}], sla_over=["jaar-0"])
    assert len(rijen) == 3 and rapport == {}


def test_hernoem_behoud_constant_tekst_prefix_waarde_map():
    rijen, rapport = bewerk([
        {"hernoem": {"gebieds_id": "gebied_code"}}, {"tekst": ["gebied_code"]},
        {"prefix": {"veld": "gebied_code", "prefix": "WS", "als": {"veld": "gebiedstype_id", "gelijk": "g-ws"}}},
        {"waarde_map": {"veld": "status", "map": {"A": "O"}}},
        {"constant": {"scenario": ""}}, {"behoud": ["gebied_code", "status", "scenario"]}])
    assert rijen[0] == {"gebied_code": "WS728", "status": "O", "scenario": ""}
    assert rijen[1]["gebied_code"] == "BU19000002"
    assert rapport == {"status: A → O": 1}


def test_jaar_uit_en_naar_datum():
    rijen, rapport = bewerk([{"jaar_uit_datum": {"veld": "d"}}],
                            [{"d": "2022-01-01"}, {"d": "2022-07-01"}, {"d": "0000-01-01"}, {"d": ""}])
    assert rijen == [{"d": "2022-01-01", "jaar": 2022, "peildatum": ""}, {"d": "2022-07-01", "jaar": "", "peildatum": "2022-07-01"}]
    assert rapport == {"jaar-ongeldig": 2}
    rijen, _ = bewerk([{"jaar_naar_datum": {"veld": "jaar", "naar": "begingeldigheid"}}], [{"jaar": 2012}])
    assert rijen[0]["begingeldigheid"] == "2012-01-01"


def test_iso_datumtijd_deel_sjabloon_nummer_getal():
    rijen, _ = bewerk([{"iso_datumtijd": ["b"]}, {"deel": {"veld": "c", "start": 2, "eind": 6, "naar": "gm"}},
                       {"sjabloon": {"naar": "n", "sjabloon": "{c}_BBKJ {onbekend}"}}, {"nummer": {"naar": "nr"}},
                       {"getal": ["w"]}],
                      [{"b": "2024-11-20 00:00", "c": "BU19000002", "w": "3"}, {"b": None, "c": "WK190001", "w": "2.5"}])
    assert rijen[0] == {"b": "2024-11-20T00:00:00", "c": "BU19000002", "w": 3, "gm": "1900", "n": "BU19000002_BBKJ ", "nr": 1}
    assert rijen[1]["b"] == "" and rijen[1]["w"] == 2.5 and rijen[1]["nr"] == 2


def test_sjabloon_voert_geen_code_uit():
    rijen, _ = bewerk([{"sjabloon": {"naar": "x", "sjabloon": "{c.__class__}{c[0]}"}}], [{"c": "abc"}])
    assert rijen[0]["x"] == "{c.__class__}{c[0]}"


def test_koppel_met_mapping_en_normaliseren(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps([{"naam": "Beperking ", "id": "u1"}, {"naam": "Groen", "id": "u2"}]), encoding="utf-8")
    ctx = {"usecase_map": tmp_path}
    stap = {"koppel": {"sleutel": "ind", "op": "naam", "bron": {"adapter": "usecase-bestand", "pad": "m.json"},
                       "velden": {"id": "uuid"}, "verplicht": True, "reden": "niet-gevonden", "normaliseer": True}}
    rijen, rapport = bewerk([stap], [{"ind": "beperking"}, {"ind": "groen"}, {"ind": "onbekend"}], ctx=ctx)
    assert [r["uuid"] for r in rijen] == ["u1", "u2"] and rapport == {"niet-gevonden": 1}


def test_koppel_bewerkt_eerst_de_bron(tmp_path):
    """swf-initialisatie: alleen codes die de installatie kent (bron eerst gefilterd, zoals `binnen`)."""
    (tmp_path / "b.json").write_text(json.dumps([{"code": "BU1", "pv": "PV21"}, {"code": "BU2", "pv": "PV22"}]),
                                     encoding="utf-8")
    stap = {"koppel": {"sleutel": "gebied", "op": "code", "bron": {"adapter": "usecase-bestand", "pad": "b.json"},
                       "bewerkingen": [{"filter": {"veld": "pv", "gelijk": "PV21"}}], "velden": {"code": "_bekend"}}}
    rijen, rapport = bewerk([stap, {"afwijzen": {"veld": "_bekend", "leeg": True, "reden": "gebied-onbekend"}}],
                            [{"gebied": "BU1"}, {"gebied": "BU2"}, {"gebied": "BU3"}], ctx={"usecase_map": tmp_path})
    assert [r["gebied"] for r in rijen] == ["BU1"] and rapport == {"gebied-onbekend": 2}


def test_ontdubbel_houdt_de_voorkeur_en_laat_de_rest_vervallen():
    """A4 (#222): dubbele naam, andere UUID: de voorkeur blijft, de rest krijgt status B en '(vervallen)'."""
    stap = {"ontdubbel": {"veld": "naam", "sleutel": "uuid", "normaliseer": True,
                          "houd": {"Waterdiepte op straat": "f6eafa70", "Werkzamen": "7fd17589-46b6-460a-a1f6-ef421517ccb3"},
                          "zet": {"status": "B"}, "achtervoegsel": " (vervallen)", "reden": "dubbele-naam"}}
    rijen = [
        {"uuid": "c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3", "naam": "Waterdiepte op straat", "status": "C"},
        {"uuid": "f6eafa70-9383-4de6-bd2a-e47309843437", "naam": "Waterdiepte op straat", "status": "O"},
        {"uuid": "ca06d8ad-6430-4f4d-bb32-7b406d26ecc8", "naam": "werkzamen ", "status": "O"},
        {"uuid": "7fd17589-46b6-460a-a1f6-ef421517ccb3", "naam": "Werkzamen", "status": "O"},
        {"uuid": "u5", "naam": "Uniek", "status": "O"},
        {"uuid": "u6", "naam": "Dubbel zonder voorkeur", "status": "O"},
        {"uuid": "u7", "naam": "Dubbel zonder voorkeur", "status": "O"},
    ]
    uit, rapport = bewerk([stap], rijen)
    assert [(r["naam"], r["status"]) for r in uit] == [
        ("Waterdiepte op straat (vervallen)", "B"), ("Waterdiepte op straat", "O"),
        ("werkzamen  (vervallen)", "B"), ("Werkzamen", "O"), ("Uniek", "O"),
        ("Dubbel zonder voorkeur", "O"), ("Dubbel zonder voorkeur", "O")]
    assert [r["uuid"] for r in uit] == [r["uuid"] for r in rijen], "UUID's blijven gelijk"
    assert rapport == {"dubbele-naam": 2, "dubbele-naam-zonder-voorkeur": 2}


def test_ontdubbel_voorkeur_die_niet_bestaat_of_niet_uniek_is():
    stap = {"ontdubbel": {"veld": "naam", "sleutel": "uuid", "houd": {"A": "x"}, "zet": {"status": "B"}}}
    rijen = [{"uuid": "a1", "naam": "A"}, {"uuid": "a2", "naam": "A"}, {"uuid": "a1", "naam": "a"}]
    uit, rapport = bewerk([stap], rijen)
    assert uit == rijen and rapport == {"dubbel-zonder-voorkeur": 2}  # zonder normaliseer is 'a' een andere naam
    stap["ontdubbel"]["houd"] = {"A": "a"}  # begin past op a1 én a2: geen keuze
    assert bewerk([stap], rijen)[1] == {"dubbel-zonder-voorkeur": 2}
    stap["ontdubbel"]["houd"] = {"A": "a2"}
    uit, rapport = bewerk([stap], rijen)
    assert [r.get("status") for r in uit] == ["B", None, None] and uit[0]["naam"] == "A" and rapport == {"dubbel": 1}


def test_ontdubbel_voorkeurslijst_swf_definities_is_volledig_en_gelijk():
    """De voorkeurslijst is data in de use case (geen code); swf-definities en swf-adapter-fme houden dezelfde aan."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    lijsten = []
    for uc in ("swf-definities", "swf-adapter-fme"):
        d = json.loads((root / "usecases" / uc / "datasets" / "swf-monitor-definities.json").read_text(encoding="utf-8"))
        stap = next(b for b in d["bewerkingen"] if b.get("id") == "dubbele-naam")
        lijsten.append(stap["ontdubbel"]["houd"])
        ids = [b.get("id") for b in d["bewerkingen"]]
        # O → C vóór A → O (anders wordt A → O → C); waterdiepte-actief na de statusvertaling (#341)
        assert ids.index("status-onderzoek") < ids.index("status-a") < ids.index("dubbele-naam") < ids.index("waterdiepte-actief")
    assert lijsten[0] == lijsten[1] == {"Waterdiepte op straat": "c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3",
                                        "Werkzamen": "7fd17589-46b6-460a-a1f6-ef421517ccb3"}


def test_zet_alleen_in_regels_die_voldoen():
    stap = {"zet": {"als": {"veld": "uuid", "gelijk": "c4"}, "velden": {"status": "O"}, "reden": "waterdiepte-actief"}}
    uit, rapport = bewerk([stap], [{"uuid": "c4", "status": "C"}, {"uuid": "f6", "status": "C"}])
    assert [r["status"] for r in uit] == ["O", "C"] and rapport == {"waterdiepte-actief": 1}
    assert bewerk([{"zet": {"als": {"veld": "x", "leeg": True}, "velden": {"y": 1}}}], [{"x": ""}])[1] == {"gezet": 1}


def test_swf_definities_statussen_en_waterdiepte():
    """Besluit #341: A → O (openbaar), O (Onderzoek) → C (intern), C blijft C; Waterdiepte op straat houdt c4e1b3bb… (O)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    d = json.loads((root / "usecases" / "swf-definities" / "datasets" / "swf-monitor-definities.json").read_text(encoding="utf-8"))
    c4, f6 = "c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3", "f6eafa70-9383-4de6-bd2a-e47309843437"
    rijen = [{"id": c4, "naam": "Waterdiepte op straat", "status": "C"},
             {"id": f6, "naam": "Waterdiepte op straat", "status": "A"},
             {"id": "u1", "naam": "Actueel", "status": "A"}, {"id": "u2", "naam": "Onderzoek", "status": "O"},
             {"id": "u3", "naam": "Concept", "status": "C"}, {"id": "u4", "naam": "Buiten gebruik", "status": "B"}]
    stappen = [b for b in d["bewerkingen"] if b.get("tabel") == "indicatoren" and naam_van(b) != "iso_datumtijd"]
    uit, rapport = voer_uit({"indicatoren": rijen}, stappen)
    assert [(r["naam"], r["status"]) for r in uit["indicatoren"]] == [
        ("Waterdiepte op straat", "O"), ("Waterdiepte op straat (vervallen)", "B"), ("Actueel", "O"),
        ("Onderzoek", "C"), ("Concept", "C"), ("Buiten gebruik", "B")]
    assert rapport["status: O → C"] == 1 and rapport["waterdiepte-actief"] == 1 and rapport["dubbele-naam"] == 1


def test_snake_case():
    assert snake("KL_PROJECTOMSCHRIJVING") == "kl_projectomschrijving"
    assert snake("Extra onderdeel") == "extra_onderdeel"
    assert snake("aantalInwoners65Jaar") == "aantal_inwoners65_jaar"
    assert snake("2e veld") == "v_2e_veld"
    assert len(snake("x" * 100)) == 63


def test_een_bewerking_per_stap_en_alleen_bekende():
    with pytest.raises(BewerkingFout):
        naam_van({"hernoem": {}, "behoud": []})
    with pytest.raises(BewerkingFout):
        naam_van({"eval": "__import__('os')"})
    assert naam_van({"id": "x", "tabel": "t", "omschrijving": "...", "filter": {}}) == "filter"


def test_alleen_op_de_genoemde_tabel():
    t, _ = voer_uit({"a": [{"x": 1}], "b": [{"x": 1}]}, [{"tabel": "a", "constant": {"y": 2}}])
    assert t == {"a": [{"x": 1, "y": 2}], "b": [{"x": 1}]}


def test_geometrie_bewerkingen():
    shapely = pytest.importorskip("shapely")
    from shapely.geometry import LineString, Point, Polygon, box
    vlinder = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])  # ongeldig (zelfdoorsnijdend)
    rijen, rapport = bewerk([{"multipolygon": True}], [{"geometry": vlinder}, {"geometry": box(0, 0, 1, 1)},
                                                       {"geometry": LineString([(0, 0), (1, 1)])}, {"geometry": None}])
    assert [r["geometry"].geom_type for r in rijen] == ["MultiPolygon", "MultiPolygon"]
    assert all(r["geometry"].is_valid for r in rijen)
    assert rapport == {"gerepareerd": 1, "geometrie-geen-vlak": 1, "geometrie-leeg": 1}
    rijen, rapport = bewerk([{"geometrietype": ["Point"]}], [{"geometry": Point(0, 0)}, {"geometry": box(0, 0, 1, 1)}])
    assert len(rijen) == 1 and rapport == {"ander geometrietype": 1}
    assert shapely


def test_binnen_en_splits_op(tmp_path):
    pytest.importorskip("shapely")
    from shapely.geometry import box, mapping
    gebied = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
              "features": [{"type": "Feature", "properties": {}, "geometry": mapping(box(0, 0, 10, 10))}]}
    (tmp_path / "kom.json").write_text(json.dumps(gebied), encoding="utf-8")
    bron = {"adapter": "usecase-bestand", "pad": "kom.json"}
    ctx = {"usecase_map": tmp_path}
    rijen, rapport = bewerk([{"binnen": {"bron": bron}}], [{"geometry": box(1, 1, 2, 2)}, {"geometry": box(20, 20, 21, 21)}], ctx=ctx)
    assert len(rijen) == 1 and rapport == {"buiten het gebied": 1}
    rijen, _ = bewerk([{"splits_op": {"bron": bron, "veld": "code", "binnen": "{c}_BBKJ", "buiten": "{c}_BBKN"}}],
                      [{"c": "BU1", "geometry": box(5, 5, 15, 15)}, {"c": "BU2", "geometry": box(1, 1, 2, 2)}], ctx=ctx)
    assert [(r["code"], round(r["geometry"].area)) for r in rijen] == [("BU1_BBKJ", 25), ("BU1_BBKN", 75), ("BU2_BBKJ", 1)]


# ---------------------------------------------------------------- schrijvers

def dataset(profiel, formaat, **levering):
    return {"id": "test-ds", "beschrijving": {"dct:title": "Test", "dct:accessRights": "x"},
            "laadprofiel": {"profiel": profiel}, "levering": {"formaat": formaat, **levering}}


def test_datapackage_waarnemingen(tmp_path):
    rijen = [{"gebied_code": "BU19000002", "gebiedstype": "g", "indicator_uuid": "u", "jaar": 2024, "waarde": 1.5, "extra": "weg"}]
    (pad,) = schrijf({"waarden": rijen}, dataset("waarnemingen", "datapackage"), tmp_path)
    with zipfile.ZipFile(pad) as z:
        assert sorted(z.namelist()) == ["datapackage.json", "dcat.jsonld", "waarnemingen.csv"]
        regels = list(csv.DictReader(io.TextIOWrapper(z.open("waarnemingen.csv"), encoding="utf-8")))
        dcat = json.loads(z.read("dcat.jsonld"))
    assert regels[0]["gebied_code"] == "BU19000002" and regels[0]["n"] == "" and "extra" not in regels[0]
    assert dcat["dct:temporal"]["dcat:startDate"]["@value"] == "2024-01-01"


def test_swf_json_waarden_per_combinatie(tmp_path):
    rijen = [{"indicator_id": "i1", "gebiedstype_id": "g1", "gebieds_id": "BU1", "waarde": 1, "begingeldigheid": "2020-01-01", "eindgeldigheid": None},
             {"indicator_id": "i1", "gebiedstype_id": "g2", "gebieds_id": "728", "waarde": 2, "begingeldigheid": "2021-01-01", "eindgeldigheid": None}]
    (map_,) = schrijf({"waarden": rijen}, dataset("waarnemingen", "swf-json", bestand="waarden"), tmp_path)
    assert sorted(p.name for p in map_.iterdir()) == ["i1_g1.json", "i1_g2.json"]


def test_levering_validatie_datapackage(tmp_path):
    pytest.importorskip("frictionless")
    from omnitwin.laden.levering import valideer_levering
    rijen = [{"gebied_code": "BU19000002", "indicator_uuid": "00000000-0000-4000-8000-000000000001", "jaar": 2024, "waarde": 1.5},
             {"gebied_code": "BU19000002", "indicator_uuid": "00000000-0000-4000-8000-000000000001", "jaar": 0, "waarde": 2}]
    ds = dataset("waarnemingen", "datapackage")
    ds["laadprofiel"]["bijOntbrekendeN"] = "bron-onderdrukt"
    (pad,) = schrijf({"waarnemingen": rijen}, ds, tmp_path)
    (r,) = valideer_levering(ds, pad)
    assert not r["geldig"] and r["aantallen"]["waarnemingen"] == 2
    assert any("veld jaar" in f for f in r["fouten"])


# ---------------------------------------------------------------- cbs-statline (#236)

def test_statline_filter_regio_dimensies_en_jaren():
    from omnitwin.bronadapters.statline import odata_filter
    bron = {"gemeenten": ["1900"], "regio_prefix": ["BU", "WK"], "filter": {"SoortMisdrijf": ["1.1.1"], "Marges": "MW00000"},
            "jaren": [2024]}
    f = odata_filter(bron, {"SoortMisdrijf": {"1.1.1": "1.1.1 "}})
    assert "startswith(WijkenEnBuurten,'BU1900') or startswith(WijkenEnBuurten,'WK1900')" in f
    assert "(SoortMisdrijf eq '1.1.1 ')" in f, "de echte key met opvulspatie"
    assert "(Marges eq 'MW00000')" in f and "(Perioden eq '2024JJ00')" in f
    assert odata_filter({"gebieden": ["BU1'; x"]}, {}) == "(WijkenEnBuurten eq 'BU1''; x')", "quote ge-escaped"


def test_statline_records_uitgepakt_per_kolom():
    from omnitwin.bronadapters.statline import records
    rijen = [{"WijkenEnBuurten": "BU19000002", "Perioden": "2024JJ00", "Leeftijd": "20300 ", "A_1": 46.5, "B_2": None},
             {"WijkenEnBuurten": "BU19000002", "Perioden": "2024KW01", "Leeftijd": "20300", "A_1": 1}]
    uit = records(rijen, {"kolommen": ["A_1", "B_2"], "filter": {"Leeftijd": "20300"}})
    assert uit == [{"gebied_code": "BU19000002", "jaar": 2024, "periode": "2024JJ00", "Leeftijd": "20300",
                    "kolom": "A_1", "waarde": 46.5}], "lege waarde en geen-jaarperiode vallen weg"


class _Antwoord:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_statline_pagineert_en_cachet(tmp_path, monkeypatch):
    requests = pytest.importorskip("requests")
    url = "https://dataderden.cbs.nl/ODataFeed/odata/47018NED"
    gevraagd = []

    def get(self, u, params=None, headers=None, timeout=None):
        gevraagd.append((u, params))
        if u.endswith("/SoortMisdrijf"):
            return _Antwoord({"value": [{"Key": "1.1.1 "}, {"Key": "2.2.1 "}]})
        if "skip" in u:
            return _Antwoord({"value": [{"WijkenEnBuurten": "BU19000002", "Perioden": "2025JJ00", "SoortMisdrijf": "1.1.1 ", "M_1": 3}]})
        return _Antwoord({"value": [{"WijkenEnBuurten": "BU19000002", "Perioden": "2024JJ00", "SoortMisdrijf": "1.1.1 ", "M_1": 2}],
                          "odata.nextLink": f"{url}/TypedDataSet?$skip=10000"})
    monkeypatch.setattr(requests.Session, "get", get)
    bron = {"adapter": "cbs-statline", "url": url, "gemeenten": ["1900"], "filter": {"SoortMisdrijf": ["1.1.1"]},
            "kolommen": ["M_1"]}
    ctx = {"bronnen": {"DATA_CACHE": str(tmp_path)}}
    tab = ba.haal(bron, ctx)
    assert [(r["jaar"], r["SoortMisdrijf"], r["waarde"]) for r in tab["waarnemingen"]] == [(2024, "1.1.1", 2), (2025, "1.1.1", 3)]
    assert "SoortMisdrijf eq '1.1.1 '" in gevraagd[1][1]["$filter"]
    n = len(gevraagd)
    assert ba.haal(bron, ctx) == tab and len(gevraagd) == n, "tweede keer uit de cache"


def test_statline_weigert_onbekende_key_en_verkeerde_url(tmp_path, monkeypatch):
    requests = pytest.importorskip("requests")
    monkeypatch.setattr(requests.Session, "get", lambda self, u, **kw: _Antwoord({"value": [{"Key": "1.1.1 "}]}))
    ctx = {"bronnen": {"DATA_CACHE": str(tmp_path)}}
    with pytest.raises(ba.BronFout, match="kent"):
        ba.haal({"adapter": "cbs-statline", "url": "https://dataderden.cbs.nl/ODataFeed/odata/47018NED",
                 "filter": {"SoortMisdrijf": "9.9.9"}, "kolommen": ["M_1"]}, ctx)
    with pytest.raises(ba.BronFout, match="ODataFeed"):
        ba.haal({"adapter": "cbs-statline", "url": "https://opendata.cbs.nl/ODataApi/odata/85984NED", "kolommen": ["x"]}, ctx)
    with pytest.raises(ba.BronFout, match="niet toegestaan"):
        ba.haal({"adapter": "cbs-statline", "url": "https://voorbeeld.org/ODataFeed/odata/1", "kolommen": ["x"]}, ctx)


def test_statline_geen_netwerk_is_geen_bron(tmp_path, monkeypatch):
    requests = pytest.importorskip("requests")

    def kapot(self, u, **kw):
        raise requests.ConnectionError("geen netwerk")
    monkeypatch.setattr(requests.Session, "get", kapot)
    with pytest.raises(ba.GeenBron):
        ba.haal({"adapter": "cbs-statline", "url": "https://dataderden.cbs.nl/ODataFeed/odata/50150NED",
                 "kolommen": ["Eenzaam_25"]}, {"bronnen": {"DATA_CACHE": str(tmp_path)}})


# ---------------------------------------------------------------- wcs-zonaal (#236)

def test_zonaal_gemiddelde_per_gebied_met_nodata():
    np = pytest.importorskip("numpy")
    pytest.importorskip("shapely")
    from shapely.geometry import box

    from omnitwin.bronadapters.raster import uitsnede, zonaal
    a = np.array([[1.0, 2.0, -9999.0], [3.0, 4.0, 5.0]])  # 3 x 2 cellen van 10 m, linksboven (0, 20)
    transform = (0.0, 10.0, 20.0, -10.0)
    polys = {"links": box(0, 0, 20, 20), "rechts": box(20, 0, 30, 20), "buiten": box(100, 100, 110, 110)}
    assert zonaal(a, transform, polys) == {"links": (2.5, 4), "rechts": (5.0, 1)}
    assert zonaal(a, transform, polys, nodata_als=0)["rechts"] == (2.5, 2), "nodata telt als 0"
    assert uitsnede((101, 99, 119, 121), 10) == (80, 70, 140, 150)


def test_geotiff_georeferentie_uit_tiepoint_en_schaal():
    np = pytest.importorskip("numpy")
    PIL = pytest.importorskip("PIL.Image")
    from PIL import TiffImagePlugin

    from omnitwin.bronadapters.raster import geotiff
    im = PIL.fromarray(np.array([[1.5, 2.5]], dtype="float32"))
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[33550] = (10.0, 10.0, 0.0)
    info[33922] = (0.0, 0.0, 0.0, 155000.0, 463000.0, 0.0)
    buf = io.BytesIO()
    im.save(buf, format="TIFF", tiffinfo=info)
    a, transform = geotiff(buf.getvalue())
    assert a.tolist() == [[1.5, 2.5]] and transform == (155000.0, 10.0, 463000.0, -10.0)


def test_wcs_zonaal_controleert_bron_zonder_netwerk(tmp_path):
    with pytest.raises(ba.BronFout, match="niet toegestaan"):
        ba.haal({"adapter": "wcs-zonaal", "url": "https://voorbeeld.org/wcs", "coverage": "x",
                 "gebieden": {"bron": {"adapter": "usecase-bestand", "pad": "g.json"}}}, {})
    with pytest.raises(ba.BronFout, match="gebieden.bron"):
        ba.haal({"adapter": "wcs-zonaal", "url": "https://data.rivm.nl/geo/ank/wcs", "coverage": "x"}, {})
