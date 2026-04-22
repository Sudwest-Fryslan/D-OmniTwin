#!/usr/bin/env python3
"""
D-OmniTwin ETL — Stap 4: CBS Data Importeren
=============================================
Haalt CBS kerncijfers (en optioneel RIVM gezondheidsdata) op via de
CBS OData API en laadt deze als indicator-metingen naar de database.

Bronnen:
  - CBS Kerncijfers Wijken en Buurten (opendata.cbs.nl)
  - RIVM Gezondheidsmonitor (dataderden.cbs.nl)
  - Alle configuratie via ETL/CBS/cbs_mapping_v3.json

Gebruik:
    cd ETL/local
    python etl_04_import_cbs.py

    # Specifieke gemeenten (CBS codes):
    python etl_04_import_cbs.py --gemeenten 1900,0090

    # Specifiek dataset:
    python etl_04_import_cbs.py --dataset 84799NED --gemeenten 1900

    # Alleen RIVM gezondheidsdata (dataderden endpoint):
    python etl_04_import_cbs.py --rivm --gemeenten 1900

    # Alleen ophalen, niet importeren:
    python etl_04_import_cbs.py --extract-only --gemeenten 1900

    # Alleen importeren vanuit eerder opgeslagen JSON:
    python etl_04_import_cbs.py --import-only

    # Alle beschikbare datasets tonen:
    python etl_04_import_cbs.py --lijst

Configuratie:
    Zie ETL/local/db.ini.example → kopieer naar ETL/local/db.ini
    Dataset IDs:   ETL/CBS/cbs_dataset_config.json
    Kolom mapping: ETL/CBS/cbs_mapping_v3.json
"""

import sys
import os
import json
import glob
import argparse
import time
from pathlib import Path

LOCAL_DIR    = Path(__file__).resolve().parent
ETL_DIR      = LOCAL_DIR.parent
PROJECT_ROOT = ETL_DIR.parent
CBS_DIR      = ETL_DIR / "CBS"

# Voeg CBS map toe zodat we CBSDataFetcher kunnen importeren
sys.path.insert(0, str(CBS_DIR))
sys.path.insert(0, str(LOCAL_DIR))

from db_connect import get_connection, get_etl_config


def load_json(pad: Path) -> dict | list:
    """Laad een JSON bestand."""
    if not pad.exists():
        print(f"❌ Bestand niet gevonden: {pad}")
        sys.exit(1)
    with open(pad, encoding="utf-8") as f:
        return json.load(f)


def get_indicator_uuid(conn, naam: str, code: str = None, bron: str = None) -> str:
    """
    Haal indicator UUID op, of maak de indicator aan als die nog niet bestaat.
    Geeft altijd een UUID terug.
    """
    cur = conn.cursor()

    # 1. Zoek op code
    if code:
        cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
        row = cur.fetchone()
        if row:
            cur.close()
            return str(row[0])

    # 2. Zoek op naam (exact)
    cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (naam,))
    row = cur.fetchone()
    if row:
        cur.close()
        return str(row[0])

    # 3. Aanmaken
    print(f"  ✨ Nieuwe indicator aangemaakt: {naam}")
    cur.execute("""
        INSERT INTO indicatoren (uuid, naam, code, bron, score_type, status)
        VALUES (gen_random_uuid(), %s, %s, %s, '+/+', 'O')
        ON CONFLICT (code) DO UPDATE SET naam = EXCLUDED.naam
        RETURNING uuid
    """, (naam, code or f"IND_{naam[:40].upper().replace(' ', '_')}", bron))
    uuid = str(cur.fetchone()[0])
    conn.commit()
    cur.close()
    return uuid


