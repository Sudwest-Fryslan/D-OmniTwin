#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 5: Kompas Hiërarchie Importeren
=======================================================
Laadt de kompas-hiërarchie (Titel → Thema → Onderdeel → Indicator)
vanuit een CSV bestand naar de kompas_* tabellen.

Dit is een volledige vervanging voor ETL/Kompas/import_kompas_hierarchie.py,
maar dan werkend met db.ini/omgevingsvariabelen in plaats van config.ini.

Gebruik:
    cd ETL/local
    python etl_05_import_kompas.py

    # Alternatief CSV bestand:
    python etl_05_import_kompas.py --bestand /pad/naar/mijn_kompas.csv

    # Eerst bestaande kompas data wissen:
    python etl_05_import_kompas.py --reset

    # Overzicht van huidige kompas structuur:
    python etl_05_import_kompas.py --check

CSV formaat (verwachte kolomnamen):
    Title, Thema, Onderdeel, Indicator, Indicator actueel, Bron, Indicator SWF

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini
"""

import sys
import csv
import argparse
from pathlib import Path

LOCAL_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_DIR.parent.parent
DEFAULT_CSV  = PROJECT_ROOT / "db" / "stuurdata" / "kompas_hierarchie.csv"

sys.path.insert(0, str(LOCAL_DIR))
from db_connect import get_connection


def get_or_create(cur, table: str, where_cols: list, values: dict) -> int:
    """Haal bestaande rij op of maak nieuwe aan. Geeft ID terug."""
    where_sql = " AND ".join(f"{c} = %s" for c in where_cols)
    cur.execute(f"SELECT id FROM {table} WHERE {where_sql}",
                [values[c] for c in where_cols])
    row = cur.fetchone()
    if row:
        return row[0]

    cols    = ", ".join(values.keys())
    holders = ", ".join("%s" for _ in values)
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({holders}) RETURNING id",
                list(values.values()))
    return cur.fetchone()[0]


def find_indicator_uuid(cur, indicator_naam: str, indicator_swf: str) -> str | None:
    """
    Zoek indicator UUID — probeert SWF naam eerst, daarna normale naam.
    """
    for naam in filter(None, [indicator_swf, indicator_naam]):
        naam = naam.strip()
        if not naam:
            continue
        cur.execute("SELECT uuid FROM indicatoren WHERE naam ILIKE %s LIMIT 1", (naam,))
        row = cur.fetchone()
        if row:
            return str(row[0])
    return None


def reset_kompas(conn, config_naam: str = "Volledig Kompas"):
    """Verwijder alle bestaande kompas data voor de gegeven configuratie."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM kompas_configuraties WHERE naam = %s", (config_naam,))
    row = cur.fetchone()
    if row:
        config_id = row[0]
        cur.execute("DELETE FROM kompas_indicator_mapping WHERE config_id = %s", (config_id,))
        cur.execute("DELETE FROM kompas_onderdelen WHERE thema_id IN (SELECT id FROM kompas_themas WHERE titel_id IN (SELECT id FROM kompas_titels WHERE config_id = %s))", (config_id,))
        cur.execute("DELETE FROM kompas_themas WHERE titel_id IN (SELECT id FROM kompas_titels WHERE config_id = %s)", (config_id,))
        cur.execute("DELETE FROM kompas_titels WHERE config_id = %s", (config_id,))
        conn.commit()
        print(f"  🗑️  Bestaande kompas data gewist voor '{config_naam}'")
    cur.close()


