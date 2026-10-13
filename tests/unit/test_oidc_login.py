"""Inloggen via OIDC in de beheeromgeving (#251): instellingen, beheerroutes met een bearer-token,
lokaal inloggen uit bij OIDC en de start van de authorization-code-flow. Zonder netwerk of database."""

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from omnitwin import oidc, oidc_login
from omnitwin.config import instellingen
from omnitwin.database import get_db
from omnitwin.fouten import registreer_foutafhandeling
from omnitwin.routers import auth

pytestmark = pytest.mark.unit

ISSUER = "http://localhost/auth/realms/omnitwin"
INTERN = "http://keycloak:8080/auth/realms/omnitwin"
SLEUTEL = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks():
    d = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(SLEUTEL.public_key()))
    d.update(kid="a", use="sig", alg="RS256")
    return {"keys": [d]}


def token(rollen, **wijzig):
    nu = int(time.time())
    claims = {"iss": ISSUER, "aud": ["omnitwin-api"], "sub": "4b1d-sub", "azp": "omnitwin-web",
              "preferred_username": "anne", "email": "anne@example.org", "jti": "j1",
              "iat": nu, "exp": nu + 300, "realm_access": {"roles": list(rollen)}}
    claims.update(wijzig)
    return jwt.encode(claims, SLEUTEL, algorithm="RS256", headers={"kid": "a"})


class Stil:
    berichten: list = []

    @classmethod
    def _log(cls, msg, **_):
        cls.berichten.append(msg)

    info = warning = error = debug = _log


@pytest.fixture
def stil(monkeypatch):
    Stil.berichten = []
    monkeypatch.setattr(auth, "AppLogger", Stil)
    return Stil


@pytest.fixture
def oidc_aan(monkeypatch, stil):
    for naam in ("OIDC_AUDIENCE", "OIDC_JWKS_URL", "LOKAAL_INLOGGEN", "OIDC_CLIENT_ID", "ADMIN_API_KEY",
                 "OMNITWIN_OMGEVING"):
        monkeypatch.delenv(naam, raising=False)
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_INTERN_URL", INTERN)

    def haal(url):
        if url.endswith("/.well-known/openid-configuration"):
            return {"issuer": ISSUER, "jwks_uri": ISSUER + "/protocol/openid-connect/certs"}
        if url == INTERN + "/protocol/openid-connect/certs":
            return _jwks()
        raise AssertionError(url)

    monkeypatch.setattr(oidc, "_haal_json", haal)
    oidc.wis_cache()
    oidc_login.wis_cache()
    yield
    oidc.wis_cache()
    oidc_login.wis_cache()


@pytest.fixture
def oidc_uit(monkeypatch, stil):
    for naam in ("OIDC_ISSUER", "LOKAAL_INLOGGEN", "ADMIN_API_KEY", "OMNITWIN_OMGEVING"):
        monkeypatch.setenv(naam, "")


def _client():
    app = FastAPI()
    registreer_foutafhandeling(app)
    app.include_router(auth.router)

    @app.get("/api/admin/iets")
    def iets(g: dict = Depends(auth.vereis_admin)):
        return {"naam": g["username"], "type": g["type"]}

    app.dependency_overrides[get_db] = lambda: None  # zonder cookie geen databasevraag
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


# ------------------------------------------------------------------ instellingen

@pytest.mark.parametrize("issuer, lokaal, aan, nood", [
    ("", "", True, False),            # zonder Keycloak: lokaal inloggen zoals altijd
    ("", "false", True, False),       # ook dan; anders kan niemand meer in
    (ISSUER, "", False, False),       # met Keycloak standaard uit
    (ISSUER, "true", True, True),     # noodtoegang
])
def test_lokaal_inloggen(monkeypatch, issuer, lokaal, aan, nood):
    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("LOKAAL_INLOGGEN", lokaal)
    i = instellingen()
    assert (i.lokaal_inloggen_aan, i.noodtoegang) == (aan, nood)
    assert i.oidc_client_id == "omnitwin-web"


def test_config_met_oidc(oidc_aan):
    r = _client().get("/api/admin/auth/config")
    assert r.json() == {
        "oidc": True, "lokaal": False, "noodtoegang": False,
        "gebruikersbeheer_url": "http://localhost/auth/admin/omnitwin/console/",
        "account_url": ISSUER + "/account", "demo": False,
    }


