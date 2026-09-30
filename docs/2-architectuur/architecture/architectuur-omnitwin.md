# D-OmniTwin — Systeem Architectuur
**Versie:** 2.2.0 | **Sprint:** 11 | **Datum:** 27 maart 2026  
**Status:** 🟡 MEDIUM RISK — API key auth, CORS locked, Security headers actief

---

## 1. Overzicht

D-OmniTwin ("The Omni Twin") is een **digitale spiegel van de fysieke leefomgeving**. De applicatie combineert geografische datavisualisatie, een AI-gedreven chat-assistent en een beheerpaneel voor Noord-Nederland (Fryslân, Groningen, Drenthe). De kern is een interactieve kaart met een Kompas-visualisatie van 217 indicatoren verdeeld over 12 thema's, op buurtniveau.

---

## 2. Systeem Componenten

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER (Gebruiker)                                                    │
│                                                                         │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Kaart        │  │  D-Omni Kompas   │  │  AI Chat Zijpaneel       │  │
│  │  deck.gl      │  │  D3.js Sunburst  │  │  ChatPanel (chat.js)     │  │
│  │  Mapbox GL    │  │  12 thema's      │  │  Glassmorphism UI        │  │
│  │  app.js       │  │  217 indicatoren │  │  Actie-knoppen           │  │
│  └──────┬────────┘  └────────┬─────────┘  └────────────┬─────────────┘  │
│         │                   │                          │                │
│         └─────────── EventBus (event-bus.js) ──────────┘                │
│                      pub/sub | INDICATOR_SELECTED                       │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ HTTP/REST
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FASTAPI BACKEND (Python 3.12 | Uvicorn | Port 8000)                    │
│                                                                         │
│  main.py — Security Middleware, CORS, Router registratie                │
│                                                                         │
│  ┌──────────────────────────── ROUTERS ──────────────────────────────┐  │
│  │ gebiedsmonitor.py  kompas.py      report.py                       │  │
│  │ gemeenten.py       visualisatie.py admin.py     auth.py           │  │
│  │ chat.py            ai_search.py   llm_prompts.py dashboard.py     │  │
│  │ data_controle.py                                                  │  │
│  └──────────────────────────── SERVICES ─────────────────────────────┘  │
│  │ gebiedsmonitor_service.py   kompas_service.py                     │  │
│  │ llm_service.py              report_service.py                     │  │
│  │ ai_search_service.py        color_scale_service.py                │  │
│  │ data_controle_service.py                                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ SQLAlchemy + psycopg2
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL 14+ | PostGIS | pgvector)                         │
│                                                                         │
│  gebieden      indicatoren     indicator_embeddings (vector(384))       │
│  indicator_waarden             kompas_hierarchie                        │
│  color_schemas  visualisatie_profielen  llm_config   system_prompts     │
│  bronnen        indicator_metadata      data_controle                   │
└─────────────────────────────────────────────────────────────────────────┘
                      │                              │
          ┌───────────┘                    ┌─────────┘
          ▼                                ▼
