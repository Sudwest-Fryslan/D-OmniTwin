"""
Unit tests laadstraat van de laad-API (#205): lezen, Table Schema, profielen waarnemingen en
definities (zonder database), adapter swf-monitor-v1, opslag en catalogus.
"""

import io
import json
import zipfile

import pytest

from omnitwin.laden import adapter_swf, opslag
from omnitwin.laden import p_definities as pdef
from omnitwin.laden import p_waarnemingen as pwrn
from omnitwin.laden.basis import Afkeuring, Context
from omnitwin.laden.catalogus import catalogus, is_publiek
from omnitwin.laden.lezen import Onleesbaar, lees
from omnitwin.laden.tabelschema import Ongeldig, Tabel, converteer, laad_schema

pytestmark = pytest.mark.unit

IND = "00000000-0000-4000-8000-000000000001"
KOP = "gebied_code,gebiedstype,indicator_uuid,jaar,peildatum,scenario,waarde,n,kwaliteit,bron,opmerking"


def ctx(**lp):
    return Context(levering={"id": "11111111-1111-4111-8111-111111111111", "alleen_valideren": False},
                   dataset={"id": "test-waarden", "profiel": lp.get("profiel", "waarnemingen"),
                            "laadprofiel": {"profiel": "waarnemingen", **lp}, "beschrijving": {}})


def csv_bestand(tmp_path, regels, naam="w.csv"):
    p = tmp_path / naam
    p.write_text("\n".join([KOP, *regels]) + "\n", encoding="utf-8")
    return p


# ── Table Schema ─────────────────────────────────────────────────────────────

def test_converteer_typen():
    assert converteer("12", {"type": "integer"}) == 12
    assert converteer(2025.0, {"type": "integer"}) == 2025
    with pytest.raises(Ongeldig):
        converteer("12.5", {"type": "integer"})
    assert converteer("1.5", {"type": "number"}) == "1.5"
    with pytest.raises(Ongeldig):
        converteer("abc", {"type": "number"})
    with pytest.raises(Ongeldig):
        converteer("nan", {"type": "number"})
    assert converteer("True", {"type": "boolean"}) is True
    assert converteer("2025-07-01", {"type": "date"}).isoformat() == "2025-07-01"
    assert converteer("2024-11-20 00:00", {"type": "datetime"}).isoformat() == "2024-11-20T00:00:00"
    assert converteer(IND.upper(), {"type": "string", "format": "uuid"}) == IND
    with pytest.raises(Ongeldig):
        converteer("geen-uuid", {"type": "string", "format": "uuid"})
    assert converteer("", {"type": "integer"}) is None


def test_tabel_constraints_en_kop():
    t = Tabel(laad_schema("waarnemingen"), "waarnemingen")
    assert t.controleer_kop(KOP.split(",")) == []
    fouten = t.controleer_kop(["gebied_code", "extra"])
    assert {f.code for f in fouten} == {"schema-ongeldig"}
    r, f = t.rij({"gebied_code": "BU1", "indicator_uuid": IND, "jaar": "1800", "waarde": "1", "kwaliteit": "slecht"}, 3)
    assert {(x.veld, x.regel) for x in f} == {("jaar", 3), ("kwaliteit", 3)}
    assert all("1800" not in x.melding and "slecht" not in x.melding for x in f), "geen brondata in fouten"


# ── lezen ────────────────────────────────────────────────────────────────────

def test_lees_csv_en_regelnummers(tmp_path):
    b = lees(csv_bestand(tmp_path, ["BU1,,%s,2025,,,1,20,,," % IND]), "text/csv", "waarnemingen", 10**6)
    assert b.resources["waarnemingen"].kop == KOP.split(",")
    assert b.resources["waarnemingen"].regels[0]["gebied_code"] == "BU1"


def test_lees_zip_met_dcat(tmp_path):
    p = tmp_path / "l.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": "waarnemingen", "path": "w.csv"}]}))
        z.writestr("w.csv", KOP + "\n")
        z.writestr("dcat.jsonld", json.dumps({"dct:title": "t"}))
    b = lees(p, "application/zip; charset=binary", None, 10**6)
    assert b.dcat == {"dct:title": "t"} and "waarnemingen" in b.resources


@pytest.mark.parametrize("inhoud,mt", [(b"geen zip", "application/zip"), (b"{", "application/json"),
                                        (b"", "text/csv"), (b"42", "application/json")])
def test_onleesbaar(tmp_path, inhoud, mt):
    p = tmp_path / "x"
    p.write_bytes(inhoud)
    with pytest.raises(Onleesbaar):
        lees(p, mt, "waarnemingen", 10**6)


