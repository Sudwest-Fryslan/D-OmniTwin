"""
Trends uit de CBS Kerncijfers (#159): na een verse installatie met LOAD_SAMPLE_DATA=true
heeft Bolsward-Noord meerdere jaren per CBS-indicator, en telt "Trending (5j+)" mee.

Draaien: zie tests/integration/test_sample_stack.py (zelfde stack en omgeving).
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30
BOLSWARD_NOORD = "BU19000001"
INWONERS = "31f70dff-c116-4267-bef0-d15b0ff4c020"


def history(indicator_uuid, gebied=BOLSWARD_NOORD):
    r = requests.get(f"{BASE_URL}/api/kompas/1/history/{gebied}/{indicator_uuid}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _uuid_65_plus():
    """Zelfde uuid5 als laad_usecase.py en download_cbs_kerncijfers.py."""
    import uuid
    return str(uuid.uuid5(uuid.UUID("6f1d3c2a-0b7e-4c8e-9a51-d0a1b2c3e4f5"), "65+ jaar (%)"))


@pytest.mark.parametrize("indicator_uuid", [INWONERS, _uuid_65_plus()], ids=["Inwoners", "65+ jaar (%)"])
def test_history_heeft_minstens_drie_jaren(indicator_uuid):
    data = history(indicator_uuid)
    punten = data["history"]
    jaren = [p["jaar"] for p in punten]
    assert len(set(jaren)) >= 3, f"te weinig jaren: {jaren}"
    assert jaren == sorted(jaren)
    assert all(p["bron"].startswith("CBS Kerncijfers wijken en buurten") for p in punten), punten


def test_history_jaar_is_peiljaar():
    """85039NED (2021) stond als 2023; de tabel van 2023 (85618NED) geeft 1.920 inwoners."""
    punten = {p["jaar"]: p for p in history(INWONERS)["history"]}
    assert punten[2023]["waarde"] == 1920
    assert "85618NED" in punten[2023]["bron"]
    assert punten[2021]["waarde"] == 1770 and "85039NED" in punten[2021]["bron"]


def test_trending_vijf_jaar_of_meer():
    """Dezelfde telling als routers/dashboard.py ('Trending (5j+)')."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(host=os.environ.get("DATABASE_HOST", "localhost"),
                            port=int(os.environ.get("DATABASE_PORT", 5432)),
                            dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
                            user=os.environ.get("DATABASE_USER", "omnitwin_user"),
                            password=os.environ.get("DATABASE_PASSWORD", ""))
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM (SELECT indicator_uuid FROM gebied_data WHERE jaar IS NOT NULL
                           GROUP BY indicator_uuid HAVING COUNT(DISTINCT jaar) >= 5) s""")
            assert cur.fetchone()[0] > 0
            cur.execute("SELECT metadata->>'bron_tabel' FROM gebied_data WHERE gebied_id = %s "
                        "AND indicator_uuid = %s AND jaar = 2024", (BOLSWARD_NOORD, INWONERS))
            assert cur.fetchone()[0] == "85984NED"
    finally:
        conn.close()