def test_config_zonder_oidc(oidc_uit):
    r = _client().get("/api/admin/auth/config")
    assert r.json() == {"oidc": False, "lokaal": True, "noodtoegang": False,
                        "gebruikersbeheer_url": None, "account_url": None, "demo": False}


# ------------------------------------------------------------------ beheerroutes met een bearer-token

def _kop(t):
    return {"Authorization": f"Bearer {t}"}


def test_bearer_met_beheerder_200(oidc_aan):
    r = _client().get("/api/admin/iets", headers=_kop(token(["beheerder", "lezer"])))
    assert r.status_code == 200, r.text
    assert r.json() == {"naam": "anne", "type": "bearer"}


def test_bearer_met_lezer_403_en_audit_zonder_email(oidc_aan, stil):
    r = _client().get("/api/admin/iets", headers=_kop(token(["lezer"])))
    assert r.status_code == 403
    log = " ".join(stil.berichten)
    assert "anne" in log and "4b1d-sub" in log and "example.org" not in log


def test_zonder_token_401(oidc_aan):
    assert _client().get("/api/admin/iets").status_code == 401


@pytest.mark.parametrize("t", ["geen-jwt", token(["beheerder"], exp=int(time.time()) - 600),
                               token(["beheerder"], iss="http://elders/realms/x")])
def test_ongeldig_token_401(oidc_aan, t):
    r = _client().get("/api/admin/iets", headers=_kop(t))
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Bearer")


def test_bearer_genegeerd_zonder_oidc(oidc_uit):
    assert _client().get("/api/admin/iets", headers=_kop(token(["beheerder"]))).status_code == 401


# ------------------------------------------------------------------ lokaal inloggen

def test_lokaal_inloggen_uit_bij_oidc(oidc_aan):
    r = _client().post("/api/admin/auth/login", data={"username": "admin", "password": "x"})
    assert r.status_code == 403
    assert "Keycloak" in r.json()["detail"]


# ------------------------------------------------------------------ authorization code + PKCE

@pytest.fixture
def discovery(monkeypatch, oidc_aan):
    """Discovery zoals Keycloak die intern geeft; legt de meegestuurde headers vast."""
    gevraagd = []

    class Antwoord:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            b = "http://localhost:8080/auth/realms/omnitwin"  # interne issuer (KC_HOSTNAME zonder schema)
            return {"issuer": b, "authorization_endpoint": b + "/protocol/openid-connect/auth",
                    "token_endpoint": b + "/protocol/openid-connect/token",
                    "end_session_endpoint": b + "/protocol/openid-connect/logout"}

    def get(url, **kw):
        gevraagd.append((url, kw.get("headers", {})))
        return Antwoord()

    monkeypatch.setattr(oidc_login.httpx, "get", get)
    return gevraagd


def test_eindpunten_publiek_voor_browser_intern_voor_backend(discovery):
    e = oidc_login.eindpunten()
    assert e.autorisatie == ISSUER + "/protocol/openid-connect/auth"
    assert e.uitloggen == ISSUER + "/protocol/openid-connect/logout"
    assert e.token == INTERN + "/protocol/openid-connect/token"
    url, headers = discovery[0]
    assert url == INTERN + "/.well-known/openid-configuration"
    assert headers["X-Forwarded-Host"] == "localhost" and headers["X-Forwarded-Proto"] == "http"
    assert headers["X-Forwarded-Port"] == "80"


def test_start_inloggen_met_pkce(discovery):
    r = _client().get("/api/admin/auth/oidc/login?terug=/admin/indicatoren",
                      headers={"host": "omnitwin.example.nl", "x-forwarded-proto": "https"})
    assert r.status_code == 303
    adres = urlsplit(r.headers["location"])
    q = {k: v[0] for k, v in parse_qs(adres.query).items()}
    assert f"{adres.scheme}://{adres.netloc}{adres.path}" == ISSUER + "/protocol/openid-connect/auth"
    assert q["client_id"] == "omnitwin-web" and q["response_type"] == "code"
    assert q["code_challenge_method"] == "S256" and "email" not in q["scope"]
    assert q["redirect_uri"] == "https://omnitwin.example.nl/api/admin/auth/oidc/callback"
    cookie = r.cookies.get(oidc_login.INLOG_COOKIE)
    inlog = json.loads(base64.urlsafe_b64decode(cookie + "=" * (-len(cookie) % 4)))
    assert inlog["s"] == q["state"] and inlog["t"] == "/admin/indicatoren"
    verwacht = base64.urlsafe_b64encode(hashlib.sha256(inlog["v"].encode()).digest()).rstrip(b"=").decode()
    assert q["code_challenge"] == verwacht
    kop = r.headers["set-cookie"].lower()
    assert "httponly" in kop and "path=/api/admin/auth/oidc" in kop and "samesite=lax" in kop


