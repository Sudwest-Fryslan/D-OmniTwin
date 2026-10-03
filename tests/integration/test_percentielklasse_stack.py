"""
Integratietests voor de percentielklasse en de kaartmodi (#255).

Draait tegen een draaiende stack met de sample dataset (zie test_sample_stack.py).

Wat wordt bewezen:
- kaart_data?modus=percentiel geeft per gebied een klasse 1-8, gelijk aan een eigen
  berekening over de referentieset uit de database (zscore_referentie_waarden);
- de kleur hoort bij de klasse, de legenda heeft 8 klassen met aantallen;
- modus=waarde geeft klassen met bereik voor de legenda; een onbekende modus 422;
- een waarde met n < 10 krijgt geen klasse (status onderdrukt);
- kompasprofiel met classificatie percentiel_8: klassen op indicator, onderdeel,
  thema en kwadrant, de selectie-route aggregeert over meer gebieden; profiel zscore
  blijft zonder klassen.
"""

import os

import pytest
import requests

from omnitwin.services import percentielklasse as pk

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
GEBIED = "BU19000002"     # Bolsward-Zuidoost
GEBIED_2 = "BU19000001"   # Bolsward-Noord
GEMEENTE = "1900"


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
    """Indicator met waarden voor ten minste 8 buurten in de gemeente, ook voor het testgebied."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT v.indicator_uuid::text, COALESCE(i.score_type, '+/+')
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


def kaart(gebiedstype_id, uuid, modus):
    r = requests.get(
        f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{gebiedstype_id}",
        params={"indicator_uuid": uuid, "gemeente_code": GEMEENTE, "modus": modus},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return r.json()


def verwachte_klassen(conn, gebiedstype_id, uuid, score_type):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT waarde FROM zscore_referentie_waarden(%s::uuid, %s, 'zelfde_jaar', 'current',
                                                           ARRAY[%s::uuid], 5)""",
            (gebiedstype_id, GEMEENTE, uuid),
        )
        ref = [float(r[0]) for r in cur.fetchall()]
        cur.execute(
            """SELECT v.gebied_id, v.waarde FROM vw_gebied_indicator_actueel v
               JOIN gebieden g ON g.id = v.gebied_id
               WHERE v.indicator_uuid = %s::uuid AND g.gemeente_code = %s AND g.gebiedstype_id = %s::uuid
                 AND NOT public.is_waterbuurt(g.naam, g.metadata)""",
            (uuid, GEMEENTE, gebiedstype_id),
        )
        hoger = pk.hoger_is_beter(score_type)
        return {gid: pk.klasse(float(w), ref, hoger) for gid, w in cur.fetchall()}


# ── Kaart ────────────────────────────────────────────────────────────────────

def test_kaart_percentiel_geeft_klasse_per_gebied(conn, gebiedstype_id, indicator):
    uuid, score_type = indicator
    d = kaart(gebiedstype_id, uuid, "percentiel")
    meta = d["metadata"]
    assert meta["modus"] == "percentiel"
    assert [k["klasse"] for k in meta["klassen"]] == list(range(1, 9))
    kleur_van = {k["klasse"]: k["kleur"] for k in meta["klassen"]}

    verwacht = verwachte_klassen(conn, gebiedstype_id, uuid, score_type)
    assert GEBIED in verwacht and verwacht[GEBIED] is not None
    for gid, klasse in verwacht.items():
        props = d["data"][gid]
        assert props["klasse"] == klasse, gid
        assert props["color"] == kleur_van[klasse], gid
    assert sum(k["aantal"] for k in meta["klassen"]) == sum(1 for p in d["data"].values() if p.get("klasse"))
    # meer dan één klasse in gebruik, en de uitersten komen voor
    gebruikt = {p["klasse"] for p in d["data"].values() if p.get("klasse")}
    assert {1, 8} <= gebruikt


def test_kaart_waarde_geeft_klassen_met_bereik(gebiedstype_id, indicator):
    uuid, _ = indicator
    d = kaart(gebiedstype_id, uuid, "waarde")
    meta = d["metadata"]
    assert meta["modus"] == "waarde"
    klassen = meta["klassen"]
    assert klassen and all(k["van"] <= k["tot"] for k in klassen)
    assert [k["van"] for k in klassen] == sorted(k["van"] for k in klassen)
    assert sum(k["aantal"] for k in klassen) == meta["features_with_data"]
    assert all("klasse" not in p for p in d["data"].values())


