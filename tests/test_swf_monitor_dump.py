"""
Export uit de database-dump van de huidige SWF-gebiedsmonitor (scripts/beheer/swf_monitor_dump.py, #316).
Met een fictieve mini-dump (tests/data/swf_monitor_dump/): verzonnen indicatoren, waarden en gebruikers
(`voorbeeld.gebruiker1..3`). De echte dump komt nooit in git.
"""

import csv
import importlib.util
import json
import math
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data" / "swf_monitor_dump"
spec = importlib.util.spec_from_file_location("swf_monitor_dump", ROOT / "scripts" / "beheer" / "swf_monitor_dump.py")
smd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smd)

BU, WS = "afba67cb-6b38-4723-9c95-102a22d5b38a", "29fc9f28-89d9-488b-bf68-2ed176187b21"
I1, I2, I5 = ("0e5b1c4a-1111-4aaa-8aaa-000000000001", "0e5b1c4a-2222-4bbb-8bbb-000000000002",
              "0e5b1c4a-5555-4eee-8eee-000000000005")
SUB = "0e5b1c4a-9999-4999-8999-000000000099"


@pytest.fixture(scope="module")
def tabellen():
    return smd.lees_dump(DATA / "voorbeeld_monitor.sql")


def test_lees_copy_tekstformaat(tabellen):
    assert {t: len(r) for t, r in tabellen.items()} == {
        "gebiedstype": 3, "indicator": 5, "indicator_gebiedstype": 5, "indicator_waarde": 6, "monitor": 3,
        "user_properties": 9}
    i1 = next(i for i in tabellen["indicator"] if i["id"] == I1)
    assert i1["omschrijving"] == "Omschrijving met een tab\tin de tekst" and i1["eindgeldigheid"] is None


def test_dump_zonder_tabel_is_fout(tmp_path):
    (tmp_path / "x.sql").write_text("COPY public.indicator (id, naam) FROM stdin;\na\tb\n\\.\n", encoding="utf-8")
    with pytest.raises(smd.DumpFout, match="ontbreken"):
        smd.lees_dump(tmp_path / "x.sql")


def test_custom_format_zonder_pg_restore(tmp_path, monkeypatch):
    (tmp_path / "x.dmp").write_bytes(b"PGDMP\x01\x0f")
    monkeypatch.delenv("PG_RESTORE", raising=False)
    monkeypatch.setattr(smd.shutil, "which", lambda _: None)
    with pytest.raises(smd.DumpFout, match="pg_restore"):
        smd.lees_dump(tmp_path / "x.dmp")


def test_actieve_monitor_is_de_open_versie(tabellen):
    actief = smd.actieve_monitors(tabellen["monitor"])
    assert [(m["naam"], m["volgnummer"]) for m in actief] == [("Voorbeeld basis", "2"), ("Voorbeeld klimaat", "1")]


def test_definities_in_vorm_van_de_api_export(tabellen):
    d = smd.definities(tabellen, smd.actieve_monitors(tabellen["monitor"]))
    assert set(d) == {"indicatoren", "gebiedstypen", "relaties"}
    i1, i2 = (next(i for i in d["indicatoren"] if i["id"] == u) for u in (I1, I2))
    assert i1["begingeldigheid"] == "2024-11-20 00:00" and i1["eindgeldigheid"] == "" and i1["status"] == "A"
    assert i2["eindgeldigheid"] == "2025-01-14 10:30"
    # omkeren true = lager is beter, false = hoger is beter; zonder omkeren geen score_type
    assert i1["score_type"] == "-/+" and i2["score_type"] == "+/+"
    assert not any("score_type" in i for i in d["indicatoren"] if i["naam"] == "Fictieve indicator drie")
    bbk = next(g for g in d["gebiedstypen"] if g["naam"].endswith("komgrens"))
    assert bbk == {"id": "d210c084-506b-48b4-87c9-b7d4bf422553", "naam": "CBS buurten bebouwde komgrens", "wfs": "",
                   "typenames": "", "sleutel": "", "label": "", "actief": False}
    assert len(d["relaties"]) == 5 and set(d["relaties"][0]) == {"indicator_id", "gebiedstype_id"}


