#!/usr/bin/env python3
"""
Import Meetwaarden/Metingen (Nieuwe Bestanden)
Importeert indicator-meetwaarden uit JSON data bestanden in de 'nieuwebestanden' submap.
"""
import json
import psycopg2
import configparser
import os
import glob

def get_db_connection():
    """Maak database connectie op basis van config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config.read(config_path)
    
    return psycopg2.connect(
        host=config['DATABASE']['host'],
        port=config['DATABASE']['port'],
        dbname=config['DATABASE']['dbname'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password']
    )

def import_data_file(filepath, conn):
    """Import metingen uit één data JSON bestand"""
    filename = os.path.basename(filepath)
    print(f"📊 Verwerken: {filename}")
    
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print(f"⚠️  Onverwacht formaat in {filename}, overgeslagen")
        return 0
    
    with conn.cursor() as cur:
        count = 0
        errors = 0
        for record in data:
            try:
                # Check of dit een data record is (heeft waarde en jaar)
                if 'waarde' not in record or 'jaar' not in record:
                    continue
                
                cur.execute("""
                    INSERT INTO gebied_data 
                        (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
                    VALUES (
                        %(gebied_id)s, %(indicator_uuid)s, %(waarde)s, 
                        %(jaar)s, %(scenario_id)s, %(bron)s
                    )
                    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) 
                    DO UPDATE SET
                        waarde = EXCLUDED.waarde,
                        bron = EXCLUDED.bron
                """, {
                    'gebied_id': record['gebieds_id'],
                    'indicator_uuid': record['indicator_id'],
                    'waarde': record['waarde'],
                    'jaar': record['jaar'],
                    'scenario_id': 'current',
                    'bron': filename
                })
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 3:  # Alleen eerste paar fouten tonen
                    print(f"⚠️  Fout: {e}")
        
        conn.commit()
        print(f"✅ {count} metingen geïmporteerd ({errors} fouten)")
        return count

def is_data_file(filename):
    """Check of een bestand een data bestand is (UUID prefix)"""
    # Data bestanden beginnen met een UUID pattern
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_'
    return bool(re.match(uuid_pattern, filename, re.IGNORECASE))

def main():
    print("🚀 Start Meetwaarden Import (Nieuwe Bestanden)")
    print("=" * 50)
    
    # Path naar de 'nieuwebestanden' submap
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'voorbeeld_gebiedsmonitor', 'nieuwebestanden')
    
    conn = get_db_connection()
    print("✅ Database verbinding gemaakt")
    print(f"📂 Zoeken in map: {base_dir}")
    
    # Vind alle JSON data bestanden (met UUID prefix)
    json_files = glob.glob(os.path.join(base_dir, '*.json'))
    data_files = [f for f in json_files if is_data_file(os.path.basename(f))]
    
    print(f"📁 {len(data_files)} data bestanden gevonden")
    
    total = 0
    for filepath in data_files:
        count = import_data_file(filepath, conn)
        total += count
    
    conn.close()
    print("=" * 50)
    print(f"🎉 Totaal {total} metingen geïmporteerd!")

if __name__ == "__main__":
    main()
