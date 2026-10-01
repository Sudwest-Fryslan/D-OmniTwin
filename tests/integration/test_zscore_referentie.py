"""
Integratietests voor de Z-score-referentie (#66).

Draait tegen een draaiende stack met de sample dataset, net als
test_sample_stack.py (zie daar hoe je ze reproduceerbaar draait).

Wat wordt bewezen:
- de SQL-functies uit init_data/schema/08_zscore_referentie.sql bestaan;
- een waterbuurt met extreme waarden, in dezelfde gemeente en hetzelfde
  gebiedstype, verandert gemiddelde, standaarddeviatie en n van de
  referentie niet (eigen testtransactie, daarna rollback);
- een scenario-rij (geen 'current') telt niet mee;
- de SQL-formule zscore() en de Python-tegenhanger rekenen gelijk;
- twee rapportroutes geven voor hetzelfde gebied en dezelfde indicator
  dezelfde Z-score, ook als er een waterbuurt in de database staat.
"""

import os

import pytest
import requests

from services.zscore_referentie import bereken_zscore

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60

GEBIED = "BU19000002"          # Bolsward-Zuidoost
GEBIED_2 = "BU19000200"        # Workum
GEMEENTE = "1900"
WATERBUURT = "BU1900T066"      # bestaat niet in de sample; wordt opgeruimd


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
def gebiedstype_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT gebiedstype_id FROM gebieden WHERE id = %s", (GEBIED,))
        row = cur.fetchone()
    conn.rollback()
    assert row, f"{GEBIED} ontbreekt in de sample"
    return str(row[0])


def referentie_stats(cur, gebiedstype_id):
    cur.execute(
        """SELECT indicator_uuid::text, gemiddelde, standaarddeviatie, n
           FROM zscore_referentie_stats(%s::uuid, %s)""",
        (gebiedstype_id, GEMEENTE),
    )
    return {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}


def voeg_waterbuurt_toe(cur, gebiedstype_id, water=True):
    """Waterbuurt (of gewone buurt) met extreme waarden voor alle indicatoren."""
    metadata = '{"water": "JA"}' if water else '{}'
    cur.execute(
        """INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, metadata, actief)
           VALUES (%s, %s::uuid, 'Testwaterbuurt #66', %s, %s::jsonb, true)""",
        (WATERBUURT, gebiedstype_id, GEMEENTE, metadata),
    )
    cur.execute(
        """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
           SELECT %s, gd.indicator_uuid, MAX(gd.waarde) * 100 + 1000, MAX(gd.jaar), 'current', 'test #66'
           FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
           WHERE g.gemeente_code = %s
           GROUP BY gd.indicator_uuid""",
        (WATERBUURT, GEMEENTE),
    )


def ruim_waterbuurt_op(conn):
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gebied_data WHERE gebied_id = %s", (WATERBUURT,))
        cur.execute("DELETE FROM gebieden WHERE id = %s", (WATERBUURT,))
    conn.commit()


# ── Schema ───────────────────────────────────────────────────────────────────

def test_referentiefuncties_bestaan(conn):
    with conn.cursor() as cur:
        for f in ("zscore_referentie_waarden", "zscore_referentie_stats", "zscore", "zscore_gebieden"):
            cur.execute("SELECT count(*) FROM pg_proc WHERE proname = %s", (f,))
            assert cur.fetchone()[0] >= 1, f"functie {f} ontbreekt"
    conn.rollback()


# ── Waterbuurten en scenario's ───────────────────────────────────────────────

def test_waterbuurt_verandert_referentie_niet(conn, gebiedstype_id):
    try:
        with conn.cursor() as cur:
            voor = referentie_stats(cur, gebiedstype_id)
            assert voor, "geen referentiestatistiek voor de sample"
            voeg_waterbuurt_toe(cur, gebiedstype_id, water=True)
            na = referentie_stats(cur, gebiedstype_id)
        assert na == voor
    finally:
        conn.rollback()


def test_zelfde_buurt_zonder_waterlabel_verandert_referentie_wel(conn, gebiedstype_id):
    """Controle op de test hierboven: zonder waterlabel telt de buurt wel mee."""
    try:
        with conn.cursor() as cur:
            voor = referentie_stats(cur, gebiedstype_id)
            voeg_waterbuurt_toe(cur, gebiedstype_id, water=False)
            na = referentie_stats(cur, gebiedstype_id)
        assert na != voor
        assert all(na[k][2] == voor[k][2] + 1 for k in voor)  # n telt één gebied meer
    finally:
        conn.rollback()


def test_scenario_telt_niet_mee(conn, gebiedstype_id):
    try:
        with conn.cursor() as cur:
            voor = referentie_stats(cur, gebiedstype_id)
            cur.execute(
                """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                   SELECT gebied_id, indicator_uuid, waarde * 100 + 1000, 2099, '2050', 'test #66'
                   FROM gebied_data WHERE gebied_id = %s""",
                (GEBIED_2,),
            )
            na = referentie_stats(cur, gebiedstype_id)
        assert na == voor
    finally:
        conn.rollback()


# ── Formule en randgevallen ──────────────────────────────────────────────────

