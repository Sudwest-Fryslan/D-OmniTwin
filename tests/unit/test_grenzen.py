"""Rate limiting (#203): inloggen per IP + gebruiker, LLM-routes per IP."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from omnitwin import grenzen
from omnitwin.grenzen import Limiet, beperk_llm, client_ip

pytestmark = pytest.mark.unit


class Klok:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_limiet_schuivend_venster():
    klok = Klok()
    limiet = Limiet(3, 60, klok=klok)
    assert [limiet.probeer("a") for _ in range(3)] == [0, 0, 0]
    assert limiet.probeer("a") == 60          # vol: wachten tot de oudste verloopt
    assert limiet.probeer("b") == 0           # andere sleutel telt apart
    klok.t += 30
    assert limiet.wachttijd("a") == 30
    klok.t += 30
    assert limiet.wachttijd("a") == 0         # oudste is verlopen
    limiet.registreer("a")
    limiet.reset("a")
    assert limiet.wachttijd("a") == 0


def test_limiet_ruimt_verlopen_sleutels_op():
    klok = Klok()
    limiet = Limiet(1, 10, klok=klok)
    limiet.MAX_SLEUTELS = 5
    for i in range(6):
        limiet.registreer(f"ip{i}")
    klok.t += 11
    limiet.registreer("nieuw")
    assert set(limiet._tijden) == {"nieuw"}


def _verzoek(client, headers=None):
    return Request({
        "type": "http", "scheme": "http", "method": "GET", "path": "/", "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "server": ("testserver", 80), "client": (client, 1234),
    })


def test_client_ip():
    # Direct van buiten: X-Forwarded-For wordt genegeerd (vervalsbaar)
    assert client_ip(_verzoek("8.8.8.8", {"X-Forwarded-For": "10.9.9.9"})) == "8.8.8.8"
    # Via Traefik (privé-adres): het laatste adres in X-Forwarded-For
    assert client_ip(_verzoek("172.18.0.3", {"X-Forwarded-For": "1.2.3.4, 198.51.100.7"})) == "198.51.100.7"
    assert client_ip(_verzoek("172.18.0.3")) == "172.18.0.3"


def test_llm_limiet_geeft_429_met_retry_after(monkeypatch):
    monkeypatch.setenv("LLM_RATE_LIMIT", "3")
    grenzen._llm_limieten.clear()
    app = FastAPI()

    @app.post("/api/chat", dependencies=[Depends(beperk_llm)])
    def chat():
        return {"ok": True}

    client = TestClient(app)
    assert [client.post("/api/chat").status_code for _ in range(3)] == [200, 200, 200]
    r = client.post("/api/chat")
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 60


def test_llm_limiet_uit_met_nul(monkeypatch):
    monkeypatch.setenv("LLM_RATE_LIMIT", "0")
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(beperk_llm)])
    def x():
        return {}

    client = TestClient(app)
    assert all(client.get("/x").status_code == 200 for _ in range(100))


# ── Inloggen ──────────────────────────────────────────────────────────────────

class _Resultaat:
    def __init__(self, rij=None):
        self._rij = rij

    def fetchone(self):
        return self._rij


class _NepDatabase:
    """Kent alleen gebruiker 'admin' met wachtwoord 'goed'."""

    def __init__(self, hash_):
        self.hash = hash_

    def execute(self, stmt, params=None):
        if params and params.get("username") == "admin":
            return _Resultaat(("id-1", "admin", self.hash, True))
        return _Resultaat()

    def commit(self):
        pass


@pytest.fixture
def login_client(monkeypatch):
    from omnitwin.database import get_db
    from omnitwin.routers import auth

    monkeypatch.setattr(auth, "_mislukt_per_gebruiker", Limiet(5, 900))
    monkeypatch.setattr(auth, "_mislukt_per_ip", Limiet(20, 900))
    monkeypatch.setattr(auth, "LOGIN_VERTRAGING_SECONDEN", 0)
    db = _NepDatabase(auth.get_password_hash("goed"))
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _login(client, gebruiker, wachtwoord):
    return client.post("/api/admin/auth/login", data={"username": gebruiker, "password": wachtwoord})


def test_login_na_vijf_fouten_429_ook_met_goed_wachtwoord(login_client):
    codes = [_login(login_client, "admin", "fout").status_code for _ in range(5)]
    assert codes == [401] * 5
    r = _login(login_client, "admin", "goed")
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0


def test_login_geslaagd_zet_teller_terug(login_client):
    for _ in range(4):
        assert _login(login_client, "admin", "fout").status_code == 401
    r = _login(login_client, "admin", "goed")
    assert r.status_code == 200 and "session_token" in r.cookies
    assert "secure" not in r.headers["set-cookie"].lower()  # http + COOKIE_SECURE=auto
    assert _login(login_client, "admin", "fout").status_code == 401


def test_login_per_ip_over_gebruikersnamen_heen(login_client):
    codes = [_login(login_client, f"gebruiker{i}", "fout").status_code for i in range(21)]
    assert codes[:20] == [401] * 20 and codes[20] == 429