┌─────────────────────┐        ┌─────────────────────────┐
│  LOKALE AI (Ollama) │        │  ADMIN PANEL (React)    │
│  qwen3:30b          │        │  TypeScript + React 18  │
│  Port 11434         │        │  React Router v6        │
│  Narrative gen.     │        │  Zustand (state)        │
│                     │        │  Port 3000 (dev)        │
│  SentenceTransformer│        │  Gebouwd naar:          │
│  all-MiniLM-L6-v2   │        │  static/admin-panel/    │
│  384-dim vectors    │        │  Geserved via FastAPI   │
└─────────────────────┘        └─────────────────────────┘
```

---

## 3. Frontend — Browser Laag

### 3.1 Hoofdapplicatie (`static/js/app.js` — ~2200 regels)
- **Mapbox GL JS** — Basiskaart rendering (satelliet/straat stijlen)
- **deck.gl** — 3D/2D polygon overlay voor buurt-datavisualisatie
  - `GeoJsonLayer` voor 2D choropleth
  - `PolygonLayer` voor 3D extrusie (toggle)
  - `onViewStateChange` listener — camera-positie preserve bij 3D toggle
- Multi-gebied selectie via **Shift+Click** / **Ctrl+Click**
- **Legenda** — dynamisch op basis van kleurschema uit database
- Floating selectie-badge met gebied-teller

### 3.2 D-Omni Kompas (`static/js/kompas.js` — ~1926 regels)
- **D3.js** — Sunburst-diagram met hiërarchie van 12 thema's & 217 indicatoren
- `loadMultiGebiedData()` — parallelle data fetch + `_mergeHierarchies()` voor gewogen gemiddelden
- `navigateToIndicator(uuid)` — contextuele zoom naar thema-niveau
- `_isSyncing` guard — EventBus loop-preventie (Bug #36)

### 3.3 AI Chat Zijpaneel (`static/js/chat.js`)
- Vanilla JS `ChatPanel` klasse — geen framework
- Glassmorphism styling, 380px breed, thema-aware
- Beheert state: `isOpen`, `isLoading`
- Laat kaartcontext mee bij API call (`huidig_gebied_id`, `huidige_indicator_uuid`)

### 3.4 EventBus (`static/js/core/event-bus.js`)
- Globale pub/sub singleton — ontkoppelt alle frontend componenten
- Centraal event: **`INDICATOR_SELECTED`** — chat → kaart → Kompas
- Additionele events: `SELECTEER_GEMEENTE`, `SELECTEER_GEBIEDSTYPE`, `OPEN_KOMPAS`

### 3.5 Draggable Window (`static/js/draggable-window.js`)
- Herbruikbare drag-functionaliteit voor Kompas-venster en overige panelen

---

## 4. Backend — FastAPI Laag

### 4.1 Applicatie Entry Point (`main.py`)
| Component | Bibliotheek |
|-----------|-------------|
| Web framework | `FastAPI 0.128.0` |
| ASGI server | `Uvicorn 0.40.0` |
| ORM | `SQLAlchemy 2.0.45` |
| DB driver | `psycopg2-binary 2.9.11` |
| Templates | `Jinja2 3.1.6` |
| Env vars | `python-dotenv 1.2.1` |
| Data validation | `Pydantic 2.12.5` |

**Security middleware:**
- `SecurityHeadersMiddleware` — CSP, X-Frame-Options, XSS-Protection, Referrer-Policy
- `CORSMiddleware` — gelocked op `CORS_ORIGINS` env var; ngrok-regex in DEBUG mode
- Swagger UI wordt lokaal geserved (geen externe CDN)

### 4.2 Routers (API Endpoints)

| Router | Prefix | Toegang | Kernfunctie |
|--------|--------|---------|-------------|
| `gebiedsmonitor.py` | `/api/gebiedsmonitor` | Publiek | Gebieden & indicator waarden |
| `kompas.py` | `/api/kompas` | Publiek | Hiërarchie, configuraties, multi-gebied |
| `gemeenten.py` | `/api/gemeenten` | Publiek | Gemeenten + typeahead zoek |
| `chat.py` | `/api/chat` | Publiek | D-Omni AI Chat (POST) |
| `ai_search.py` | `/api/search` | Publiek | Semantisch zoeken |
| `report.py` | `/api/report` | Publiek | Gebiedsdossier + Benchmark |
| `visualisatie.py` | `/api/visualisatie` | Publiek + Admin | Kleurschema's & profielen |
| `auth.py` | `/api/auth` | Publiek | Admin login/token |
| `admin.py` | `/api/admin` | 🔐 X-Admin-Key | Indicator CRUD, health |
| `llm_prompts.py` | `/api/admin/prompts` | 🔐 X-Admin-Key | System prompt beheer |
| `dashboard.py` | `/api/admin/dashboard` | 🔐 X-Admin-Key | Stats & overzicht |
| `data_controle.py` | `/api/data-controle` | 🔐 X-Admin-Key | Data kwaliteitscheck |

### 4.3 Services

| Service | Kernbibliotheek | Functie |
|---------|-----------------|---------|
| `gebiedsmonitor_service.py` | SQLAlchemy, GeoAlchemy2 | Gebieden, waarden, scores |
| `kompas_service.py` | SQLAlchemy, numpy | Hiërarchie, Z-scores, aggregatie |
| `llm_service.py` | requests (Ollama REST) | Narrative generatie via qwen3:30b |
| `ai_search_service.py` | sentence-transformers, pgvector | Semantisch zoeken indicatoren |
| `report_service.py` | SQLAlchemy, numpy | Z-scores, benchmark payloads |
| `color_scale_service.py` | numpy | Kleurclassificatie (min-max, jenks) |
| `data_controle_service.py` | SQLAlchemy | Data kwaliteitsrapport |

---

## 5. AI & Zoeken

### 5.1 Semantisch Zoeken (Vector Search)
```
Gebruikersvraag → SentenceTransformer (all-MiniLM-L6-v2, 384-dim)
               → pgvector cosine similarity query (indicator_embeddings)
               → Top 10 meest relevante indicatoren (score > 0.25)
