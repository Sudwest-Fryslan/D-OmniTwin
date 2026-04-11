#!/usr/bin/env python3
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm
from dotenv import load_dotenv

# Add ETL/CBS to path for CBSDataFetcher
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ETL', 'CBS'))
from cbs_data_fetcher import CBSDataFetcher

def get_db_connection():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST'),
        port=os.getenv('DATABASE_PORT'),
        dbname=os.getenv('DATABASE_NAME'),
        user=os.getenv('DATABASE_USER'),
        password=os.getenv('DATABASE_PASSWORD')
    )

def main():
    conn = get_db_connection()
    conn.autocommit = True
    
    fetcher = CBSDataFetcher()
    
    # 1. Map Indicators to DB UUIDs
    safety_map = {
        'inbraak woning': {'type': 'politie', 'id': '47018NED', 'code': '1.1.1', 'column': 'GeregistreerdeMisdrijven_1'},
        'inbraak auto': {'type': 'politie', 'id': '47018NED', 'code': '1.2.1', 'column': 'GeregistreerdeMisdrijven_1'},
        'diefstal fiets': {'type': 'politie', 'id': '47018NED', 'code': '1.2.3', 'column': 'GeregistreerdeMisdrijven_1'},
        "beschadiging auto's": {'type': 'politie', 'id': '47018NED', 'code': '2.2.1', 'column': 'GeregistreerdeMisdrijven_1'},
        'slachtoffer inbraak': {'type': 'cbs', 'id': '85146NED', 'column': 'VanInbraakInWoning_47'}
    }
    
    # Pre-resolve indicator UUIDs
    indicator_uuids = {}
    with conn.cursor() as cur:
        for naam in safety_map.keys():
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (naam,))
            row = cur.fetchone()
            if row:
                indicator_uuids[naam] = row[0]
            else:
                print(f"⚠️  Indicator '{naam}' not found in DB!")
                
    # 2. Fetch and Process Politie Data (47018NED)
    print("\n👮 Fetching Politie Data (47018NED)...")
    fetcher.base_url = "https://dataderden.cbs.nl/ODataApi/odata"
    
    # Target period: Latest available (2024JJ00)
    # Using startswith for codes to avoid space padding issues
    target_codes = ["1.1.1", "1.2.1", "1.2.3", "2.2.1"]
    
    # Fetch GM codes from DB to use for BU batching
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM gebieden WHERE id LIKE 'GM%';")
        gm_codes = [r[0] for r in cur.fetchall()]
        print(f"📌 Found {len(gm_codes)} municipalities for batching.")

    # Workaround for 10k limit: Fetch for GM, WK, and then per-municipality for BU
    # GM and WK are small enough to fetch in one go (per category)
    primary_prefixes = ["GM", "WK", "NL"]
    
    for code in target_codes:
        print(f"📥 Fetching Misdrijf code: {code}...")
        indicator_name = next(k for k, v in safety_map.items() if v.get('code') == code)
        target_uuid = indicator_uuids.get(indicator_name)
        if not target_uuid: continue

        # Step A: Primary Prefixes (GM, WK, NL)
        for prefix in primary_prefixes:
            print(f"   📥 Prefix {prefix}...")
            url = f"{fetcher.base_url}/47018NED/TypedDataSet?$filter=(startswith(SoortMisdrijf,'{code}')) and (Perioden eq '2024JJ00') and (startswith(WijkenEnBuurten,'{prefix}'))&$format=json"
            
            try:
                response = fetcher.session.get(url, timeout=60)
                response.raise_for_status()
                data = response.json().get('value', [])
                
                # Year logic
                if not data and prefix == "GM":
                    print(f"   ⚠️ No 2024 data for {prefix}, trying 2023...")
                    url = f"{fetcher.base_url}/47018NED/TypedDataSet?$filter=(startswith(SoortMisdrijf,'{code}')) and (Perioden eq '2023JJ00') and (startswith(WijkenEnBuurten,'{prefix}'))&$format=json"
                    response = fetcher.session.get(url, timeout=60)
                    response.raise_for_status()
                    data = response.json().get('value', [])
                    jaar_val = 2023
                else:
                    jaar_val = 2024 if (prefix == "GM" and data) else 2024 # default or keep from GM

                if not data: continue
                print(f"   Found {len(data)} records for {code} ({prefix}) in {jaar_val}")
                
                # Import
                with conn.cursor() as cur:
                    for rec in data:
                        regio_code = rec.get('WijkenEnBuurten', '').strip()
                        waarde = rec.get('GeregistreerdeMisdrijven_1')
                        if regio_code and waarde is not None:
                            cur.execute("SELECT id FROM gebieden WHERE id = %s", (regio_code,))
                            if cur.fetchone():
                                cur.execute("""
                                    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar)
                                    VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (gebied_id, indicator_uuid, jaar) DO UPDATE SET waarde = EXCLUDED.waarde
                                """, (regio_code, target_uuid, waarde, jaar_val))

            except Exception as e:
                print(f"   ❌ Error fetching {code} {prefix}: {e}")

        # Step B: Per-Municipality BU Fetching
        print(f"   📥 Fetching BU records per municipality...")
        # To speed up, we only use the year determined in Step A
        # (Assuming jaar_val is set from the GM check above)
        for gm_id in tqdm(gm_codes, desc=f"   BU for {indicator_name}"):
            bu_prefix = "BU" + gm_id[2:]
            url = f"{fetcher.base_url}/47018NED/TypedDataSet?$filter=(startswith(SoortMisdrijf,'{code}')) and (Perioden eq '{jaar_val}JJ00') and (startswith(WijkenEnBuurten,'{bu_prefix}'))&$format=json"
            try:
                response = fetcher.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json().get('value', [])
                if not data: continue
                
                with conn.cursor() as cur:
                    for rec in data:
                        regio_code = rec.get('WijkenEnBuurten', '').strip()
                        waarde = rec.get('GeregistreerdeMisdrijven_1')
                        if regio_code and waarde is not None:
                            # We check if it exists in gebieden before inserting to avoid FK errors
                            cur.execute("SELECT id FROM gebieden WHERE id = %s", (regio_code,))
                            if cur.fetchone():
                                cur.execute("""
                                    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar)
                                    VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (gebied_id, indicator_uuid, jaar) DO UPDATE SET waarde = EXCLUDED.waarde
                                """, (regio_code, target_uuid, waarde, jaar_val))
            except Exception:
                pass # Silently skip errors for individual BU fetches to keep moving

    # 3. Fetch and Process CBS Safety Data (85146NED)
    print("\n📊 Fetching CBS Veiligheidsmonitor (85146NED)...")
    fetcher.base_url = "https://opendata.cbs.nl/ODataFeed/OData"
    
    target_column = 'VanInbraakInWoning_47'
    indicator_name = 'slachtoffer inbraak'
    target_uuid = indicator_uuids.get(indicator_name)
    
    if target_uuid:
        # Veiligheidsmonitor 85146NED is biennial (2021, 2023). 2023JJ00 is latest.
        url = f"{fetcher.base_url}/85146NED/TypedDataSet?$filter=(Perioden eq '2023JJ00')&$format=json"
        try:
            response = fetcher.session.get(url, timeout=60)
            response.raise_for_status()
            data = response.json().get('value', [])
            print(f"   Found {len(data)} records for Veiligheidsmonitor (2023)")
            
            with conn.cursor() as cur:
                count = 0
                for rec in tqdm(data, desc=f"   Importing {indicator_name}"):
                    # Resolve regio (RegioS)
                    regio_code = rec.get('RegioS', '').strip()
                    waarde = rec.get(target_column)
                    
                    if regio_code and waarde is not None:
                        # Use 'id' instead of 'code' for gebieden table
                        cur.execute("SELECT id FROM gebieden WHERE id = %s", (regio_code,))
                        geb_row = cur.fetchone()
                        if geb_row:
                            cur.execute("""
                                INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (gebied_id, indicator_uuid, jaar) 
                                DO UPDATE SET waarde = EXCLUDED.waarde
                            """, (geb_row[0], target_uuid, waarde, 2023))
                            count += 1
                print(f"   ✅ Imported {count} records into DB.")
        except Exception as e:
            print(f"   ❌ Error fetching Veiligheidsmonitor: {e}")

    conn.close()
    print("\n🎉 Safety Data Import complete!")

if __name__ == '__main__':
    main()
