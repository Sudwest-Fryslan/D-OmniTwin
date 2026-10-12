"""Tests voor standalone rapport-routing en redirects (#290).

Borgt dat:
1. Oude /admin/rapport/* deeplinks redirecten (HTTP 307) naar /rapport/* met query parameters.
2. /rapport en /rapport/* de React SPA index.html serveren.
"""

import pytest
from fastapi.testclient import TestClient

from omnitwin.main import app

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    # follow_redirects=False zodat we de 307 status_code en Location header direct kunnen controleren
    return TestClient(app, follow_redirects=False)


def test_redirect_admin_rapport_basis(client):
    """GET /admin/rapport moet redirecten naar /rapport met 307."""
    res = client.get("/admin/rapport")
    assert res.status_code == 307
    assert res.headers["location"] == "/rapport"


def test_redirect_admin_rapport_met_subpad(client):
    """GET /admin/rapport/benchmark moet redirecten naar /rapport/benchmark met 307."""
    res = client.get("/admin/rapport/benchmark")
    assert res.status_code == 307
    assert res.headers["location"] == "/rapport/benchmark"


def test_redirect_admin_rapport_met_query_params(client):
    """GET /admin/rapport/benchmark?gebied_a=GM1900&gebieden_b=BU190001 behoudt query parameters."""
    res = client.get("/admin/rapport/benchmark?gebied_a=GM1900&gebieden_b=BU190001")
    assert res.status_code == 307
    assert res.headers["location"] == "/rapport/benchmark?gebied_a=GM1900&gebieden_b=BU190001"


def test_serve_rapport_spa(client):
    """GET /rapport en /rapport/benchmark moeten de SPA HTML serveren."""
    res = client.get("/rapport")
    assert res.status_code == 200
    assert "html" in res.headers.get("content-type", "")
    assert res.headers.get("cache-control") == "no-cache"

    res_sub = client.get("/rapport/benchmark")
    assert res_sub.status_code == 200
    assert "html" in res_sub.headers.get("content-type", "")
