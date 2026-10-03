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
- In sync blijven met de actuele stand: `CHANGELOG.md` (per versie, `[Unreleased]` voor wat er op `main` staat) en de GitHub-issues. `docs/STATE.md` is een historische momentopname (tot 0.1.0) en niet leidend.
- Geen koppelingen introduceren die losse deployment van D-OmniTwin moeilijker maken.
- **Geen multi-tenancy** (ADR 0007, `docs/2-architectuur/mesh-van-instanties.md`): één instantie per organisatie, met eigen database en Keycloak. Geen `tenant_id`/`organisatie_id`, geen RLS of rollen per organisatie, geen gemeente-filter als scheiding. Samenwerken = uitwisselen tussen instanties (mesh).
- **Alles wat een instantie inricht, is uitwisselbaar als data** (use cases, registraties, profielen, rollen, contacten, contracten), via de portabiliteitspoort. Dus: geen organisatie, gemeentecode, provincie, logo of contact hardcoded in code; UUID/URI in plaats van seriële ID's naar buiten; geheimen nooit in een exporteerbaar item.
- Architectuurkeuzes toetsen aan het doelbeeld: dataspace-platform, bron blijft bron, begrijpbaarheid boven complexiteit.
- D-OmniTwin positioneren als **methodiek + referentie-implementatie**, niet als product of platform — dit bepaalt adoptie buiten SWF.
- Spanningsveld bewaken: "federatie later, architectonisch voorbereid" versus lopende FRLDS-specifieke sprints — geen FRLDS-afhankelijkheden inbouwen die een dataspace-agnostische opzet blokkeren.

### Communicatiestijl
Direct en nuchter, kern eerst, geen omhaal. Lever wat gevraagd wordt, niet meer — als iets schuurt, benoem het kort en los het gericht op. Collegiaal en scherp op inhoud, niet hard op de relatie. Eduard's schrijfstijl: direct, zakelijk, kern vooraan, geen managementtaal.

## Project Overview

D-OmniTwin is a digital twin platform for Dutch municipalities, visualizing neighborhood-level indicators (Kompas: 235 metrics across 12 thematic quadrants) on interactive maps. Built for Súdwest-Fryslân, it combines geospatial data, AI-powered chat, and multi-area comparative reporting.

