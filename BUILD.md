# BUILD & Setup Instructions

## Vereisten
- Python 3.9+
- PostgreSQL + PostGIS extensie
- Linux/WSL omgeving

## Installatie Stappen

### 1. Ontwikkelomgeving
De mappenstructuur is opgezet:
- `data/`: Databestanden
- `scripts/`: Python scripts
- `templates/`: Frontend templates
- `.venv/`: Virtual environment

### 2. Python Environment
```bash
# Aanmaken (indien nog niet gedaan)
python3 -m venv .venv

# Activeren
source .venv/bin/activate

# Dependencies installeren
pip install -r requirements.txt
```

### 3. Environment Configuration (.env)
**Versie 1.3.0+:** Secrets worden beheerd via `.env` file (niet in git!)

Maak een `.env` file aan in de project root:
```bash
touch .env
nano .env
```

Vul de volgende variabelen in:
```bash
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=omnitwin_db
DATABASE_USER=omnitwin_user
DATABASE_PASSWORD=jouw_wachtwoord_hier

# API Security
SECRET_KEY=gebruik_python_secrets_token_urlsafe_32
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Mapbox
MAPBOX_TOKEN=pk.eyJ1IjoidGFla2V2YW5kZXJsYWFuIiwiYSI6ImNram81ejI0azB5cnIycnRmM3hiaDBsc2sifQ.MiVfnOO0xSnNXBlngW2FRA
MAPBOX_STYLE=mapbox://styles/mapbox/light-v10

# App
DEBUG=true
LOG_LEVEL=INFO
```

**Secret Key genereren:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **⚠️ BELANGRIJK:** Voeg `.env` NOOIT toe aan git! Dit bestand staat in `.gitignore`.

### 3b. Frontend Configuration (admin-panel/.env)
Voor de Admin Panel frontend is ook een `.env` file nodig in `admin-panel/.env`:
```bash
RELEASE_DATE=14-02-2026
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ADMIN_KEY=your_admin_key_here  # Must match ADMIN_API_KEY in backend .env
```
**Opmerking:** De `REACT_APP_ADMIN_KEY` is nodig zodat de frontend statistieken kan ophalen zonder eerst in te loggen (voor dashoard widgets).

### 4. Database Setup (PostgreSQL + PostGIS)
Voer de volgende commando's uit om de database server en extensies te installeren:

### 4. Database Setup (PostgreSQL + PostGIS)

> **📘 Uitgebreide Handleiding:** Zie [docs/7-projectmanagement/logs/DATABASE_INITIALISATIE_HANDLEIDING.md](docs/7-projectmanagement/logs/DATABASE_INITIALISATIE_HANDLEIDING.md) voor gedetailleerde instructies.

**Korte Versie:**

```bash
# 1. Update package lists
sudo apt update

# 2. Installeer PostgreSQL en PostGIS
sudo apt install postgresql postgresql-postgis

# 3. Importeer het geconsolideerde schema (alle tabellen + views + seed data)
psql -U omnitwin_user -d omnitwin_db -f data/schema_latest.sql
```

**Verificatie:**
```bash
psql -U omnitwin_user -d omnitwin_db -c "\dt"
# Verwacht: 15 tabellen
```

### 5. Database Migrations
Wanneer er wijzigingen zijn aan het database schema:
1.  Maak een SQL script in `data/migrations/` (bijv. `v1.1_add_column.sql`).
2.  Update `data/schema_latest.sql` zodat nieuwe installaties direct de laatste versie hebben.
3.  Documenteer de wijziging in `CHANGELOG.md` (indien aanwezig).

> **Note:** Voor grote schema wijzigingen wordt aangeraden om Alembic te gebruiken (zie Roadmap).