def test_omkeren_tegenstrijdig_geeft_geen_score_type():
    m = {"id": "m", "naam": "m", "configuratie": json.dumps({"type": "root", "children": [
        {"type": "categorie", "text": "a", "children": [{"type": "indicator", "indicator_id": I1, "omkeren": True}]},
        {"type": "categorie", "text": "b", "children": [{"type": "indicator", "indicator_id": I1, "omkeren": False}]}]})}
    assert smd.score_types([m]) == ({}, [I1])


def test_waarden_in_vorm_van_de_api_export(tabellen):
    w = smd.waarden(tabellen)
    assert w[0] == {"indicator_id": I1, "gebiedstype_id": BU, "gebieds_id": "BU99990001", "waarde": 12.5, "jaar": 2023}
    assert [r["waarde"] for r in w][:2] == [12.5, 7] and isinstance(w[1]["waarde"], int)
    assert {r["jaar"] for r in w} >= {0, 2012}  # de use case wijst jaar 0 en oude codes af, niet het script


def test_kompasregels_met_niveaus_en_volgorde(tabellen):
    regels = smd.kompasregels(smd.actieve_monitors(tabellen["monitor"]))
    basis = [r for r in regels if r["gebiedstype_id"] == BU]
    assert [r["volgorde"] for r in basis] == [1, 2, 3, 4]
    assert basis[1] == {"monitor": "Voorbeeld basis", "monitor_id": "node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa",
                        "gebiedstype_id": BU, "weergave_type": "percentiel_waarden", "volgorde": 2,
                        "niveau1": "Kwadrant een", "niveau2": "Thema een", "niveau3": "Onderdeel een",
                        "niveau4": "Extra niveau", "indicator_uuid": I2, "indicator_naam": "Fictieve indicator twee",
                        "omkeren": "false", "labels": "ja"}
    assert basis[0]["niveau4"] == "" and basis[0]["omkeren"] == "true"
    klimaat = [r for r in regels if r["gebiedstype_id"] == WS]
    assert len(klimaat) == 1 and klimaat[0]["niveau1"] == "Hitte" and klimaat[0]["niveau2"] == ""
    assert set(regels[0]) == set(smd.KOMPAS_KOLOMMEN)


def test_labels_open_grenzen_en_omgedraaid(tabellen):
    monitors = smd.actieve_monitors(tabellen["monitor"])
    lab = smd.labels(monitors, {I2: "Fictieve indicator twee", I5: "Fictieve klimaatindicator"}, "test")
    per = {i["indicator_uuid"]: i["labels"] for i in lab["indicatoren"]}
    assert per[I2] == [["A", 0.0, 10.0], ["B", 10.0, 20.0], ["C", 20.0, 30.0], ["D", 30.0, 40.0], ["E", 40.0, None]]
    # van -100 tot -9999 (zo staat het in de monitor): oplopend en open naar beneden
    assert per[I5][0] == ["A", 50.0, None] and per[I5][4] == ["E", None, -100.0]
    assert lab["indicatoren"][0]["namen"]["A"] == "Robuust"
    # zelfde formaat als db/stuurdata/indicator_labels_*.json (load_sample.py --stap drempels)
    stuur = json.loads((ROOT / "db" / "stuurdata" / "indicator_labels_klimaatmonitor_swf.json").read_text(encoding="utf-8"))
    assert {"bron", "indicatoren"} <= set(lab) and {"indicator_uuid", "labels"} <= set(stuur["indicatoren"][0])


def test_archief_zonder_vastgelegd_door(tabellen):
    archief = smd.monitorarchief(tabellen["monitor"])
    assert len(archief) == 3 and all("vastgelegd_door" not in m for m in archief)
    assert "voorbeeld.beheerder" not in json.dumps(archief)


def test_rd_naar_wgs84():
    lon, lat = smd.rd_naar_wgs84(155000, 463000)  # Amersfoort, oorsprong van RD
    assert lon == pytest.approx(5.387206, abs=1e-6) and lat == pytest.approx(52.155174, abs=1e-6)
    lon, lat = smd.rd_naar_wgs84(233883.131, 582065.167)  # Martinitoren, Groningen (±1 m)
    assert lon == pytest.approx(6.56820, abs=1e-4) and lat == pytest.approx(53.21938, abs=1e-4)


