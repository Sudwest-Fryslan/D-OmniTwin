"""
Integratietests voor de labels A-E (#256), classificatie label_ae.

Draait tegen een draaiende stack met de sample dataset en de use case hittestress
(zie test_sample_stack.py).

Wat wordt bewezen:
- kaart_data?modus=label geeft per gebied een label A-E, gelijk aan een eigen berekening
  (kwintielen over de referentieset uit de database, polariteit toegepast), met een
  legenda A-E en de melding 'voorlopige drempels (kwintielen)';
- drempels in indicator_labels gaan voor (data, geen code), zonder melding 'voorlopig';
- het Klimaat Kompas is op een verse installatie gevuld en staat op label_ae: labels op
  indicator, onderdeel, thema en kwadrant, het themalabel volgens de gewogen aggregatie,
  en de selectie-route aggregeert over meer gebieden.
"""

import os

import pytest
import requests

from omnitwin.services import labelklasse as lk
from omnitwin.services import percentielklasse as pk

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
GEBIED = "BU19000002"     # Bolsward-Zuidoost
GEBIED_2 = "BU19000001"   # Bolsward-Noord
GEMEENTE = "1900"
HITTE_EILAND = "dacb8005-ecc2-5014-a5c2-a07c119b43ae"  # use case hittestress, lager is beter
KLIMAAT = "Klimaat Kompas"


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
        row = cur.fetchone()
    if not row:
        pytest.skip(f"{GEBIED} niet geladen")
    return row[0]


