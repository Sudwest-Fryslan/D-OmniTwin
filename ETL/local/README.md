# D-OmniTwin ETL — Standalone Pipeline (`ETL/local/`)

Deze map bevat scripts waarmee je de **volledige D-OmniTwin database kunt inrichten
op een eigen PostgreSQL server**, volledig onafhankelijk van de FastAPI applicatie.

> **Let op:** `db.ini` en `output/` staan in `.gitignore` en worden **nooit gecommit**.
> Kopieer `db.ini.example` naar `db.ini` en vul je eigen database gegevens in.

---

## Vereisten

- Python 3.10+
- PostgreSQL 14+ met **PostGIS** en **pgvector** extensies
- Python packages:

```bash
pip install psycopg2-binary requests tqdm passlib[bcrypt] bcrypt==4.0.1
```

---

## Database inrichten (éénmalig, vóór de pipeline)

Voordat je de ETL pipeline kunt draaien, moet de doeldatabase correct zijn ingericht.
Doorloop de onderstaande stappen **als PostgreSQL superuser** (`postgres`).

### 1. PostgreSQL installeren

**Ubuntu / WSL (aanbevolen versie: 14 of 16):**
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Verificatie:**
```bash
psql --version
# → psql (PostgreSQL) 14.x
```

---

### 2. Database en gebruiker aanmaken

Verbind als superuser en maak de database aan:

```bash
sudo -u postgres psql
```

Voer in de psql-prompt uit:

```sql
-- Gebruiker aanmaken
CREATE USER omnitwin_user WITH PASSWORD 'kies_een_sterk_wachtwoord';

-- Database aanmaken met de juiste eigenaar
CREATE DATABASE omnitwin_db
    OWNER     = omnitwin_user
    ENCODING  = 'UTF8'
    LC_COLLATE = 'nl_NL.UTF-8'
    LC_CTYPE   = 'nl_NL.UTF-8'
    TEMPLATE   = template0;

-- Rechten geven
GRANT ALL PRIVILEGES ON DATABASE omnitwin_db TO omnitwin_user;

\q
```

> **Tip:** Als `nl_NL.UTF-8` niet beschikbaar is op je systeem:
> ```bash
> sudo locale-gen nl_NL.UTF-8
> sudo update-locale
> ```
> Of gebruik `en_US.UTF-8` als alternatief — de applicatie werkt met beide.

---

### 3. PostGIS installeren

PostGIS voegt geografische datatypes en functies toe (nodig voor buurtgrenzen/kaartlagen).

```bash
# Ubuntu 22.04 + PostgreSQL 14:
sudo apt-get install -y postgresql-14-postgis-3 postgresql-14-postgis-3-scripts

# Ubuntu 22.04 + PostgreSQL 16:
sudo apt-get install -y postgresql-16-postgis-3 postgresql-16-postgis-3-scripts
```

Activeer PostGIS in de database:

```bash
psql -h localhost -U omnitwin_user -d omnitwin_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**Verificatie:**
```bash
psql -h localhost -U omnitwin_user -d omnitwin_db -c "SELECT PostGIS_Version();"
# → 3.2 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
```

---

### 4. pgvector installeren

pgvector voegt vectoropslag toe (nodig voor de AI-assistent embeddings, 384-dimensionale vectoren).

**Optie A — via apt (Ubuntu 22.04+, werkt voor PG14/15/16):**
```bash
# Voeg de pgvector apt repository toe
sudo apt-get install -y postgresql-14-pgvector
```

> Als dit pakket niet beschikbaar is in jouw distributie, gebruik dan Optie B.

**Optie B — compileren vanuit source (altijd beschikbaar):**
```bash
# Build-tools installeren
sudo apt-get install -y postgresql-server-dev-14 build-essential git

# Source ophalen en bouwen
git clone --depth 1 https://github.com/pgvector/pgvector.git ~/pgvector_build
cd ~/pgvector_build
make
sudo make install
cd ~
```

Activeer pgvector in de database:

```bash
psql -h localhost -U omnitwin_user -d omnitwin_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Verificatie:**
```bash
psql -h localhost -U omnitwin_user -d omnitwin_db \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis','vector');"
```

