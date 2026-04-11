"""
Verificatie script voor gemeente codes tegen Excel referentie
"""
import os
import sys
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Excel data voor Fryslân (met voorloopnullen)
EXCEL_FRYSLAN = {
    '0059': 'Achtkarspelen',
    '0060': 'Ameland', 
    '1891': 'Dantumadiel',
    '1940': 'De Fryske Marren',
    '0072': 'Harlingen',
    '0074': 'Heerenveen',
    '0080': 'Leeuwarden',
    '1970': 'Noardeast-Fryslân',
    '0085': 'Ooststellingwerf',
    '0086': 'Opsterland',
    '0088': 'Schiermonnikoog',
    '0090': 'Smallingerland',
    '1900': 'Súdwest-Fryslân',
    '0093': 'Terschelling',
    '0737': 'Tytsjerksteradiel',
    '0096': 'Vlieland',
    '1949': 'Waadhoeke',
    '0098': 'Weststellingwerf'
}

def get_conn():
    """Create database connection from .env"""
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=os.getenv('DATABASE_PORT', '5432'),
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', ''),
        sslmode=os.getenv('DATABASE_SSLMODE', 'prefer')
    )

def main():
    # Connect to database
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all gemeente codes from database
    cur.execute('''
        SELECT DISTINCT code, naam
        FROM gemeenten
        ORDER BY code
    ''')
    
    db_gemeenten = {row[0]: row[1] for row in cur.fetchall()}
    
    print('=== Database Gemeente Codes (alle) ===')
    for code, naam in sorted(db_gemeenten.items()):
        print(f'{code}: {naam}')
    
    print('\n' + '='*60)
    print('=== Vergelijking Fryslân met Excel (2025) ===')
    print('='*60)
    
    missing = []
    naam_mismatch = []
    correct = []
    
    for excel_code, excel_naam in sorted(EXCEL_FRYSLAN.items()):
        if excel_code in db_gemeenten:
            if db_gemeenten[excel_code] == excel_naam:
                correct.append(excel_code)
                print(f'✓ {excel_code}: {excel_naam}')
            else:
                naam_mismatch.append((excel_code, excel_naam, db_gemeenten[excel_code]))
                print(f'⚠ {excel_code}: Excel="{excel_naam}" | DB="{db_gemeenten[excel_code]}"')
        else:
            missing.append((excel_code, excel_naam))
            print(f'✗ {excel_code}: {excel_naam} - ONTBREEKT IN DATABASE')
    
    print('\n' + '='*60)
    print('=== SAMENVATTING ===')
    print(f'✓ Correct: {len(correct)}/{len(EXCEL_FRYSLAN)}')
    print(f'⚠ Naam verschil: {len(naam_mismatch)}')
    print(f'✗ Ontbreekt: {len(missing)}')
    
    if naam_mismatch:
        print('\nGemeenten met naam verschillen:')
        for code, excel, db in naam_mismatch:
            print(f'  {code}: "{excel}" ≠ "{db}"')
    
    if missing:
        print('\nOntbrekende gemeenten:')
        for code, naam in missing:
            print(f'  {code}: {naam}')
    
    # Check specific problematic codes
    print('\n' + '='*60)
    print('=== SPECIFIEKE CHECKS ===')
    for code in ['1940', '0090']:
        naam = EXCEL_FRYSLAN[code]
        if code in db_gemeenten:
            print(f'{code} ({naam}): ✓ AANWEZIG in database')
            
            # Count records with this code
            cur.execute('SELECT COUNT(*) FROM gemeenten WHERE code = %s', (code,))
            count = cur.fetchone()[0]
            print(f'  → {count} records in gemeenten tabel')
            
            # Check if used in CBS data
            cur.execute('''
                SELECT COUNT(DISTINCT indicator_code) 
                FROM cbs_data 
                WHERE gemeente_code = %s
            ''', (code,))
            indicator_count = cur.fetchone()[0]
            print(f'  → {indicator_count} verschillende indicatoren met data')
        else:
            print(f'{code} ({naam}): ✗ ONTBREEKT')
    
    conn.close()

if __name__ == '__main__':
    main()
