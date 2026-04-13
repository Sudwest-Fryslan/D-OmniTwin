# Voorstel: Implementatieplan Initiatie Dataset & Documentatie

**Status:** Concept (Wacht op goedkeuring)  
**Datum:** 13 april 2026  

## 1. Doel
Een nieuwe gebruiker die de repository downloadt moet binnen **< 30 minuten** een werkende instantie kunnen draaien mét echte data. Momenteel ontbreekt een starter dataset, waardoor de applicatie na een schone installatie leeg blijft.

## 2. Analyse van de huidige Gaps
De `data/` map is momenteel volledig uitgesloten in `.gitignore`. Dit is correct voor grote datasets, maar het betekent ook dat:
- De database schema's niet in git staan.
- De Kompas-hiërarchie configuratie ontbreekt.
- Er geen voorbeeld geometrie of indicatorwaarden beschikbaar zijn.

## 3. Voorstel: De `init_data/` map
We introduceren een nieuwe map `init_data/` die **wel** in git wordt opgenomen (via een uitzondering in `.gitignore`).

### Structuur
```
init_data/
├── README.md                        # Beschrijving van alle bestanden + licenties
├── schema/
│   └── schema_latest.sql            # De basis database structuur
├── kompas/
│   └── kompas_hierarchie.csv        # Opgeschoonde versie van de indicatorlijst
├── indicatoren/
│   └── indicatoren_seed.json        # Metadata van alle actuele indicatoren
├── sudwestfryslan/
│   ├── README.md                    # Bronvermelding CBS open data
│   ├── buurten_swf.geojson          # ~120 buurten van Súdwest-Fryslân (WGS84)
│   └── indicatorwaarden_swf.csv     # Echte CBS open data voor deze buurten
└── scripts/
    ├── init_database.sh             # Master script voor database inrichting
    └── seed_swf.py                  # Python script voor data import
```

## 4. Voorgestelde Wijzigingen

### A. Documentatie
- **`GETTING_STARTED.md`**: Een nieuwe, heldere gids die een gebruiker van 'git clone' naar een gevulde kaart leidt.
- **`README.md`**: Vereenvoudigen van de "Snel Opstarten" sectie door te verwijzen naar de nieuwe gids.

### B. Gegevensbronnen (Automatisering)
- **Geometrie**: Wordt gedownload via de PDOK WFS (CBS Gebiedsindelingen 2024). Dit garandeert de meest actuele en officieel gelicentieerde data (CC BY).
- **Indicatoren**: Worden opgehaald via de CBS OData API voor de geselecteerde pilot-gemeente (Súdwest-Fryslân).

### C. Infrastructuur
- Aanpassing van `.gitignore` om `init_data/` toe te staan.
- Ontwikkeling van een `init_database.sh` script dat alle stappen (schema, indicatoren, geometrie, data) in de juiste volgorde uitvoert.

## 5. Te Beantwoorden Vragen (User Review Required)

> [!IMPORTANT]
> **Selectie indicatoren:** Voorstel is om te starten met de ~20 indicatoren die reeds in onze CBS mapping staan. Is dit voldoende voor een 'wow' effect bij de eerste start?

> [!IMPORTANT]
> **Formaat Geometrie:** CBS buurten SWF is ~3MB als GeoJSON. Akkoord om dit direct in de repo te zetten, of liever als gecomprimeerd bestand?

> [!NOTE]
> **Meerdere Gemeenten:** Is Súdwest-Fryslân alleen voldoende als start, of wil je direct Leeuwarden/Tytsjerksteradiel erbij hebben om de benchmark-functies te kunnen tonen?

## 6. Verificatie Plan
- **Schone Installatie Test**: Een installatie uitvoeren in een container om te verifiëren of alle paden en scripts werken zonder lokale restanten.
- **Functionaliteit**: Controleren of het Kompas, de Kaart en de AI Assistent direct resultaat geven op basis van de ingeladen data.
