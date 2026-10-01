#!/usr/bin/env python3
"""
Haal CBS open data indicatorwaarden op voor alle gemeenten in de provincie Fryslân.
Schrijft naar: init_data/fryslan/indicatorwaarden_fryslan.csv

Gebruik:
    python init_data/scripts/download_indicatoren_fryslan.py

Vereisten: pip install requests

Databronnen (CBS OData, open data, CC BY):
  - 85039NED: Kerncijfers wijken en buurten 2021 (tot #119 abusievelijk als 2023 gelabeld)
  - 50150NED: Gezondheidsmonitor RIVM via dataderden.cbs.nl (2012-2024)
"""
import csv
import time
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent.parent
OUTPUT = ROOT / "init_data" / "fryslan" / "indicatorwaarden_fryslan.csv"

# Alle Friese gemeentecodes (4-cijferig, zonder GM prefix)
FRIESE_GM_CODES = [
    '0059', '0060', '1891', '1940', '0072', '0074',
    '0080', '1970', '0085', '0086', '0088', '0090',
    '1900', '0093', '0737', '0096', '1949', '0098'
]

# Prefixen voor client-side filtering
FRIESE_BU_PREFIXES = [f"BU{gm}" for gm in FRIESE_GM_CODES]

# CBS ODataFeed endpoint (ODataApi is deprecated)
CBS_BASE = "https://opendata.cbs.nl/ODataFeed/odata"

# ────────────────────────────────────────────────────────────
# Dataset configuratie
# ────────────────────────────────────────────────────────────
# Kolomnamen in ODataFeed hebben een numeriek suffix (_N).
# We mappen deze naar leesbare indicatornamen.

DATASETS = [
    {
        "id": "85039NED",   # Kerncijfers wijken en buurten 2021 (TableInfos: Period 2021, #119)
        "naam": "Kerncijfers wijken en buurten 2021",
        "jaar": 2021,
        "base": CBS_BASE,
        "kolommen": {
            # Namen exact gelijk aan indicatoren tabel (DB-sanering 2026-04-20)
            "Koopwoningen_40": "Koopwoningen",
            "InBezitWoningcorporatie_42": "Woningcorporatie bezit",
            "InBezitOverigeVerhuurders_43": "Particulier huurbezit",
            "AfstandTotHuisartsenpraktijk_106": "Huisarts",
            "AfstandTotGroteSupermarkt_107": "Afstand tot grote supermarkt",
            "AfstandTotKinderdagverblijf_108": "Afstand tot kinderdagverblijf",
            "AfstandTotSchool_109": "Afstand tot school",
            "k_0Tot15Jaar_8": "0-15 jaar",
            "k_65JaarOfOuder_12": "65+ jaar",
            "HuishoudensZonderKinderen_30": "Huishoudens zonder kind",
            "HuishoudensMetKinderen_31": "Huishoudens met kind",
            "GemiddeldInkomenPerInwoner_72": "Inkomen per inwoner",
            "OpleidingsniveauHoog_66": "Opleidingsniveau hoog",
            "OpleidingsniveauMiddelbaar_65": "Opleidingsniveau middelbaar",
            "OpleidingsniveauLaag_64": "Opleidingsniveau laag",
            "GemiddeldeWOZWaardeVanWoningen_35": "Gemiddelde WOZ-waarde",
            "AantalInwoners_5": "Inwoners",
            "Bevolkingsdichtheid_33": "Bevolkingsdichtheid",
            "Woningvoorraad_34": "Woningvoorraad",
            "Nettoarbeidsparticipatie_67": "Netto arbeidsparticipatie",
            "HuishoudensMetEenLaagInkomen_78": "Huishoudens met laag inkomen",
            "PersonenPerSoortUitkeringBijstand_83": "Personen met bijstand",
        },
        "regio_filter_col": "Codering_3",
        "server_filter": True,  # CBS ondersteunt server-side filtering
    },
]

