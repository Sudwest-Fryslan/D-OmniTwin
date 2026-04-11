#!/usr/bin/env python3
"""
Import Gebiedsmonitor Config Data
Importeert indicatoren en relaties uit config JSON naar database.
"""
import json
import psycopg2
from psycopg2.extras import execute_values
import configparser
import os

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

def import_indicatoren(config_data, conn):
    """Import indicatoren uit config JSON"""
    indicatoren = config_data.get('indicatoren', [])
    
    if not indicatoren:
        print("⚠️  Geen indicatoren gevonden in config")
        return
    
    with conn.cursor() as cur:
        count = 0
        for ind in indicatoren:
            cur.execute("""
                INSERT INTO indicatoren 
                    (uuid, naam, omschrijving, status, begingeldigheid, eindgeldigheid)
                VALUES (
                    %(uuid)s, %(naam)s, %(omschrijving)s, %(status)s, 
                    %(begingeldigheid)s, %(eindgeldigheid)s
                )
                ON CONFLICT (uuid) DO UPDATE SET
                    naam = EXCLUDED.naam,
                    omschrijving = EXCLUDED.omschrijving,
                    status = EXCLUDED.status,
                    begingeldigheid = EXCLUDED.begingeldigheid,
                    eindgeldigheid = EXCLUDED.eindgeldigheid
            """, {
                'uuid': ind['id'],
                'naam': ind['naam'],
                'omschrijving': ind.get('omschrijving'),
                'status': ind.get('status', 'O'),
                'begingeldigheid': ind.get('begingeldigheid'),
                'eindgeldigheid': ind.get('eindgeldigheid')
            })
            count += 1
        
        conn.commit()
        print(f"✅ {count} indicatoren geïmporteerd")

def import_indicator_gebiedstype_relaties(config_data, conn):
    """Import indicator-gebiedstype relaties"""
    relaties = config_data.get('indicator_gebiedstype_relaties', [])
    
    if not relaties:
        print("⚠️  Geen relaties gevonden in config")
        return
    
    with conn.cursor() as cur:
        count = 0
        for rel in relaties:
            try:
                cur.execute("""
                    INSERT INTO indicator_gebiedstype_relaties 
                        (indicator_uuid, gebiedstype_id)
                    VALUES (%(indicator_id)s, %(gebiedstype_id)s)
                    ON CONFLICT (indicator_uuid, gebiedstype_id) DO NOTHING
                """, {
                    'indicator_id': rel['indicator_id'],
                    'gebiedstype_id': rel['gebiedstype_id']
                })
                count += 1
            except Exception as e:
                print(f"⚠️  Relatie overgeslagen: {e}")
        
        conn.commit()
        print(f"✅ {count} relaties geïmporteerd")

def main():
    print("🚀 Start Gebiedsmonitor Config Import")
    print("=" * 50)
    
    # Connectie maken
    conn = get_db_connection()
    print("✅ Database verbinding gemaakt")
    
    # Config laden
    config_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'data', 'voorbeeld_gebiedsmonitor', 
        'new_config_gebiedsmonitor_ind-geb-rel.json'
    )
    
    with open(config_path, encoding='utf-8') as f:
        config_data = json.load(f)
    print(f"✅ Config geladen: {os.path.basename(config_path)}")
    
    # Import uitvoeren
    import_indicatoren(config_data, conn)
    import_indicator_gebiedstype_relaties(config_data, conn)
    
    conn.close()
    print("=" * 50)
    print("🎉 Config import voltooid!")

if __name__ == '__main__':
    main()
