import os
import psycopg2
from configparser import ConfigParser

def get_db_config():
    config = ConfigParser()
    config.read('config.ini')
    return config['DATABASE']

def check_indicator_metadata():
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()

        # Count total indicators
        cursor.execute("SELECT COUNT(*) FROM indicatoren;")
        total_indicators = cursor.fetchone()[0]

        # Count indicators with description (omschrijving)
        cursor.execute("SELECT COUNT(*) FROM indicatoren WHERE omschrijving IS NOT NULL AND omschrijving != '';")
        filled_descriptions = cursor.fetchone()[0]

        # Count indicators with source (bron)
        cursor.execute("SELECT COUNT(*) FROM indicatoren WHERE bron IS NOT NULL AND bron != '';")
        filled_sources = cursor.fetchone()[0]

        print(f"Total Indicators: {total_indicators}")
        print(f"Indicators with Description: {filled_descriptions} ({filled_descriptions/total_indicators*100:.1f}%)")
        print(f"Indicators with Source: {filled_sources} ({filled_sources/total_indicators*100:.1f}%)")

        # List some examples of missing descriptions
        if filled_descriptions < total_indicators:
            print("\nExamples of indicators missing description:")
            cursor.execute("SELECT naam FROM indicatoren WHERE omschrijving IS NULL OR omschrijving = '' LIMIT 10;")
            for row in cursor.fetchall():
                print(f"- {row[0]}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_indicator_metadata()
