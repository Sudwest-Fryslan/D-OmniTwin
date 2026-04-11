#!/usr/bin/env python3
"""
Schema v4 Migratie Script
Migreert Kompas schema v3 naar v4 (multi-kompas configuratie systeem)

Gebruik: python scripts/migrate_to_schema_v4.py
"""

import psycopg2
import configparser
import sys
from pathlib import Path

def get_database_connection():
    """Lees database credentials uit config.ini"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    return psycopg2.connect(
        host=config['DATABASE']['host'],
        port=config['DATABASE']['port'],
        dbname=config['DATABASE']['dbname'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password']
    )

def check_v3_tables(conn):
    """Check of v3 tabellen bestaan"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'kompas_%' 
            AND table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
    
    return tables

def run_schema_v4(conn):
    """Voer schema v4 SQL uit"""
    schema_file = Path('data/schema_v4_multi_kompas.sql')
    
    if not schema_file.exists():
        print(f"❌ Schema file niet gevonden: {schema_file}")
        sys.exit(1)
    
    print(f"📄 Lezen schema: {schema_file}")
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    print("🔄 Uitvoeren schema v4 migratie...")
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    
    conn.commit()
    print("✅ Schema v4 succesvol toegepast!")

def verify_migration(conn):
    """Verifieer dat migratie succesvol was"""
    print("\n🔍 Verificatie...")
    
    with conn.cursor() as cur:
        # Check 1: Configuraties
        cur.execute("SELECT id, naam, is_standaard FROM kompas_configuraties ORDER BY id")
        configs = cur.fetchall()
        print(f"\n✓ Configuraties ({len(configs)}):")
        for config_id, naam, is_standaard in configs:
            standaard_marker = "⭐" if is_standaard else "  "
            print(f"  {standaard_marker} [{config_id}] {naam}")
        
        # Check 2: Titels per configuratie
        cur.execute("""
            SELECT kc.naam, COUNT(kt.id) 
            FROM kompas_configuraties kc
            LEFT JOIN kompas_titels kt ON kc.id = kt.config_id
            GROUP BY kc.naam
            ORDER BY kc.naam
        """)
        print(f"\n✓ Titels per configuratie:")
        for config_naam, count in cur.fetchall():
            print(f"  - {config_naam}: {count} titels")
        
        # Check 3: Indicatoren per configuratie
        cur.execute("""
            SELECT kc.naam, COUNT(DISTINCT kim.indicator_uuid) 
            FROM kompas_configuraties kc
            LEFT JOIN kompas_indicator_mapping kim ON kc.id = kim.config_id
            GROUP BY kc.naam
            ORDER BY kc.naam
        """)
        print(f"\n✓ Indicatoren per configuratie:")
        for config_naam, count in cur.fetchall():
            print(f"  - {config_naam}: {count} indicatoren")
        
        # Check 4: Views
        cur.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_name LIKE 'v_kompas_%'
            ORDER BY table_name
        """)
        views = [row[0] for row in cur.fetchall()]
        print(f"\n✓ Views ({len(views)}):")
        for view in views:
            print(f"  - {view}")
        
        # Check 5: Test view query
        cur.execute("""
            SELECT config_naam, COUNT(*) as records
            FROM v_kompas_hierarchie 
            GROUP BY config_naam
        """)
        print(f"\n✓ v_kompas_hierarchie records:")
        for config_naam, count in cur.fetchall():
            print(f"  - {config_naam}: {count} rijen")

def main():
    print("="*60)
    print("Schema v4 Migratie - Multi-Kompas Configuratie Systeem")
    print("="*60)
    
    try:
        # Verbind met database
        print("\n🔌 Verbinden met database...")
        conn = get_database_connection()
        print("✅ Verbinding succesvol!")
        
        # Check bestaande tabellen
        print("\n📋 Controleren bestaande tabellen...")
        v3_tables = check_v3_tables(conn)
        if v3_tables:
            print(f"✓ Gevonden {len(v3_tables)} Kompas v3 tabellen:")
            for table in v3_tables:
                print(f"  - {table}")
        else:
            print("⚠️  Geen bestaande Kompas tabellen gevonden (nieuwe installatie)")
        
        # Vraag bevestiging
        print("\n" + "="*60)
        response = input("Doorgaan met migratie? (ja/nee): ")
        if response.lower() not in ['ja', 'j', 'yes', 'y']:
            print("❌ Migratie geannuleerd")
            sys.exit(0)
        
        # Run migratie
        run_schema_v4(conn)
        
        # Verifieer
        verify_migration(conn)
        
        print("\n" + "="*60)
        print("✅ Migratie voltooid!")
        print("="*60)
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ FOUT: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