### 6. Configuratie
Vergeet niet `config.ini` bij te werken met de juiste database credentials en API keys.
Zie `config.ini.example` (indien aanwezig) of de [Environment Configuration](#3-environment-configuration-env) sectie.

### 6. Applicatie Starten
Om de backend te starten, moet je **altijd** eerst de virtual environment activeren.

```bash
# 1. Activeer virtual environment
source .venv/bin/activate

# 2. Start de backend server (geoptimaliseerd)
python run_dev.py
```
De API is dan beschikbaar op: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

### 7. Gebiedsmonitor Data Laden (Optioneel)

Na het initialiseren van het schema (`schema_latest.sql`) is de database structuur klaar, maar nog leeg (behalve basis seed data). Voer deze scripts uit om data te laden:

```bash
# 1. Importeer indicatoren configuratie (metadata)
python scripts/import_gebiedsmonitor_config.py

# 2. Importeer geometrieën (GPKG en GeoJSON)
python scripts/import_geometrie.py

# 3. Importeer meetwaarden
python scripts/import_metingen.py

# 4. Importeer extra data (optioneel)
python scripts/import_metingen_nieuwebestanden.py
python scripts/import_extra_indicatoren.py

# 5. Importeer Kompas hiërarchie
python scripts/import_kompas_hierarchie.py

# 6. CBS Data Import
python scripts/import_cbs_data.py
```

**Brondata locatie:** `/data/voorbeeld_gebiedsmonitor/`

**Validatie:**
```bash
psql -U omnitwin_user -d omnitwin_db -c "SELECT COUNT(*) FROM gebieden;"
psql -U omnitwin_user -d omnitwin_db -c "SELECT COUNT(*) FROM indicatoren;"
```

### 8. Database Validatie (Optioneel)

Voer uitgebreide validatie uit met visuele checks:

```bash
# Activeer virtual environment (indien nog niet gedaan)
source .venv/bin/activate

# Voer validatiescript uit
python scripts/validate_gebiedsmonitor.py
```

**Output:**
- Markdown rapport met database statistieken
- 3 visualisaties (centroïden map, coverage chart, indicator stats)
- SQL view voorbeelden voor API development
- Locatie: `data/validatie/validatierapport_*.md`

**Te verwachten resultaten:**
- 1,721 gebieden (965 CBS Buurten + 756 Welstandsgebieden)
- 226 indicatoren
- 1,046 metingen
- 100% geometrie coverage

---

## 9. API Server Starten (Dag 3)

### Backend API

De Gebiedsmonitor API is geïmplementeerd met FastAPI. Start de server:

```bash
# Activeer virtual environment
source .venv/bin/activate

# Start development server (Backend)
source .venv/bin/activate && python run_dev.py
```

**API is beschikbaar op:**
- Base URL: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

**Beschikbare endpoints:**
```
GET  /api/gebiedsmonitor/gebiedstypes          # Lijst gebiedstypes
GET  /api/gebiedsmonitor/gebieden              # Lijst gebieden (paginatie)
GET  /api/gebiedsmonitor/gebieden/{id}         # Gebied details
GET  /api/gebiedsmonitor/indicatoren           # Lijst indicatoren
GET  /api/gebiedsmonitor/kaart/{type_id}       # GeoJSON voor kaart
```

**Test endpoints:**
```bash
# Test health
curl http://localhost:8000/health

# Get gebiedstypes
curl http://localhost:8000/api/gebiedsmonitor/gebiedstypes

# Get kaart data (vervang UUIDs met echte waarden)
curl "http://localhost:8000/api/gebiedsmonitor/kaart/{gebiedstype_id}?indicator_uuid={indicator_uuid}"
```

### Frontend (Volgt Later in Dag 3)

De frontend met deck.gl 3D visualisatie wordt toegevoegd aan `templates/index.html`.

---

**Laatste Update:** 18 januari 2026 - UI Redesign + Mapbox Integratie

## 10. UI Redesign Status (Dag 4 - 18-01-2026)

### Nieuwe Features
- ✅ **Verticale Tab Bar:** 7 panels (Controls, Legenda, Layers, Upload, Export, Kompas, Rapport)
- ✅ **Mapbox Basemap:** Light/Dark/Satellite/Streets styles
- ✅ **Dynamic Legenda:** SVG color gradient met coverage info
- ✅ **Export Functies:** PNG screenshot, GeoJSON, CSV download
- ✅ **Mobile Responsive:** Bottom sheet design voor mobile devices

### Nieuwe Dependencies
De volgende externe libraries zijn toegevoegd (via CDN):
```html
<!-- Mapbox GL JS v2.15.0 (voor basemap rendering) -->
<link href="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css" rel="stylesheet">
<script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js"></script>

<!-- deck.gl v9 (bestaand) -->
<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
```

### Static Assets
- **Lucide Icons:** 12 SVG vectoren in `static/images/`. Deze worden *inline* gebruikt in HTML voor dynamische styling (currentColor support voor theming).

### Mapbox Configuration
Mapbox API token is geconfigureerd in `config.ini`:
```ini
[MAPBOX]
api_token = pk.eyJ1IjoidGFla2V2YW5kZXJsYWFuIiwiYSI6ImNram81ejI0azB5cnIycnRmM3hiaDBsc2sifQ.MiVfnOO0xSnNXBlngW2FRA
default_style = mapbox://styles/mapbox/light-v10
```

### Browser Cache Issue
**BELANGRIJK:** Na updates een hard refresh doen:
- Windows: `Ctrl + Shift + R` of `Ctrl + F5`
- Mac: `Cmd + Shift + R`

Of via DevTools:
1. Open DevTools (F12)
2. Rechtermuisklik op refresh button  
3. Kies "Empty Cache and Hard Reload"

---

**Laatste Update:** 18 januari 2026 - UI Redesign + Mapbox Integratie

## 11. Admin Dashboard Status (Sprint 5F - 15-02-2026)

### Nieuwe Features
- ✅ **Dashboard KPI's:** Real-time statistieken over data en metadata coverage.
- ✅ **Kwadrant Dekking:** Visueel overzicht van vulling per kompas-kwadrant.
- ✅ **CSV Export:** Volledige dump van indicator status en metadata (`/api/admin/dashboard/export`).
- ✅ **Data Quality Monitors:** Alerts voor missende trendlines en incomplete metadata.

### Backend Endpoints
- `GET /api/admin/dashboard/stats`
- `GET /api/admin/dashboard/quadrants`
- `GET /api/admin/dashboard/indicators`
## 12. Security Updates (18-02-2026)

### Local Swagger UI Assets
Om de afhankelijkheid van externe CDN's te verwijderen en de Content Security Policy (CSP) strikter te maken, worden de Swagger UI assets nu lokaal geserveerd.

- **Locatie assets:** `static/swagger-ui/`
- **Configuratie:** `main.py` (custom `/docs` endpoint)
- **CSP:** `script-src` en `style-src` staan lokale assets toe voor Swagger. 
    - *Note:* Externe CDNs (`mapbox.com`, `unpkg.com`, `jsdelivr.net`) blijven toegestaan voor de frontend functionaliteit (kaarten, grafieken), maar zijn niet meer nodig voor de API docs.

**Command om assets te updaten:**
```bash
mkdir -p static/swagger-ui && \
curl -L https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js -o static/swagger-ui/swagger-ui-bundle.js && \
curl -L https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js -o static/swagger-ui/swagger-ui-standalone-preset.js && \
curl -L https://unpkg.com/swagger-ui-dist@5/swagger-ui.css -o static/swagger-ui/swagger-ui.css
```

## 13. AI Rapportagemodule (Sprint 8 - 22-02-2026)

De applicatie bevat een AI-gestuurde rapportagemodule die via de React frontend (`/admin/rapport` of `/publiek-rapport`) benaderbaar is. 

**Lokale Inferentie met Ollama:**
Omdat privacygevoelige CBS data niet naar externe partijen (zoals OpenAI) gestuurd mag worden, vereist D-OmniTwin een lokale LLM service via Ollama. 

1. **Installatie:** Installeer [Ollama](https://ollama.com).
2. **Model Download:** Trek het benodigde model (bijv. Qwen3) via de command line: `ollama run qwen2.5:32b` (of een variant die uw hardware aankan). 
3. **Beheer:** De modellen en systeemprompts zijn beheerbaar via het React Admin paneel in the tab "AI Configuratie". The API communiceert standaard the naar `http://localhost:11434`.

