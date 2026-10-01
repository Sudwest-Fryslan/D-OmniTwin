# D-OmniTwin 🌍🔐
> Digitale spiegel van de fysieke leefomgeving — open source, federatief, dataspace-ready

**Versie:** 0.1.0 (eerste release in voorbereiding, zie [releasebeleid](./docs/9-beheer/releasebeleid.md)) | **Laatste update:** 20 juli 2026 | **Status:** 🟢 ACTIEF (Sprint 22)  
**Security:** API key auth actief, CORS locked, Security headers actief  
[![Licentie: EUPL 1.2](https://img.shields.io/badge/Licentie-EUPL_1.2-blue)](./LICENSE) [![Docs: CC BY 4.0](https://img.shields.io/badge/Docs-CC_BY_4.0-green)](./LICENSE-DOCS)

---

## 🌐 Wat is D-OmniTwin?

Gemeenten en provincies staan voor complexe leefomgevingsopgaven — van energietransitie en klimaatadaptatie tot sociale cohesie en brede welvaart. Data is vaak aanwezig, maar versnipperd over organisaties en systemen. D-OmniTwin biedt een **holistisch beeld van de buitenwereld**: een interactieve digitale spiegel van de fysieke leefomgeving, ontworpen voor integraal beleid en gebiedsontwikkeling.

> 🏆 **Innovatiebudget 2026 Toegekend!**
> *"D-OmniTwin: Federatieve voorziening voor inzicht in leefomgeving"*
> Ons project is succesvol gehonoreerd door het ministerie. Dit stelt ons in staat om de referentie-implementatie door te ontwikkelen naar een gevalideerde federatieve voorziening (Dataspace-architectuur).
> 🔗 [Bekijk de officiële toekenning](https://www.digitaleoverheid.nl/overzicht-van-alle-onderwerpen/innovatie/innovatiebudget/toekenning-innovatiebudget-2026/)

Via een interactief **D-Omni Kompas** — een D3.js sunburst-visualisatie met 235 indicatoren over 12 thema's — wordt data op buurtniveau direct inzichtelijk voor beleidsmakers, wijkfunctionarissen en inwoners. Een lokale AI-assistent (geen cloud-afhankelijkheid) vertaalt complexe datasets naar begrijpelijke inzichten in gewone taal.

D-OmniTwin fungeert als **dataspace-agnostische interactielaag**: data blijft bij de bron, beveiligd via iSHARE-autorisatie, in lijn met Gaia-X principes en de Fryslân Data Space (FRLDS).

### Typische use cases
- 🔥 **Energietransitie & Energiearmoede** — energielabels, EP-Online, BAG op buurtniveau
- 🌡️ **Klimaatadaptatie (hittestress)** — combinatie van groen, verharding en gezondheidsdata
- 📊 **Brede Welvaart** — integraal overzicht van sociaal-economische en leefbaarheidsdata
- 🤝 **Sociale Cohesie** — gezondheidsmonitor, eenzaamheid, buurtbetrokkenheid

**Dekkingsgebied:** Noord-Nederland — Fryslân, Groningen, Drenthe — 49 gemeenten, 235 indicatoren op CBS-buurtniveau (2020–2025).

---

## ⚡ Snel starten

Vereist: [Docker](https://www.docker.com/) met Docker Compose. Ollama is optioneel (alleen voor de AI-chat).

```bash
git clone https://github.com/TLaan/D-OmniTwin.git && cd D-OmniTwin
cp .env.example .env
# Vul in .env alleen DATABASE_PASSWORD in (en bij voorkeur ADMIN_PASSWORD)
docker compose up -d --build
```

Open daarna **http://localhost**. Alles loopt via Traefik op poort 80; de backend (poort 8000) is binnen Docker niet direct bereikbaar. Dit start de installatiemodus (`COMPOSE_FILE` in `.env`); voor alle details van een installatie bij je organisatie volg je de **[installatiegids](./docs/9-beheer/installatie.md)** (vereisten, `.env`, backup, bijwerken, beveiliging).

- Bij de eerste start maakt de eenmalige service `db-init` het databaseschema aan en laadt de **use cases** in [`usecases/`](./usecases/README.md) (`LOAD_SAMPLE_DATA=true`, de standaard): 13 buurten in Súdwest-Fryslân, elk met data, inrichting en teststappen. Met `false` krijg je het product zonder data (indicatoren, Kompas, stuurdata), klaar voor eigen data.
- **Beheeromgeving:** http://localhost/admin. Inloggen met `ADMIN_USER` (standaard `admin`) en het `ADMIN_PASSWORD` uit `.env`. Laat je `ADMIN_PASSWORD` leeg, dan wordt eenmalig een wachtwoord gegenereerd en in de log getoond: `docker compose logs db-init`. Laat `DEBUG=true` staan zolang je zonder HTTPS draait; anders wordt het inlogcookie alleen via HTTPS verstuurd en lukt inloggen niet.
- **API-documentatie:** http://localhost/docs.

Volledige data voor Fryslân laden: zie de [installatiegids](./docs/9-beheer/installatie.md#4-data). Lokaal zonder Docker ontwikkelen: zie [Installatie voor ontwikkelaars](#-installatie-voor-ontwikkelaars).

**Meedoen:** zie [CONTRIBUTING.md](./CONTRIBUTING.md) en de [gedragscode](./CODE_OF_CONDUCT.md). Een kwetsbaarheid gevonden? Meld die privé volgens [SECURITY.md](./SECURITY.md), niet via een openbaar issue. Metadata voor codebase-registers staat in [publiccode.yml](./publiccode.yml).

---

## 📸 Zo ziet het eruit

Schermafbeeldingen van een verse installatie met de sample dataset (`docker compose up`), ingezoomd op Bolsward.

![Kaart: buurten in Bolsward gekleurd op een indicator, met PDOK-achtergrondkaart](docs/images/kaart-bolsward.jpg)
*Kaart: buurten gekleurd op een indicator (hier "Afstand tot koele plek"), PDOK-achtergrondkaart.*

![Kompas: sunburst met de thema's voor buurt Bolsward-Zuidoost](docs/images/kompas-bolsward-zuidoost.jpg)
*D-Omni Kompas voor Bolsward-Zuidoost: alle indicatoren in thema's, gekleurd ten opzichte van de referentiegroep.*

![Chat: de D-Omni Assistent met het scenario Beleidsadviseur](docs/images/chat-beleidsadviseur.jpg)
*D-Omni Assistent: het scenario "Beleidsadviseur" zet kaart en Kompas klaar.*

![Beheerscherm: dashboard met datadekking per Kompas-kwadrant](docs/images/beheer-dashboard.jpg)
*Beheerscherm (`/admin`): indicatoren, datakwaliteit, AI-configuratie en rapportage.*

> Bolsward-Zuidoost bevat in de sample **demodata** (zie `init_data/sample/README.md`). De screenshots maak je opnieuw met [`scripts/docs/maak_screenshots.py`](scripts/docs/maak_screenshots.py).

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

D-OmniTwin is toegekend voor het **Innovatiebudget Digitale Overheid 2026** (looptijd sept. 2026 – aug. 2027, totaal €300.000). Doel: doorontwikkeling van de huidige referentie-implementatie naar een **gevalideerde federatieve voorziening** gekoppeld aan de Fryslân Data Space en het Federatief Datastelsel.

Vier use cases worden gevalideerd in pilots bij drie gemeenten. Resultaat: open source codebase, governance-model en herhaalbare methodiek voor andere regio's.

> **🤝 Interesse in samenwerking of pilotdeelname?**  
> Open een [discussie op GitHub](../../discussions) of neem direct contact op:  
> 📧 **[t.vanderlaan@sudwestfryslan.nl](mailto:t.vanderlaan@sudwestfryslan.nl)** 
> 🔗 Zie ook: [communicatieplan_subsidie_2026.md](./docs/8-communicatie/communicatieplan_subsidie_2026.md)

---

## 🧩 Componenten Overzicht

| Component | Technologie | Poort (intern) | Via Traefik (Docker) | Status |
|-----------|-------------|----------------|----------------------|--------|
| **API Gateway** | Traefik Reverse Proxy | 80 | http://localhost | ✅ Production Ready |
| **Main Backend** | FastAPI (Hybride logic) | 8000 | `/` en `/api/*` | ✅ Production Ready |
| **Data API** | PostgREST | 3000 | `/api/data` | ✅ Operationeel |
| **Geo API** | pg_featureserv | 9000 | `/api/geo` | ✅ Operationeel |
| **Admin Panel** | React + TypeScript | via backend (dev server: 3000) | `/admin` | ✅ MVP Ready |
| **Database** | PostgreSQL + PostGIS + pgvector | 5432 | niet via Traefik; op de host: 5433 | ✅ Operationeel |

> Met Docker Compose is alleen Traefik (poort 80, dashboard op 8081) en de database (5433) op de host bereikbaar. De interne poorten gelden binnen het Docker-netwerk of bij lokaal draaien zonder Docker.

### Main App Features
- 🗺️ **Interactieve Kaart** — MapLibre + deck.gl 3D visualisatie, choropleth op buurtniveau
- 🧭 **D-Omni Kompas** — D3.js sunburst met 12 thema's, 235 indicatoren, multi-gebied aggregatie
- 📊 **Thema-Analyse** — D3 Diverging Bar Chart en boomstructuur filter voor diepgaande analyse (Issue #15)
- 📈 **Multi-Gebied Analyse & Benchmark** — Shift+Click selectie, Omgevingsvisie-deelgebieden, Z-score rapportage en Top 3+3 afwijkers
- 🗺️ **Externe Kaartlagen & Selectie** — Dynamische externe bronnen (zoals BAG Woonplaatsen en Omgevingsvisie) met klik-selectie buffer
- ⏳ **Time Slider & Trends** — Historische tijdreeksen en trendlijnen per indicator met play/pauze bediening
- 🤖 **D-Omni Assistent** — Intent-based AI chat interface met governance-labels en contextuele acties (lokale Ollama, geen cloud)
- 💡 **Onboarding & Feedback** — Welkomstflow, contextuele tooltips en glassmorphism toast-notificaties
- 🎨 **Classic Premium UI** — Dark theme met gradient accents, glassmorphism panelen

### Admin Panel Features
- 🔐 **API Key Auth** — Beveiligde toegang tot beheer
- 🧹 **Deduplicatie Assistent** — AI-gedreven matching (pg_trgm + pgvector) voor het opschonen en samenvoegen van dubbele indicatoren
- ✏️ **Indicator Editor** — Bewerk naam, omschrijving, score type, kleurschema
- 🏷️ **Ontologie Beheer** — Validatie en beheer van AI-gegenereerde ontologieën en definities
- 📋 **Log Viewer & Retentie** — In-app realtime logging over 9 categorieën met statistieken en filtermogelijkheden
- 📈 **Dashboard** — Systeemstatistieken en Kompas hiërarchie overzicht
- 📄 **Multi-Gebiedsdossier** — D3-stijl rapportmodule voor multi-selectie van buurten met PDF/Print export
- 🗺️ **Externe Lagen Beheer** — Configuratie van WFS-bronnen en lokale uploads (GPKG/GeoJSON)
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
│  │  app.js       │  │  235 indicatoren │  │  Glassmorphism UI        │  │
│  └──────┬────────┘  └────────┬─────────┘  └────────────┬─────────────┘  │
│         └─────────── EventBus (event-bus.js) ──────────┘                │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ HTTP/REST (poort 80)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TRAEFIK API GATEWAY (Reverse Proxy)                                    │
└──────┬───────────────────────┬───────────────────────┬──────────────────┘
       │ /api/data/*           │ /api/geo/*            │ /api/* (overig)
       ▼                       ▼                       ▼
┌──────────────┐      ┌─────────────────┐    ┌───────────────────────────┐
│  PostgREST   │      │ pg_featureserv  │    │ FastAPI Backend (8000)    │
│  (Data API)  │      │ (Geo/MVT API)   │    │ AI, Rapportage, Admin     │
└──────┬───────┘      └────────┬────────┘    └───────────┬───────────────┘
       │                       │                         │ SQLAlchemy
       └───────────────────────┼─────────────────────────┘
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
ollama pull qwen3:30b-instruct  # of kleiner: qwen3:4b-instruct

# Configureerbaar via Admin Panel → LLM Config
# OF via environment variabelen (fallback):
OLLAMA_HOST=http://localhost:11434
# Model kiezen in Beheer → AI Configuratie
```

**Andere LLM-servers (OpenAI-compatibel).** In Admin → AI Configuratie kies je het API-type
([ADR 0001](./docs/2-architectuur/adr/0001-llm-koppeling-openai-standaard.md)):

- `Ollama` (standaard): de eigen Ollama-API, zoals hierboven.
- `OpenAI-compatibel`: `/v1/chat/completions` van Ollama (`http://host.docker.internal:11434`),
  vLLM, LM Studio of een aanbieder. Een API-sleutel zet je als `LLM_API_KEY` in `.env`, nooit in de database.

Bestaande databases hebben eerst migratie `migrations/schema_v20_llm_api_type.sql` nodig om `OpenAI-compatibel` op te slaan;
zonder migratie blijft alles werken als `Ollama`.

**Optionele LiteLLM-gateway** (centrale sleutels, logging, terugval naar een ander model):

```bash
# .env: LITELLM_MASTER_KEY=sk-... en LLM_API_KEY=<zelfde waarde>
docker compose --profile llm-gateway up -d
# Admin → AI Configuratie: OpenAI-compatibel, URL http://llm-gateway:4000, model d-omnitwin-default
```

De gateway stuurt standaard door naar `OLLAMA_HOST`/`OLLAMA_MODEL`; fallbacks staan als voorbeeld in
`deploy/litellm/config.yaml`. De gateway heeft geen poort op de host.

Daarnaast kent de gateway de aliassen `d-omnitwin-ollama`, `d-omnitwin-claude`, `d-omnitwin-openai` en
`d-omnitwin-gemini`. Wisselen en vergelijken:

```bash
docker compose exec backend python scripts/llm/kies_provider.py gemini   # ollama|claude|openai|gemini|direct-ollama
python scripts/llm/vergelijk_providers.py --base-url http://localhost    # rapport in docs/testcases/llm-vergelijking/
```

Sleutels (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) staan alleen in `.env`; leeg = niet beschikbaar.
Met een externe aanbieder verlaten vragen en gebiedsdata de organisatie (AVG/IAMA). Zie de
[installatiegids, §7](./docs/9-beheer/installatie.md#7-llm-optioneel).

---

## ✅ Recent Voltooid

> Zie [BUILD.md → Sprint Changelog](./BUILD.md#-sprint-changelog) voor het volledige dag-voor-dag overzicht.

| Sprint | Datum | Kernpunten |
|--------|-------|------------|
| **Sprint 22** | 20-07-2026 | 📊 **Data Engineering & Dataspace Track** — ETL/Dataspace gap-analyse (D-OmniTwin als datamart-consument van FRLDS) en indicatoren bronvergelijking (812 indicatoren). |
| **Sprint 21** | 20-07-2026 | 🧹 **Data Kwaliteit & Deduplicatie** — AI-matching (pg_trgm + pgvector), interactieve checkbox-gestuurde merge/groepeer acties en uitzonderingenbeheer. |
| **Sprint 19B** | 05-07-2026 | 📈 **Thema-Analyse & Dataspace Migratie** — D3 Diverging Bar Chart, boomstructuur filter (Issue #15) en PostgREST/pg_featureserv/Traefik architectuur. |
| **Sprint 18** | 30-06-2026 | 🗺️ **IJsselmeerkust als Besluitinstrument** — BAG Woonplaatsen (WFS), multi-gebied benchmarking, Top 3+3 uitschieters en lokale geodata uploads. |

---

## 🚀 Installatie voor ontwikkelaars

> Installeren met Docker (ook voor beheerders): zie de **[installatiegids](./docs/9-beheer/installatie.md)**. Deze sectie is alleen voor lokaal ontwikkelen zonder Docker en is deels verouderd (#21).
>
> [`GETTING_STARTED.md`](./GETTING_STARTED.md) beschrijft dezelfde route uitgebreider, maar is verouderd.

### Prerequisites
- Python 3.10+ · Node.js 18+ · PostgreSQL 14+ (PostGIS + pgvector + pg_trgm)
- [Docker & Docker Compose](https://www.docker.com/) — aanbevolen voor de volledige dataspace-stack
- [Ollama](https://ollama.ai/) — optioneel, alleen voor AI-functies

### Snelstart

```bash
# 1. Klonen & virtuele omgeving inrichten
git clone <repo-url> && cd D-OmniTwin
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Omgeving configureren via de interactieve wizard
python init_data/scripts/setup_env.py  # genereert veilige .env keys en configuratie

# 3. PostgreSQL database & extensies aanmaken (bij lokale installatie)
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'jouw-wachtwoord';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION postgis; CREATE EXTENSION vector; CREATE EXTENSION pg_trgm;"

# 4. Initiatiedata ophalen (PDOK WFS API + CBS OData) & database seeden
python init_data/scripts/download_buurten_fryslan.py
python init_data/scripts/download_indicatoren_fryslan.py
bash init_data/scripts/init_database.sh

# 5. Applicatie starten
# Optie A: Docker Compose (Aanbevolen: Traefik, PostgREST, pg_featureserv, DB & FastAPI)
docker compose up -d

# Optie B: Lokale Python dev server (FastAPI)
source .venv/bin/activate && python run_dev.py
```

**Toegang met Docker Compose (optie A)** — alles via Traefik op poort 80:
- 🌐 **App:** http://localhost
- 📚 **API Docs:** http://localhost/docs
- 🔐 **Admin Panel:** http://localhost/admin
- 🗄️ **Data API (PostgREST):** http://localhost/api/data
- 🗺️ **Geo API (pg_featureserv):** http://localhost/api/geo

**Toegang met de lokale dev server (optie B)** — alleen FastAPI, zonder PostgREST en pg_featureserv:
- 🌐 **App:** http://localhost:8000 · 📚 **API Docs:** http://localhost:8000/docs · 🔐 **Admin Panel:** http://localhost:8000/admin (of via dev server: `cd admin-panel && npm start` → http://localhost:3000/admin/)

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
| [docs/9-beheer/installatie.md](./docs/9-beheer/installatie.md) | ⭐ Installatie en beheer (Docker): de actuele installatiegids |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Installatie zonder Docker met Fryslân-dataset (verouderd, zie installatiegids) |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Bijdragen: van issue tot merge |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | Gedragscode (Contributor Covenant 2.1) |
| [SECURITY.md](./SECURITY.md) | Kwetsbaarheden privé melden |
| [PROJECT_GOVERNANCE.md](./PROJECT_GOVERNANCE.md) | Rollen en besluitvorming (concept) |
| [CHANGELOG.md](./CHANGELOG.md) | Wijzigingen per versie |
| [publiccode.yml](./publiccode.yml) | Metadata voor codebase-registers (publiccode.yml-standaard) |
| [init_data/README.md](./init_data/README.md) | Documentatie initiatie dataset (Fryslân) |
| [BUILD.md](./BUILD.md) | Build-notities & sprint changelog (installatie: zie installatiegids) |
| [TODO.md](./TODO.md) | Actieve takenlijst per domein |
| [ROADMAP.md](./ROADMAP.md) | Lange-termijn planning en features |
| [docs/STATE.md](./docs/STATE.md) | 🟢 Systeemstatus & actieve componenten (Single Source of Truth) |
| [docs/INDEX.md](./docs/INDEX.md) | Navigatielaag en router voor alle domeindocumentatie |
| [docs/2-architectuur/architecture/ARCHITECTURE_TECHNICAL_OPERATION.md](./docs/2-architectuur/architecture/ARCHITECTURE_TECHNICAL_OPERATION.md) | Volledige technische architectuur |
| [docs/3-data-engineering/etl_dataspace_gap_analyse.md](./docs/3-data-engineering/etl_dataspace_gap_analyse.md) | ETL & Dataspace integratie-analyse |
| [docs/8-communicatie/communicatieplan_subsidie_2026.md](./docs/8-communicatie/communicatieplan_subsidie_2026.md) | Subsidie & adoptie communicatieplan |

---

## 📊 API Endpoints Overzicht

### Public API (Main App & Dataspace Endpoints)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/gebiedsmonitor/gebieden` | GET | Alle gebieden en contouren |
| `/api/gebiedsmonitor/indicatoren` | GET | Indicator metadata & taxonomie |
| `/api/kompas/configuraties` | GET | Kompas configuraties |
| `/api/kompas/hierarchie` | GET | Kompas hiërarchie & D3 boomstructuur |
| `/api/kaart/v2/data` | GET | Kaart GeoJSON choropleth data |
| `/api/chat` | POST | D-Omni Assistent chat & intent dispatcher |
| `/api/report/multi-gebied` | POST | Multi-Gebiedsdossier Z-score analyse |
| `/api/externe-lagen` | GET | Actieve externe kaartlagen (WFS/GPKG) |
| `/api/data/*` | GET | PostgREST dataspace-compliant data endpoint |
| `/api/geo/*` | GET | pg_featureserv OGC API Features endpoint |

### Admin API (Beveiligd — `X-Admin-Key` header vereist)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/admin/health` | GET | API health check |
| `/api/admin/indicatoren` | GET/PUT | Indicator CRUD & parameters |
| `/api/admin/hierarchie/tree` | GET | Kompas boomstructuur beheer |
| `/api/admin/deduplicatie` | GET/POST | AI-gestuurde deduplicatie van indicatoren |
| `/api/admin/logs` | GET/PUT | In-app log viewer & categoriebeheer |
| `/api/admin/externe-lagen/upload`| POST | GeoPackage upload voor kaartlagen |
| `/api/admin/prompts` | GET/PUT | System prompt & LLM instellingen |
| `/api/admin/dashboard/stats` | GET | Dashboard statistieken |
| `/api/data-controle` | GET | Data kwaliteitsrapport |

> 📚 Volledige API documentatie beschikbaar via: http://localhost/docs (Docker) of http://localhost:8000/docs (lokale dev server)

---

**Versie:** 0.1.0 (eerste release in voorbereiding, zie [releasebeleid](./docs/9-beheer/releasebeleid.md)) | **Laatste Update:** 20 juli 2026 | **Licentie:** EUPL 1.2 / CC BY 4.0  
*Ontwikkeld door Gemeente Súdwest-Fryslân in samenwerking met Leeuwarden, Tytsjerksteradiel & DataFryslân*