def kaart(gebiedstype_id, uuid, modus="label"):
    r = requests.get(
        f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{gebiedstype_id}",
        params={"indicator_uuid": uuid, "gemeente_code": GEMEENTE, "modus": modus},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return r.json()


def waarden(conn, gebiedstype_id, uuid):
    """(referentie, {gebied_id: waarde}) zoals de backend: zelfde_jaar, zonder waterbuurten."""
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
        return ref, {gid: float(w) for gid, w in cur.fetchall()}


@pytest.fixture(scope="module")
def hitte_eiland(conn, gebiedstype_id):
    ref, per_gebied = waarden(conn, gebiedstype_id, HITTE_EILAND)
    if len(ref) < 5 or GEBIED not in per_gebied:
        pytest.skip("use case hittestress niet geladen (Stedelijk hitte-eiland effect ontbreekt)")
    return ref, per_gebied


# ── Kaart ────────────────────────────────────────────────────────────────────

def test_kaart_label_kwintielen(gebiedstype_id, hitte_eiland):
    ref, per_gebied = hitte_eiland
    d = kaart(gebiedstype_id, HITTE_EILAND)
    meta = d["metadata"]
    assert meta["modus"] == "label"
    assert meta["label_bron"] == "kwintiel"
    assert "Voorlopige drempels (kwintielen)" in meta["legenda_melding"]
    assert [k["label"] for k in meta["klassen"]] == ["A", "B", "C", "D", "E"]
    kleur_van = {k["label"]: k["kleur"] for k in meta["klassen"]}

    for gid, w in per_gebied.items():
        verwacht = lk.label(w, ref, hoger_beter=False)  # hitte-eiland: lager is beter
        props = d["data"][gid]
        assert props["label"] == verwacht, gid
        assert props["color"] == kleur_van[verwacht], gid
    assert sum(k["aantal"] for k in meta["klassen"]) == sum(1 for p in d["data"].values() if p.get("label"))
    # laagste waarde = A, hoogste = E
    assert d["data"][min(per_gebied, key=per_gebied.get)]["label"] == "A"
    assert d["data"][max(per_gebied, key=per_gebied.get)]["label"] == "E"


def test_kaart_overschreven_drempels(conn, gebiedstype_id, hitte_eiland):
    _, per_gebied = hitte_eiland
    midden = sorted(per_gebied.values())[len(per_gebied) // 2]
    with conn.cursor() as cur:
        cur.execute("DELETE FROM indicator_labels WHERE indicator_uuid = %s", (HITTE_EILAND,))
        # alles onder het midden A, vanaf het midden E: twee labels, geen kwintielen
        cur.execute(
            """INSERT INTO indicator_labels (indicator_uuid, label, ondergrens, bovengrens, bron)
               VALUES (%s, 'A', NULL, %s, 'test #256'), (%s, 'E', %s, NULL, 'test #256')""",
            (HITTE_EILAND, midden, HITTE_EILAND, midden),
        )
    try:
        d = kaart(gebiedstype_id, HITTE_EILAND)
        assert d["metadata"]["label_bron"] == "drempels"
        assert d["metadata"]["legenda_melding"] is None
        assert "kwintiel" not in d["metadata"]["klassen"][0]["omschrijving"]
        for gid, w in per_gebied.items():
            assert d["data"][gid]["label"] == ("A" if w < midden else "E"), gid
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM indicator_labels WHERE bron = 'test #256'")


def test_kaart_label_onbekende_modus_blijft_422(gebiedstype_id):
    r = requests.get(
        f"{BASE_URL}/api/gebiedsmonitor/kaart_data/{gebiedstype_id}",
        params={"indicator_uuid": HITTE_EILAND, "modus": "labels"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 422


# ── Kompas ───────────────────────────────────────────────────────────────────

def knopen(node):
    yield node
    for kind in node.get("children") or []:
        yield from knopen(kind)


@pytest.fixture(scope="module")
def klimaat_id():
    r = requests.get(f"{BASE_URL}/api/kompas/configuraties", timeout=TIMEOUT)
    assert r.status_code == 200
    config = next((c for c in r.json()["configuraties"] if c["naam"] == KLIMAAT), None)
    assert config, "Klimaat Kompas ontbreekt"
    assert config["aantal_indicatoren"] >= 6, "Klimaat Kompas is niet gevuld (db/stuurdata/kompasprofiel_klimaat.json)"
    assert config["classificatie"] == "label_ae"
    return config["id"]


def test_klimaat_kompas_labels_en_themalabel(klimaat_id, hitte_eiland):
    r = requests.get(f"{BASE_URL}/api/kompas/{klimaat_id}/gebied/{GEBIED}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["classificatie"] == "label_ae"
    assert [k["label"] for k in d["klassen_legenda"]] == ["A", "B", "C", "D", "E"]
    assert "Voorlopige drempels (kwintielen)" in d["label_melding"]
    kleur_van = {k["label"]: k["kleur"] for k in d["klassen_legenda"]}

    thema_namen = {n["name"] for n in knopen(d["hierarchie"]) if n.get("type") == "thema"}
    assert {"Hittestress", "Hemelwateroverlast", "Droogte"} <= thema_namen

    indicatoren = {n["uuid"]: n for n in knopen(d["hierarchie"]) if n.get("type") == "indicator"}
    ref, per_gebied = hitte_eiland
    hitte = indicatoren[HITTE_EILAND]
    assert hitte["label"] == lk.label(per_gebied[GEBIED], ref, hoger_beter=False)
    assert hitte["label_bron"] == "kwintiel"
    assert hitte["color"] == kleur_van[hitte["label"]]

    for n in knopen(d["hierarchie"]):
        if n.get("label"):
            assert n["label"] == lk.score_naar_label(n["klasse"])
            assert n["klasse_kleur"] == kleur_van[n["label"]]
        if n.get("type") in ("onderdeel", "thema", "titel") and n.get("klasse"):
            onder = [i["klasse"] for i in knopen(n) if i.get("type") == "indicator" and i.get("klasse")]
            assert min(onder) <= n["klasse"] <= max(onder)

    # themalabel = gewogen gemiddelde van de indicatorscores (gewicht: gebieden in de referentie)
    hittestress = next(n for n in knopen(d["hierarchie"]) if n.get("type") == "thema" and n["name"] == "Hittestress")
    met_label = [i for i in knopen(hittestress) if i.get("type") == "indicator" and i.get("klasse")]
    assert met_label
    if len({i["klasse"] for i in met_label}) == 1:
        assert hittestress["label"] == met_label[0]["label"]


def test_klimaat_kompas_selectie(klimaat_id, hitte_eiland):
    def labels(url):
        r = requests.get(url, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["classificatie"] == "label_ae"
        return {n["uuid"]: n.get("klasse") for n in knopen(body["hierarchie"]) if n.get("type") == "indicator"}

    een = labels(f"{BASE_URL}/api/kompas/{klimaat_id}/gebied/{GEBIED}")
    twee = labels(f"{BASE_URL}/api/kompas/{klimaat_id}/gebied/{GEBIED_2}")
    sel = labels(f"{BASE_URL}/api/kompas/{klimaat_id}/selectie?gebied_id={GEBIED}&gebied_id={GEBIED_2}")
    vergeleken = 0
    for uuid, k in sel.items():
        a, b = een.get(uuid), twee.get(uuid)
        if a and b:
            assert min(a, b) <= k <= max(a, b)
            vergeleken += 1
    assert vergeleken > 0


def test_classificaties_bekend():
    r = requests.get(f"{BASE_URL}/api/kompas/configuraties", timeout=TIMEOUT)
    assert all(c["classificatie"] in pk.CLASSIFICATIES for c in r.json()["configuraties"])
