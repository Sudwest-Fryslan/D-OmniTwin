#!/usr/bin/env python3
"""
D-OmniTwin — CBS Alias Analyse
================================
Vergelijk indicator_namen in de CSV met wat er in de DB staat
en toon welke CBS-namen nog NIET vertaald worden door de aliases.

Gebruik:
    python scripts/analyse_cbs_aliases.py
"""

import csv
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 niet gevonden. Activeer je venv.")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.parent
CSV_PAD = ROOT / "init_data" / "fryslan" / "indicatorwaarden_fryslan.csv"

# Huidige aliases uit seed_fryslan.py
CBS_ALIASES = {
    "0 tot 15 jaar": "0-15 jaar",
    "15 tot 25 jaar": "15-25 jaar",
    "25 tot 45 jaar": "25-45 jaar",
    "45 tot 65 jaar": "45-65 jaar",
    "65 jaar of ouder": "65+ jaar",
    "Aantal inwoners": "Inwoners",
    "Afstand tot huisartsenpraktijk": "Huisarts",
    "Eenzaam": "Eenzaamheid",
    "Ernstig eenzaam": "Eenzaamheid",
    "Gemiddeld inkomen per inwoner": "Inkomen per inwoner",
    "Gemiddelde WOZ-waarde van woningen": "Gemiddelde WOZ-waarde",
    "Goed ervaren gezondheid": "Ervaren gezondheid",
    "Hoog risico angststoornis of depressie": "Gezondheid",
    "Huishoudens met een laag inkomen": "Huishoudens met laag inkomen",
    "Huishoudens met kinderen": "Minima kinderen",
    "Huishoudens zonder kinderen": "Minima huish met kinderen",
    "In bezit overige verhuurders": "Particulier huurbezit",
    "In bezit woningcorporatie": "Woningcorporatie bezit",
    "Mantelzorger": "Mantelzorger",
    "Moeite met rondkomen": "Moeite met rondkomen",
    "Netto arbeidsparticipatie": "Participatiewet 5+ jaar",
    "Opleidingsniveau laag": "laag",
    "Overmatige drinker": "Overmatig drinken",
    "Roker": "Roken",
    "Personen met bijstand": "Participatiewet totaal",
    "Voldoet aan beweegrichtlijn": "Bewegen",
    "Vrijwilligerswerk": "Vrijwilliger",
}

# DB indicatoren ophalen
conn = psycopg2.connect(
    host=os.environ.get("DATABASE_HOST", "localhost"),
    port=int(os.environ.get("DATABASE_PORT", 5432)),
    dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
    user=os.environ.get("DATABASE_USER", "omnitwin_user"),
    password=os.environ.get("DATABASE_PASSWORD", ""),
)
cur = conn.cursor()
cur.execute("SELECT naam FROM indicatoren ORDER BY naam")
db_namen = {r[0] for r in cur.fetchall()}
cur.close()
conn.close()

print(f"DB indicatoren: {len(db_namen)}")
print(f"CBS aliases:    {len(CBS_ALIASES)}")
print()

# Lees alle unieke CBS-namen uit de CSV
csv_namen_count: dict[str, int] = {}
with open(CSV_PAD, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        naam = row.get("indicator_naam", "").strip()
        if naam:
            csv_namen_count[naam] = csv_namen_count.get(naam, 0) + 1

print(f"Unieke CBS-namen in CSV: {len(csv_namen_count)}")
print()

# Uitgebreide cache (DB namen + aliases)
indicator_cache = set(db_namen)
alias_targets = {}
for cbs_naam, db_naam in CBS_ALIASES.items():
    if db_naam in db_namen:
        indicator_cache.add(cbs_naam)
        alias_targets[cbs_naam] = db_naam

# Categoriseer CSV namen
direct_match = []  # exact in DB
via_alias = []  # via CBS_ALIASES
niet_gevonden = []  # geen match

for naam, count in sorted(csv_namen_count.items()):
    if naam in db_namen:
        direct_match.append((naam, count))
    elif naam in alias_targets:
        via_alias.append((naam, alias_targets[naam], count))
    else:
        niet_gevonden.append((naam, count))

print(f"{'=' * 60}")
print(f"✅ DIRECT MATCH in DB ({len(direct_match)} namen, {sum(c for _, c in direct_match):,} rijen):")
for naam, count in direct_match:
    print(f"   {count:5d}x  {naam}")

print()
print(f"{'=' * 60}")
print(f"🔁 VIA ALIAS ({len(via_alias)} namen, {sum(c for _, _, c in via_alias):,} rijen):")
for cbs, db, count in via_alias:
    print(f"   {count:5d}x  '{cbs}'  →  '{db}'")

print()
print(f"{'=' * 60}")
print(f"❌ NIET GEVONDEN ({len(niet_gevonden)} namen, {sum(c for _, c in niet_gevonden):,} rijen):")
for naam, count in niet_gevonden:
    print(f"   {count:5d}x  '{naam}'")

print()
print(f"{'=' * 60}")
print(f"TOTAAL RIJEN IN CSV:   {sum(csv_namen_count.values()):,}")
print(f"  Direct:              {sum(c for _, c in direct_match):,}")
print(f"  Via alias:           {sum(c for _, _, c in via_alias):,}")
print(f"  Onbekend/overgeslagen: {sum(c for _, c in niet_gevonden):,}")
