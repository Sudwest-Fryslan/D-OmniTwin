#!/usr/bin/env python3
"""
Sprint 22 Track C — Metadata & Data Lineage Enrichment Script
============================================================
Enriches all active indicators in `omnitwin_db` with standardized lineage metadata:
- `bron`: Formal publisher name
- `bron_systeem_api`: Standard taxonomy (CBS_ODATA, RIVM_STATLINE, POLITIE_DATA, BAG_API, OV_API, etc.)
- `bron_tabel_referentie`: Exact dataset ID / endpoint table reference
- `begingeldigheid` & `eindgeldigheid`: Dynamically computed from `gebied_data` min/max year
- `laatste_check_datum`: Timestamp of verification
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Load environment
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")


def get_connection():
    """Connect to database with fallback for local vs docker ports"""
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "omnitwin_db")
    db_user = os.getenv("DATABASE_USER", "omnitwin_user")
    db_password = os.getenv("DATABASE_PASSWORD") or sys.exit(
        "DATABASE_PASSWORD ontbreekt; zet hem in de omgeving of in .env."
    )

    # Try configured port first, fallback to 5433 if local port 5432 fails
    ports_to_try = [db_port]
    if db_port == "5432":
        ports_to_try.append("5433")
    elif db_port == "5433":
        ports_to_try.append("5432")

    for p in ports_to_try:
        try:
            conn = psycopg2.connect(
                host=db_host, port=p, dbname=db_name, user=db_user, password=db_password, cursor_factory=RealDictCursor
            )
            return conn
        except Exception:
            continue

    raise ConnectionError(f"Could not connect to postgres at {db_host} on ports {ports_to_try}")


def determine_lineage(indicator: dict) -> dict:
    """
    Determine standardized lineage based on code, naam, existing bron, etc.
    """
    code = (indicator.get("code") or "").upper()
    naam = (indicator.get("naam") or "").lower()
    cat = (indicator.get("categorie") or "").lower()
    existing_bron = (indicator.get("bron") or "").lower()

    # 1. OV Haltes
    if "OV_" in code or "halte" in naam or "ov_" in cat:
        return {
            "bron": "OpenOV / NDOV Loket",
            "bron_systeem_api": "OV_API",
            "bron_tabel_referentie": "ov_haltes_fryslan",
        }

    # 2. BAG Panden / Gebruiksfuncties / Bouwjaren
    if "BAG_" in code or "bouwjaar" in naam or "woonfunctie" in naam or "oppervlakte pand" in naam:
        return {
            "bron": "Kadaster / Basisregistratie Adressen en Gebouwen (BAG)",
            "bron_systeem_api": "BAG_API",
            "bron_tabel_referentie": "bag_panden_fryslan",
        }

    # 3. Politie (Misdrijven / Overlast)
    if "misdrijf" in naam or "diefstal" in naam or "geweld" in naam or "vernieling" in naam or "overlast" in naam:
        return {
            "bron": "Politie / CBS Datawonen",
            "bron_systeem_api": "POLITIE_DATA",
            "bron_tabel_referentie": "47018NED",
        }

    # 4. RIVM / GGD Gezondheidsmonitor
    if any(
        k in naam
        for k in ["gezondheid", "roken", "alcohol", "bewegen", "eenzaamheid", "overgewicht", "bmi", "stress", "mentale"]
    ):
        return {
            "bron": "RIVM / GGD Gezondheidsmonitor",
            "bron_systeem_api": "RIVM_STATLINE",
            "bron_tabel_referentie": "50150NED",
        }

    # 5. CBS Nabijheid voorzieningen
    if any(k in naam for k in ["afstand tot", "nabijheid", "huisartsenpraktijk", "supermarkt", "basisschool"]):
        return {
            "bron": "Centraal Bureau voor de Statistiek (CBS)",
            "bron_systeem_api": "CBS_ODATA",
            "bron_tabel_referentie": "84463NED",
        }

    # 6. CBS Kerncijfers Wijken en Buurten (Standaard CBS Core)
    return {
        "bron": "Centraal Bureau voor de Statistiek (CBS)",
        "bron_systeem_api": "CBS_ODATA",
        "bron_tabel_referentie": "85984NED",
    }


def run_enrichment():
    conn = get_connection()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Fetch all active indicators
            cur.execute("""
                SELECT id, uuid, code, naam, categorie, bron, bron_systeem_api, bron_tabel_referentie
                FROM indicatoren
                WHERE is_actief = true
                ORDER BY naam ASC
            """)
            indicators = cur.fetchall()
            print(f"🔍 Gevonden: {len(indicators)} actieve indicatoren om te controleren en verrijken.\n")

            stats = {"total": len(indicators), "updated": 0, "by_source": {}}

            for ind in indicators:
                lineage = determine_lineage(ind)

                # Dynamically fetch min and max year from gebied_data for period validity
                cur.execute(
                    """
                    SELECT MIN(jaar) as min_jaar, MAX(jaar) as max_jaar
                    FROM gebied_data
                    WHERE indicator_uuid = %s AND jaar IS NOT NULL
                """,
                    (ind["uuid"],),
                )
                years = cur.fetchone()

                min_year = years["min_jaar"] if years and years["min_jaar"] else None
                max_year = years["max_jaar"] if years and years["max_jaar"] else None

                begin_valid = f"{min_year}-01-01" if min_year else None
                eind_valid = f"{max_year}-12-31" if max_year else None

                # Update indicator record
                cur.execute(
                    """
                    UPDATE indicatoren
                    SET bron = %s,
                        bron_systeem_api = %s,
                        bron_tabel_referentie = %s,
                        begingeldigheid = COALESCE(begingeldigheid, %s::timestamp),
                        eindgeldigheid = COALESCE(eindgeldigheid, %s::timestamp),
                        laatste_check_datum = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (
                        lineage["bron"],
                        lineage["bron_systeem_api"],
                        lineage["bron_tabel_referentie"],
                        begin_valid,
                        eind_valid,
                        ind["id"],
                    ),
                )

                stats["updated"] += 1
                src_key = lineage["bron_systeem_api"]
                stats["by_source"][src_key] = stats["by_source"].get(src_key, 0) + 1

            conn.commit()
            print("✅ Database update succesvol uitgevoerd!\n")
            print("📊 Verrijkingsstatistieken per bron-taxonomie:")
            for src, count in sorted(stats["by_source"].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {src:<15}: {count:>3} indicatoren")

            # Verify result summary
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(bron_systeem_api) as with_api,
                    COUNT(bron_tabel_referentie) as with_ref,
                    COUNT(begingeldigheid) as with_period
                FROM indicatoren
                WHERE is_actief = true
            """)
            summary = cur.fetchone()
            print("\n📈 Totale Lineage Dekking:")
            print(f"   • Totaal actief           : {summary['total']}")
            print(
                f"   • Met bron_systeem_api    : {summary['with_api']} ({summary['with_api'] / summary['total'] * 100:.1f}%)"
            )
            print(
                f"   • Met bron_tabel_ref      : {summary['with_ref']} ({summary['with_ref'] / summary['total'] * 100:.1f}%)"
            )
            print(
                f"   • Met peildatum/periode   : {summary['with_period']} ({summary['with_period'] / summary['total'] * 100:.1f}%)"
            )

    except Exception as e:
        conn.rollback()
        print(f"❌ Fout tijdens lineage verrijking: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    run_enrichment()
