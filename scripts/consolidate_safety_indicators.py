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
            # 1. Diefstal Fiets Consolidation
            # Keep 'diefstal fiets' (3ca8572d-cc03-4fd9-9bc9-e1cd0fc0a627)
            # Merge 'diefstal fietsen' (35cd7fcf-3ddd-49b8-9703-9b07dbf280db)
            print("1. Consolidating 'diefstal fiets'...")
            
            target_fiest = 'diefstal fiets'
            duplicate_fiets = 'diefstal fietsen'
            
            # Get UUIDs
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (target_fiest,))
            target_uuid = cur.fetchone()['uuid']
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (duplicate_fiets,))
            row = cur.fetchone()
            if row:
                duplicate_uuid = row['uuid']
                
                # Move data (if any)
                cur.execute("UPDATE gebied_data SET indicator_uuid = %s WHERE indicator_uuid = %s", (target_uuid, duplicate_uuid))
                print(f"   Moved {cur.rowcount} data rows.")
                
                # Update mappings (if needed) - we prefer the target one
                cur.execute("DELETE FROM kompas_indicator_mapping WHERE indicator_uuid = %s", (duplicate_uuid,))
                print(f"   Deleted {cur.rowcount} mappings for duplicate.")
                
                # Delete duplicate indicator
                cur.execute("DELETE FROM indicatoren WHERE uuid = %s", (duplicate_uuid,))
                print(f"   Deleted duplicate indicator '{duplicate_fiets}'.")
            
            # 2. Inbraak Auto Consolidation
            # Keep 'inbraak auto' (92137246-e0f1-493d-97a8-e4a5660a99fb)
            # Merge 'inbraak auto's ' (fab534cc-537b-46e6-ab80-1fbacadbfca7)
            print("\n2. Consolidating 'inbraak auto'...")
            target_auto = 'inbraak auto'
            duplicate_auto = "inbraak auto's " # Note the trailing space as seen in psql output
            
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (target_auto,))
            target_auto_uuid = cur.fetchone()['uuid']
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (duplicate_auto,))
            row = cur.fetchone()
            if not row:
                # Try without trailing space
                cur.execute("SELECT uuid FROM indicatoren WHERE naam = %s", (target_auto.strip(),))
                row = cur.fetchone()
                
            if row:
                duplicate_auto_uuid = row['uuid']
                
                # Move data
                cur.execute("UPDATE gebied_data SET indicator_uuid = %s WHERE indicator_uuid = %s", (target_auto_uuid, duplicate_auto_uuid))
                print(f"   Moved {cur.rowcount} data rows.")
                
                # Update mappings
                cur.execute("DELETE FROM kompas_indicator_mapping WHERE indicator_uuid = %s", (duplicate_auto_uuid,))
                print(f"   Deleted {cur.rowcount} mappings for duplicate.")
                
                # Delete duplicate
                cur.execute("DELETE FROM indicatoren WHERE uuid = %s", (duplicate_auto_uuid,))
                print(f"   Deleted duplicate indicator '{duplicate_auto}'.")

            # 3. Ensure 'inbraak woning' and 'slachtoffer inbraak' exist and have units
            print("\n3. Verifying other safety indicators...")
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = 'aantal' 
                WHERE naam IN ('inbraak woning', 'inbraak auto', 'diefstal fiets')
            """)
            cur.execute("""
                UPDATE indicatoren 
                SET eenheid = '%' 
                WHERE naam = 'slachtoffer inbraak'
            """)
            print("   Updated units for safety indicators.")

            conn.commit()
            print("\n✅ Consolidation complete!")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during consolidation: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
