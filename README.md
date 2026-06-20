# D-OmniTwin 🌍🔐
> Digitale spiegel van de fysieke leefomgeving — open source, federatief, dataspace-ready

**Versie:** v1.0.0-beta (pre-release) | **Laatste update:** 20 juni 2026 | **Status:** 🟡 MEDIUM RISK  
**Security:** API key auth actief, CORS locked, Security headers actief  
[![Licentie: EUPL 1.2](https://img.shields.io/badge/Licentie-EUPL_1.2-blue)](./LICENSE) [![Docs: CC BY 4.0](https://img.shields.io/badge/Docs-CC_BY_4.0-green)](./LICENSE-DOCS)

---

## 🌐 Wat is D-OmniTwin?

Gemeenten en provincies staan voor complexe leefomgevingsopgaven — van energietransitie en klimaatadaptatie tot sociale cohesie en brede welvaart. Data is vaak aanwezig, maar versnipperd over organisaties en systemen. D-OmniTwin biedt een **holistisch beeld van de buitenwereld**: een interactieve digitale spiegel van de fysieke leefomgeving, ontworpen voor integraal beleid en gebiedsontwikkeling.

Via een interactief **D-Omni Kompas** — een D3.js sunburst-visualisatie met 217 indicatoren over 12 thema's — wordt data op buurtniveau direct inzichtelijk voor beleidsmakers, wijkfunctionarissen en inwoners. Een lokale AI-assistent (geen cloud-afhankelijkheid) vertaalt complexe datasets naar begrijpelijke inzichten in gewone taal.

D-OmniTwin fungeert als **dataspace-agnostische interactielaag**: data blijft bij de bron, beveiligd via iSHARE-autorisatie, in lijn met Gaia-X principes en de Fryslân Data Space (FRLDS).

### Typische use cases
- 🔥 **Energietransitie & Energiearmoede** — energielabels, EP-Online, BAG op buurtniveau
- 🌡️ **Klimaatadaptatie (hittestress)** — combinatie van groen, verharding en gezondheidsdata
- 📊 **Brede Welvaart** — integraal overzicht van sociaal-economische en leefbaarheidsdata
- 🤝 **Sociale Cohesie** — gezondheidsmonitor, eenzaamheid, buurtbetrokkenheid

**Dekkingsgebied:** Noord-Nederland — Fryslân, Groningen, Drenthe — 49 gemeenten, ~217 indicatoren op CBS-buurtniveau (2020–2025).

---

## 🤝 Innovatie & Samenwerking

D-OmniTwin wordt ontwikkeld als **open methodiek + referentie-implementatie** (EUPL licentie), met structurele samenwerking tussen overheden en datapartners in Fryslân.

### Samenwerkingspartners

| Partner | Rol |
|---------|-----|
| **Gemeente Súdwest-Fryslân** | Initiatiefnemer & inhoudelijk opdrachtgever |
| **Gemeente Leeuwarden** | Pilotgemeente & praktijkcontext |
| **Gemeente Tytsjerksteradiel** | Pilotgemeente & praktijkcontext |
| **Coöperatie DataFryslân** | Dataspace-partner (FRLDS / iSHARE) |

### Innovatiesubsidie 2026

D-OmniTwin heeft een aanvraag lopen voor het **Innovatiebudget Digitale Overheid 2026** (looptijd sept. 2026 – aug. 2027, totaal €300.000). Doel: doorontwikkeling van de huidige referentie-implementatie naar een **gevalideerde federatieve voorziening** gekoppeld aan de Fryslân Data Space en het Federatief Datastelsel.

Vier use cases worden gevalideerd in pilots bij drie gemeenten. Resultaat: open source codebase, governance-model en herhaalbare methodiek voor andere regio's.

> **🤝 Interesse in samenwerking of pilotdeelname?**  
> Open een [discussie op GitHub](../../discussions) of neem direct contact op:  
> 📧 **[t.vanderlaan@sudwestfryslan.nl](mailto:t.vanderlaan@sudwestfryslan.nl)** 
> 🔗 Zie ook: [communicatieplan_subsidie_2026.md](./docs/8-communicatie/communicatieplan_subsidie_2026.md)

---

## 🧩 Componenten Overzicht

| Component | Technologie | Port | Status |
|-----------|-------------|------|--------|
| **Main App** | FastAPI + deck.gl + D3.js | 8000 | ✅ Production Ready |
| **Admin Panel** | React + TypeScript | 3000 | ✅ MVP Ready |
| **Database** | PostgreSQL + PostGIS + pgvector | 5432 | ✅ Operationeel |

### Main App Features
- 🗺️ **Interactieve Kaart** — Mapbox + deck.gl 3D visualisatie, choropleth op buurtniveau
- 🧭 **D-Omni Kompas** — D3.js sunburst met 12 thema's, 217 indicatoren, multi-gebied aggregatie
- 📊 **Multi-Gebied Analyse** — Shift+Click selectie of via Omgevingsvisie-deelgebieden, Z-score rapportage
- 🗺️ **Externe Kaartlagen & Selectie** — Dynamische externe bronnen (zoals BAG Woonplaatsen en de Omgevingsvisie) met klik-selectie buffer.
- 🤖 **D-Omni Assistent** — Intent-based AI chat interface (lokale Ollama, geen cloud)
- 🎨 **Classic Premium UI** — Dark theme met gradient accents, glassmorphism panelen

### Admin Panel Features
- 🔐 **API Key Auth** — Beveiligde toegang tot beheer
- ✏️ **Indicator Editor** — Bewerk naam, omschrijving, score type, kleurschema
- 📈 **Dashboard** — Stats en Kompas hiërarchie overzicht
- 📄 **Multi-Gebiedsdossier** — D3-stijl react rapportmodule voor multi-selectie van buurten (PDF export)
- 🗺️ **Externe Lagen Beheer** — Configuratie van WFS-bronnen en lokale uploads (GPKG).
- 🤖 **LLM Config** — Ollama host/model configureerbaar via UI

---

## 🏗️ Architectuur Overzicht

### Systeem Stack

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
│  Routers: gebiedsmonitor · kompas · kaart_v2 · report · gemeenten       │
│           visualisatie · admin · auth · chat · ai_search · dashboard    │
│                                                                         │
│  Services: gebiedsmonitor · kompas · llm · report · ai_search           │
│            color_scale · data_controle                                  │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ SQLAlchemy + psycopg2
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL 14+ | PostGIS | pgvector)                         │
│                                                                         │
│  gebieden · indicatoren · indicator_embeddings (vector 384-dim)         │
│  indicator_waarden · kompas_hierarchie · color_schemas                  │
│  visualisatie_profielen · llm_config · system_prompts                   │
│  bronnen · indicator_metadata · data_controle                           │
└──────────────────────┬──────────────────────────────┬───────────────────┘
                       ▼                              ▼
         ┌─────────────────────┐        ┌─────────────────────────┐
         │  LOKALE AI (Ollama) │        │  ADMIN PANEL (React)    │
         │  qwen3:30b          │        │  TypeScript + React 18  │
         │  SentenceTransformer│        │  Zustand state mgmt     │
         │  all-MiniLM-L6-v2   │        │  Gebouwd → static/      │
         │  384-dim vectors    │        │  admin-panel/           │
         └─────────────────────┘        └─────────────────────────┘
```

> 📐 Zie [ARCHITECTURE_TECHNICAL_OPERATION.md](./ARCHITECTURE_TECHNICAL_OPERATION.md) voor de volledige technische specificatie.

---

## 🤖 D-Omni Assistent — Lokale AI

D-OmniTwin bevat een ingebouwde AI-assistent die werkt als een **"alternatieve muis"**: de gebruiker stelt in gewone taal een vraag, en de assistent stuurt de kaart, het Kompas en de rapportage aan — zonder cloud-afhankelijkheid.

### AI Chat Architectuur

```
┌─────────────────────────────────────────────────────────┐
│  Gebruiker                                              │
│  "Welke buurten hebben weinig groen?"                   │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /api/chat
┌──────────────────────▼──────────────────────────────────┐
│  Intent Router  (routers/chat.py)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Intent Classifier (rule-based, <1ms)           │    │
│  │  VERKEN_INDICATORS │ VERGELIJK_GEBIEDEN         │    │
│  │  MAAK_RAPPORT      │ ALGEMEEN                   │    │
│  └──────────────┬──────────────────────────────────┘    │
│                 │                                       │
│  ┌──────────────▼──────────┐  ┌──────────────────────┐  │
│  │  AISearchService        │  │  LLMService          │  │
│  │  pgvector similarity    │  │  Ollama qwen3:30b    │  │
│  │  ≤10 indicatoren        │  │  ≤80 woorden NL      │  │
│  └──────────────┬──────────┘  └──────────┬───────────┘  │
│                 └──────────────┬─────────┘              │
│                                │ Command Dispatch JSON  │
└────────────────────────────────┼────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────┐
│  ChatPanel  (static/js/chat.js)                         │
│  Narrative tekst + Actie-knoppen + Indicatorlijst       │
│               │ INDICATOR_SELECTED    │ MAAK_RAPPORT    │
│          EventBus                EventBus               │
│        ┌──────▼──────┐        ┌───────▼─────────┐       │
│        │  Kaart      │        │  Rapport Admin  │       │
│        │  (app.js)   │        │  /admin/rapport │       │
│        └──────┬──────┘        └─────────────────┘       │
│               │ INDICATOR_SELECTED (_isSyncing guard)   │
│        ┌──────▼───────┐                                 │
│        │  Kompas      │  navigateToIndicator(uuid)      │
│        │  (kompas.js) │                                 │
│        └──────────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

### Intent Types

| Intent | Trigger-woorden | Acties |
|--------|-----------------|--------|
| `VERKEN_INDICATORS` | groen, leefbaarheid, kinderdagverblijf... | Toont indicatoren op kaart + Kompas |
| `VERGELIJK_GEBIEDEN` | vergelijk, benchmark, verschil... | Opent Benchmark pagina met selectie |
| `MAAK_RAPPORT` | rapport, dossier, exporteer... | Opent gebiedsdossier of benchmark |
| `SELECTEER_GEMEENTE` | ga naar, toon, open... | Selecteert gemeente op kaart |
| `ALGEMEEN` | alle andere vragen | Narratief antwoord zonder acties |

### Technische Details

- **LLM:** Lokale [Ollama](https://ollama.ai/) instantie met `qwen3:30b` (configureerbaar via Admin Panel)
- **Vector Search:** `pgvector` (cosine similarity) op `indicator_embeddings` tabel, 384-dim
- **Beschrijvingsprioriteit:** menselijk gevalideerd → AI-gegenereerd → standaard omschrijving
- **Chat Zijpaneel:** Vanilla JS `ChatPanel` klasse, glassmorphism styling, thema-aware
- **EventBus:** Ontkoppeld commando-systeem — chat spreekt nooit direct met kaart of Kompas

### AI Instellen

```bash
# Ollama starten (vereist)
ollama serve
ollama pull qwen3:30b  # of een kleiner model indien gewenst

# Configureerbaar via Admin Panel → LLM Config
# OF via environment variabelen (fallback):
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:30b
```

---

## ✅ Recent Voltooid

> Laatste drie sprints — zie [BUILD.md → Sprint Changelog](./BUILD.md#-sprint-changelog) voor het volledige dag-voor-dag overzicht.

| Sprint | Datum | Kernpunten |
|--------|-------|------------|
| **Sprint 18** | 08-06-2026 | 🗺️ **Externe Kaartlagen & Uploads (Track B)** — BAG Woonplaatsen via WFS (PDOK) geïntegreerd. Lokale (GPKG/GeoJSON) geodata uploads via Admin paneel. |
| **Issue #11** | 07-06-2026 | 🚌 **OV Haltes ETL** — Nieuwe data-pipeline voor OV-haltes in FR/GR/DR met 5 nieuwe Kompas-indicatoren (Bereikbaarheid). |
| **Sprint 17** | 26-05-2026 | 📝 **Configureerbare Logging Infrastructuur** — AsyncLogQueue, 9 categorieën en een In-App Log Viewer in het Admin paneel. |

---

## 🚀 Snel Opstarten

> 📖 **Volledige gids:** Zie [`GETTING_STARTED.md`](./GETTING_STARTED.md) voor een stap-voor-stap installatie inclusief starter dataset.

### Prerequisites
- Python 3.12+ · Node.js 18+ · PostgreSQL 14+ (PostGIS + pgvector)
- [Ollama](https://ollama.ai/) — optioneel, alleen voor AI-functies

### Snelstart
```bash
# 1. Klonen & omgeving instellen
git clone <repo-url> && cd D-OmniTwin
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # vul DATABASE_*, SECRET_KEY, MAPBOX_TOKEN in

# 2. Database aanmaken
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'jouw-wachtwoord';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION postgis; CREATE EXTENSION vector;"

# 3. Buurten extraheren (lokale GPKG → GeoJSON) + CBS data downloaden
python init_data/scripts/extract_buurten_fryslan.py
python init_data/scripts/download_indicatoren_fryslan.py
bash init_data/scripts/init_database.sh

# 4. App starten
source .venv/bin/activate && python run_dev.py
```

**Toegang:**
- 🌐 **App:** http://localhost:8000
- 📚 **API Docs:** http://localhost:8000/docs
- 🔐 **Admin Panel:** `cd admin-panel && npm install && npm start` → http://localhost:3000/admin

> [!TIP]
> **Waarom `run_dev.py`?** Slimmer dan standaard uvicorn: lazy loading van AI-modellen (30% snellere start) en optimized reload die `node_modules` uitsluit.

---

## 🔒 Security

| Maatregel | Status | Detail |
|-----------|--------|--------|
| Environment secrets | ✅ Actief | `.env` — nooit in git |
| CORS lockdown | ✅ Actief | `CORS_ORIGINS` env var; ngrok regex in DEBUG mode |
| Security headers | ✅ Actief | CSP, X-Frame-Options, XSS-Protection, Referrer-Policy |
| API key auth (Admin) | ✅ Actief | `X-Admin-Key` header voor alle `/api/admin` routes |
| Swagger lokaal geserved | ✅ Actief | Geen externe CDN voor API docs |
| Database SSL/TLS | ⏳ Gepland | Sprint 13 |
| HTTPS/TLS reverse proxy | ⏳ Gepland | Fase 1 |
| Gebruikers-authenticatie (JWT) | ⏳ Gepland | Fase 2 |

---

## ⚖️ Licenties & Hergebruik (Dual Licensing)

D-OmniTwin streeft naar maximale maatschappelijke impact via een dual-licensing model:

**1. De Software (EUPL 1.2)**  
Alle broncode (Python backend, React/JS frontend, database-schema's en ETL-scripts) is gelicentieerd onder de [European Union Public License v1.2](./LICENSE). Dit garandeert dat de software open blijft en verbeteringen terugvloeien naar de gemeenschap, terwijl commerciële partijen de code wel kunnen gebruiken in hun dienstverlening (mits open).

**2. De Methodiek & Documentatie (CC BY 4.0)**  
De D-OmniTwin methodiek, de Kompas-hiërarchie, alle documenten in `/docs`, de indicatorstructuur en de AI-prompting filosofie zijn beschikbaar onder de [Creative Commons Attribution 4.0 International](./LICENSE-DOCS) licentie. Vrij te gebruiken en te verspreiden mits bronvermelding.

Zie [NOTICE.md](./NOTICE.md) voor informatie over third-party licenties.

---

## 📖 Documentatie

| Document | Beschrijving |
|----------|-------------|
| [README.md](./README.md) | Project overview (dit document) |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | ⭐ Stap-voor-stap installatiehhandleiding met starter dataset |
| [init_data/README.md](./init_data/README.md) | Documentatie initiatie dataset (Fryslân) |
| [BUILD.md](./BUILD.md) | Installatie, setup & sprint changelog |
| [TODO.md](./TODO.md) | Actieve takenlijst per domein |
| [ROADMAP.md](./ROADMAP.md) | Lange-termijn planning en features |
| [ARCHITECTURE_TECHNICAL_OPERATION.md](./ARCHITECTURE_TECHNICAL_OPERATION.md) | Volledige technische architectuur |
| [docs/8-communicatie/architectuur-omnitwin.md](./docs/8-communicatie/architectuur-omnitwin.md) | Systeem architectuur (uitgebreid) |
| [docs/8-communicatie/communicatieplan_subsidie_2026.md](./docs/8-communicatie/communicatieplan_subsidie_2026.md) | Subsidie & adoptie communicatieplan |

---

## 📊 API Endpoints Overzicht

### Public API (Main App)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/gebiedsmonitor/gebieden` | GET | Alle gebieden |
| `/api/gebiedsmonitor/indicatoren` | GET | Indicator metadata |
| `/api/kompas/configuraties` | GET | Kompas configuraties |
| `/api/kompas/hierarchie` | GET | Kompas hiërarchie |
| `/api/kaart/v2/data` | GET | Kaart GeoJSON data |
| `/api/chat` | POST | D-Omni Assistent chat |
| `/api/report/data/{gebied_id}` | GET | Gebiedsdossier Z-scores |
| `/api/report/benchmark` | GET | Benchmark vergelijker |

### Admin API (Beveiligd — `X-Admin-Key` header vereist)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/admin/health` | GET | API health check |
| `/api/admin/indicatoren` | GET/PUT | Indicator CRUD |
| `/api/admin/hierarchie/tree` | GET | Kompas tree data |
| `/api/admin/prompts` | GET/POST | System prompt beheer |
| `/api/admin/dashboard/stats` | GET | Dashboard statistieken |
| `/api/data-controle` | GET | Data kwaliteitsrapport |

> 📚 Volledige API documentatie beschikbaar via: http://localhost:8000/docs

---

**Versie:** v1.0.0-beta (pre-release) | **Laatste Update:** 9 juni 2026 | **Licentie:** EUPL 1.2 / CC BY 4.0  
*Ontwikkeld door Gemeente Súdwest-Fryslân in samenwerking met Leeuwarden, Tytsjerksteradiel & DataFryslân*
