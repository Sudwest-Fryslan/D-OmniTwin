#!/usr/bin/env python3
"""
D-OmniTwin ETL — OV Haltes Import
====================================
Issue #11: OV-haltes ophalen uit OpenStreetMap en koppelen als Kompas-indicator.

Haalt OV-haltelocaties op via Overpass API, dedupliceert via spatial clustering,
koppelt aan CBS-buurten via PostGIS, en schrijft naar gebied_data.

Gebruik:
    cd /mnt/f/VSCode_Projects/D-OmniTwin
    source .venv/bin/activate

    # Dry run (alleen tellen, niet naar DB schrijven):
    python ETL/OV/import_ov_haltes.py --dry-run

    # Alleen Fryslân:
    python ETL/OV/import_ov_haltes.py --provincies FR

    # Alles (FR, GR, DR):
    python ETL/OV/import_ov_haltes.py

    # Schema overslaan (al aangemaakt):
    python ETL/OV/import_ov_haltes.py --skip-schema
"""

import sys
import os
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

# ─── Paden ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # ETL/OV/
ETL_DIR = SCRIPT_DIR.parent                           # ETL/
PROJECT_ROOT = ETL_DIR.parent                         # D-OmniTwin/
SCHEMA_FILE = SCRIPT_DIR / "migrations" / "schema_v14_ov_haltes.sql"

sys.path.insert(0, str(ETL_DIR / "local"))
sys.path.insert(0, str(SCRIPT_DIR))

from overpass_client import ophalen_ov_nodes, PROVINCIES


def get_connection():
    """DB connectie met hardcoded sslmode (workaround .env comment-bug)."""
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    conn = psycopg2.connect(
        host=os.getenv("DATABASE_HOST"),
        port=int(os.getenv("DATABASE_PORT", 5432)),
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD", ""),
        sslmode="prefer",
    )
    logger.info(f"🔌 Verbonden met {os.getenv('DATABASE_NAME')}")
    return conn

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constanten ──────────────────────────────────────────────────────────────
CLUSTER_RADIUS_M = 75.0   # Deduplicatieradius in meters
PEILJAAR = 2026
BRON = "OpenStreetMap / Overpass API 2026"

INDICATOR_CODES = {
    "totaal":   "OV_HALTES_TOTAAL",
    "bus":      "OV_HALTES_BUS",
    "trein":    "OV_HALTES_TREIN",
    "tram":     "OV_HALTES_TRAM",
    "veerboot": "OV_HALTES_VEERBOOT",
}

# CRS transformatie: WGS84 → Rijksdriehoek
transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)


# ─── Fase 1: Schema ─────────────────────────────────────────────────────────

def maak_schema(conn):
    """Maak de OV-haltes tabellen aan (idempotent)."""
    logger.info("Fase 1: Database schema aanmaken...")
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("  ✅ Schema aangemaakt (of bestond al)")


# ─── Fase 2: Ophalen & transformeren ────────────────────────────────────────

def verwerk_provincie(provincie_code: str, peildatum: date) -> pd.DataFrame:
    """
    Haal nodes op via Overpass en transformeer naar DataFrame met RD-coördinaten.

    Returns:
        DataFrame met kolommen: osm_id, naam, ov_type, osm_pt_type,
        network, ref, provincie, x_rd, y_rd, peildatum, tags
    """
    logger.info(f"Fase 2: Ophalen {PROVINCIES[provincie_code]} ({provincie_code})...")
    nodes = ophalen_ov_nodes(provincie_code)

    if not nodes:
        logger.warning(f"  ⚠️ Geen nodes ontvangen voor {provincie_code}")
        return pd.DataFrame()

    df = pd.DataFrame(nodes)

    # Filter nodes zonder coördinaten
    voor = len(df)
    df = df.dropna(subset=["lat", "lon"])
    if len(df) < voor:
        logger.info(f"  → {voor - len(df)} nodes zonder coördinaten verwijderd")

    # CRS transformatie: WGS84 → RD
    x_rd, y_rd = transformer.transform(df["lon"].values, df["lat"].values)
    df["x_rd"] = x_rd
    df["y_rd"] = y_rd
    df["peildatum"] = peildatum

    logger.info(f"  → {len(df)} nodes met RD-coördinaten")

    # Statistieken
    type_counts = df["ov_type"].value_counts()
    for ov_type, n in type_counts.items():
        logger.info(f"     {ov_type}: {n}")

    return df


# ─── Fase 2b: Clustering ────────────────────────────────────────────────────

