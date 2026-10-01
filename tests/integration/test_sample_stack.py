"""
Integratietests voor een verse installatie met de sample dataset (Issue #52).

Draait tegen een draaiende stack (docker compose up) en controleert de
acceptatiecriteria uit #52: app laadt, 12 buurten op de kaart, Kompas-data per
buurt, chat-scenario 'Beleidsadviseur', en idempotent laden van de sample.

Reproduceerbaar draaien, onafhankelijk van de Python-omgeving op de host:

    docker compose down -v && docker compose up -d --build
    docker run --rm --network d-omnitwin_default -v "$PWD":/app -w /app \
        --env-file .env -e DATABASE_HOST=postgres -e DATABASE_PORT=5432 \
        -e OMNITWIN_BASE_URL=http://traefik \
        python:3.11-slim sh -c "pip install -q pytest requests psycopg2-binary python-dotenv \
        && pytest -m integration tests/integration"

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


# ── Security (bekend probleem, zie #57) ──────────────────────────────────────

@pytest.mark.xfail(reason="PostgREST anonieme rol ziet alle tabellen — #57", strict=True)
def test_postgrest_anoniem_geen_toegang_tot_users():
    r = requests.get(f"{BASE_URL}/api/data/users", params={"select": "id", "limit": 1}, timeout=TIMEOUT)
    assert r.status_code in (401, 403, 404)
