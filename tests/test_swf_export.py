"""
Export voor de eerste SWF-vulling (scripts/beheer/swf_export.py, use case swf-initialisatie, #222 A1).
Zonder database: de keuzes die het script maakt (welke definities al bekend zijn, toegang per laag,
Kompasprofiel in het stuurdataformaat). De export zelf draait tegen een herstelde dump (README van
de use case).
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("swf_export", ROOT / "scripts" / "beheer" / "swf_export.py")
swf_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(swf_export)


def test_bekende_definities_uit_repo_en_monitor(tmp_path):
    monitor = tmp_path / "api_backup_dump.json"
    monitor.write_text(json.dumps({"indicatoren": [{"id": "F6EAFA70-9383-4DE6-BD2A-E47309843437"}]}), encoding="utf-8")
    bekend = swf_export.bekende_definities(monitor)
    assert "f6eafa70-9383-4de6-bd2a-e47309843437" in bekend
    # stuurdata (db/stuurdata/indicatoren.csv) en het CBS-recept tellen mee
    stuur = (ROOT / "db" / "stuurdata" / "indicatoren.csv").read_text(encoding="utf-8").splitlines()[1].split(",")[0]
    assert stuur in bekend
    assert "69616648-298a-493e-8264-57b5756e6fb7" not in swf_export.bekende_definities(None)


@pytest.mark.parametrize("laag, toegang", [
    ({"naam": "GeoVisia Project Locaties"}, "intern"),
    ({"naam": "Projecten", "beschrijving": "projecten in plan"}, "intern"),
    ({"naam": "Natura 2000", "beschrijving": "beschermde natuur", "typename": "natura2000:natura2000"}, "openbaar"),
])
def test_toegang_volgens_b3(laag, toegang):
    assert swf_export.toegang(laag) == toegang


def test_kompasprofielen_in_stuurdataformaat():
    regels = [
        {"profiel": "Volledig Kompas", "classificatie": "zscore", "beschrijving": "x", "kwadrant": "K", "thema": "T",
         "onderdeel": None, "indicator_uuid": "u1", "indicator_naam": "A", "weging": 10, "is_actueel": True},
        {"profiel": "Volledig Kompas", "classificatie": "zscore", "beschrijving": "x", "kwadrant": "K", "thema": "T",
         "onderdeel": "O", "indicator_uuid": "u2", "indicator_naam": None, "weging": None, "is_actueel": False},
    ]
    (p,) = swf_export.kompasprofielen(regels)
    assert {"profiel", "classificatie", "indicatoren"} <= set(p) and p["profiel"] == "Volledig Kompas"
    assert p["indicatoren"][0] == {"kwadrant": "K", "thema": "T", "onderdeel": "", "indicator_uuid": "u1",
                                   "indicator_naam": "A", "weging": 10.0, "is_actueel": True}
    assert p["indicatoren"][1]["weging"] == 1.0 and p["indicatoren"][1]["indicator_naam"] == ""
    assert swf_export.slug(p["profiel"]) == "volledig_kompas"


def test_zonder_monitordefinities_geen_export(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SWF_DUMP_DIR", raising=False)
    assert swf_export.main(["--uit", str(tmp_path / "uit")]) == 2
    assert "definities van de monitor" in capsys.readouterr().err