def test_zip_zonder_datapackage_en_pad_buiten_de_zip(tmp_path):
    p = tmp_path / "l.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": "w", "path": "../w.csv"}]}))
    with pytest.raises(Onleesbaar):
        lees(p, "application/zip", None, 10**6)


# ── profiel waarnemingen ─────────────────────────────────────────────────────

def test_waarnemingen_n_drempel_jaar_en_dubbel(tmp_path):
    regels = [
        f"BU1,,{IND},2025,,,1.5,148,definitief,,",       # gemeten
        f"BU2,,{IND},2025,,,1.5,7,definitief,,",         # onder drempel → onderdrukt
        f"BU3,,{IND},2025,,current,1.5,,,,",             # n ontbreekt → bron-onderdrukt
        f"BU4,,{IND},,,,1.5,20,,,",                      # jaar én peildatum leeg
        f"BU1,,{IND},2025,,current,2,30,,,",             # dubbel met regel 1 (scenario leeg = current)
    ]
    b = lees(csv_bestand(tmp_path, regels), "text/csv", "waarnemingen", 10**6)
    staging, fouten, a = pwrn.controleer(b, ctx(minimumN=10, bijOntbrekendeN="bron-onderdrukt"), {})
    codes = {(f.code, f.regel) for f in fouten.lijst}
    assert codes == {("jaar-ongeldig", 4), ("dubbele-sleutel", 5)}
    assert a["gelezen"] == 5 and a["fout"] == 2 and a["onderdrukt"] == 1 and a["bronOnderdrukt"] == 1
    assert [s[10] for s in staging] == ["gemeten", "onderdrukt", "bron-onderdrukt"]


def test_waarnemingen_n_per_indicator_en_afkeuren(tmp_path):
    b = lees(csv_bestand(tmp_path, [f"BU1,,{IND},2025,,,1,20,,,", f"BU2,,{IND},2025,,,1,,,,"]),
             "text/csv", "waarnemingen", 10**6)
    _, fouten, _ = pwrn.controleer(b, ctx(minimumNPerIndicator={IND: 25}, bijNOnderDrempel="afkeuren"), {})
    assert {(f.code, f.regel) for f in fouten.lijst} == {("n-onder-drempel", 1), ("n-ontbreekt", 2)}


def test_waarnemingen_kolom_ontbreekt_is_afkeuring(tmp_path):
    p = tmp_path / "w.csv"
    p.write_text("gebied_code,indicator_uuid,jaar,waarde\nBU1,%s,2025,1\n" % IND, encoding="utf-8")
    with pytest.raises(Afkeuring) as e:
        pwrn.controleer(lees(p, "text/csv", "waarnemingen", 10**6), ctx(), {})
    assert e.value.fouten.lijst[0].code == "schema-ongeldig"


def test_waarnemingen_json_zonder_kop(tmp_path):
    p = tmp_path / "w.json"
    p.write_text(json.dumps([{"gebied_code": "BU1", "indicator_uuid": IND, "jaar": 2025, "waarde": 1.2, "n": 50}]))
    staging, fouten, a = pwrn.controleer(lees(p, "application/json", "waarnemingen", 10**6), ctx(), {})
    assert not fouten and a["geldig"] == 1 and staging[0][7] == "current"


# ── voorrang bij overlap: bronpeildatum (A6, #222) ──────────────────────────

def test_bronpeildatum_volgorde_modified_issued_ontvangst():
    import datetime as dt
    ontvangen = dt.datetime(2026, 10, 3, 23, 30, tzinfo=dt.timezone(dt.timedelta(hours=-2)))  # 4 okt UTC
    vandaag = dt.date(2026, 10, 4)
    assert pwrn.bronpeildatum({"dct:modified": "2025-06-01", "dct:issued": "2024-01-01"}, ontvangen, vandaag) == (
        dt.date(2025, 6, 1), "dct:modified")
    assert pwrn.bronpeildatum({"dct:issued": {"@value": "2024-01-01", "@type": "xsd:date"}}, ontvangen, vandaag) == (
        dt.date(2024, 1, 1), "dct:issued")
    assert pwrn.bronpeildatum({"dct:modified": "2025-06-01T10:00:00Z"}, ontvangen, vandaag)[0] == dt.date(2025, 6, 1)
    assert pwrn.bronpeildatum({"dct:modified": ""}, ontvangen, vandaag) == (dt.date(2026, 10, 4), "ontvangst")
    assert pwrn.bronpeildatum(None, ontvangen, vandaag) == (dt.date(2026, 10, 4), "ontvangst")
    assert pwrn.bronpeildatum(None, None, vandaag) == (vandaag, "ontvangst")


@pytest.mark.parametrize("dcat", [{"dct:modified": "gisteren"}, {"dct:issued": 2025},
                                  {"dct:modified": "2099-01-01"}])
