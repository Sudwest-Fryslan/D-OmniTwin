"""Toegang per laag en bron (#254, ADR 0010): stand per verzoek, rol per databaseverbinding, forwardAuth-header
voor PostgREST, interne collecties van pg_featureserv, 401/403 bij een directe aanroep, en de vastlegging in
migratie, schema api en Traefik. Zonder netwerk of database."""

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from omnitwin import oidc, toegang, viewer_toegang
from omnitwin.laden.catalogus import toegang_van

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
ISSUER = "http://localhost/auth/realms/omnitwin"
LEZER = {"user_id": "s1", "username": "gebruiker", "is_admin": False, "type": "oidc", "rollen": ["lezer"]}
BEHEERDER = {"user_id": "s2", "username": "admin", "is_admin": True, "type": "oidc", "rollen": ["beheerder"]}
ZONDER_ROL = {"user_id": "s3", "username": "piet", "is_admin": False, "type": "oidc", "rollen": []}
ETL = {"user_id": "etl", "username": "etl", "is_admin": False, "type": "bearer", "rollen": ["datasets:laden"]}
COOKIE = {"session_token": "x"}


@pytest.fixture
def app(monkeypatch):
    """App met de middleware, het forwardAuth-endpoint en een route die de stand teruggeeft."""
    monkeypatch.delenv("VIEWER_TOEGANG", raising=False)
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    staat = {"wie": None, "intern": set()}

    def gebruiker_van(_request):
        if isinstance(staat["wie"], Exception):
            raise staat["wie"]
        return staat["wie"]

    monkeypatch.setattr(viewer_toegang, "gebruiker_van", gebruiker_van)
    monkeypatch.setattr(
        toegang, "collectie_is_intern", lambda uri: (toegang.collectie_uit_uri(uri) or ("", ""))[1] in staat["intern"]
    )
    a = FastAPI()
    oidc.registreer(a)
    a.add_middleware(viewer_toegang.ViewerToegangMiddleware)
    a.add_api_route(viewer_toegang.CONTROLE_PAD, viewer_toegang.controleer, methods=["GET"])

    def stand():
        return JSONResponse({"stand": toegang.stand(), "mag_intern": toegang.mag_intern()})

    for pad in ("/api/kompas/stand", "/api/laden/v1/stand", "/static/stand"):
        a.add_api_route(pad, stand, methods=["GET"])
    a.state.staat = staat
    return a


def client(app, wie=None):
    app.state.staat["wie"] = wie
    return TestClient(app)


# ---------------------------------------------------------------- stand per verzoek


def test_zonder_verzoek_geen_filter():
    assert toegang.stand() is None and toegang.mag_intern()


@pytest.mark.parametrize(
    "wie,cookies,stand",
    [
        (None, {}, "anoniem"),
        (LEZER, {}, "anoniem"),  # zonder cookie of token: niet opzoeken
        (LEZER, COOKIE, "met-rol"),
        (BEHEERDER, COOKIE, "met-rol"),
        (ZONDER_ROL, COOKIE, "zonder-rol"),
        (None, COOKIE, "anoniem"),  # verlopen sessie
    ],
)
def test_stand_in_open_modus(app, wie, cookies, stand):
    c = client(app, wie)
    c.cookies.update(cookies)
    r = c.get("/api/kompas/stand").json()
    assert r["stand"] == stand and r["mag_intern"] is (stand == "met-rol")


def test_bearer_token_telt(app):
    r = client(app, ETL).get("/api/kompas/stand", headers={"Authorization": "Bearer x"}).json()
    assert r["stand"] == "zonder-rol"


def test_ongeldig_token_is_anoniem(app):
    fout = oidc.AuthProbleem(401, "token-ongeldig", "Ongeldig token", "x")
    r = client(app, fout).get("/api/kompas/stand", headers={"Authorization": "Bearer x"}).json()
    assert r["stand"] == "anoniem"


def test_laad_api_en_statisch_zonder_filter(app):
    """De laad-API heeft eigen tokens en rollen; statische bestanden geen data."""
    c = client(app)
    assert c.get("/api/laden/v1/stand").json()["stand"] is None
    assert c.get("/static/stand").json()["stand"] is None


