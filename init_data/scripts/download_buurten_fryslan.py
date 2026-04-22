#!/usr/bin/env python3
"""
Download CBS Buurten 2024 voor de provincie Fryslân via PDOK WFS.
Dit script gebruikt Geopandas om de 'lichte' geometrie layer in GML op te halen,
en filtert deze lokaal. Dit is de meest robuuste manier omdat PDOK WFS filters vaak negeert.
Output: init_data/fryslan/buurten_fryslan.geojson (WGS84)
"""
import geopandas as gpd
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
OUTPUT = ROOT / "init_data" / "fryslan" / "buurten_fryslan.geojson"

FRIESE_GEMEENTEN = {
    'GM0059': 'Achtkarspelen', 'GM0060': 'Ameland', 'GM1891': 'Dantumadiel',
    'GM1921': 'De Fryske Marren', 'GM0072': 'Harlingen', 'GM0074': 'Heerenveen',
    'GM0080': 'Leeuwarden', 'GM1970': 'Noardeast-Fryslân', 'GM0085': 'Ooststellingwerf',
    'GM0086': 'Opsterland', 'GM0088': 'Schiermonnikoog', 'GM0140': 'Smallingerland',
    'GM1900': 'Súdwest-Fryslân', 'GM0093': 'Terschelling', 'GM0737': 'Tytsjerksteradiel',
    'GM0096': 'Vlieland', 'GM1949': 'Waadhoeke', 'GM0098': 'Weststellingwerf'
}

WFS_BASE = "https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0"
LAYER = "gebiedsindelingen:buurt_gegeneraliseerd"
PAGE_SIZE = 1000


def download_buurten():
    print("=" * 60)
    print("Download CBS Buurten 2024 — Fryslân (via Geopandas GML)")
    print("=" * 60)
    print(f"Bron: PDOK WFS ({LAYER})")
    print()

    all_gdfs = []
    start_index = 0
    pagina = 1

    print("  📥 Downloaden van alle Nederlandse buurten (GML paginering)...")
    while True:
        url = f"{WFS_BASE}?request=GetFeature&service=WFS&version=2.0.0&typeName={LAYER}&count={PAGE_SIZE}&startIndex={start_index}"
        print(f"     Pagina {pagina} (offset {start_index})...", end=" ", flush=True)
        try:
            # Geopandas leest de GML stream direct
            gdf = gpd.read_file(url)
            print(f"{len(gdf)} features")
            
            if len(gdf) == 0:
                break
                
            all_gdfs.append(gdf)
            
            if len(gdf) < PAGE_SIZE:
                break
                
            start_index += PAGE_SIZE
            pagina += 1
            
        except Exception as e:
            print(f"\n❌ Fout tijdens download: {e}")
            return False

    if not all_gdfs:
        print("\n⚠️  Geen features ontvangen.")
        return False

    print("  ⚙️  Samenvoegen en verwerken in Geopandas...")
    combined = pd.concat(all_gdfs, ignore_index=True)
    
    print(f"  📊 Totaal gedownload: {len(combined)} buurten (heel NL)")
    
    # In deze lichte layer heten de kolommen statcode en statnaam.
    # We hernoemen ze naar de verwachte formaten.
    if 'statcode' in combined.columns:
        combined['buurtcode'] = combined['statcode']
        combined['buurtnaam'] = combined['statnaam']
        # Gemeentecode is altijd 'GM' + de eerste 4 cijfers na 'BU'
        combined['gemeentecode'] = 'GM' + combined['statcode'].str[2:6]
    
    print("  ⚙️  Filteren op Fryslân...")
    # Lokaal filteren op de keys van onze dictionary
    gdf_filtered = combined[combined['gemeentecode'].isin(FRIESE_GEMEENTEN.keys())].copy()
    
    # Voeg gemeentenaam toe
    gdf_filtered['gemeentenaam'] = gdf_filtered['gemeentecode'].map(FRIESE_GEMEENTEN)
    
    print("  🗺️  Controleren op MultiPolygon compatibiliteit...")
    # Cast alle geometrieën expliciet naar MultiPolygon, omdat PostGIS dat verwacht
    from shapely.geometry import MultiPolygon, Polygon
    
    def cast_to_multipolygon(geom):
        if geom is None:
            return None
        elif isinstance(geom, Polygon):
            return MultiPolygon([geom])
        return geom
        
    gdf_filtered['geometry'] = gdf_filtered['geometry'].apply(cast_to_multipolygon)
    
    # Zorg dat de geometrie klopt (EPSG:28992 -> EPSG:4326 voor de kaart)
    if gdf_filtered.crs and gdf_filtered.crs.to_epsg() != 4326:
        print("  🗺️  Reprojecteren naar EPSG:4326 (WGS84)...")
        gdf_filtered = gdf_filtered.to_crs("EPSG:4326")
    elif not gdf_filtered.crs:
        # Als er geen CRS is meegekomen, ga er dan van uit dat PDOK standaard EPSG:28992 stuurt
        gdf_filtered.set_crs("EPSG:28992", inplace=True)
        gdf_filtered = gdf_filtered.to_crs("EPSG:4326")
    
    # Verwijder overtollige kolommen
    keep_cols = ['buurtcode', 'buurtnaam', 'gemeentecode', 'gemeentenaam', 'geometry']
    for col in gdf_filtered.columns:
        if col not in keep_cols:
            gdf_filtered = gdf_filtered.drop(columns=[col])

    print(f"  ✅ Filter succesvol: {len(gdf_filtered)} Friese buurten over.")
    
    # Oude file verwijderen indien aanwezig
    if OUTPUT.exists():
        OUTPUT.unlink()
        
    # Schrijf weg als GeoJSON
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gdf_filtered.to_file(OUTPUT, driver="GeoJSON")
    
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"\n✅ Opgeslagen: {OUTPUT}")
    print(f"   {len(gdf_filtered)} buurten | {size_mb:.1f} MB")
    
    return True


if __name__ == "__main__":
    download_buurten()
