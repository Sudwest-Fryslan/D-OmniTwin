# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also: @.claude/soul.md | @.claude/skills.md

## Project Overview

D-OmniTwin is a digital twin platform for Dutch municipalities, visualizing neighborhood-level indicators (Kompas: 217 metrics across 12 thematic quadrants) on interactive maps. Built for Súdwest-Fryslân, it combines geospatial data, AI-powered chat, and multi-area comparative reporting.

- **Backend:** FastAPI (Python 3.9+) on port 8000
- **Main Frontend:** Vanilla JS + Mapbox GL + Deck.gl (no build step, served from `/static/`)
- **Admin Panel:** React 19 + TypeScript SPA in `/admin-panel/` (port 3000 in dev)
- **Database:** PostgreSQL 12+ with PostGIS extension

## Commands

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
npm start        # dev server on port 3000
npm run build    # production build
npm test         # run tests
```

### Database initialization (run in order)
```bash
python scripts/import_gebiedsmonitor_config.py
python scripts/import_geometrie.py
python scripts/import_metingen.py
python scripts/import_kompas_hierarchie.py
python scripts/import_cbs_data.py
```

### ETL
```bash
python ETL/search_api.py   # discover datasets from CBS/RIVM/Politie portals
python ETL/run_etl.py      # extract and import data into PostgreSQL
```

## Environment Setup

Copy `.env.example` to `.env` and fill in:
- `DATABASE_*` — PostgreSQL connection (requires PostGIS extension)
- `MAPBOX_TOKEN` — for map tiles
- `ADMIN_API_KEY` — for admin panel authentication
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

These communicate via a **custom EventBus** (`static/js/core/`) — not via shared state or a framework. When an area is selected on the map, an event fires that kompas.js and chat.js subscribe to.

State is managed through a global `window.state` object (selected areas, active layers, filters).

### Backend Router → Service Pattern
Each API concern has a router in `/routers/` (thin HTTP layer) and a service in `/services/` (business logic):
- `gebiedsmonitor_service.py` — data aggregation, Z-score normalization, color scaling
- `kompas_service.py` — thematic hierarchy aggregation and scoring
- `report_service.py` — multi-area dossier generation with SVG choropleth rendering
- `llm_service.py` — Ollama integration (lazy-loaded, with graceful fallback)
- `ai_search_service.py` — SentenceTransformer semantic search (lazy-loaded on first use)

### Z-Score Calculations
Z-scores are computed dynamically per request, relative to a reference group defined by `gebiedstype` + `gemeente` (not globally). "Water neighborhoods" (watergebieden) are silently excluded from all statistical calculations. This logic lives in `kompas_service.py` and `report_service.py`.

### Authentication
Hybrid model: API key authentication for admin panel API calls, session-based auth for dashboard access. See `routers/auth.py`. The admin panel uses the API key for initial stats and then sessions for full access.

### LLM / AI
- **Chat intent classification is rule-based** (deterministic), not LLM-driven. LLM (Ollama/Qwen, local) is used only for narrative summaries (capped at ~80 words).
- LLM configuration (model, endpoint, prompts) is stored in database tables (`llm_config`, `system_prompts`), not hardcoded.
- `ai_search_service.py` uses SentenceTransformer with locally-computed embeddings. Both services lazy-load to avoid blocking startup.

### Color System
Colorblind-safe diverging palettes are used throughout. Palette definitions live in `static/css/colors/`. Dynamic color generation (including diverging scales) is in `color_scale_service.py`.

### Database
Schema is in `data/schema_latest.sql`. Key tables: `gebieden` (areas/buurten), `indicatoren` (metrics), `gebied_data` (measurements), `kompas_data` (thematic hierarchy). SQLAlchemy uses a large connection pool (`pool_size=20, max_overflow=20`) for concurrent map layer queries.

## Documentation
- `docs/STATE.md` — authoritative system status and component inventory
- `docs/INDEX.md` — documentation router by domain
- `BUILD.md` — full setup instructions
- `ROADMAP.md` — sprint planning
- `TODO.md` — active task list by domain
- `BUGFIX.md` — known bugs and workarounds

## GitHub workflow

Elke wijziging gaat via GitHub Flow:

1. Issue aanmaken op TLaan/D-OmniTwin
2. Branch aanmaken: `feature/<issue-nr>-<korte-naam>`
3. Commits op die branch
4. Pull Request naar `main` met `Closes #<nr>` in de beschrijving
5. Nooit direct op `main` pushen

`gh` CLI staat op: `"/c/Program Files/GitHub CLI/gh.exe"`
