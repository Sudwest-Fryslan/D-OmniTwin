"""Toegang tot de viewer (#266, ADR 0009): VIEWER_TOEGANG=open|inloggen, de middleware van de backend
en het forwardAuth-endpoint voor /api/data en /api/geo. Zonder netwerk of database."""

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from omnitwin import oidc, oidc_login, viewer_toegang
from omnitwin.config import instellingen

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
ISSUER = "http://localhost/auth/realms/omnitwin"

LEZER = {"user_id": "s1", "username": "gebruiker", "is_admin": False, "type": "oidc", "rollen": ["lezer"]}
BEHEERDER = {
    "user_id": "s2",
    "username": "admin",
    "is_admin": True,
    "type": "oidc",
    "rollen": ["beheerder", "gebruikersbeheerder"],
}
ZONDER_ROL = {"user_id": "s3", "username": "piet", "is_admin": False, "type": "oidc", "rollen": []}
LOKALE_BEHEERDER = {"user_id": 1, "username": "admin", "is_admin": True, "type": "session"}
SCRIPT = {"user_id": "system_admin_key", "username": "API_SCRIPT", "is_admin": True, "type": "api_key"}


@pytest.fixture
def app(monkeypatch):
    """Minimale app met de middleware en het controle-endpoint; `wie` bepaalt de gebruiker."""
    monkeypatch.delenv("VIEWER_TOEGANG", raising=False)
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    staat = {"wie": None}

    def gebruiker_van(_request):
        if isinstance(staat["wie"], Exception):
            raise staat["wie"]
        return staat["wie"]

    monkeypatch.setattr(viewer_toegang, "gebruiker_van", gebruiker_van)
    a = FastAPI()
    a.add_middleware(viewer_toegang.ViewerToegangMiddleware)
    a.add_api_route(viewer_toegang.CONTROLE_PAD, viewer_toegang.controleer, methods=["GET", "HEAD"])
    for pad in (
        "/",
        "/api/gebiedsmonitor/gebieden",
        "/api/kompas/configuraties",
        "/docs",
        "/health",
        "/static/css/styles.css",
        "/admin/login",
        "/api/admin/auth/config",
        "/api/laden/v1/datasets",
        "/api/organisatie",
        "/api/admin/statistieken",
    ):
        a.add_api_route(pad, lambda: PlainTextResponse("ok"), methods=["GET"])
    a.state.staat = staat
    return a


def client(app, wie=None):
    app.state.staat["wie"] = wie
    return TestClient(app, follow_redirects=False)


HTML = {"Accept": "text/html,application/xhtml+xml"}


# ---------------------------------------------------------------- instellingen


@pytest.mark.parametrize(
    "waarde,verwacht",
    [
        (None, "open"),
        ("", "open"),
        ("open", "open"),
        ("OPEN", "open"),
        ("inloggen", "inloggen"),
        ("Inloggen", "inloggen"),
        ("dicht", "inloggen"),
        ("ja", "inloggen"),
    ],
)
def test_viewer_toegang_instelling(monkeypatch, waarde, verwacht):
    if waarde is None:
        monkeypatch.delenv("VIEWER_TOEGANG", raising=False)
    else:
        monkeypatch.setenv("VIEWER_TOEGANG", waarde)
    assert instellingen().viewer_toegang == verwacht
    assert instellingen().viewer_dicht is (verwacht == "inloggen")


@pytest.mark.parametrize(
    "pad,open_",
    [
        ("/health", True),
        ("/static/js/app.js", True),
        ("/admin/login", True),
        ("/admin", True),
        ("/api/admin/auth/oidc/login", True),
        ("/api/laden/v1/datasets", True),
        ("/api/organisatie", True),
        ("/api/viewer/toegang", True),
        ("/.well-known/security.txt", True),
        ("/api/oidc/ik", True),
        ("/", False),
        ("/api/gebiedsmonitor/gebieden", False),
        ("/api/data/gemeenten", False),
        ("/api/geo/collections", False),
        ("/docs", False),
        ("/openapi.json", False),
        ("/api", False),
        ("/api/admin/statistieken", False),
        ("/api/organisatie/x", False),
        ("/api/chat", False),
    ],
)
def test_open_paden(pad, open_):
    assert viewer_toegang.is_open_pad(pad) is open_


