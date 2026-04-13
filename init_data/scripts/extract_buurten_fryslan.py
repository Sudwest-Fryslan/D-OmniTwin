#!/usr/bin/env python3
"""
Extraheer CBS Buurten 2024 voor Fryslân uit de lokale GPKG.
================================================
Leest de bestaande data/cbs_pc6_huisnr_buurt/CBS_BUURTEN2024.gpkg,
filtert op de 18 Friese gemeenten, converteert naar WGS84 en
schrijft het resultaat als GeoJSON naar init_data/fryslan/.

Gebruik:
    python init_data/scripts/extract_buurten_fryslan.py

Vereisten: geopandas (pip install geopandas)
"""
import json
from pathlib import Path

try:
    import geopandas as gpd
except ImportError:
    print("❌ geopandas niet gevonden. Installeer met: pip install geopandas")
    raise SystemExit(1)

ROOT = Path(__file__).parent.parent.parent
GPKG_PATH = ROOT / "data" / "cbs_pc6_huisnr_buurt" / "CBS_BUURTEN2024.gpkg"
OUTPUT = ROOT / "init_data" / "fryslan" / "buurten_fryslan.geojson"

# Alle Friese gemeente CBS-codes (GM-formaat zoals in GPKG)
# Let op: GPKG gebruikt soms andere codes dan het schema:
#   Smallingerland  → GM0090 (GPKG) i.p.v. GM0140 (schema legacy)
#   De Fryske Marren → GM1940 (GPKG) i.p.v. GM1921 (schema legacy)
FRIESE_GEMEENTEN = {
    'GM0059', 'GM0060', 'GM1891', 'GM1940', 'GM0072', 'GM0074',
    'GM0080', 'GM1970', 'GM0085', 'GM0086', 'GM0088', 'GM0090',
    'GM1900', 'GM0093', 'GM0737', 'GM0096', 'GM1949', 'GM0098'
}

# Kolommen die we meenemen in de GeoJSON
BEWAAR_KOLOMMEN = [
    "buurtcode", "buurtnaam",
    "gemeentecode", "gemeentenaam",
    "wijkcode",
    "geometry"
]


def main():
    print("=" * 60)
    print("D-OmniTwin — Fryslân Buurten extraheren uit GPKG")
    print("=" * 60)

    if not GPKG_PATH.exists():
        print(f"❌ GPKG niet gevonden: {GPKG_PATH}")
        print("   Verwacht pad: data/cbs_pc6_huisnr_buurt/CBS_BUURTEN2024.gpkg")
        raise SystemExit(1)

    print(f"📂 Bron: {GPKG_PATH}")
    print(f"📁 Output: {OUTPUT}")
    print()

    # Laad de buurten layer
    print("⏳ GPKG laden (dit duurt ~30 seconden voor heel NL)...")
    gdf = gpd.read_file(GPKG_PATH, layer="buurten", engine="pyogrio")
    print(f"   Totaal NL: {len(gdf)} buurten geladen")
    print(f"   CRS: {gdf.crs}")

    # Filter op Friese gemeenten
    # Kolom is 'gemeentecode' met waarden als 'GM1900'
    gm_col = next(
        (c for c in gdf.columns if "gemeente" in c.lower() and "code" in c.lower()),
        None
    )
    if not gm_col:
        # Fallback: zoek op naam
        gm_col = next((c for c in gdf.columns if "gm_code" in c.lower()), None)

    if not gm_col:
        print(f"❌ Gemeentecode kolom niet gevonden. Beschikbare kolommen:\n{list(gdf.columns)}")
        raise SystemExit(1)

    print(f"   Gemeente-kolom: '{gm_col}'")

    gdf_fryslan = gdf[gdf[gm_col].isin(FRIESE_GEMEENTEN)].copy()
    print(f"   Fryslân:  {len(gdf_fryslan)} buurten")

    if len(gdf_fryslan) == 0:
        # Probeer zonder leading zeros of GM prefix
        sample = gdf[gm_col].dropna().head(5).tolist()
        print(f"   ⚠️  Geen match. Voorbeeldwaarden in kolom: {sample}")
        print("      Pas FRIESE_GEMEENTEN aan in het script.")
        raise SystemExit(1)

    # Selecteer relevante kolommen (gebruik alleen wat bestaat)
    beschikbaar = [c for c in BEWAAR_KOLOMMEN if c in gdf_fryslan.columns]
    ontbrekend = [c for c in BEWAAR_KOLOMMEN if c not in gdf_fryslan.columns and c != "geometry"]
    if ontbrekend:
        print(f"   ℹ️  Kolommen niet aanwezig (overgeslagen): {ontbrekend}")
    gdf_fryslan = gdf_fryslan[beschikbaar]

    # Converteer naar WGS84 (EPSG:4326)
    if gdf_fryslan.crs and gdf_fryslan.crs.to_epsg() != 4326:
        print("   🔄 Transformeren naar WGS84 (EPSG:4326)...")
        gdf_fryslan = gdf_fryslan.to_crs(epsg=4326)

    # Schrijf als GeoJSON
    print()
    print("💾 Schrijven naar GeoJSON...")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gdf_fryslan.to_file(OUTPUT, driver="GeoJSON")

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"\n✅ Klaar!")
    print(f"   {len(gdf_fryslan)} buurten opgeslagen")
    print(f"   Bestandsgrootte: {size_mb:.1f} MB")

    # Samenvatting per gemeente
    if "gemeentenaam" in gdf_fryslan.columns:
        print(f"\n📊 Buurten per gemeente:")
        per_gemeente = gdf_fryslan.groupby("gemeentenaam").size().sort_values(ascending=False)
        for naam, count in per_gemeente.items():
            print(f"   {naam:<30} {count:>3} buurten")


if __name__ == "__main__":
    main()
