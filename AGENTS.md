# AGENTS.md

Dit is het **enige** bestand met instructies en projectfeiten voor AI-coding-agents (Claude Code, Gemini/Antigravity, Codex, Copilot, of anders) die in deze repository werken. Tool-specifieke bestanden (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) zijn alleen een verwijzing hiernaartoe — wijzig **altijd hier**, nooit in die bestanden, zodat de instructies niet uiteen gaan lopen per tool.

## Context & samenwerking

D-OmniTwin is gestart door Taeke van der Laan (CDO, Súdwest-Fryslân), die actief ontwikkelt via Google Antigravity (Gemini). Eduard Witteveen (Solutions Innovator, SWF) draagt bij vanuit een architectuurrol, met als doel het platform breder inzetbaar te maken dan alleen SWF.

Relevante externe actoren:
- **DataFryslân** — erkende DGA-dataintermediair en coöperatie; centrale governance-actor voor FRLDS-integratie.
- **FRLLLM** — Fryslân Large Language Model; toekomstige optie als federatieve AI-laag naast/boven de lokale Qwen3.
- **Terp 2030** — overarching Fryslân datastrategie waar FRLDS uit voortvloeit; D-OmniTwin positioneert zich daarbinnen.

**Doelbeeld:** D-OmniTwin als gemeentelijk dataspace-platform — van visualisatietool naar regie-, betekenis- en ontsluitingslaag. Metadata, kwaliteit en semantiek zijn eersteklas onderdelen. AI werkt op beheerde informatie. Federatie komt later, maar de architectuur wordt er nu al op voorbereid (GGM, iSHARE, Common Ground, NORA).

### Architectuur-guardrails
- Niets aanpassen aan projectbestanden zonder issue en PR (zie GitHub-workflow hieronder).
- In sync blijven met `docs/STATE.md` — dit is het leidende statusdocument, bijgewerkt na elke sprint.
- Geen koppelingen introduceren die losse deployment van D-OmniTwin moeilijker maken.
- Architectuurkeuzes toetsen aan het doelbeeld: dataspace-platform, bron blijft bron, begrijpbaarheid boven complexiteit.
- D-OmniTwin positioneren als **methodiek + referentie-implementatie**, niet als product of platform — dit bepaalt adoptie buiten SWF.
- Spanningsveld bewaken: "federatie later, architectonisch voorbereid" versus lopende FRLDS-specifieke sprints — geen FRLDS-afhankelijkheden inbouwen die een dataspace-agnostische opzet blokkeren.

### Communicatiestijl
Direct en nuchter, kern eerst, geen omhaal. Lever wat gevraagd wordt, niet meer — als iets schuurt, benoem het kort en los het gericht op. Collegiaal en scherp op inhoud, niet hard op de relatie. Eduard's schrijfstijl: direct, zakelijk, kern vooraan, geen managementtaal.

## Project Overview

D-OmniTwin is a digital twin platform for Dutch municipalities, visualizing neighborhood-level indicators (Kompas: 235 metrics across 12 thematic quadrants) on interactive maps. Built for Súdwest-Fryslân, it combines geospatial data, AI-powered chat, and multi-area comparative reporting.

- **API Gateway:** Traefik on port 80 (Reverse proxy)
- **Main Backend:** FastAPI (Python 3.10+) on port 8000
- **Data API:** PostgREST on port 3000 (`/api/data/*`)
- **Geo API:** pg_featureserv on port 9000 (`/api/geo/*`)
- **Main Frontend:** Vanilla JS + MapLibre GL + Deck.gl (no build step, served from `/static/`)
- **Admin Panel:** React 19 + TypeScript SPA in `/admin-panel/` (port 3001 in dev, built to `/static/admin-panel/`)
- **Database:** PostgreSQL 14+ with PostGIS, pgvector, and pg_trgm extensions

## Commands