@pytest.mark.parametrize(
    "gebruiker,toegang",
    [
        (None, False),
        (LEZER, True),
        (BEHEERDER, True),
        (ZONDER_ROL, False),
        (LOKALE_BEHEERDER, True),
        (SCRIPT, True),
        ({"is_admin": False, "type": "session"}, False),
        ({"is_admin": False, "type": "bearer", "rollen": ["datasets:laden"]}, False),
        ({"is_admin": False, "type": "oidc", "rollen": ["gebruikersbeheerder"]}, False),
    ],
)
def test_heeft_rol(gebruiker, toegang):
    assert viewer_toegang.heeft_rol(gebruiker) is toegang


# ---------------------------------------------------------------- open (standaard)


def test_open_anoniem_alles_200(app):
    c = client(app)
    for pad in ("/", "/api/gebiedsmonitor/gebieden", "/docs"):
        assert c.get(pad, headers=HTML).status_code == 200, pad
    assert c.get(viewer_toegang.CONTROLE_PAD).status_code == 204


# ---------------------------------------------------------------- inloggen


def test_inloggen_anoniem_pagina_naar_keycloak(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app).get("/", headers=HTML)
    assert r.status_code == 302
    assert r.headers["location"] == "/api/admin/auth/oidc/login?terug=/"


def test_inloggen_zonder_keycloak_naar_lokale_inlogpagina(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    monkeypatch.setenv("OIDC_ISSUER", "")
    r = client(app).get("/", headers=HTML)
    assert (r.status_code, r.headers["location"]) == (302, "/admin/login")


@pytest.mark.parametrize(
    "pad", ["/api/gebiedsmonitor/gebieden", "/api/kompas/configuraties", "/docs", "/api/admin/statistieken"]
)
def test_inloggen_anoniem_api_401(app, monkeypatch, pad):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app).get(pad)
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "niet-ingelogd"


def test_inloggen_anoniem_forwardauth_401(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app).get(viewer_toegang.CONTROLE_PAD, headers=HTML)
    assert r.status_code == 401 and r.json()["code"] == "niet-ingelogd"


@pytest.mark.parametrize("wie", [LEZER, BEHEERDER, LOKALE_BEHEERDER, SCRIPT])
def test_inloggen_met_rol_200(app, monkeypatch, wie):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    c = client(app, wie)
    assert c.get("/", headers=HTML).status_code == 200
    assert c.get("/api/gebiedsmonitor/gebieden").status_code == 200
    assert c.get(viewer_toegang.CONTROLE_PAD).status_code == 204