Verwachte uitvoer:
```
 extname  | extversion
----------+-----------
 postgis  | 3.2.0
 vector   | 0.8.0
```

---

### 5. Verbinding verifiëren

Controleer dat alles klopt voordat je de pipeline start:

```bash
cd ETL/local
python db_connect.py
```

Verwachte uitvoer:
```
🔌 Verbinden met omnitwin_user@localhost:5432/omnitwin_db ...
✅ Database verbinding OK

📊 Database Status:
──────────────────────────────────────────────────
  ✅  PostgreSQL versie        PostgreSQL 14.x
  ✅  Indicatoren              0          ← wordt gevuld door pipeline
  ✅  Gebieden                 0          ← wordt gevuld door pipeline
  ✅  Metingen (gebied_data)   0          ← wordt gevuld door pipeline
  ✅  PostGIS actief           3.2 ...
  ✅  pgvector actief          0.8.x
──────────────────────────────────────────────────
```

> Als PostGIS of pgvector ontbreekt (`❌`), doorloop dan stap 3 of 4 opnieuw.
> `etl_01_init_schema.py` zal de extensies ook proberen te activeren, maar dit
> vereist dat de `.so` bibliotheek al op de server is geïnstalleerd.

---

### Samenvatting extensie vereisten

| Extensie | Versie | Waarvoor | Installatie |
|----------|--------|----------|-------------|
| `postgis` | ≥ 3.0 | Geografische datatypes, `ST_GeomFromGeoJSON`, ruimtelijke queries | `apt install postgresql-14-postgis-3` |
| `vector` | ≥ 0.5 | 384-dim AI embeddings voor de D-Omni Assistent | `apt install postgresql-14-pgvector` of compile |
| `plpgsql` | ingebouwd | Stored procedures en triggers | Altijd aanwezig |

---



## Snelstart

```bash
# 1. Configureer je database
cp ETL/local/db.ini.example ETL/local/db.ini
nano ETL/local/db.ini   # vul host, dbname, user, password in

# 2. Voer de volledige pipeline uit
cd ETL/local
python run_pipeline.py --alle --gemeenten 1900,0090

# Of voor heel Fryslân:
python run_pipeline.py --alle --provincie Fryslan
```

---

## Stappen (één voor één)

| Script | Beschrijving |
|--------|-------------|
| `etl_01_init_schema.py` | Database schema laden (tabellen, views, triggers, seed data) |
| `etl_02_import_geometrie.py` | CBS buurtgrenzen importeren via PDOK WFS of lokaal GeoJSON |
| `etl_03_seed_indicatoren.py` | Indicator definities laden uit `indicatoren_seed.json` |
| `etl_04_import_cbs.py` | CBS kerncijfers ophalen via OData API en in DB laden |
| `etl_05_import_kompas.py` | Kompas hiërarchie laden vanuit `kompas_hierarchie.csv` |
| `etl_06_maak_admin.py` | Admin gebruiker en API key aanmaken |

### Stap 1 — Schema initialiseren

```bash
python etl_01_init_schema.py           # normaal
python etl_01_init_schema.py --check   # alleen status controleren
python etl_01_init_schema.py --force-reset  # ⚠️ WIST ALLES en herlaadt
```

### Stap 2 — Geometrie

```bash
python etl_02_import_geometrie.py --provincie Fryslan
python etl_02_import_geometrie.py --gemeenten 1900,0090,1940
python etl_02_import_geometrie.py --bestand /pad/naar/buurten.geojson
python etl_02_import_geometrie.py --check   # alleen tellen
```

### Stap 3 — Indicatoren seeden

```bash
python etl_03_seed_indicatoren.py
python etl_03_seed_indicatoren.py --dry-run      # simuleer, geen wijzigingen
python etl_03_seed_indicatoren.py --bestand /pad/naar/eigen_indicatoren.json
```

### Stap 4 — CBS Data importeren

```bash
python etl_04_import_cbs.py --gemeenten 1900
python etl_04_import_cbs.py --dataset 84799NED --gemeenten 1900
python etl_04_import_cbs.py --rivm --gemeenten 1900         # RIVM data
python etl_04_import_cbs.py --extract-only --gemeenten 1900  # alleen ophalen
python etl_04_import_cbs.py --import-only                    # alleen importeren
python etl_04_import_cbs.py --lijst                          # datasets tonen
```

