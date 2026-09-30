# init_data — Initiatie Dataset D-OmniTwin

> ⚠️ **Installeren met Docker:** zie [`docs/9-beheer/installatie.md`](../docs/9-beheer/installatie.md). Daar laadt `db-init` het schema en de sample. De Fryslân-data laden in de Docker-installatie werkt nog niet (zie de installatiegids, sectie Data, en #69). `init_database.sh` hieronder is voor een PostgreSQL zonder Docker.

Deze map bevat alle benodigde data en scripts om D-OmniTwin **vanaf nul** op te zetten.  
Na dit proces heb je een gevulde database met **alle buurten in de provincie Fryslân** en **echte CBS open data** voor direct gebruik.

> **Licentie data:** CBS open data is beschikbaar onder [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — vrij herbruikbaar mits bronvermelding.  
> **Licentie code:** EUPL 1.2

---

## 📁 Inhoud

```
init_data/
├── schema/
│   └── schema_latest.sql              # Volledig database schema (tabellen, views, triggers)
│
├── kompas/
│   └── kompas_hierarchie.csv          # D-Omni Kompas structuur (titels → thema's → onderdelen → indicatoren)
│
├── indicatoren/
│   └── indicatoren_seed.json          # Metadata van 235 indicatoren (incl. Kompas-hiërarchie)
│
├── fryslan/
│   ├── README.md                      # Bronvermelding en licentie-informatie
│   ├── buurten_fryslan.geojson        # CBS buurten 2024 — provincie Fryslân (~350 buurten, WGS84)
│   └── indicatorwaarden_fryslan.csv   # CBS open data — indicatorwaarden per buurt
│
└── scripts/
    ├── init_database.sh               # ⭐ Master initiatie script (alles in 1 stap, incl. admin)
    ├── seed_fryslan.py                # Python import script (database vullen)
    ├── create_admin.py                # 👤 Admin gebruiker + API key aanmaken (stap 6)
    ├── download_buurten_fryslan.py    # Download GeoJSON via PDOK WFS
    └── download_indicatoren_fryslan.py # Download CBS indicatorwaarden via OData API
```

---

## 🚀 Gebruik

Zie [`GETTING_STARTED.md`](../GETTING_STARTED.md) in de projectroot voor de volledige stap-voor-stap gids.

**Snel starten (na database aanmaken):**

```bash
# 1. Geodata downloaden (eenmalig, ~5 MB)
python init_data/scripts/download_buurten_fryslan.py

# 2. CBS indicatorwaarden downloaden (eenmalig)
python init_data/scripts/download_indicatoren_fryslan.py

# 3. Alles in de database laden (incl. admin gebruiker aanmaken)
bash init_data/scripts/init_database.sh
```

Of los de admin stap separaat draaien:
```bash
python init_data/scripts/create_admin.py
# Of wachtwoord resetten:
python init_data/scripts/create_admin.py --reset-password
```

---

## 📊 Inhoud Datasets

### Buurten Fryslân (`buurten_fryslan.geojson`)

| Kenmerk | Waarde |
|---------|--------|
| Bron | CBS Gebiedsindelingen 2024 via PDOK WFS |
| Licentie | CC BY 4.0 |
| Coördinatenstelsel | WGS84 (EPSG:4326) |
| Gemeente coverage | Alle 18 Friese gemeenten |
| Aantal buurten | ≈ 350 |

### Indicatorwaarden (`indicatorwaarden_fryslan.csv`)

| Kolom | Beschrijving |
|-------|-------------|
| `buurt_id` | CBS buurtcode (bijv. `BU19000101`) |
| `indicator_naam` | Naam van de indicator |
| `waarde` | Numerieke waarde |
| `jaar` | Peiljaar (2022 of 2023) |
| `bron` | CBS dataset naam |

| Thema | Indicatoren |
|-------|------------|
| Bevolking | Leeftijdsverdeling, inkomen, opleiding, huishoudens, bevolkingsdichtheid |
| Wonen | Koopwoningen, huurwoningen, WOZ-waarde, bouwjaar, woningoppervlakte (BAG) |
| Gezondheid | Overgewicht, roken, eenzaamheid, bewegen, obesitas, ervaren gezondheid |
| Voorzieningen | Afstand tot huisarts, supermarkt, school, apotheek, bibliotheek, zwembad |
| Veiligheid | Overlastmeldingen, inbraak, diefstal |
| Meedoen | Vrijwilligerswerk, mantelzorg |
| Energie | Energielabels (definitief, voorlopig, totaal), coverage |
| Bebouwing | BAG-functies (woon, winkel, kantoor, onderwijs, sport, ...) |
| Klimaat | Koele plekken, grondwaterstand, wateroverlast (toekomstige ETL) |

---

## 🔗 Databronnen & Licenties

| Dataset | Bron | Licentie |
|---------|------|----------|
| CBS Buurten 2024 | [PDOK / CBS](https://www.pdok.nl) | CC BY 4.0 |
| Kerncijfers wijken en buurten 2023 | [CBS StatLine](https://opendata.cbs.nl) | CC BY 4.0 |
| Gezondheid per wijk en buurt 2022 | [RIVM via CBS dataderden](https://dataderden.cbs.nl) | CC BY 4.0 |

**Bronvermelding:** Centraal Bureau voor de Statistiek (CBS) / Rijksinstituut voor Volksgezondheid en Milieu (RIVM), [jaar van download].