- **API Gateway:** Traefik on port 80 (Reverse proxy). Security-headers per router (`traefik.http.routers.<naam>.middlewares=security-headers@file`, niet op het entrypoint); een nieuwe router zonder headers-middleware laat `tests/test_traefik_routers.py` falen
- **Main Backend:** FastAPI (Python 3.10+) on port 8000
- **Data API:** PostgREST on port 3000 (`/api/data/*`). Alleen-lezen: publiceert alleen schema `api` (views/functies), rol `web_anon` via `authenticator` (#57). Nieuw object voor de frontend: view/functie + `GRANT` in `db/migraties/R__api_rollen.sql`, nooit `users`/`sessions`/`api_keys`/`llm_config`/`system_prompts`/logs. Schrijven gaat via FastAPI met auth
- **Geo API:** pg_featureserv on port 9000 (`/api/geo/*`), als alleen-lezen rol `featureserv` (alleen `vw_gebieden_features`, `omgevingsvisie_deelgebieden`, `postgisftw.*`)
- **Laad-API:** FastAPI-router `/api/laden/v1` (`src/omnitwin/routers/laden.py`, laadstraat in `src/omnitwin/laden/`), spec eerst: `docs/api/laden/openapi.yaml` (die serveert hij ook op `/api/laden/v1/openapi.json`; een contracttest houdt routes en spec gelijk). Schema `laden` (V024), schrijft als rol `laden_schrijver`; ruwe leveringen in het volume `leveringen`. Verwerking in een threadpool in de backend. Machineclient met rollen: `deploy/keycloak/machineclient.sh`
- **Main Frontend:** Vanilla JS + MapLibre GL + Deck.gl (no build step, served from `/static/`)
- **Admin Panel:** React 19 + TypeScript SPA in `/admin-panel/`, gebouwd met Vite (port 3000 in dev, built to `/static/admin-panel/`)
- **Identity provider (optioneel):** Keycloak, compose-profiel `keycloak` (#214), achter Traefik op `/auth`, eigen database `keycloak` in dezelfde PostgreSQL (aangemaakt door `keycloak-db-init`, `docker-entrypoint.sh keycloak-db`). Realm-import bij de eerste start uit `deploy/keycloak/realm-omnitwin.json` (realm `omnitwin`, clients `omnitwin-web`, `omnitwin-api`, `etl-voorbeeld`); secret opvragen met `deploy/keycloak/client-secret.sh`. Headers-middleware `keycloak-headers` (Keycloak zet zelf CSP en frame-regels). De backend valideert tokens op de nieuwe API's als `OIDC_ISSUER` is gezet (`src/omnitwin/oidc.py`, zie Authentication)
- **Database:** PostgreSQL 15 (image `postgis/postgis:15-3.5`, zie `db.Dockerfile`) with PostGIS, pgvector, and pg_trgm extensions

## Commands

### Full Stack (Docker Compose)
```bash
docker compose up -d --build   # dev: laadt ook docker-compose.override.yml (bind-mount, DB op 5433, Traefik-dashboard 8081)
```
Installatie voor beheerders (`COMPOSE_FILE=docker-compose.yml` in `.env`, alleen poort 80 / `OMNITWIN_HTTP_PORT`): zie **`docs/9-beheer/installatie.md`** — de enige actuele installatiegids. Bij de eerste start richt de eenmalige service `db-init` (`docker-entrypoint.sh init`) een lege database in: schema, views, de schemamigraties (`db/migraties/`, runner `python -m omnitwin.migraties`), stuurdata en definities (`load_sample.py --stap definities`), de use cases (`usecases/`, `python -m omnitwin.usecases installeer --alle --inproces`: de laadstraat in-process, open data gedownload met cache in `bron-cache`; alleen bij `LOAD_SAMPLE_DATA=true`) en admin-gebruiker. Alle data hoort bij een use case: data + inrichting + stappen; wat nog niet open is, staat in `init_data/sample/` en is gemarkeerd als `DEMODATA` (#236). Daarna werkt hij altijd de rollen en het schema `api` bij (`db/migraties/R__api_rollen.sql`) en maakt hij ontbrekende embeddings aan. Een geslaagde eerste init legt hij vast in tabel `installatie_status` (#201). Een bestaande database (rij in `installatie_status`, of een installatie van vóór 0.2.1 met `gebieden` en een beheerder) laat hij qua data ongemoeid, maar de migratierunner past wel openstaande migraties toe (#54). Tabellen zonder markering en zonder beheerder (half mislukte eerste init): db-init stopt met een foutmelding en herstelinstructie.

### Backend
De backend is één Python-pakket: `src/omnitwin/` (`main.py`, `routers/`, `services/`, `schemas/`, `database.py`, `version.py`, `utils/`). De app is `omnitwin.main:app`; imports altijd als `from omnitwin.services... import ...`. In de image staat `PYTHONPATH=/app/src`, pytest vindt het pakket via `pythonpath` in `pyproject.toml`. Database (SQL): `db/` (zie Database). `static/`, `templates/`, `init_data/`, `usecases/`, `scripts/`, `ETL/` en `tests/` staan (nog) in de root (RFC #182).

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e . --no-deps   # pakket omnitwin (src/omnitwin), voor scripts buiten pytest

# Start development server (optimized file watching, port 8000)
python run_dev.py

# Run tests (elke test heeft een marker unit/integration/e2e/llm; zonder marker faalt de collectie)
python -m pytest -m unit                  # zoals de CI-job Unit Tests, zonder database
python -m pytest tests/test_migraties.py  # single test file
# integration/e2e: tegen een draaiende stack, zie tests/integration/test_sample_stack.py en tests/e2e/README.md
```

### Admin Panel (React)
```bash
cd admin-panel
npm install
npm start        # Vite dev server on port 3000 (proxy /api -> :8000)
npm run build:static  # production build + kopie naar static/admin-panel (commit die map mee)
npm run typecheck     # tsc --noEmit
npm test         # Vitest (eenmalig)
npm run lint     # ESLint
# CI (job Admin-panel): npm ci, typecheck, lint, test, build:static, en faalt als static/admin-panel daarna afwijkt
```

### API-specificaties
Elke API heeft een eigen spec in `docs/api/<naam>/openapi.yaml` (OAS 3.0.3), de bron voor de implementatie (ADR 0005, `docs/2-architectuur/api-landschap.md`). Een wijziging aan een API begint met de spec. Lint met de Logius-ruleset (NL GOV API Design Rules 2.1, `docs/api/.spectral.yaml`); 0 errors vereist, bewuste waarschuwingen staan in de README van de API. Nog niet in de CI (geen Actions-minuten, #200); wel lokaal draaien bij elke wijziging.
```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/w" -w /w stoplight/spectral:6 lint -r docs/api/.spectral.yaml docs/api/laden/openapi.yaml
# zonder Docker: npx -y @stoplight/spectral-cli@6 lint -r docs/api/.spectral.yaml docs/api/laden/openapi.yaml
npx -y @redocly/cli@1 lint --extends minimal docs/api/laden/openapi.yaml   # OpenAPI-validatie, ook voorbeelden tegen schema's
```

### Database initialisatie — Fryslân-dataset zonder Docker (verouderd)
```bash
python init_data/scripts/download_buurten_fryslan.py
python init_data/scripts/download_indicatoren_fryslan.py
bash init_data/scripts/init_database.sh   # master initiatie-script, zie init_data/README.md
```
Alleen voor een PostgreSQL zonder Docker (`docs/archief/GETTING_STARTED.md`). Loopt achter op `docker-entrypoint.sh`: geen `06`/`07`, geen migratierunner en geen `R__api_rollen.sql`. Werkt niet tegen de Docker-stack: `init_database.sh` verwacht een `.env` in de container en laadt het schema opnieuw. In Docker laad je de Fryslân-data na `db-init` met `docker compose exec backend python init_data/scripts/seed_fryslan.py --stap alle` (idempotent, exitcode 1 bij fouten; zie `docs/9-beheer/installatie.md`).

### ETL — doorlopend nieuwe databronnen/gemeenten toevoegen (ná de initiële setup)
```bash
python ETL/search_api.py                     # discovery: welke datasets bestaan bij CBS/RIVM/Politie
python ETL/run_etl.py -ds <dataset_id> -gm <gemeentecode>   # extract + import van één dataset/gemeente
```
Dit framework is **niet** voor de initiële bootstrap (dat is `init_data/`, hierboven) maar voor het uitbreiden met extra gemeenten of databronnen daarna. Zie `ETL/ETL_DOCUMENTATION.md` en `docs/archief/GETTING_STARTED.md` ("Eigen gemeente of regio toevoegen").

Het oude pipeline-pad `ETL/local/` (`etl_01..06`, met `DROP SCHEMA public CASCADE`) en `ETL/Utils/db_init.py` zijn verwijderd (#69). Nieuwe data hoort in een use case en gaat via de laad-API (`docs/api/laden/README.md`).

## Environment Setup

Copy `.env.example` to `.env` and fill in (details: `docs/9-beheer/installatie.md`, sectie 2.2):
- `DATABASE_*` — PostgreSQL connection (requires PostGIS extension). `DATABASE_PASSWORD` alleen letters/cijfers: het komt in database-URL's terecht
- `ADMIN_API_KEY` — voor scripts (`X-Admin-Key`), niet voor de beheer-UI; minimaal 32 tekens, een lege of voorbeeldwaarde wordt geweigerd
- `ADMIN_USER` / `ADMIN_PASSWORD` — eerste beheeraccount; leeg = gegenereerd, eenmalig in `docker compose logs db-init`
- `OLLAMA_*` — for local LLM (optional; Qwen model)

The admin panel authenticates only with the session cookie (local user with `is_admin`, or via Keycloak with realm role `beheerder`; the backend does the OIDC flow). Never put secrets in `VITE_*` variables: Vite bakes them into the bundle.

## Architecture

### Request Flow
```
Browser (Map click / Chat query)
  → EventBus dispatch (static/js/core/)
  → Fetch to FastAPI router (src/omnitwin/routers/)
  → Service layer (src/omnitwin/services/) — Z-scores, spatial queries, LLM calls
  → PostgreSQL + PostGIS
  → JSON response → D3 / Deck.gl render
```

### Frontend Architecture (non-obvious)
The main app has **no build step**. `templates/index.html` (Jinja2) loads the libraries from `static/vendor/` (self-hosted with SRI, no CDN, #144) and the three main JS files:
- `static/js/app.js` (~180KB) — map, layers, area selection, global `window.state`
- `static/js/kompas.js` (~105KB) — D3.js sunburst chart for 12-quadrant Kompas
- `static/js/chat.js` (~21KB) — chat panel with rule-based intent classification

These are large files — wijzig gericht, niet in bulk. They communicate via a **custom EventBus** (`static/js/core/`) — not via shared state or a framework. When an area is selected on the map, an event fires that kompas.js and chat.js subscribe to. State is managed through a global `window.state` object (selected areas, active layers, filters). No frameworks toevoegen.

### Backend Router → Service Pattern
Each API concern has a router in `src/omnitwin/routers/` (thin HTTP layer) and a service in `src/omnitwin/services/` (business logic). Wijzig zo min mogelijk, gebruik bestaande naamgeving:
- `gebiedsmonitor_service.py` — data aggregation, Z-score normalization, color scaling
- `kompas_service.py` — thematic hierarchy aggregation and scoring
- `report_service.py` — multi-area dossier generation with SVG choropleth rendering
- `llm_service.py` — Ollama integration (lazy-loaded, with graceful fallback)
- `ai_search_service.py` — SentenceTransformer semantic search (lazy-loaded on first use)

Conventies (#203): omgevingsvariabelen alleen via `omnitwin.config` (`instellingen()`), nooit los `os.getenv`; nieuwe variabele ook in `.env.example` en tabel 2.2 van de installatiegids. Geen `detail=str(e)`: onverwachte fouten gaan naar de centrale handler (`omnitwin/fouten.py`, 500 met correlatie-id), een melding voor de gebruiker is een `GebruikersFout`. Een route is `def`, tenzij hij iets `await`; synchroon werk daarin via `run_in_threadpool`. UUID-parameters typeren als `uuid.UUID` (422 bij ongeldige invoer).

### Z-Score Calculations
Z-scores are computed dynamically per request, relative to a reference group defined by `gebiedstype` + `gemeente` (not globally). Eén bron: de SQL-functies in `db/schema/08_zscore_referentie.sql` (`zscore_referentie_stats`, `zscore_gebieden`, ...; migratie v21), met parameters en standaardwaarden in `src/omnitwin/services/zscore_referentie.py`. Waterbuurten (`gebieden.metadata->>'water' = 'JA'`) zitten nooit in de referentie; jaarlogica standaard `zelfde_jaar` (referentie = waarden in het jaar van de meest recente waarde van het doelgebied, zoals executive en Kompas werkten); alleen scenario `current`. Schrijf geen eigen referentie-CTE in `report_service.py` of `kompas_service.py`, gebruik deze functies. Methodiek: `docs/3-data-engineering/zscore_methodiek.md` (#66).

### Authentication
Zie `src/omnitwin/routers/auth.py`.
- **Beheeromgeving en web-UI:** sessie. Inloggen via `POST /api/admin/auth/login` (form-data; wachtwoorden bcrypt in `users`). Het cookie `session_token` is `HttpOnly`, `SameSite=lax` en `Secure` volgens `COOKIE_SECURE` (standaard `auto`: alleen bij HTTPS, ook via `X-Forwarded-Proto`); het token staat gehasht (sha256) in `sessions` en verloopt na 12 uur. Het admin-panel gebruikt alleen dit cookie (`admin-panel/src/services/api.ts`), nooit een API-key.
- **Keycloak in de beheeromgeving (#251, ADR 0008):** met `OIDC_ISSUER` gezet logt de beheer-UI in via Keycloak; de backend is de OIDC-client (BFF, `src/omnitwin/oidc_login.py`, routes `/api/admin/auth/oidc/login` en `/oidc/callback`, `GET /api/admin/auth/config`). Sessie in tabel `oidc_sessies` (V029) achter hetzelfde cookie `session_token`; ververst met het refresh token, RP-initiated logout. Realm-rol `beheerder` = `is_admin`. Lokale accounts dan alleen met `LOKAAL_INLOGGEN=true` (noodtoegang); zonder `OIDC_ISSUER` lokaal zoals altijd. Geen eigen gebruikersbeheer bouwen: dat is Keycloak. Log alleen `sub`/`preferred_username`. Viewer-login (lezer) volgt.
- **Nieuwe API's (laad-API en verder): altijd `vereis_rol` uit `src/omnitwin/oidc.py`** (#205), bijv. `principal: Principal = Depends(vereis_rol("dataset:{dataset_id}:laden", "datasets:laden"))`; `{dataset_id}` komt uit de path-parameter. Verder `vereis_principal` (alleen geldig token) en `principal_optioneel` (Principal of `None`). Controle: handtekening via de JWKS van de issuer (gecachet, ververst bij onbekende `kid`), `iss` = `OIDC_ISSUER`, `aud` bevat `OIDC_AUDIENCE` (`omnitwin-api`), `exp`/`nbf` met 30 s speling, alleen asymmetrische algoritmes. Rollen = realm-rollen + client-rollen van `omnitwin-api`. Fouten als Problem Details: `401` (met `WWW-Authenticate: Bearer`), `403` zonder rol, `503` als `OIDC_ISSUER` leeg is of de sleutels niet op te halen zijn. Achter Traefik haalt de backend discovery en sleutels via `OIDC_INTERN_URL` (`http://keycloak:8080/auth/realms/omnitwin`). Nooit tokens of claims met persoonsgegevens loggen; bij een weigering alleen `client_id`/`jti`. Testendpoint: `GET /api/oidc/ik` (client en rollen). Gebruik op nieuwe routes geen sessie of `X-Admin-Key`.
- **Oude beheerroutes** (`/api/admin/*`, `/api/visualisatie/admin/*`) houden `vereis_admin` (hieronder): sessie (lokaal of OIDC), bearer-token met rol `beheerder`, of `X-Admin-Key`.
- **Scripts:** header `X-Admin-Key` met de waarde van `ADMIN_API_KEY` uit `.env` (minimaal 32 tekens; leeg of een voorbeeldwaarde = uitgeschakeld). De tabel `api_keys` speelt geen rol bij de autorisatie.
- **Autorisatie:** `vereis_admin` hangt op routerniveau aan alle beheerroutes (`/api/admin/*` behalve auth, `/api/visualisatie/admin/*`): zonder sessie, token of key `401`, zonder `is_admin` of rol `beheerder` `403`. Publieke routes (kaart, Kompas, rapporten, chat) hebben dezelfde rechten als een anonieme bezoeker (#65); zie de installatiegids, Beveiliging.

### LLM / AI
- **Chat intent classification is rule-based** (deterministic), not LLM-driven. LLM (Ollama/Qwen, local) is used only for narrative summaries (capped at ~80 words). LLM-config en system-prompts staan in databasetabellen (`llm_config`, `system_prompts`), niet hardcoded.
- `ai_search_service.py` zoekt indicatoren met begrippen en synoniemen (`db/stuurdata/synoniemen.json`), woorden uit de naam en betekenis (rangschikking en afkap in `services/zoektaal.py`, #233). Betekenis: `sentence-transformers` (model `intfloat/multilingual-e5-small`, lazy-loaded; model, gepinde revisie en schaalgrenzen in `src/omnitwin/services/embedding_model.py`, in de image onder `/opt/models` als float16, container draait met `HF_HUB_OFFLINE=1`) en `pgvector`: embeddings staan in tabel `indicator_embeddings` (kolom `embedding vector(384)`, `tekst_hash` sinds V028, HNSW-index met cosine ops), bevraagd via de `<=>`-operator. Embeddings bijwerken: `services/indicator_embeddings.py` (`herbereken_embeddings`). Kwaliteit meten: `scripts/ai/evalueer_assistent.py` met `tests/data/assistent_evaluatie.json`. `kompas_service.py` gebruikt géén vector-zoekopdrachten.

### Color System
Colorblind-safe diverging palettes are used throughout. Palette definitions live in database table `color_schemas` (beheer via de admin-API, publiek via `/api/visualisatie/paletten`). Dynamic color generation (including diverging scales) is in `color_scale_service.py`. `static/css/colors/` is een losse demopagina met het SWF-kleurenschema, geen bron voor de app.

**Thema per organisatie (#89):** UI-kleuren, lettertypen, ruimte en hoeken komen uit NL Design System-tokens (`--basis-*`, plus `--d-omnitwin-*`) in `static/css/themes/<thema>.css` (`d-omnitwin` standaard, `swf`); de variabelen in `styles.css` lezen die tokens met de standaardwaarde als fallback. Nieuwe UI-kleur = token (of een `color-mix()` daarvan, zoals `--tint`) gebruiken, geen vaste hexwaarde; ook niet in inline styles in `app.js`/`kompas.js` (Chart.js: `themaKleur()`). Een nieuw componenttoken `--d-omnitwin-*` komt in álle thema's, in alle drie de blokken; de test faalt anders. Kaartselectie (goud) en datakleuren blijven vast. Datakleuren (Z-score, kaart, Kompas) nooit in een thema; die blijven in `color_schemas`. Inlogpagina van Keycloak: `deploy/keycloak/themes/<thema>/`, één per viewerthema. Contrast en opbouw: `tests/test_thema.py`. Uitleg en eigen thema maken: [`docs/9-beheer/thema-s.md`](docs/9-beheer/thema-s.md).

### Database
Schema is in `db/schema/schema_latest.sql`. Key tables: `gebieden` (areas/buurten), `indicatoren` (metrics), `gebied_data` (measurements), `kompas_titels` / `kompas_themas` / `kompas_onderdelen` / `kompas_indicator_mapping` (thematic hierarchy, samengevoegd in view `v_kompas_hierarchie`). In Docker laadt `db-init` bij een lege database dit schema plus `db/schema/06_pg_featureserv_views.sql` en `07_postgisftw_functions.sql`; daarna past de migratierunner (`python -m omnitwin.migraties`, `src/omnitwin/migraties.py`) de migraties uit `db/migraties/` toe die nog niet in tabel `schema_migraties` staan, ook op een bestaande database. Bij elke run werkt `docker-entrypoint.sh` daarna de rollen en het schema `api` bij (`db/migraties/R__api_rollen.sql`, herhaalbaar). Stuurdata (seed, Kompas-indeling, indicatordefinities) staat in `db/stuurdata/`. **Schemawijziging:** nieuw bestand `db/migraties/V<nnn>__<naam>.sql` (volgend nummer, idempotent); een toegepaste migratie nooit aanpassen, ook niet een bestand dat hij met `\ir` inleest (de runner waarschuwt bij een andere checksum; V021 leest `db/schema/08_zscore_referentie.sql`, zie `db/README.md`). De runner neemt een advisory lock, dus twee runs tegelijk kan. `db/migraties/baseline/` bevat oude migraties die al in `schema_latest.sql` zitten; die draait de runner niet. Views zoals `vw_gebied_kaart_basis` gebruiken herkenbare aliassen — geen alias waarbij de tabelnaam niet herkenbaar terugkomt. SQLAlchemy uses a large connection pool (`pool_size=20, max_overflow=20`) for concurrent map layer queries. Let op water-buurt filtering (watergebieden worden uitgesloten van statistiek).

### Eigen organisatie (instellingsdata, #231)
Eén instantie hoort bij één organisatie (ADR 0007). Naam, korte naam, OIN, CBS-gemeentecode(s) van het eigen gebied, standaard-benchmarkprovincie, contactadres, footer-logo's en thema (huisstijl, `static/css/themes/<thema>.css` als dat bestaat) staan in tabel `organisatie` (één rij; migratie `V027__organisatie.sql`, vulling `db/stuurdata/organisatie.sql`, door `docker-entrypoint.sh` geladen als de tabel leeg is). **Regel:** code neemt nooit een vaste organisatie, gemeentecode, provincie, logo of contact aan; backend leest `omnitwin.services.organisatie` (`lees_organisatie`, `eigen_gemeente_code`), frontend en beheer lezen `GET /api/organisatie`, templates krijgen `organisatie` mee. De Kompas-standaard komt uit `kompas_configuraties.is_standaard` (`/api/kompas/standaard/hierarchie`), niet uit ID 1. `tests/unit/test_organisatie.py` faalt bij een nieuwe `'1900'` in de runtimecode.

### Admin UI (React/TypeScript)
Aparte codebase in `admin-panel/`, eigen build-stap nodig. API calls via relatieve paden, geproxied naar de backend op poort 8000.

### Data-engineering (ETL)
Scripts in `ETL/` en `scripts/` zijn standalone, geen deel van de web-API. CBS, RIVM, BAG zijn de primaire bronnen. Zie de Commands-sectie hierboven voor het onderscheid tussen initiële bootstrap (`init_data/`) en doorlopende uitbreiding (`ETL/`).

## Documentation
- `CHANGELOG.md` — wijzigingen per versie, met migratie-instructies; `[Unreleased]` = wat er op `main` staat
- `docs/STATE.md` — historische momentopname van de systeemstatus tot 0.1.0; niet leidend
- `docs/INDEX.md` — documentation router by domain
- `docs/9-beheer/installatie.md` — **de** installatiegids (Docker), ook voor beheerders
- `docs/9-beheer/beheerhandleiding.md` — beheer in productie (#257): back-up en herstel (`scripts/beheer/backup.sh`, `restore.sh`, `hersteltest.sh`), bijwerken en terugrollen, Keycloak, leveringen, incidenten, acceptatie naast productie. Privacy: `docs/5-secops/privacy-quickscan.md`; toegankelijkheid: `docs/4-ux-design/toegankelijkheid.md` (beide uitgezonderd in `.gitignore`)
- `docs/archief/` — verouderde logboeken en gidsen: `GETTING_STARTED.md` (installatie zonder Docker), `BUILD.md` (sprint changelog), `ROADMAP.md`, `TODO.md`, `BUGFIX.md`. Niet meer bijhouden; taken en bugs staan in de GitHub-issues
- `GOVERNANCE.md`, `SUPPORT.md`, `PARTICIPANTS.md` — governance volgens het OpenWebconcept (#183): eigenaar en beheerder SWF, review bij voorkeur door een andere partij, onderhoud minimaal tot en met 31-08-2027; deelnemers zonder persoonsnamen

## Projectmanagement
De stand van zaken staat in de GitHub-issues en in `CHANGELOG.md`. Elke PR met een merkbare wijziging zet een regel onder `[Unreleased]` (zie `docs/9-beheer/releasebeleid.md`). `docs/STATE.md` wordt niet meer bijgewerkt.

## GitHub workflow

Elke wijziging gaat via GitHub Flow:

1. Issue aanmaken op TLaan/D-OmniTwin
2. Branch aanmaken: `feature/<issue-nr>-<korte-naam>`
3. Commits op die branch
4. Pull Request naar `main` met `Closes #<nr>` in de beschrijving
5. Nooit direct op `main` pushen

Versies en releases: Semantic Versioning, één bron `VERSION`, conventional commits, regel in `CHANGELOG.md` onder `[Unreleased]`, release-branch `release/<MAJOR>.<MINOR>` met tag `v<versie>`. Zie `docs/9-beheer/releasebeleid.md`.
**Nieuwe functionaliteit = een use case erbij** (`usecases/<naam>/`: data, inrichting, stappen, verwachte uitkomst). De use case werkt out of the box, ook zonder AI-sleutel, en wordt getoetst door `tests/integration/test_usecases.py`. Zie CONTRIBUTING.md.

Use cases (vanaf 0.3.0): **leidend is de [Use Case Specificatie 1.0](docs/specificaties/usecase/README.md)** (normatief, met de schema's in `docs/specificaties/usecase/1.0/`; ADR 0006); `usecases/README.md` is het overzicht. Elk `usecase.json` heeft `"specificatie": "1.0"`; een nieuw manifestveld begint met een wijziging van de specificatie en het schema (geen onbekende velden).
- **Een use case is declaratief: geen code of uitvoerbare bestanden.** Alleen `usecase.json` (manifest: `naam` = mapnaam, `versie` semver, `titel`, `vraag`, `gebruiker`, `status`, `afhankelijk_van`, `rechten`, `datasets[]`, `controles[]`), `README.md`, `datasets/<id>.json` (DCAT `beschrijving` + `laadprofiel` + `bron` + `bewerkingen` + `levering`) en kleine statische `.json`/`.csv`. Schema's: `docs/specificaties/usecase/1.0/usecase.schema.json`, `dataset.schema.json`, `bewijs.schema.json`. Een nieuwe soort bron = een nieuwe kernadapter in `src/omnitwin/bronadapters/` via een PR met tests; bewerkingen zijn een vaste lijst (geen expressies). `hittestress/maak_data.py` is de enige uitzondering en wordt uitgefaseerd.
- **Bronnen:** open data (CBS, PDOK, BAG, RIVM) nooit in de repo; de adapter downloadt (https, allowlist van domeinen, cache in `$DATA_CACHE`). Interne data via `SWF_DUMP_DIR`, `SWF_DOCS_DIR`, `SWF_GEO_DIR`, `SWF_DB_DUMP`; geen meetwaarden, hostnamen, secrets of persoonsnamen in de use case.
- **`afhankelijk_van`:** namen (geen paden), of `{"naam", "versie": ">=0.1.0", "optioneel": true}`; topologische volgorde, fout bij cyclus, onbekende naam of versie. `status: "ontwerp"` en wat er niet-optioneel van afhangt, wordt overgeslagen. Extern (`{"naam", "bron": <absolute URL>, "versie": <tag>}`) is nog niet ondersteund.
- **Uitvoerder:** `python -m omnitwin.usecases lijst | boom <naam> | index | controleer <naam> | installeer <naam>|--alle | test <naam>`; acceptatietests per use case in `tests/integration/test_usecase_<naam>.py` (overgeslagen zolang de laad-API ontbreekt). `controleer` maakt en valideert de leveringen lokaal (zonder API). Na een nieuwe of gewijzigde use case: `python -m omnitwin.usecases index` (de unittest faalt anders). Eerst de use case met toetsbare `controles`, dan bouwen.

`gh` CLI: `/usr/bin/gh` — gebruik altijd met `GH_PAGER=cat` om pager-blokkering te voorkomen.