### Stap 5 — Kompas

```bash
python etl_05_import_kompas.py
python etl_05_import_kompas.py --check   # huidige structuur tonen
python etl_05_import_kompas.py --reset   # eerst wissen, dan laden
python etl_05_import_kompas.py --bestand /pad/naar/eigen_kompas.csv
```

### Stap 6 — Admin gebruiker

```bash
python etl_06_maak_admin.py
python etl_06_maak_admin.py --gebruiker admin --wachtwoord Veilig@2026
python etl_06_maak_admin.py --check     # gebruikersoverzicht
python etl_06_maak_admin.py --reset     # wachtwoord resetten
```

---

## Database configuratie (`db.ini`)

De scripts ondersteunen drie manieren om de database te configureren (in volgorde van prioriteit):

1. **Omgevingsvariabelen** (hoogste prioriteit — ideaal voor CI/CD)
   ```bash
   export DATABASE_HOST=mijn-server.nl
   export DATABASE_NAME=omnitwin_db
   export DATABASE_USER=omnitwin_user
   export DATABASE_PASSWORD=geheim
   python run_pipeline.py --alle
   ```

2. **`.env` bestand** in de project root (standaard voor de app)
   ```env
   DATABASE_HOST=localhost
   DATABASE_NAME=omnitwin_db
   DATABASE_USER=omnitwin_user
   DATABASE_PASSWORD=geheim
   ```

3. **`ETL/local/db.ini`** (aanbevolen voor losse ETL runs op afwijkende databases)
   ```ini
   [DATABASE]
   host     = localhost
   port     = 5432
   dbname   = mijn_eigen_db
   user     = mijn_user
   password = mijn_wachtwoord
   ```

---

## Status controleren

```bash
# Verbinding testen + DB statistieken tonen:
python db_connect.py

# Of via de pipeline runner:
python run_pipeline.py --status
```

---

## Inhoud van deze map

```
ETL/local/
├── README.md                   # Dit bestand
├── db.ini.example              # Template — kopieer naar db.ini
├── db.ini                      # Jouw configuratie (in .gitignore!)
├── db_connect.py               # Centrale DB connector (gedeeld door alle scripts)
├── run_pipeline.py             # Orchestrator — voert alle stappen uit
├── etl_01_init_schema.py       # Stap 1: Schema
├── etl_02_import_geometrie.py  # Stap 2: Geometrie (CBS buurten)
├── etl_03_seed_indicatoren.py  # Stap 3: Indicator definities
├── etl_04_import_cbs.py        # Stap 4: CBS kerncijfers
├── etl_05_import_kompas.py     # Stap 5: Kompas hiërarchie
├── etl_06_maak_admin.py        # Stap 6: Admin gebruiker
└── output/                     # Tijdelijke CBS JSON bestanden (in .gitignore!)
```

---

## Relatie met bestaande scripts

De scripts in `ETL/local/` zijn **nieuw en staan naast** de bestaande scripts in `ETL/CBS/`,
`ETL/Kompas/`, etc. De bestaande scripts zijn ongewijzigd en gebruiken nog `config.ini`.

| Functie | Oud (config.ini) | Nieuw (db.ini/.env) |
|---------|-----------------|---------------------|
| DB verbinding | `ETL/CBS/import_cbs_data.py` | `ETL/local/db_connect.py` |
| CBS import | `ETL/CBS/import_cbs_data.py` | `ETL/local/etl_04_import_cbs.py` |
| Kompas import | `ETL/Kompas/import_kompas_hierarchie.py` | `ETL/local/etl_05_import_kompas.py` |
| Geometrie | `ETL/Geometrie/import_geometrie.py` | `ETL/local/etl_02_import_geometrie.py` |
| Schema | `ETL/Utils/db_init.py` | `ETL/local/etl_01_init_schema.py` |
| Orchestratie | `ETL/run_etl.py` | `ETL/local/run_pipeline.py` |

---

*Gegenereerd: april 2026 — D-OmniTwin ETL v2.0*
