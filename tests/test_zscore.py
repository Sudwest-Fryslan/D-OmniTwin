import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DATABASE_HOST"),
    port=os.getenv("DATABASE_PORT"),
    dbname=os.getenv("DATABASE_NAME"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD")
)
cur = conn.cursor()

# Get indicator UUID for Personenauto's per huishouden
cur.execute("SELECT uuid, naam, eenheid, score_type FROM indicatoren WHERE naam ILIKE '%personenauto%per huishouden%'")
ind = cur.fetchone()
if not ind:
    print("Indicator not found")
    exit()
print(f"Indicator: {ind}")

ind_uuid = ind[0]
gebied_id = "BU19492802" # Franeker Binnenstad (from screenshot 1) but the user's new screenshot says "Franeker It Stiselplak". Let's search for "Franeker It Stiselplak"
cur.execute("SELECT id, naam, gemeente_code, gebiedstype_id FROM gebieden WHERE naam ILIKE '%Stiselplak%'")
gebied = cur.fetchone()
print(f"Gebied: {gebied}")

# Run the query logic purely for this indicator
query = """
    WITH actuele_data AS (
        SELECT DISTINCT ON (gebied_id, indicator_uuid)
            gebied_id, indicator_uuid, waarde, jaar
        FROM gebied_data
        WHERE indicator_uuid = %s
        ORDER BY gebied_id, indicator_uuid, jaar DESC
    ),
    referentie_stats AS (
        SELECT 
            ad.indicator_uuid,
            AVG(ad.waarde) as avg_waarde,
            STDDEV_SAMP(ad.waarde) as std_waarde
        FROM actuele_data ad
        JOIN gebieden g ON ad.gebied_id = g.id
        WHERE g.gebiedstype_id = %s AND g.gemeente_code = %s
        GROUP BY ad.indicator_uuid
    )
    SELECT 
        ad.gebied_id,
        ad.waarde as gebied_waarde,
        ad.jaar as gebied_jaar,
        rs.avg_waarde as referentie_gemiddelde,
        rs.std_waarde as referentie_std,
        CASE 
            WHEN rs.std_waarde > 0 THEN (ad.waarde - rs.avg_waarde) / rs.std_waarde 
            ELSE 0 
        END as z_score
    FROM actuele_data ad
    JOIN referentie_stats rs ON ad.indicator_uuid = rs.indicator_uuid
    WHERE ad.gebied_id = %s
"""

cur.execute(query, (ind_uuid, gebied[3], gebied[2], gebied[0]))
res = cur.fetchone()
print(f"Z-Score Stats: {res}")

# Check overall distribution of years
cur.execute("SELECT jaar, count(*), avg(waarde) FROM actuele_data GROUP BY jaar")
# Note: can't do this directly. Let's do it simply
cur.execute("""
    SELECT jaar, count(*), avg(waarde) 
    FROM (
        SELECT DISTINCT ON (gebied_id) jaar, waarde 
        FROM gebied_data 
        WHERE indicator_uuid = %s 
        ORDER BY gebied_id, jaar DESC
    ) sub 
    GROUP BY jaar
""", (ind_uuid,))
print(f"Years: {cur.fetchall()}")

conn.close()
