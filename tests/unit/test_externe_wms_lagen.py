"""Unit tests voor externe WMS-lagen met serverstijl, legenda en instelbare opacity (#529)."""

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
from pydantic import ValidationError

from omnitwin import oidc, toegang
from omnitwin.database import get_db
from omnitwin.laden import beheer
from omnitwin.routers import externe_lagen as el_router
from omnitwin.routers.externe_lagen import ExterneKaartlaagCreate, ExterneKaartlaagUpdate

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
MIGRATIE = ROOT / "db" / "migraties" / "V055__externe_kaartlagen_wms.sql"
ROLLEN_SQL = ROOT / "db" / "migraties" / "R__api_rollen.sql"
SCHEMA_JSON = ROOT / "usecases" / "swf-kaartlagen" / "externe-kaartlagen.schema.json"
APP_JS = ROOT / "static" / "js" / "app.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"


class _NepWmsDb:
    """Minimale nep-sessie voor testen van WMS-proxy en features-fallback."""

    def __init__(self, rij: dict | None, toegang_waarde: str = "openbaar") -> None:
        self.rij = rij
        self.toegang_waarde = toegang_waarde
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
    """Minimale nep-cursor voor testen van beheer.externe_kaartlagen met WMS."""

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


def test_migratie_view_en_usecase_schema_bevatten_wms_velden():
    """V055, api.externe_kaartlagen en externe-kaartlagen.schema.json ondersteunen overlay en wms_stijl."""
    mig_sql = MIGRATIE.read_text(encoding="utf-8")
    assert "wms_stijl" in mig_sql
    assert "'overlay'" in mig_sql

    rollen_sql = ROLLEN_SQL.read_text(encoding="utf-8")
    view_match = re.search(
        r"CREATE VIEW api\.externe_kaartlagen AS\s*(SELECT .*?WHERE toegang = 'openbaar' OR public\.verzoek_mag_intern\(\));",
        rollen_sql,
        re.DOTALL,
    )
    assert view_match is not None
    assert "wms_stijl" in view_match.group(1)

    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    veldnamen = {f["name"]: f for f in schema["fields"]}
    assert "overlay" in veldnamen["laag_type"]["constraints"]["enum"]
    assert veldnamen["wms_stijl"]["type"] == "string"


def test_pydantic_modellen_wms_standaarden_en_validatie():
    """WMS krijgt veilige overlay-defaults en valideert wms_stijl en laag_type."""
    laag = ExterneKaartlaagCreate(
        naam="Bomen WMS",
        bron_type="WMS",
        url="https://geo.example.org/geoserver/wms",
        typename="swf:gv_bomen",
        wms_stijl="  swf_bomen  ",
    )
    assert laag.laag_type == "overlay"
    assert laag.opacity == 0.8
    assert laag.versie == "1.3.0"
    assert laag.srsname == "EPSG:3857"
    assert laag.filter_type == "alles"
    assert laag.wms_stijl == "swf_bomen"

    with pytest.raises(ValidationError):
        ExterneKaartlaagCreate(
            naam="Te lange stijl",
            bron_type="WMS",
            url="https://geo.example.org/wms",
            wms_stijl="x" * 121,
        )

    upd = ExterneKaartlaagUpdate(laag_type="overlay", wms_stijl="")
    assert upd.laag_type == "overlay"
    assert "wms_stijl" in upd.model_fields_set
    assert upd.wms_stijl is None

    with pytest.raises(ValidationError):
        ExterneKaartlaagUpdate(laag_type="onbekend")


def test_beheer_loader_ondersteunt_wms_overlay_en_stijl():
    """beheer.externe_kaartlagen slaat overlay en wms_stijl op en laat lege wms_stijl weg."""
    cur = _BeheerCursor()
    regels = [
        {
            "naam": "Waterdiepte WMS",
            "laag_type": "overlay",
            "bron_type": "WMS",
            "url": "https://geo.example.org/wms",
            "typename": "kea:waterdiepte",
            "wms_stijl": "diepte_blauw",
            "opacity": "0.75",
            "actief": "true",
            "toegang": "openbaar",
        },
        {
            "naam": "WFS zonder wms_stijl",
            "laag_type": "selectie",
            "bron_type": "WFS",
            "url": "https://service.pdok.nl/kadaster/bag/wfs/v2_0",
            "typename": "bag:woonplaats",
            "actief": "true",
            "toegang": "openbaar",
        },
    ]
    uit = beheer.externe_kaartlagen(cur, regels)
    assert uit["toegevoegd"] == ["Waterdiepte WMS", "WFS zonder wms_stijl"]
    assert cur.lagen["Waterdiepte WMS"]["laag_type"] == "overlay"
    assert cur.lagen["Waterdiepte WMS"]["wms_stijl"] == "diepte_blauw"
    assert cur.lagen["Waterdiepte WMS"]["opacity"] == 0.75
    assert "wms_stijl" not in cur.lagen["WFS zonder wms_stijl"]


