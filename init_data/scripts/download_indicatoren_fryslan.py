#!/usr/bin/env python3
"""
Haal CBS open data indicatorwaarden op voor alle gemeenten in de provincie Fryslân.
Schrijft naar: init_data/fryslan/indicatorwaarden_fryslan.csv

Gebruik:
    python init_data/scripts/download_indicatoren_fryslan.py

Vereisten: pip install requests psycopg2-binary

Databronnen (CBS OData, open data, CC BY):
  - KERNCIJFERS_WIJKEN_EN_BUURTEN_2023: kerncijfers buurten
  - GEZONDHEID_PER_WIJK_EN_BUURT_RIVM: gezondheidsmonitor RIVM
  - MISDRIJVEN_PER_WIJK_EN_BUURT: veiligheidscijfers
  - GEREGISTREERDE_OVERLAST_PER_BUURT: overlastmeldingen
  - NABIJHEID_VOORZIENINGEN_BUURT_2022: afstandsindicatoren (CBS)
"""
import csv
import json
import time
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent.parent
OUTPUT = ROOT / "init_data" / "fryslan" / "indicatorwaarden_fryslan.csv"
MAPPING_FILE = ROOT / "ETL" / "CBS" / "cbs_mapping_v3.json"

# Alle Friese gemeentecodes (4-cijferig, zonder GM prefix)
FRIESE_GM_CODES = [
    '0059', '0060', '1891', '1921', '0072', '0074',
    '0080', '1970', '0085', '0086', '0088', '0140',
    '1900', '0093', '0737', '0096', '1949', '0098'
]

CBS_BASE = "https://opendata.cbs.nl/ODataApi/odata"

# Dataset configuratie: (dataset_id, kolom_filter, indicator_naam_mapping, jaar)
DATASETS = [
    {
        "id": "85039NED",   # Kerncijfers wijken en buurten 2023
        "naam": "Kerncijfers wijken en buurten 2023",
        "jaar": 2023,
        "kolommen": {
            "Koopwoningen_P": "Koopwoningen",
            "Woningcorporaties_P": "In bezit woningcorporatie",
            "ParticuliereVerhuur_P": "In bezit overige verhuurders",
            "AfstandTotHuisartsenpraktijk_A": "Afstand tot huisartsenpraktijk",
            "AfstandTotGroteSupermarkt_A": "Afstand tot grote supermarkt",
            "AfstandTotKinderdagverblijf_A": "Afstand tot kinderdagverblijf",
            "k_0Tot15Jaar_P": "0 tot 15 jaar",
            "k_65JaarOfOuder_P": "65 jaar of ouder",
            "HuishoudensZonderKinderen_P": "Huishoudens zonder kinderen",
            "HuishoudensMetKinderen_P": "Huishoudens met kinderen",
            "BuitenEuropa_P": "Buiten Europa",
            "GemiddeldeInkomenPerInwoner_P": "Gemiddeld inkomen per inwoner",
            "OpleidingsniveauHoog_P": "Opleidingsniveau hoog",
            "OpleidingsniveauMiddelbaar_P": "Opleidingsniveau middelbaar",
            "OpleidingsniveauLaag_P": "Opleidingsniveau laag",
        },
        "regio_filter_col": "Codering_3",
        "regio_prefix": "BU",
    },
    {
        "id": "85039NED",   # Nabijheid voorzieningen (zit ook in kerncijfers)
        "naam": "Kerncijfers wijken en buurten 2023 (nabijheid)",
        "jaar": 2023,
        "kolommen": {
            "AfstandTotZwembad_A": "Afstand tot zwembad",
            "AfstandTotBibliotheek_A": "Afstand tot bibliotheek",
            "AfstandTotRestaurant_A": "Afstand tot restaurant",
            "AfstandTotCafe_A": "Afstand tot café e.d.",
            "AfstandTotApotheek_A": "Afstand tot apotheek",
        },
        "regio_filter_col": "Codering_3",
        "regio_prefix": "BU",
    },
]

# Kolommapping voor gezondheidsdata (RIVM via dataderden)
RIVM_DATASETS = [
    {
        "id": "50150NED",  # Gezondheidsmonitor GGD 2022
        "naam": "Gezondheid per wijk en buurt RIVM 2022",
        "jaar": 2022,
        "base": "https://dataderden.cbs.nl/ODataApi/odata",
        "kolommen": {
            "RokerTabak_P": "Roker",
            "Overgewicht_P": "Overgewicht",
            "Eenzaam_P": "Eenzaam",
            "MoeiteMetRondkomen_P": "Moeite met rondkomen",
            "OvermatigDrinken_P": "Overmatige drinker",
            "VoldoetAanBeweegrichtlijn_P": "Voldoet aan beweegrichtlijn",
            "ErnstigBeperktVanwegeGezondheid_P": "Ernstig beperkt vanwege gezondheid",
            "BeperktVanwegeGezondheid_P": "Beperkt vanwege gezondheid",
            "Vrijwilligerswerk_P": "Vrijwilligerswerk",
            "Mantelzorger_P": "Mantelzorger",
        },
        "regio_filter_col": "Codering_3",
        "regio_prefix": "BU",
    },
]