def import_json_naar_db(conn, json_pad: Path, mapping: dict, dataset_id: str, jaar: int = 2023) -> dict:
    """
    Verwerk een opgeslagen CBS DATA JSON bestand naar de database.

    Args:
        conn: Database verbinding
        json_pad: Pad naar *_DATA.json bestand
        mapping: Mapping definitie uit cbs_mapping_v3.json
        dataset_id: CBS dataset ID voor de bron-tag

    Returns:
        Dict met statistieken
    """
    with open(json_pad, encoding="utf-8") as f:
        data = json.load(f)

    records  = data.get("data", {}).get("records", [])
    metadata_pad = str(json_pad).replace("_DATA.json", "_METADATA.json")

    # Lees metadata voor kolomtitels → kolomkeys mapping
    title_to_key = {}
    if Path(metadata_pad).exists():
        with open(metadata_pad, encoding="utf-8") as f:
            meta = json.load(f)
        for prop in meta.get("metadata", {}).get("properties", []):
            t = prop.get("title") or prop.get("Title")
            k = prop.get("key")   or prop.get("Key")
            if t and k:
                title_to_key[t] = k

        # Probeer jaar uit dataset titel te halen
        ds_title = meta.get("dataset", {}).get("title", "")
        import re
        m = re.search(r"20\d{2}", ds_title)
        if m:
            jaar = int(m.group(0))

    columns_map     = mapping.get("columns", [])
    indicator_names = mapping.get("indicator_name", [])
    use_titles      = mapping.get("use_titles", False)
    normalize_field = mapping.get("normalize")

    # Resolve fysieke kolomnamen
    physical_cols = []
    for col in columns_map:
        if use_titles:
            key = title_to_key.get(col, col)
        else:
            key = col
        physical_cols.append(key)

    # Pre-resolve indicator UUIDs
    indicator_uuids = []
    for i, ind_naam in enumerate(indicator_names):
        col_ref = physical_cols[i] if i < len(physical_cols) else f"IND_{i}"
        code = f"CBS_{col_ref.split('_')[0][:40].upper()}"
        uuid = get_indicator_uuid(conn, ind_naam, code=code, bron=f"CBS {dataset_id}")
        indicator_uuids.append(uuid)

    stats = {"geladen": 0, "overgeslagen": 0, "fouten": 0}
    cur = conn.cursor()

    for rec in records:
        # Haal gebied code op
        area_code = (rec.get("WijkenEnBuurten") or rec.get("RegioS") or "").strip()
        if not (area_code.startswith("BU") or area_code.startswith("WK")):
            stats["overgeslagen"] += 1
            continue

        # Controleer of gebied bestaat
        cur.execute("SELECT id FROM gebieden WHERE id = %s", (area_code,))
        if not cur.fetchone():
            stats["overgeslagen"] += 1
            continue

        # Haal jaar op uit record (Perioden kolom)
        periode = rec.get("Perioden", "")
        rec_jaar = jaar
        if periode and len(periode) >= 4 and periode[:4].isdigit():
            try:
                rec_jaar = int(periode[:4])
            except ValueError:
                pass

        # Importeer per kolom
        for i, phys_col in enumerate(physical_cols):
            if not phys_col or i >= len(indicator_uuids):
                continue

            val = rec.get(phys_col)
            if val is None:
                continue

            try:
                val_float = float(val)
            except (ValueError, TypeError):
                continue

            # Normalisatie (bijv. huishoudens als % van totaal)
            if normalize_field:
                norm_key = title_to_key.get(normalize_field, normalize_field) if use_titles else normalize_field
                norm_val = rec.get(norm_key)
                if norm_val:
                    try:
                        norm_float = float(norm_val)
                        if norm_float > 0:
                            val_float = (val_float / norm_float) * 100
                    except (ValueError, TypeError):
                        pass

            try:
                cur.execute("SAVEPOINT sp_data")
                cur.execute("""
                    INSERT INTO gebied_data
                        (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
                    VALUES (%s, %s, %s, %s, %s, 'current')
                    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
                    DO UPDATE SET
                        waarde     = EXCLUDED.waarde,
                        updated_at = CURRENT_TIMESTAMP
                """, (area_code, indicator_uuids[i], val_float, rec_jaar, f"CBS_{dataset_id}"))
                cur.execute("RELEASE SAVEPOINT sp_data")
                stats["geladen"] += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_data")
                stats["fouten"] += 1
                if stats["fouten"] <= 3:
                    print(f"  ⚠️  Insert fout: {e}")

    conn.commit()
    cur.close()
    return stats


