# D-OmniTwin — Sample Dataset (Súdwest-Fryslân)

Deze map bevat een compacte, zelfstandige sample dataset van de gemeente **Súdwest-Fryslân** (13 buurten). Hiermee kan de D-OmniTwin applicatie direct lokaal getest en gedemonstreerd worden na een nieuwe installatie, zonder externe downloads of een volledige provinciedatabase.

## Doel en opzet

- **Onafhankelijk:** Geen afhankelijkheid van externe API's of grote downloads tijdens setup of CI/CD.
- **Representatief:** Bevat 13 diverse buurten (historisch stadje, dorpskern, lintbebouwing, woonwijk) met ~87 indicatoren en ~1.130 metingen. Eén buurt (Bolsward-Zuidoost) bevat demodata, zie hieronder.
- **Volledig functioneel:** Genoeg spreiding en observaties om Z-scores, Kompas-visualisaties, kaartlagen en de beleidsadviseur-chat direct te laten werken.
- **Idempotent:** Veilig en herhaaldelijk te laden zonder dubbele records (`ON CONFLICT DO UPDATE/NOTHING`).

---

## Inhoud van de map

```
init_data/sample/
├── README.md                           # Deze documentatie
├── 1_stuurdata/
│   └── stuurdata_seed.sql              # Basisconfiguratie, scenario's, profielen, kleurenschema's en prompts
└── 2_brondata/
    ├── sample_buurten.geojson          # Geometrieën van de 13 SWF-buurten (WGS84 / EPSG:4326)
    └── sample_indicatoren.csv          # Indicatoren en metingen per buurt (meest recente peiljaar)
```

### Geselecteerde buurten (SWF)

| CBS Code | Buurtnaam | Type / Karakteristiek |
|---|---|---|
| `BU19000001` | Bolsward-Noord | Stedelijk / Woonwijk |
| `BU19000002` | Bolsward-Zuidoost | Woonwijk — **demodata** (zie onder) |
| `BU19000004` | Bolsward-Noordoost | Stedelijk / Centrum |
| `BU19000108` | Bomenbuurt | Woonwijk |
| `BU19000200` | Workum | Regionaal centrum |
| `BU19000202` | Hindeloopen | Historisch stadje |
| `BU19000300` | Koudum | Dorpskern |
| `BU19000301` | Heidenschap | Lintbebouwing |
| `BU19000400` | Hemelum | Klein dorp |
| `BU19000401` | Warns | Klein dorp |
| `BU19001200` | Woudsend | Watersportdorp |
| `BU19001300` | Witmarsum | Dorpskern |
| `BU19002017` | Boazum | Terpdorp |

### Demodata: Bolsward-Zuidoost

`BU19000002` Bolsward-Zuidoost is toegevoegd als vaste testbuurt voor demo's en functionele tests. De **geometrie** is de echte CBS-buurtgrens (uit `init_data/fryslan/`, CC BY 4.0). De **indicatorwaarden zijn demodata**: per indicator en jaar het gemiddelde van Bolsward-Noord en Bolsward-Noordoost. In de kolom `bron` staat daarom `DEMO: …`. Gebruik deze waarden niet als echte cijfers. Wie de sample opnieuw genereert met `generate_sample.py` op een volledige database, krijgt voor deze buurt de echte waarden.

---

## Gebruik

### 1. Automatisch via Docker Compose (Aanbevolen voor snelle start)

Als `LOAD_SAMPLE_DATA=true` in je `.env` staat (standaard in `.env.example`), laadt de backend container bij de allereerste start automatisch het schema én de sample dataset zodra de database gereed is:

```bash
docker compose up
```
Zodra de logs aangeven dat `D-OmniTwin backend` is gestart, is de app direct operationeel op `http://localhost`.

### 2. Handmatig laden (CLI)

Indien je de database handmatig wilt seeden of lokaal buiten Docker draait:

```bash
# Schema laden (als database nog leeg is)
psql -h localhost -p 5433 -U omnitwin_user -d omnitwin_db -f init_data/schema/schema_latest.sql

# Sample data laden
python init_data/scripts/load_sample.py --stap alle
```

### 3. Specifieke stap uitvoeren

Het laadscript ondersteunt de volgende modules:

```bash
# Alléén stuurdata (configuratie, scenario's, prompts)
python init_data/scripts/load_sample.py --stap stuurdata

# Alléén de 13 buurten en geometrieën
python init_data/scripts/load_sample.py --stap buurten

# Alléén indicatoren metadata
python init_data/scripts/load_sample.py --stap indicatoren

# Alléén kompas mapping
python init_data/scripts/load_sample.py --stap kompas

# Alléén metingen/indicatorwaarden
python init_data/scripts/load_sample.py --stap waarden
```

---

## Bronvermelding & Licenties

De data in deze sample is afkomstig uit openbare overheidsbronnen en vrij herbruikbaar:

- **Centraal Bureau voor de Statistiek (CBS):** Kerncijfers wijken en buurten (Open Data Licentie / CC BY 4.0).
- **Basisregistratie Adressen en Gebouwen (Kadaster / BAG):** Woonplaatsen en pandstatistieken via PDOK (Publiek Domein).
- **Rijksinstituut voor Volksgezondheid en Milieu (RIVM / GGD):** Gezondheidsmonitor volwassenen en ouderen (Open Data).
- **Rijksdienst voor Ondernemend Nederland (RVO):** EP-Online energielabels (Open Data).
- **OpenStreetMap:** Halte-informatie OV (ODbL / Open Data).

Voor de volledige Friese dataset met alle 3.725 buurten en historische reeksen, zie [GETTING_STARTED.md](../../GETTING_STARTED.md).