def test_wms_proxy_getmap_getlegend_cache_en_features_fallback(monkeypatch):
    """WMS-proxy stuurt GetMap en GetLegendGraphic naar de geconfigureerde bron en cached de legenda."""
    el_router._wms_legend_cache.clear()
    aanroepen: list[tuple[str, dict[str, str]]] = []

    class _FakeResp:
        def __init__(self, content: bytes, ct: str = "image/png", status_code: int = 200):
            self.content = content
            self.headers = {"content-type": ct}
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "err", request=httpx.Request("GET", "https://geo.example.org"), response=self
                )

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            p = dict(params or [])
            aanroepen.append((url, p))
            if p.get("REQUEST") == "GetLegendGraphic":
                return _FakeResp(b"PNG-LEGEND", "image/png")
            return _FakeResp(b"PNG-TILE", "image/png; charset=utf-8")

    monkeypatch.setattr(el_router.httpx, "AsyncClient", _FakeClient)

    laag_rij = {
        "id": 42,
        "naam": "Bomenkaart",
        "bron_type": "WMS",
        "url": "https://geo.example.org/geoserver/wms?map=swf&REQUEST=Hack",
        "typename": "swf:gv_bomen",
        "srsname": "EPSG:3857",
        "versie": "1.3.0",
        "wms_stijl": "groen",
        "toegang": "openbaar",
    }
    client = _maak_client(_NepWmsDb(laag_rij))

    # 1. GetMap
    r_map = client.get(
        "/api/externe-lagen/42/wms?request=GetMap&bbox=500000,6900000,520000,6920000&width=256&height=256"
    )
    assert r_map.status_code == 200
    assert r_map.content == b"PNG-TILE"
    assert r_map.headers["content-type"].startswith("image/png")
    url, sent = aanroepen[-1]
    assert url == "https://geo.example.org/geoserver/wms"
    assert sent["map"] == "swf"
    assert sent["REQUEST"] == "GetMap"
    assert sent["LAYERS"] == "swf:gv_bomen"
    assert sent["STYLES"] == "groen"
    assert sent["CRS"] == "EPSG:3857"

    # 2. GetLegendGraphic + cache hit
    r_leg1 = client.get("/api/externe-lagen/42/wms?request=GetLegendGraphic")
    r_leg2 = client.get("/api/externe-lagen/42/wms?request=GetLegendGraphic")
    assert r_leg1.status_code == 200 and r_leg1.content == b"PNG-LEGEND"
    assert r_leg2.status_code == 200 and r_leg2.content == b"PNG-LEGEND"
    assert len(aanroepen) == 2  # Tweede GetLegendGraphic komt uit _wms_legend_cache

    # 3. /features fallback geeft geen 501 meer
    r_feat = client.get("/api/externe-lagen/42/features")
    assert r_feat.status_code == 200
    body = r_feat.json()
    assert body["features"] == []
    assert body["metadata"]["wms_url"] == "/api/externe-lagen/42/wms"
    assert body["metadata"]["wms_stijl"] == "groen"