def test_dicht_met_rol(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    assert client(app, LEZER).get("/api/kompas/stand").json()["stand"] == "met-rol"


def test_stand_lekt_niet_naar_een_volgend_verzoek(app):
    c = client(app, LEZER)
    c.cookies.update(COOKIE)
    assert c.get("/api/kompas/stand").json()["stand"] == "met-rol"
    assert toegang.stand() is None


# ---------------------------------------------------------------- forwardAuth


@pytest.mark.parametrize(
    "wie,cookies,header",
    [
        (None, {}, "openbaar"),
        (LEZER, COOKIE, "intern"),
        (BEHEERDER, COOKIE, "intern"),
        (ZONDER_ROL, COOKIE, "openbaar"),
    ],
)
def test_forwardauth_header_voor_postgrest(app, wie, cookies, header):
    c = client(app, wie)
    c.cookies.update(cookies)
    r = c.get(viewer_toegang.CONTROLE_PAD, headers={"X-Forwarded-Uri": "/api/data/indicatoren"})
    assert r.status_code == 204 and r.headers[toegang.HEADER] == header


def test_forwardauth_dicht_met_rol_intern(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app, LEZER).get(viewer_toegang.CONTROLE_PAD)
    assert r.status_code == 204 and r.headers[toegang.HEADER] == "intern"


@pytest.mark.parametrize("wie,cookies,status", [(None, {}, 401), (ZONDER_ROL, COOKIE, 403), (LEZER, COOKIE, 204)])
def test_forwardauth_interne_collectie(app, wie, cookies, status):
    app.state.staat["intern"] = {"demo_intern_laag"}
    c = client(app, wie)
    c.cookies.update(cookies)
    r = c.get(
        viewer_toegang.CONTROLE_PAD,
        headers={"X-Forwarded-Uri": "/api/geo/v1/collections/laag.demo_intern_laag/items?limit=1"},
    )
    assert r.status_code == status
    if status != 204:
        assert r.headers["content-type"].startswith("application/problem+json")


def test_forwardauth_openbare_collectie(app):
    app.state.staat["intern"] = {"demo_intern_laag"}
    r = client(app).get(
        viewer_toegang.CONTROLE_PAD,
        headers={"X-Forwarded-Uri": "/api/geo/collections/public.vw_gebieden_features/items"},
    )
    assert r.status_code == 204


@pytest.mark.parametrize(
    "uri,verwacht",
    [
        ("/api/geo/v1/collections/laag.x_y/items", ("laag", "x_y")),
        ("/api/geo/collections/public.vw_gebieden_features", ("public", "vw_gebieden_features")),
        ("/api/geo/collections/laag.abc?f=json", ("laag", "abc")),
        ("/api/geo/collections", None),
        ("/api/data/indicatoren", None),
        ("", None),
    ],
)
def test_collectie_uit_uri(uri, verwacht):
    assert toegang.collectie_uit_uri(uri) == verwacht


def test_collectie_buiten_schema_laag_niet_opzoeken(monkeypatch):
    monkeypatch.setattr("omnitwin.database.SessionLocal", lambda: pytest.fail("geen database nodig"), raising=False)
    assert toegang.collectie_is_intern("/api/geo/collections/public.vw_gebieden_features/items") is False


# ---------------------------------------------------------------- rol per databaseverbinding


class NepCursor:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql):
        self.log.append(sql)


class NepVerbinding:
    def __init__(self):
        self.log = []

    def cursor(self):
        return NepCursor(self.log)

    def commit(self):
        self.log.append("COMMIT")


@pytest.mark.parametrize(
    "stand,sql",
    [
        (None, "RESET ROLE"),
        ("met-rol", "RESET ROLE"),
        ("anoniem", "SET ROLE omnitwin_openbaar"),
        ("zonder-rol", "SET ROLE omnitwin_openbaar"),
    ],
)
def test_checkout_zet_rol_en_commit(monkeypatch, stand, sql):
    from sqlalchemy import event

    vangst = {}
    monkeypatch.setattr(event, "listens_for", lambda doel, naam: lambda fn: vangst.setdefault(naam, fn))
    toegang.registreer(object())
    verbinding = NepVerbinding()
    token = toegang.zet(stand)
    try:
        vangst["checkout"](verbinding, None, None)
    finally:
        toegang.herstel(token)
    assert verbinding.log == [sql, "COMMIT"]  # commit: een latere rollback draait de rol niet terug


# ---------------------------------------------------------------- directe aanroep: 401/403


class NepDb:
    def __init__(self, waarde):
        self.waarde, self.sql = waarde, []

    def execute(self, sql, params=None):
        self.sql.append((str(sql), params))
        waarde = self.waarde

        class R:
            def scalar(self):
                return waarde

        return R()