def test_inloggen_zonder_rol_403(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    c = client(app, ZONDER_ROL)
    pagina = c.get("/", headers=HTML)
    assert pagina.status_code == 403 and "Geen toegang" in pagina.text and "piet" in pagina.text
    assert 'id="uitloggen"' in pagina.text
    assert c.get("/api/gebiedsmonitor/gebieden").json()["code"] == "geen-toegang"
    assert c.get(viewer_toegang.CONTROLE_PAD).status_code == 403


def test_geen_toegang_pagina_escapet_naam(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app, {**ZONDER_ROL, "username": "<script>x</script>"}).get("/", headers=HTML)
    assert "<script>x</script>" not in r.text and "&lt;script&gt;" in r.text


@pytest.mark.parametrize(
    "pad",
    [
        "/health",
        "/static/css/styles.css",
        "/admin/login",
        "/api/admin/auth/config",
        "/api/laden/v1/datasets",
        "/api/organisatie",
    ],
)
def test_inloggen_open_paden_blijven_open(app, monkeypatch, pad):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    assert client(app).get(pad).status_code == 200


def test_tikfout_is_dicht(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "dicht")
    assert client(app).get("/api/gebiedsmonitor/gebieden").status_code == 401


def test_ongeldig_token_401_met_www_authenticate(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    fout = oidc.AuthProbleem(
        401, "token-ongeldig", "Ongeldig token", "x", www_authenticate='Bearer error="invalid_token"'
    )
    r = client(app, fout).get("/api/gebiedsmonitor/gebieden")
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Bearer")
    assert client(app).get("/api/gebiedsmonitor/gebieden").headers["www-authenticate"] == "Bearer"


def test_provider_onbereikbaar_503(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    fout = oidc.AuthProbleem(503, "oidc-niet-bereikbaar", "Authenticatie niet beschikbaar", "weg")
    r = client(app, fout).get("/api/gebiedsmonitor/gebieden")
    assert r.status_code == 503 and r.json()["code"] == "oidc-niet-bereikbaar"


# ---------------------------------------------------------------- pagina's in de web-container (#408)

PAGINA = viewer_toegang.CONTROLE_PAD + "?pagina=1"
VIA_TRAEFIK = {
    **HTML,
    "X-Forwarded-Proto": "https",
    "X-Forwarded-Host": "omnitwin.example.nl",
    "X-Forwarded-Uri": "/rapport/benchmark",
}


def test_pagina_open_204(app):
    assert client(app).get(PAGINA, headers=VIA_TRAEFIK).status_code == 204


def test_pagina_anoniem_naar_inloggen_met_absoluut_adres(app, monkeypatch):
    """Traefik maakt een relatieve Location absoluut ten opzichte van de backend; daarom absoluut."""
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app).get(PAGINA, headers=VIA_TRAEFIK)
    assert r.status_code == 302
    assert r.headers["location"] == "https://omnitwin.example.nl/api/admin/auth/oidc/login?terug=/"


def test_pagina_zonder_rol_geen_toegang(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    r = client(app, ZONDER_ROL).get(PAGINA, headers=VIA_TRAEFIK)
    assert r.status_code == 403 and "Geen toegang" in r.text


@pytest.mark.parametrize("wie", [LEZER, BEHEERDER])
def test_pagina_met_rol_204(app, monkeypatch, wie):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    assert client(app, wie).get(PAGINA, headers=VIA_TRAEFIK).status_code == 204


def test_pagina_ongeldig_token_blijft_401(app, monkeypatch):
    monkeypatch.setenv("VIEWER_TOEGANG", "inloggen")
    fout = oidc.AuthProbleem(401, "token-ongeldig", "Ongeldig token", "x", www_authenticate="Bearer")
    assert client(app, fout).get(PAGINA, headers=VIA_TRAEFIK).status_code == 401


def test_rapport_router_heeft_pagina_forwardauth():
    tekst = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    m = re.search(r"traefik\.http\.routers\.rapport\.middlewares=([^\"\s]+)", tekst)
    assert m and "viewer-pagina@file" in m.group(1).split(",")
    dynamic = (ROOT / "deploy/traefik/dynamic.yml").read_text(encoding="utf-8")
    assert f'address: "http://backend:8000{PAGINA}"' in dynamic


# ---------------------------------------------------------------- BFF: terug naar de viewer


@pytest.mark.parametrize(
    "terug,verwacht",
    [
        ("/", "/"),
        ("/admin/llm", "/admin/llm"),
        (None, "/admin/dashboard"),
        ("//evil.example", "/admin/dashboard"),
        ("https://evil.example/", "/admin/dashboard"),
        ("/?x=1", "/admin/dashboard"),
        ("/api/data", "/admin/dashboard"),
    ],
)
def test_veilig_terug(terug, verwacht):
    assert oidc_login.veilig_terug(terug) == verwacht


def test_sessiegebruiker_bevat_rollen():
    g = oidc_login._als_gebruiker("sub", "anne", ["lezer"])
    assert g["rollen"] == ["lezer"] and g["is_admin"] is False


# ---------------------------------------------------------------- Traefik en template


def test_data_api_routers_hebben_forwardauth_voor_het_strippen():
    tekst = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for router in ("postgrest", "postgrest-v1", "pg_featureserv", "pg_featureserv-v1"):
        m = re.search(rf"traefik\.http\.routers\.{re.escape(router)}\.middlewares=([^\"\s]+)", tekst)
        assert m, router
        lijst = m.group(1).split(",")
        assert "viewer-toegang@file" in lijst, router
        # Vóór strip/anoniem: de backend moet het oorspronkelijke verzoek (cookie, Authorization) zien
        assert lijst.index("viewer-toegang@file") <= 1, (router, lijst)


def test_forwardauth_middleware_wijst_naar_controle_endpoint():
    tekst = (ROOT / "deploy/traefik/dynamic.yml").read_text(encoding="utf-8")
    assert "viewer-toegang:" in tekst
    assert f"http://backend:8000{viewer_toegang.CONTROLE_PAD}" in tekst


def test_viewer_kop_heeft_beheer_uitloggen_en_demobalk():
    tekst = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    assert 'id="inloggen"' not in tekst  # één ingang: "Beheer" leidt naar het inloggen
    assert 'id="admin-btn"' in tekst and 'id="uitloggen"' in tekst and "account.naam" in tekst
    assert "Demo-omgeving — standaardwachtwoorden, niet voor productie" in tekst
    assert "/static/js/viewer-account.js" in tekst
