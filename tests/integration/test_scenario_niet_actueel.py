"""
Projecties tellen nergens als actuele waarde of als historie (#159).

Een waarde met een ander scenario dan 'current' (bijvoorbeeld een projectie voor 2050) is geen
meting. Hij mag niet de recentste waarde worden in de actuele view, in de gebiedsdetails of in
de tijdreeks van het Kompas.

Draaien: zie tests/integration/test_sample_stack.py (zelfde stack en omgeving).
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
GEBIED = "BU19000001"                                # Bolsward-Noord
INWONERS = "31f70dff-c116-4267-bef0-d15b0ff4c020"
BRON = "test #159 projectie"
JAAR = 2050
WAARDE = 987654


@pytest.fixture(scope="module")
def projectie():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(host=os.environ.get("DATABASE_HOST", "localhost"),
                            port=int(os.environ.get("DATABASE_PORT", 5432)),
                            dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
                            user=os.environ.get("DATABASE_USER", "omnitwin_user"),
                            password=os.environ.get("DATABASE_PASSWORD", ""))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                       VALUES (%s, %s::uuid, %s, %s, '2050', %s)""", (GEBIED, INWONERS, WAARDE, JAAR, BRON))
    yield conn
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gebied_data WHERE bron = %s", (BRON,))
    conn.close()


def test_actuele_view(projectie):
    with projectie.cursor() as cur:
        cur.execute("SELECT waarde, jaar FROM vw_gebied_indicator_actueel "
                    "WHERE gebied_id = %s AND indicator_uuid = %s::uuid", (GEBIED, INWONERS))
        waarde, jaar = cur.fetchone()
    assert jaar != JAAR and float(waarde) != WAARDE


def test_gebiedsdetails(projectie):
    r = requests.get(f"{BASE_URL}/api/gebiedsmonitor/gebieden/{GEBIED}", timeout=TIMEOUT)
    r.raise_for_status()
    inwoners = [i for i in r.json()["indicatoren"] if str(i.get("uuid")) == INWONERS]
    assert inwoners, "Inwoners ontbreekt in de gebiedsdetails"
    assert inwoners[0]["jaar"] != JAAR and inwoners[0]["waarde"] != WAARDE


def test_kompas_historie(projectie):
    r = requests.get(f"{BASE_URL}/api/kompas/1/history/{GEBIED}/{INWONERS}", timeout=TIMEOUT)
    r.raise_for_status()
    jaren = [p["jaar"] for p in r.json()["history"]]
    assert jaren and JAAR not in jaren
