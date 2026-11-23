"""Unit tests voor contrastrijke, instelbare kaartselectie- en highlightstijl (#500)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from omnitwin.routers import organisatie as org_router
from omnitwin.services import organisatie as org_service
from tests.test_thema import contrast

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "js" / "app.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
MIGRATIE_V054 = ROOT / "db" / "migraties" / "V054__organisatie_selectiestijl.sql"


class _Rij:
    def __init__(self, d):
        self._mapping = d


class _NepDb:
    def __init__(self, rij=None):
        self.rij = rij
        self.opgeslagen = None

    def execute(self, sql, params=None):
        q = str(sql)
        if "INSERT INTO public.organisatie" in q:
            self.opgeslagen = params
        return self

    def fetchone(self):
        return _Rij(self.rij) if self.rij is not None else None

    def commit(self):
        pass


def _extract_js_function(bron: str, naam: str) -> str:
    m = re.search(rf"function\s+{re.escape(naam)}\s*\(", bron)
    assert m, f"Functie {naam} niet gevonden"
    start = m.start()
    brace_start = bron.index("{", bron.index(")", m.end()))
    diepte = 0
    in_str: str | None = None
    escaped = False
    for idx in range(brace_start, len(bron)):
        ch = bron[idx]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
        elif ch == "{":
            diepte += 1
        elif ch == "}":
            diepte -= 1
            if diepte == 0:
                return bron[start : idx + 1]
    raise AssertionError(f"Geen sluitende accolade voor {naam}")


def _run_app_js(expressie: str):
    bron = APP_JS.read_text(encoding="utf-8")
    code = "\n\n".join(
        [
            _extract_js_function(bron, "hexNaarRgb"),
            _extract_js_function(bron, "normaliseerSelectieStijl"),
            f"console.log(JSON.stringify(({expressie})));",
        ]
    )
    proc = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_standaardkleur_magenta_haalt_wcag_aa_contrast_op_licht_en_donker():
    """ADR 0011 / WCAG 1.4.11: >= 3.0:1 op witte/lichte én donkere kaartondergronden."""
    standaard = org_service.SELECTIE_KLEUR_STANDAARD
    assert standaard == "#e6007e"
    for achtergrond in ("#ffffff", "#f1f5f9", "#1e293b", "#0f172a"):
        assert contrast(standaard, achtergrond) >= 3.0, f"Contrast {standaard} op {achtergrond} te laag"


def test_backend_standaarden_en_oude_rij_zonder_v054_kolommen():
    """Een bestaande rij zonder de V054-kolommen krijgt de veilige standaarden (#500)."""
    oude_rij = {
        "code": "swf",
        "naam": "Gemeente Súdwest-Fryslân",
        "gemeente_codes": ["1900"],
        "thema": "swf",
        "logos": [],
    }
    org = org_service.lees_organisatie(_NepDb(oude_rij))
    assert org["selectie_kleur"] == "#e6007e"
    assert org["selectie_lijndikte"] == 4
    assert org["selectie_lijntype"] == "halo"
    assert org["selectie_vulling"] is False


def test_put_en_export_import_validatie_selectiestijl():
    app = FastAPI()
    app.include_router(org_router.router)
    db = _NepDb(
        {
            "code": "swf",
            "naam": "Gemeente Súdwest-Fryslân",
            "gemeente_codes": ["1900"],
            "thema": "swf",
            "logos": [],
            "selectie_kleur": "#007ba3",
            "selectie_lijndikte": 6,
            "selectie_lijntype": "gestreept",
            "selectie_vulling": True,
        }
    )
    app.dependency_overrides[org_router.get_db] = lambda: db
    app.dependency_overrides[org_router.vereis_admin] = lambda: {"username": "admin", "type": "session"}
    client = TestClient(app)

    r = client.get("/api/organisatie")
    assert r.status_code == 200
    assert r.json()["selectie_kleur"] == "#007ba3"
    assert r.json()["selectie_lijndikte"] == 6
    assert r.json()["selectie_lijntype"] == "gestreept"
    assert r.json()["selectie_vulling"] is True

    # Ongeldige kleur en dikte worden geweigerd (422)
    basis = {
        "code": "swf",
        "naam": "Gemeente Súdwest-Fryslân",
        "gemeente_codes": ["1900"],
        "thema": "swf",
        "logos": [],
    }
    assert client.put("/api/organisatie", json={**basis, "selectie_kleur": "magenta"}).status_code == 422
    assert client.put("/api/organisatie", json={**basis, "selectie_lijndikte": 12}).status_code == 422
    assert client.put("/api/organisatie", json={**basis, "selectie_lijntype": "stippel"}).status_code == 422

    # Oude export zonder selectie_*-velden blijft geldig importeren
    oud_export = {"formaat": "d-omnitwin/organisatie", "versie": 1, "organisatie": basis}
    assert client.post("/api/organisatie/import", json=oud_export).status_code == 200


def test_migratie_v054_template_en_css_behoeften():
    sql = MIGRATIE_V054.read_text(encoding="utf-8")
    for kol in ("selectie_kleur", "selectie_lijndikte", "selectie_lijntype", "selectie_vulling"):
        assert kol in sql

    css = STYLES_CSS.read_text(encoding="utf-8")
    assert "--map-selection-color: #e6007e;" in css
    assert ".legenda-selectie-sample--halo" in css
    assert ".legenda-selectie-sample--gestreept" in css

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    html = env.get_template("index.html").render(
        request=None,
        organisatie={
            "selectie_kleur": "#007ba3",
            "selectie_lijndikte": 5,
            "selectie_lijntype": "gestreept",
            "selectie_vulling": True,
            "logos": [],
        },
        app_version="t",
    )
    assert 'data-selectie-kleur="#007ba3"' in html
    assert 'data-selectie-lijndikte="5"' in html
    assert 'data-selectie-lijntype="gestreept"' in html
    assert 'data-selectie-vulling="true"' in html


def test_app_js_selectiestijl_normalisatie_en_geen_hardcoded_geel_in_lagen():
    standaard = _run_app_js("normaliseerSelectieStijl({})")
    assert standaard == {
        "kleur": "#e6007e",
        "rgb": [230, 0, 126],
        "dikte": 4,
        "lijntype": "halo",
        "vulling": False,
    }

    aangepast = _run_app_js(
        "normaliseerSelectieStijl({ selectie_kleur: '#007BA3', selectie_lijndikte: 99, selectie_lijntype: 'gestreept', selectie_vulling: 'true' })"
    )
    assert aangepast == {
        "kleur": "#007ba3",
        "rgb": [0, 123, 163],
        "dikte": 8,
        "lijntype": "gestreept",
        "vulling": True,
    }

    app = APP_JS.read_text(encoding="utf-8")
    # In actieve kaartlagen mag #eab308 / #ECC94B niet meer hardcoded staan
    assert "[234, 179, 8" not in app
    assert "[236, 201, 75" not in app
    assert "selection-halo-layer" in app
    assert "selection-fill-layer-" in app
    assert "selection-overlay-layer" in app