def test_kaart_onbekende_modus_422(gebiedstype_id, indicator):
    r = requests.get(
        f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{gebiedstype_id}",
        params={"indicator_uuid": indicator[0], "modus": "zscore"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 422


def test_onderdrukte_waarde_krijgt_geen_klasse(conn, gebiedstype_id, indicator):
    uuid, _ = indicator
    with conn.cursor() as cur:
        cur.execute(
            "SELECT max(jaar) FROM gebied_data WHERE indicator_uuid = %s::uuid AND gebied_id = %s",
            (uuid, GEBIED),
        )
        jaar = cur.fetchone()[0] + 1
        cur.execute(
            """INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron, n, n_status)
               VALUES (%s, %s::uuid, 1, %s, 'current', 'test #255', 5, 'gemeten')""",
            (GEBIED, uuid, jaar),
        )
    try:
        d = kaart(gebiedstype_id, uuid, "percentiel")
        props = d["data"][GEBIED]
        assert props["jaar"] == jaar
        assert props["klasse"] is None and props["klasse_status"] == "onderdrukt"
        assert props["color"] == d["metadata"]["nodata_color"]
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gebied_data WHERE bron = 'test #255'")


# ── Kompas ───────────────────────────────────────────────────────────────────

@pytest.fixture
def percentiel_profiel(conn):
    """Het standaardprofiel tijdelijk op percentiel_8."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, classificatie FROM kompas_configuraties WHERE is_standaard AND is_actief LIMIT 1")
        config_id, oud = cur.fetchone()
        cur.execute("UPDATE kompas_configuraties SET classificatie = 'percentiel_8' WHERE id = %s", (config_id,))
    try:
        yield config_id
    finally:
        with conn.cursor() as cur:
            cur.execute("UPDATE kompas_configuraties SET classificatie = %s WHERE id = %s", (oud, config_id))


def knopen(node):
    yield node
    for kind in node.get("children") or []:
        yield from knopen(kind)


def test_kompas_zscore_zonder_klassen():
    r = requests.get(f"{BASE_URL}/api/kompas/configuraties", timeout=TIMEOUT)
    assert r.status_code == 200
    configs = r.json()["configuraties"]
    assert all(c["classificatie"] in pk.CLASSIFICATIES for c in configs)
    standaard = r.json()["standaard_config_id"]
    if next(c for c in configs if c["id"] == standaard)["classificatie"] != "zscore":
        pytest.skip("standaardprofiel staat niet op zscore")
    d = requests.get(f"{BASE_URL}/api/kompas/{standaard}/gebied/{GEBIED}", timeout=TIMEOUT).json()
    assert d["classificatie"] == "zscore"
    assert all(n.get("klasse") is None for n in knopen(d["hierarchie"]))


def test_kompas_percentiel_klassen_en_aggregatie(percentiel_profiel):
    r = requests.get(f"{BASE_URL}/api/kompas/{percentiel_profiel}/gebied/{GEBIED}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["classificatie"] == "percentiel_8"
    assert [k["klasse"] for k in d["klassen_legenda"]] == list(range(1, 9))
    kleur_van = {k["klasse"]: k["kleur"] for k in d["klassen_legenda"]}

    # Samenstelling is neutraal: eigen (blauw) palet, telt niet mee in de wortel
    neutraal = {id(n) for t in d["hierarchie"]["children"] if pk.is_neutraal_kwadrant(t["name"]) for n in knopen(t)}
    indicatoren = [n for n in knopen(d["hierarchie"]) if n.get("type") == "indicator"]
    met_klasse = [n for n in indicatoren if n.get("klasse")]
    assert met_klasse, "geen indicator met een klasse"
    for n in met_klasse:
        assert 1 <= n["klasse"] <= 8
        assert n["color"] == n["klasse_kleur"]
        if id(n) not in neutraal:
            assert n["klasse_kleur"] == kleur_van[n["klasse"]]
    # ouders hebben een klasse binnen het bereik van hun indicatoren
    for n in knopen(d["hierarchie"]):
        if n.get("type") in ("onderdeel", "thema", "titel") and n.get("klasse"):
            onder = [i["klasse"] for i in knopen(n) if i.get("type") == "indicator" and i.get("klasse")]
            assert min(onder) <= n["klasse"] <= max(onder)
            if id(n) not in neutraal:
                assert n["klasse_kleur"] == kleur_van[n["klasse"]]


def test_kompas_selectie_aggregeert_over_gebieden(percentiel_profiel):
    def klassen(url):
        r = requests.get(url, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        return {n["uuid"]: n.get("klasse") for n in knopen(r.json()["hierarchie"]) if n.get("type") == "indicator"}

    een = klassen(f"{BASE_URL}/api/kompas/{percentiel_profiel}/gebied/{GEBIED}")
    twee = klassen(f"{BASE_URL}/api/kompas/{percentiel_profiel}/gebied/{GEBIED_2}")
    sel = klassen(f"{BASE_URL}/api/kompas/{percentiel_profiel}/selectie?gebied_id={GEBIED}&gebied_id={GEBIED_2}")
    alleen_een = klassen(f"{BASE_URL}/api/kompas/{percentiel_profiel}/selectie?gebied_id={GEBIED}")
    assert alleen_een == een
    vergeleken = 0
    for uuid, k in sel.items():
        a, b = een.get(uuid), twee.get(uuid)
        if a and b:
            assert min(a, b) <= k <= max(a, b)
            vergeleken += 1
        elif a or b:
            assert k == (a or b)
    assert vergeleken > 0