def cluster_platforms(df: pd.DataFrame, radius_m: float = CLUSTER_RADIUS_M) -> pd.DataFrame:
    """
    Groepeer platform-nodes met dezelfde naam en ov_type die binnen radius_m
    meter van elkaar liggen tot één cluster.

    Retourneert DataFrame met:
        naam, ov_type, n_platforms, x_rd, y_rd, provincie, peildatum
    """
    if df.empty:
        return pd.DataFrame()

    clusters = []
    used = set()
    coords = df[["x_rd", "y_rd"]].values
    namen = df["naam"].fillna("").values
    typen = df["ov_type"].values

    tree = cKDTree(coords)

    for i in range(len(df)):
        if i in used:
            continue
        idxs = tree.query_ball_point(coords[i], radius_m)
        # Zelfde naam EN zelfde ov_type
        zelfde = [j for j in idxs if namen[j] == namen[i] and typen[j] == typen[i]]
        cluster_coords = coords[zelfde]
        centroid = cluster_coords.mean(axis=0)
        clusters.append({
            "naam": namen[i] or None,
            "ov_type": typen[i],
            "n_platforms": len(zelfde),
            "x_rd": centroid[0],
            "y_rd": centroid[1],
            "provincie": df.iloc[i]["provincie"],
            "peildatum": df.iloc[i]["peildatum"],
        })
        used.update(zelfde)

    result = pd.DataFrame(clusters)
    logger.info(f"  → {len(df)} nodes → {len(result)} clusters (factor {len(df)/len(result):.1f}x)")
    return result


# ─── Fase 3: Laden naar database ────────────────────────────────────────────

def laad_ruwe_haltes(conn, df: pd.DataFrame):
    """INSERT ruwe nodes in ov_haltes (idempotent via ON CONFLICT)."""
    if df.empty:
        return
    logger.info(f"  Laden {len(df)} ruwe haltes naar ov_haltes...")
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO ov_haltes
                    (osm_id, naam, ov_type, osm_pt_type, network, ref,
                     provincie, geom, peildatum, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 28992),
                        %s, %s)
                ON CONFLICT (osm_id) DO UPDATE SET
                    naam        = EXCLUDED.naam,
                    ov_type     = EXCLUDED.ov_type,
                    osm_pt_type = EXCLUDED.osm_pt_type,
                    network     = EXCLUDED.network,
                    ref         = EXCLUDED.ref,
                    geom        = EXCLUDED.geom,
                    peildatum   = EXCLUDED.peildatum,
                    tags        = EXCLUDED.tags
            """, (
                int(row["osm_id"]), row["naam"], row["ov_type"],
                row["osm_pt_type"], row["network"], row["ref"],
                row["provincie"], float(row["x_rd"]), float(row["y_rd"]),
                row["peildatum"],
                json.dumps(row["tags"], ensure_ascii=False) if row["tags"] else None,
            ))
    conn.commit()
    logger.info(f"  ✅ {len(df)} ruwe haltes geladen")


def koppel_gebieden(conn):
    """Spatial join: koppel ov_haltes aan gebieden (buurt-niveau)."""
    logger.info("  Spatial join: ov_haltes → gebieden...")
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ov_haltes h
            SET gebied_id     = g.id,
                gemeente_code = g.gemeente_code
            FROM gebieden g
            WHERE ST_Within(h.geom, g.geom)
              AND h.gebied_id IS NULL
        """)
        n = cur.rowcount
    conn.commit()
    logger.info(f"  ✅ {n} haltes gekoppeld aan gebieden")

    # Check hoeveel ongekoppeld
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM ov_haltes WHERE gebied_id IS NULL")
        ongekoppeld = cur.fetchone()[0]
    if ongekoppeld > 0:
        logger.warning(f"  ⚠️ {ongekoppeld} haltes niet gekoppeld aan een buurt (buiten gebieden-polygonen)")


def laad_clusters(conn, df_clusters: pd.DataFrame):
    """INSERT gededupliceerde clusters in ov_halte_clusters."""
    if df_clusters.empty:
        return
    logger.info(f"  Laden {len(df_clusters)} clusters naar ov_halte_clusters...")

    # Verwijder eerst bestaande clusters voor deze provincie + peildatum
    prov = df_clusters.iloc[0]["provincie"]
    peildatum = df_clusters.iloc[0]["peildatum"]
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM ov_halte_clusters WHERE provincie = %s AND peildatum = %s",
            (prov, peildatum)
        )

        for _, row in df_clusters.iterrows():
            cur.execute("""
                INSERT INTO ov_halte_clusters
                    (naam, ov_type, n_platforms, provincie, geom, peildatum)
                VALUES (%s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 28992), %s)
            """, (
                row["naam"], row["ov_type"], int(row["n_platforms"]),
                row["provincie"],
                float(row["x_rd"]), float(row["y_rd"]),
                row["peildatum"],
            ))
    conn.commit()
    logger.info(f"  ✅ {len(df_clusters)} clusters geladen")


