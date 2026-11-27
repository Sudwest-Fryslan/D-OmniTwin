"""Unit tests voor WMS GetFeatureInfo-inspectiemodus los van gebiedsselectie (#530)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnitwin import oidc, toegang
from omnitwin.database import get_db
from omnitwin.laden import beheer
from omnitwin.routers import externe_lagen as el_router
from omnitwin.routers.externe_lagen import ExterneKaartlaagCreate, ExterneKaartlaagUpdate

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
MIGRATIE = ROOT / "db" / "migraties" / "V056__externe_kaartlagen_info_actief.sql"
ROLLEN_SQL = ROOT / "db" / "migraties" / "R__api_rollen.sql"
SCHEMA_JSON = ROOT / "usecases" / "swf-kaartlagen" / "externe-kaartlagen.schema.json"
APP_JS = ROOT / "static" / "js" / "app.js"
INDEX_HTML = ROOT / "templates" / "index.html"


class _NepWmsDb:
    def __init__(self, rij: dict | None, toegang_waarde: str = "openbaar") -> None:
        self.rij = rij
        self.toegang_waarde = toegang_waarde
        self._result = None
        self._scalar = None

    def execute(self, sql, params=None):
        s = " ".join(str(sql).split())
        self._result = None
        self._scalar = None
        if "public.toegang_kaartlaag" in s:
            self._scalar = self.toegang_waarde if self.rij is not None else None
        elif "FROM externe_kaartlagen" in s:
            self._result = SimpleNamespace(**self.rij) if self.rij is not None else None
        else:
            raise AssertionError(f"Onverwachte SQL: {s}")
        return self

    def fetchone(self):
        return self._result

    def scalar(self):
        return self._scalar


class _BeheerCursor:
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


def _maak_client(db_obj, stand: str = toegang.ANONIEM) -> TestClient:
    app = FastAPI()
    oidc.registreer(app)
    app.include_router(el_router.router)

    def _override_db():
        yield db_obj

    app.dependency_overrides[get_db] = _override_db

    @app.middleware("http")
    async def _zet_toegang(request, call_next):
        tok = toegang.zet(stand)
        try:
            return await call_next(request)
        finally:
            toegang.herstel(tok)

    return TestClient(app)


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


def test_migratie_v056_view_schema_en_beheer_bevatten_info_actief():
    """V056, api.externe_kaartlagen, schema.json en beheer.py ondersteunen info_actief."""
    mig_sql = MIGRATIE.read_text(encoding="utf-8")
    assert "info_actief" in mig_sql
    assert "DEFAULT false" in mig_sql

    rollen_sql = ROLLEN_SQL.read_text(encoding="utf-8")
    view_match = re.search(
        r"CREATE VIEW api\.externe_kaartlagen AS\s*(SELECT .*?WHERE toegang = 'openbaar' OR public\.verzoek_mag_intern\(\));",
        rollen_sql,
        re.DOTALL,
    )
    assert view_match is not None
    assert "info_actief" in view_match.group(1)

    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    veldnamen = {f["name"]: f for f in schema["fields"]}
    assert veldnamen["info_actief"]["type"] == "boolean"

    cur = _BeheerCursor()
    res = beheer.externe_kaartlagen(
        cur,
        [
            {
                "naam": "Projectenkaart",
                "bron_type": "WMS",
                "url": "https://geo.example.org/geoserver/wms",
                "typename": "swf:projecten",
                "info_actief": "true",
                "toegang": "openbaar",
            }
        ],
    )
    assert res["toegevoegd"] == ["Projectenkaart"]
    assert cur.lagen["Projectenkaart"]["info_actief"] is True


def test_pydantic_info_actief_standaard_uit_en_opt_in():
    """info_actief staat standaard uit en kan expliciet aangezet worden."""
    standaard = ExterneKaartlaagCreate(
        naam="Luchtfoto",
        bron_type="WMS",
        url="https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0",
        typename="Actueel_orthoHR",
    )
    assert standaard.info_actief is False

    opt_in = ExterneKaartlaagCreate(
        naam="Projecten",
        bron_type="WMS",
        url="https://geo.example.org/wms",
        typename="swf:projecten",
        info_actief=True,
    )
    assert opt_in.info_actief is True

    upd = ExterneKaartlaagUpdate(info_actief=True)
    assert upd.info_actief is True


def test_feature_info_validatie_en_toegang():
    """Alleen actieve WMS-lagen met info_actief=true en geldige bbox/pixels worden toegelaten."""
    uit = _NepWmsDb(
        {
            "id": 10,
            "naam": "Luchtfoto",
            "bron_type": "WMS",
            "url": "https://geo.example.org/wms",
            "typename": "ortho",
            "srsname": "EPSG:3857",
            "versie": "1.3.0",
            "wms_stijl": None,
            "info_actief": False,
            "toegang": "openbaar",
        }
    )
    res = _maak_client(uit).get("/api/externe-lagen/10/feature-info?bbox=0,0,100,100&width=101&height=101&i=50&j=50")
    assert res.status_code == 400
    assert "niet ingeschakeld" in res.json()["detail"]

    intern = _NepWmsDb(
        {
            "id": 11,
            "naam": "Intern WMS",
            "bron_type": "WMS",
            "url": "https://geo.example.org/wms",
            "typename": "intern",
            "srsname": "EPSG:3857",
            "versie": "1.3.0",
            "wms_stijl": None,
            "info_actief": True,
            "toegang": "intern",
        },
        toegang_waarde="intern",
    )
    assert (
        _maak_client(intern, stand=toegang.ANONIEM)
        .get("/api/externe-lagen/11/feature-info?bbox=0,0,100,100")
        .status_code
        == 401
    )

    client = _maak_client(intern, stand=toegang.MET_ROL)
    assert client.get("/api/externe-lagen/11/feature-info?bbox=0,0,100,100&width=30&height=101").status_code == 400
    assert (
        client.get("/api/externe-lagen/11/feature-info?bbox=0,0,100,100&width=101&height=101&i=101&j=50").status_code
        == 400
    )
    assert client.get("/api/externe-lagen/11/feature-info?bbox=0,0,100,100&crs=EPSG:9999").status_code == 400


def test_feature_info_geojson_filtering_en_text_plain_fallback(monkeypatch):
    """JSON wordt opgeschoond (zonder geom/lege velden); non-JSON valt terug op text/plain."""
    laag = {
        "id": 12,
        "naam": "Projecten WMS",
        "bron_type": "WMS",
        "url": "https://geo.example.org/wms?token=abc",
        "typename": "swf:projecten",
        "srsname": "EPSG:3857",
        "versie": "1.3.0",
        "wms_stijl": "standaard",
        "info_actief": True,
        "toegang": "openbaar",
    }

    vastgelegde_requests = []

    def _mock_handler(req: httpx.Request) -> httpx.Response:
        vastgelegde_requests.append(dict(req.url.params))
        return httpx.Response(
            200,
            headers={"content-type": "application/json;charset=UTF-8"},
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": "proj.1",
                        "properties": {
                            "geom": "MULTIPOLYGON(...)",
                            "the_geom": "abc",
                            "naam": "Herinrichting Kade",
                            "aantal": 0,
                            "afgerond": False,
                            "leeg": "",
                            "onbekend": None,
                        },
                    }
                ],
            },
        )

    transport = httpx.MockTransport(_mock_handler)
    orig_client = el_router.httpx.AsyncClient
    monkeypatch.setattr(
        el_router.httpx,
        "AsyncClient",
        lambda **kw: orig_client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}),
    )

    res = _maak_client(_NepWmsDb(laag)).get(
        "/api/externe-lagen/12/feature-info?bbox=600000,6980000,601000,6981000&width=101&height=101&i=50&j=50"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["formaat"] == "json"
    assert len(body["features"]) == 1
    eig = {e["sleutel"]: e["waarde"] for e in body["features"][0]["eigenschappen"]}
    assert eig == {"naam": "Herinrichting Kade", "aantal": "0", "afgerond": "Nee"}
    assert vastgelegde_requests[0]["CRS"] == "EPSG:3857"
    assert vastgelegde_requests[0]["I"] == "50"
    assert vastgelegde_requests[0]["J"] == "50"
    assert vastgelegde_requests[0]["INFO_FORMAT"] == "application/json"

    # Terugval naar text/plain bij WMS 1.1.1 en ServiceException op JSON
    laag_111 = {**laag, "versie": "1.1.1"}
    vastgelegde_requests.clear()

    def _fallback_handler(req: httpx.Request) -> httpx.Response:
        vastgelegde_requests.append(dict(req.url.params))
        if req.url.params.get("INFO_FORMAT") == "application/json":
            return httpx.Response(200, headers={"content-type": "text/xml"}, text="<ServiceExceptionReport/>")
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            text="Project: Herinrichting Kade\nStatus: Uitvoering",
        )

    transport_fb = httpx.MockTransport(_fallback_handler)
    monkeypatch.setattr(
        el_router.httpx,
        "AsyncClient",
        lambda **kw: orig_client(transport=transport_fb, **{k: v for k, v in kw.items() if k != "transport"}),
    )

    res_fb = _maak_client(_NepWmsDb(laag_111)).get(
        "/api/externe-lagen/12/feature-info?bbox=600000,6980000,601000,6981000&width=101&height=101&i=50&j=50"
    )
    assert res_fb.status_code == 200
    assert res_fb.json()["formaat"] == "text"
    assert "Herinrichting Kade" in res_fb.json()["tekst"]
    assert vastgelegde_requests[1]["SRS"] == "EPSG:3857"
    assert vastgelegde_requests[1]["X"] == "50"
    assert vastgelegde_requests[1]["Y"] == "50"


def test_feature_info_weigert_html_en_te_grote_respons(monkeypatch):
    """HTML-responsen en antwoorden > 1 MB worden geweigerd (502)."""
    laag = {
        "id": 13,
        "naam": "Grote WMS",
        "bron_type": "WMS",
        "url": "https://geo.example.org/wms",
        "typename": "swf:groot",
        "srsname": "EPSG:3857",
        "versie": "1.3.0",
        "wms_stijl": None,
        "info_actief": True,
        "toegang": "openbaar",
    }

    orig_client = el_router.httpx.AsyncClient
    transport_html = httpx.MockTransport(
        lambda _req: httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>xss</h1>")
    )
    monkeypatch.setattr(
        el_router.httpx,
        "AsyncClient",
        lambda **kw: orig_client(transport=transport_html, **{k: v for k, v in kw.items() if k != "transport"}),
    )
    res_html = _maak_client(_NepWmsDb(laag)).get("/api/externe-lagen/13/feature-info?bbox=0,0,100,100")
    assert res_html.status_code == 502

    transport_groot = httpx.MockTransport(
        lambda _req: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{" + b" " * (el_router._WMS_FEATURE_INFO_MAX_BYTES + 100) + b"}",
        )
    )
    monkeypatch.setattr(
        el_router.httpx,
        "AsyncClient",
        lambda **kw: orig_client(transport=transport_groot, **{k: v for k, v in kw.items() if k != "transport"}),
    )
    res_groot = _maak_client(_NepWmsDb(laag)).get("/api/externe-lagen/13/feature-info?bbox=0,0,100,100")
    assert res_groot.status_code == 502


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_viewer_inspectie_mercator_venster_guards_en_geen_innerhtml():
    """101x101 venster werkt bij elke zoom, alle 3 click-handlers hebben de guard en geen innerHTML."""
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="wms-inspectie-balk"' in index_html
    assert 'id="wms-feature-info-paneel"' in index_html
    assert 'src="/static/js/app.js?v=21"' in index_html

    # Alle 3 selectie-lagen moeten door isWmsInspectieActief() geblokkeerd worden bij inspectie
    assert app_js.count("if (isWmsInspectieActief()) return false;") >= 3

    # Escape-handler staat in capture-fase vóór de indicator-reset
    init_fn = _extract_js_function(app_js, "initWmsInspectieUi")
    assert "capture: true" in init_fn
    assert "preventDefault()" in init_fn

    # Geen innerHTML in de nieuwe renderfunctie (XSS-preventie)
    render_fn = _extract_js_function(app_js, "renderWmsFeatureInfoResultaat")
    assert "innerHTML" not in render_fn
    assert "textContent" in render_fn

    # 101x101 venster in Node testen
    script = "\n".join(
        [
            "const window = {};",
            "const MERCATOR_MAX = 20037508.342789244;",
            _extract_js_function(app_js, "lonLatNaarMercator"),
            _extract_js_function(app_js, "berekenWmsFeatureInfoVenster"),
            "const v12 = berekenWmsFeatureInfoVenster(5.66, 53.03, 12, 101);",
            "const v15 = berekenWmsFeatureInfoVenster(5.66, 53.03, 15, 101);",
            "console.log(JSON.stringify({ v12, v15 }));",
        ]
    )
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    out = json.loads(proc.stdout)
    v12, v15 = out["v12"], out["v15"]
    assert v12["width"] == 101 and v12["height"] == 101
    assert v12["i"] == 50 and v12["j"] == 50
    b12 = [float(x) for x in v12["bbox"].split(",")]
    b15 = [float(x) for x in v15["bbox"].split(",")]
    assert b12[2] > b12[0] and b12[3] > b12[1]
    # Hogere zoom betekent kleiner venster in meters
    assert (b15[2] - b15[0]) < (b12[2] - b12[0])