def test_wms_proxy_beveiliging_validatie_en_toegang(monkeypatch):
    """Weigert ongeldige bbox/requests, SSRF-URL's, XML-fouten van WMS en anonieme toegang op interne laag."""
    el_router._wms_legend_cache.clear()

    basis = {
        "id": 7,
        "naam": "Test WMS",
        "bron_type": "WMS",
        "url": "https://geo.example.org/wms",
        "typename": "swf:laag",
        "srsname": "EPSG:3857",
        "versie": "1.3.0",
        "wms_stijl": None,
        "toegang": "openbaar",
    }
    client = _maak_client(_NepWmsDb(basis))

    # Ongeldige request en bbox
    assert client.get("/api/externe-lagen/7/wms?request=GetCapabilities").status_code == 400
    assert client.get("/api/externe-lagen/7/wms?request=GetMap&bbox=ongeldig").status_code == 400
    assert client.get("/api/externe-lagen/7/wms?request=GetMap&bbox=10,10,5,20").status_code == 400

    # Niet-WMS laag
    wfs_client = _maak_client(_NepWmsDb({**basis, "bron_type": "WFS"}))
    assert wfs_client.get("/api/externe-lagen/7/wms?request=GetLegendGraphic").status_code == 400

    # SSRF-bescherming
    for slechte_url in (
        "http://127.0.0.1:8000/wms",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/wms",
        "http://backend.internal/wms",
    ):
        ssrf_client = _maak_client(_NepWmsDb({**basis, "url": slechte_url}))
        assert ssrf_client.get("/api/externe-lagen/7/wms?request=GetLegendGraphic").status_code == 400

    # Upstream XML ServiceExceptionReport wordt geweigerd met 502
    class _XmlResp:
        content = b"<ServiceExceptionReport/>"
        headers = {"content-type": "application/vnd.ogc.se_xml"}

        def raise_for_status(self):
            pass

    class _XmlClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            return _XmlResp()

    monkeypatch.setattr(el_router.httpx, "AsyncClient", _XmlClient)
    assert client.get("/api/externe-lagen/7/wms?request=GetLegendGraphic").status_code == 502

    # Interne WMS-laag zonder rol (#254) geeft 401
    intern_client = _maak_client(_NepWmsDb({**basis, "toegang": "intern"}, toegang_waarde="intern"), toegang.ANONIEM)
    assert intern_client.get("/api/externe-lagen/7/wms?request=GetLegendGraphic").status_code == 401


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_viewer_wms_mercator_bbox_opacity_en_css():
    """Node-evaluatie van berekenWmsMercatorBbox, zetExterneLaagOpacity en syncExterneLaagCheckboxes + CSS-tokens."""
    js = APP_JS.read_text(encoding="utf-8")
    css = STYLES_CSS.read_text(encoding="utf-8")

    assert "TileLayer" in js and "BitmapLayer" in js
    assert ".externe-laag-actief-details" in css
    assert ".externe-laag-wms-legenda" in css
    assert ".externe-laag-opacity-slider" in css

    fn_lonlat = _extract_js_function(js, "lonLatNaarMercator")
    fn_bbox = _extract_js_function(js, "berekenWmsMercatorBbox")
    fn_op = _extract_js_function(js, "zetExterneLaagOpacity")
    fn_sync = _extract_js_function(js, "syncExterneLaagCheckboxes")

    script = f"""
const window = {{}};
const MERCATOR_MAX = 20037508.342789244;
let redrawCount = 0;
const state = {{
  externeKaartlagen: [{{ id: 12, opacity: 0.8 }}],
  externeKaartlaagData: {{ 12: {{ laag: {{ id: 12, opacity: 0.8 }}, isWms: true }} }},
  deckgl: {{}},
  currentData: {{ features: [] }},
}};
function displayOnMap() {{ redrawCount++; }}
function renderExterneLagenOnly() {{ redrawCount++; }}

const imgMock = {{
  src: '',
  dataset: {{ wmsLegendUrl: '/api/externe-lagen/12/wms?request=GetLegendGraphic' }},
  getAttribute(name) {{ return name === 'src' ? this.src : null; }},
}};
const cbs = [
  {{ id: 'toggle-externe-laag-12', dataset: {{ laagId: '12' }}, checked: false, disabled: false }},
  {{ id: 'toggle-aanbevolen-laag-12', dataset: {{ laagId: '12' }}, checked: false, disabled: false }},
];
const details = [
  {{ dataset: {{ laagDetailsId: '12' }}, hidden: true, querySelector: (s) => s.includes('legenda-img') ? imgMock : null }},
];
const sliders = [
  {{ dataset: {{ laagOpacityId: '12' }}, value: '80' }},
  {{ dataset: {{ laagOpacityId: '12' }}, value: '80' }},
];
const labels = [
  {{ dataset: {{ laagOpacityWaarde: '12' }}, textContent: '80%' }},
  {{ dataset: {{ laagOpacityWaarde: '12' }}, textContent: '80%' }},
];
const sectie = {{
  querySelectorAll(sel) {{
    if (sel.includes('data-laag-id')) return cbs;
    if (sel.includes('data-laag-details-id')) return details;
    if (sel.includes('data-laag-opacity-id')) return sliders;
    if (sel.includes('data-laag-opacity-waarde')) return labels;
    return [];
  }},
}};
const document = {{ getElementById: (id) => id === 'externe-lagen-sectie' ? sectie : null }};

{fn_lonlat}
{fn_bbox}
{fn_op}
{fn_sync}

const bbox = berekenWmsMercatorBbox({{ west: 5.0, south: 53.0, east: 6.0, north: 53.5 }});
syncExterneLaagCheckboxes(12, true, false);
const naActief = {{ checked: cbs.map(c => c.checked), hidden: details[0].hidden, legendSrc: imgMock.src }};
zetExterneLaagOpacity(12, 0.45);
const naOpacity = {{
  stateOp: state.externeKaartlagen[0].opacity,
  dataOp: state.externeKaartlaagData[12].laag.opacity,
  sliders: sliders.map(s => s.value),
  labels: labels.map(l => l.textContent),
  redrawCount,
}};
syncExterneLaagCheckboxes(12, false, false);
console.log(JSON.stringify({{ bbox, naActief, naOpacity, naUitHidden: details[0].hidden }}));
"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)

    minx, miny, maxx, maxy = (float(x) for x in res["bbox"].split(","))
    assert 556000 < minx < 557000
    assert 6980000 < miny < 6985000
    assert 667000 < maxx < 668500
    assert 7075000 < maxy < 7077000
    assert res["naActief"] == {
        "checked": [True, True],
        "hidden": False,
        "legendSrc": "/api/externe-lagen/12/wms?request=GetLegendGraphic",
    }
    assert res["naOpacity"] == {
        "stateOp": 0.45,
        "dataOp": 0.45,
        "sliders": ["45", "45"],
        "labels": ["45%", "45%"],
        "redrawCount": 1,
    }
    assert res["naUitHidden"] is True