def test_callback_met_andere_state_geweigerd(discovery):
    c = _client()
    start = c.get("/api/admin/auth/oidc/login")
    c.cookies.set(oidc_login.INLOG_COOKIE, start.cookies.get(oidc_login.INLOG_COOKIE), path="/api/admin/auth/oidc")
    r = c.get("/api/admin/auth/oidc/callback?code=abc&state=vervalst")
    assert r.status_code == 303 and r.headers["location"] == "/admin/login?fout=state"
    assert "session_token" not in r.cookies


def test_callback_zonder_inlogcookie(discovery):
    r = _client().get("/api/admin/auth/oidc/callback?code=abc&state=x")
    assert r.headers["location"] == "/admin/login?fout=sessie-verlopen"


def test_callback_geweigerd_door_gebruiker(oidc_aan):
    r = _client().get("/api/admin/auth/oidc/callback?error=access_denied&state=x")
    assert r.headers["location"] == "/admin/login?fout=geweigerd"


@pytest.mark.parametrize("terug, verwacht", [
    ("/admin/indicatoren", "/admin/indicatoren"),
    ("https://elders.example/admin", "/admin/dashboard"),
    ("//elders.example/admin", "/admin/dashboard"),
    ("/admin//elders", "/admin/dashboard"),
    ("/api/admin/llm", "/admin/dashboard"),
    (None, "/admin/dashboard"),
])
def test_alleen_terug_naar_de_beheeromgeving(terug, verwacht):
    assert oidc_login.veilig_terug(terug) == verwacht


def test_geen_keycloak_console_bij_andere_provider(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER", "https://login.example.org/tenant/v2.0")
    assert oidc_login.gebruikersbeheer_url() is None and oidc_login.account_url() is None


def test_forwarded_headers_https_met_poort():
    h = oidc_login._forwarded("https://omnitwin.example.nl:8443/auth/realms/omnitwin")
    assert h == {"X-Forwarded-Proto": "https", "X-Forwarded-Host": "omnitwin.example.nl:8443",
                 "X-Forwarded-Port": "8443"}


# ------------------------------------------------------------------ Entra ID: scope en clientgeheim (#411)

def test_extra_scope_bij_inloggen(discovery, monkeypatch):
    monkeypatch.setenv("OIDC_SCOPE", " offline_access  api://00000000-0000-0000-0000-0000000000aa/toegang ")
    r = _client().get("/api/admin/auth/oidc/login")
    q = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
    assert q["scope"] == "openid profile offline_access api://00000000-0000-0000-0000-0000000000aa/toegang"


def test_zonder_extra_scope_ongewijzigd(discovery, monkeypatch):
    monkeypatch.delenv("OIDC_SCOPE", raising=False)
    r = _client().get("/api/admin/auth/oidc/login")
    assert parse_qs(urlsplit(r.headers["location"]).query)["scope"] == ["openid profile"]
    assert oidc_login._ververs_data("rt") == {"grant_type": "refresh_token", "refresh_token": "rt"}


def test_verversen_met_dezelfde_scope(monkeypatch):
    monkeypatch.setenv("OIDC_SCOPE", "offline_access api://x/toegang")
    assert oidc_login._ververs_data("rt")["scope"] == "openid profile offline_access api://x/toegang"


@pytest.mark.parametrize("geheim, verwacht", [("", None), ("s3cr3t", "s3cr3t")])
def test_clientgeheim_alleen_als_gezet(discovery, monkeypatch, geheim, verwacht):
    monkeypatch.setenv("OIDC_CLIENT_SECRET", geheim)
    verstuurd = {}

    def post(url, data=None, **kw):
        verstuurd.update(data)
        return None

    monkeypatch.setattr(oidc_login.httpx, "post", post)
    oidc_login._token_verzoek({"grant_type": "authorization_code", "code": "c"})
    assert verstuurd.get("client_secret") == verwacht
    assert verstuurd["client_id"] == "omnitwin-web"
