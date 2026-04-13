#!/usr/bin/env python3
"""
Download CBS Buurten 2024 voor de provincie Fryslân via PDOK WFS.
Output: init_data/fryslan/buurten_fryslan.geojson (WGS84)

Gebruik:
    python init_data/scripts/download_buurten_fryslan.py

Vereisten: pip install requests
"""
import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
OUTPUT = ROOT / "init_data" / "fryslan" / "buurten_fryslan.geojson"

# Friese gemeente CBS-codes (GM-formaat voor WFS)
FRIESE_GEMEENTEN = [
    'GM0059', 'GM0060', 'GM1891', 'GM1921', 'GM0072', 'GM0074',
    'GM0080', 'GM1970', 'GM0085', 'GM0086', 'GM0088', 'GM0140',
    'GM1900', 'GM0093', 'GM0737', 'GM0096', 'GM1949', 'GM0098'
]

WFS_BASE = "https://geodata.nationaalgeoregister.nl/cbsgebiedsindelingen/wfs"
LAYER = "cbsgebiedsindelingen:cbs_buurten_2024_gegeneraliseerd"
PAGE_SIZE = 500


def build_url(start_index=0, gemeente_filter=None):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": PAGE_SIZE,
        "startIndex": start_index,
    }
    if gemeente_filter:
        params["CQL_FILTER"] = gemeente_filter
    return WFS_BASE, params


def download_buurten():
    print("=" * 60)
    print("Download CBS Buurten 2024 — Fryslân")
    print("=" * 60)
    print(f"Bron: PDOK WFS ({LAYER})")
    print(f"Filter: {len(FRIESE_GEMEENTEN)} Friese gemeenten")
    print()

    # Bouw CQL filter: gemeentecode IN ('GM0059', 'GM0060', ...)
    codes_str = ",".join(f"'{c}'" for c in FRIESE_GEMEENTEN)
    gemeente_filter = f"gemeentecode IN ({codes_str})"

    all_features = []
    start_index = 0
    pagina = 1
    crs = None

    while True:
        print(f"  📥 Pagina {pagina} (offset {start_index})...", end=" ", flush=True)
        url, params = build_url(start_index, gemeente_filter)

        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"\n❌ Fout: {e}")
            break

        data = resp.json()

        if "features" not in data:
            print(f"\n❌ Onverwacht response: {list(data.keys())}")
            # Probeer zonder CQL_FILTER (layer naam misschien anders)
            print("   Probeer zonder filter om layernaam te checken...")
            resp2 = requests.get(WFS_BASE, params={
                "service": "WFS", "version": "2.0.0",
                "request": "GetFeature", "typeName": LAYER,
                "outputFormat": "application/json", "count": "1"
            }, timeout=30)
            print(f"   Status: {resp2.status_code}")
            if resp2.status_code == 200:
                d2 = resp2.json()
                print(f"   Keys: {list(d2.keys())}")
                if "features" in d2 and d2["features"]:
                    props = list(d2["features"][0].get("properties", {}).keys())
                    print(f"   Properties: {props}")
            break

        features = data.get("features", [])
        if crs is None:
            crs = data.get("crs")
        all_features.extend(features)
        print(f"{len(features)} features → totaal: {len(all_features)}")

        if len(features) < PAGE_SIZE:
            break  # Laatste pagina

        start_index += PAGE_SIZE
        pagina += 1
        time.sleep(0.5)  # Netjes zijn voor de API

    if not all_features:
        print("\n⚠️  Geen features ontvangen. Probeer alternatieve laagnaam...")
        # Probeer 'gegeneraliseerd' eraf
        return try_alternative_layer()

    # Schrijf GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "name": "CBS Buurten 2024 - Fryslân",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": all_features
    }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"\n✅ Opgeslagen: {OUTPUT}")
    print(f"   {len(all_features)} buurten | {size_mb:.1f} MB")
    return True


def try_alternative_layer():
    """Probeer alternatieve laagnamen als de eerste niet werkt."""
    alternative_layers = [
        "cbsgebiedsindelingen:cbs_buurten_2024",
        "cbsgebiedsindelingen:cbs_buurten_2023_gegeneraliseerd",
        "cbsgebiedsindelingen:cbs_buurten_2023",
    ]

    for layer in alternative_layers:
        print(f"  🔄 Probeer: {layer}")
        resp = requests.get(WFS_BASE, params={
            "service": "WFS", "version": "2.0.0",
            "request": "GetFeature", "typeName": layer,
            "outputFormat": "application/json", "count": "1"
        }, timeout=30)

        if resp.status_code != 200:
            print(f"     ❌ HTTP {resp.status_code}")
            continue

        data = resp.json()
        if "features" not in data or not data["features"]:
            print(f"     ❌ Geen features")
            continue

        props = list(data["features"][0].get("properties", {}).keys())
        print(f"     ✅ Werkt! Properties: {props[:8]}...")

        # Voer echte download uit met deze layer
        codes_str = ",".join(f"'{c}'" for c in FRIESE_GEMEENTEN)

        # Zoek de juiste property naam voor gemeentecode
        gem_prop = next((p for p in props if 'gemeente' in p.lower() and 'code' in p.lower()), None)
        if not gem_prop:
            gem_prop = next((p for p in props if 'gm_code' in p.lower() or 'gm_naam' in p.lower()), None)

        print(f"     Gemeentecode property: {gem_prop}")
        if not gem_prop:
            print(f"     ⚠️ Alle properties: {props}")
            continue

        gemeente_filter = f"{gem_prop} IN ({codes_str})"
        print(f"     Filter: {gemeente_filter}")

        # Download alle pagina's
        all_features = []
        start_index = 0
        pagina = 1

        while True:
            params = {
                "service": "WFS", "version": "2.0.0",
                "request": "GetFeature", "typeName": layer,
                "outputFormat": "application/json", "srsName": "EPSG:4326",
                "count": PAGE_SIZE, "startIndex": start_index,
                "CQL_FILTER": gemeente_filter
            }
            print(f"  📥 Pagina {pagina}...", end=" ", flush=True)
            r = requests.get(WFS_BASE, params=params, timeout=90)
            r.raise_for_status()
            d = r.json()
            feats = d.get("features", [])
            all_features.extend(feats)
            print(f"{len(feats)} → totaal {len(all_features)}")
            if len(feats) < PAGE_SIZE:
                break
            start_index += PAGE_SIZE
            pagina += 1
            time.sleep(0.5)

        if all_features:
            geojson = {
                "type": "FeatureCollection",
                "name": f"CBS Buurten — Fryslân",
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
                "features": all_features
            }
            with open(OUTPUT, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, separators=(',', ':'))
            size_mb = OUTPUT.stat().st_size / 1024 / 1024
            print(f"\n✅ Opgeslagen: {OUTPUT}")
            print(f"   {len(all_features)} buurten | {size_mb:.1f} MB")
            return True

    print("\n❌ Alle alternatieven mislukt. Controleer PDOK bereikbaarheid.")
    return False


if __name__ == "__main__":
    download_buurten()