```
- Model: `all-MiniLM-L6-v2` (~28MB, lokaal, lazy-loaded)
- Index: `ivfflat (vector_cosine_ops)` in PostgreSQL
- Inferentietijd: 50–150ms per query

### 5.2 LLM Narrative Generatie (Ollama)
```
Indicator context → System Prompt (uit DB: llm_config / system_prompts)
                → Ollama REST API → qwen3:30b
                → ≤80 woorden Nederlandse toelichting
```
- Latentie: 2–15s (afhankelijk van warm/cold start)
- Timeout: 120s
- Lazy loading: model wordt pas geladen bij eerste chat-request (30% snellere server start)

### 5.3 Intent Classifier
Rule-based regex classifier (< 1ms):

| Intent | Trigger-woorden | Actie |
|--------|-----------------|-------|
| `VERKEN_INDICATORS` | groen, leefbaarheid, zorg... | Toont indicatoren op kaart + Kompas |
| `VERGELIJK_GEBIEDEN` | vergelijk, benchmark, verschil... | Opent Benchmark pagina |
| `MAAK_RAPPORT` | rapport, dossier, exporteer... | Opent gebiedsdossier of benchmark |
| `SELECTEER_GEMEENTE` | ga naar, toon, open... | Selecteert gemeente op kaart |
| `ALGEMEEN` | overige vragen | Narratief antwoord |

### 5.4 AI Chat Flow (end-to-end)

```
Gebruiker typt vraag
        │ POST /api/chat (+kaartcontext)
        ▼
Intent Classifier [<1ms]
        │
        ├──→ AISearchService → pgvector → Top 10 indicatoren [50-150ms]
        │
        ├──→ LLMService → Ollama qwen3:30b → ≤80w Nederlandse tekst [2-15s]
        │
        └──→ Actie-knoppen genereren [<1ms]
                │ ChatResponse JSON
                ▼
        ChatPanel rendert response
                │ Gebruiker klikt actie-knop
                ▼
        EventBus.emit('INDICATOR_SELECTED', {uuid})
                │
        ┌───────┴──────────┐
        ▼                  ▼
   app.js (kaart)    kompas.js
   laadt GeoJSON     zoomt naar node
                     (_isSyncing guard)
