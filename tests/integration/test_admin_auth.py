"""
Integratietests voor de autorisatie van beheerroutes (#65).

Draait tegen een draaiende stack, net als test_sample_stack.py (zie daar hoe je
ze reproduceerbaar draait). Extra nodig: `bcrypt` (voor de testgebruiker).

- elke beheerroute (/api/admin/* behalve inloggen, /api/visualisatie/admin/*)
  geeft zonder login 401;
- met een ingelogde gebruiker zonder is_admin 403;
- met een beheerder 200 (GET-routes zonder parameters; de rest niet-401/403);
- X-Admin-Key met een lege of voorbeeldwaarde wordt geweigerd;
- sessietokens staan gehasht in de database, verlopen sessies worden opgeruimd.

De routes komen uit /openapi.json; een nieuwe beheerroute wordt dus vanzelf
meegetest.
"""

import hashlib
import os
import secrets

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
DUMMY_UUID = "00000000-0000-0000-0000-000000000000"

PUBLIEKE_ADMIN_ROUTES = {"/api/admin/auth/login", "/api/admin/auth/logout", "/api/admin/auth/me"}
# Elke ingelogde gebruiker (ook zonder is_admin) mag zijn eigen wachtwoord wijzigen
EIGEN_ACCOUNT_ROUTES = {"/api/admin/auth/change-password"}
# Moeten in elk geval beveiligd zijn (stonden zonder auth vóór #65)
VERPLICHT_BEVEILIGD = {
    ("GET", "/api/admin/prompts"),
    ("PUT", "/api/admin/prompts/{naam}"),
    ("GET", "/api/admin/llm/config"),
    ("PUT", "/api/admin/llm/config"),
    ("GET", "/api/admin/data-controle/run"),
    ("POST", "/api/admin/data-controle/deduplicatie/merge"),
    ("POST", "/api/admin/data-controle/acties/herbereken-statistieken"),
}
# GET-routes die de beheerder-test overslaat: hangen af van externe diensten
BEHEERDER_GET_OVERSLAAN = {"/api/admin/llm/models"}

PLACEHOLDER_KEYS = ["", "<genereer-met-python-secrets-token-hex-32>", "jouw_admin_api_key",
                    "your_admin_key_here"]


def is_beheerroute(path):
    if path in PUBLIEKE_ADMIN_ROUTES or path in EIGEN_ACCOUNT_ROUTES:
        return False
    return path.startswith("/api/admin/") or path.startswith("/api/visualisatie/admin/")


def vul_in(path):
    """Padparameters vervangen door een geldige maar niet-bestaande waarde."""
    import re
    return re.sub(r"\{[^}]+\}", lambda m: DUMMY_UUID if "uuid" in m.group(0) else "1", path)


@pytest.fixture(scope="module")
def beheerroutes():
    r = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
    r.raise_for_status()
    routes = sorted(
        (method.upper(), path)
        for path, ops in r.json()["paths"].items()
        for method in ops
        if is_beheerroute(path)
    )
    assert routes, "geen beheerroutes in /openapi.json"
    ontbrekend = VERPLICHT_BEVEILIGD - set(routes)
    assert not ontbrekend, f"verwachte beheerroutes ontbreken: {ontbrekend}"
    return routes


@pytest.fixture(scope="module")
def db():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
    )
    conn.autocommit = True
    yield conn
    conn.close()


def doe(sessie, method, path, **kwargs):
    kwargs.setdefault("timeout", TIMEOUT)
    if method in ("POST", "PUT", "PATCH"):
        kwargs.setdefault("json", {})
    return sessie.request(method, f"{BASE_URL}{vul_in(path)}", **kwargs)