def haal_op_en_importeer(
    conn, dataset_id: str, mapping: dict, gemeente_codes: list,
    endpoint: str = "opendata.cbs.nl", output_dir: Path = None,
    extract_only: bool = False, import_only: bool = False,
    etl_cfg: dict = None
):
    """Voer de volledige ETL cyclus uit voor één dataset."""
    try:
        from cbs_data_fetcher import CBSDataFetcher
    except ImportError:
        print("❌ cbs_data_fetcher.py niet gevonden in ETL/CBS/")
        print(f"   Zorg dat het bestand bestaat: {CBS_DIR / 'cbs_data_fetcher.py'}")
        sys.exit(1)

    if output_dir is None:
        output_dir = LOCAL_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    fetcher = CBSDataFetcher(endpoint=endpoint, timeout=etl_cfg.get("cbs_timeout", 60) if etl_cfg else 60)

    totaal = {"geladen": 0, "overgeslagen": 0, "fouten": 0}

    for gm_code in (gemeente_codes or [None]):
        label = f"gemeente {gm_code}" if gm_code else "alle gemeenten"
        print(f"\n  🏙️  Verwerken: {label} (dataset {dataset_id})")

        if not import_only:
            # Extract: download CBS data
            print(f"    📥 Ophalen van {endpoint}...")
            try:
                fetcher.fetch_and_save(dataset_id, output_dir=str(output_dir), gemeente_filter=gm_code)
            except Exception as e:
                print(f"    ❌ Ophalen mislukt: {e}")
                continue

        if extract_only:
            continue

        # Import: verwerk opgeslagen JSON bestanden
        json_bestanden = sorted(glob.glob(str(output_dir / "*_DATA.json")), key=os.path.getmtime, reverse=True)
        if not json_bestanden:
            print(f"    ⚠️  Geen DATA.json bestanden gevonden in {output_dir}")
            continue

        # Neem meest recente
        json_pad = Path(json_bestanden[0])
        print(f"    💾 Importeren: {json_pad.name}")
        stats = import_json_naar_db(conn, json_pad, mapping, dataset_id,
                                    jaar=etl_cfg.get("default_jaar", 2023) if etl_cfg else 2023)
        print(f"    ✅ Geladen: {stats['geladen']:,} | Overgeslagen: {stats['overgeslagen']:,} | Fouten: {stats['fouten']:,}")

        for k in totaal:
            totaal[k] += stats[k]

    return totaal


