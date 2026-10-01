"""
Integratietests voor een verse installatie met de sample dataset (Issue #52).

Draait tegen een draaiende stack (docker compose up) en controleert de
acceptatiecriteria uit #52: app laadt, 12 buurten op de kaart, Kompas-data per
buurt, chat-scenario 'Beleidsadviseur', en idempotent laden van de sample.

Reproduceerbaar draaien, onafhankelijk van de Python-omgeving op de host:

    docker compose down -v && docker compose up -d --build --wait
    docker run --rm --network d-omnitwin_default -v "$PWD":/app -w /app \
        --env-file .env -e DATABASE_HOST=postgres -e DATABASE_PORT=5432 \
        -e OMNITWIN_BASE_URL=http://traefik \
        python:3.11-slim sh -c "pip install -q pytest requests psycopg2-binary python-dotenv \
        && pytest -m integration tests/integration"

Het netwerk heet <projectnaam>_default: d-omnitwin_default, of bij een eigen
COMPOSE_PROJECT_NAME die naam + _default. CI (.github/workflows/ci.yml, job
integration) draait precies dit met COMPOSE_PROJECT_NAME=omnitwin-ci.

Omgevingsvariabelen:
    OMNITWIN_BASE_URL   basis-URL via Traefik (standaard http://localhost)
    DATABASE_*          databaseverbinding voor de schema- en idempotentietests
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
SAMPLE_GEOJSON = ROOT / "init_data" / "sample" / "2_brondata" / "sample_buurten.geojson"
TIMEOUT = 30


def sample_buurt_namen():
    with open(SAMPLE_GEOJSON, encoding="utf-8") as f:
        return {feat["properties"]["naam"] for feat in json.load(f)["features"]}


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


def scalar(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


@pytest.fixture(scope="module")
def buurten():
    """Buurten zoals de frontend ze ophaalt: via pg_featureserv."""
    r = requests.get(
        f"{BASE_URL}/api/geo/collections/public.vw_gebieden_features/items",
        params={"limit": 1000, "properties": "id,naam,gebiedstype_id"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["features"]


# ── 1. App laadt ─────────────────────────────────────────────────────────────

def test_app_laadt():
    r = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "D-OmniTwin" in r.text


# ── 2. Kaart toont de 12 SWF-buurten ─────────────────────────────────────────

def test_kaart_toont_sample_buurten(buurten):
    namen = {f["properties"]["naam"] for f in buurten}
    assert namen == sample_buurt_namen()


def test_buurten_hebben_geometrie(buurten):
    assert all(f.get("geometry") for f in buurten)


# ── 3. Buurt aanklikken toont Kompas-data ────────────────────────────────────

def test_kompas_data_voor_buurt(buurten):
    configs = requests.get(f"{BASE_URL}/api/kompas/configuraties", timeout=TIMEOUT)
    configs.raise_for_status()
    body = configs.json()
    lijst = body.get("configuraties", body) if isinstance(body, dict) else body
    assert lijst, "geen Kompas-configuraties gevonden"
    config_id = lijst[0]["id"]

    gebied_id = buurten[0]["properties"]["id"]
    r = requests.get(f"{BASE_URL}/api/kompas/{config_id}/gebied/{gebied_id}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["hierarchie"]
    assert data["coverage_percentage"] > 0


# ── 4. Chat-scenario 'Beleidsadviseur' ───────────────────────────────────────

def test_chat_scenario_beleidsadviseur():
    r = requests.post(f"{BASE_URL}/api/chat", json={"vraag": "Ik ben beleidsadviseur"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    acties = r.json()["acties"]
    types = {a["type"] for a in acties}
    assert {"SELECTEER_GEBIEDSTYPE", "SELECTEER_GEMEENTE", "OPEN_KOMPAS"} <= types
    assert any(a["type"] == "SELECTEER_GEMEENTE" and a.get("gemeente_code") == "1900" for a in acties)


# ── AI-zoeken: embeddings na verse installatie (#139) ────────────────────────

def test_embeddings_voor_alle_actieve_indicatoren(db):
    zonder = scalar(db, """
        SELECT count(*) FROM indicatoren i
        LEFT JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
        WHERE i.is_actief AND e.id IS NULL
    """)
    assert scalar(db, "SELECT count(*) FROM indicator_embeddings") > 0
    assert zonder == 0


def test_embeddingmodel_lokaal_en_offline():
    # #118: het model staat in de image (gepinde revisie) en de backend draait offline,
    # dus AI-zoeken (test hieronder) werkt zonder toegang tot huggingface.co
    r = requests.get(f"{BASE_URL}/api/ai/health", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    model = r.json()["embedding_model"]
    assert model["lokaal"], model
    assert model["offline"], model
    assert len(model["revisie"]) == 40, model


def test_ai_zoeken_vindt_concept_indicator():
    # De eerste zoekvraag laadt het model in de backend; ruime timeout
    r = requests.get(f"{BASE_URL}/api/ai/kompas/search", params={"q": "koele plek"}, timeout=300)
    assert r.status_code == 200, r.text[:300]
    resultaten = r.json()
    assert resultaten and "error" not in resultaten[0], resultaten
    treffer = next((x for x in resultaten if x["naam"] == "Afstand tot koele plek"), None)
    assert treffer, [x["naam"] for x in resultaten]
    assert "ontologie_status" in treffer and "gevalideerd" in treffer


# ── 5. load_sample.py is idempotent ──────────────────────────────────────────

TELLINGEN = {
    "gebieden": "SELECT count(*) FROM gebieden",
    "indicatoren": "SELECT count(*) FROM indicatoren",
    "gebied_data": "SELECT count(*) FROM gebied_data",
}


def test_load_sample_idempotent(db):
    voor = {k: scalar(db, q) for k, q in TELLINGEN.items()}
    result = subprocess.run(
        [sys.executable, str(ROOT / "init_data" / "scripts" / "load_sample.py"), "--stap", "alle"],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    na = {k: scalar(db, q) for k, q in TELLINGEN.items()}
    assert voor == na


# ── Schema compleet: migraties v18/v19 worden bij init geladen (#52, structureel #54) ──

def test_schema_bevat_alle_migraties(db):
    assert scalar(db, "SELECT count(*) FROM pg_extension WHERE extname = 'pg_trgm'") == 1
    assert scalar(db, "SELECT to_regclass('public.deduplicatie_uitzonderingen') IS NOT NULL")


# ── Security: PostgREST en pg_featureserv met eigen rollen (#57) ─────────────
#
# PostgREST ziet alleen schema api (views en functies) en draait anoniem als web_anon
# (alleen lezen). pg_featureserv draait als featureserv (alleen de geo-views).

# Wat de frontend, de admin en de tests via /api/data gebruiken; zie db/migraties/R__api_rollen.sql
API_WHITELIST = [
    "gemeenten",
    "gebiedstypes",
    "gebieden",
    "externe_kaartlagen",
    "indicatoren",
    "vw_gebied_indicator_actueel",
    "rpc/get_indicatoren_stats",
]

# Applicatiedata: nooit via PostgREST
GEHEIM = ["users", "sessions", "api_keys", "llm_config", "system_prompts", "app_logs", "log_config"]


def test_postgrest_anoniem_geen_toegang_tot_users():
    r = requests.get(f"{BASE_URL}/api/data/users", params={"select": "id", "limit": 1}, timeout=TIMEOUT)
    assert r.status_code in (401, 403, 404)


@pytest.mark.parametrize("tabel", GEHEIM)
def test_postgrest_anoniem_geen_applicatiedata(tabel):
    r = requests.get(f"{BASE_URL}/api/data/{tabel}", params={"limit": 1}, timeout=TIMEOUT)
    assert r.status_code in (401, 404), f"{tabel}: HTTP {r.status_code}"


@pytest.mark.parametrize("pad", API_WHITELIST)
def test_postgrest_whitelist_leesbaar(pad):
    params = {} if pad.startswith("rpc/") else {"limit": 1}
    r = requests.get(f"{BASE_URL}/api/data/{pad}", params=params, timeout=TIMEOUT)
    assert r.status_code == 200, f"{pad}: HTTP {r.status_code} {r.text[:200]}"
    assert isinstance(r.json(), list)


def test_postgrest_toont_alleen_whitelist():
    """De OpenAPI-beschrijving van PostgREST noemt alleen de objecten uit schema api."""
    r = requests.get(f"{BASE_URL}/api/data/", timeout=TIMEOUT)
    assert r.status_code == 200
    paden = {p.strip("/") for p in r.json().get("paths", {})} - {""}
    assert paden == set(API_WHITELIST)


@pytest.mark.parametrize("methode,pad,body", [
    ("POST", "gemeenten", {"code": "9999", "naam": "Test", "provincie": "Test"}),
    ("POST", "indicatoren", {"naam": "test-57"}),
    ("PATCH", "gemeenten?code=eq.1900", {"naam": "Gehackt"}),
    ("PATCH", "indicatoren?id=gt.0", {"naam": "Gehackt"}),
    ("DELETE", "gebieden?id=eq.BU19000002", None),
    ("DELETE", "externe_kaartlagen?id=gt.0", None),
    ("POST", "users", {"username": "x"}),
    ("PATCH", "users?id=not.is.null", {"is_active": False}),
    ("DELETE", "sessions?token=not.is.null", None),
])
def test_postgrest_anoniem_kan_niet_schrijven(methode, pad, body):
    r = requests.request(methode, f"{BASE_URL}/api/data/{pad}", json=body, timeout=TIMEOUT)
    assert r.status_code in (401, 403, 404, 405), f"{methode} {pad}: HTTP {r.status_code}"


def test_postgrest_schrijfpoging_verandert_niets(db):
    voor = scalar(db, "SELECT naam FROM gemeenten WHERE code = '1900'")
    requests.patch(f"{BASE_URL}/api/data/gemeenten", params={"code": "eq.1900"},
                   json={"naam": "Gehackt"}, timeout=TIMEOUT)
    assert scalar(db, "SELECT naam FROM gemeenten WHERE code = '1900'") == voor


@pytest.mark.parametrize("functie", [
    "update_updated_at_column",
    "update_gebied_centroid",
    "postgis_full_version",
    "st_asgeojson",
])
def test_postgrest_rpc_buiten_whitelist(functie):
    r = requests.post(f"{BASE_URL}/api/data/rpc/{functie}", json={}, timeout=TIMEOUT)
    assert r.status_code in (401, 404), f"{functie}: HTTP {r.status_code}"


def test_featureserv_alleen_geo_views():
    r = requests.get(f"{BASE_URL}/api/geo/collections", timeout=TIMEOUT)
    r.raise_for_status()
    ids = {c["id"] for c in r.json()["collections"]}
    assert ids == {"public.vw_gebieden_features", "public.omgevingsvisie_deelgebieden"}
    r = requests.get(f"{BASE_URL}/api/geo/collections/public.gebieden/items", params={"limit": 1}, timeout=TIMEOUT)
    assert r.status_code == 404


def test_featureserv_functie_buurten_in_deelgebied():
    r = requests.get(f"{BASE_URL}/api/geo/functions/postgisftw.buurten_in_deelgebied/items",
                     params={"deelgebied_id": 1}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]


ROL_ATTRIBUTEN = """
    SELECT rolsuper, rolinherit, rolcanlogin, rolcreaterole, rolcreatedb, rolbypassrls
    FROM pg_roles WHERE rolname = %s
"""


def test_rollen_zonder_extra_rechten(db):
    with db.cursor() as cur:
        cur.execute(ROL_ATTRIBUTEN, ("authenticator",))
        assert cur.fetchone() == (False, False, True, False, False, False)
        cur.execute(ROL_ATTRIBUTEN, ("web_anon",))
        assert cur.fetchone() == (False, True, False, False, False, False)
        cur.execute(ROL_ATTRIBUTEN, ("featureserv",))
        assert cur.fetchone()[0] is False


@pytest.mark.parametrize("rol", ["web_anon", "authenticator", "featureserv"])
@pytest.mark.parametrize("tabel", GEHEIM + ["gebieden", "indicatoren", "gebied_data"])
def test_rollen_geen_rechten_op_tabellen(db, rol, tabel):
    """Geen enkele API-rol heeft rechten op de tabellen in public; alleen via views."""
    for recht in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        heeft = scalar(db, "SELECT has_table_privilege(%s, %s, %s)", (rol, f"public.{tabel}", recht))
        assert not heeft, f"{rol} heeft {recht} op {tabel}"