```

---

## 6. Database Laag

### 6.1 Stack
- **PostgreSQL 14+** met **PostGIS** (geometrie) en **pgvector** (vector search)
- ORM: SQLAlchemy 2.0 + GeoAlchemy2
- Geographisch: WGS84 / EPSG:4326

### 6.2 Kerntabellen

| Tabel | Inhoud |
|-------|--------|
| `gebieden` | Buurten, wijken, gemeenten (CBS 2024 grenzen) |
| `indicatoren` | 217+ indicatoren met ontologische beschrijvingen |
| `indicator_waarden` | Historische waarden per gebied (2020–2025) |
| `indicator_embeddings` | pgvector(384) voor semantisch zoeken |
| `kompas_hierarchie` | 12 thema's → kwadrant → indicator boom |
| `color_schemas` | 8 palet types (sequential, diverging, specialised) |
| `visualisatie_profielen` | Pattern matching: indicator → kleurpalet auto-mapping |
| `llm_config` | Ollama host, model naam (runtime configureerbaar) |
| `system_prompts` | Dynamische LLM prompt sjablonen |
| `bronnen` | Data lineage — herkomst van elke dataregel |
| `indicator_metadata` | Uitgebreide metadata per indicator |

### 6.3 Beschrijvingsprioriteit (AI Search)
```
1. ontologische_beschrijving   ← menselijk gevalideerd (hoogste kwaliteit)
2. beschrijving_ai             ← AI-gegenereerd (Qwen3:30b, "Hek en Bron" filosofie)
3. omschrijving                ← standaard technische omschrijving (fallback)
```

---

## 7. Admin Panel

- **Stack:** React 18 + TypeScript + React Router v6 + Zustand
- **Authenticatie:** `X-Admin-Key` header (API key uit `.env`)
- **Build:** `npm run build` → `static/admin-panel/` → geserved door FastAPI
- **Routing:** FastAPI catchall `/admin/{catchall:path}` → React SPA

### Pagina's
| Pagina | Route | Functie |
|--------|-------|---------|
| Login | `/admin/login` | API key invoer |
| Dashboard | `/admin/dashboard` | Stats, kompas-hiërarchie, kwaliteitsrapport |
| Indicatoren | `/admin/indicatoren` | CRUD: naam, omschrijving, score_type, kleurschema |
| Kleurschema's | `/admin/kleurschemas` | Live color picker + gradient preview |
| LLM Config | `/admin/llm-config` | Ollama host/model configuratie |
| Prompts | `/admin/prompts` | System prompt beheer |
| Rapport | `/admin/rapport` | Gebiedsdossier (PDF export) |
| Benchmark | `/admin/rapport/benchmark` | Gebiedsvergelijker (publiek toegankelijk) |

---

## 8. Rapportage Module

### Rapport Types
| Type | Endpoint | Beschrijving |
|------|----------|-------------|
| **Gebiedsdossier** | `GET /api/report/data/{gebied_id}` | Z-scores, kansen & risico's per buurt |
| **Narrative** | `GET /api/report/narrative/{gebied_id}` | LLM AI samenvatting |
| **Executive** | `GET /api/report/executive/{gebied_id}` | Top 3 kansen + top 3 risico's |
| **Benchmark** | `GET /api/report/benchmark` | 1-op-n vergelijking + gemeente/prov. gemiddelde |
| **Benchmark Narrative** | `GET /api/report/benchmark/narrative` | LLM vergelijkende analyse |

- **PDF Export:** React print handler met dynamische bestandsnaam + @media print CSS
- **Z-score methode:** Min-Max normalisatie `[0.01, 1.00]` (script: `scripts/ai/normalisation.py`)

---

## 9. Security

| Maatregel | Status | Detail |
|-----------|--------|--------|
| Environment secrets | ✅ Actief | `.env` — nooit in git |
| CORS lockdown | ✅ Actief | `CORS_ORIGINS` env var; ngrok regex in DEBUG |
| Security headers | ✅ Actief | CSP, X-Frame-Options, XSS-Protection, Referrer-Policy |
| API key auth (Admin) | ✅ Actief | `X-Admin-Key` header voor alle `/api/admin` routes |
| Swagger lokaal | ✅ Actief | Geen externe CDN voor API docs |
| Database SSL/TLS | ⏳ Gepland | Nog niet geconfigureerd |
| HTTPS/TLS proxy | ⏳ Gepland | Fase 1 (bijv. Nginx reverse proxy) |
| Gebruikers-authenticatie | ⏳ Gepland | Fase 2 (JWT of OAuth2) |

---

## 10. ETL & Data Bronnen

| Bron | Type | Inhoud |
|------|------|--------|
| **CBS Kerncijfers Wijken & Buurten** | OData API | Sociaal-economische indicatoren |
| **CBS 2024 Gebiedsgrenzen** | GPKG | Buurtpolygonen (WGS84) |
| **RIVM Gezondheidsmonitor** | OData API | Gezondheidsdata (roken, BMI, eenzaamheid) |
| **BAG (Basisadministratie Adressen)** | XML/CSV | Bouwjaar, woonoppervlak, woonfunctie |
| **EP-Online (RVO)** | Streaming XML (8GB) | Energielabels — 100% dekking Fryslân |
| **CBS PC6-Buurt Relatie** | CSV (448k codes) | Postcode → buurt koppeling |

**Dekking Noord-Nederland:**
- Fryslân: 100% (2020–2025, CBS 2024 grenzen)
- Groningen: ~65.000 records
- Drenthe: ~85.000 records

---

## 11. Development Setup

### Vereisten
- Python 3.12+, Node.js 18+, PostgreSQL 14+ + PostGIS + pgvector
- Ollama lokaal draaiend op `http://localhost:11434`

