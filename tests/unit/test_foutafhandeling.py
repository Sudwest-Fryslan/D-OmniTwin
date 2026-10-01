"""Centrale foutafhandeling en UUID-validatie (#203): geen interne fouten naar buiten."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import DataError, IntegrityError

from omnitwin.database import get_db
from omnitwin.fouten import HEADER, GebruikersFout, registreer_foutafhandeling

pytestmark = pytest.mark.unit

GEHEIM = "SELECT wachtwoord FROM users -- psycopg2.errors.InvalidTextRepresentation"


@pytest.fixture
def client():
    app = FastAPI()
    registreer_foutafhandeling(app)

    @app.get("/crash")
    def crash():
        raise RuntimeError(GEHEIM)

    @app.get("/crash-async")
    async def crash_async():
        raise KeyError(GEHEIM)

    @app.get("/data-fout")
    def data_fout():
        raise DataError(GEHEIM, {}, Exception("invalid input syntax for type uuid"))

    @app.get("/conflict")
    def conflict():
        raise IntegrityError(GEHEIM, {}, Exception("duplicate key"))

    @app.get("/http")
    def http():
        raise HTTPException(404, "Niet gevonden")

    @app.get("/gebruikersfout")
    def gebruikersfout():
        try:
            raise GebruikersFout("Gebied X niet gevonden.")
        except GebruikersFout as e:
            raise HTTPException(404, str(e))

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("pad", ["/crash", "/crash-async"])
def test_onverwachte_fout_geeft_generieke_melding_met_correlatie_id(client, pad):
    r = client.get(pad)
    assert r.status_code == 500
    body = r.json()
    assert GEHEIM not in r.text and "wachtwoord" not in r.text
    cid = body["correlatie_id"]
    assert len(cid) == 12 and cid in body["detail"]
    assert r.headers[HEADER] == cid


def test_fout_wordt_gelogd_met_traceback(client, caplog):
    with caplog.at_level("ERROR", logger="omnitwin.fouten"):
        r = client.get("/crash")
    cid = r.json()["correlatie_id"]
    record = next(rec for rec in caplog.records if rec.name == "omnitwin.fouten")
    assert cid in record.getMessage() and "GET /crash" in record.getMessage()
    assert record.exc_info and GEHEIM in str(record.exc_info[1])


def test_correlatie_id_is_per_fout_uniek(client):
    assert client.get("/crash").json()["correlatie_id"] != client.get("/crash").json()["correlatie_id"]


def test_ongeldige_invoer_in_database_geeft_422(client):
    r = client.get("/data-fout")
    assert r.status_code == 422
    assert GEHEIM not in r.text and "uuid" not in r.text.lower()
    assert r.json()["correlatie_id"]


def test_conflict_geeft_409_zonder_sql(client):
    r = client.get("/conflict")
    assert r.status_code == 409
    assert GEHEIM not in r.text and "duplicate" not in r.text


def test_httpexception_en_gebruikersfout_blijven_ongewijzigd(client):
    assert client.get("/http").json() == {"detail": "Niet gevonden"}
    r = client.get("/gebruikersfout")
    assert r.status_code == 404 and r.json() == {"detail": "Gebied X niet gevonden."}


def test_gebruikersfout_is_valueerror():
    """Bestaande `except ValueError` blijft werken voor meldingen uit de services."""
    assert issubclass(GebruikersFout, ValueError)


# ── Ongeldige UUID in het pad: 422 vóór er een databasequery is ────────────────

class _GeenDatabase:
    def __getattr__(self, naam):
        raise AssertionError("Bij een ongeldige UUID mag de database niet aangeroepen worden")


@pytest.fixture
def app_client():
    from omnitwin.routers import gebiedsmonitor, kompas, visualisatie
    app = FastAPI()
    registreer_foutafhandeling(app)
    for r in (gebiedsmonitor.router, kompas.router, visualisatie.router):
        app.include_router(r)
    app.dependency_overrides[get_db] = lambda: _GeenDatabase()
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("pad", [
    "/api/gebiedsmonitor/kaart_data/1",
    "/api/gebiedsmonitor/kaart_data/00000000-0000-0000-0000-000000000000?indicator_uuid=abc",
    "/api/kompas/indicator/geen-uuid/top-buurten",
    "/api/kompas/1/history/BU19000002/geen-uuid",
    "/api/kompas/1/indicator/geen-uuid",
    "/api/visualisatie/config/geen-uuid",
])
def test_ongeldige_uuid_geeft_422(app_client, pad):
    r = app_client.get(pad)
    assert r.status_code == 422, r.text
    assert "SELECT" not in r.text