def test_bronpeildatum_ongeldig_of_in_de_toekomst_keurt_af(dcat):
    import datetime as dt
    with pytest.raises(Afkeuring) as e:
        pwrn.bronpeildatum(dcat, None, dt.date(2026, 10, 4))
    f = e.value.fouten.lijst[0]
    assert f.code == "schema-ongeldig" and f.resource == "dcat"


def test_controleer_legt_bronpeildatum_vast(tmp_path):
    import datetime as dt
    p = tmp_path / "l.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": "waarnemingen", "path": "w.csv"}]}))
        z.writestr("w.csv", f"{KOP}\nBU1,,{IND},2025,,,1,20,,,\n")
        z.writestr("dcat.jsonld", json.dumps({"dct:modified": "2025-03-15"}))
    c = ctx()
    _, fouten, a = pwrn.controleer(lees(p, "application/zip", "waarnemingen", 10**6), c, {})
    assert not fouten and a["bronpeildatum"] == "2025-03-15" and a["bronpeildatumUit"] == "dct:modified"
    assert c.extra["bronpeildatum"] == dt.date(2025, 3, 15)
    # zonder dcat: datum van ontvangst
    c = ctx()
    c.levering["ontvangen_op"] = dt.datetime(2026, 1, 2, 12, tzinfo=dt.timezone.utc)
    _, _, a = pwrn.controleer(lees(csv_bestand(tmp_path, [f"BU1,,{IND},2025,,,1,20,,,"]), "text/csv",
                                   "waarnemingen", 10**6), c, {})
    assert (a["bronpeildatum"], a["bronpeildatumUit"]) == ("2026-01-02", "ontvangst")


def test_voorrangsregel_staat_in_een_functie_in_v036():
    """De regel staat op één plek (laden.herbouw_gebied_data, V036): nieuwste bronpeildatum, dan laatst
    aangeleverd; de rest als andere_bronnen. Geen vaste voorkeursdataset meer (LADEN_VOORRANG)."""
    from pathlib import Path
    import re
    root = Path(__file__).resolve().parents[2]
    sql = (root / "db" / "migraties" / "V036__voorrang_bronpeildatum.sql").read_text(encoding="utf-8")
    volgorde = re.search(r"ORDER BY (w\.bronpeildatum DESC, l\.ontvangen_op DESC, [^)]*)\)", sql)
    assert volgorde and volgorde.group(1).split(",")[0] == "w.bronpeildatum DESC"
    assert "'andere_bronnen'" in sql and "WHERE a.rang = 1" in sql
    assert "laden.herbouw_gebied_data()" in (root / "src" / "omnitwin" / "laden" / "p_waarnemingen.py").read_text(
        encoding="utf-8")
    from omnitwin import config
    assert "LADEN_VOORRANG" not in Path(config.__file__).read_text(encoding="utf-8")


def test_vervangbereik_onbekend_veld():
    with pytest.raises(Afkeuring):
        pwrn._bereik_voorwaarde({"vervangBereik": ["waarde"]})
    assert "gebiedstype_id" in pwrn._bereik_voorwaarde({"vervangBereik": ["indicator_uuid", "gebiedstype"]})
    assert pwrn._bereik_voorwaarde({}) == ""


def test_plausibiliteit():
    pwrn.plausibel({"plausibiliteit": {"maxDalingProcent": 20}}, 80, 100)
    with pytest.raises(Afkeuring):
        pwrn.plausibel({"plausibiliteit": {"maxDalingProcent": 20}}, 79, 100)
    with pytest.raises(Afkeuring):
        pwrn.plausibel({"plausibiliteit": {"minRegels": 5}}, 4, 0)


# ── adapter swf-monitor-v1 ───────────────────────────────────────────────────

def test_adapter_waarden(tmp_path):
    gt = "29fc9f28-89d9-488b-bf68-2ed176187b21"
    data = [{"indicator_id": IND, "gebiedstype_id": gt, "gebieds_id": 728, "waarde": 1.5, "begingeldigheid": "2025-01-01"},
            {"indicator_id": IND, "gebiedstype_id": gt, "gebieds_id": "729", "waarde": 2, "begingeldigheid": "2025-06-30",
             "eindgeldigheid": "2025-12-31"},
            {"indicator_id": IND, "gebiedstype_id": gt, "gebieds_id": "730", "waarde": 2, "begingeldigheid": "0000-01-01"}]
    p = tmp_path / "w.json"
    p.write_text(json.dumps(data))
    staging, fouten, a = pwrn.controleer(lees(p, "application/json", "waarnemingen", 10**6),
                                         ctx(adapter="swf-monitor-v1", bijOntbrekendeN="bron-onderdrukt"), {gt: "WS"})
    assert [(f.code, f.regel, f.resource) for f in fouten.lijst] == [("jaar-ongeldig", 3, "waarden")]
    assert [s[2] for s in staging] == ["WS728", "WS729"]
    assert staging[0][5] == 2025 and staging[1][5] is None and str(staging[1][6]) == "2025-06-30"
    assert a["eindgeldigheidGenegeerd"] == 1 and a["bronOnderdrukt"] == 2


