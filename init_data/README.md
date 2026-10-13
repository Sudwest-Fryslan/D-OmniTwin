# init_data — Initiatie Dataset D-OmniTwin

> ⚠️ **Installeren met Docker:** zie [`docs/9-beheer/installatie.md`](../docs/9-beheer/installatie.md). Daar laadt `db-init` het schema en de sample. De volledige Fryslân-data laad je daarna met één commando:
>
> ```bash
> docker compose run --rm db-init python init_data/scripts/seed_fryslan.py --stap alle
> ```
>
> Idempotent, eindigt met een samenvatting per stap en exitcode 1 bij fouten.
>
> **Eén initialisatieroute (#69):** `docker-entrypoint.sh init`. In Docker is dat de service `db-init`; zonder Docker doet `init_database.sh` precies hetzelfde. Configuratie alleen uit `.env` (`DATABASE_*`).

Deze map bevat alle benodigde data en scripts om D-OmniTwin **vanaf nul** op te zetten.  
Na dit proces heb je een gevulde database met **alle buurten in de provincie Fryslân** en **echte CBS open data** voor direct gebruik.

> **Licentie data:** CBS open data is beschikbaar onder [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — vrij herbruikbaar mits bronvermelding.  
> **Licentie code:** EUPL 1.2

---

## 📁 Inhoud

Schema, migraties en stuurdata (Kompas-indeling, indicatordefinities) staan sinds 0.2.0 in [`db/`](../db/README.md).

```
init_data/
├── fryslan/
│   ├── README.md                      # Bronvermelding en licentie-informatie
│   ├── buurten_fryslan.geojson        # CBS buurten 2024 — provincie Fryslân (931 buurten, WGS84)
│   └── indicatorwaarden_fryslan.csv   # RIVM Gezondheidsmonitor — indicatorwaarden per buurt
│
├── cbs/
│   └── datapackage.json               # bron, licentie, tabellen per jaar, mapping, codecontrole
│
└── scripts/
    ├── init_database.sh               # Zonder Docker: dezelfde route als db-init (docker-entrypoint.sh init)
    ├── load_sample.py                 # Stuurdata, definities en drempels (aangeroepen door de init)
    ├── seed_fryslan.py                # Volledige Fryslân-data (na de init; ook in Docker)
    ├── create_admin.py                # 👤 Beheerder aanmaken of wachtwoord resetten
    ├── download_buurten_fryslan.py    # Download GeoJSON via PDOK WFS
    ├── download_indicatoren_fryslan.py # Download RIVM-indicatorwaarden via CBS dataderden
    ├── download_cbs_kerncijfers.py    # Download CBS Kerncijfers 2019-nu (alle jaargangen) via OData
    └── laad_cbs.py                    # CBS Kerncijfers downloaden (met cache) en laden voor de gebieden in de database
```

---

## 🚀 Gebruik

Installeren met Docker: zie de [installatiegids](../docs/9-beheer/installatie.md).

**Zonder Docker** (PostgreSQL met PostGIS en pgvector, `psql` en een Python-omgeving met `requirements.txt`; `.env` met de `DATABASE_*`-gegevens):

```bash
# 1. Database inrichten: schema, migraties, stuurdata, use cases (LOAD_SAMPLE_DATA=true), beheerder, rollen
bash init_data/scripts/init_database.sh

# 2. Optioneel: volledige Fryslân-data
python init_data/scripts/download_buurten_fryslan.py        # eenmalig, ~5 MB
python init_data/scripts/download_indicatoren_fryslan.py    # RIVM (de CSV staat ook in git)
python init_data/scripts/seed_fryslan.py --stap alle
```

Beheerder los aanmaken of het wachtwoord resetten:
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
| Aantal buurten | 931 |

### Indicatorwaarden (`indicatorwaarden_fryslan.csv`)

| Kolom | Beschrijving |
|-------|-------------|
| `buurt_id` | CBS buurtcode (bijv. `BU19000101`) |
| `indicator_naam` | Naam van de indicator |
| `waarde` | Numerieke waarde |
| `jaar` | Peiljaar (RIVM 2012-2024) |
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
| Kerncijfers wijken en buurten 2019-2026 (`init_data/cbs/`, zie [`cbs_kerncijfers.md`](../docs/3-data-engineering/cbs_kerncijfers.md)) | [CBS StatLine](https://opendata.cbs.nl) | CC BY 4.0 |
| Gezondheid per wijk en buurt 2022 | [RIVM via CBS dataderden](https://dataderden.cbs.nl) | CC BY 4.0 |

**Bronvermelding:** Centraal Bureau voor de Statistiek (CBS) / Rijksinstituut voor Volksgezondheid en Milieu (RIVM), [jaar van download].
