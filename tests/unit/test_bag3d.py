"""
Unit tests voor 3D BAG Panden router (src/omnitwin/routers/bag3d.py).
Dekt #410: NameError 'text' herstel, lege gebiedsafhandeling (geen 404 maar 200 met lege features),
kleurberekening en validaties.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from omnitwin.database import get_db
from omnitwin.routers.bag3d import (
    router,
    bouwjaar_kleur,
    get_bbox_for_gebieden,
    get_indicator_code,
)

pytestmark = pytest.mark.unit


def test_bouwjaar_kleur():
    """Valideer kleurberekening op basis van bouwjaar."""
    assert bouwjaar_kleur(None) == "#888888"
    assert bouwjaar_kleur("onbekend") == "#888888"
    assert bouwjaar_kleur(1890) == "#8B0000"
    assert bouwjaar_kleur(1920) == "#c0392b"
    assert bouwjaar_kleur(1950) == "#e74c3c"
    assert bouwjaar_kleur(1970) == "#e67e22"
    assert bouwjaar_kleur(1980) == "#f1c40f"
    assert bouwjaar_kleur(2000) == "#2ecc71"
    assert bouwjaar_kleur(2020) == "#27ae60"


def test_get_bbox_for_gebieden_succes():
    """Valideer dat BBOX correct uit de database wordt opgehaald via text() SQL."""
    mock_db = MagicMock()
    mock_row = MagicMock()
    mock_row.minx = 150000.0
    mock_row.miny = 550000.0
    mock_row.maxx = 160000.0
    mock_row.maxy = 560000.0
    mock_db.execute.return_value.fetchone.return_value = mock_row

    bbox = get_bbox_for_gebieden(mock_db, ["BU00800001"])
    assert bbox == {
        "minx": 150000.0,
        "miny": 550000.0,
        "maxx": 160000.0,
        "maxy": 560000.0,
    }
    # Controleer dat db.execute is aangeroepen
    assert mock_db.execute.called


def test_get_bbox_for_gebieden_niet_gevonden():
    """Valideer dat 404 optreedt als gebieden geen geldige geometrie opleveren."""
    mock_db = MagicMock()
    mock_row = MagicMock()
    mock_row.minx = None
    mock_db.execute.return_value.fetchone.return_value = mock_row

    with pytest.raises(HTTPException) as exc_info:
        get_bbox_for_gebieden(mock_db, ["BU99999999"])
    assert exc_info.value.status_code == 404


def test_get_indicator_code():
    """Valideer indicator code lookup."""
    mock_db = MagicMock()
    mock_row = MagicMock()
    mock_row.code = "gemiddeld_bouwjaar"
    mock_db.execute.return_value.fetchone.return_value = mock_row

    code = get_indicator_code(mock_db, "some-uuid")
    assert code == "gemiddeld_bouwjaar"

    mock_db.execute.return_value.fetchone.return_value = None
    assert get_indicator_code(mock_db, "onbekend-uuid") is None


@pytest.fixture
def bag3d_client():
    app = FastAPI()
    app.include_router(router)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    return client, mock_db


def test_bag3d_validatie_gebied_ids(bag3d_client):
    """Valideer dat 0 of meer dan 3 gebieden wordt geweigerd."""
    client, _ = bag3d_client

    # 0 gebieden
    res_leeg = client.post("/api/3dbag/buildings", json={"gebied_ids": []})
    assert res_leeg.status_code == 422

    # 4 gebieden (max is 3)
    res_teveel = client.post("/api/3dbag/buildings", json={"gebied_ids": ["BU1", "BU2", "BU3", "BU4"]})
    assert res_teveel.status_code == 422


@patch("omnitwin.routers.bag3d.fetch_buildings_from_api")
@patch("omnitwin.routers.bag3d.get_bbox_for_gebieden")
def test_bag3d_lege_respons_buitengebied(mock_bbox, mock_fetch, bag3d_client):
    """
    Test fix voor #410: Gebied zonder panden (buitengebied) moet HTTP 200 retourneren
    met een lege FeatureCollection en vriendelijke melding i.p.v. HTTP 404 of 500.
    """
    client, _ = bag3d_client
    mock_bbox.return_value = {"minx": 1000.0, "miny": 2000.0, "maxx": 3000.0, "maxy": 4000.0}
    mock_fetch.return_value = {"type": "FeatureCollection", "features": []}

    res = client.post("/api/3dbag/buildings", json={"gebied_ids": ["BU00800000"]})
    assert res.status_code == 200
    data = res.json()

    assert data["type"] == "FeatureCollection"
    assert data["features"] == []
    assert data["metadata"]["panden_count"] == 0
    assert "Geen 3D panden gevonden" in data["metadata"]["melding"]


@patch("omnitwin.routers.bag3d.enrich_features_with_color")
@patch("omnitwin.routers.bag3d.fetch_buildings_from_api")
@patch("omnitwin.routers.bag3d.get_bbox_for_gebieden")
def test_bag3d_gevulde_respons(mock_bbox, mock_fetch, mock_enrich, bag3d_client):
    """Test succesvolle respons met panden."""
    client, _ = bag3d_client
    mock_bbox.return_value = {"minx": 1000.0, "miny": 2000.0, "maxx": 3000.0, "maxy": 4000.0}
    raw_feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[5.0, 52.0], [5.1, 52.0], [5.1, 52.1], [5.0, 52.0]]]},
        "properties": {"identificatie": "NL.IMBAG.Pand.001", "bouwjaar": 1965}
    }
    mock_fetch.return_value = {"type": "FeatureCollection", "features": [raw_feature]}
    mock_enrich.return_value = [{
        **raw_feature,
        "properties": {**raw_feature["properties"], "indicator_color": "#e67e22", "kleur_mode": "bouwjaar"}
    }]

    res = client.post("/api/3dbag/buildings", json={"gebied_ids": ["BU00800000"]})
    assert res.status_code == 200
    data = res.json()

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["metadata"]["panden_count"] == 1
    assert data["metadata"]["kleur_mode"] == "bouwjaar"


def test_bag3d_health(bag3d_client):
    """Test health check route."""
    client, _ = bag3d_client
    res = client.get("/api/3dbag/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