def main():
    parser = argparse.ArgumentParser(
        description="D-OmniTwin — CBS data importeren",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python etl_04_import_cbs.py --gemeenten 1900
  python etl_04_import_cbs.py --gemeenten 1900,0090 --dataset 84799NED
  python etl_04_import_cbs.py --rivm --gemeenten 1900
  python etl_04_import_cbs.py --extract-only --gemeenten 1900
  python etl_04_import_cbs.py --import-only
  python etl_04_import_cbs.py --lijst
        """
    )
    parser.add_argument(
        "--gemeenten",
        help="Komma-gescheiden CBS gemeente codes (bijv. 1900,0090)"
    )
    parser.add_argument(
        "--dataset",
        help="Specifieke CBS dataset ID (bijv. 84799NED). Overrides cbs_dataset_config.json."
    )
    parser.add_argument(
        "--rivm", action="store_true",
        help="RIVM data via dataderden.cbs.nl endpoint"
    )
    parser.add_argument(
        "--extract-only", action="store_true",
        help="Alleen ophalen (JSON opslaan), niet in DB laden"
    )
    parser.add_argument(
        "--import-only", action="store_true",
        help="Niet ophalen, alleen eerder opgeslagen JSON importeren"
    )
    parser.add_argument(
        "--lijst", action="store_true",
        help="Toon alle geconfigureerde datasets"
    )
    parser.add_argument(
        "--output",
        help="Output map voor CBS JSON bestanden"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("📈 D-OmniTwin — Stap 4: CBS Data Importeren")
    print("=" * 60)

    # Laad configuraties
    mapping_pad = CBS_DIR / "cbs_mapping_v3.json"
    dataset_cfg_pad = CBS_DIR / "cbs_dataset_config.json"
    mappings     = load_json(mapping_pad)
    dataset_cfg  = load_json(dataset_cfg_pad)

    if args.lijst:
        print("\n📋 Geconfigureerde datasets:")
        for mapping in mappings:
            table_name = mapping["table_name"]
            ds_info = dataset_cfg.get(table_name, "—")
            print(f"  • {table_name}")
            print(f"    Dataset IDs: {ds_info}")
            print(f"    Kolommen:    {len(mapping.get('columns', []))}")
        return

    etl_cfg = get_etl_config()
    conn    = get_connection()

    # Gemeente codes
    gemeente_codes = []
    if args.gemeenten:
        gemeente_codes = [c.strip().zfill(4) for c in args.gemeenten.split(",") if c.strip()]
    elif etl_cfg.get("gemeente_codes"):
        gemeente_codes = [c.zfill(4) for c in etl_cfg["gemeente_codes"]]

    if not gemeente_codes:
        print("ℹ️  Geen gemeente codes opgegeven — verwerkt alle gemeenten in de database")

    # Output map
    output_dir = Path(args.output) if args.output else LOCAL_DIR / "output"

    # Endpoint
    endpoint = etl_cfg.get("cbs_endpoint_derden", "dataderden.cbs.nl") if args.rivm \
               else etl_cfg.get("cbs_endpoint_public", "opendata.cbs.nl")

    print(f"\n🔧 Instellingen:")
    print(f"  Gemeenten:  {gemeente_codes or '(alle)'}")
    print(f"  Endpoint:   {endpoint}")
    print(f"  Output:     {output_dir}")

    groot_totaal = {"geladen": 0, "overgeslagen": 0, "fouten": 0}

    for mapping in mappings:
        table_name = mapping["table_name"]

        # Specifiek dataset override
        if args.dataset:
            datasets_te_verwerken = [{"id": args.dataset, "endpoint": endpoint}]
        else:
            ds_val = dataset_cfg.get(table_name)
            if not ds_val:
                continue

            # RIVM filter
            if args.rivm:
                # Verwerk alleen datasets op dataderden endpoint
                if isinstance(ds_val, dict) and "dataderden" not in ds_val.get("endpoint", ""):
                    continue
                elif isinstance(ds_val, str):
                    continue

            # Normaliseer naar lijst
            if isinstance(ds_val, str):
                datasets_te_verwerken = [{"id": ds_val, "endpoint": endpoint}]
            elif isinstance(ds_val, list):
                datasets_te_verwerken = [{"id": v, "endpoint": endpoint} if isinstance(v, str) else v for v in ds_val]
            elif isinstance(ds_val, dict):
                datasets_te_verwerken = [ds_val]
            else:
                continue

        print(f"\n{'='*50}")
        print(f"📊 Tabel: {table_name}")

        for ds_info in datasets_te_verwerken:
            ds_id   = ds_info["id"]
            ds_ep   = ds_info.get("endpoint", endpoint)

            totaal = haal_op_en_importeer(
                conn, ds_id, mapping, gemeente_codes,
                endpoint=ds_ep, output_dir=output_dir,
                extract_only=args.extract_only,
                import_only=args.import_only,
                etl_cfg=etl_cfg,
            )
            for k in groot_totaal:
                groot_totaal[k] += totaal.get(k, 0)

    print("\n" + "=" * 60)
    print("📊 Eindtotaal:")
    print(f"  ✅ Metingen geladen:   {groot_totaal['geladen']:,}")
    print(f"  ⏭️  Overgeslagen:       {groot_totaal['overgeslagen']:,}")
    print(f"  ❌ Fouten:             {groot_totaal['fouten']:,}")
    print()
    print("✅ Stap 4 voltooid!")
    print()
    print("   Volgende stap:")
    print("   python etl_05_import_kompas.py")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