def koppel_clusters_gebieden(conn):
    """Spatial join: koppel ov_halte_clusters aan gebieden."""
    logger.info("  Spatial join: clusters → gebieden...")
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ov_halte_clusters c
            SET gebied_id     = g.id,
                gemeente_code = g.gemeente_code
            FROM gebieden g
            WHERE ST_Within(c.geom, g.geom)
              AND c.gebied_id IS NULL
        """)
        n = cur.rowcount
    conn.commit()
    logger.info(f"  ✅ {n} clusters gekoppeld aan gebieden")


# ─── Fase 4: Aggregatie & gebied_data ────────────────────────────────────────

def bereken_aggregaten(conn, jaar: int):
    """Bereken haltes per buurt per type uit clusters en sla op."""
    logger.info("Fase 4: Aggregatie per buurt...")
    with conn.cursor() as cur:
        # Wis bestaande aggregaten voor dit jaar
        cur.execute("DELETE FROM ov_haltes_per_buurt WHERE jaar = %s", (jaar,))

        cur.execute("""
            INSERT INTO ov_haltes_per_buurt
                (gebied_id, jaar, totaal_haltes, haltes_bus, haltes_trein,
                 haltes_tram, haltes_veerboot, haltes_metro)
            SELECT
                gebied_id,
                %s AS jaar,
                COUNT(*) AS totaal,
                COUNT(*) FILTER (WHERE ov_type = 'bus') AS bus,
                COUNT(*) FILTER (WHERE ov_type = 'trein') AS trein,
                COUNT(*) FILTER (WHERE ov_type = 'tram') AS tram,
                COUNT(*) FILTER (WHERE ov_type = 'veerboot') AS veerboot,
                COUNT(*) FILTER (WHERE ov_type = 'metro') AS metro
            FROM ov_halte_clusters
            WHERE gebied_id IS NOT NULL
            GROUP BY gebied_id
        """, (jaar,))
        n = cur.rowcount
    conn.commit()
    logger.info(f"  ✅ Aggregaten voor {n} buurten opgeslagen")
    return n


def get_indicator_uuid(cur, code: str) -> str:
    """Haal indicator UUID op. Fout als die niet bestaat."""
    cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise ValueError(
            f"Indicator '{code}' niet gevonden in indicatoren tabel.\n"
            f"  Seed eerst: python ETL/local/etl_03_seed_indicatoren.py "
            f"--bestand ETL/OV/seed_ov_indicatoren.json"
        )
    return str(row[0])


def schrijf_naar_gebied_data(conn, jaar: int):
    """Schrijf OV-indicatoren naar gebied_data (Kompas-koppeling)."""
    logger.info("Fase 5: Schrijven naar gebied_data (Kompas-koppeling)...")

    with conn.cursor() as cur:
        # Haal alle indicator UUIDs op
        uuids = {}
        for ov_type, code in INDICATOR_CODES.items():
            try:
                uuids[ov_type] = get_indicator_uuid(cur, code)
            except ValueError as e:
                logger.error(str(e))
                return 0

        # Lees aggregaten
        cur.execute("""
            SELECT gebied_id, totaal_haltes, haltes_bus, haltes_trein,
                   haltes_tram, haltes_veerboot
            FROM ov_haltes_per_buurt
            WHERE jaar = %s
        """, (jaar,))
        rijen = cur.fetchall()

        n_geschreven = 0
        for (gebied_id, totaal, bus, trein, tram, veerboot) in rijen:
            waarden = {
                "totaal":   totaal,
                "bus":      bus,
                "trein":    trein,
                "tram":     tram,
                "veerboot": veerboot,
            }
            for ov_type, waarde in waarden.items():
                cur.execute("""
                    INSERT INTO gebied_data
                        (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                    VALUES (%s, %s, %s, %s, 'current', %s)
                    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
                    DO UPDATE SET
                        waarde     = EXCLUDED.waarde,
                        updated_at = CURRENT_TIMESTAMP
                """, (gebied_id, uuids[ov_type], waarde, jaar, BRON))
                n_geschreven += 1

    conn.commit()
    logger.info(f"  ✅ {n_geschreven} waarden geschreven naar gebied_data")
    return n_geschreven


# ─── Verificatie ─────────────────────────────────────────────────────────────

def verificatie(conn, jaar: int):
    """Print verificatierapport."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("VERIFICATIERAPPORT")
    logger.info("=" * 60)

    with conn.cursor() as cur:
        # Ruwe haltes
        cur.execute("""
            SELECT provincie, ov_type, COUNT(*) AS n
            FROM ov_haltes
            GROUP BY provincie, ov_type
            ORDER BY provincie, n DESC
        """)
        logger.info("\n📊 Ruwe haltes per provincie en type:")
        for prov, ov_type, n in cur.fetchall():
            logger.info(f"  {prov} | {ov_type:<10} | {n:>5}")

        # Clusters
        cur.execute("""
            SELECT provincie, ov_type, COUNT(*) AS n, AVG(n_platforms)::numeric(5,1) AS gem
            FROM ov_halte_clusters
            GROUP BY provincie, ov_type
            ORDER BY provincie, n DESC
        """)
        logger.info("\n📊 Clusters per provincie en type (na deduplicatie):")
        for prov, ov_type, n, gem in cur.fetchall():
            logger.info(f"  {prov} | {ov_type:<10} | {n:>5} clusters (gem {gem} platforms/cluster)")

        # Niet-gekoppeld
        cur.execute("SELECT COUNT(*) FROM ov_halte_clusters WHERE gebied_id IS NULL")
        ongekoppeld = cur.fetchone()[0]
        logger.info(f"\n⚠️  Clusters zonder buurt-koppeling: {ongekoppeld}")

        # gebied_data
        cur.execute("""
            SELECT i.code, COUNT(*) AS n, AVG(gd.waarde)::numeric(5,1) AS gem
            FROM gebied_data gd
            JOIN indicatoren i ON gd.indicator_uuid = i.uuid
            WHERE i.code LIKE 'OV_HALTES%%'
              AND gd.scenario_id = 'current'
              AND gd.jaar = %s
            GROUP BY i.code
            ORDER BY i.code
        """, (jaar,))
        logger.info(f"\n📊 gebied_data per indicator (jaar={jaar}):")
        for code, n, gem in cur.fetchall():
            logger.info(f"  {code:<25} | {n:>5} buurten | gem={gem}")

    logger.info("\n" + "=" * 60)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin ETL — OV Haltes Import (Issue #11)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provincies", default="FR,GR,DR",
        help="Komma-gescheiden provincielijst (default: FR,GR,DR)",
    )
    parser.add_argument(
        "--peildatum", default=str(date.today()),
        help=f"Peildatum voor import (default: vandaag)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Alleen ophalen en tellen, niet naar DB schrijven",
    )
    parser.add_argument(
        "--skip-schema", action="store_true",
        help="Schema-aanmaak overslaan (al aangemaakt)",
    )
    args = parser.parse_args()

    provincies = [p.strip().upper() for p in args.provincies.split(",")]
    peildatum = date.fromisoformat(args.peildatum)

    logger.info("=" * 60)
    logger.info("🚍 D-OmniTwin — ETL OV Haltes (Issue #11)")
    logger.info(f"   Provincies: {', '.join(provincies)}")
    logger.info(f"   Peildatum:  {peildatum}")
    logger.info(f"   Dry run:    {'Ja' if args.dry_run else 'Nee'}")
    logger.info("=" * 60)

    # Validatie
    for p in provincies:
        if p not in PROVINCIES:
            logger.error(f"Onbekende provincie: {p}. Verwacht: {list(PROVINCIES)}")
            sys.exit(1)

    conn = get_connection()

    # Fase 1: Schema
    if not args.skip_schema:
        maak_schema(conn)

    # Fase 2 + 2b + 3: Per provincie ophalen, clusteren, laden
    alle_clusters = []
    for i, prov in enumerate(provincies):
        if i > 0:
            logger.info("  ⏳ Wacht 3s (Overpass beleefdheidspause)...")
            time.sleep(3)

        df_nodes = verwerk_provincie(prov, peildatum)
        if df_nodes.empty:
            continue

        # Clustering
        logger.info(f"Fase 2b: Clustering {prov} (radius={CLUSTER_RADIUS_M}m)...")
        df_clusters = cluster_platforms(df_nodes)
        alle_clusters.append(df_clusters)

        if args.dry_run:
            logger.info(f"  🔍 DRY RUN — {prov}: {len(df_nodes)} nodes → {len(df_clusters)} clusters")
            continue

        # Laden naar DB
        logger.info(f"Fase 3: Laden {prov}...")
        laad_ruwe_haltes(conn, df_nodes)
        laad_clusters(conn, df_clusters)

    if args.dry_run:
        logger.info("\n🔍 DRY RUN voltooid — geen DB wijzigingen gemaakt")
        conn.close()
        return

    # Spatial joins
    logger.info("Fase 3b: Spatial joins...")
    koppel_gebieden(conn)
    koppel_clusters_gebieden(conn)

    # Fase 4: Aggregatie
    bereken_aggregaten(conn, PEILJAAR)

    # Fase 5: gebied_data
    schrijf_naar_gebied_data(conn, PEILJAAR)

    # Verificatie
    verificatie(conn, PEILJAAR)

    conn.close()
    logger.info("\n✅ ETL OV Haltes voltooid!")


if __name__ == "__main__":
    main()