@pytest.mark.parametrize("waarde,gem,sd,n", [
    (12, 10, 2, 5),
    (8, 10, 2, 5),
    (10, 10, 2, 2),
    (15, 10, 0, 5),      # sd = 0
    (15, 15, None, 1),   # n < 2
    (15, 10, 2, 1),      # n < 2
])
def test_sql_en_python_formule_gelijk(conn, waarde, gem, sd, n):
    with conn.cursor() as cur:
        cur.execute("SELECT zscore(%s::numeric, %s::numeric, %s::numeric, %s)", (waarde, gem, sd, n))
        sql = cur.fetchone()[0]
    conn.rollback()
    py = bereken_zscore(waarde, gem, sd, n)
    if py is None:
        assert sql is None
    else:
        assert float(sql) == pytest.approx(py)


def test_zscore_gebieden_volgt_formule(conn, gebiedstype_id):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT waarde, gemiddelde, standaarddeviatie, n, z_score
               FROM zscore_gebieden(ARRAY[%s]::varchar[], %s::uuid, %s)""",
            (GEBIED, gebiedstype_id, GEMEENTE),
        )
        rows = cur.fetchall()
    conn.rollback()
    assert rows
    for waarde, gem, sd, n, z in rows:
        verwacht = bereken_zscore(float(waarde), float(gem), float(sd) if sd is not None else None, n)
        assert (z is None) == (verwacht is None)
        if z is not None:
            assert float(z) == pytest.approx(verwacht)


def test_zelfde_jaar_als_doelgebied(conn, gebiedstype_id):
    """Standaard jaarlogica: referentie = alle niet-waterbuurten met een waarde in het
    meetjaar van het doelgebied (onafhankelijk nagerekend)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT zs.indicator_uuid, zs.jaar, zs.gemiddelde, zs.n,
                      (SELECT AVG(gd.waarde) FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
                        WHERE gd.indicator_uuid = zs.indicator_uuid AND gd.jaar = zs.jaar
                          AND g.gebiedstype_id = %s::uuid AND g.gemeente_code = %s
                          AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
                          AND COALESCE(gd.scenario_id, 'current') = 'current'),
                      (SELECT COUNT(*) FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
                        WHERE gd.indicator_uuid = zs.indicator_uuid AND gd.jaar = zs.jaar
                          AND g.gebiedstype_id = %s::uuid AND g.gemeente_code = %s
                          AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
                          AND COALESCE(gd.scenario_id, 'current') = 'current')
               FROM zscore_gebieden(ARRAY[%s, %s]::varchar[], %s::uuid, %s) zs""",
            (gebiedstype_id, GEMEENTE, gebiedstype_id, GEMEENTE, GEBIED, GEBIED_2, gebiedstype_id, GEMEENTE),
        )
        rows = cur.fetchall()
    conn.rollback()
    assert rows
    for _uuid, _jaar, gem, n, gem_los, n_los in rows:
        assert float(gem) == pytest.approx(float(gem_los))
        assert n == n_los


# ── Rapportroutes geven dezelfde Z-score ─────────────────────────────────────

def zscores_data(gebied_id):
    """Route 1: GET /api/report/data/{id} (executive-basis), alleen |Z| >= 1."""
    r = requests.get(f"{BASE_URL}/api/report/data/{gebied_id}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    return {
        i["indicator"]: i["z_score"]
        for lst in r.json()["significante_domeinen"].values() for i in lst
    }


def zscores_thema(gebied_ids):
    """Route 2: POST /api/report/thema-analyse, alle indicatoren."""
    r = requests.post(
        f"{BASE_URL}/api/report/thema-analyse",
        json={"gebied_ids": gebied_ids, "referentie": "gemeente", "gemeente_code": GEMEENTE},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:300]
    return {
        (b["buurt_id"], i["indicator_naam"]): i["z_score"]
        for b in r.json()["buurten_analyse"] for i in b["indicatoren"]
    }


def zscores_deelgebied(gebied_ids):
    """Route 3: POST /api/report/deelgebied, buurt-drilldown."""
    r = requests.post(
        f"{BASE_URL}/api/report/deelgebied",
        json={"gebied_ids": gebied_ids, "referentie": "gemeente"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:300]
    out = {}

    def walk(node):
        if isinstance(node, dict):
            for d in node.get("buurten_drilldown") or []:
                out[(d["buurt_id"], node["indicator_naam"])] = d["buurt_z_score"]
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(r.json()["kwadranten"])
    return out


def assert_routes_gelijk():
    thema = zscores_thema([GEBIED, GEBIED_2])
    assert thema, "thema-analyse gaf geen Z-scores"
    for gebied_id in (GEBIED, GEBIED_2):
        data = zscores_data(gebied_id)
        assert data, f"geen significante indicatoren voor {gebied_id}"
        for indicator, z in data.items():
            assert thema[(gebied_id, indicator)] == z, (gebied_id, indicator)
    deel = zscores_deelgebied([GEBIED, GEBIED_2])
    gedeeld = set(deel) & set(thema)
    assert gedeeld, "geen overlap tussen deelgebied en thema-analyse"
    for k in gedeeld:
        assert deel[k] == thema[k], k
    return thema


def test_rapportroutes_geven_zelfde_zscore():
    assert_routes_gelijk()


def test_rapporten_ongevoelig_voor_waterbuurt(conn, gebiedstype_id):
    """Met een (opgeruimde) waterbuurt in de database blijven de Z-scores gelijk."""
    voor = assert_routes_gelijk()
    try:
        with conn.cursor() as cur:
            voeg_waterbuurt_toe(cur, gebiedstype_id, water=True)
        conn.commit()
        na = assert_routes_gelijk()
    finally:
        ruim_waterbuurt_op(conn)
    assert na == voor
