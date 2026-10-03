"""Cachebeleid voor statische bestanden (#246): versie/hash in het pad = lang, de rest opnieuw valideren."""

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from omnitwin.statisch import ONVERANDERLIJK, OPNIEUW_VALIDEREN, StatischeBestanden, cache_control

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("pad,verwacht", [
    ("/static/vendor/d3@7.9.0/d3.min.js", ONVERANDERLIJK),
    ("vendor/maplibre-gl@3.6.2/maplibre-gl.css", ONVERANDERLIJK),
    ("admin-panel/assets/index-D_76-aSi.js", ONVERANDERLIJK),
    ("/static/admin-panel/assets/index-B5kdNBqP.css", ONVERANDERLIJK),
    ("/static/css/styles.css", OPNIEUW_VALIDEREN),
    ("/static/css/themes/swf.css", OPNIEUW_VALIDEREN),
    ("/static/images/beeldmerk.svg", OPNIEUW_VALIDEREN),
    ("/static/js/app.js", OPNIEUW_VALIDEREN),
    ("/static/vendor/README.md", OPNIEUW_VALIDEREN),
    ("admin-panel/index.html", OPNIEUW_VALIDEREN),
    ("admin-panel/manifest.json", OPNIEUW_VALIDEREN),
])
def test_cache_control(pad, verwacht):
    assert cache_control(pad) == verwacht


def test_statische_bestanden_zetten_header(tmp_path):
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "a.css").write_text("body{}")
    (tmp_path / "vendor" / "x@1.0.0").mkdir(parents=True)
    (tmp_path / "vendor" / "x@1.0.0" / "x.js").write_text("1")
    app = Starlette()
    app.mount("/static", StatischeBestanden(directory=str(tmp_path)), name="static")
    c = TestClient(app)
    r = c.get("/static/css/a.css")
    assert r.status_code == 200 and r.headers["cache-control"] == OPNIEUW_VALIDEREN
    assert c.get("/static/css/a.css", headers={"If-None-Match": r.headers["etag"]}).status_code == 304
    assert c.get("/static/vendor/x@1.0.0/x.js").headers["cache-control"] == ONVERANDERLIJK
