#!/usr/bin/env python3
"""
D-OmniTwin — Seed Script voor provincie Fryslân
================================================
Importeert de initiatie dataset (buurten + indicatorwaarden) naar de database.

Gebruik:
    python init_data/scripts/seed_fryslan.py [--stap alle|buurten|indicatoren|kompas|waarden]

Vereisten:
    pip install psycopg2-binary python-dotenv
    Database ingesteld via .env (zie .env.example)

Volgorde:
    1. buurten     → gebieden tabel (GeoJSON → PostGIS)
    2. indicatoren → indicatoren tabel (seed JSON)
    3. kompas      → kompas_* tabellen (hierarchie CSV)
    4. waarden     → gebied_data tabel (indicatorwaarden CSV)
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

# Laad .env bestand
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optioneel

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 niet gevonden. Installeer met: pip install psycopg2-binary")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.parent
INIT_DATA = ROOT / "init_data"

# Gebiedstype UUID voor CBS Buurten (uit schema_latest.sql seed)
CBS_BUURT_TYPE_ID = "afba67cb-6b38-4723-9c95-102a22d5b38a"


def get_db_connection():
    """Database connectie via environment variabelen."""
    return psycopg2.connect(
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
    )


# ─────────────────────────────────────────────────────────
# STAP 1: Buurten importeren
# ─────────────────────────────────────────────────────────
def import_buurten(conn):
    print("\n📍 STAP 1: Buurten importeren (GeoJSON → PostGIS)")
    print("-" * 50)

    geojson_path = INIT_DATA / "fryslan" / "buurten_fryslan.geojson"
    if not geojson_path.exists():
        print(f"❌ GeoJSON niet gevonden: {geojson_path}")
        print("   Voer eerst uit: python init_data/scripts/download_buurten_fryslan.py")
        return False

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"   📂 {len(features)} buurten geladen uit GeoJSON")

    cur = conn.cursor()

    # Zorg dat gemeenten tabel gevuld is (schema seed doet dit voor Friesland)
    cur.execute("SELECT COUNT(*) FROM gemeenten WHERE provincie = 'Fryslân'")
    gm_count = cur.fetchone()[0]
    print(f"   🏛️  {gm_count} Friese gemeenten in database")

    inserted = 0
    skipped = 0
    errors = 0

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        # Zoek buurtcode en -naam (PDOK WFS gebruikt verschillende property namen)
        bu_code = (props.get("buurtcode") or props.get("BU_CODE") or
                   props.get("statcode") or "").strip().replace("BU", "")
        bu_naam = (props.get("buurtnaam") or props.get("BU_NAAM") or
                   props.get("statnaam") or "Onbekend").strip()
        gm_code = (props.get("gemeentecode") or props.get("GM_CODE") or "").strip()
        gm_code = gm_code.replace("GM", "").zfill(4)

        if not bu_code:
            skipped += 1
            continue

        bu_id = f"BU{bu_code.zfill(8)}"

        # Geometrie als GeoJSON string → PostGIS
        geom_str = json.dumps(geom) if geom else None

        try:
            cur.execute("SAVEPOINT sp_buurt")
            cur.execute("""
                INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, geom, actief)
                VALUES (
                    %s, %s, %s, %s,
                    CASE WHEN %s IS NOT NULL
                         THEN ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 28992)
                         ELSE NULL END,
                    true
                )
                ON CONFLICT (id) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    gemeente_code = EXCLUDED.gemeente_code,
                    geom = EXCLUDED.geom,
                    updated_at = CURRENT_TIMESTAMP
            """, (bu_id, CBS_BUURT_TYPE_ID, bu_naam, gm_code or None,
                  geom_str, geom_str))
            cur.execute("RELEASE SAVEPOINT sp_buurt")
            inserted += 1

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_buurt")
            errors += 1
            if errors <= 3:
                print(f"   ⚠️  Fout bij {bu_id}: {e}")

    conn.commit()
    cur.close()
    markeer_waterbuurten(conn)

    print(f"   ✅ {inserted} buurten geïmporteerd | {skipped} overgeslagen | {errors} fouten")
    return True


def markeer_waterbuurten(conn):
    """Watervlag in gebieden.metadata zetten voor gebieden die alleen op naam een
    waterbuurt zijn (#155). Definitie: is_waterbuurt() in init_data/schema/08_zscore_referentie.sql."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT public.markeer_waterbuurten()")
        n = cur.fetchone()[0]
        conn.commit()
        if n:
            print(f"   💧 {n} waterbuurt(en) gemarkeerd op naam")
    except Exception as e:
        conn.rollback()
        print(f"   ⚠️  Watervlag niet gezet ({e}); voer migrations/schema_v21_zscore_referentie.sql uit")
    finally:
        cur.close()


# ─────────────────────────────────────────────────────────
# STAP 2: Indicatoren seeden
# ─────────────────────────────────────────────────────────
def import_indicatoren(conn):
    print("\n📊 STAP 2: Indicatoren seeden")
    print("-" * 50)

    seed_path = INIT_DATA / "indicatoren" / "indicatoren_seed.json"
    if not seed_path.exists():
        print(f"❌ Seed bestand niet gevonden: {seed_path}")
        return False

    with open(seed_path, encoding="utf-8") as f:
        indicatoren = json.load(f)

    print(f"   📂 {len(indicatoren)} indicatoren geladen")

    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for ind in indicatoren:
        naam = ind.get("naam", "").strip()
        if not naam:
            continue

        # Gebruik score_type uit seed, val terug op heuristiek
        score_type = ind.get("score_type")
        if not score_type:
            naam_lower = naam.lower()
            if any(kw in naam_lower for kw in ["afstand", "criminaliteit", "overlast",
                                                 "diefstal", "inbraak", "eenzaam",
                                                 "werkloos", "moeite"]):
                score_type = "+/-"
            else:
                score_type = "+/+"

        bron = ind.get("bron", "")
        eenheid = ind.get("eenheid", "")

        # Gebruik code uit seed, val terug op gegenereerde code
        code = ind.get("code")
        if not code:
            code = "IND_" + naam.upper()[:40].replace(" ", "_").replace("/", "_").replace(",", "").replace("-", "_")

        # Omschrijving: gebruik seed-veld of bouw op uit hiërarchie
        omschrijving = ind.get("omschrijving") or ""
        if not omschrijving:
            titel = ind.get("titel", "")
            thema = ind.get("thema", "")
            onderdeel = ind.get("onderdeel", "")
            if titel or thema:
                omschrijving = f"{titel} → {thema} → {onderdeel}"

        try:
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
            """, (naam, code, eenheid, omschrijving, bron, score_type))
            inserted += 1
        except Exception as e:
            skipped += 1
            if skipped <= 3:
                print(f"   ⚠️  Overgeslagen {naam}: {e}")

    conn.commit()
    cur.close()
    print(f"   ✅ {inserted} indicatoren geïmporteerd | {skipped} overgeslagen")
    return True


# ─────────────────────────────────────────────────────────
# STAP 3: Kompas hiërarchie laden
# ─────────────────────────────────────────────────────────
def import_kompas(conn):
    print("\n🧭 STAP 3: Kompas hiërarchie laden")
    print("-" * 50)

    csv_path = INIT_DATA / "kompas" / "kompas_hierarchie.csv"
    if not csv_path.exists():
        print(f"❌ CSV niet gevonden: {csv_path}")
        return False

    cur = conn.cursor()

    # Zorg dat er een Volledig Kompas configuratie is
    cur.execute("""
        INSERT INTO kompas_configuraties (naam, beschrijving, is_standaard, is_actief, icoon)
        VALUES ('Volledig Kompas',
                'Complete overzicht van alle indicatoren. Gegenereerd vanuit initiatie dataset.',
                TRUE, TRUE, '🌍')
        ON CONFLICT (naam) DO NOTHING
        RETURNING id
    """)
    row = cur.fetchone()
    if row:
        config_id = row[0]
    else:
        cur.execute("SELECT id FROM kompas_configuraties WHERE naam = 'Volledig Kompas'")
        config_id = cur.fetchone()[0]

    stats = {"titels": 0, "themas": 0, "onderdelen": 0, "gekoppeld": 0, "niet_gevonden": 0}

    def get_or_create(table, where_cols, insert_cols, values_dict):
        where = " AND ".join(f"{c} = %s" for c in where_cols)
        cur.execute(f"SELECT id FROM {table} WHERE {where}",
                    [values_dict[c] for c in where_cols])
        row = cur.fetchone()
        if row:
            return row[0]
        cols = ", ".join(insert_cols)
        placeholders = ", ".join("%s" for _ in insert_cols)
        cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) RETURNING id",
                    [values_dict[c] for c in insert_cols])
        return cur.fetchone()[0]

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            titel = row.get("Title", "").strip()
            thema = row.get("Thema", "").strip()
            onderdeel = row.get("Onderdeel", "").strip() or "(Algemeen)"
            indicator_swf = row.get("Indicator SWF", "").strip()
            actueel = row.get("Indicator actueel", "").strip().upper() == "J"

            if not titel or not thema:
                continue

            # Titel
            titel_id = get_or_create(
                "kompas_titels",
                ["naam", "config_id"],
                ["naam", "config_id"],
                {"naam": titel, "config_id": config_id}
            )
            stats["titels"] += 1

            # Thema
            thema_id = get_or_create(
                "kompas_themas",
                ["naam", "titel_id"],
                ["naam", "titel_id"],
                {"naam": thema, "titel_id": titel_id}
            )
            stats["themas"] += 1

            # Onderdeel
            onderdeel_id = get_or_create(
                "kompas_onderdelen",
                ["naam", "thema_id"],
                ["naam", "thema_id"],
                {"naam": onderdeel, "thema_id": thema_id}
            )
            stats["onderdelen"] += 1

            # Koppel indicator — gebruik 'Indicator' kolom als primair, 'Indicator SWF' als fallback
            indicator_naam = row.get("Indicator", "").strip()
            if not indicator_naam:
                indicator_naam = indicator_swf

            if indicator_naam:
                cur.execute(
                    "SELECT uuid FROM indicatoren WHERE naam ILIKE %s LIMIT 1",
                    (indicator_naam,)
                )
                ind_row = cur.fetchone()
                if ind_row:
                    cur.execute("""
                        INSERT INTO kompas_indicator_mapping
                            (config_id, indicator_uuid, onderdeel_id, is_actueel)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (config_id, indicator_uuid, onderdeel_id) DO UPDATE SET
                            is_actueel = EXCLUDED.is_actueel
                    """, (config_id, ind_row[0], onderdeel_id, actueel))
                    stats["gekoppeld"] += 1
                else:
                    stats["niet_gevonden"] += 1

    conn.commit()
    cur.close()

    print(f"   ✅ Kompas geladen:")
    print(f"      Titels: {len(set())} (uniek)")
    print(f"      Indicatoren gekoppeld: {stats['gekoppeld']}")
    print(f"      Indicatoren niet gevonden: {stats['niet_gevonden']}")
    return True


# ─────────────────────────────────────────────────────────
# STAP 4: Indicatorwaarden laden
# ─────────────────────────────────────────────────────────
def import_waarden(conn):
    print("\n📈 STAP 4: Indicatorwaarden laden")
    print("-" * 50)

    csv_path = INIT_DATA / "fryslan" / "indicatorwaarden_fryslan.csv"
    if not csv_path.exists():
        print(f"❌ CSV niet gevonden: {csv_path}")
        print("   Voer eerst uit: python init_data/scripts/download_indicatoren_fryslan.py")
        return False

    cur = conn.cursor()

    # Bouw indicator naam → uuid cache
    cur.execute("SELECT naam, uuid FROM indicatoren")
    indicator_cache = {row[0]: str(row[1]) for row in cur.fetchall()}

    # CBS-naam → DB-naam aliases (CBS OData namen ≠ seed JSON namen)
    # Let op: geef elke CBS-naam een UNIEKE target-indicator om duplicate-batch fouten te voorkomen
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
        "In bezit overige verhuurders":         "Particulier huurbezit",  # fix: was fout→Woningcorporatie
        "In bezit woningcorporatie":            "Woningcorporatie bezit",
        "Mantelzorger":                         "Mantelzorger",
        "Moeite met rondkomen":                 "Moeite met rondkomen",
        # Opleidingsniveau: directe match na rename in DB (geen alias meer nodig als seed opnieuw geladen)
        "Opleidingsniveau laag":                "Opleidingsniveau laag",
        "Opleidingsniveau hoog":                "Opleidingsniveau hoog",
        "Opleidingsniveau middelbaar":          "Opleidingsniveau middelbaar",
        "Overmatige drinker":                   "Overmatig drinken",  # fix: was fout→Roken
        "Roker":                                "Roken",
        "Personen met bijstand":                "Participatiewet totaal",
        "Voldoet aan beweegrichtlijn":          "Bewegen",  # fix: was fout→Gezondheid
        "Vrijwilligerswerk":                    "Vrijwilliger",
        # Woningvoorraad: directe match na toevoeging indicator in DB
        # (geen alias nodig — naam in CBS en DB zijn identiek)
    }

    # Breid cache uit met aliases
    for cbs_naam, db_naam in CBS_ALIASES.items():
        if cbs_naam not in indicator_cache and db_naam in indicator_cache:
            indicator_cache[cbs_naam] = indicator_cache[db_naam]

    print(f"   📋 {len(indicator_cache)} indicatoren in cache (incl. {len(CBS_ALIASES)} CBS-aliassen)")

    inserted = 0
    skipped_ind = 0
    skipped_gebied = 0
    errors = 0

    batch = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buurt_id = row.get("buurt_id", "").strip()
            indicator_naam = row.get("indicator_naam", "").strip()
            waarde_str = row.get("waarde", "").strip()
            jaar_str = row.get("jaar", "").strip()
            bron = row.get("bron", "").strip()

            # BU prefix normaliseren
            if not buurt_id.startswith("BU"):
                buurt_id = f"BU{buurt_id.zfill(8)}"

            indicator_uuid = indicator_cache.get(indicator_naam)
            if not indicator_uuid:
                skipped_ind += 1
                continue

            try:
                waarde = float(waarde_str)
                jaar = int(jaar_str) if jaar_str else None
            except ValueError:
                errors += 1
                continue

            batch.append((buurt_id, indicator_uuid, waarde, jaar, bron))

            # Batch inserts van 500 rijen
            if len(batch) >= 500:
                # Dedupliceer op (gebied_id, indicator_uuid, jaar) — voorkomt ON CONFLICT errors
                seen = {}
                for b in batch:
                    key = (b[0], b[1], b[3])  # gebied_id, indicator_uuid, jaar
                    seen[key] = b
                deduped = list(seen.values())
                try:
                    execute_values(cur, """
                        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
                        VALUES %s
                        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
                            waarde = EXCLUDED.waarde,
                            bron = EXCLUDED.bron,
                            updated_at = CURRENT_TIMESTAMP
                    """, [(b[0], b[1], b[2], b[3], b[4], "current") for b in deduped])
                    inserted += len(deduped)
                    conn.commit()
                except Exception as e:
                    errors += len(deduped)
                    if errors <= 5:
                        print(f"   ⚠️  Batch fout: {e}")
                    conn.rollback()
                batch = []

    # Resterende batch
    if batch:
        seen = {}
        for b in batch:
            key = (b[0], b[1], b[3])
            seen[key] = b
        deduped = list(seen.values())
        try:
            execute_values(cur, """
                INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
                VALUES %s
                ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
                    waarde = EXCLUDED.waarde,
                    bron = EXCLUDED.bron,
                    updated_at = CURRENT_TIMESTAMP
            """, [(b[0], b[1], b[2], b[3], b[4], "current") for b in deduped])
            inserted += len(deduped)
            conn.commit()
        except Exception as e:
            errors += len(deduped)
            print(f"   ⚠️  Resterende batch fout: {e}")

    cur.close()
    print(f"   ✅ {inserted} metingen geladen")
    print(f"   ⏭️  Overgeslagen (indicator onbekend): {skipped_ind}")
    print(f"   ❌ Fouten: {errors}")
    return True


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Seed Fryslân initiatie dataset"
    )
    parser.add_argument(
        "--stap",
        choices=["alle", "buurten", "indicatoren", "kompas", "waarden", "admin"],
        default="alle",
        help="Welke stap uitvoeren (default: alle)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌍 D-OmniTwin — Seed Fryslân Initiatie Dataset")
    print("=" * 60)

    try:
        conn = get_db_connection()
        print("✅ Database verbinding OK")
    except Exception as e:
        print(f"❌ Database verbinding mislukt: {e}")
        print("   Controleer je .env bestand (DATABASE_HOST, DATABASE_NAME, etc.)")
        sys.exit(1)

    stap = args.stap

    if stap in ("alle", "buurten"):
        import_buurten(conn)

    if stap in ("alle", "indicatoren"):
        import_indicatoren(conn)

    if stap in ("alle", "kompas"):
        import_kompas(conn)

    if stap in ("alle", "waarden"):
        import_waarden(conn)

    conn.close()

    if stap in ("alle", "admin"):
        # Admin aanmaken via apart script (heeft eigen DB conn + interactie)
        import subprocess
        admin_script = ROOT / "init_data" / "scripts" / "create_admin.py"
        subprocess.run([sys.executable, str(admin_script)], check=False)

    print()
    print("=" * 60)
    print("✅ Seed voltooid!")
    print()
    print("   🌐 Open de applicatie: http://localhost:8000")
    print("   📚 API docs:           http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