def get_buurt_codes_voor_gemeenten(gm_codes):
    """
    Geef een set buurtcodes terug voor de gegeven Friese gemeenten.
    Buurtcodes starten met BU + gemeentecode (bv. BU00590001).
    """
    prefixes = [f"BU{code}" for code in gm_codes]
    return prefixes


def fetch_dataset_page(base_url, dataset_id, kolommen, regio_filter_col, regio_prefixes, 
                        select_cols, skip=0, top=10000):
    """Haal 1 pagina op van CBS OData."""
    # Filter op buurten van Friese gemeenten via startswith emulatie
    # CBS OData ondersteunt startswith() in $filter
    filter_parts = [f"startswith({regio_filter_col}, '{pfx}')" for pfx in regio_prefixes]
    filter_str = " or ".join(filter_parts)

    url = f"{base_url}/{dataset_id}/TypedDataSet"
    params = {
        "$format": "json",
        "$top": top,
        "$skip": skip,
        "$select": ",".join([regio_filter_col] + select_cols),
        "$filter": filter_str,
    }

    resp = requests.get(url, params=params, timeout=120)
    if resp.status_code != 200:
        print(f"     HTTP {resp.status_code}: {resp.text[:200]}")
        return []

    data = resp.json()
    return data.get("value", [])


def download_dataset(ds_config, alle_rijen):
    """Download een dataset en voeg toe aan alle_rijen."""
    base = ds_config.get("base", CBS_BASE)
    dataset_id = ds_config["id"]
    naam = ds_config["naam"]
    jaar = ds_config["jaar"]
    kolommen = ds_config["kolommen"]
    regio_filter_col = ds_config["regio_filter_col"]
    regio_prefix = ds_config["regio_prefix"]

    print(f"\n  📊 {naam} ({dataset_id})")

    # Genereer buurtprefixen
    prefixes = [f"{regio_prefix}{gm}" for gm in FRIESE_GM_CODES]
    select_cols = list(kolommen.keys())

    skip = 0
    pagina = 1
    totaal = 0

    while True:
        print(f"     Pagina {pagina}...", end=" ", flush=True)
        records = fetch_dataset_page(base, dataset_id, kolommen, regio_filter_col,
                                      prefixes, select_cols, skip=skip)
        if not records:
            print("klaar")
            break

        for record in records:
            buurt_code = record.get(regio_filter_col, "").strip()
            if not buurt_code:
                continue

            for col_naam, indicator_naam in kolommen.items():
                waarde = record.get(col_naam)
                if waarde is None:
                    continue
                try:
                    waarde_float = float(waarde)
                except (ValueError, TypeError):
                    continue

                alle_rijen.append({
                    "buurt_id": buurt_code,
                    "indicator_naam": indicator_naam,
                    "waarde": waarde_float,
                    "jaar": jaar,
                    "bron": naam,
                })

        print(f"{len(records)} records → totaal buurt×indicator rijen: {len(alle_rijen)}")
        totaal += len(records)

        if len(records) < 10000:
            break
        skip += len(records)
        pagina += 1
        time.sleep(0.3)

    return totaal


def main():
    print("=" * 60)
    print("Download CBS Indicatorwaarden — Fryslân")
    print("=" * 60)
    print(f"Gemeenten: {len(FRIESE_GM_CODES)} Friese gemeenten")
    print(f"Output: {OUTPUT}")
    print()

    alle_rijen = []

    # CBS Kerncijfers
    for ds in DATASETS:
        download_dataset(ds, alle_rijen)
        time.sleep(1)

    # RIVM Gezondheid (dataderden)
    print("\n  ℹ️  RIVM data via dataderden.cbs.nl (kan langzamer zijn)")
    for ds in RIVM_DATASETS:
        try:
            download_dataset(ds, alle_rijen)
        except Exception as e:
            print(f"  ⚠️  RIVM dataset mislukt: {e}")
        time.sleep(1)

    # Schrijf CSV
    print(f"\n  💾 Schrijven naar {OUTPUT}...")
    with open(OUTPUT, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ["buurt_id", "indicator_naam", "waarde", "jaar", "bron"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(alle_rijen)

    print(f"\n✅ Klaar!")
    print(f"   {len(alle_rijen)} rijen opgeslagen")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"   Bestandsgrootte: {size_kb:.0f} KB")

    # Overzicht indicatoren
    unique_indicators = sorted(set(r["indicator_naam"] for r in alle_rijen))
    print(f"\n📊 Indicatoren ({len(unique_indicators)}):")
    for ind in unique_indicators:
        count = sum(1 for r in alle_rijen if r["indicator_naam"] == ind)
        print(f"   • {ind}: {count} buurten")


if __name__ == "__main__":
    main()