def test_adapter_definities_status_a_afgekeurd(tmp_path):
    gt = "afba67cb-6b38-4723-9c95-102a22d5b38a"
    data = {"indicatoren": [{"id": IND, "naam": "x", "status": "A", "begingeldigheid": "2024-11-20 00:00"}],
            "gebiedstypen": [{"id": gt, "naam": "CBS buurten", "wfs": "https://example.org/wfs", "actief": True}],
            "relaties": [{"indicator_id": IND, "gebiedstype_id": gt},
                         {"indicator_id": "00000000-0000-4000-8000-000000000009", "gebiedstype_id": gt}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(data))
    c = ctx(adapter="swf-monitor-v1")
    c.dataset["laadprofiel"]["profiel"] = "definities"
    uit, fouten, a = pdef.controleer(lees(p, "application/json", None, 10**6), c)
    assert {(f.code, f.resource, f.veld) for f in fouten.lijst} == {
        ("schema-ongeldig", "indicatoren", "status"), ("indicator-onbekend", "relaties", "indicator_uuid")}
    assert uit["gebiedstypen"][0]["_meta"] == {"wfs": "https://example.org/wfs"}
    assert a["perResource"] == {"indicatoren": 1, "gebiedstypen": 1, "relaties": 2}


def test_definities_zonder_resources_afgekeurd(tmp_path):
    p = tmp_path / "l.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": "indicatoren", "path": "i.csv"}]}))
        z.writestr("i.csv", "uuid,naam\n")
    c = ctx()
    c.dataset["laadprofiel"]["profiel"] = "definities"
    with pytest.raises(Afkeuring) as e:
        pdef.controleer(lees(p, "application/zip", None, 10**6), c)
    assert e.value.fouten.lijst[0].code == "formaat-ongeldig"


# ── opslag ───────────────────────────────────────────────────────────────────

def test_opslag_limiet_sha256_en_onveranderlijk(tmp_path, monkeypatch):
    monkeypatch.setenv("LEVERINGEN_DIR", str(tmp_path))
    o = opslag.ontvang_bestand(io.BytesIO(b"abc"), 10)
    assert o.sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" and o.grootte == 3
    doel = opslag.bewaar(o, "ds", "lv1", "levering.csv")
    assert doel == tmp_path / "ds" / "lv1" / "levering.csv" and doel.read_bytes() == b"abc"
    with pytest.raises(FileExistsError):  # nooit overschrijven
        opslag.bewaar(opslag.ontvang_bestand(io.BytesIO(b"x"), 10), "ds", "lv1", "levering.csv")
    with pytest.raises(opslag.TeGroot):
        opslag.ontvang_bestand(io.BytesIO(b"x" * 11), 10)


def test_veilige_bestandsnaam():
    assert opslag.veilige_bestandsnaam("../../etc/passwd", "text/csv") == "passwd"
    assert opslag.veilige_bestandsnaam(None, "application/zip") == "levering.zip"
    assert opslag.veilige_bestandsnaam("a b?.gpkg", "application/geopackage+sqlite3") == "a_b_.gpkg"


# ── catalogus ────────────────────────────────────────────────────────────────

def test_catalogus_jsonld():
    ds = {"id": "voorbeeld", "profiel": "waarnemingen", "beschrijving": {
        "@context": "x", "@type": "dcat:Dataset", "dct:title": "T",
        "dct:accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC"}}
    c = catalogus([ds], "https://omnitwin.example.nl")
    assert c["@type"] == "dcat:Catalog"
    d = c["dcat:dataset"][0]
    assert d["@id"].endswith("/api/laden/v1/datasets/voorbeeld") and d["dct:identifier"] == "voorbeeld"
    assert d["dct:conformsTo"][0].endswith("waarnemingen.schema.json") and "@context" not in d
    assert is_publiek(ds["beschrijving"]) and not is_publiek({"dct:accessRights": {"@id": "x/RESTRICTED"}})


def test_adapter_herkenning():
    assert adapter_swf.is_waarden([{"indicator_id": 1, "gebieds_id": 2}])
    assert not adapter_swf.is_waarden([{"gebied_code": 1}])
    assert adapter_swf.is_definities({"indicatoren": [], "gebiedstypen": [], "relaties": []})