# RIVM Gezondheidsmonitor (dataderden.cbs.nl)
# Deze dataset heeft dimensies: Leeftijd, Marges, Perioden
# We willen: Leeftijd=20300 (18+), Marges=MW00000 (waarde), alle Perioden
RIVM_DATASETS = [
    {
        "id": "50150NED",
        "naam": "Gezondheidsmonitor RIVM",
        "base": "https://dataderden.cbs.nl/ODataFeed/odata",
        "regio_filter_col": "Codering_3",
        "server_filter": False,  # dataderden ondersteunt GEEN server-side $filter op Codering_3
        # Dimensie-filters: alleen totaal leeftijd + alleen waarde (geen betrouwbaarheidsinterval)
        "dimensie_filters": {
            "Leeftijd": "20300",      # 18 jaar of ouder (= totaal)
            "Marges": "MW00000",      # Waarde (geen onder/bovengrens)
        },
        # Perioden kolom → jaar extractie (2022JJ00 → 2022)
        "periode_col": "Perioden",
        "kolommen": {
            # Namen exact gelijk aan indicatoren tabel (DB-sanering 2026-04-20)
            "Overgewicht_33": "Overgewicht",
            "Eenzaam_25": "Eenzaamheid",
            "MoeiteMetRondkomen_32": "Moeite met rondkomen",
            "OvermatigDrinken_37": "Overmatig drinken",
            "VoldoetAanDeBeweegrichtlijn_40": "Bewegen",
            "Vrijwilligerswerk_31": "Vrijwilliger",
            "Mantelzorger_30": "Mantelzorger",
            "RooktTabak_35": "Roken",
            "GoedErvarenGezondheid_4": "Ervaren gezondheid",
            "HoogRisicoAngststoornisOfDepressie_14": "Hoog risico angststoornis of depressie",
        },
    },
]


def is_friese_buurt(buurt_id):
    """Check of een buurtcode bij een Friese gemeente hoort."""
    return any(buurt_id.startswith(pfx) for pfx in FRIESE_BU_PREFIXES)


def fetch_page(base_url, dataset_id, select_cols, regio_filter_col,
               extra_select=None, extra_filter=None, skip=0, top=10000):
    """Haal 1 pagina op van CBS/RIVM ODataFeed."""
    url = f"{base_url}/{dataset_id}/TypedDataSet"

    all_select = [regio_filter_col] + select_cols
    if extra_select:
        all_select = extra_select + all_select

    params = {
        "$format": "json",
        "$top": top,
        "$skip": skip,
        "$select": ",".join(all_select),
    }
    if extra_filter:
        params["$filter"] = extra_filter

    resp = requests.get(url, params=params, timeout=120)
    if resp.status_code != 200:
        print(f"     HTTP {resp.status_code}: {resp.text[:200]}")
        return []

    data = resp.json()
    return data.get("value", [])


def download_cbs_dataset(ds_config, alle_rijen):
    """Download een CBS dataset met server-side filtering."""
    base = ds_config["base"]
    dataset_id = ds_config["id"]
    naam = ds_config["naam"]
    jaar = ds_config["jaar"]
    kolommen = ds_config["kolommen"]
    regio_filter_col = ds_config["regio_filter_col"]

    print(f"\n  📊 {naam} ({dataset_id})")

    # Server-side filter op Friese buurten
    filter_parts = [f"startswith({regio_filter_col}, '{pfx}')" for pfx in FRIESE_BU_PREFIXES]
    filter_str = " or ".join(filter_parts)

    select_cols = list(kolommen.keys())
    skip = 0
    pagina = 1

    while True:
        print(f"     Pagina {pagina}...", end=" ", flush=True)
        records = fetch_page(base, dataset_id, select_cols, regio_filter_col,
                             extra_filter=filter_str, skip=skip)
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

        print(f"{len(records)} records → totaal rijen: {len(alle_rijen)}")

        if len(records) < 10000:
            break
        skip += len(records)
        pagina += 1
        time.sleep(0.3)


