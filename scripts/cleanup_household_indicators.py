#!/usr/bin/env python3
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

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
    conn.autocommit = False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Metadata transfer
            # met kind (4b521d5c-fbd7-458d-8612-cd4e845951f9) -> Huishoudens met kind (ad3b0509-3c14-49f8-aa10-4b3b391a2d84)
            # zonder kind (662d5d2f-d682-4007-8c59-bdb1eae11b98) -> Huishoudens zonder kind (428c1232-0213-491b-ad0c-56dcc82a8c59)
            
            print("1. Transferring metadata and units...")
            
            # Huishoudens met kind
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = 'aantal',
                    omschrijving = (SELECT omschrijving FROM indicatoren WHERE naam = 'met kind' LIMIT 1)
                WHERE naam = 'Huishoudens met kind'
            """)
            print(f"Updated 'Huishoudens met kind': {cur.rowcount} row(s)")
            
            # Huishoudens zonder kind
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = 'aantal',
                    omschrijving = (SELECT omschrijving FROM indicatoren WHERE naam = 'zonder kind' LIMIT 1)
                WHERE naam = 'Huishoudens zonder kind'
            """)
            print(f"Updated 'Huishoudens zonder kind': {cur.rowcount} row(s)")
            
            # 2. Cleanup other missing units in Huishoudens section
            print("\n2. Updating other units in Huishoudens section...")
            other_aantal = ['kind gescheid. Ouders', 'één ouder gezin', 'tm 27 jaar', 'jongeren']
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = 'aantal'
                WHERE naam = ANY(%s) AND (eenheid IS NULL OR eenheid = '')
            """, (other_aantal,))
            print(f"Updated units for {cur.rowcount} indicators to 'aantal'")
            
            # Bevolkingsdichtheid
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = 'inw/km²'
                WHERE naam = 'Bevolkingsdichtheid' AND (eenheid IS NULL OR eenheid = '')
            """)
            print(f"Updated unit for 'Bevolkingsdichtheid': {cur.rowcount} row(s)")
            
            # 3. Delete empty duplicates
            print("\n3. Deleting empty duplicate indicators...")
            to_delete = ['met kind', 'zonder kind']
            
            # Get UUIDs
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = ANY(%s)", (to_delete,))
            delete_uuids = [row['uuid'] for row in cur.fetchall()]
            
            if delete_uuids:
                # Delete from mappings
                cur.execute("DELETE FROM kompas_indicator_mapping WHERE indicator_uuid = ANY(%s::uuid[])", (delete_uuids,))
                print(f"Deleted {cur.rowcount} mappings.")
                
                # Delete from scoring rules
                cur.execute("DELETE FROM kompas_indicator_scoring_regels WHERE indicator_uuid = ANY(%s::uuid[])", (delete_uuids,))
                print(f"Deleted {cur.rowcount} scoring rules.")
                
                # Delete from gebied_data
                cur.execute("DELETE FROM gebied_data WHERE indicator_uuid = ANY(%s::uuid[])", (delete_uuids,))
                print(f"Deleted {cur.rowcount} data rows.")
                
                # Delete from indicatoren
                cur.execute("DELETE FROM indicatoren WHERE uuid = ANY(%s::uuid[])", (delete_uuids,))
                print(f"Deleted {cur.rowcount} indicators.")
            else:
                print("No duplicates found to delete.")
            
            conn.commit()
            print("\n✅ Consolidation and cleanup complete!")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during cleanup: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
