#!/usr/bin/env python3
"""
D-OmniTwin — Load Sample Dataset
================================
Laadt de minimale, zelfstandige sample dataset (12 SWF buurten) in de database.
Bedoeld voor snelle start, tests en demonstraties zonder externe data-downloads.

Gebruik:
    python init_data/scripts/load_sample.py [--stap alle|definities|stuurdata|buurten|indicatoren|kompas|waarden]

    'definities' laadt het product zonder data (stuurdata, indicatordefinities, Kompas).
    De data (gebieden en waarden) komt uit de use cases: init_data/scripts/laad_usecase.py.

Vereisten:
    Database schema geladen via: db/schema/schema_latest.sql (db-init)
    .env geconfigureerd (DATABASE_HOST, DATABASE_PORT, etc.)
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Laad .env bestand
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 niet gevonden. Installeer met: pip install psycopg2-binary")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # download_cbs_kerncijfers
SAMPLE_DIR = ROOT / "init_data" / "sample"
STUURDATA_SQL = ROOT / "db" / "stuurdata" / "stuurdata_seed.sql"
BUURTEN_GEOJSON = SAMPLE_DIR / "2_brondata" / "sample_buurten.geojson"
INDICATOREN_CSV = SAMPLE_DIR / "2_brondata" / "sample_indicatoren.csv"
STANDAARD_INDICATOREN_CSV = INDICATOREN_CSV
KOMPAS_CSV = ROOT / "db" / "stuurdata" / "kompas_hierarchie.csv"
# Vulling van andere Kompasprofielen (bijv. Klimaat Kompas, #256): db/stuurdata/kompasprofiel_*.json
KOMPASPROFIELEN = sorted((ROOT / "db" / "stuurdata").glob("kompasprofiel_*.json"))
# Indicatordefinities van de use cases (geen waarden): uuid, naam, eenheid, categorie, richting, herkomst (#236)
DEFINITIES_CSV = ROOT / "db" / "stuurdata" / "indicatoren.csv"

CBS_BUURT_TYPE_ID = "afba67cb-6b38-4723-9c95-102a22d5b38a"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jaargang_controle import (  # noqa: E402
    controleer_jaargangen, geometrie_codes, geometrie_jaar_sample, rapporteer,
)


def get_db_connection():
    """Database connectie via environment variabelen."""
    host = os.environ.get("DATABASE_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    port = int(os.environ.get("DATABASE_PORT", 5432))
    dbname = os.environ.get("DATABASE_NAME", "omnitwin_db")
    user = os.environ.get("DATABASE_USER", "omnitwin_user")
    password = os.environ.get("DATABASE_PASSWORD", "")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
    )


# ─────────────────────────────────────────────────────────
# STAP 1: Stuurdata importeren
# ─────────────────────────────────────────────────────────
def import_stuurdata(conn):
    print("\n⚙️  STAP 1: Stuurdata importeren (stuurdata_seed.sql)")
    print("-" * 50)

    if not STUURDATA_SQL.exists():
        print(f"❌ Bestand niet gevonden: {STUURDATA_SQL}")
        return False

    with open(STUURDATA_SQL, "r", encoding="utf-8") as f:
        sql = f.read()

    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print(f"   ✅ Stuurdata succesvol uitgevoerd vanuit {STUURDATA_SQL.name}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Fout bij stuurdata import: {e}")
        return False
    finally:
        cur.close()


# ─────────────────────────────────────────────────────────
# STAP 2: Buurten importeren
# ─────────────────────────────────────────────────────────
def import_buurten(conn):
    print("\n📍 STAP 2: Buurten importeren (sample_buurten.geojson → PostGIS)")
    print("-" * 50)

    if not BUURTEN_GEOJSON.exists():
        print(f"❌ GeoJSON niet gevonden: {BUURTEN_GEOJSON}")
        return False

    with open(BUURTEN_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"   📂 {len(features)} buurten gevonden in GeoJSON")

    # Geometrie-jaargang vastleggen in gebieden.metadata (#119)
    geo_jaar = geometrie_jaar_sample()
    geo_meta = json.dumps({"geometrie_jaar": geo_jaar, "geometrie_bron": "CBS Wijk- en buurtkaart"}
                          if geo_jaar else {})
    print(f"   🗓️  Geometrie-jaargang: {geo_jaar or 'onbekend'}")

    cur = conn.cursor()
    inserted = 0
    errors = 0

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        bu_id = props.get("id")
        naam = props.get("naam", "Onbekend")
        gm_code = props.get("gemeente_code", "1900")
        type_id = props.get("gebiedstype_id") or CBS_BUURT_TYPE_ID
        prov = props.get("provincienaam", "Fryslân")

        if not bu_id:
            continue

        geom_str = json.dumps(geom) if geom else None

        try:
            cur.execute("SAVEPOINT sp_buurt")
            cur.execute("""
                INSERT INTO gebieden (id, gebiedstype_id, naam, gemeente_code, geom, provincienaam, actief, metadata)
                VALUES (
                    %s, %s, %s, %s,
                    CASE WHEN %s IS NOT NULL
                         THEN ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 28992))
                         ELSE NULL END,
                    %s,
                    TRUE,
                    %s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    gemeente_code = EXCLUDED.gemeente_code,
                    gebiedstype_id = EXCLUDED.gebiedstype_id,
                    geom = EXCLUDED.geom,
                    provincienaam = EXCLUDED.provincienaam,
                    actief = TRUE,
                    metadata = COALESCE(gebieden.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP;
            """, (bu_id, type_id, naam, gm_code, geom_str, geom_str, prov, geo_meta))
            cur.execute("RELEASE SAVEPOINT sp_buurt")
            inserted += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_buurt")
            errors += 1
            if errors <= 3:
                print(f"   ⚠️  Fout bij {bu_id} ({naam}): {e}")

    conn.commit()
    cur.close()
    markeer_waterbuurten(conn)

    print(f"   ✅ {inserted} buurten geïmporteerd / bijgewerkt | {errors} fouten")
    return errors == 0


def markeer_waterbuurten(conn):
    """Watervlag in gebieden.metadata zetten voor gebieden die alleen op naam een
    waterbuurt zijn (#155). Definitie: is_waterbuurt() in db/schema/08_zscore_referentie.sql."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT public.markeer_waterbuurten()")
        n = cur.fetchone()[0]
        conn.commit()
        if n:
            print(f"   💧 {n} waterbuurt(en) gemarkeerd op naam")
    except Exception as e:
        conn.rollback()
        print(f"   ⚠️  Watervlag niet gezet ({e}); voer python -m omnitwin.migraties uit (V021)")
    finally:
        cur.close()


# ─────────────────────────────────────────────────────────
# STAP 3: Indicatoren importeren
# ─────────────────────────────────────────────────────────
def import_indicatoren(conn):
    # Standaard: de definities uit de stuurdata (db/stuurdata/indicatoren.csv); de waarden komen uit
    # open bronnen via de use cases. Een andere CSV (extra brondata van een use case): metadata daaruit.
    standaard = INDICATOREN_CSV == STANDAARD_INDICATOREN_CSV
    bron_csv = DEFINITIES_CSV if standaard else INDICATOREN_CSV
    print(f"\n📊 STAP 3: Indicatoren importeren (definities uit {bron_csv.name})")
    print("-" * 50)

    if not bron_csv.exists():
        print(f"❌ CSV niet gevonden: {bron_csv}")
        return False

    unique_indicators = {}
    with open(bron_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uuid = (row.get("uuid") or row.get("indicator_uuid") or "").strip()
            if not uuid:
                continue
            if uuid not in unique_indicators:
                unique_indicators[uuid] = {
                    "uuid": uuid,
                    "naam": (row.get("naam") or row.get("indicator_naam") or "").strip(),
                    "eenheid": row.get("eenheid", "").strip() or None,
                    "categorie": row.get("categorie", "").strip() or None,
                    "interpretatie_logica": row.get("interpretatie_logica", "").strip() or "pos_is_pos",
                    "bron": row.get("bron", "").strip() or None,
                }

    print(f"   📂 {len(unique_indicators)} indicatoren in {bron_csv.name}")

    # CBS Kerncijfers: de waarden worden gedownload (use case cbs-kerncijfers), de definities horen bij
    # de stuurdata en komen uit het recept (download_cbs_kerncijfers.INDICATOREN), niet uit de sample.
    if standaard:
        import download_cbs_kerncijfers as cbs
        voor = len(unique_indicators)
        for naam, (ind_uuid, eenheid, logica, categorie) in cbs.INDICATOREN.items():
            unique_indicators.setdefault(ind_uuid, {
                "uuid": ind_uuid, "naam": naam, "eenheid": eenheid or None, "categorie": categorie or None,
                "interpretatie_logica": logica or "pos_is_pos", "bron": "CBS Kerncijfers wijken en buurten",
            })
        print(f"   📂 {len(unique_indicators) - voor} CBS-indicatoren uit het recept (init_data/cbs)")

    cur = conn.cursor()
    inserted = 0
    errors = 0

    for uuid, ind in unique_indicators.items():
        naam = ind["naam"]
        # Code genereren
        clean_name = "".join(c if c.isalnum() else "_" for c in naam.upper())[:30]
        code = f"IND_{clean_name}_{uuid[:8]}"

        # Score type afleiden
        score_type = "+/-" if ind["interpretatie_logica"] == "-/+" else "+/+"

        try:
            cur.execute("SAVEPOINT sp_ind")
            cur.execute("""
                INSERT INTO indicatoren (uuid, naam, code, eenheid, categorie, interpretatie_logica, bron, score_type, status, is_actief)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'O', TRUE)
                ON CONFLICT (uuid) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    eenheid = COALESCE(EXCLUDED.eenheid, indicatoren.eenheid),
                    categorie = COALESCE(EXCLUDED.categorie, indicatoren.categorie),
                    interpretatie_logica = COALESCE(EXCLUDED.interpretatie_logica, indicatoren.interpretatie_logica),
                    bron = COALESCE(EXCLUDED.bron, indicatoren.bron),
                    score_type = EXCLUDED.score_type,
                    is_actief = TRUE,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                uuid,
                naam,
                code,
                ind["eenheid"],
                ind["categorie"],
                ind["interpretatie_logica"],
                ind["bron"],
                score_type,
            ))
            cur.execute("RELEASE SAVEPOINT sp_ind")
            inserted += 1
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_ind")
            errors += 1
            if errors <= 3:
                print(f"   ⚠️  Fout bij indicator {naam} ({uuid}): {e}")

    conn.commit()
    cur.close()

    print(f"   ✅ {inserted} indicatoren geïmporteerd / bijgewerkt | {errors} fouten")
    return errors == 0


# ─────────────────────────────────────────────────────────
# STAP 4: Kompas hiërarchie koppelen
# ─────────────────────────────────────────────────────────
def import_kompas(conn):
    print("\n🧭 STAP 4: Kompas hiërarchie koppelen")
    print("-" * 50)

    if not KOMPAS_CSV.exists():
        print(f"   ℹ️  Geen kompas_hierarchie.csv gevonden op {KOMPAS_CSV}, sla over.")
        return True

    cur = conn.cursor()

    # Zorg dat er een Volledig Kompas configuratie is (id=1)
    cur.execute("""
        INSERT INTO kompas_configuraties (id, naam, beschrijving, is_standaard, is_actief, icoon, versie)
        VALUES (1, 'Volledig Kompas',
                'Complete overzicht van alle indicatoren over alle thema''s. Geeft een 360° beeld van de leefomgeving.',
                TRUE, TRUE, '🌍', 1)
        ON CONFLICT (id) DO NOTHING;
    """)
    conn.commit()

    config_id = 1

    stats = {"gekoppeld": 0, "overgeslagen": 0}

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

    with open(KOMPAS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            titel = row.get("Title", "").strip()
            thema = row.get("Thema", "").strip()
            onderdeel = row.get("Onderdeel", "").strip() or "(Algemeen)"
            indicator_naam = row.get("Indicator", "").strip() or row.get("Indicator SWF", "").strip()
            actueel = row.get("Indicator actueel", "").strip().upper() == "J"

            if not titel or not thema:
                continue

            titel_id = get_or_create(
                "kompas_titels",
                ["naam", "config_id"],
                ["naam", "config_id"],
                {"naam": titel, "config_id": config_id}
            )

            thema_id = get_or_create(
                "kompas_themas",
                ["naam", "titel_id"],
                ["naam", "titel_id"],
                {"naam": thema, "titel_id": titel_id}
            )

            onderdeel_id = get_or_create(
                "kompas_onderdelen",
                ["naam", "thema_id"],
                ["naam", "thema_id"],
                {"naam": onderdeel, "thema_id": thema_id}
            )

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
                    stats["overgeslagen"] += 1

    conn.commit()
    cur.close()

    print(f"   ✅ Kompas mapping bijgewerkt: {stats['gekoppeld']} indicatoren gekoppeld")
    return True


def import_kompasprofielen(conn, bestanden=None):
    """
    Andere Kompasprofielen vullen uit db/stuurdata/kompasprofiel_*.json (#256): profiel (naam),
    classificatie en indicatoren (kwadrant, thema, onderdeel, indicator_uuid). Alleen als het
    profiel bestaat en nog geen indicatoren heeft: een eigen inrichting wordt nooit overschreven.
    Een indicator die (nog) niet bestaat, wordt overgeslagen. Idempotent.
    """
    bestanden = KOMPASPROFIELEN if bestanden is None else bestanden
    cur = conn.cursor()
    for pad in bestanden:
        profiel = json.loads(Path(pad).read_text(encoding="utf-8"))
        cur.execute("SELECT id FROM kompas_configuraties WHERE naam = %s", (profiel["profiel"],))
        row = cur.fetchone()
        if not row:
            print(f"   ℹ️  Kompasprofiel '{profiel['profiel']}' bestaat niet, sla {Path(pad).name} over.")
            continue
        config_id = row[0]
        cur.execute("SELECT count(*) FROM kompas_indicator_mapping WHERE config_id = %s", (config_id,))
        if cur.fetchone()[0] > 0:
            print(f"   ℹ️  Kompasprofiel '{profiel['profiel']}' is al ingericht, niet overschreven.")
            continue
        gekoppeld, overgeslagen = 0, []
        for volgorde, ind in enumerate(profiel["indicatoren"]):
            cur.execute("SELECT 1 FROM indicatoren WHERE uuid = %s", (ind["indicator_uuid"],))
            if not cur.fetchone():
                overgeslagen.append(ind.get("indicator_naam") or ind["indicator_uuid"])
                continue
            ids = []
            for tabel, ouder_kolom, ouder, naam in (
                ("kompas_titels", "config_id", config_id, ind["kwadrant"]),
                ("kompas_themas", "titel_id", None, ind["thema"]),
                ("kompas_onderdelen", "thema_id", None, ind.get("onderdeel") or "(Algemeen)"),
            ):
                ouder = ouder if ouder is not None else ids[-1]
                cur.execute(f"SELECT id FROM {tabel} WHERE naam = %s AND {ouder_kolom} = %s", (naam, ouder))
                r = cur.fetchone()
                if not r:
                    cur.execute(f"INSERT INTO {tabel} (naam, {ouder_kolom}, volgorde) VALUES (%s, %s, %s) RETURNING id",
                                (naam, ouder, volgorde))
                    r = cur.fetchone()
                ids.append(r[0])
            cur.execute("""
                INSERT INTO kompas_indicator_mapping (config_id, indicator_uuid, onderdeel_id, is_actueel)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (config_id, indicator_uuid, onderdeel_id) DO NOTHING
            """, (config_id, ind["indicator_uuid"], ids[-1]))
            gekoppeld += 1
        if gekoppeld and profiel.get("classificatie"):
            cur.execute("UPDATE kompas_configuraties SET classificatie = %s WHERE id = %s",
                        (profiel["classificatie"], config_id))
        conn.commit()
        print(f"   ✅ Kompasprofiel '{profiel['profiel']}': {gekoppeld} indicatoren gekoppeld"
              + (f", classificatie {profiel['classificatie']}" if gekoppeld and profiel.get("classificatie") else "")
              + (f"; overgeslagen (bestaat niet): {', '.join(overgeslagen)}" if overgeslagen else ""))
    cur.close()
    return True


# ─────────────────────────────────────────────────────────
# STAP 5: Indicatorwaarden importeren
# ─────────────────────────────────────────────────────────
def import_waarden(conn):
    print("\n📈 STAP 5: Indicatorwaarden laden (sample_indicatoren.csv → gebied_data)")
    print("-" * 50)

    if not INDICATOREN_CSV.exists():
        print(f"❌ CSV niet gevonden: {INDICATOREN_CSV}")
        return False

    # Jaargangcontrole tegen de geometrie (#119): alleen waarschuwingen
    geo_jaar = geometrie_jaar_sample()
    with open(INDICATOREN_CSV, "r", encoding="utf-8") as f:
        controle = controleer_jaargangen(csv.DictReader(f), geometrie_codes(BUURTEN_GEOJSON), geo_jaar)
    rapporteer(*controle, geo_jaar)

    cur = conn.cursor()

    # Valideer aanwezige indicatoren en buurten
    cur.execute("SELECT uuid FROM indicatoren")
    valid_uuids = {str(r[0]) for r in cur.fetchall()}

    cur.execute("SELECT id FROM gebieden WHERE actief = true")
    valid_gebieden = {r[0] for r in cur.fetchall()}

    inserted = 0
    skipped = 0
    errors = 0
    batch = []

    with open(INDICATOREN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buurt_id = row.get("gebied_id", "").strip()
            ind_uuid = row.get("indicator_uuid", "").strip()
            waarde_str = row.get("waarde", "").strip()
            jaar_str = row.get("jaar", "").strip()
            bron = row.get("bron", "").strip() or None
            kwaliteit = row.get("kwaliteit", "").strip() or None
            scenario_id = row.get("scenario_id", "").strip() or "current"

            if ind_uuid not in valid_uuids or buurt_id not in valid_gebieden:
                skipped += 1
                continue

            try:
                waarde = float(waarde_str)
                jaar = int(jaar_str) if jaar_str else None
            except ValueError:
                errors += 1
                continue

            batch.append((buurt_id, ind_uuid, waarde, jaar, bron, kwaliteit, scenario_id))

            if len(batch) >= 250:
                # Dedupliceer op (gebied_id, indicator_uuid, jaar, scenario_id)
                seen = {}
                for b in batch:
                    key = (b[0], b[1], b[3], b[6])
                    seen[key] = b
                deduped = list(seen.values())

                try:
                    execute_values(cur, """
                        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id)
                        VALUES %s
                        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
                            waarde = EXCLUDED.waarde,
                            bron = EXCLUDED.bron,
                            kwaliteit = EXCLUDED.kwaliteit,
                            updated_at = CURRENT_TIMESTAMP;
                    """, deduped)
                    inserted += len(deduped)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    errors += len(deduped)
                    if errors <= 3:
                        print(f"   ⚠️  Batch fout: {e}")
                batch = []

    if batch:
        seen = {}
        for b in batch:
            key = (b[0], b[1], b[3], b[6])
            seen[key] = b
        deduped = list(seen.values())
        try:
            execute_values(cur, """
                INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, kwaliteit, scenario_id)
                VALUES %s
                ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) DO UPDATE SET
                    waarde = EXCLUDED.waarde,
                    bron = EXCLUDED.bron,
                    kwaliteit = EXCLUDED.kwaliteit,
                    updated_at = CURRENT_TIMESTAMP;
            """, deduped)
            inserted += len(deduped)
            conn.commit()
        except Exception as e:
            conn.rollback()
            errors += len(deduped)
            print(f"   ⚠️  Resterende batch fout: {e}")

    cur.close()
    print(f"   ✅ {inserted} metingen geladen | {skipped} overgeslagen | {errors} fouten")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Laad Sample Dataset (Súdwest-Fryslân)"
    )
    parser.add_argument(
        "--stap",
        choices=["alle", "definities", "stuurdata", "buurten", "indicatoren", "kompas", "waarden"],
        default="alle",
        help="Welke stap uitvoeren (default: alle). 'definities' = stuurdata, indicatoren en Kompas, "
             "zonder gebieden en waarden; die komen uit de use cases (laad_usecase.py)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 D-OmniTwin — Sample Dataset Loader (Issue #52)")
    print("=" * 60)

    try:
        conn = get_db_connection()
        print("✅ Database verbinding succesvol tot stand gebracht")
    except Exception as e:
        print(f"❌ Database verbinding mislukt: {e}", file=sys.stderr)
        print("   Controleer of de database draait en .env juist is ingesteld.")
        sys.exit(1)

    stap = args.stap
    success = True

    try:
        if stap in ("alle", "definities", "stuurdata"):
            if not import_stuurdata(conn):
                success = False

        if stap in ("alle", "buurten") and success:
            if not import_buurten(conn):
                success = False

        if stap in ("alle", "definities", "indicatoren") and success:
            if not import_indicatoren(conn):
                success = False

        if stap in ("alle", "definities", "kompas") and success:
            if not import_kompas(conn):
                success = False
            elif not import_kompasprofielen(conn):
                success = False

        if stap in ("alle", "waarden") and success:
            if not import_waarden(conn):
                success = False

    finally:
        conn.close()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Sample dataset import succesvol voltooid!")
        print("   Start de app via: python run_dev.py (of docker compose up)")
        print("   Open in browser:  http://localhost:8000 (of http://localhost)")
    else:
        print("⚠️  Import voltooid met één of meer waarschuwingen/fouten.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