def download_rivm_dataset(ds_config, alle_rijen):
    """
    Download een RIVM dataset met dimensie-filtering en client-side buurtfiltering.
    
    RIVM data via dataderden.cbs.nl ondersteunt geen server-side $filter op Codering_3.
    We halen alle buurten op, maar filteren op:
    - Leeftijd = 20300 (18 jaar of ouder = totaal)
    - Marges = MW00000 (waarde, geen betrouwbaarheidsinterval)
    - Alle Perioden (voor trendlines)
    En filteren dan client-side op Friese gemeenten.
    """
    base = ds_config["base"]
    dataset_id = ds_config["id"]
    naam = ds_config["naam"]
    kolommen = ds_config["kolommen"]
    regio_filter_col = ds_config["regio_filter_col"]
    dimensie_filters = ds_config.get("dimensie_filters", {})
    periode_col = ds_config.get("periode_col", "Perioden")

    print(f"\n  📊 {naam} ({dataset_id})")
    print(f"     Dimensie-filters: {dimensie_filters}")
    print(f"     ⚠️  Geen server-side regio filter → client-side filtering op Fryslân")

    # Server-side filter op dimensies (Leeftijd + Marges)
    dim_filter_parts = [f"{dim} eq '{val}'" for dim, val in dimensie_filters.items()]
    dim_filter = " and ".join(dim_filter_parts) if dim_filter_parts else None

    select_cols = list(kolommen.keys())
    extra_select = [periode_col] + list(dimensie_filters.keys())

    skip = 0
    pagina = 1
    friese_count = 0
    overgeslagen = 0

    while True:
        print(f"     Pagina {pagina}...", end=" ", flush=True)
        records = fetch_page(base, dataset_id, select_cols, regio_filter_col,
                             extra_select=extra_select, extra_filter=dim_filter,
                             skip=skip)
        if not records:
            print("klaar")
            break

        for record in records:
            buurt_code = record.get(regio_filter_col, "").strip()

            # Client-side filter: alleen Friese buurten
            if not buurt_code or not is_friese_buurt(buurt_code):
                overgeslagen += 1
                continue

            # Jaar uit perioden halen (bijv. "2022JJ00" → 2022)
            periode = record.get(periode_col, "")
            try:
                jaar = int(periode[:4])
            except (ValueError, TypeError):
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
                    "bron": f"{naam} {jaar}",
                })
                friese_count += 1

        print(f"{len(records)} records (Fryslân: +{friese_count}) → totaal rijen: {len(alle_rijen)}")

        if len(records) < 10000:
            break
        skip += len(records)
        pagina += 1
        time.sleep(0.3)

    print(f"     ✅ {friese_count} Friese metingen | {overgeslagen} niet-Fries overgeslagen")


def main():
    print("=" * 60)
    print("Download CBS Indicatorwaarden — Fryslân")
    print("=" * 60)
    print(f"Gemeenten: {len(FRIESE_GM_CODES)} Friese gemeenten")
    print(f"Output: {OUTPUT}")
    print()

    alle_rijen = []

    # CBS Kerncijfers (server-side filtering)
    for ds in DATASETS:
        download_cbs_dataset(ds, alle_rijen)
        time.sleep(1)

    # RIVM Gezondheid (client-side filtering, met perioden voor trendlines)
    print("\n  ℹ️  RIVM data via dataderden.cbs.nl (client-side filtering)")
    for ds in RIVM_DATASETS:
        try:
            download_rivm_dataset(ds, alle_rijen)
        except Exception as e:
            print(f"  ⚠️  RIVM dataset mislukt: {e}")
        time.sleep(1)

    # Schrijf CSV
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
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
    import collections
    unique_indicators = sorted(set(r["indicator_naam"] for r in alle_rijen))
    print(f"\n📊 Indicatoren ({len(unique_indicators)}):")
    for ind in unique_indicators:
        jaren = sorted(set(r["jaar"] for r in alle_rijen if r["indicator_naam"] == ind))
        count = sum(1 for r in alle_rijen if r["indicator_naam"] == ind)
        print(f"   • {ind}: {count} metingen (jaren: {jaren})")


if __name__ == "__main__":
    main()
