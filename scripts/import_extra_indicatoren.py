#!/usr/bin/env python3
"""
Import Extra Indicatoren
Importeert indicatoren uit flat JSON lijsten (DMART export formaat).
"""
import json
import psycopg2
import configparser
import os
import glob
from datetime import datetime

def get_db_connection():
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

def parse_date(date_str):
    """Converteer YYYYMMDDHHMMSS string naar ISO formaat"""
    if not date_str:
        return None
    try:
        # Formaat voorbeeld: 20250114000000
        dt = datetime.strptime(str(date_str), "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def import_indicators_from_file(filepath, conn):
    print(f"📊 Verwerken: {os.path.basename(filepath)}")
    
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        print("⚠️  Verwachtte een lijst, bestand overgeslagen")
        return 0
        
    count = 0
    with conn.cursor() as cur:
        for item in data:
            try:
                uuid = item.get('indicator_id')
                if not uuid:
                    continue

                cur.execute("""
                    INSERT INTO indicatoren 
                        (uuid, naam, omschrijving, status, begingeldigheid, eindgeldigheid)
                    VALUES (
                        %(uuid)s, %(naam)s, %(omschrijving)s, %(status)s, 
                        %(begin)s, %(eind)s
                    )
                    ON CONFLICT (uuid) DO UPDATE SET
                        naam = EXCLUDED.naam,
                        omschrijving = EXCLUDED.omschrijving,
                        status = EXCLUDED.status,
                        begingeldigheid = EXCLUDED.begingeldigheid,
                        eindgeldigheid = EXCLUDED.eindgeldigheid
                """, {
                    'uuid': uuid,
                    'naam': item.get('naam'),
                    'omschrijving': item.get('omschrijving'),
                    'status': item.get('status', 'O'),
                    'begin': parse_date(item.get('date_from')),
                    'eind': parse_date(item.get('date_to'))
                })
                count += 1
            except Exception as e:
                print(f"⚠️  Fout bij indicator {item.get('naam', '?')}: {e}")
                
        conn.commit()
    print(f"✅ {count} indicatoren geïmporteerd/geupdate")
    return count

def main():
    print("🚀 Start Extra Indicatoren Import")
    print("=" * 50)
    
    conn = get_db_connection()
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'voorbeeld_gebiedsmonitor')
    
    # Specifieke bestanden scannen
    files = [
        'CBS_BUURTEN_BBK_DMART_V_INDICATOREN.json',
        'CBS_BUURTEN_DMART_V_INDICATOREN.json'
    ]
    
    total = 0
    for filename in files:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            total += import_indicators_from_file(filepath, conn)
        else:
            print(f"⚠️  Bestand niet gevonden: {filename}")
            
    conn.close()
    print("=" * 50)
    print(f"🎉 Totaal {total} indicatoren verwerkt!")

if __name__ == "__main__":
    main()
