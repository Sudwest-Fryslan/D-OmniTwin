import os
import sys
from sqlalchemy import text
from omnitwin.database import get_db, engine

def check_dashboard_data():
    print("--- Starting Dashboard Data Check ---")
    
    db = next(get_db())
    
    try:
        # 1. Check Indicatoren Count
        count = db.execute(text("SELECT COUNT(*) FROM indicatoren")).scalar()
        print(f"Total indicatoren: {count}")
        
        # 2. Check GebiedData Count
        count_gd = db.execute(text("SELECT COUNT(*) FROM gebied_data")).scalar()
        print(f"Total gebied_data rows: {count_gd}")
        
        # 3. Check v_kompas_hierarchie
        # First check if view exists
        try:
            count_vkh = db.execute(text("SELECT COUNT(*) FROM v_kompas_hierarchie")).scalar()
            print(f"Total v_kompas_hierarchie rows: {count_vkh}")
        except Exception as e:
            print(f"Error querying v_kompas_hierarchie: {e}")

        # 4. Check specific coverage query from dashboard.py
        coverage_query = text("""
            SELECT COUNT(DISTINCT indicator_uuid) 
            FROM gebied_data 
            WHERE waarde IS NOT NULL
        """)
        with_data = db.execute(coverage_query).scalar()
        print(f"Indicators with data (dashboard logic): {with_data}")

        # 5. Check if we have any data at all in gebied_data with values
        check_values = db.execute(text("SELECT COUNT(*) FROM gebied_data WHERE waarde IS NOT NULL")).scalar()
        print(f"Rows in gebied_data with non-null values: {check_values}")

        # 6. Check config_id in v_kompas_hierarchie
        try:
            configs = db.execute(text("SELECT DISTINCT config_id FROM v_kompas_hierarchie")).fetchall()
            print(f"Available config_ids in v_kompas_hierarchie: {[r[0] for r in configs]}")
        except:
             print("Could not check config_ids")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()
        print("--- Check Complete ---")

if __name__ == "__main__":
    check_dashboard_data()