### Full Stack (Docker Compose)
```bash
docker compose up -d --build   # dev: laadt ook docker-compose.override.yml (bind-mount, DB op 5433, Traefik-dashboard 8081)
```
Installatie voor beheerders (`COMPOSE_FILE=docker-compose.yml` in `.env`, alleen poort 80 / `OMNITWIN_HTTP_PORT`): zie **`docs/9-beheer/installatie.md`** — de enige actuele installatiegids. Bij de eerste start richt de eenmalige service `db-init` (`docker-entrypoint.sh init`) een lege database in: schema, views, migraties v18/v19/v21, stuurdata, sample (`LOAD_SAMPLE_DATA`) en admin-gebruiker. Een bestaande database (tabel `gebieden` aanwezig) laat hij ongemoeid; schemamigraties op bestaande databases zijn handmatig (#54).

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Start development server (optimized file watching, port 8000)
python run_dev.py

# Run tests
python -m pytest tests/
python -m pytest tests/test_zscore.py   # single test file
```

### Admin Panel (React)
```bash
cd admin-panel
npm install
npm start        # dev server on port 3001
npm run build    # production build (deploy via .agents/workflows/build-admin-panel.md)
npm test         # run tests
```

### Database initialisatie — Fryslân-dataset zonder Docker (verouderd)
```bash
python init_data/scripts/download_buurten_fryslan.py
python init_data/scripts/download_indicatoren_fryslan.py
bash init_data/scripts/init_database.sh   # master initiatie-script, zie init_data/README.md
```
Alleen voor een PostgreSQL zonder Docker (`GETTING_STARTED.md`). Werkt niet tegen de Docker-stack: `init_database.sh` verwacht een `.env` in de container en laadt het schema opnieuw, en `seed_fryslan.py` faalt grotendeels op de database van `db-init` (tabel `gemeenten` bevat alleen 1900). Eén initialisatieroute volgt in #69.

### ETL — doorlopend nieuwe databronnen/gemeenten toevoegen (ná de initiële setup)
```bash
python ETL/search_api.py                     # discovery: welke datasets bestaan bij CBS/RIVM/Politie
python ETL/run_etl.py -ds <dataset_id> -gm <gemeentecode>   # extract + import van één dataset/gemeente
```
Dit framework is **niet** voor de initiële bootstrap (dat is `init_data/`, hierboven) maar voor het uitbreiden met extra gemeenten of databronnen daarna. Zie `ETL/ETL_DOCUMENTATION.md` en `GETTING_STARTED.md` ("Eigen gemeente of regio toevoegen").

> **Let op:** `ETL/local/` bevat een ouder/parallel pipeline-pad (`etl_01..06`, `run_pipeline.py`) dat niet in `GETTING_STARTED.md` staat en vermoedelijk legacy is. Niet gebruiken als startpunt zonder eerst te verifiëren of het nog actief onderhouden wordt.

## Environment Setup

Copy `.env.example` to `.env` and fill in (details: `docs/9-beheer/installatie.md`, sectie 2.2):
- `DATABASE_*` — PostgreSQL connection (requires PostGIS extension). `DATABASE_PASSWORD` alleen letters/cijfers: het komt in database-URL's terecht
- `ADMIN_API_KEY` — for admin panel authentication (`X-Admin-Key`); nooit de voorbeeldwaarde laten staan
- `ADMIN_USER` / `ADMIN_PASSWORD` — eerste beheeraccount; leeg = gegenereerd, eenmalig in `docker compose logs db-init`
- `OLLAMA_*` — for local LLM (optional; Qwen model)

For the admin panel, create `admin-panel/.env` with `REACT_APP_API_URL` and `REACT_APP_ADMIN_KEY`.

## Architecture

### Request Flow
```
Browser (Map click / Chat query)
  → EventBus dispatch (static/js/core/)
  → Fetch to FastAPI router (/routers/)
  → Service layer (/services/) — Z-scores, spatial queries, LLM calls
  → PostgreSQL + PostGIS
  → JSON response → D3 / Deck.gl render
```

### Frontend Architecture (non-obvious)
The main app has **no build step**. `templates/index.html` (Jinja2) loads CDN scripts and the three main JS files:
- `static/js/app.js` (~109KB) — map, layers, area selection, global `window.state`
- `static/js/kompas.js` (~79KB) — D3.js sunburst chart for 12-quadrant Kompas
- `static/js/chat.js` (~18KB) — chat panel with rule-based intent classification

These are large files — wijzig gericht, niet in bulk. They communicate via a **custom EventBus** (`static/js/core/`) — not via shared state or a framework. When an area is selected on the map, an event fires that kompas.js and chat.js subscribe to. State is managed through a global `window.state` object (selected areas, active layers, filters). No frameworks toevoegen.

### Backend Router → Service Pattern
Each API concern has a router in `/routers/` (thin HTTP layer) and a service in `/services/` (business logic). Wijzig zo min mogelijk, gebruik bestaande naamgeving:
- `gebiedsmonitor_service.py` — data aggregation, Z-score normalization, color scaling
- `kompas_service.py` — thematic hierarchy aggregation and scoring
- `report_service.py` — multi-area dossier generation with SVG choropleth rendering
- `llm_service.py` — Ollama integration (lazy-loaded, with graceful fallback)
- `ai_search_service.py` — SentenceTransformer semantic search (lazy-loaded on first use)

### Z-Score Calculations
Z-scores are computed dynamically per request, relative to a reference group defined by `gebiedstype` + `gemeente` (not globally). Eén bron: de SQL-functies in `init_data/schema/08_zscore_referentie.sql` (`zscore_referentie_stats`, `zscore_gebieden`, ...; migratie v21), met parameters en standaardwaarden in `services/zscore_referentie.py`. Waterbuurten (`gebieden.metadata->>'water' = 'JA'`) zitten nooit in de referentie; jaarlogica standaard `zelfde_jaar` (referentie = waarden in het jaar van de meest recente waarde van het doelgebied, zoals executive en Kompas werkten); alleen scenario `current`. Schrijf geen eigen referentie-CTE in `report_service.py` of `kompas_service.py`, gebruik deze functies. Methodiek: `docs/3-data-engineering/zscore_methodiek.md` (#66).

### Authentication
Hybrid model: API key authentication for admin panel API calls, session-based auth for dashboard access. See `routers/auth.py`. The admin panel uses the API key for initial stats and then sessions for full access.

### LLM / AI
- **Chat intent classification is rule-based** (deterministic), not LLM-driven. LLM (Ollama/Qwen, local) is used only for narrative summaries (capped at ~80 words). LLM-config en system-prompts staan in databasetabellen (`llm_config`, `system_prompts`), niet hardcoded.
- `ai_search_service.py` doet semantische zoekopdrachten met `sentence-transformers` (model `all-MiniLM-L6-v2`, lazy-loaded) en `pgvector`: embeddings staan in tabel `indicator_embeddings` (kolom `embedding vector(384)`, HNSW-index met cosine ops), bevraagd via de `<=>`-operator. `kompas_service.py` gebruikt géén vector-zoekopdrachten.

### Color System
Colorblind-safe diverging palettes are used throughout. Palette definitions live in `static/css/colors/`. Dynamic color generation (including diverging scales) is in `color_scale_service.py`.

### Database
Schema is in `init_data/schema/schema_latest.sql`. Key tables: `gebieden` (areas/buurten), `indicatoren` (metrics), `gebied_data` (measurements), `kompas_titels` / `kompas_themas` / `kompas_onderdelen` / `kompas_indicator_mapping` (thematic hierarchy, samengevoegd in view `v_kompas_hierarchie`). In Docker laadt `db-init` dit schema plus `init_data/schema/06_pg_featureserv_views.sql` en `migrations/schema_v18_*.sql`/`schema_v19_*.sql`/`schema_v21_*.sql`. Views zoals `vw_gebied_kaart_basis` gebruiken herkenbare aliassen — geen alias waarbij de tabelnaam niet herkenbaar terugkomt. SQLAlchemy uses a large connection pool (`pool_size=20, max_overflow=20`) for concurrent map layer queries. Let op water-buurt filtering (watergebieden worden uitgesloten van statistiek).

### Admin UI (React/TypeScript)
Aparte codebase in `admin-panel/`, eigen build-stap nodig. API calls via relatieve paden, geproxied naar de backend op poort 8000.

### Data-engineering (ETL)
Scripts in `ETL/` en `scripts/` zijn standalone, geen deel van de web-API. CBS, RIVM, BAG zijn de primaire bronnen. Zie de Commands-sectie hierboven voor het onderscheid tussen initiële bootstrap (`init_data/`) en doorlopende uitbreiding (`ETL/`).

## Documentation
- `docs/STATE.md` — authoritative system status and component inventory (leidend bij tegenstrijdigheden)
- `docs/INDEX.md` — documentation router by domain
- `docs/9-beheer/installatie.md` — **de** installatiegids (Docker), ook voor beheerders
- `GETTING_STARTED.md` — installatie zonder Docker met Fryslân-dataset (verouderd)
- `BUILD.md` — build reference & sprint changelog (installatiedeel verouderd)
- `ROADMAP.md` — sprint planning
- `TODO.md` — active task list by domain
- `BUGFIX.md` — known bugs and workarounds

## Projectmanagement
`docs/STATE.md` is leidend. Na elke sprint bijwerken: versie, actieve componenten, recente wijzigingen, issues, roadmap.

## GitHub workflow

Elke wijziging gaat via GitHub Flow:

1. Issue aanmaken op TLaan/D-OmniTwin
2. Branch aanmaken: `feature/<issue-nr>-<korte-naam>`
3. Commits op die branch
4. Pull Request naar `main` met `Closes #<nr>` in de beschrijving
5. Nooit direct op `main` pushen

`gh` CLI: `/usr/bin/gh` — gebruik altijd met `GH_PAGER=cat` om pager-blokkering te voorkomen.
