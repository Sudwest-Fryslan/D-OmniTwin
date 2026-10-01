"""
Integratietests voor de Z-score-referentie (#66, #155).

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
  dezelfde Z-score, ook als er een waterbuurt in de database staat;
- #155: een waterbuurt alleen op naam ("buitenwater") valt ook buiten de
  referentie en de kaartview; markeer_waterbuurten() zet de vlag in de data;
- #155: bij te weinig gebieden in hetzelfde jaar (minimum-n) valt de referentie
  terug op de meest recente waarde per gebied, met referentie_terugval = true,
  en het gebiedsdossier meldt dat;
- #155: een waterbuurt als doelgebied krijgt geen Z-score (SQL, rapport-data,
  executive, Kompas), met een melding.
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
WATERBUURT_NAAM = "BU1900T155"  # waterbuurt alleen op naam (#155); wordt opgeruimd
MIN_N = 5                       # standaard minimum-n (services.zscore_referentie.MIN_N_STANDAARD)


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
    # p_min_n => 0: deze tests gaan over de samenstelling van de groep, niet over de
    # terugval. Met terugval kan één extra gebied de set laten wisselen (peiljaar ↔ recentst).
    cur.execute(
        """SELECT indicator_uuid::text, gemiddelde, standaarddeviatie, n
           FROM zscore_referentie_stats(%s::uuid, %s, p_min_n => 0)""",
        (gebiedstype_id, GEMEENTE),
    )
    return {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}


def voeg_waterbuurt_toe(cur, gebiedstype_id, water=True, gebied_id=WATERBUURT, naam="Testwaterbuurt #66"):
    """Waterbuurt (of gewone buurt) met extreme waarden voor alle indicatoren."""
    metadata = '{"water": "JA"}' if water else '{}'
    cur.execute(
        """INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, metadata, actief)
           VALUES (%s, %s::uuid, %s, %s, %s::jsonb, true)""",
        (gebied_id, gebiedstype_id, naam, GEMEENTE, metadata),
    )
    cur.execute(
        """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
           SELECT %s, gd.indicator_uuid, MAX(gd.waarde) * 100 + 1000, MAX(gd.jaar), 'current', 'test #66'
           FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
           WHERE g.gemeente_code = %s
           GROUP BY gd.indicator_uuid""",
        (gebied_id, GEMEENTE),
    )


def ruim_waterbuurt_op(conn, gebied_id=WATERBUURT):
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gebied_data WHERE gebied_id = %s", (gebied_id,))
        cur.execute("DELETE FROM gebieden WHERE id = %s", (gebied_id,))
    conn.commit()


# ── Schema ───────────────────────────────────────────────────────────────────

def test_referentiefuncties_bestaan(conn):
    with conn.cursor() as cur:
        for f in ("zscore_referentie_waarden", "zscore_referentie_stats", "zscore", "zscore_gebieden",
                  "is_waterbuurt", "markeer_waterbuurten"):
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


def test_waterbuurt_op_naam_uitgesloten(conn, gebiedstype_id):
    """#155: een gebied zonder watervlag, met 'buitenwater' in de naam, telt niet mee
    in de referentie en staat niet in de kaartview. markeer_waterbuurten() zet de vlag."""
    try:
        with conn.cursor() as cur:
            voor = referentie_stats(cur, gebiedstype_id)
            voeg_waterbuurt_toe(cur, gebiedstype_id, water=False,
                                gebied_id=WATERBUURT_NAAM, naam="Buitenwater Test #155")
            na = referentie_stats(cur, gebiedstype_id)
            cur.execute("SELECT count(*) FROM vw_gebied_kaart_basis WHERE id = %s", (WATERBUURT_NAAM,))
            op_kaart = cur.fetchone()[0]
            cur.execute("SELECT is_waterbuurt(naam, metadata) FROM gebieden WHERE id = %s", (WATERBUURT_NAAM,))
            is_water = cur.fetchone()[0]
            cur.execute("SELECT markeer_waterbuurten()")
            assert cur.fetchone()[0] >= 1
            cur.execute("SELECT metadata->>'water', metadata->>'water_bron' FROM gebieden WHERE id = %s",
                        (WATERBUURT_NAAM,))
            vlag = cur.fetchone()
            cur.execute("SELECT markeer_waterbuurten()")
            tweede_keer = cur.fetchone()[0]
        assert na == voor
        assert op_kaart == 0
        assert is_water is True
        assert vlag == ("JA", "naam")
        assert tweede_keer == 0  # idempotent
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
               FROM zscore_gebieden(ARRAY[%s, %s]::varchar[], %s::uuid, %s, p_min_n => 0) zs""",
            (gebiedstype_id, GEMEENTE, gebiedstype_id, GEMEENTE, GEBIED, GEBIED_2, gebiedstype_id, GEMEENTE),
        )
        rows = cur.fetchall()
    conn.rollback()
    assert rows
    for _uuid, _jaar, gem, n, gem_los, n_los in rows:
        assert float(gem) == pytest.approx(float(gem_los))
        assert n == n_los