### Starten
```bash
# Backend
source .venv/bin/activate && python run_dev.py   # Port 8000

# Admin Panel (dev)
cd admin-panel && npm start                       # Port 3000

# Admin Panel (productie build)
cd admin-panel && npm run build                   # → static/admin-panel/
```

### Configuratie (.env)
```
DATABASE_HOST / PORT / NAME / USER / PASSWORD
SECRET_KEY
CORS_ORIGINS
MAPBOX_TOKEN
ADMIN_API_KEY
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:30b
DEBUG=false
```

---

## 12. Bibliotheek Referentie (volledig)

### Backend Python
| Bibliotheek | Versie | Rol |
|-------------|--------|-----|
| fastapi | 0.128.0 | Web framework |
| uvicorn | 0.40.0 | ASGI server |
| sqlalchemy | 2.0.45 | ORM |
| geoalchemy2 | 0.18.1 | Geometrie kolommen |
| psycopg2-binary | 2.9.11 | PostgreSQL driver |
| pydantic | 2.12.5 | Data validatie |
| jinja2 | 3.1.6 | HTML templates |
| python-dotenv | 1.2.1 | Environment variabelen |
| sentence-transformers | (lokaal) | all-MiniLM-L6-v2 embeddings |
| requests | 2.32.5 | Ollama REST client |
| geopandas | 1.1.2 | ETL geodata verwerking |
| shapely | 2.1.2 | Geometrie operaties |
| numpy | 2.4.1 | Numerieke berekeningen |
| pandas | 2.3.3 | Data manipulatie |
| starlette | 0.50.0 | ASGI middleware basis |

### Frontend JavaScript (CDN / lokaal)
| Bibliotheek | Rol |
|-------------|-----|
| deck.gl | 3D/2D polygon kaartlagen |
| Mapbox GL JS | Basiskaart rendering |
| D3.js | Sunburst Kompas visualisatie |
| Chart.js | Barcharts multi-gebied vergelijking |
| Lucide Icons | UI iconen |

### Admin Panel (React)
| Bibliotheek | Rol |
|-------------|-----|
| React 18 | UI framework |
| TypeScript | Type-safe development |
| React Router v6 | Client-side routing |
| Zustand | State management |

### Database Extensies
| Extensie | Functie |
|----------|---------|
| PostGIS | Geometrie opslag & queries |
| pgvector | Vector similarity search (384-dim) |

---

## 13. Bekende Gaps & Risico's

| # | Type | Omschrijving | Prioriteit |
|---|------|-------------|-----------|
| G1 | Security | Database SSL/TLS niet geconfigureerd | 🔴 High |
| G2 | Security | Geen HTTPS/TLS reverse proxy | 🔴 High |
| G3 | Security | Admin authenticatie via enkelvoudige API key (geen JWT/refresh) | 🟡 Medium |
| G4 | Reliability | Ollama single point of failure — geen fallback LLM | 🟡 Medium |
| G5 | Performance | LLM latentie 2–15s per chat request (geen streaming) | 🟡 Medium |
| G6 | Functionaliteit | Executive Summary frontend pagina ontbreekt | 🟢 Low |
| G7 | Data | Legenda kleurbalk matcht indicator palette niet altijd (hardcoded gradient) | 🟢 Low |
| G8 | Monitoring | Geen structured logging / APM tooling | 🟡 Medium |
| G9 | Testing | Minimale test coverage (alleen `test_canvas.py`, `test_zscore.py`) | 🟡 Medium |

---

*Gegenereerd door: Technisch-Communicatie-Assistent (SKILL.md)*  
*Bronnen: README.md, main.py, routers/*, services/*, admin-panel/src, requirements.txt*