def import_kompas(conn, csv_pad: Path, config_naam: str = "Volledig Kompas") -> dict:
    """
    Importeer kompas hiërarchie uit CSV.

    Returns:
        Dict met statistieken
    """
    cur = conn.cursor()
    stats = {
        "rijen": 0,
        "titels": set(),
        "themas": set(),
        "onderdelen": set(),
        "gekoppeld": 0,
        "niet_gevonden": 0,
    }

    # Zorg dat de configuratie bestaat
    cur.execute("""
        INSERT INTO kompas_configuraties (naam, beschrijving, is_standaard, is_actief, icoon)
        VALUES (%s, %s, TRUE, TRUE, '🌍')
        ON CONFLICT (naam) DO NOTHING
        RETURNING id
    """, (config_naam, f"Geïmporteerd vanuit {csv_pad.name}"))
    row = cur.fetchone()
    if row:
        config_id = row[0]
    else:
        cur.execute("SELECT id FROM kompas_configuraties WHERE naam = %s", (config_naam,))
        config_id = cur.fetchone()[0]

    with open(csv_pad, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["rijen"] += 1

            # Haal kolomwaarden op (let op variaties in kolomnamen)
            titel      = (row.get("Title") or row.get("Titel") or "").strip()
            thema      = (row.get("Thema") or "").strip()
            onderdeel  = (row.get("Onderdeel") or row.get("Onderdeel ") or "").strip() or "(Algemeen)"
            ind_naam   = (row.get("Indicator") or "").strip()
            ind_swf    = (row.get("Indicator SWF") or "").strip()
            actueel    = (row.get("Indicator actueel") or "").strip().upper() == "J"

            if not titel or not thema:
                continue

            # Niveau 1: Titel
            titel_id = get_or_create(cur, "kompas_titels",
                                     ["naam", "config_id"],
                                     {"naam": titel, "config_id": config_id})
            stats["titels"].add(titel)

            # Niveau 2: Thema
            thema_id = get_or_create(cur, "kompas_themas",
                                     ["naam", "titel_id"],
                                     {"naam": thema, "titel_id": titel_id})
            stats["themas"].add(f"{titel} > {thema}")

            # Niveau 3: Onderdeel
            onderdeel_id = get_or_create(cur, "kompas_onderdelen",
                                         ["naam", "thema_id"],
                                         {"naam": onderdeel, "thema_id": thema_id})
            stats["onderdelen"].add(f"{thema} > {onderdeel}")

            # Niveau 4: Indicator koppeling
            if ind_naam or ind_swf:
                uuid = find_indicator_uuid(cur, ind_naam, ind_swf)
                if uuid:
                    try:
                        cur.execute("SAVEPOINT sp_mapping")
                        cur.execute("""
                            INSERT INTO kompas_indicator_mapping
                                (config_id, indicator_uuid, onderdeel_id, is_actueel)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (config_id, indicator_uuid, onderdeel_id) DO UPDATE SET
                                is_actueel = EXCLUDED.is_actueel
                        """, (config_id, uuid, onderdeel_id, actueel))
                        cur.execute("RELEASE SAVEPOINT sp_mapping")
                        stats["gekoppeld"] += 1
                    except Exception as e:
                        cur.execute("ROLLBACK TO SAVEPOINT sp_mapping")
                        print(f"  ⚠️  Mapping fout: {e}")
                else:
                    stats["niet_gevonden"] += 1
                    if actueel:
                        print(f"  ❓ Actuele indicator niet gevonden: '{ind_swf or ind_naam}'")

    conn.commit()
    cur.close()
    return stats


def show_check(conn):
    """Toon overzicht van huidige kompas structuur."""
    cur = conn.cursor()
    print("\n📊 Huidige kompas structuur:")
    print("─" * 40)

    cur.execute("SELECT naam, is_standaard FROM kompas_configuraties ORDER BY is_standaard DESC")
    configs = cur.fetchall()

    if not configs:
        print("  (leeg — geen configuraties)")
        cur.close()
        return

    for naam, standaard in configs:
        label = " (standaard)" if standaard else ""
        print(f"\n  📁 {naam}{label}")

        cur.execute("""
            SELECT kt.naam, COUNT(DISTINCT ko.id) as onderdelen, COUNT(km.id) as indicatoren
            FROM kompas_titels kt
            JOIN kompas_configuraties kc ON kt.config_id = kc.id
            LEFT JOIN kompas_themas kth ON kth.titel_id = kt.id
            LEFT JOIN kompas_onderdelen ko ON ko.thema_id = kth.id
            LEFT JOIN kompas_indicator_mapping km ON km.onderdeel_id = ko.id
            WHERE kc.naam = %s
            GROUP BY kt.naam
            ORDER BY kt.naam
        """, (naam,))
        for titel, n_ond, n_ind in cur.fetchall():
            print(f"  ├─ {titel}  [{n_ond} onderdelen, {n_ind} indicatoren]")

    cur.close()


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — Kompas hiërarchie importeren",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_05_import_kompas.py
  python etl_05_import_kompas.py --check
  python etl_05_import_kompas.py --reset
  python etl_05_import_kompas.py --bestand /data/mijn_kompas.csv
        """
    )
    parser.add_argument(
        "--bestand",
        help=f"Pad naar kompas CSV (standaard: {DEFAULT_CSV.name})"
    )
    parser.add_argument(
        "--config",
        default="Volledig Kompas",
        help="Naam van de kompas configuratie in de DB (standaard: 'Volledig Kompas')"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Verwijder bestaande kompas data voor deze configuratie vóór import"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Toon overzicht van huidige kompas structuur"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🧭 D-OmniTwin — Stap 5: Kompas Hiërarchie Importeren")
    print("=" * 60)

    conn = get_connection()

    if args.check:
        show_check(conn)
        conn.close()
        return

    if args.reset:
        print(f"\n🗑️  Kompas data resetten voor '{args.config}'...")
        reset_kompas(conn, args.config)

    csv_pad = Path(args.bestand) if args.bestand else DEFAULT_CSV

    if not csv_pad.exists():
        print(f"❌ CSV bestand niet gevonden: {csv_pad}")
        print(f"   Verwacht: {DEFAULT_CSV}")
        conn.close()
        sys.exit(1)

    print(f"\n📂 CSV laden: {csv_pad.name}")
    stats = import_kompas(conn, csv_pad, config_naam=args.config)

    print(f"\n📊 Resultaat:")
    print(f"  📄 Rijen verwerkt:      {stats['rijen']:,}")
    print(f"  🏷️  Unieke titels:       {len(stats['titels'])}")
    print(f"  📂 Unieke thema's:      {len(stats['themas'])}")
    print(f"  📁 Unieke onderdelen:   {len(stats['onderdelen'])}")
    print(f"  🔗 Indicatoren gekoppeld: {stats['gekoppeld']:,}")
    print(f"  ❓ Niet gevonden:       {stats['niet_gevonden']:,}")

    print("\n" + "=" * 60)
    print("✅ Stap 5 voltooid!")
    print()
    print("   Volgende stap:")
    print("   python etl_06_maak_admin.py")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