# ── Minimum-n en terugval (#155) ─────────────────────────────────────────────

ZELFDE_JAAR_N = """
    (SELECT COUNT(*) FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
      WHERE gd.indicator_uuid = zs.indicator_uuid AND gd.jaar = zs.jaar
        AND g.gebiedstype_id = %(gt)s::uuid AND g.gemeente_code = %(gm)s
        AND NOT is_waterbuurt(g.naam, g.metadata)
        AND COALESCE(gd.scenario_id, 'current') = 'current')"""

RECENTST = """
    (SELECT {agg} FROM (
        SELECT DISTINCT ON (gd.gebied_id) gd.waarde
        FROM gebied_data gd JOIN gebieden g ON g.id = gd.gebied_id
        WHERE gd.indicator_uuid = zs.indicator_uuid AND gd.jaar IS NOT NULL
          AND g.gebiedstype_id = %(gt)s::uuid AND g.gemeente_code = %(gm)s
          AND NOT is_waterbuurt(g.naam, g.metadata)
          AND COALESCE(gd.scenario_id, 'current') = 'current'
        ORDER BY gd.gebied_id, gd.jaar DESC) r)"""


def test_minimum_n_terugval_met_vlag(conn, gebiedstype_id):
    """Terugval precies waar minder dan MIN_N gebieden een waarde in het jaar van het
    doelgebied hebben; de referentie is dan de meest recente waarde per gebied."""
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT zs.indicator_uuid, zs.referentie_terugval, zs.gemiddelde, zs.n,
                       {ZELFDE_JAAR_N} AS n_jaar,
                       {RECENTST.format(agg='AVG(r.waarde)')} AS gem_recent,
                       {RECENTST.format(agg='COUNT(*)')} AS n_recent
                FROM zscore_gebieden(ARRAY[%(a)s, %(b)s]::varchar[], %(gt)s::uuid, %(gm)s) zs""",
            {"a": GEBIED, "b": GEBIED_2, "gt": gebiedstype_id, "gm": GEMEENTE},
        )
        rows = cur.fetchall()
    conn.rollback()
    assert rows
    for _uuid, terugval, gem, n, n_jaar, gem_recent, n_recent in rows:
        assert terugval == (n_jaar < MIN_N)
        if terugval:
            assert n == n_recent
            assert float(gem) == pytest.approx(float(gem_recent))
        else:
            assert n == n_jaar
    # De sample heeft dit geval: "Inkomen per inwoner" heeft 2024 voor 4 buurten
    assert any(r[1] for r in rows), "geen terugval in de sample; test dekt het geval niet"


def test_minimum_n_parameter(conn, gebiedstype_id):
    """p_min_n => 0: nooit terugvallen; hoge p_min_n: overal terugval."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT bool_or(referentie_terugval) FROM zscore_gebieden(
                   ARRAY[%s]::varchar[], %s::uuid, %s, p_min_n => 0)""",
            (GEBIED, gebiedstype_id, GEMEENTE),
        )
        assert cur.fetchone()[0] is False
        cur.execute(
            """SELECT bool_and(referentie_terugval) FROM zscore_gebieden(
                   ARRAY[%s]::varchar[], %s::uuid, %s, p_min_n => 1000)""",
            (GEBIED, gebiedstype_id, GEMEENTE),
        )
        assert cur.fetchone()[0] is True
        # Zonder doelgebied (Kompas top-buurten): ook de referentieset valt terug
        cur.execute(
            """SELECT bool_and(referentie_terugval) FROM zscore_referentie_stats(
                   %s::uuid, %s, p_min_n => 1000)""",
            (gebiedstype_id, GEMEENTE),
        )
        assert cur.fetchone()[0] is True
    conn.rollback()


def test_gebiedsdossier_meldt_terugval(conn):
    """GET /api/report/data meldt welke indicatoren met de terugval zijn vergeleken.
    In de sample valt alleen "Inkomen per inwoner" terug, en die staat niet in het
    Kompas (dus niet in het dossier). Daarom: een nieuw meetjaar (2099) voor één
    Kompas-indicator van het gebied; daarin heeft alleen dit gebied een waarde."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT i.uuid::text, i.naam FROM gebied_data gd
               JOIN indicatoren i ON i.uuid = gd.indicator_uuid
               JOIN v_kompas_hierarchie v ON v.indicator_uuid = i.uuid AND v.config_id = 1
               WHERE gd.gebied_id = %s AND i.naam != 'Inwoners'
               ORDER BY i.naam LIMIT 1""",
            (GEBIED,),
        )
        ind_uuid, ind_naam = cur.fetchone()
        cur.execute(
            """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
               SELECT gebied_id, indicator_uuid, waarde, 2099, 'current', 'test #155'
               FROM gebied_data WHERE gebied_id = %s AND indicator_uuid = %s::uuid
               ORDER BY jaar DESC LIMIT 1""",
            (GEBIED, ind_uuid),
        )
    conn.commit()
    try:
        r = requests.get(f"{BASE_URL}/api/report/data/{GEBIED}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert ind_naam in body["referentie_terugval_indicatoren"]
        assert any("meest recente waarde per gebied" in m and ind_naam in m for m in body["meldingen"])
        for lst in body["significante_domeinen"].values():
            for ind in lst:
                assert "referentie_terugval" in ind and "n_referentie" in ind
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gebied_data WHERE bron = 'test #155'")
        conn.commit()

    # Zonder het extra meetjaar: geen melding voor deze indicator
    body = requests.get(f"{BASE_URL}/api/report/data/{GEBIED}", timeout=TIMEOUT).json()
    assert ind_naam not in body["referentie_terugval_indicatoren"]


# ── Waterbuurt als doelgebied (#155) ─────────────────────────────────────────

def test_waterbuurt_als_doelgebied_geen_zscore(conn, gebiedstype_id):
    try:
        with conn.cursor() as cur:
            voeg_waterbuurt_toe(cur, gebiedstype_id, water=True)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT count(*), count(z_score), bool_and(is_waterbuurt)
                   FROM zscore_gebieden(ARRAY[%s]::varchar[], %s::uuid, %s)""",
                (WATERBUURT, gebiedstype_id, GEMEENTE),
            )
            totaal, met_z, water = cur.fetchone()
        conn.rollback()
        assert totaal > 0 and met_z == 0 and water is True

        data = requests.get(f"{BASE_URL}/api/report/data/{WATERBUURT}", timeout=TIMEOUT)
        assert data.status_code == 200, data.text[:300]
        body = data.json()
        assert body["is_waterbuurt"] is True
        assert body["significante_domeinen"] == {}
        assert any("waterbuurt" in m for m in body["meldingen"])

        exe = requests.get(f"{BASE_URL}/api/report/executive/{WATERBUURT}", timeout=TIMEOUT)
        assert exe.status_code == 200, exe.text[:300]
        exe = exe.json()
        assert exe["is_waterbuurt"] is True
        assert exe["top_kansen"] == [] and exe["top_risicos"] == []
        assert exe["meldingen"]

        configs = requests.get(f"{BASE_URL}/api/kompas/configuraties", timeout=TIMEOUT).json()
        lijst = configs.get("configuraties", configs) if isinstance(configs, dict) else configs
        kompas = requests.get(f"{BASE_URL}/api/kompas/{lijst[0]['id']}/gebied/{WATERBUURT}", timeout=TIMEOUT)
        assert kompas.status_code == 200, kompas.text[:300]
        kompas = kompas.json()
        assert kompas["is_waterbuurt"] is True
        assert kompas["melding"]
    finally:
        ruim_waterbuurt_op(conn)


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
