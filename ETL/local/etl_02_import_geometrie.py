#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 2: Geometrie Importeren
===============================================
Importeert CBS buurtgrenzen (GeoJSON via PDOK WFS) naar de database.

Bronnen:
  - Primair: PDOK WFS API (live download, altijd actueel)
  - Alternatief: lokaal GeoJSON bestand

Gebruik:
    cd ETL/local
    python etl_02_import_geometrie.py

    # Specifieke provincie:
    python etl_02_import_geometrie.py --provincie Fryslan

    # Specifieke gemeenten (CBS codes):
    python etl_02_import_geometrie.py --gemeenten 1900,0090,1940

    # Lokaal GeoJSON bestand:
    python etl_02_import_geometrie.py --bestand /pad/naar/buurten.geojson

    # Alleen tellen wat er al in de DB zit:
    python etl_02_import_geometrie.py --check

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini

Vereisten:
    pip install psycopg2-binary requests
    PostgreSQL met PostGIS extensie
"""

import sys
import json
import argparse
import time
from pathlib import Path

LOCAL_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_DIR.parent.parent

sys.path.insert(0, str(LOCAL_DIR))
from db_connect import get_connection, get_etl_config

# PDOK WFS endpoint voor CBS buurten
PDOK_WFS_URL = "https://service.pdok.nl/cbs/wijkenbuurten/2023/wfs/v1_0"

# Gebiedstype UUID voor CBS Buurten (uit schema seed)
CBS_BUURT_TYPE_ID = "afba67cb-6b38-4723-9c95-102a22d5b38a"

# Alle Friese gemeente CBS-codes (standaard scope)
FRYSLAN_GEMEENTEN = {
    "0059": "Achtkarspelen",   "0060": "Ameland",
    "1891": "Dantumadiel",     "1940": "De Fryske Marren",
    "0072": "Harlingen",       "0074": "Heerenveen",
    "0080": "Leeuwarden",      "1970": "Noardeast-Fryslân",
    "0085": "Ooststellingwerf","0086": "Opsterland",
    "0088": "Schiermonnikoog", "0090": "Smallingerland",
    "1900": "Súdwest-Fryslân", "0093": "Terschelling",
    "0737": "Tytsjerksteradiel","0096": "Vlieland",
    "1949": "Waadhoeke",       "0098": "Weststellingwerf",
}


def fetch_via_pdok(gemeente_codes: list, provincie_filter: str = None) -> list:
    """
    Download CBS buurtgrenzen via PDOK WFS API.

    Args:
        gemeente_codes: Lijst van CBS gemeente codes (bijv. ['1900', '0090'])
        provincie_filter: Optioneel provinciefiltert (bijv. 'Fryslan')

    Returns:
        Lijst van GeoJSON features
    """
    try:
        import requests
    except ImportError:
        print("❌ requests niet gevonden. Installeer met: pip install requests")
        sys.exit(1)

    all_features = []

    # WFS ondersteunt max ~500 features per request — gebruik paginering
    WFS_PARAMS = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "wijkenbuurten2023:cbs_buurten_2023",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": 500,
        "startIndex": 0,
    }

    if provincie_filter:
        # WFS CQL filter op provincienaam
        prov = provincie_filter.replace("Fryslan", "Fryslân").replace("Fryslân", "Fryslân")
        WFS_PARAMS["CQL_FILTER"] = f"provincienaam='{prov}'"
    elif gemeente_codes:
        # Filter op specifieke gemeentes
        filters = " OR ".join([f"gemeentecode='GM{code.zfill(4)}'" for code in gemeente_codes])
        WFS_PARAMS["CQL_FILTER"] = f"({filters})"

    print(f"  🌐 Ophalen via PDOK WFS: {PDOK_WFS_URL}")
    if "CQL_FILTER" in WFS_PARAMS:
        print(f"  🔍 Filter: {WFS_PARAMS['CQL_FILTER'][:80]}...")

    session = requests.Session()
    start_time = time.time()

    while True:
        try:
            resp = session.get(PDOK_WFS_URL, params=WFS_PARAMS, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"\n❌ PDOK WFS fout: {e}")
            print("   Probeer --bestand met een lokaal GeoJSON bestand")
            sys.exit(1)

        features = data.get("features", [])
        all_features.extend(features)

        print(f"  📥 {len(all_features)} buurten opgehaald...", end="\r")

        # Controleer of er meer pagina's zijn
        total_matched = data.get("totalFeatures", data.get("numberMatched", 0))
        if not features or len(all_features) >= total_matched:
            break

        WFS_PARAMS["startIndex"] += WFS_PARAMS["count"]
        WFS_PARAMS.pop("CQL_FILTER", None)  # CQL alleen bij eerste aanroep

    elapsed = time.time() - start_time
    print(f"\n  ✅ {len(all_features)} buurten opgehaald in {elapsed:.1f}s")
    return all_features


def load_from_file(bestand_pad: str) -> list:
    """Laad GeoJSON features uit een lokaal bestand."""
    path = Path(bestand_pad)
    if not path.exists():
        print(f"❌ Bestand niet gevonden: {path}")
        sys.exit(1)

    print(f"  📂 Laden uit: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", data if isinstance(data, list) else [])
    print(f"  ✅ {len(features)} features geladen")
    return features


def import_features(conn, features: list, gemeente_codes_filter: list = None) -> dict:
    """
    Importeer GeoJSON features naar de gebieden tabel.

    Returns:
        Dict met statistieken
    """
    # Haal bestaande gemeente codes op uit DB
    cur = conn.cursor()
    cur.execute("SELECT code FROM gemeenten")
    db_gemeente_codes = {row[0] for row in cur.fetchall()}

    stats = {"ingevoegd": 0, "bijgewerkt": 0, "overgeslagen": 0, "fouten": 0}

    for feature in features:
        props = feature.get("properties", {})
        geom  = feature.get("geometry")

        # Normaliseer CBS veldnamen (PDOK gebruikt verschillende benamingen)
        bu_code = (
            props.get("buurtcode") or props.get("bu_code") or
            props.get("statcode")  or props.get("BU_CODE") or ""
        ).strip()
        bu_naam = (
            props.get("buurtnaam") or props.get("bu_naam") or
            props.get("statnaam")  or props.get("BU_NAAM") or "Onbekend"
        ).strip()
        gm_code_raw = (
            props.get("gemeentecode") or props.get("gm_code") or
            props.get("GM_CODE") or ""
        ).strip()

        # Normaliseer: verwijder 'BU' prefix en zorg voor 8 cijfers
        bu_code = bu_code.replace("BU", "").replace("bu", "")
        bu_id   = f"BU{bu_code.zfill(8)}"

        # Normaliseer gemeente code: verwijder 'GM' prefix
        gm_code = gm_code_raw.replace("GM", "").replace("gm", "").zfill(4)

        if not bu_code:
            stats["overgeslagen"] += 1
            continue

        # Optionele filter op gemeente codes
        if gemeente_codes_filter and gm_code not in gemeente_codes_filter:
            stats["overgeslagen"] += 1
            continue

        # Controleer of gemeente in DB bestaat (anders FK violation)
        if gm_code and gm_code not in db_gemeente_codes:
            # Probeer gemeente aan te maken
            gm_naam = props.get("gemeentenaam", f"Gemeente {gm_code}")
            prov    = props.get("provincienaam", "Onbekend")
            try:
                cur.execute("SAVEPOINT sp_gemeente")
                cur.execute("""
                    INSERT INTO gemeenten (code, naam, provincie)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                """, (gm_code, gm_naam, prov))
                cur.execute("RELEASE SAVEPOINT sp_gemeente")
                db_gemeente_codes.add(gm_code)
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_gemeente")
                gm_code = None  # FK probleem voorkomen

        geom_str = json.dumps(geom) if geom else None

        try:
            cur.execute("SAVEPOINT sp_buurt")
            cur.execute("""
                INSERT INTO gebieden
                    (id, gebiedstype_id, naam, gemeente_code, geom, actief)
                VALUES (
                    %s, %s, %s, %s,
                    CASE WHEN %s IS NOT NULL
                         THEN ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 28992)
                         ELSE NULL END,
                    true
                )
                ON CONFLICT (id) DO UPDATE SET
                    naam          = EXCLUDED.naam,
                    gemeente_code = EXCLUDED.gemeente_code,
                    geom          = EXCLUDED.geom,
                    updated_at    = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, (bu_id, CBS_BUURT_TYPE_ID, bu_naam, gm_code or None,
                  geom_str, geom_str))

            was_inserted = cur.fetchone()
            cur.execute("RELEASE SAVEPOINT sp_buurt")

            if was_inserted and was_inserted[0]:
                stats["ingevoegd"] += 1
            else:
                stats["bijgewerkt"] += 1

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_buurt")
            stats["fouten"] += 1
            if stats["fouten"] <= 3:
                print(f"\n  ⚠️  Fout bij {bu_id}: {e}")

    conn.commit()
    cur.close()
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — CBS buurten importeren",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_02_import_geometrie.py
  python etl_02_import_geometrie.py --provincie Fryslan
  python etl_02_import_geometrie.py --gemeenten 1900,0090
  python etl_02_import_geometrie.py --bestand /data/buurten_2023.geojson
  python etl_02_import_geometrie.py --check
        """
    )
    parser.add_argument(
        "--provincie",
        help="Filteren op provincie (bijv. Fryslan, Groningen)"
    )
    parser.add_argument(
        "--gemeenten",
        help="Komma-gescheiden CBS gemeente codes (bijv. 1900,0090,1940)"
    )
    parser.add_argument(
        "--bestand",
        help="Pad naar lokaal GeoJSON bestand"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Alleen tellen wat er in de DB zit, niets importeren"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🗺️  D-OmniTwin — Stap 2: Geometrie Importeren")
    print("=" * 60)

    conn = get_connection()
    etl_cfg = get_etl_config()

    if args.check:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM gebieden")
        print(f"\n📊 Gebieden in database: {cur.fetchone()[0]:,}")
        cur.execute("SELECT COUNT(*) FROM gebieden WHERE geom IS NOT NULL")
        print(f"   Met geometrie:        {cur.fetchone()[0]:,}")
        cur.execute("SELECT COUNT(*) FROM gebieden WHERE geom IS NULL")
        print(f"   Zonder geometrie:     {cur.fetchone()[0]:,}")
        cur.close()
        conn.close()
        return

    # Bepaal gemeente codes
    gemeente_codes = []
    if args.gemeenten:
        gemeente_codes = [c.strip().zfill(4) for c in args.gemeenten.split(",") if c.strip()]
    elif etl_cfg.get("gemeente_codes"):
        gemeente_codes = [c.zfill(4) for c in etl_cfg["gemeente_codes"]]

    # Laad features
    print("\n📥 Buurtgeometrieën ophalen:")
    if args.bestand:
        features = load_from_file(args.bestand)
    else:
        features = fetch_via_pdok(gemeente_codes, args.provincie)

    if not features:
        print("❌ Geen features gevonden om te importeren")
        conn.close()
        sys.exit(1)

    # Importeer
    print(f"\n💾 Importeren naar database:")
    start = time.time()
    stats = import_features(conn, features, gemeente_codes or None)
    elapsed = time.time() - start

    print(f"\n📊 Resultaat ({elapsed:.1f}s):")
    print(f"  ✅ Nieuw ingevoegd:  {stats['ingevoegd']:,}")
    print(f"  🔄 Bijgewerkt:       {stats['bijgewerkt']:,}")
    print(f"  ⏭️  Overgeslagen:     {stats['overgeslagen']:,}")
    print(f"  ❌ Fouten:           {stats['fouten']:,}")

    print("\n" + "=" * 60)
    print("✅ Stap 2 voltooid!")
    print()
    print("   Volgende stap:")
    print("   python etl_03_seed_indicatoren.py")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
