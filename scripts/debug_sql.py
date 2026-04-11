from src.database import get_db
from sqlalchemy import text
import sys

def debug_query():
    print("Testing SQL Query...")
    db = next(get_db())
    
    query = text("""
        SELECT 
            titel_naam,
            COUNT(DISTINCT vkh.indicator_uuid) as total_indicators,
            COUNT(DISTINCT CASE WHEN gd.indicator_uuid IS NOT NULL THEN i.uuid END) as with_data
        FROM v_kompas_hierarchie vkh
        JOIN indicatoren i ON vkh.indicator_uuid = i.uuid
        LEFT JOIN (
            SELECT DISTINCT indicator_uuid 
            FROM gebied_data 
            WHERE waarde IS NOT NULL
        ) gd ON i.uuid = gd.indicator_uuid
        WHERE vkh.config_id = :config_id
        GROUP BY titel_naam
        ORDER BY titel_naam
    """)
    
    try:
        rows = db.execute(query, {"config_id": 1}).fetchall()
        print("✅ Query executed successfully!")
        for row in rows:
            print(row)
    except Exception as e:
        print(f"❌ SQL Execution Failed: {e}")

if __name__ == "__main__":
    debug_query()
