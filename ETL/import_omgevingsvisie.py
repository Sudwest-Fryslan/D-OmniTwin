"""
ETL: Import Omgevingsvisie Deelgebieden (Súdwest-Fryslân)
==========================================================
Importeert de GeoPackage naar PostgreSQL/PostGIS tabel `omgevingsvisie_deelgebieden`.
Slaat zowel EPSG:28992 (voor buffer-queries) als EPSG:4326 (voor GeoJSON output) op.

Gebruik:
    python ETL/import_omgevingsvisie.py

Idempotent: kan veilig herhaald worden (TRUNCATE + herinsert).
"""

import geopandas as gpd
from sqlalchemy import text
from pathlib import Path
import sys

# Project root toevoegen aan sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from omnitwin.database import engine


# ============================================================================
# Configuratie
# ============================================================================
GPKG_PATH = Path(__file__).resolve().parent.parent / "data" / "bestuurlijke_postcode_gebieden" / "Deelgebieden_omgevingsvisie.gpkg"
TABLE_NAME = "omgevingsvisie_deelgebieden"


# ============================================================================
# DDL: Tabel + indices aanmaken
# ============================================================================
DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id          SERIAL PRIMARY KEY,
    naam        TEXT NOT NULL,
    deelgebied  TEXT NOT NULL,
    geom        GEOMETRY(Polygon, 28992),
    geom_wgs84  GEOMETRY(Polygon, 4326)
);
CREATE INDEX IF NOT EXISTS idx_omg_deelgebieden_geom
    ON {TABLE_NAME} USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_omg_deelgebieden_geom_wgs84
    ON {TABLE_NAME} USING GIST(geom_wgs84);
"""


def main():
    # --- Lees GeoPackage ---
    if not GPKG_PATH.exists():
        print(f"❌ Bestand niet gevonden: {GPKG_PATH}")
        sys.exit(1)

    print(f"📂 Lezen: {GPKG_PATH}")
    gdf = gpd.read_file(GPKG_PATH)
    print(f"   {len(gdf)} deelgebieden, CRS: {gdf.crs}")

    # Valideer CRS
    assert gdf.crs.to_epsg() == 28992, f"Verwacht EPSG:28992, kreeg {gdf.crs}"

    # --- Pre-compute WGS84 geometrie ---
    gdf_wgs84 = gdf.to_crs(epsg=4326)

    # --- Database operaties ---
    with engine.begin() as conn:
        # DDL: tabel + indices
        conn.execute(text(DDL))
        print(f"✅ Tabel `{TABLE_NAME}` aangemaakt (of bestaat al)")

        # Truncate voor idempotentie
        conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY"))
        print(f"🗑️  Tabel geleegd")

        # Insert per deelgebied
        insert_sql = text(f"""
            INSERT INTO {TABLE_NAME} (naam, deelgebied, geom, geom_wgs84)
            VALUES (
                :naam,
                :deelgebied,
                ST_GeomFromText(:wkt_28992, 28992),
                ST_GeomFromText(:wkt_4326, 4326)
            )
        """)

        for idx, (_, row) in enumerate(gdf.iterrows()):
            wkt_28992 = row.geometry.wkt
            wkt_4326 = gdf_wgs84.iloc[idx].geometry.wkt

            conn.execute(insert_sql, {
                "naam": row["Naam"],
                "deelgebied": row["Deelgebied"],
                "wkt_28992": wkt_28992,
                "wkt_4326": wkt_4326,
            })
            print(f"   ✅ {row['Deelgebied']} ({row.geometry.area / 1e6:.1f} km²)")

    # --- Verificatie ---
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()
        print(f"\n✅ Import voltooid: {count} deelgebieden in `{TABLE_NAME}`")

        # Snelle check: SRID correct?
        srid_check = conn.execute(text(f"""
            SELECT ST_SRID(geom) as srid_rd, ST_SRID(geom_wgs84) as srid_wgs
            FROM {TABLE_NAME} LIMIT 1
        """)).fetchone()
        print(f"   SRID check: geom={srid_check.srid_rd}, geom_wgs84={srid_check.srid_wgs}")


if __name__ == "__main__":
    main()
