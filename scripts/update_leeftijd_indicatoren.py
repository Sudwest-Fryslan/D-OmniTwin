#!/usr/bin/env python3
import sys
import os
import uuid
import configparser
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    from dotenv import load_dotenv
    import os
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
    conn.autocommit = False
    
    # Old indicators to delete
    old_names = ['0-3 jaar', '4-12 jaar', '13-17 jaar', '28-64 jaar', '65+ jaar', '65-79 jaar', '80+ jaar']
    
    # New indicators to add
    new_indicators = [
        {'naam': '0-15 jaar', 'code': 'CBS_K_0TOT15JAAR_8'},
        {'naam': '15-25 jaar', 'code': 'CBS_K_15TOT25JAAR_9'},
        {'naam': '25-45 jaar', 'code': 'CBS_K_25TOT45JAAR_10'},
        {'naam': '45-65 jaar', 'code': 'CBS_K_45TOT65JAAR_11'},
        {'naam': '65+ jaar', 'code': 'CBS_K_65JAAROFOUDER_12'}
    ]
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("1. Identifying old indicators...")
            cur.execute("SELECT uuid, naam FROM indicatoren WHERE naam = ANY(%s)", (old_names,))
            old_inds = cur.fetchall()
            old_uuids = [ind['uuid'] for ind in old_inds]
            
            if old_uuids:
                print(f"Found {len(old_uuids)} old indicators. Deleting dependencies...")
                # Delete from gebied_data
                cur.execute("DELETE FROM gebied_data WHERE indicator_uuid = ANY(%s::uuid[])", (old_uuids,))
                print(f"Deleted {cur.rowcount} rows from gebied_data.")
                
                # Delete from kompas_indicator_mapping
                cur.execute("DELETE FROM kompas_indicator_mapping WHERE indicator_uuid = ANY(%s::uuid[])", (old_uuids,))
                print(f"Deleted {cur.rowcount} rows from kompas_indicator_mapping.")
                
                # Delete indicator_gebiedstype_relaties
                cur.execute("DELETE FROM indicator_gebiedstype_relaties WHERE indicator_uuid = ANY(%s::uuid[])", (old_uuids,))
                print(f"Deleted {cur.rowcount} rows from indicator_gebiedstype_relaties.")

                # Delete scoring rules
                cur.execute("DELETE FROM kompas_indicator_scoring_regels WHERE indicator_uuid = ANY(%s::uuid[])", (old_uuids,))
                print(f"Deleted {cur.rowcount} rows from kompas_indicator_scoring_regels.")
                
                # Finally delete from indicatoren
                cur.execute("DELETE FROM indicatoren WHERE uuid = ANY(%s::uuid[])", (old_uuids,))
                print(f"Deleted {cur.rowcount} rows from indicatoren.")
            else:
                print("No old indicators found (maybe already deleted).")
                
            print("\n2. Finding 'Leeftijd' onderdeel for Kompas mapping...")
            cur.execute("SELECT id FROM kompas_onderdelen WHERE naam ILIKE 'Leeftijd'")
            onderdeel = cur.fetchone()
            if not onderdeel:
                raise Exception("Could not find 'Leeftijd' in kompas_onderdelen table!")
            onderdeel_id = onderdeel['id']
            print(f"Found onderdeel_id: {onderdeel_id}")
            
            # Find all active kompas configs
            cur.execute("SELECT id FROM kompas_configuraties WHERE is_actief = TRUE")
            active_configs = [c['id'] for c in cur.fetchall()]
            print(f"Active Kompas Configs: {active_configs}")
            
            print("\n3. Creating new indicators and mapping them...")
            # For each new indicator, we want a fixed UUID for simplicity or generate one. Let's generate.
            # We insert with a specific volgorde (1 to 5)
            for i, ind in enumerate(new_indicators, start=1):
                # Check if it already exists by name
                cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (ind['naam'],))
                existing = cur.fetchone()
                
                if existing:
                    new_uuid = existing['uuid']
                    print(f"Indicator '{ind['naam']}' already exists with UUID {new_uuid}")
                else:
                    new_uuid = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO indicatoren (uuid, naam, code, eenheid, bron, status) 
                        VALUES (%s, %s, %s, 'Aantal', 'CBS', 'O')
                    """, (new_uuid, ind['naam'], ind['code']))
                    print(f"Created indicator '{ind['naam']}' with UUID {new_uuid}")
                
                # For each config, add to kompas_indicator_mapping
                for config_id in active_configs:
                    # Check if mapped
                    cur.execute("""
                        SELECT id FROM kompas_indicator_mapping 
                        WHERE config_id = %s AND indicator_uuid = %s AND onderdeel_id = %s
                    """, (config_id, new_uuid, onderdeel_id))
                    
                    if not cur.fetchone():
                        try:
                            cur.execute("""
                                INSERT INTO kompas_indicator_mapping (config_id, indicator_uuid, onderdeel_id)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (config_id, new_uuid, onderdeel_id))
                            if cur.rowcount > 0:
                                print(f"Mapped '{ind['naam']}' to config {config_id}")
                        except psycopg2.errors.UniqueViolation:
                            print(f"Skipped mapping '{ind['naam']}' to config {config_id} (already exists)")
                            conn.rollback()
                            conn.autocommit = False # Need to handle transaction carefully, wait ON CONFLICT DO NOTHING handles it without error!
                    
            conn.commit()
            print("\n✅ Migration complete!")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
