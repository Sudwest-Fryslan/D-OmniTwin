"""Web-container (#408) tegen een draaiende stack: de bestanden van de viewer en de beheeromgeving komen
van de service web, via de gateway, met hetzelfde cachebeleid en dezelfde routes als eerder de backend
(#246, #290). De API's en de pagina van de viewer blijven bij de backend.

    OMNITWIN_BASE_URL=http://localhost:8080 pytest -m integration tests/integration/test_web_container_stack.py
"""

import os
import re

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
DICHT = os.environ.get("VIEWER_TOEGANG", "open").strip().lower() not in ("", "open")
LANG = "public, max-age=31536000, immutable"


def get(pad, **kw):
    return requests.get(f"{BASE_URL}{pad}", timeout=TIMEOUT, allow_redirects=False, **kw)


@pytest.mark.parametrize("pad", ["/admin", "/admin/", "/admin/dashboard", "/admin/login"])
def test_beheeromgeving_spa(pad):
    r = get(pad)
    assert r.status_code == 200, pad
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["cache-control"] == "no-cache"
    assert '<div id="root">' in r.text


def test_bestanden_in_de_root_van_de_build():
    r = get("/admin/manifest.json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert r.headers["cache-control"] == "no-cache"


def test_vite_assets_een_jaar():
    index = get("/admin/").text
    for pad in re.findall(r'(?:src|href)="(/static/admin-panel/assets/[^"]+)"', index):
        r = get(pad)
        assert r.status_code == 200 and r.headers["cache-control"] == LANG, pad


def test_eigen_bestanden_opnieuw_valideren_met_etag():
    r = get("/static/js/app.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert get("/static/js/app.js", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_vendor_een_jaar():
    r = get("/static/vendor/inter@5.3.0/inter.css")
    assert r.status_code == 200 and r.headers["cache-control"] == LANG


def test_oude_rapportlinks_doorsturen_met_query():
    r = get("/admin/rapport/benchmark?gebied_a=GM1900&gebieden_b=BU190001")
    assert r.status_code == 307
    assert r.headers["location"] == "/rapport/benchmark?gebied_a=GM1900&gebieden_b=BU190001"
    assert get("/admin/rapport").headers["location"] == "/rapport"


@pytest.mark.skipif(DICHT, reason="VIEWER_TOEGANG=inloggen: zie test_viewer_toegang_stack.py")
@pytest.mark.parametrize("pad", ["/rapport", "/rapport/benchmark"])
def test_rapport_spa(pad):
    r = get(pad, headers={"Accept": "text/html"})
    assert r.status_code == 200 and '<div id="root">' in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_onbekend_pad_404():
    assert get("/bestaat-niet").status_code == 404


def test_backend_blijft_de_viewer_en_de_api_serveren():
    assert get("/health").json()["api"] == "online"
    assert get("/openapi.json").status_code == (401 if DICHT else 200)
    if not DICHT:
        assert 'id="map"' in get("/", headers={"Accept": "text/html"}).text
