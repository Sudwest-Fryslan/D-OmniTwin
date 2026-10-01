#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 1: Database Schema Initialiseren
=======================================================
Laadt het volledige schema (tabellen, views, triggers, seed data)
naar een doeldatabase naar keuze.

Gebruik:
    cd ETL/local
    python etl_01_init_schema.py

    # Of met expliciete database URL:
    DATABASE_HOST=mijn-server.nl DATABASE_NAME=mijn_db python etl_01_init_schema.py

    # Alleen verificatie, geen wijzigingen:
    python etl_01_init_schema.py --check

    # Schema forceren herladen (DROP CASCADE — GEVAARLIJK op productie!):
    python etl_01_init_schema.py --force-reset

Vereisten:
    pip install psycopg2-binary
    PostgreSQL met PostGIS en pgvector extensies

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini
"""

import sys
import argparse
from pathlib import Path

# Voeg de local map toe aan het pad voor db_connect
LOCAL_DIR    = Path(__file__).resolve().parent
ETL_DIR      = LOCAL_DIR.parent
PROJECT_ROOT = ETL_DIR.parent
SCHEMA_PATH  = PROJECT_ROOT / "db" / "schema" / "schema_latest.sql"

sys.path.insert(0, str(LOCAL_DIR))
from db_connect import get_connection


def check_extensions(conn) -> bool:
    """Controleer of PostGIS en pgvector beschikbaar zijn."""
    cur = conn.cursor()
    ok = True

    for ext_name in ("postgis", "vector"):
        try:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = %s", (ext_name,))
            row = cur.fetchone()
            if row:
                print(f"  ✅ {ext_name} v{row[0]}")
            else:
                # Probeer aan te maken
                cur.execute(f"CREATE EXTENSION IF NOT EXISTS {ext_name};")
                conn.commit()
                cur.execute("SELECT extversion FROM pg_extension WHERE extname = %s", (ext_name,))
                row = cur.fetchone()
                if row:
                    print(f"  ✅ {ext_name} v{row[0]} (zojuist geactiveerd)")
                else:
                    print(f"  ❌ {ext_name} — niet beschikbaar op deze server")
                    print(f"     Zie docs/archief/GETTING_STARTED.md voor installatie-instructies")
                    ok = False
        except Exception as e:
            conn.rollback()
            print(f"  ❌ {ext_name} — fout: {e}")
            ok = False

    cur.close()
    return ok


def count_objects(conn) -> dict:
    """Tel bestaande tabellen, views en rijen."""
    cur = conn.cursor()
    result = {}

    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    result["tabellen"] = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM information_schema.views
        WHERE table_schema = 'public'
    """)
    result["views"] = cur.fetchone()[0]

    # Check sleuteltabellen
    for tabel in ("indicatoren", "gebieden", "gebied_data", "kompas_indicator_mapping"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tabel}")
            result[tabel] = cur.fetchone()[0]
        except Exception:
            result[tabel] = None

    cur.close()
    return result


def run_schema(conn, force_reset: bool = False):
    """Voer het schema SQL uit."""
    if not SCHEMA_PATH.exists():
        print(f"❌ Schema bestand niet gevonden: {SCHEMA_PATH}")
        print("   Verwacht: db/schema/schema_latest.sql")
        sys.exit(1)

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema_sql = f.read()

    cur = conn.cursor()

    if force_reset:
        print("\n⚠️  FORCE RESET: alle tabellen worden verwijderd en opnieuw aangemaakt!")
        print("   Druk Ctrl+C om te annuleren (5 seconden)...")
        import time
        time.sleep(5)
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()
        print("   ✅ Schema geleegd")

    print(f"\n📄 Schema laden uit: {SCHEMA_PATH.name}")
    print(f"   Grootte: {len(schema_sql):,} tekens")

    try:
        cur.execute(schema_sql)
        conn.commit()
        print("   ✅ Schema succesvol uitgevoerd")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Schema fout: {e}")
        print("\n   Hint: Als tabellen al bestaan, gebruik dan --force-reset")
        print("   (LET OP: dit wist alle data!)")
        sys.exit(1)

    cur.close()


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Database schema initialiseren",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_01_init_schema.py
  python etl_01_init_schema.py --check
  python etl_01_init_schema.py --force-reset
  DATABASE_HOST=prod.server.nl python etl_01_init_schema.py
        """
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Alleen controleren, geen schema laden"
    )
    parser.add_argument(
        "--force-reset", action="store_true",
        help="Schema leegmaken en opnieuw aanmaken (WIST ALLE DATA!)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🗄️  D-OmniTwin — Stap 1: Schema Initialiseren")
    print("=" * 60)

    conn = get_connection()

    # ── Extensies controleren ──
    print("\n🔌 Extensies controleren:")
    ext_ok = check_extensions(conn)
    if not ext_ok:
        print("\n❌ Verplichte extensies ontbreken. Installeer PostGIS en pgvector eerst.")
        print("   Zie docs/archief/GETTING_STARTED.md voor instructies.")
        sys.exit(1)

    # ── Huidige staat ──
    print("\n📊 Huidige database staat:")
    before = count_objects(conn)
    print(f"  Tabellen:  {before['tabellen']}")
    print(f"  Views:     {before['views']}")
    for tabel in ("indicatoren", "gebieden", "gebied_data"):
        val = before.get(tabel)
        if val is not None:
            print(f"  {tabel}: {val:,} rijen")
        else:
            print(f"  {tabel}: (tabel bestaat nog niet)")

    if args.check:
        print("\n✅ Check voltooid (--check flag: geen wijzigingen gemaakt)")
        conn.close()
        return

    # ── Schema uitvoeren ──
    run_schema(conn, force_reset=args.force_reset)

    # ── Resultaat ──
    print("\n📊 Database staat na initialisatie:")
    after = count_objects(conn)
    print(f"  Tabellen:  {after['tabellen']}")
    print(f"  Views:     {after['views']}")

    print("\n" + "=" * 60)
    print("✅ Stap 1 voltooid!")
    print()
    print("   Volgende stap:")
    print("   python etl_02_import_geometrie.py")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
