"""
Integratietests voor vw_gebied_indicator_actueel (#159, migratie V030).

Draait tegen een draaiende stack met de sample dataset (zie
test_sample_stack.py). Elke test voegt rijen toe in een eigen transactie en
draait die daarna terug.

Wat wordt bewezen:
- een projectie (scenario_id <> 'current') met een later jaar telt niet als actueel;
- een rij zonder jaar (alleen datum) gaat niet vóór een rij met een jaar (NULLS LAST);
- scenario_id NULL telt als 'current';
- de api-view (PostgREST) volgt de publieke view.
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
GEBIED = "BU19000002"  # Bolsward-Zuidoost


@pytest.fixture(scope="module")
def conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
    )
    yield c
    c.rollback()
    c.close()


@pytest.fixture(scope="module")
def actueel(conn):
    """Een indicator met een gerealiseerde waarde voor het testgebied: (uuid, waarde, jaar)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT indicator_uuid::text, waarde, jaar FROM vw_gebied_indicator_actueel
               WHERE gebied_id = %s AND jaar IS NOT NULL ORDER BY indicator_uuid LIMIT 1""",
            (GEBIED,),
        )
        row = cur.fetchone()
    conn.rollback()
    assert row, f"geen actuele waarde voor {GEBIED} in de sample"
    return row


def lees_actueel(cur, uuid):
    cur.execute(
        """SELECT waarde, jaar FROM vw_gebied_indicator_actueel
           WHERE gebied_id = %s AND indicator_uuid = %s::uuid""",
        (GEBIED, uuid),
    )
    rijen = cur.fetchall()
    assert len(rijen) == 1
    return rijen[0]


def test_v030_toegepast(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM schema_migraties WHERE versie = 30")
        assert cur.fetchone(), "migratie V030 is niet toegepast"
    conn.rollback()


def test_projectie_telt_niet_als_actueel(conn, actueel):
    uuid, waarde, jaar = actueel
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                   VALUES (%s, %s::uuid, %s, %s, '2050', 'test #159')""",
                (GEBIED, uuid, float(waarde) * 100 + 1000, jaar + 30),
            )
            assert lees_actueel(cur, uuid) == (waarde, jaar)
    finally:
        conn.rollback()


def test_rij_zonder_jaar_gaat_niet_voor(conn, actueel):
    uuid, waarde, jaar = actueel
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, datum, scenario_id, bron)
                   VALUES (%s, %s::uuid, -12345, NULL, DATE '1990-01-01', 'current', 'test #159')""",
                (GEBIED, uuid),
            )
            assert lees_actueel(cur, uuid) == (waarde, jaar)
    finally:
        conn.rollback()


def test_scenario_null_telt_als_current(conn, actueel):
    uuid, waarde, jaar = actueel
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                   VALUES (%s, %s::uuid, -54321, %s, NULL, 'test #159')""",
                (GEBIED, uuid, jaar + 1),
            )
            assert lees_actueel(cur, uuid) == (-54321, jaar + 1)
    finally:
        conn.rollback()


def test_api_view_volgt_publieke_view(conn, actueel):
    uuid, waarde, jaar = actueel
    r = requests.get(
        f"{BASE_URL}/api/data/vw_gebied_indicator_actueel",
        params={"gebied_id": f"eq.{GEBIED}", "indicator_uuid": f"eq.{uuid}", "select": "waarde,jaar"},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.json() == [{"waarde": float(waarde), "jaar": jaar}]
