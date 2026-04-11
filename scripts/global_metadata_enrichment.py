#!/usr/bin/env python3
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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

def fetch_all_metadata():
    fetcher = CBSDataFetcher()
    
    # Dataset mapping
    datasets = [
        {'id': '86165NED', 'endpoint': 'opendata.cbs.nl', 'label': 'CBS Core 2025'},
        {'id': '85984NED', 'endpoint': 'opendata.cbs.nl', 'label': 'CBS Core 2024'},
        {'id': '83739NED', 'endpoint': 'opendata.cbs.nl', 'label': 'CBS Core 2023'},
        {'id': '84463NED', 'endpoint': 'opendata.cbs.nl', 'label': 'CBS Nabijheid'},
        {'id': '85618NED', 'endpoint': 'opendata.cbs.nl', 'label': 'CBS Overlast'},
        {'id': '50150NED', 'endpoint': 'dataderden.cbs.nl', 'label': 'RIVM Gezondheid'},
        {'id': '50140NED', 'endpoint': 'dataderden.cbs.nl', 'label': 'Gezondheidsmonitor Jongvolwassenen'},
        {'id': '47018NED', 'endpoint': 'dataderden.cbs.nl', 'label': 'Politie Misdrijven'},
        {'id': '47024NED', 'endpoint': 'dataderden.cbs.nl', 'label': 'Politie Overlast'}
    ]
    
    master_map = {}
    
    for ds in datasets:
        print(f"📥 Fetching metadata for {ds['label']} ({ds['id']})...")
        try:
            # Fix endpoint handling
            fetcher = CBSDataFetcher(endpoint=ds['endpoint'])
            
            props = fetcher.fetch_data_properties(ds['id'])
            for p in props:
                title = p.get('Title', '')
                key = p.get('Key', '')
                desc = p.get('Description', '')
                unit = p.get('Unit', '')
                
                # Safe normalization
                unit_str = str(unit or '').lower()
                if unit_str in ['aantal', 'number']:
                    unit = 'aantal'
                elif unit_str in ['percentage', '%']:
                    unit = '%'
                
                # We store both by key and by title for fuzzy matching later
                meta_obj = {
                    'description': desc,
                    'unit': unit,
                    'code': key,
                    'source': ds['label']
                }
                if title:
                    master_map[title.lower()] = meta_obj
                if key:
                    master_map[key.lower()] = meta_obj
                    
        except Exception as e:
            print(f"   ⚠️ Error fetching {ds['id']}: {e}")
            
    return master_map

def is_fuzzy_match(name1, name2):
    """Simple word-based matching logic"""
    if not name1 or not name2:
        return False
    
    n1 = name1.lower().replace('-', ' ').replace('_', ' ')
    n2 = name2.lower().replace('-', ' ').replace('_', ' ')
    
    if n1 == n2:
        return True
    
    # Check if one is a subset of the other or has significant word overlap
    words1 = set(n1.split())
    words2 = set(n2.split())
    
    if not words1 or not words2:
        return False
        
    overlap = words1.intersection(words2)
    if len(overlap) / min(len(words1), len(words2)) >= 0.8:
        return True
        
    return False

def main():
    print("🚀 Start Global Metadata Enrichment")
    print("=" * 50)
    
    # 1. Fetch metadata from APIs
    metadata_cache = fetch_all_metadata()
    print(f"\n✅ Cached metadata for {len(metadata_cache)} properties.")
    
    # 2. Connect to DB
    conn = get_db_connection()
    conn.autocommit = False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 3. Find indicators missing metadata
            cur.execute("""
                SELECT uuid, naam, code, eenheid, omschrijving 
                FROM indicatoren 
                WHERE omschrijving IS NULL OR omschrijving = '' OR eenheid IS NULL OR eenheid = ''
            """)
            indicators = cur.fetchall()
            print(f"🔍 Found {len(indicators)} indicators missing metadata in DB.")
            
            count_updated = 0
            for ind in indicators:
                match = None
                
                # Priority 1: Exact code match
                if ind['code'] and ind['code'].lower() in metadata_cache:
                    match = metadata_cache[ind['code'].lower()]
                
                # Priority 2: Partial code match
                if not match and ind['code']:
                    clean_code = ind['code'].split('_')[-1] if 'CBS_' in ind['code'] else ind['code']
                    if clean_code.lower() in metadata_cache:
                        match = metadata_cache[clean_code.lower()]
                
                # Priority 3: Exact name match
                if not match and ind['naam'].lower() in metadata_cache:
                    match = metadata_cache[ind['naam'].lower()]
                
                # Priority 4: Fuzzy word-based match
                if not match:
                    for meta_title, meta_obj in metadata_cache.items():
                        if is_fuzzy_match(ind['naam'], meta_title):
                            match = meta_obj
                            break
                
                if match:
                    # Enrich!
                    updated_desc = ind['omschrijving']
                    updated_unit = ind['eenheid']
                    
                    if not updated_desc or updated_desc == '':
                        updated_desc = match['description']
                    if not updated_unit or updated_unit == '':
                        updated_unit = match['unit']
                    
                    if updated_desc != ind['omschrijving'] or updated_unit != ind['eenheid']:
                        cur.execute("""
                            UPDATE indicatoren 
                            SET omschrijving = %s,
                                eenheid = %s,
                                admin_notes = COALESCE(admin_notes, '') || '\nMetadata verrijkt uit ' || %s
                            WHERE uuid = %s
                        """, (updated_desc, updated_unit, match['source'], ind['uuid']))
                        count_updated += 1
            
            conn.commit()
            print(f"\n🎉 Enrichment complete! {count_updated} indicators updated.")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during enrichment: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