@pytest.mark.parametrize("stand,status", [("anoniem", 401), ("zonder-rol", 403)])
def test_interne_indicator_geweigerd(stand, status):
    token = toegang.zet(stand)
    try:
        with pytest.raises(oidc.AuthProbleem) as e:
            toegang.vereis_indicator(NepDb("intern"), "e36c5cab-2e36-4be0-bd8f-ade7924975a6")
        assert e.value.status == status
        with pytest.raises(oidc.AuthProbleem):
            toegang.vereis_kaartlaag(NepDb("intern"), 2)
    finally:
        toegang.herstel(token)


@pytest.mark.parametrize(
    "stand,waarde", [("anoniem", "openbaar"), ("anoniem", None), ("met-rol", "intern"), (None, "intern")]
)
def test_indicator_toegestaan(stand, waarde):
    token = toegang.zet(stand)
    try:
        db = NepDb(waarde)
        toegang.vereis_indicator(db, "e36c5cab-2e36-4be0-bd8f-ade7924975a6")
        toegang.vereis_kaartlaag(db, 1)
        if stand in (None, "met-rol"):
            assert db.sql == []  # met rol: niets opzoeken
    finally:
        toegang.herstel(token)


def test_geen_uuid_geen_opzoeking():
    token = toegang.zet("anoniem")
    try:
        db = NepDb("intern")
        toegang.vereis_indicator(db, None)
        toegang.vereis_indicator(db, "geen-uuid")
        assert db.sql == []
    finally:
        toegang.herstel(token)


# ---------------------------------------------------------------- toegang uit dct:accessRights


@pytest.mark.parametrize(
    "w,verwacht",
    [
        ("http://publications.europa.eu/resource/authority/access-right/PUBLIC", "openbaar"),
        ("http://publications.europa.eu/resource/authority/access-right/PUBLIC/", "openbaar"),
        ({"@id": "http://publications.europa.eu/resource/authority/access-right/PUBLIC"}, "openbaar"),
        ("http://publications.europa.eu/resource/authority/access-right/RESTRICTED", "intern"),
        ("http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC", "intern"),
        (None, "intern"),
    ],
)
def test_toegang_van(w, verwacht):
    assert toegang_van({} if w is None else {"dct:accessRights": w}) == verwacht


# ---------------------------------------------------------------- vastgelegd in migratie, api en Traefik


def test_migratie_rls_en_rol():
    sql = (ROOT / "db/migraties/V032__toegang_per_laag.sql").read_text(encoding="utf-8")
    assert "CREATE ROLE omnitwin_openbaar NOLOGIN" in sql and "NOBYPASSRLS" in sql
    for t in ("indicatoren", "gebied_data", "externe_kaartlagen"):
        assert t in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "FORCE ROW LEVEL SECURITY" in sql
    assert "current_user <> 'omnitwin_openbaar'" in sql
    # dezelfde regel als in Python
    assert "access-right/PUBLIC'" in sql and "THEN 'openbaar' ELSE 'intern'" in sql
    assert "GENERATED ALWAYS AS (laden.toegang_uit_dcat(beschrijving))" in sql


def test_schema_api_filtert_op_toegang():
    sql = (ROOT / "db/migraties/R__api_rollen.sql").read_text(encoding="utf-8")
    for view in ("externe_kaartlagen", "indicatoren", "vw_gebied_indicator_actueel", "gebied_data"):
        blok = sql[sql.index(f"CREATE VIEW api.{view} AS") :]
        blok = blok[: blok.index(";")]
        assert "public.verzoek_mag_intern()" in blok, view
    rpc = sql[sql.index("CREATE FUNCTION api.get_indicatoren_stats") :]
    assert "public.verzoek_mag_intern()" in rpc[: rpc.index("$$;")]
    assert "x-omnitwin-toegang" in sql
    assert "security_invoker = true" in sql
    # de controlefunctie is geen RPC: niet in schema api en niet aan web_anon gegeven
    assert "api.verzoek_mag_intern" not in sql
    assert not re.search(r"GRANT EXECUTE ON FUNCTION public\.verzoek_mag_intern[^;]*web_anon", sql)


def test_traefik_vervangt_toegangsheader():
    yml = (ROOT / "deploy/traefik/dynamic.yml").read_text(encoding="utf-8")
    blok = yml[yml.index("viewer-toegang:") :]
    blok = blok[: blok.index("keycloak-headers:")]
    assert "authResponseHeaders" in blok and '"X-Omnitwin-Toegang"' in blok
    assert toegang.HEADER == "X-Omnitwin-Toegang"
