#!/usr/bin/env python3
"""
Genereer kompas_hierarchie.csv en indicatoren_seed.json vanuit de bronlijst.
Gebruik: python init_data/scripts/_generate_kompas_seed.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
INPUT = ROOT / "data" / "gebiedsmonitor" / "indicator_testlijst.csv"
KOMPAS_OUT = ROOT / "init_data" / "kompas" / "kompas_hierarchie.csv"
SEED_OUT = ROOT / "init_data" / "indicatoren" / "indicatoren_seed.json"

actuele_indicatoren = []
kompas_rijen = []

with open(INPUT, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        titel = row.get('Title', '').strip()
        thema = row.get('Thema', '').strip()
        onderdeel = row.get('Onderdeel ', '').strip()
        indicator = row.get('Indicator', '').strip()
        actueel = row.get('Indicator actueel', '').strip().upper()
        bron = row.get('Bron', '').strip()
        indicator_swf = row.get('Indicator SWF', '').strip()

        if not titel or titel.lower() == 'test3' or not thema:
            continue

        kompas_rijen.append({
            'Title': titel,
            'Thema': thema,
            'Onderdeel': onderdeel,
            'Indicator': indicator,
            'Indicator actueel': actueel,
            'Bron': bron,
            'Indicator SWF': indicator_swf,
        })

        if actueel == 'J' and indicator_swf:
            actuele_indicatoren.append({
                'naam': indicator_swf,
                'indicator_origineel': indicator,
                'titel': titel,
                'thema': thema,
                'onderdeel': onderdeel,
                'bron': bron,
            })

with open(KOMPAS_OUT, 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['Title', 'Thema', 'Onderdeel', 'Indicator', 'Indicator actueel', 'Bron', 'Indicator SWF']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(kompas_rijen)

with open(SEED_OUT, 'w', encoding='utf-8') as f:
    json.dump(actuele_indicatoren, f, ensure_ascii=False, indent=2)

print(f"kompas_hierarchie.csv: {len(kompas_rijen)} rijen")
print(f"indicatoren_seed.json: {len(actuele_indicatoren)} actuele indicatoren")
for ind in actuele_indicatoren:
    print(f"  [{ind['thema']}] {ind['naam']}")
