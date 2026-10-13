"""
Integratietest: na een geslaagde eerste initialisatie staat de markering (#201).

Draait tegen een draaiende stack, zoals de andere integratietests (zie test_sample_stack.py).
"""

import os

import pytest

pytestmark = pytest.mark.integration


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


def test_installatie_gemarkeerd_als_voltooid(db):
    with db.cursor() as cur:
        cur.execute("SELECT count(*), min(versie) FROM public.installatie_status")
        aantal, versie = cur.fetchone()
    assert aantal == 1
    assert versie


def test_objecten_van_database_gebruiker(db):
    """Alle tabellen in public en app zijn van DATABASE_USER (geen vaste rol omnitwin_user)."""
    with db.cursor() as cur:
        cur.execute("""
            SELECT c.relname, pg_get_userbyid(c.relowner)
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname IN ('public', 'app') AND c.relkind IN ('r', 'v', 'm')
              AND pg_get_userbyid(c.relowner) <> current_user
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                              AND d.objid = c.oid AND d.deptype = 'e')
        """)
        anders = cur.fetchall()
    assert not anders, f"tabellen met een andere eigenaar: {anders}"
