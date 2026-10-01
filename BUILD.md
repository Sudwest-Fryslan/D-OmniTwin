# BUILD & Setup Instructions

> ⚠️ **Verouderd/aanvullend** — de actuele installatie staat in [`docs/9-beheer/installatie.md`](./docs/9-beheer/installatie.md). Bij verschillen geldt die gids. Dit bestand blijft voor de build-notities en de sprint-changelog.

## Vereisten
- Python 3.10+
- PostgreSQL 14+ (met PostGIS, pgvector en pg_trgm extensies)
- Docker & Docker Compose (aanbevolen voor Traefik, PostgREST en pg_featureserv)
- Linux / WSL2 omgeving

## Installatie Stappen

### 1. Ontwikkelomgeving & Applicatie Stack
De Hybride Dataspace Architectuur draait met Docker Compose. Dit start in één keer de FastAPI backend, PostgREST (Data API), pg_featureserv (Geo API), PostgreSQL en de Traefik reverse proxy.

```bash
docker compose up -d
```
(Voor lokale backend ontwikkeling via Python, zie Stap 2 hieronder)

### 2. Python Environment (Lokale Backend Dev)
```bash
# Aanmaken (indien nog niet gedaan)
python3 -m venv .venv

# Activeren
source .venv/bin/activate

# Dependencies installeren
pip install -r requirements.txt
```

### 3. Environment Configuration (.env)
Secrets worden beheerd via `.env` (nooit in git committen!). Gebruik de interactieve setup wizard om veilige sleutels te genereren:

```bash
python init_data/scripts/setup_env.py
```

Of maak handmatig een `.env` aan op basis van `.env.example`:
```bash
cp .env.example .env
```

Belangrijke variabelen:
```bash
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=omnitwin_db
DATABASE_USER=omnitwin_user
DATABASE_PASSWORD=jouw_wachtwoord_hier

# API Security
SECRET_KEY=gebruik_python_secrets_token_urlsafe_32
ADMIN_API_KEY=jouw_admin_api_key
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# App
DEBUG=true
LOG_LEVEL=INFO
```

### 3b. Frontend Configuration (admin-panel/.env)
Voor de Admin Panel dev server (Vite) kan optioneel een `.env` file in `admin-panel/.env`; API-calls gaan via de proxy naar poort 8000:
```bash
VITE_ADMIN_KEY=your_admin_key_here  # Optioneel; must match ADMIN_API_KEY in backend .env
```

### 4. Database Setup & Initiatie Data

> **📘 Volledige Gids:** Zie [`GETTING_STARTED.md`](./GETTING_STARTED.md) voor de actuele stap-voor-stap installatie.

```bash
# 1. Database en gebruiker aanmaken
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'jouw-wachtwoord';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"

# 2. Extensies activeren
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION postgis; CREATE EXTENSION vector; CREATE EXTENSION pg_trgm;"

# 3. Initiatiedata ophalen (PDOK API + CBS OData) & database seeden
python init_data/scripts/download_buurten_fryslan.py
python init_data/scripts/download_indicatoren_fryslan.py
bash init_data/scripts/init_database.sh
```

### 5. Database Migrations
Wanneer er wijzigingen zijn aan het database schema:
1. Maak een SQL migratiescript in `migrations/` (bijv. `schema_v15_xxx.sql`).
2. Update `init_data/schema/schema_latest.sql` zodat nieuwe installaties direct up-to-date zijn.
3. Documenteer de wijziging in [docs/STATE.md](docs/STATE.md) en [BUILD.md](BUILD.md).

### 6. Applicatie Starten
Om de backend lokaal te starten met geoptimaliseerde live reload:

```bash
source .venv/bin/activate
python run_dev.py
```
- App: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Admin Panel: `http://localhost:8000/admin` (of via `cd admin-panel && npm start` op poort 3000)

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
MapLibre GL JS 3.6.2, deck.gl 9.4.0, D3.js 7.9.0, Chart.js 4.5.1 en het lettertype Inter worden zelf gehost in `static/vendor/` (#117), niet via een CDN. Versies, licenties en bijwerken: zie `static/vendor/README.md`.

### Static Assets
- **Lucide Icons:** 12 SVG vectoren in `static/images/`. Deze worden *inline* gebruikt in HTML voor dynamische styling (currentColor support voor theming).

### Basiskaart
De basiskaart is MapLibre met PDOK-achtergrondkaarten (stijlen in `templates/index.html`). Een Mapbox-token is niet nodig.

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
    - *Note:* Sinds #117 staan ook de frontend-bibliotheken lokaal (`static/vendor/`); de CSP staat geen CDN- of font-domeinen meer toe.

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
2. **Model Download:** Trek het benodigde model (bijv. Qwen3) via de command line: `ollama run qwen3:30b` (of een kleiner model indien uw hardware dit vereist).
3. **Beheer:** De modellen en systeemprompts zijn beheerbaar via het React Admin paneel → tab "AI Configuratie". De API communiceert standaard naar `http://localhost:11434`.

---

## 📋 Sprint Changelog

> Volledig dag-voor-dag overzicht van alle ontwikkelsessies.
> De laatste sprints zijn samengevat in de [README.md](./README.md#-recent-voltooid).
> Dit changelog dient als archief en basis voor toekomstige CHANGELOG.md releases.

---

### Dag 92 (20-07-2026): Sprint 22 — Data Engineering & ETL Dataspace Track 📊🌐
**Focus:** ETL/Dataspace gap-analyse en bronvergelijking sociaaldomein (812 indicatoren).
- ✅ **Gap-Analyse:** `etl_dataspace_gap_analyse.md` — D-OmniTwin herpositioneerd als datamart-consument (Gold laag) van de Friese Data Space (FRLDS).
- ✅ **Bronvergelijking:** 812 indicatoren uit Excel Jantina geïdentificeerd t.o.v. de database (1,4% dekking), plan voor geautomatiseerde ontologie mapping vastgelegd.

---

### Dag 90 (20-07-2026): Sprint 21 — Data Kwaliteit & Deduplicatie Assistent 🧹✨
**Focus:** Ruisvrije database, AI matching en interactieve merge tooling.
- ✅ **Deduplicatie Pipeline:** `pg_trgm` fuzzy matching + `pgvector` embeddings + AI-advies validatie.
- ✅ **Admin UI:** Interactieve deduplicatie pagina met checkboxes voor samenvoegen, groeperen en uitzonderingenbeheer.

---

### Dag 86 (05-07-2026): Sprint 19B — Van Data naar Inzicht (Issue #15) 📈🧭
**Focus:** Diepgaande analyse en besluitvormingsondersteuning.
- ✅ **Thema-Analyse Visualisatie:** D3 Diverging Bar Chart voor Z-scores en thematische afwijkingen.
- ✅ **Boomstructuur Filter:** Interactief filteren op thema en subthema in het rapportagepaneel.
- ✅ **Dataspace Migratie (Sprint 19):** Traefik API Gateway, PostgREST (`/api/data/*`) en pg_featureserv (`/api/geo/*`) geïntegreerd in Docker stack.

---

### Dag 79 (30-06-2026): Sprint 18 — IJsselmeerkust als Besluitinstrument 🗺️⚖️
**Focus:** Besluitondersteuning, BAG Woonplaatsen (WFS), multi-gebied benchmarking en top afwijkers.
- ✅ **Externe Kaartlagen:** WFS koppeling voor BAG Woonplaatsen en lokale GPKG/GeoJSON file uploads via het beheerpaneel.
- ✅ **Multi-Gebied Benchmarking:** Benchmark vergelijkingstabel per woonplaats vs. gemeentelijk/provinciaal gemiddelde.
- ✅ **Top 3+3 Uitschieters:** Automatische uitschieterdetectie en highlight per indicator.

---

### Dag 68 (26-05-2026): Sprint 17 — Configureerbare Logging Infrastructuur 📋🔒
**Focus:** Realtime in-app logging en monitoring.
- ✅ **AsyncLogQueue:** Logging naar `app_logs` database en roterende server logs over 9 categorieën.
- ✅ **Log Viewer:** React Admin Panel log viewer met filtering, statistieken en automatische retentie opschoning.

---

### Dag 57 (12-04-2026): Multi-Gebiedsdossier Uitbreiding — Top 3, Themafilter & D3 Projectie 🗺️📊
**Focus:** Verrijking van de analysefunctionaliteit en visuele correctheid van het Multi-Gebiedsdossier.

- ✅ **Backend Top 3** (`report_service.py`): SQL CTE omgebouwd van `DISTINCT ON` naar `ROW_NUMBER() OVER(PARTITION BY gebied_id ORDER BY ABS(z_score) DESC)` — retourneert nu top-3 uitschieters per buurt als geneste `top_3: []` array.
- ✅ **Backend Thema-filter** (`report_service.py`, `routers/report.py`): Optioneel `thema: Optional[str]`-parameter in Pydantic model + `WHERE thema = :thema_filter` CTE-laag. Werkt voor zowel de JSON als de GeoJSON endpoint.
- ✅ **Backend GeoJSON** (`report_service.py`): `generate_multi_gebied_geojson()` aangevuld met `thema`-param en `top_3` in de GeoJSON `properties` per feature.
- ✅ **Frontend D3 Projectie** (`MultiGebiedPage.tsx`): `d3.geoMercator().fitSize()` vervangt de platte lineaire XY-schaling — Fryslân wordt nu geografisch correct weergegeven.
- ✅ **Frontend Donut Fix** (`MultiGebiedPage.tsx`): Polygonen gesorteerd op `d3.geoArea` (grootste oppervlakte eerst), zodat kleine binnenbuurten bovenop grote vlakken renderen.
- ✅ **Frontend Thema Dropdown** (`MultiGebiedPage.tsx`): Selector met 5 opties triggert een herlaad van kaart + tabel.
- ✅ **Frontend Hover Top 3** (`MultiGebiedPage.tsx`): Hover-paneel toont genummerde top-3 afwijkingen per buurt.
- ✅ **Frontend Nested Tabel** (`MultiGebiedPage.tsx`): Uitklapknop `▶`/`▼` per buurt onthult subrijen voor rang 2 en 3.
- ✅ **Frontend Lucide Icons**: `Map`, `BarChart2`, `List`, `ChevronRight`, `ChevronDown` vervangen emoji's.
- ✅ **Bug #44 Fix** (thema case-mismatch): Dropdown-waarden gecorrigeerd naar exact DB-lowercase.
- ✅ **Bug #45 Fix** (hover flicker loop): Vaste `height: 140px` op hover-paneel.
- ✅ **UI** (`templates/index.html`): `🗺️` emoji → `map-pinned.svg` in Kaartlagen-paneel.
- ✅ **Coverage Fix + Semantiek** (`gebiedsmonitor_service.py`, `index.html`, `kompas.js`): Onafhankelijke COUNT-query voor werkelijk gebiedstotaal; labels hernoemd naar "Gebiedsdekking" / "Indicatordekking".

---

### Dag 56 (11-04-2026): Git Initiatie & Veiligheidsslag 🔒🚀
**Focus:** Project opschonen voor versiebeheer en eerste release-candidate naar de private repository sturen.

- ✅ **Security Cleanup:** Hardcoded beheerdersgegevens verwijderd/uitgesloten van Git en veilig verplaatst naar `.env`. De `.gitignore` waterdicht gemaakt voor zware datasets (`/data`), logs en AI geheugen.
- ✅ **Remote Connectie:** SSH authenticatie en remote push naar `TLaan/D-OmniTwin.git` opgeleverd (319+ bestanden).
- ✅ **Root Opschoning:** Onnodige en achterhaalde werkbestanden weggewerkt voor een opgeruimde basis `main` branch.

---

### Dag 55 (10-04-2026): Multi-Gebiedsdossier & Optimalisaties 🗺️📊
**Focus:** Afronding rapportmodule voor Multi-gebied selecties en integratie van directe verbeteringen vanuit kwaliteitscontrole.

- ✅ **Backend Analyse** (`routers/report.py`, `services/report_service.py`): Nieuwe POST-endpoints (`/multi-gebied`, `/geojson`), generatie van dynamische payload voor thema-aggregatie, Z-scores, kleurcoderingen, en dynamisch bereik (min/max/gemiddelde).
- ✅ **Frontend Panel** (`MultiGebiedPage.tsx`): Interactieve SVG choropleth-kaart met Z-score afwijkingen, Ranked Uitschietertabel en Thema-aggregaat bars.
- ✅ **UI/UX Fixes:**
    - Introductie van een divergerend **Colorblind-safe** z-score palet.
    - Oplossen van een mouse-hover *flicker bug* via specifieke CSS/layout vastlegging.
    - Volledige integratie via modals van de interactielaag in de `app.js` (Multi-select fallback).
- ✅ **Data Opschoning:** Automatische detectie en filtering van "water-buurten" via metadata velden om ruis te voorkomen in statistische overzichten.

**Track B aanvulling (Dag 55):**
- ✅ **Track A — Intelligente Chat Acties** (`chat.js`, `app.js`, `kompas.js`, `chat.py`, `llm_service.py`):
    - Nieuwe actie-types: `SELECTEER_GEMEENTE`, `SELECTEER_GEBIEDSTYPE`, `SELECTEER_KOMPAS`, `OPEN_KOMPAS`.
    - Context-uitbreiding: De assistent bevat nu de meta-data van **49 gemeenten** (Fryslân, Groningen, Drenthe).
    - EventBus integratie met manual event dispatching voor naadloze UI-synchronisatie.
    - Robuuste Pydantic modellen in de backend voor volledige data-doorgifte van LLM naar frontend.
- ✅ **Track D — Performance & Developer Experience** (`run_dev.py`, `llm_service.py`):
    - Lazy loading van `SentenceTransformer` AI-modellen (30% snellere server start).
    - Geoptimaliseerde Uvicorn reload (uitsluiten van `node_modules`, `admin-panel`).
    - Introductie `run_dev.py` script voor een gestroomlijnde development loop.
- ✅ **Track E — Admin Integratie** (`index.html`, `styles.css`):
    - Auth-aware **"Beheer" knop** in de hoofdapp header.
    - Dynamische routing naar `/admin/login` of `/admin/dashboard`.

---

### Dag 43 (20-03-2026): Sprint 10 — D-Omni Assistent Chat Interface 🤖💬
**Focus:** Implementatie van een intent-based AI chat zijpaneel dat de kaart, het Kompas en rapport-generatie aanstuurt via natuurlijke taal.

- ✅ **Fase 0 — AI Search Priority Fix** (`services/ai_search_service.py`):
    - COALESCE beschrijvings-voorkeur: menselijk gevalideerd → AI-gegenereerd → standaard omschrijving.
    - `ontologie_status`, `eenheid` en `score_type` beschikbaar in zoekresultaten.
- ✅ **Fase 1 — Backend Chat Endpoint** (`routers/chat.py`, `services/llm_service.py`):
    - Nieuw `POST /api/chat` endpoint met Command Dispatch JSON structuur.
    - Rule-based intent classifier: `VERKEN_INDICATORS`, `VERGELIJK_GEBIEDEN`, `MAAK_RAPPORT`, `ALGEMEEN`.
    - `generate_chat_narrative()` in `LLMService` — beknopte NL-toelichting (≤80 woorden).
- ✅ **Fase 2 — Frontend Chat Zijpaneel** (`static/js/chat.js`, `templates/index.html`, `static/css/styles.css`):
    - `ChatPanel` klasse: open/close/toggle, loading dots, chat-historiek (groeit omhoog).
    - cpu.svg toggle-knop (inline SVG) in de verticale tab-balk — thema-aware.
    - Glassmorphism rechts-zijpaneel (380px breed), identieke stijl als Kaart Configuratie.
    - Actie-knoppen dispatchen `INDICATOR_SELECTED` via EventBus naar kaart én Kompas.
    - `MAAK_RAPPORT`: opent gebiedsdossier of benchmark op basis van huidige kaart-selectie.
- ✅ **Chat↔Kompas Sync** (`static/js/kompas.js`):
    - Kompas luistert naar `INDICATOR_SELECTED` en navigeert automatisch naar het juiste kwadrant.
    - `_isSyncing` guard voorkomt event-loop (Bug #36 gefixt).

---

### Dag 42 (18-03-2026): AI Ontologie Kwaliteitsfix 🧠✨
**Focus:** Implementatie van de "Hek en Bron" filosofie voor prompt engineering en herstel van 51 indicatoren.

- ✅ **"Hek en Bron" Filosofie:** Documentatie van de identiteit-gedreven prompt-strategie (`docs/6-ai-parallel-track/ai-integratie/prompt_engineering_filosofie.md`).
- ✅ **Targeted Re-generatie:** 51 indicatoren met technische ruis (RDF/OWL) succesvol hersteld naar verhalende Nederlandse tekst met het Qwen-30b model.
- ✅ **AI Audit Tooling:** Ontwikkeling van `src/utils/ai_audit.py` voor automatische kwaliteitscontrole van AI-output.

---

### Dag 41 (17-03-2026): CBS 2024 Geografie & ETL Data Gaten 🗺️🔋
**Focus:** Implementatie van de 2024 buurtindeling voor Northern Provinces en het structureel dichten van datagaten voor Smallingerland en De Fryske Marren.

**Resultaten:**
De noordelijke provincies (Fryslân, Groningen, Drenthe) zijn nu volledig "up-to-date" met de nieuwste 2024 grenzen én een diepe historische data-stand (2020–2025).
- **Groningen**: ~65.000 records geïmporteerd.
- **Drenthe**: ~85.000 records geïmporteerd.
- **Totaal Noord-Nederland**: 100% dekking op RIVM en CBS Kerncijfers voor actieve gebieden.
- **Stabiliteit**: De kaart-API is bug-vrij voor records zonder geometrie.

- ✅ **CBS 2024 Boundary Import:** Succesvolle import van buurtgeometrieën voor Fryslân, Groningen en Drenthe uit landelijke GPKG. Resolutie van overlappende geometrieën in Smallingerland door deactivering van verouderde buurtcodes.
- ✅ **Noordelijke Provincies Data-expansie:** RIVM & CBS: Volledige import voor Groningen (10 gemeenten, ~65k records) en Drenthe (12 gemeenten, ~85k records).
- ✅ **ETL Data Gaten gedicht (Fryslân focus):**
    - **PC6 Mapping Update**: Nieuwe `pc6_buurt_mapping.json` op basis van CBS 2025 relatie-tabel (448.646 codes).
    - **RIVM Her-import**: Alle Gezondheidsmonitor data voor Smallingerland gematcht aan de nieuwe 2024 indeling.
    - **BAG & EP-Online**: Bouwjaar, woonoppervlakte en energielabels succesvol geïmporteerd voor Smallingerland en De Fryske Marren.
- ✅ **Kaart-Service Stabiliteit:** Fix voor een kritieke `NULL geometry` fout in de GeoJSON response van de kaart-API (`get_kaart_data_v2`).

---

### Dag 39 (15-03-2026): Sprint 8F — AI Search Navigation & Data Lineage 🧭🤖
**Focus:** Optimalisatie van de AI-zoekervaring, contextualiteit in het Kompas en 100% data coverage.

- ✅ **AI Search Expansion (100% Coverage):** Alle **280 indicatoren** zijn voorzien van een AI-ontologische beschrijving via lokale Ollama inferentie. Vectorisatie voltooid; alle indicatoren semantisch doorzoekbaar via `pgvector`.
- ✅ **Kompas UI & Navigatie:** Contextuele Zoom bij het selecteren van een zoekresultaat; Z-Index reparatie voor tooltips; Stability Fix voor zichtbare viewport.
- ✅ **Data Lineage Fundament:** Introductie van de `bronnen` en `indicator_metadata` tabellen voor volledige herleidbaarheid van data-assets.

---

### Dag 38 (06-03-2026): Bugfix — 3D Extrusie Visualisatie & Belichting 🎮✨
**Focus:** Herstellen van de defecte 3D-weergave van gebieden op de kaart.

- ✅ **Bug #25 Fix:** Introductie van een `onViewStateChange` listener die actief de camerahoek opslaat, zodat het aanvinken van de 3D-toggle de kaart niet meer reset naar de oceaan. Oplossen van triangulatie-artifacten door de 2D en 3D laag-ID's afzonderlijk te benoemen.
- ✅ **Materiaal & Belichtingsfixes:** Verwijdering van defecte FPS-monitor; vervangen van experimentele `_SunLight` door stabiele `DirectionalLight`; matte renderer instellen in 3D.

---

### Dag 37 (05-03-2026): Bugfix — Ngrok Tunneling Compatibiliteit 🔧🌐
**Focus:** Applicatie volledig functioneel maken via ngrok tunneling.

- ✅ **Bug #22 Fix:** Hardcoded `isLocalhost` check verwijderd; universele relatieve URLs.
- ✅ **CORS Regex voor Ngrok:** `allow_origin_regex` accepteert nu automatisch `*.ngrok-free.dev` origins (alleen in DEBUG mode).
- ✅ **Build & Deploy Workflow:** `.agents/workflows/build-admin-panel.md` aangemaakt.

---

### Dag 36 (03-03-2026): Sprint 8E — Kleur-Transformatie "Triple Threat" Palet 🎨
**Focus:** Visuele revisie naar de "Deep Data" identiteit, CSS tokenisatie, map-highlights en light mode optimalisaties.

- ✅ **CSS Tokenisatie:** Uniforme design-tokens (`--brand-main`, `--brand-action`, `--brand-accent`, `--brand-nature`). Sanering van hardcoded `SWF-rood` voor `Trust Blue` en `Nature Green`.
- ✅ **Geïntegreerde Highlights:** Deck.gl map-selecties in `Geo Gold` merk-kleur.
- ✅ **Bugfixes Light Mode (Bug #20 / #21):** Ontbrekende leesbaarheid opgelost.

---

### Dag 35 (02-03-2026): Sprint 8D — Benchmark Kaart-integratie & Bugfixes 🗺️⚖️
**Focus:** Typeahead fixeren, rapport-knop uitbreiden, Benchmark publiek toegankelijk maken.

- ✅ **Bug #17 Fix — Typeahead:** Nieuw `GET /api/gebieden/zoek?q=<term>` endpoint. Debounced search (300ms) vervangt de gebroken pre-load.
- ✅ **BenchmarkPage Upgrade:** URL pre-populatie met area-IDs als queryparams.
- ✅ **Bug #11 Fix — Rapport-knop Modal:** Single selectie: keuze-overlay (📄 Gebiedsdossier / ⚖️ Benchmark). Multi-selectie: direct naar Benchmark.
- ✅ **Bug #18:** Benchmark publiek toegankelijk (ProtectedRoute verwijderd).

---

### Dag 34 (28-02-2026): Sprint 8C — Benchmark Vergelijker & Executive Summary ⚖️📋
**Focus:** Rapportage sjablonen uitbreiden met gebiedsvergelijking en executive summary.

- ✅ **Sjabloon C: Benchmark Vergelijker:** `generate_benchmark_payload()` met 3 vergelijkingsmodi: 1-op-n gebieden (max 5), gemeente-gemiddelde, Fryslân-gemiddelde.
- ✅ **Sjabloon A: Executive Summary:** `generate_executive_payload()` filtert top 3 kansen en top 3 risico's.
- ✅ **LLM Prompt:** Nieuwe `benchmark_vergelijker` system prompt.

---

### Dag 33 (24-02-2026): Sprint 7 — Multi-Gebied Analyse & Kompas Upgrade 📊🗺️
**Focus:** Volledig nieuwe multi-area selectie en vergelijkingsvisualisatie.

- ✅ **Multi-Select op de Kaart:** Shift+Click / Ctrl+Click, floating selectie-badge, groene highlights.
- ✅ **Kompas Aggregatie:** `loadMultiGebiedData()` fetcht parallel + `_mergeHierarchies()` berekent gewogen gemiddelden.
- ✅ **Vergelijkende Barcharts:** Bij multi-select horizontale barcharts per indicator in het detail-paneel.
- ✅ **Wiskundig Fundament:** `scripts/ai/normalisation.py` — veilige Min-Max normalisatie `[0.01, 1.00]`.
- ✅ **Semantisch Vector Zoeken:** PostgreSQL geüpgrade met `pgvector`, cosine similarity queries actief.

---

### Dag 31 (22-02-2026): Rapportage Opschoning & PDF Export 📄✅
**Focus:** Sprint 8B — Afronding functionaliteiten rondom AI-rapportage.

- ✅ **Publieke Toegang & Routing:** Alias `/publiek-rapport` en `/rapport` fallback-ready.
- ✅ **PDF Export & Print CSS:** Verbeterd contrast voor dark-mode tabellen; dynamische bestandsnaamgeneratie.
- ✅ **Data Correcties:** Fix impact-interpretaties voor omgekeerde z-scores; opruimen "spook"-indicatoren.

---

### Dag 28 (20-02-2026): AI Rapportagemodule Backend (Fase 1 & 2) 🤖📄
**Focus:** Sprint 8 — Modulaire API voor Data Aggregatie en Lokale Ollama Integratie.

- ✅ **Fase 1: Data Rekenlaag:** `ReportDataService` berekent on-the-fly Z-scores en gemiddeldes per gebied.
- ✅ **Fase 2: Narrative Engine:** Database migratie `schema_v7_llm_prompts.sql`; nieuwe CRUD Service `/api/admin/prompts`; timeout verhoogd naar 120s voor Qwen3:30b.

---

### Dag 27 (16-02-2026): Data Verificatie & Legend Sync 🔧✨
**Focus:** Sprint 5E — Gemeente data verificatie en Kompas-Legenda synchronisatie.

- ✅ **Gemeente Code Verificatie:** Database codes correct (Smallingerland=0090, De Fryske Marren=1940).
- ✅ **Bug #9 Fixed — Legenda Sync:** Root cause: twee duplicate `updateLegenda()` functies geconsolideerd.

---

### Dag 26 (15-02-2026): Visualisatie Standaard 🎨✨
**Focus:** Sprint 5D — Database-driven color palettes and visualization profiles.

- ✅ **Database Schema v6:** Extended `color_schemas` met palette_type, classificatie, klassen, nodata_kleur. 8 standaard palettes.
- ✅ **Backend Integration:** New `/api/visualisatie` router; `ColorScaleService` met 4 classificatiemethoden.
- ✅ **Admin Panel:** `KleurschemasPage` met live color previews en profile editor.

---

### Dag 25 (15-02-2026): BAG Integratie & Dashboard Finalization 🏘️📊
**Focus:** Afronding BAG Fryslân en Admin Dashboard (Sprint 5C & 5F).

- ✅ **BAG Data Integratie:** 6 Nieuwe indicatoren; ~18k records; 97% dekking.
- ✅ **Admin Dashboard V1.0:** Data Export (CSV) en visualisatie van data quality per kwadrant.

---

### Dag 20 (10-02-2026): Nieuwe Datasets & Metadata 📚✨
**Focus:** Inventarisatie & Documentatie van BAG, Postcodegebieden, en EP-Online.

- ✅ **Uitgebreide Documentatie:** Metadata voor 4 cruciale datasets (BAG, PC4, PC6, EP-Online).
- ✅ **Bugfix Kompas Service:** Robuuste afhandeling van JSON velden (thresholds) voor bredere driver compatibiliteit.

---

### Dag 19 (09-02-2026): Energielabels & Metadata 🏷️⚡
**Focus:** Data dekking en kwaliteit.

- ✅ **Energielabel Import (Heel Friesland):** Streaming XML import van RVO EP-Online (8GB); 100% dekking voor "Gemiddeld energielabel" (was 17%).
- ✅ **Metadata Verrijking:** Automatische koppeling met CBS definities.
- ✅ **Bugfixes:** Kaartlaag API (500 error) gefixt; Data correctie "Huishoudens totaal".

---

### Dag 18 (08-02-2026): RIVM Data & Map Fixes 🏥🛠️
**Focus:** Uitbreiding databronnen en UX bugfixes.

- ✅ **RIVM Data Integratie:** Directe koppeling met RIVM/CBS OData; Import van Gezondheidsmonitor (Roken, BMI, Eenzaamheid) op buurtniveau.
- ✅ **UX Verbeteringen:** Fix voor "dode zone" op kaart onder menu's (`pointer-events` CSS fix).

---

### Dag 14 (01-02-2026): Beheerscherm MVP + Security Foundation 🛠️
**Focus:** Admin Panel voor Kompas beheer.

- ✅ **Backend Admin API:** 6 endpoints: health, score-types, color-schemas, indicatoren, hierarchie/tree. API key authenticatie (`X-Admin-Key` header).
- ✅ **React Admin Panel:** TypeScript + React Router + Zustand state. Login, Dashboard, Indicatoren pagina's. D-OmniTwin matching dark theme styling.
- ✅ **Security Hardening (Punt 0):** Environment variables (`.env`), CORS lockdown, CSP + Security headers.

---

*Sprint Changelog verplaatst vanuit README.md — april 2026*