def test_kaartpositie():
    pos = smd.kaartpositie('{"center":[155000,463000],"resolution":4.5}')
    assert pos["longitude"] == pytest.approx(5.387206) and pos["latitude"] == pytest.approx(52.155174)
    verwacht = math.log2(40075016.686 * math.cos(math.radians(pos["latitude"])) / (512 * 4.5))
    assert pos["zoom"] == pytest.approx(verwacht, abs=0.01)
    merc = smd.kaartpositie('{"center":[600000,6800000],"resolution":20}')
    assert 5.3 < merc["longitude"] < 5.5 and 51 < merc["latitude"] < 53
    assert smd.kaartpositie("geen json") is None
    assert smd.kaartpositie('{"center":[1,2],"resolution":1}') is None


def test_mapping_expliciet_geen_email(tmp_path):
    assert smd.lees_mapping(DATA / "gebruikers-mapping.csv") == {"voorbeeld.gebruiker1": SUB,
                                                                 "voorbeeld.gebruiker2": "lokaal:7"}
    (tmp_path / "m.csv").write_text("gebruikersnaam,eigenaar\nvoorbeeld.gebruiker1,iemand@voorbeeld.nl\n", encoding="utf-8")
    with pytest.raises(smd.DumpFout, match="e-mail"):
        smd.lees_mapping(tmp_path / "m.csv")
    (tmp_path / "m.csv").write_text("gebruikersnaam,eigenaar\nvoorbeeld.gebruiker1,Voorbeeld Gebruiker\n", encoding="utf-8")
    with pytest.raises(smd.DumpFout, match="sub"):
        smd.lees_mapping(tmp_path / "m.csv")


def test_voorkeuren_alleen_gekoppelde_gebruikers(tabellen):
    mapping = smd.lees_mapping(DATA / "gebruikers-mapping.csv")
    monitors = {m["id"]: m["naam"] for m in smd.actieve_monitors(tabellen["monitor"])}
    items, telling = smd.voorkeuren(tabellen["user_properties"], mapping, monitors)
    assert [i["eigenaar"] for i in items] == [SUB, "lokaal:7"]
    assert telling["gekoppeld"] == 2 and telling["niet_gekoppeld"] == 1 and telling["gebruikers"] == 3
    assert "voorbeeld.gebruiker" not in json.dumps(items) + json.dumps(telling)  # geen oude namen in de uitvoer
    een = items[0]
    assert set(een["kaartpositie"]) == {"longitude", "latitude", "zoom"}
    assert een["niet_overgenomen"] == {"monitor": "Voorbeeld basis", "actief_paneel": "Voorbeeldpaneel",
                                       "paneel_zichtbaar": True, "basislaag": "Voorbeeldkaart"}
    assert items[1]["niet_overgenomen"] == {"monitor": "Voorbeeld klimaat"}


class NepCursor:
    def __init__(self, bestaand=()):
        self.rijen, self.rowcount, self.bestaand = {}, 0, set(bestaand)

    def execute(self, sql, params):
        assert "ON CONFLICT (eigenaar) DO NOTHING" in sql
        eigenaar, positie = params
        if eigenaar in self.bestaand or eigenaar in self.rijen:
            self.rowcount = 0
        else:
            self.rijen[eigenaar] = json.loads(positie) if positie else None
            self.rowcount = 1


def test_laad_voorkeuren_vult_aan_en_overschrijft_niet():
    cur = NepCursor(bestaand={"lokaal:7"})
    items = [{"eigenaar": SUB, "kaartpositie": {"longitude": 5.6, "latitude": 53.0, "zoom": 12.3}},
             {"eigenaar": "lokaal:7", "kaartpositie": {"longitude": 5.6, "latitude": 53.0, "zoom": 12.3}},
             {"eigenaar": "voorbeeld.gebruiker3"},
             {"eigenaar": "0e5b1c4a-8888-4888-8888-000000000088", "kaartpositie": {"longitude": 500, "latitude": 1, "zoom": 1}}]
    telling = smd.laad_voorkeuren(cur, items)
    assert telling == {"toegevoegd": 2, "al_aanwezig": 1, "eigenaar_ongeldig": 1}
    assert cur.rijen[SUB] == {"longitude": 5.6, "latitude": 53.0, "zoom": 12.3}
    assert cur.rijen["0e5b1c4a-8888-4888-8888-000000000088"] is None  # ongeldige positie: alleen de eigenaar


