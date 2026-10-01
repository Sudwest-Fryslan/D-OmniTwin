#!/usr/bin/env python3
"""
D-OmniTwin — Seed Script voor provincie Fryslân
================================================
Laadt de volledige Fryslân-dataset (931 CBS-buurten 2024 + indicatorwaarden)
in een bestaande database, bijvoorbeeld de database die `db-init` aanmaakt.

Gebruik:
    python init_data/scripts/seed_fryslan.py [--stap alle|buurten|indicatoren|kompas|waarden|cbs]
                                             [--max-fouten-pct 1.0]

In de Docker-installatie:
    docker compose run --rm db-init python init_data/scripts/seed_fryslan.py --stap alle

Vereisten:
    Schema geladen (db-init of init_data/schema/schema_latest.sql).
    Databaseverbinding via omgevingsvariabelen of .env (DATABASE_HOST, DATABASE_PORT,
    DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD), zoals load_sample.py.

Volgorde:
    1. buurten     → gemeenten (18 Friese, uit de GeoJSON) + gebieden (GeoJSON → PostGIS)
    2. indicatoren → indicatoren (seed JSON); bestaande indicatoren met dezelfde naam
                     (bijvoorbeeld uit de sample) worden aangevuld, niet gedupliceerd
    3. kompas      → kompas_* tabellen (hiërarchie CSV)
    4. waarden     → gebied_data (indicatorwaarden CSV, RIVM); alleen voor gebieden in de database
    5. cbs         → gebied_data (CBS Kerncijfers 2019-nu uit init_data/cbs, via laad_cbs.py)

Idempotent: opnieuw draaien werkt bestaande rijen bij en maakt geen duplicaten.
Het script maakt geen gebruikers of API-keys aan (daarvoor: create_admin.py).

Exitcode: 0 als alle stappen slaagden en het aandeel fouten per stap onder
--max-fouten-pct blijft, anders 1.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

# Laad .env bestand (bestaande omgevingsvariabelen gaan voor)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optioneel

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 niet gevonden. Installeer met: pip install psycopg2-binary")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
INIT_DATA = ROOT / "init_data"
BUURTEN_GEOJSON = INIT_DATA / "fryslan" / "buurten_fryslan.geojson"
WAARDEN_CSV = INIT_DATA / "fryslan" / "indicatorwaarden_fryslan.csv"
INDICATOREN_SEED = INIT_DATA / "indicatoren" / "indicatoren_seed.json"
KOMPAS_CSV = INIT_DATA / "kompas" / "kompas_hierarchie.csv"

# Gebiedstype UUID voor CBS Buurten (uit schema_latest.sql seed)
CBS_BUURT_TYPE_ID = "afba67cb-6b38-4723-9c95-102a22d5b38a"
PROVINCIE = "Fryslân"
EILANDGEMEENTEN = {"0060", "0088", "0093", "0096"}  # Ameland, Schiermonnikoog, Terschelling, Vlieland

# CBS-naam → DB-naam aliases (CBS OData namen ≠ seed JSON namen).
# Alleen gebruikt als de CBS-naam zelf niet als indicator bestaat.
CBS_ALIASES = {
    "0 tot 15 jaar":                        "0-15 jaar",
    "15 tot 25 jaar":                       "15-25 jaar",
    "25 tot 45 jaar":                       "25-45 jaar",
    "45 tot 65 jaar":                       "45-65 jaar",
    "65 jaar of ouder":                     "65+ jaar",
    "Aantal inwoners":                      "Inwoners",
    "Afstand tot huisartsenpraktijk":       "Huisarts",
    "Eenzaam":                              "Eenzaamheid",
    "Ernstig eenzaam":                      "Eenzaamheid",
    "Gemiddeld inkomen per inwoner":        "Inkomen per inwoner",
    "Gemiddelde WOZ-waarde van woningen":   "Gemiddelde WOZ-waarde",
    "Goed ervaren gezondheid":              "Ervaren gezondheid",
    "Hoog risico angststoornis of depressie": "Gezondheid",
    "Huishoudens met een laag inkomen":     "Huishoudens met laag inkomen",
    "Huishoudens met kinderen":             "Huishoudens met kind",
    "Huishoudens zonder kinderen":          "Huishoudens zonder kind",
    "In bezit overige verhuurders":         "Particulier huurbezit",
    "In bezit woningcorporatie":            "Woningcorporatie bezit",
    "Overmatige drinker":                   "Overmatig drinken",
    "Roker":                                "Roken",
    "Personen met bijstand":                "Participatiewet totaal",
    "Voldoet aan beweegrichtlijn":          "Bewegen",
    "Vrijwilligerswerk":                    "Vrijwilliger",
}


class StapResultaat:
    """Tellingen per stap voor de eindsamenvatting en de exitcode."""

    def __init__(self, naam):
        self.naam = naam
        self.ok = 0
        self.fouten = 0
        self.info = []          # extra regels voor de samenvatting (overgeslagen e.d.)
        self.mislukt = False    # stap kon niet draaien (bestand ontbreekt, onverwachte fout)
        self.duur = 0.0

    @property
    def fout_pct(self):
        totaal = self.ok + self.fouten
        return 100.0 * self.fouten / totaal if totaal else 0.0


def get_db_connection():
    """Database connectie via environment variabelen (gelijk aan load_sample.py)."""
    host = os.environ.get("DATABASE_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    return psycopg2.connect(
        host=host,
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
        connect_timeout=10,
    )


# ─────────────────────────────────────────────────────────
# STAP 1: Gemeenten + buurten importeren
# ─────────────────────────────────────────────────────────
def import_buurten(conn, res):
    print("\n📍 STAP 1: Gemeenten en buurten importeren (GeoJSON → PostGIS)")
    print("-" * 50)

    if not BUURTEN_GEOJSON.exists():
        print(f"❌ GeoJSON niet gevonden: {BUURTEN_GEOJSON}")
        res.mislukt = True
        return

    with open(BUURTEN_GEOJSON, encoding="utf-8") as f:
        features = json.load(f).get("features", [])
    print(f"   📂 {len(features)} buurten in GeoJSON")

    cur = conn.cursor()

    # Gemeenten uit de GeoJSON (bron van waarheid voor de benodigde codes).
    # Bestaande gemeenten blijven ongewijzigd (ON CONFLICT DO NOTHING).
    gemeenten = {}
    for feat in features:
        props = feat.get("properties", {})
        code = (props.get("gemeentecode") or "").strip().replace("GM", "")
        if code:
            gemeenten[code.zfill(4)] = (props.get("gemeentenaam") or "").strip() or code
    nieuw = 0
    for code, naam in sorted(gemeenten.items()):
        cur.execute("""
            INSERT INTO gemeenten (code, naam, provincie, is_eiland)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        """, (code, naam, PROVINCIE, code in EILANDGEMEENTEN))
        nieuw += cur.rowcount
    conn.commit()
    print(f"   🏛️  {len(gemeenten)} gemeenten in GeoJSON, {nieuw} toegevoegd aan tabel gemeenten")
    res.info.append(f"gemeenten: {len(gemeenten)} in GeoJSON, {nieuw} nieuw")

    overgeslagen = 0
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        bu_code = (props.get("buurtcode") or props.get("BU_CODE") or
                   props.get("statcode") or "").strip().replace("BU", "")
        bu_naam = (props.get("buurtnaam") or props.get("BU_NAAM") or
                   props.get("statnaam") or "Onbekend").strip()
        gm_code = (props.get("gemeentecode") or props.get("GM_CODE") or "").strip()
        gm_code = gm_code.replace("GM", "").zfill(4) if gm_code else None

        if not bu_code:
            overgeslagen += 1
            continue

        bu_id = f"BU{bu_code.zfill(8)}"
        geom_str = json.dumps(geom) if geom else None

        try:
            cur.execute("SAVEPOINT sp_buurt")
            cur.execute("""
                INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, geom, provincienaam, actief)
                VALUES (
                    %s, %s, %s, %s,
                    CASE WHEN %s IS NOT NULL
                         THEN ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 28992))
                         ELSE NULL END,
                    %s,
                    TRUE
                )
                ON CONFLICT (id) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    gemeente_code = EXCLUDED.gemeente_code,
                    geom = EXCLUDED.geom,
                    provincienaam = EXCLUDED.provincienaam,
                    actief = TRUE,
                    updated_at = CURRENT_TIMESTAMP
            """, (bu_id, CBS_BUURT_TYPE_ID, bu_naam, gm_code, geom_str, geom_str, PROVINCIE))
            cur.execute("RELEASE SAVEPOINT sp_buurt")
            res.ok += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_buurt")
            res.fouten += 1
            if res.fouten <= 5:
                print(f"   ⚠️  Fout bij {bu_id}: {e}".rstrip())

    conn.commit()
    cur.close()

    if overgeslagen:
        res.info.append(f"{overgeslagen} features zonder buurtcode overgeslagen")
    print(f"   ✅ {res.ok} buurten geïmporteerd/bijgewerkt | {overgeslagen} overgeslagen | {res.fouten} fouten")


# ─────────────────────────────────────────────────────────
# STAP 2: Indicatoren seeden
# ─────────────────────────────────────────────────────────
def _score_type(ind, naam):
    score_type = ind.get("score_type")
    if score_type:
        return score_type
    naam_lower = naam.lower()
    if any(kw in naam_lower for kw in ["afstand", "criminaliteit", "overlast", "diefstal",
                                       "inbraak", "eenzaam", "werkloos", "moeite"]):
        return "+/-"
    return "+/+"


def import_indicatoren(conn, res):
    print("\n📊 STAP 2: Indicatoren seeden")
    print("-" * 50)

    if not INDICATOREN_SEED.exists():
        print(f"❌ Seed bestand niet gevonden: {INDICATOREN_SEED}")
        res.mislukt = True
        return

    with open(INDICATOREN_SEED, encoding="utf-8") as f:
        indicatoren = json.load(f)
    print(f"   📂 {len(indicatoren)} indicatoren in seed")

    cur = conn.cursor()
    # Bestaande indicatoren op naam (hoofdletterongevoelig); bij dubbele namen de oudste
    cur.execute("SELECT DISTINCT ON (lower(naam)) lower(naam), uuid FROM indicatoren ORDER BY lower(naam), id")
    bestaand = {naam: uuid for naam, uuid in cur.fetchall()}

    nieuw = 0
    bijgewerkt = 0
    for ind in indicatoren:
        naam = (ind.get("naam") or "").strip()
        if not naam:
            continue

        score_type = _score_type(ind, naam)
        bron = ind.get("bron") or ""
        eenheid = ind.get("eenheid") or ""
        code = ind.get("code") or (
            "IND_" + naam.upper()[:40].replace(" ", "_").replace("/", "_")
            .replace(",", "").replace("-", "_"))
        omschrijving = ind.get("omschrijving") or ""
        if not omschrijving:
            titel, thema, onderdeel = ind.get("titel", ""), ind.get("thema", ""), ind.get("onderdeel", "")
            if titel or thema:
                omschrijving = f"{titel} → {thema} → {onderdeel}"

        try:
            cur.execute("SAVEPOINT sp_ind")
            if naam.lower() in bestaand:
                # Bestaat al (bijv. uit de sample, met eigen uuid/code): alleen lege velden aanvullen
                cur.execute("""
                    UPDATE indicatoren SET
                        eenheid = COALESCE(NULLIF(eenheid, ''), NULLIF(%s, '')),
                        omschrijving = COALESCE(NULLIF(omschrijving, ''), NULLIF(%s, '')),
                        bron = COALESCE(NULLIF(bron, ''), NULLIF(%s, '')),
                        score_type = COALESCE(score_type, %s)
                    WHERE uuid = %s
                """, (eenheid, omschrijving, bron, score_type, bestaand[naam.lower()]))
                bijgewerkt += 1
            else:
                cur.execute("""
                    INSERT INTO indicatoren (uuid, naam, code, eenheid, omschrijving, bron, score_type, status)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, 'O')
                    ON CONFLICT (code) DO UPDATE SET
                        naam = EXCLUDED.naam,
                        eenheid = COALESCE(NULLIF(EXCLUDED.eenheid, ''), indicatoren.eenheid),
                        omschrijving = COALESCE(NULLIF(EXCLUDED.omschrijving, ''), indicatoren.omschrijving),
                        bron = COALESCE(NULLIF(EXCLUDED.bron, ''), indicatoren.bron),
                        score_type = EXCLUDED.score_type,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING uuid
                """, (naam, code, eenheid, omschrijving, bron, score_type))
                bestaand[naam.lower()] = cur.fetchone()[0]
                nieuw += 1
            cur.execute("RELEASE SAVEPOINT sp_ind")
            res.ok += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_ind")
            res.fouten += 1
            if res.fouten <= 5:
                print(f"   ⚠️  Fout bij {naam}: {e}".rstrip())

    conn.commit()
    cur.close()
    res.info.append(f"{nieuw} nieuw, {bijgewerkt} bestaand (aangevuld)")
    print(f"   ✅ {res.ok} indicatoren verwerkt ({nieuw} nieuw, {bijgewerkt} bestaand) | {res.fouten} fouten")


# ─────────────────────────────────────────────────────────
# STAP 3: Kompas hiërarchie laden
# ─────────────────────────────────────────────────────────
def import_kompas(conn, res):
    print("\n🧭 STAP 3: Kompas hiërarchie laden")
    print("-" * 50)

    if not KOMPAS_CSV.exists():
        print(f"❌ CSV niet gevonden: {KOMPAS_CSV}")
        res.mislukt = True
        return

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO kompas_configuraties (naam, beschrijving, is_standaard, is_actief, icoon)
        VALUES ('Volledig Kompas',
                'Complete overzicht van alle indicatoren. Gegenereerd vanuit initiatie dataset.',
                TRUE, TRUE, '🌍')
        ON CONFLICT (naam) DO NOTHING
    """)
    cur.execute("SELECT id FROM kompas_configuraties WHERE naam = 'Volledig Kompas'")
    config_id = cur.fetchone()[0]
    conn.commit()

    def get_or_create(table, values):
        cols = list(values)
        where = " AND ".join(f"{c} = %s" for c in cols)
        cur.execute(f"SELECT id FROM {table} WHERE {where}", [values[c] for c in cols])
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('%s' for _ in cols)}) RETURNING id",
                    [values[c] for c in cols])
        return cur.fetchone()[0]

    onderdelen = set()
    niet_gevonden = set()
    with open(KOMPAS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titel = row.get("Title", "").strip()
            thema = row.get("Thema", "").strip()
            onderdeel = row.get("Onderdeel", "").strip() or "(Algemeen)"
            indicator_naam = row.get("Indicator", "").strip() or row.get("Indicator SWF", "").strip()
            actueel = row.get("Indicator actueel", "").strip().upper() == "J"
            if not titel or not thema:
                continue

            try:
                cur.execute("SAVEPOINT sp_kompas")
                titel_id = get_or_create("kompas_titels", {"naam": titel, "config_id": config_id})
                thema_id = get_or_create("kompas_themas", {"naam": thema, "titel_id": titel_id})
                onderdeel_id = get_or_create("kompas_onderdelen", {"naam": onderdeel, "thema_id": thema_id})
                onderdelen.add(onderdeel_id)

                if indicator_naam:
                    cur.execute("SELECT uuid FROM indicatoren WHERE lower(naam) = lower(%s) ORDER BY id LIMIT 1",
                                (indicator_naam,))
                    ind_row = cur.fetchone()
                    if ind_row:
                        cur.execute("""
                            INSERT INTO kompas_indicator_mapping
                                (config_id, indicator_uuid, onderdeel_id, is_actueel)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (config_id, indicator_uuid, onderdeel_id) DO UPDATE SET
                                is_actueel = EXCLUDED.is_actueel
                        """, (config_id, ind_row[0], onderdeel_id, actueel))
                        res.ok += 1
                    else:
                        niet_gevonden.add(indicator_naam)
                cur.execute("RELEASE SAVEPOINT sp_kompas")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_kompas")
                res.fouten += 1
                if res.fouten <= 5:
                    print(f"   ⚠️  Fout bij {titel} / {thema} / {onderdeel}: {e}".rstrip())

    conn.commit()
    cur.close()

    res.info.append(f"{len(onderdelen)} onderdelen; {len(niet_gevonden)} indicatornamen zonder indicator in database")
    print(f"   ✅ {res.ok} indicator-koppelingen | {len(onderdelen)} onderdelen | {res.fouten} fouten")
    if niet_gevonden:
        print(f"   ℹ️  {len(niet_gevonden)} indicatornamen uit de Kompas-CSV niet gevonden (geen koppeling)")
    if res.ok == 0:
        print("   ❌ Geen enkele indicator gekoppeld: ontbreken de indicatoren? (stap indicatoren)")
        res.mislukt = True


# ─────────────────────────────────────────────────────────
# STAP 4: Indicatorwaarden laden
# ─────────────────────────────────────────────────────────
INSERT_WAARDEN = """
    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
    VALUES %s
    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
        waarde = EXCLUDED.waarde,
        bron = EXCLUDED.bron,
        updated_at = CURRENT_TIMESTAMP
"""


def _schrijf_batch(conn, cur, rows, res):
    try:
        execute_values(cur, INSERT_WAARDEN, rows, page_size=1000)
        conn.commit()
        res.ok += len(rows)
    except Exception:
        conn.rollback()
        # Per rij opnieuw, zodat één foute rij niet de hele batch kost
        for r in rows:
            try:
                cur.execute("SAVEPOINT sp_w")
                execute_values(cur, INSERT_WAARDEN, [r])
                cur.execute("RELEASE SAVEPOINT sp_w")
                res.ok += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_w")
                res.fouten += 1
                if res.fouten <= 5:
                    print(f"   ⚠️  Fout bij {r[0]} / {r[1]} / {r[3]}: {e}".rstrip())
        conn.commit()


def import_waarden(conn, res):
    print("\n📈 STAP 4: Indicatorwaarden laden")
    print("-" * 50)

    if not WAARDEN_CSV.exists():
        print(f"❌ CSV niet gevonden: {WAARDEN_CSV}")
        res.mislukt = True
        return

    cur = conn.cursor()

    # naam → uuid; bij dubbele namen wint de oudste (laagste id), net als bij het Kompas
    cur.execute("SELECT naam, uuid FROM indicatoren ORDER BY id DESC")
    indicator_cache = {}
    for naam, uuid in cur.fetchall():
        indicator_cache[naam] = str(uuid)
        indicator_cache[naam.lower()] = str(uuid)
    for cbs_naam, db_naam in CBS_ALIASES.items():
        if cbs_naam not in indicator_cache and db_naam in indicator_cache:
            indicator_cache[cbs_naam] = indicator_cache[db_naam]

    cur.execute("SELECT id FROM gebieden")
    gebieden = {r[0] for r in cur.fetchall()}
    print(f"   📋 {len(indicator_cache)} indicatornamen (incl. aliassen) | {len(gebieden)} gebieden in database")

    rijen = {}
    buiten_dataset = 0
    onbekende_indicatoren = {}
    ongeldig = 0
    totaal = 0

    with open(WAARDEN_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            totaal += 1
            buurt_id = row.get("buurt_id", "").strip()
            if not buurt_id.startswith(("BU", "WK", "GM", "NL")):
                buurt_id = f"BU{buurt_id.zfill(8)}"
            if buurt_id not in gebieden:
                # De CSV bevat ook wijken/gemeenten en gebieden buiten Fryslân
                buiten_dataset += 1
                continue

            indicator_naam = row.get("indicator_naam", "").strip()
            indicator_uuid = indicator_cache.get(indicator_naam) or indicator_cache.get(indicator_naam.lower())
            if not indicator_uuid:
                onbekende_indicatoren[indicator_naam] = onbekende_indicatoren.get(indicator_naam, 0) + 1
                continue

            try:
                waarde = float(row.get("waarde", "").strip())
                jaar_str = row.get("jaar", "").strip()
                jaar = int(jaar_str) if jaar_str else None
            except ValueError:
                ongeldig += 1
                continue

            # Laatste waarde per (gebied, indicator, jaar) wint — voorkomt ON CONFLICT-fouten in één batch
            rijen[(buurt_id, indicator_uuid, jaar)] = (
                buurt_id, indicator_uuid, waarde, jaar, row.get("bron", "").strip() or None, "current")

    print(f"   📂 {totaal} rijen in CSV | {len(rijen)} te laden | {buiten_dataset} voor gebieden buiten de database")
    if totaal and not rijen:
        print("   ❌ Geen enkele waarde te laden: ontbreken de buurten of indicatoren? (stap buurten/indicatoren)")
        res.mislukt = True

    batch = list(rijen.values())
    for i in range(0, len(batch), 5000):
        _schrijf_batch(conn, cur, batch[i:i + 5000], res)

    cur.close()
    res.fouten += ongeldig
    res.info.append(f"{totaal} CSV-rijen; {buiten_dataset} voor gebieden niet in database (overgeslagen)")
    if onbekende_indicatoren:
        n = sum(onbekende_indicatoren.values())
        res.info.append(f"{n} rijen met onbekende indicator: {', '.join(sorted(onbekende_indicatoren))}")
    print(f"   ✅ {res.ok} metingen geladen/bijgewerkt | {ongeldig} ongeldige waarden | {res.fouten} fouten")


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def import_cbs(conn, res):
    """CBS Kerncijfers 2019-nu (init_data/cbs, alle jaargangen) voor alle gebieden in de database."""
    print("\n📈 STAP 5: CBS Kerncijfers (alle jaargangen)")
    print("-" * 50)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import laad_cbs
    res.ok += laad_cbs.laad(conn)


STAPPEN = [
    ("buurten", import_buurten),
    ("indicatoren", import_indicatoren),
    ("kompas", import_kompas),
    ("waarden", import_waarden),
    ("cbs", import_cbs),
]


def main():
    parser = argparse.ArgumentParser(description="D-OmniTwin — Seed Fryslân dataset")
    parser.add_argument(
        "--stap",
        choices=["alle"] + [naam for naam, _ in STAPPEN],
        default="alle",
        help="Welke stap uitvoeren (default: alle)",
    )
    parser.add_argument(
        "--max-fouten-pct", type=float, default=1.0,
        help="Maximaal percentage foute rijen per stap voordat de exitcode 1 wordt (default: 1.0)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌍 D-OmniTwin — Seed Fryslân Dataset")
    print("=" * 60)

    try:
        conn = get_db_connection()
        print("✅ Database verbinding OK")
    except Exception as e:
        print(f"❌ Database verbinding mislukt: {e}", file=sys.stderr)
        print("   Controleer DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER en DATABASE_PASSWORD.")
        sys.exit(1)

    # Stuurdata (gebiedstypes, kleurschema's, scenario's) moet er zijn; db-init laadt die altijd
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.gebiedstypes') IS NOT NULL")
        schema_ok = cur.fetchone()[0]
        stuurdata_ok = False
        if schema_ok:
            cur.execute("SELECT EXISTS (SELECT 1 FROM gebiedstypes WHERE id = %s)", (CBS_BUURT_TYPE_ID,))
            stuurdata_ok = cur.fetchone()[0]
    if not stuurdata_ok:
        print("❌ Schema of stuurdata ontbreekt (gebiedstype 'CBS Buurt' niet gevonden).", file=sys.stderr)
        print("   Laad eerst het schema en de stuurdata: db-init doet dit automatisch, of")
        print("   python init_data/scripts/load_sample.py --stap stuurdata")
        conn.close()
        sys.exit(1)

    resultaten = []
    start = time.monotonic()
    try:
        for naam, functie in STAPPEN:
            if args.stap not in ("alle", naam):
                continue
            res = StapResultaat(naam)
            t0 = time.monotonic()
            try:
                functie(conn, res)
            except Exception as e:
                conn.rollback()
                res.mislukt = True
                print(f"   ❌ Stap '{naam}' afgebroken: {e}".rstrip())
            res.duur = time.monotonic() - t0
            resultaten.append(res)
    finally:
        conn.close()

    # PostgREST schema cache verversen is niet nodig (alleen data gewijzigd).
    print("\n" + "=" * 60)
    print("📋 Samenvatting")
    print("-" * 60)
    geslaagd = True
    for res in resultaten:
        te_veel = res.fout_pct > args.max_fouten_pct
        status = "❌" if (res.mislukt or te_veel) else ("⚠️ " if res.fouten else "✅")
        if res.mislukt or te_veel:
            geslaagd = False
        extra = " (afgebroken)" if res.mislukt else ""
        print(f"{status} {res.naam:<12} ok: {res.ok:>7}  fouten: {res.fouten:>6} ({res.fout_pct:.1f}%)"
              f"  {res.duur:6.1f}s{extra}")
        for regel in res.info:
            print(f"      {regel}")
    print("-" * 60)
    print(f"Totale duur: {time.monotonic() - start:.1f}s")
    if geslaagd:
        print("✅ Seed Fryslân voltooid.")
    else:
        print(f"❌ Seed Fryslân NIET volledig geslaagd (stap afgebroken of meer dan "
              f"{args.max_fouten_pct}% fouten). Zie de meldingen hierboven.")
    print("=" * 60)
    sys.exit(0 if geslaagd else 1)


if __name__ == "__main__":
    main()
