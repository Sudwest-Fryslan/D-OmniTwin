"""
Integratietests voor kleine aantallen (#325).

Draait tegen een draaiende stack met de sample dataset (zie test_sample_stack.py).

Wat wordt bewezen: een waarde die op minder waarnemingen rust dan de drempel
(standaard 10, organisatie.n_drempel), wordt nergens getoond en telt niet mee:
- SQL: kleine_aantallen_drempel() en is_kleine_aantallen(n), en de drempel volgt de instelling;
- Z-score: niet in de referentiegroep, geen Z-score voor het doelgebied;
- kaart (modus waarde): geen waarde, wel het gebied met onderdrukt = true, grijs;
- benchmarkrapport: de indicator ontbreekt bij het gebied;
- organisatie-API: n_drempel staat in de instelling (standaard 10).
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
GEBIED = "BU19000002"     # Bolsward-Zuidoost
GEMEENTE = "1900"
BRON = "test #325"


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
    c.autocommit = True
    yield c
    c.close()


@pytest.fixture(scope="module")
def gebiedstype_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT gebiedstype_id::text FROM gebieden WHERE id = %s", (GEBIED,))
        return cur.fetchone()[0]


@pytest.fixture(scope="module")
def indicator(conn):
    """Een actieve indicator met een waarde voor het testgebied en veel buurten in de gemeente."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT v.indicator_uuid::text, i.naam
               FROM vw_gebied_indicator_actueel v
               JOIN gebieden g ON g.id = v.gebied_id
               JOIN indicatoren i ON i.uuid = v.indicator_uuid AND i.is_actief
               WHERE g.gemeente_code = %s
                 AND g.gebiedstype_id = (SELECT gebiedstype_id FROM gebieden WHERE id = %s)
               GROUP BY 1, 2
               HAVING count(DISTINCT v.waarde) >= 8 AND bool_or(v.gebied_id = %s)
               ORDER BY count(*) DESC, 1 LIMIT 1""",
            (GEMEENTE, GEBIED, GEBIED),
        )
        row = cur.fetchone()
    assert row, "geen bruikbare indicator in de sample"
    return row


@pytest.fixture
def kleine_waarde(conn, indicator):
    """Een nieuwe, recentste waarde voor het testgebied met n = 5 (onder de drempel)."""
    uuid, _ = indicator
    with conn.cursor() as cur:
        cur.execute(
            "SELECT max(jaar) FROM gebied_data WHERE indicator_uuid = %s::uuid AND gebied_id = %s",
            (uuid, GEBIED),
        )
        jaar = cur.fetchone()[0] + 1
        cur.execute(
            """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron, n, n_status)
               VALUES (%s, %s::uuid, 987654, %s, 'current', %s, 5, 'gemeten')""",
            (GEBIED, uuid, jaar, BRON),
        )
    yield jaar
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gebied_data WHERE bron = %s", (BRON,))


def test_drempel_in_sql(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT kleine_aantallen_drempel(), is_kleine_aantallen(9), is_kleine_aantallen(10), "
                    "is_kleine_aantallen(NULL)")
        drempel, negen, tien, onbekend = cur.fetchone()
        cur.execute("SELECT n_drempel FROM organisatie LIMIT 1")
        rij = cur.fetchone()
    ingesteld = rij[0] if rij else None
    assert drempel == (ingesteld or 10)
    if ingesteld is None:
        assert negen is True and tien is False
    assert onbekend is False  # zonder bekende n telt een waarde mee


def test_drempel_volgt_instelling(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT n_drempel FROM organisatie LIMIT 1")
        rij = cur.fetchone()
        if rij is None:
            pytest.skip("geen organisatie ingericht")
        oud = rij[0]
        try:
            cur.execute("UPDATE organisatie SET n_drempel = 3")
            cur.execute("SELECT kleine_aantallen_drempel(), is_kleine_aantallen(5)")
            assert cur.fetchone() == (3, False)
        finally:
            cur.execute("UPDATE organisatie SET n_drempel = %s", (oud,))


def test_zscore_zonder_kleine_aantallen(conn, gebiedstype_id, indicator, kleine_waarde):
    uuid, _ = indicator
    with conn.cursor() as cur:
        cur.execute(
            """SELECT count(*) FROM zscore_referentie_waarden(%s::uuid, %s, 'alle_jaren', 'current',
                   ARRAY[%s::uuid], 5) WHERE gebied_id = %s AND jaar = %s""",
            (gebiedstype_id, GEMEENTE, uuid, GEBIED, kleine_waarde),
        )
        assert cur.fetchone()[0] == 0, "waarde met n = 5 zit in de referentiegroep"
        cur.execute(
            """SELECT count(*) FROM zscore_gebieden(ARRAY[%s]::varchar[], %s::uuid, %s, 'zelfde_jaar',
                   'current', ARRAY[%s::uuid])""",
            (GEBIED, gebiedstype_id, GEMEENTE, uuid),
        )
        assert cur.fetchone()[0] == 0, "Z-score op een waarde met n = 5"


def test_kaart_toont_waarde_niet(gebiedstype_id, indicator, kleine_waarde):
    uuid, _ = indicator
    r = requests.get(
        f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{gebiedstype_id}",
        params={"indicator_uuid": uuid, "gemeente_code": GEMEENTE},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    props = d["data"][GEBIED]
    assert props["jaar"] == kleine_waarde
    assert props["indicator_waarde"] is None and props["onderdrukt"] is True
    assert props["color"] == d["metadata"]["nodata_color"]
    assert d["metadata"]["aantal_onderdrukt"] >= 1 and d["metadata"]["n_drempel"] >= 1
    assert 987654 not in [p["indicator_waarde"] for p in d["data"].values()]


def test_benchmark_toont_waarde_niet(indicator, kleine_waarde):
    _, naam = indicator
    r = requests.get(
        f"{BASE_URL}/api/report/benchmark",
        params={"gebied_a": GEBIED, "mode": "gemeente", "referentie_gemeente": GEMEENTE},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    rijen = [v for v in r.json()["vergelijking"] if v["indicator"] == naam]
    assert all(v["waarde_a"] != 987654 for v in rijen)
    assert rijen == []


def test_organisatie_heeft_n_drempel():
    r = requests.get(f"{BASE_URL}/api/organisatie", timeout=TIMEOUT)
    if r.status_code == 404:
        pytest.skip("geen organisatie ingericht")
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["n_drempel"], int)
