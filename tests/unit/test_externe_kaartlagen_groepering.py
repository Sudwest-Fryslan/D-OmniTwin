"""Unit tests voor groeperen, ordenen en koppelen van externe kaartlagen (#527)."""

import json
import re
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnitwin.laden import beheer
from omnitwin.routers.externe_lagen import (
    ExterneKaartlaagCreate,
    ExterneKaartlaagUpdate,
    KaartlaagVolgordeUpdate,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
MIGRATIE = ROOT / "db" / "migraties" / "V053__externe_kaartlagen_groepering.sql"
ROLLEN_SQL = ROOT / "db" / "migraties" / "R__api_rollen.sql"
SCHEMA_JSON = ROOT / "usecases" / "swf-kaartlagen" / "externe-kaartlagen.schema.json"
ROUTER_PY = ROOT / "src" / "omnitwin" / "routers" / "externe_lagen.py"
APP_JS = ROOT / "static" / "js" / "app.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"


class _BeheerCursor:
    """Minimale nep-cursor voor testen van beheer.externe_kaartlagen met nieuwe kolommen."""

    def __init__(self) -> None:
        self.lagen: dict[str, dict] = {}
        self._rij = None

    def execute(self, sql: str, params=()) -> None:
        s = " ".join(sql.split())
        self._rij = None
        if s.startswith("SELECT 1 FROM information_schema.columns"):
            self._rij = (1,)
        elif s.startswith("SELECT 1 FROM public.externe_kaartlagen"):
            self._rij = (1,) if params[0] in self.lagen else None
        elif s.startswith("INSERT INTO public.externe_kaartlagen"):
            cols = re.search(r"\((.*?)\) VALUES", s).group(1).split(", ")
            laag = dict(zip(cols, params, strict=True))
            self.lagen[laag["naam"]] = laag
        else:
            raise AssertionError(f"Onverwachte SQL: {s}")

    def fetchone(self):
        return self._rij


def _maak_pakket(tmp_path: Path, regels: list[dict]) -> Path:
    pad = tmp_path / "lagen.zip"
    velden = list(regels[0])
    csv = ",".join(velden) + "\r\n" + "".join(",".join(str(r.get(v, "")) for v in velden) + "\r\n" for r in regels)
    with zipfile.ZipFile(pad, "w") as z:
        z.writestr("datapackage.json", json.dumps({"resources": [{"name": "lagen", "path": "lagen.csv"}]}))
        z.writestr("lagen.csv", csv)
    return pad


def test_migratie_view_en_usecase_schema_bevatten_groepering_kolommen():
    """V053, api.externe_kaartlagen en externe-kaartlagen.schema.json bevatten de #527 velden."""
    mig_sql = MIGRATIE.read_text(encoding="utf-8")
    for kol in ("groep_naam", "groep_volgorde", "kompas_thema_naam", "gekoppelde_indicatoren"):
        assert kol in mig_sql
    assert "idx_externe_kaartlagen_groep_volgorde" in mig_sql

    rollen_sql = ROLLEN_SQL.read_text(encoding="utf-8")
    view_match = re.search(
        r"CREATE VIEW api\.externe_kaartlagen AS\s*(SELECT .*?WHERE toegang = 'openbaar' OR public\.verzoek_mag_intern\(\));",
        rollen_sql,
        re.DOTALL,
    )
    assert view_match is not None
    view_sql = view_match.group(1)
    for kol in ("groep_naam", "groep_volgorde", "kompas_thema_naam", "gekoppelde_indicatoren"):
        assert kol in view_sql

    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    veldnamen = {f["name"]: f for f in schema["fields"]}
    assert veldnamen["groep_naam"]["type"] == "string"
    assert veldnamen["groep_volgorde"]["type"] == "integer"
    assert veldnamen["kompas_thema_naam"]["type"] == "string"
    assert veldnamen["gekoppelde_indicatoren"]["type"] == "array"


def test_pydantic_modellen_en_route_volgorde():
    """Pydantic valideert groep/thema/UUID's en vaste routes staan vóór /{laag_id}."""
    u1 = "11111111-1111-1111-1111-111111111111"
    laag = ExterneKaartlaagCreate(
        naam="Groenkaart",
        url="https://example.org/wfs",
        groep_naam="   ",
        groep_volgorde=10,
        kompas_thema_naam="  Klimaat  ",
        gekoppelde_indicatoren=[u1],
    )
    assert laag.groep_naam is None
    assert laag.kompas_thema_naam == "Klimaat"
    assert laag.gekoppelde_indicatoren == [uuid.UUID(u1)]

    with pytest.raises(ValidationError):
        ExterneKaartlaagCreate(
            naam="Fout",
            url="https://example.org/wfs",
            gekoppelde_indicatoren=["geen-uuid"],
        )

    with pytest.raises(ValidationError):
        ExterneKaartlaagCreate(
            naam="Te lang",
            url="https://example.org/wfs",
            groep_naam="x" * 121,
        )

    wissen = ExterneKaartlaagUpdate(groep_naam="", kompas_thema_naam=None, gekoppelde_indicatoren=[])
    assert {"groep_naam", "kompas_thema_naam", "gekoppelde_indicatoren"} <= wissen.model_fields_set
    assert wissen.groep_naam is None
    assert wissen.gekoppelde_indicatoren == []

    bulk = KaartlaagVolgordeUpdate(items=[{"id": 1, "volgorde": 0, "groep_volgorde": 10}])
    assert bulk.items[0].groep_volgorde == 10

    router_txt = ROUTER_PY.read_text(encoding="utf-8")
    assert router_txt.index('@admin_router.get("/koppelopties")') < router_txt.index('@admin_router.put("/{laag_id}")')
    assert router_txt.index('@admin_router.put("/volgorde")') < router_txt.index('@admin_router.put("/{laag_id}")')


def test_beheer_laden_met_en_zonder_nieuwe_velden(tmp_path):
    """beheer.externe_kaartlagen ondersteunt nieuwe velden (incl. ;- en JSON-UUID-lijsten) en laat lege weg."""
    u1 = "11111111-1111-1111-1111-111111111111"
    u2 = "22222222-2222-2222-2222-222222222222"
    basis = {
        "beschrijving": "",
        "laag_type": "selectie",
        "bron_type": "WFS",
        "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
        "typename": "natura2000:natura2000",
        "srsname": "EPSG:28992",
        "versie": "2.0.0",
        "filter_type": "provincie",
        "filter_waarde": "Fryslân",
        "koppel_veld": "",
        "kleur_lijn": "#059669",
        "kleur_fill": "#34ef99",
        "opacity": "0.3",
        "actief": "True",
        "volgorde": "2",
        "toegang": "openbaar",
    }
    cur = _BeheerCursor()
    regels = [
        dict(
            basis,
            naam="Met koppeling",
            groep_naam="Natuur & Klimaat",
            groep_volgorde="10",
            kompas_thema_naam="Klimaat",
            gekoppelde_indicatoren=f"{u1}; {u2}",
        ),
        dict(
            basis,
            naam="Met JSON lijst",
            groep_naam="",
            groep_volgorde="",
            kompas_thema_naam="Wonen",
            gekoppelde_indicatoren=json.dumps([u2]),
        ),
    ]
    # Test ook directe aanroep (zonder CSV-komma's in JSON-array) en via CSV-pakket voor ;-notatie
    uit_csv = beheer.externe_kaartlagen(cur, beheer.lees_resource(_maak_pakket(tmp_path, [regels[0]])))
    assert uit_csv["toegevoegd"] == ["Met koppeling"]
    opgeslagen = cur.lagen["Met koppeling"]
    assert opgeslagen["groep_naam"] == "Natuur & Klimaat"
    assert opgeslagen["groep_volgorde"] == 10
    assert opgeslagen["kompas_thema_naam"] == "Klimaat"
    assert opgeslagen["gekoppelde_indicatoren"] == [u1, u2]

    cur2 = _BeheerCursor()
    uit_json = beheer.externe_kaartlagen(cur2, [regels[1], dict(basis, naam="Zonder nieuwe velden")])
    assert uit_json["toegevoegd"] == ["Met JSON lijst", "Zonder nieuwe velden"]
    assert cur2.lagen["Met JSON lijst"]["kompas_thema_naam"] == "Wonen"
    assert cur2.lagen["Met JSON lijst"]["gekoppelde_indicatoren"] == [u2]
    assert "groep_naam" not in cur2.lagen["Zonder nieuwe velden"]
    assert "gekoppelde_indicatoren" not in cur2.lagen["Zonder nieuwe velden"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_viewer_groepeer_externe_kaartlagen_en_css():
    """Node-evaluatie van groepeerExterneKaartlagen en controle op viewer-groepering + CSS."""
    js = APP_JS.read_text(encoding="utf-8")
    css = STYLES_CSS.read_text(encoding="utf-8")

    assert "aria-expanded" in js
    assert "externe-groep-header" in js
    assert ".externe-lagen-groep" in css
    assert '.externe-groep-header[aria-expanded="false"]' in css

    match = re.search(
        r"(function groepeerExterneKaartlagen\(lagen\).*?window\.groepeerExterneKaartlagen = groepeerExterneKaartlagen;)",
        js,
        re.DOTALL,
    )
    assert match is not None

    script = f"""
const window = {{}};
{match.group(1)}
const groepen = groepeerExterneKaartlagen([
  {{ id: 1, naam: 'Zonder thema', volgorde: 0, groep_volgorde: 0 }},
  {{ id: 2, naam: 'Woonplaatsen', groep_naam: 'Gebiedsindelingen', groep_volgorde: 20, volgorde: 5 }},
  {{ id: 3, naam: 'Natura 2000', kompas_thema_naam: 'Klimaat', groep_volgorde: 10, volgorde: 20 }},
  {{ id: 4, naam: 'Groenstroken', kompas_thema_naam: 'Klimaat', groep_volgorde: 10, volgorde: 5 }},
]);
console.log(JSON.stringify(groepen.map(g => ({{ naam: g.naam, lagen: g.lagen.map(l => l.naam) }}))));
"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)
    assert res == [
        {"naam": "Klimaat", "lagen": ["Groenstroken", "Natura 2000"]},
        {"naam": "Gebiedsindelingen", "lagen": ["Woonplaatsen"]},
        {"naam": "Overige kaartlagen", "lagen": ["Zonder thema"]},
    ]