def login(username, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/admin/auth/login",
               data={"username": username, "password": password}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    assert s.cookies.get("session_token")
    return s


@pytest.fixture(scope="module")
def gewone_gebruiker(db):
    """Een actieve gebruiker zonder is_admin (kolomdefault)."""
    bcrypt = pytest.importorskip("bcrypt")
    username = f"test65_{secrets.token_hex(4)}"
    password = secrets.token_urlsafe(16)
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with db.cursor() as cur:
        # is_admin bewust niet opgegeven: de kolomdefault moet false zijn
        cur.execute("INSERT INTO users (username, hashed_password, is_active) VALUES (%s, %s, true) RETURNING id",
                    (username, hashed))
        user_id = cur.fetchone()[0]
    yield {"id": user_id, "username": username, "password": password}
    with db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


@pytest.fixture(scope="module")
def beheerder():
    username = os.environ.get("ADMIN_USER", "admin")
    password = os.environ.get("ADMIN_PASSWORD")
    if not password or password.startswith("<"):
        pytest.skip("ADMIN_PASSWORD niet bekend in de testomgeving")
    return login(username, password)


# ── Zonder login: 401 ────────────────────────────────────────────────────────

def test_beheerroutes_zonder_login_401(beheerroutes):
    fout = []
    for method, path in beheerroutes:
        r = doe(requests, method, path)
        if r.status_code != 401:
            fout.append(f"{method} {path} -> {r.status_code}")
    assert not fout, "niet 401 zonder login:\n" + "\n".join(fout)


@pytest.mark.parametrize("key", PLACEHOLDER_KEYS)
def test_x_admin_key_placeholder_of_leeg_geweigerd(beheerroutes, key):
    fout = []
    for method, path in beheerroutes:
        r = doe(requests, method, path, headers={"X-Admin-Key": key})
        if r.status_code != 401:
            fout.append(f"{method} {path} -> {r.status_code}")
    assert not fout, f"X-Admin-Key {key!r} niet geweigerd:\n" + "\n".join(fout)


def test_x_admin_key_geldig_werkt():
    key = os.environ.get("ADMIN_API_KEY", "")
    if len(key) < 32 or key.startswith("<"):
        pytest.skip("geen geldige ADMIN_API_KEY in de testomgeving")
    r = requests.get(f"{BASE_URL}/api/admin/health", headers={"X-Admin-Key": key}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]


# ── Ingelogd zonder is_admin: 403 ────────────────────────────────────────────

def test_is_admin_default_false(db):
    with db.cursor() as cur:
        cur.execute("""SELECT column_default FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'is_admin'""")
        assert cur.fetchone()[0] == "false"


def test_beheerroutes_zonder_is_admin_403(beheerroutes, gewone_gebruiker):
    s = login(gewone_gebruiker["username"], gewone_gebruiker["password"])
    me = s.get(f"{BASE_URL}/api/admin/auth/me", timeout=TIMEOUT).json()
    assert me["authenticated"] and me["user"]["is_admin"] is False
    fout = []
    for method, path in beheerroutes:
        r = doe(s, method, path)
        if r.status_code != 403:
            fout.append(f"{method} {path} -> {r.status_code}")
    assert not fout, "niet 403 voor gebruiker zonder is_admin:\n" + "\n".join(fout)


# ── Beheerder: 200 ───────────────────────────────────────────────────────────

def test_beheerroutes_met_beheerder(beheerroutes, beheerder):
    fout = []
    for method, path in beheerroutes:
        if method != "GET" or "{" in path or path in BEHEERDER_GET_OVERSLAAN:
            continue
        r = doe(beheerder, method, path)
        if r.status_code != 200:
            fout.append(f"{method} {path} -> {r.status_code}: {r.text[:120]}")
    assert not fout, "beheerder krijgt geen 200:\n" + "\n".join(fout)


def test_beheerder_niet_geweigerd_op_routes_met_parameters(beheerroutes, beheerder):
    """Alleen lezen: GET-routes met padparameters mogen 404 geven, geen 401/403."""
    fout = []
    for method, path in beheerroutes:
        if method != "GET" or "{" not in path:
            continue
        r = doe(beheerder, method, path)
        if r.status_code in (401, 403):
            fout.append(f"{method} {path} -> {r.status_code}")
    assert not fout, "\n".join(fout)


# ── Sessies ──────────────────────────────────────────────────────────────────

def test_sessietoken_gehasht_opgeslagen(db, gewone_gebruiker):
    s = login(gewone_gebruiker["username"], gewone_gebruiker["password"])
    token = s.cookies.get("session_token")
    with db.cursor() as cur:
        cur.execute("SELECT count(*) FROM sessions WHERE token_hash = %s", (token,))
        assert cur.fetchone()[0] == 0, "ruw token staat in de database"
        cur.execute("SELECT count(*) FROM sessions WHERE token_hash = %s",
                    (hashlib.sha256(token.encode()).hexdigest(),))
        assert cur.fetchone()[0] == 1


def test_uitloggen_verwijdert_sessie(db, gewone_gebruiker):
    s = login(gewone_gebruiker["username"], gewone_gebruiker["password"])
    token_hash = hashlib.sha256(s.cookies.get("session_token").encode()).hexdigest()
    s.post(f"{BASE_URL}/api/admin/auth/logout", timeout=TIMEOUT)
    with db.cursor() as cur:
        cur.execute("SELECT count(*) FROM sessions WHERE token_hash = %s", (token_hash,))
        assert cur.fetchone()[0] == 0


def test_verlopen_sessies_opgeruimd_bij_inloggen(db, gewone_gebruiker):
    verlopen = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
    with db.cursor() as cur:
        cur.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, NOW() - interval '1 hour')",
                    (verlopen, gewone_gebruiker["id"]))
    login(gewone_gebruiker["username"], gewone_gebruiker["password"])
    with db.cursor() as cur:
        cur.execute("SELECT count(*) FROM sessions WHERE expires_at <= NOW()")
        assert cur.fetchone()[0] == 0


# ── Rapporten: publiek, maar niet meer dan de publieke app toont ────────────

BEHEERVELDEN = ("admin_notes", "gevalideerd_door", "gevalideerd_op", "ontologie_status",
                "ontologie_beoordeeld", "system_prompt", "user_prompt", "debug_info", "api_url")


def test_rapportdata_publiek_zonder_beheervelden(buurten_ids):
    for url in (f"/api/report/data/{buurten_ids[0]}",
                f"/api/report/executive/{buurten_ids[0]}",
                f"/api/report/benchmark?gebied_a={buurten_ids[0]}&mode=gebieden&gebieden_b={buurten_ids[1]}"):
        r = requests.get(f"{BASE_URL}{url}", timeout=TIMEOUT)
        assert r.status_code == 200, f"{url}: {r.status_code} {r.text[:200]}"
        gevonden = [v for v in BEHEERVELDEN if v in r.text]
        assert not gevonden, f"{url} bevat beheervelden: {gevonden}"


@pytest.fixture(scope="module")
def buurten_ids(db):
    with db.cursor() as cur:
        cur.execute("""SELECT DISTINCT gd.gebied_id FROM gebied_data gd
                       JOIN gebieden g ON g.id = gd.gebied_id
                       JOIN gebiedstypes gt ON gt.id = g.gebiedstype_id
                       WHERE gd.gebied_id LIKE 'BU%%' ORDER BY 1 LIMIT 2""")
        ids = [r[0] for r in cur.fetchall()]
    if len(ids) < 2:
        pytest.skip("geen sample-buurten met data")
    return ids