def test_exporteer_maakt_de_bestanden(tabellen, tmp_path):
    mapping = smd.lees_mapping(DATA / "gebruikers-mapping.csv")
    s = smd.exporteer(tabellen, tmp_path, mapping, "2026-01-01")
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "definities.json", "export.json", "gebruikers-mapping.csv", "gebruikersvoorkeuren.json",
        "indicator_labels_monitor.json", "kompasprofiel_monitor.csv", "monitorconfiguraties.json", "waarden.json"]
    assert s["definities"]["status"] == {"A": 2, "B": 1, "C": 1, "O": 1}
    assert s["waarden"]["totaal"] == 6 and s["monitors"]["versies"] == 3
    assert s["gebruikersvoorkeuren"]["gekoppeld"] == 2
    export = (tmp_path / "export.json").read_text(encoding="utf-8")
    assert "voorbeeld.gebruiker" not in export and "voorbeeld.beheerder" not in export
    with open(tmp_path / "gebruikers-mapping.csv", encoding="utf-8") as f:
        sjabloon = list(csv.DictReader(f))
    assert sjabloon[2] == {"gebruikersnaam": "voorbeeld.gebruiker3", "eigenaar": ""}
    assert json.loads((tmp_path / "waarden.json").read_text(encoding="utf-8"))[0]["jaar"] == 2023


def test_main_exporteer_en_foutmelding(tmp_path, capsys):
    assert smd.main(["exporteer", "--dump", str(DATA / "voorbeeld_monitor.sql"), "--uit", str(tmp_path / "uit")]) == 0
    assert "0 van 3 gebruikers gekoppeld" in capsys.readouterr().out
    (tmp_path / "m.csv").write_text("gebruikersnaam,eigenaar\nx,iemand@voorbeeld.nl\n", encoding="utf-8")
    assert smd.main(["exporteer", "--dump", str(DATA / "voorbeeld_monitor.sql"), "--uit", str(tmp_path / "uit"),
                     "--gebruikers-mapping", str(tmp_path / "m.csv")]) == 2


def test_use_cases_lezen_de_export(tabellen, tmp_path):
    """De varianten monitor-database van de swf-* use cases maken een geldige levering uit de export."""
    from omnitwin import usecases as uc
    smd.exporteer(tabellen, tmp_path / "export", {}, None)
    ucs = uc.lees_usecases()
    bronnen = {"SWF_DB_DUMP": str(tmp_path / "export")}
    for naam, ds_id, verwacht in (("swf-definities", "swf-monitor-definities", None),
                                  ("swf-basismonitor-waarden", "swf-monitor-waarden", {"jaar-ongeldig": 1, "buurtcode-oud": 1}),
                                  ("swf-klimaatmonitor", "swf-monitor-waarden", None),
                                  ("swf-kompasprofiel", "swf-kompas-basis", {"indicator-niet-in-definities": 0}),
                                  ("swf-kompasprofiel", "swf-kompas-klimaat", None)):
        u = ucs[naam]
        ds = next(d for d in u["datasets"] if d["id"] == ds_id)
        paden, rapport = uc.maak_levering(u, ds, tmp_path / naam / ds_id, bron_env=bronnen)
        assert rapport["variant"] == "monitor-database", naam
        assert paden and paden[0].exists()
        for reden, n in (verwacht or {}).items():
            assert rapport["bewerkingen"].get(reden, 0) == n, (naam, reden)
    _, rapport = uc.maak_levering(ucs["swf-kompasprofiel"], next(
        d for d in ucs["swf-kompasprofiel"]["datasets"] if d["id"] == "swf-kompas-basis"), tmp_path / "k", bron_env=bronnen)
    assert rapport["geschreven"] == {"data": 4}
