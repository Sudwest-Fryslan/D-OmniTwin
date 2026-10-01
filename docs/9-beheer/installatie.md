# Installatie en beheer van D-OmniTwin

Dit is de installatiegids voor beheerders. Andere installatiedocumenten in deze repository (`docs/archief/BUILD.md`, `docs/archief/GETTING_STARTED.md`, het stappenplan voor dump-migratie) zijn verouderd of aanvullend; bij verschillen geldt deze gids.

De gids gaat uit van een Linux-server of een werkplek met Docker. Alle commando's draai je in de map van de repository.

**Status:** D-OmniTwin is een pre-release. Lees [Beveiliging](#beveiliging) voordat je de installatie buiten je eigen netwerk bereikbaar maakt.

---

## 1. Vereisten

| Wat | Minimaal |
|-----|----------|
| Docker Engine met Compose v2 (`docker compose`, niet `docker-compose`) | Docker 24, Compose 2.20. Op Windows en macOS: Docker Desktop |
| Git | elke recente versie |
| Geheugen | 4 GB vrij voor de stack, 8 GB aanbevolen. Een lokaal taalmodel (Ollama) komt daar bovenop |
| Schijf | ± 6 GB vrij: backend-image ± 1,7 GB uitgepakt (Docker Desktop toont ± 2,3 GB; inclusief het embeddingmodel, circa 90 MB), database-image ± 1,1 GB, overige images ± 0,4 GB, plus de database en de build-cache (± 2 GB, op te ruimen met `docker builder prune`) |
| Poort | 80 op de host vrij (of een andere poort, zie `OMNITWIN_HTTP_PORT`) |
| Internet tijdens de installatie | voor Docker Hub, PyPI, de PyTorch-index en HuggingFace (images bouwen). Daarna draait de stack zonder internet, ook AI-zoeken. De kaart gebruikt PDOK-achtergrondkaarten in de browser; een token is niet nodig |

Controleer:

```bash
docker --version
docker compose version
```

**Imagegrootte.** Backend en `db-init` gebruiken dezelfde image (`<projectnaam>-backend`); die wordt één keer gebouwd. Uitgepakt is hij ± 1,7 GB, de download (gecomprimeerd) ± 0,5 GB. Het grootste deel is PyTorch (CPU, ± 0,6 GB), dat het embeddingmodel voor AI-zoeken nodig heeft. De image bevat alleen wat de backend en `db-init` gebruiken; voor ETL-scripts installeer je de extra pakketten lokaal uit `requirements-etl.txt` (zie [`ETL/ETL_DOCUMENTATION.md`](../../ETL/ETL_DOCUMENTATION.md)). De CI faalt als de image boven 1900 MiB uitgepakt komt (#157).

**Windows:** gebruik Docker Desktop met de WSL2-backend. De voorbeelden hieronder zijn voor een bash-shell; gebruik op Windows **Git Bash** (wordt met Git for Windows meegeleverd, inclusief `openssl`). Git mag regeleinden omzetten (`core.autocrlf=true`): `.gitattributes` houdt de shell-scripts op LF, zodat de containers werken.

---

## 2. Installatie

### 2.1 Code ophalen

```bash
git clone https://github.com/TLaan/D-OmniTwin.git
cd D-OmniTwin
```

### 2.2 `.env` aanmaken

```bash
cp .env.example .env
```

Vul in `.env` alleen het databasewachtwoord in. Al het andere heeft een werkende standaard:

```bash
openssl rand -hex 24   # waarde voor DATABASE_PASSWORD
```

Gebruik alleen letters en cijfers (zoals hierboven): tekens als `@ : / # % $` breken de database-URL's.

| Variabele | Wat invullen |
|-----------|--------------|
| `COMPOSE_FILE=docker-compose.yml` | **Verplicht voor een installatie.** Haal het `#` weg. Zonder deze regel laadt `docker compose` ook de ontwikkelinstellingen (zie [Ontwikkelmodus](#3-ontwikkelmodus)). |
| `OMNITWIN_HTTP_PORT` | Optioneel. Poort op de host, standaard `80`. |
| `DATABASE_PASSWORD` | **Verplicht.** Het gegenereerde wachtwoord. |
| `SECRET_KEY` | **Verplicht invullen**, al gebruikt de code hem nu nog niet. |
| `ADMIN_API_KEY` | Voor scripts: wie deze waarde in de header `X-Admin-Key` meestuurt, heeft beheerrechten. Minimaal 32 tekens (`openssl rand -hex 32`). Een lege of voorbeeldwaarde schakelt de header uit. De beheeromgeving gebruikt hem niet; die werkt met inloggen. |
| `ADMIN_USER`, `ADMIN_PASSWORD` | Het eerste beheeraccount. Laat je `ADMIN_PASSWORD` op de voorbeeldwaarde staan of leeg, dan wordt er een wachtwoord gegenereerd (zie [2.4](#24-eerste-keer-inloggen)). |
| `DEBUG` | `true` zolang je zonder HTTPS draait, anders werkt inloggen in de browser niet (zie [Beveiliging](#beveiliging)). Met HTTPS: `false`. |
| `LOAD_SAMPLE_DATA` | `true`: de sample dataset laden bij de eerste start. `false`: alleen stuurdata (configuratie, zonder buurten). Zie [Data](#4-data). |
| `DATABASE_NAME`, `DATABASE_USER` | Mogen blijven staan. Wijzig ze alleen vóór de eerste start. |
| `DATABASE_HOST`, `DATABASE_PORT` | Laten staan. De containers negeren deze en gebruiken `postgres:5432`; ze gelden alleen voor scripts op de host in ontwikkelmodus. |
| `DATABASE_SSLMODE` | `prefer` laten staan. De database is alleen binnen het Docker-netwerk bereikbaar en heeft geen TLS; `require` werkt hier niet. |
| `CORS_ORIGINS` | Alleen nodig als andere websites de API aanroepen. De app zelf draait op hetzelfde adres. |
| `OLLAMA_*` | Optioneel, zie [LLM](#7-llm-optioneel). |
| `LOG_ALERT_*`, `SMTP_*` | Nog niet in gebruik (#47). |
| `DATABASE_PASSWORD` | **Verplicht.** Het gegenereerde wachtwoord. Wijzig het niet meer na de eerste start. |
| `ADMIN_PASSWORD` | Aanbevolen. Wachtwoord van het eerste beheeraccount (`admin`). Leeg: er wordt eenmalig een wachtwoord gegenereerd (zie [2.4](#24-eerste-keer-inloggen)). |
| `COMPOSE_FILE=docker-compose.yml` | Staat al aan: alleen de installatie-instellingen. Ontwikkelaars halen deze regel weg (zie [Ontwikkelmodus](#3-ontwikkelmodus)). |
| `DEBUG` | `true` zolang je zonder HTTPS draait, anders werkt inloggen niet (zie [Beveiliging](#beveiliging)). Met HTTPS: `false`. |
| Optioneel | Poort (`OMNITWIN_HTTP_PORT`), demodata via de use cases (`LOAD_SAMPLE_DATA`; `false` = product zonder data, zie [Data](#4-data)), lokale AI (`OLLAMA_HOST`, zie [LLM](#7-llm-optioneel)) en `ADMIN_API_KEY` (alleen voor scripts; leeg = uitgeschakeld, laat nooit een voorbeeldwaarde staan). De standaardwaarden staan in `.env.example`. |

Bescherm het bestand: `chmod 600 .env`.

### 2.3 Starten

```bash
docker compose up -d --build
```

De eerste keer duurt dit lang (10 tot 30 minuten): de backend-image installeert onder meer PyTorch en GDAL. Daarna starten de services in deze volgorde:

1. `postgres` (PostGIS met pgvector) wordt *healthy*.
2. `db-init` draait één keer en stopt. Bij een **lege** database maakt hij het schema aan (`db/schema/schema_latest.sql` en de views voor de kaart), laadt de stuurdata (`db/stuurdata/`) en eventueel de sample dataset, en maakt het beheeraccount aan. Bestaat de tabel `gebieden` al, dan slaat hij dit allemaal over. Hij overschrijft dus nooit bestaande data.
   In beide gevallen past hij daarna de schemamigraties uit `db/migraties/` toe die nog niet in de tabel `schema_migraties` staan (`python -m omnitwin.migraties`, #54).
   Daarna genereert hij, ook bij een bestaande database, de embeddings voor AI-zoeken en de chat (`scripts/ai/genereer_embeddings.py`), voor alle actieve indicatoren zonder embedding, ook concepten. Het model daarvoor (`all-MiniLM-L6-v2`) zit al in de image; zie [Embeddingmodel](#embeddingmodel-offline). Lukt het genereren niet, dan staat er een waarschuwing in de log en gaat de installatie gewoon door; AI-zoeken en de chat vinden dan geen indicatoren.
   Daarna werkt hij altijd de databaserollen en het schema `api` voor PostgREST en pg_featureserv bij (`db/migraties/R__api_rollen.sql`, zie [Beveiliging](#beveiliging)). Dat raakt geen data.
   Daarna genereert hij, ook bij een bestaande database, de embeddings voor AI-zoeken en de chat (`scripts/ai/genereer_embeddings.py`), voor alle actieve indicatoren zonder embedding, ook concepten. Daarvoor downloadt hij de eerste keer het model `all-MiniLM-L6-v2` (circa 90 MB) van HuggingFace. Lukt dat niet, bijvoorbeeld zonder internet, dan staat er een waarschuwing in de log en gaat de installatie gewoon door; AI-zoeken en de chat vinden dan geen indicatoren.
3. `backend` (FastAPI), `postgrest` en `pg_featureserv` starten, `traefik` stuurt het verkeer door.

Controleer:

```bash
docker compose ps -a
```

Goed is: `postgres` en `backend` staan op `Up ... (healthy)`, `traefik`, `postgrest` en `pg_featureserv` op `Up`, en `db-init` op `Exited (0)`. De backend heeft tot een minuut nodig om *healthy* te worden.

### 2.4 Eerste keer inloggen

Heb je `ADMIN_PASSWORD` ingevuld, dan log je in met `ADMIN_USER` (standaard `admin`) en dat wachtwoord.

Heb je dat niet gedaan, dan staat het gegenereerde wachtwoord **eenmalig** in de log van `db-init`:

```bash
docker compose logs db-init
```

Zoek naar `ADMIN_PASSWORD niet ingesteld. Gegenereerd wachtwoord voor 'admin'`. Het wachtwoord staat op de regel daaronder. Het wordt niet opgeslagen; bewaar het direct.

De log van `db-init` toont ook een `ADMIN_API_KEY` ("BEWAAR DEZE KEY"). Die wordt nu niet gebruikt: de backend accepteert alleen de `ADMIN_API_KEY` uit `.env`, en alleen voor scripts.

Wachtwoord later wijzigen (vraagt interactief om een nieuw wachtwoord):

```bash
docker compose exec backend python init_data/scripts/create_admin.py --reset-password
```

### 2.5 Adressen

Met de standaardpoort 80 (anders `http://<host>:<OMNITWIN_HTTP_PORT>/...`):

| Adres | Wat |
|-------|-----|
| `http://<host>/` | De applicatie (kaart, Kompas, chat) |
| `http://<host>/admin/` | Beheeromgeving |
| `http://<host>/docs` | API-documentatie van de backend (Swagger) |
| `http://<host>/api/data/` | PostgREST: alleen-lezen REST-API op de views en functies in schema `api` |
| `http://<host>/api/geo/` | pg_featureserv: OGC API Features, bijvoorbeeld `/api/geo/collections` |
| `http://<host>/health` | Healthcheck van de backend |
| `http://<host>/.well-known/security.txt` | Meldpunt voor kwetsbaarheden (zie [Beveiliging](#securitytxt)) |

Alleen Traefik publiceert een poort. De database en de afzonderlijke services zijn van buiten Docker niet bereikbaar.

---

## 3. Ontwikkelmodus

Zonder `COMPOSE_FILE` in `.env` laadt `docker compose` naast `docker-compose.yml` ook `docker-compose.override.yml`. Die voegt toe:

- een bind-mount van de repository over `/app` in `backend` en `db-init`: codewijzigingen zijn direct zichtbaar na een herstart van de backend;
- de database op de host op poort **5433** (`DATABASE_HOST=localhost`, `DATABASE_PORT=5433` in `.env`, voor scripts en tools zoals pgAdmin of QGIS);
- het Traefik-dashboard op **http://localhost:8081**.

```bash
docker compose up -d --build
```

Gebruik dit niet voor een installatie: de database en het dashboard zijn dan onbeveiligd bereikbaar. In ontwikkelmodus schrijft `db-init` bovendien een nieuwe `ADMIN_API_KEY` in je `.env`.

Ontwikkelen zonder Docker (Python venv, `run_dev.py`, admin-panel met `npm start`) staat in de [README](../../README.md#-installatie-voor-ontwikkelaars) en [`AGENTS.md`](../../AGENTS.md).

---

## 4. Data

### Sample dataset (standaard)

`db-init` laadt bij de eerste start altijd het product zonder data: stuurdata (scenario's, profielen, prompts), de indicatordefinities en de Kompas-indeling. Met `LOAD_SAMPLE_DATA=true` laadt het daarna de **use cases** uit [`usecases/`](../../usecases/README.md). Elke use case brengt zijn eigen gebieden en waarden mee, gekozen uit de bronbibliotheek [`init_data/sample/`](../../init_data/sample/README.md), plus de inrichting en de teststappen. Een deel van de waarden is demodata. Eén use case laden: `docker compose exec backend python init_data/scripts/laad_usecase.py hittestress`.

Na de use cases laadt `db-init` ook de **CBS Kerncijfers 2019-2026** voor de gebieden die dan in de database staan (`init_data/scripts/laad_cbs.py`). Die data staat niet in git: `db-init` downloadt hem bij CBS en bewaart hem in het volume `bron-cache`; daarna werkt het ook offline. Zonder internet bij de eerste start ontbreken de CBS-reeksen, de rest werkt wel. Zo toont het Kompas-detail met de tijdslider meerdere jaren, bijvoorbeeld voor Inwoners in Bolsward-Noord. Zie [`docs/3-data-engineering/cbs_kerncijfers.md`](../3-data-engineering/cbs_kerncijfers.md).

De sample is bedoeld om de installatie te testen en te demonstreren, niet voor beleid.

### Volledige Fryslân-data

De repository bevat voor heel Fryslân de CBS-buurten (indeling 2024) en de RIVM-indicatoren (`init_data/fryslan/`, zie [`init_data/README.md`](../../init_data/README.md)), en de CBS Kerncijfers 2019-2026 (`init_data/cbs/`). `db-init` laadt die niet vanzelf. Laad ze na de eerste start, als `db-init` klaar is, met een expliciete stap:

```bash
docker compose run --rm db-init python init_data/scripts/seed_fryslan.py --stap alle
```

`docker compose exec backend python init_data/scripts/seed_fryslan.py --stap alle` werkt ook. Alleen de CBS-reeksen opnieuw laden, voor alle gebieden in de database: `docker compose run --rm db-init python init_data/scripts/laad_cbs.py`. Er is geen netwerk nodig.

Dit duurt ongeveer 20 seconden (gemeten: 16 s, waarvan 13 s voor de CBS-reeksen). Het werkt met en zonder sample (`LOAD_SAMPLE_DATA`); de sample-buurten worden dan overschreven door dezelfde buurten uit de Fryslân-data. Verwachte aantallen in de database na sample + Fryslân:

| Tabel | Aantal |
|-------|--------|
| `gemeenten` | 18 (alle Friese gemeenten) |
| `gebieden` | 931 buurten |
| `indicatoren` | 246 (238 uit `indicatoren_seed.json`; namen die de sample al heeft worden aangevuld, niet gedupliceerd) |
| `kompas_indicator_mapping` | 185 |
| `gebied_data` | ± 208.700 (179.749 CBS Kerncijfers 2019-2026 voor 931 buurten, 28.235 RIVM-metingen, plus de use cases) |

- Het script eindigt met een samenvatting per stap (aantal ok en fouten) en geeft exitcode 1 als een stap mislukt of meer dan 1% fouten heeft (`--max-fouten-pct`).
- Opnieuw draaien is veilig: bestaande rijen worden bijgewerkt, er ontstaan geen duplicaten. `load_sample.py` blijft daarna ook werken.
- De CSV bevat ook wijk-, gemeente- en landelijke rijen en buurten buiten Fryslân. Die worden overgeslagen ("gebieden niet in database"); dat is geen fout.
- Het script maakt geen gebruikers of API-keys aan.
- Bekend gat: de 61 buurten van Smallingerland (0090) hebben geen indicatorwaarden. De CSV gebruikt voor Smallingerland de buurtcodes van vóór de indeling 2024.

Losse stappen: `--stap buurten|indicatoren|kompas|waarden`. `init_database.sh` is alleen voor een PostgreSQL zonder Docker.

### Eigen gemeente of andere bronnen

Via het ETL-framework in `ETL/`; zie [`ETL/ETL_DOCUMENTATION.md`](../../ETL/ETL_DOCUMENTATION.md). Dit is nog gericht op ontwikkelaars.

---

## 5. Bijwerken

```bash
git pull
docker compose up -d --build
```

`db-init` draait opnieuw, ziet dat de database bestaat en laat de data met rust. Wel past hij de nieuwe schemamigraties toe: elk bestand `db/migraties/V<nnn>__<naam>.sql` dat nog niet in de tabel `schema_migraties` staat, op volgorde, en registreert het daar (#54). De rollen en het schema `api` voor PostgREST en pg_featureserv werkt hij altijd bij (`R__api_rollen.sql`, zie [Beveiliging](#beveiliging)).

Een database van vóór 0.2.0 heeft nog geen tabel `schema_migraties`. De eerste keer maakt de runner die aan en draait hij V018 t/m V022 opnieuw; die zijn idempotent. Bekijken wat is toegepast en wat openstaat:

```bash
docker compose run --rm db-init python -m omnitwin.migraties --status
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM schema_migraties"'
```

Maak eerst een backup (zie hieronder). Lees bij een nieuwe versie [`CHANGELOG.md`](../../CHANGELOG.md).

### Embeddingmodel (offline)

AI-zoeken en de chat gebruiken het model [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (licentie Apache-2.0). Het model en de revisie (een commit-hash van HuggingFace) staan op één plek: `src/omnitwin/services/embedding_model.py`.

- `docker compose build` downloadt die revisie naar `/opt/models/all-MiniLM-L6-v2` in de image. Dat maakt de image circa 90 MB groter (91,8 MB; totaal ± 1,7 GB uitgepakt). Alleen bij het bouwen is HuggingFace nodig.
- Backend en `db-init` draaien met `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` en `HF_HUB_DISABLE_TELEMETRY=1`: geen download en geen telemetrie, ook niet bij een nieuwe container. AI-zoeken werkt zonder internet.
- Het model staat buiten `/app`, dus ook in ontwikkelmodus (bind-mount van de repo over `/app`) blijft het zichtbaar.
- Controleren: `/api/ai/health` toont onder `embedding_model` de revisie, `lokaal` en `offline`.

Model bijwerken naar een nieuwere revisie:

1. Zoek de commit-hash op `https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/commits/main` en zet die in `MODEL_REVISIE` in `src/omnitwin/services/embedding_model.py`.
2. Bouw opnieuw: `docker compose up -d --build`.
3. Bereken de embeddings opnieuw, want vectoren van verschillende revisies passen niet bij elkaar: `docker compose exec backend python scripts/ai/genereer_embeddings.py --opnieuw`.

Een ander model met een andere dimensie (niet 384) vraagt ook een schemawijziging van `indicator_embeddings`.

---

## 6. Beheer

### Status en logs

```bash
docker compose ps -a
docker compose logs -f backend          # of: db-init, postgres, postgrest, pg_featureserv, traefik
docker compose logs --tail 100 backend
```

De backend schrijft ook naar de databasetabel voor logs; die zijn in te zien via de beheeromgeving.

### Stoppen en starten

```bash
docker compose stop        # stoppen, alles blijft bewaard
docker compose up -d       # weer starten
docker compose down        # containers verwijderen; de database (volume pgdata) blijft bewaard
```

### Backup

Alle data staat in het Docker-volume `pgdata`. Maak een dump:

```bash
mkdir -p backups
docker compose exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/omnitwin.dump'
docker compose cp postgres:/tmp/omnitwin.dump backups/omnitwin-$(date +%F).dump
docker compose exec postgres sh -c 'rm /tmp/omnitwin.dump'
```

Dit werkt ook op Windows (Git Bash). Gebruik in PowerShell geen `pg_dump ... > bestand`: PowerShell 5 verminkt binaire uitvoer bij omleiden. De `sh -c '...'`-vorm voorkomt ook dat Git Bash `/tmp/...` omzet naar een Windows-pad.

### Restore

Terugzetten in een lege installatie:

```bash
docker compose down -v                 # LET OP: verwijdert de huidige database
docker compose up -d postgres
docker compose cp backups/omnitwin-JJJJ-MM-DD.dump postgres:/tmp/omnitwin.dump
docker compose exec postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner /tmp/omnitwin.dump'
docker compose up -d
```

Wacht na `up -d postgres` tot `docker compose ps` voor `postgres` *healthy* toont. `pg_restore` eindigt met drie meldingen `schema "tiger" / "tiger_data" / "topology" already exists` en `errors ignored on restore: 3` (exitcode 1). Die zijn onschuldig: de PostGIS-image maakt deze schema's zelf al aan. Andere fouten zijn dat niet. Na de restore bestaat de tabel `gebieden`, dus `db-init` slaat de initialisatie over. Een dump van een oudere versie heeft mogelijk de migraties uit [Bijwerken](#5-bijwerken) nodig.

Voor het overzetten van een complete database naar een andere organisatie, zie ook [`stappenplan_docker_installatie_externe_organisatie.md`](./stappenplan_docker_installatie_externe_organisatie.md) (aanvullend).

### Opnieuw beginnen

```bash
docker compose down -v
docker compose up -d
```

`-v` verwijdert het volume `pgdata` en daarmee alle data. `db-init` richt de database daarna opnieuw in.

### Eigen logo

Het logo linksboven, het favicon en het logo in het beheerscherm en de rapporten komen uit één bestand: `static/images/beeldmerk.svg`. Standaard staat daar een neutraal, tijdelijk D-OmniTwin-beeldmerk (#83). Er is geen instelling in `.env` voor nodig.

Eigen logo gebruiken:

- **Vervangen:** zet je eigen bestand op `static/images/beeldmerk.svg` en bouw opnieuw (`docker compose up -d --build`).
- **Mounten (zonder de code aan te passen):** maak naast `docker-compose.yml` een bestand `docker-compose.logo.yml`:

  ```yaml
  services:
    backend:
      volumes:
        - ./mijn-logo.svg:/app/static/images/beeldmerk.svg:ro
  ```

  Voeg het toe aan `COMPOSE_FILE` in `.env` (scheidingsteken `:` op Linux en macOS, `;` op Windows):

  ```
  COMPOSE_FILE=docker-compose.yml:docker-compose.logo.yml
  ```

  Daarna `docker compose up -d`. Een update van D-OmniTwin overschrijft je logo dan niet.

Aandachtspunten:

- Gebruik een **SVG** en houd de bestandsnaam `beeldmerk.svg`. Een PNG werkt ook als je hem onder die naam mount, maar het favicon wordt dan minder scherp.
- Het logo staat in de header op een gekleurd verloop (blauw/groen) en in het beheerscherm op een donkere achtergrond. Kies een versie met een eigen vlak of een lichte variant, zodat het leesbaar blijft. Er staat geen kleurfilter op: je logo houdt zijn eigen kleuren.
- Het logo wordt getoond op 36 tot 56 pixels hoog; een (bijna) vierkant logo werkt het best.
- Het PWA-pictogram van het beheerscherm (`static/admin-panel/favicon.ico`, `logo192.png`, `logo512.png`) is een rasterversie van het standaardbeeldmerk. Moderne browsers tonen het SVG-bestand; vervang deze PNG/ICO-bestanden alleen als je ook dat pictogram wilt aanpassen.

---

## 7. LLM (optioneel)

De chat en de samenvattingen gebruiken een lokaal taalmodel via [Ollama](https://ollama.com). Zonder Ollama werken kaart, Kompas en rapportage gewoon.

1. Installeer Ollama op de host en haal een model op, bijvoorbeeld `ollama pull qwen3:30b-instruct` (groot; een kleiner model zoals `qwen3:4b-instruct` kan ook). Gebruik een *instruct*-variant: `qwen3:30b` zonder toevoeging is de 'thinking'-variant en is traag.
2. Op Linux: laat Ollama op alle interfaces luisteren (`OLLAMA_HOST=0.0.0.0` in de service-omgeving van Ollama), anders kan de container er niet bij. Docker Desktop (Windows, macOS) regelt dit zelf.
3. Laat in `.env` `OLLAMA_HOST` op de standaard staan (`http://host.docker.internal:11434`), of zet het adres van je Ollama-server.
4. Zet in de beheeromgeving onder **AI Configuratie** de API-URL op `http://host.docker.internal:11434` en kies het model. **Dit is nodig:** de stuurdata zet hier `http://localhost:11434`, en deze instelling gaat vóór `OLLAMA_HOST`. Vanuit de container wijst `localhost` naar de container zelf.

### Andere aanbieders via de LiteLLM-gateway

De optionele gateway (compose-profiel `llm-gateway`, [ADR 0001](../2-architectuur/adr/0001-llm-koppeling-openai-standaard.md)) kent vaste aliassen ([`deploy/litellm/config.yaml`](../../deploy/litellm/config.yaml)):

| Alias | Model | Sleutel in `.env` |
|---|---|---|
| `d-omnitwin-default`, `d-omnitwin-ollama` | lokaal Ollama (`OLLAMA_MODEL`) | — |
| `d-omnitwin-claude` | Anthropic `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| `d-omnitwin-openai` | OpenAI `gpt-4o-mini` | `OPENAI_API_KEY` |
| `d-omnitwin-gemini` | Google `gemini-3.8-flash` | `GEMINI_API_KEY` |

1. Zet in `.env` `LITELLM_MASTER_KEY=sk-…` en `LLM_API_KEY=<zelfde waarde>`, plus de sleutel(s) van de aanbieder. Sleutels staan **alleen in `.env`**, nooit in de database, in `config.yaml` of in git. Een lege sleutel betekent: aanbieder niet beschikbaar.
2. Start met de gateway: `docker compose --profile llm-gateway up -d`.
3. Kies de aanbieder (voegt een rij toe aan `llm_config`; de app gebruikt de nieuwste):

   ```bash
   docker compose exec backend python scripts/llm/kies_provider.py beschikbaar   # wat kan er
   docker compose exec backend python scripts/llm/kies_provider.py gemini        # ollama|claude|openai|gemini|direct-ollama
   docker compose exec backend python scripts/llm/kies_provider.py status        # wat is actief
   ```

   Het script weigert een aanbieder zonder sleutel of als de gateway de alias niet kent. `direct-ollama` gaat buiten de gateway om (`OLLAMA_HOST`/`OLLAMA_MODEL`).
4. Vergelijken: `python scripts/llm/vergelijk_providers.py --base-url http://localhost` draait vaste scenario's (chat en rapport voor Bolsward-Zuidoost en Workum) per beschikbare aanbieder en schrijft een rapport in `docs/testcases/llm-vergelijking/`. Daarna staat de oorspronkelijke configuratie weer actief.

**Let op (AVG, IAMA):** met `claude`, `openai` of `gemini` verlaten vragen, kaartcontext en indicatorwaarden de organisatie en gaan naar een externe aanbieder. Doe dat alleen met de sample dataset of na een afweging (verwerkersovereenkomst, IAMA/DPIA). Lokaal Ollama houdt alles binnen.

Een gratis Gemini-sleutel (met lage limieten) maak je aan op [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

---

## 8. Problemen oplossen

| Probleem | Oplossing |
|----------|-----------|
| `Bind for 0.0.0.0:80 failed: port is already allocated` | Poort 80 is bezet (webserver, IIS, andere stack). Zet `OMNITWIN_HTTP_PORT=8080` (of een andere vrije poort) in `.env` en draai `docker compose up -d`. |
| `dependency failed to start: container ... db-init ... exited (1)` | De initialisatie is mislukt. Bekijk `docker compose logs db-init`. Vaak: verkeerd `DATABASE_PASSWORD` ten opzichte van een bestaand volume (het wachtwoord geldt alleen bij het eerste aanmaken van de database). Oplossing: het oude wachtwoord terugzetten, of `docker compose down -v` als de data weg mag. |
| `backend` wordt niet *healthy* | `docker compose logs backend`. De backend heeft bij de start tot een minuut nodig. Blijft hij *unhealthy*, controleer de databaseverbinding en `.env`. |
| Kaart laadt geen buurten | Controleer `http://<host>/api/geo/collections`. Leeg of fout: kijk in `docker compose logs pg_featureserv`. Na een restore of handmatige schemawijziging: `docker compose restart pg_featureserv postgrest`. |
| Inloggen lukt, maar je blijft op het inlogscherm | Het sessiecookie wordt zonder HTTPS alleen verstuurd als `DEBUG=true`. Zet `DEBUG=true` of zet HTTPS ervoor (zie [Beveiliging](#beveiliging)), en draai `docker compose up -d`. |
| `function similarity(...) does not exist` of ontbrekende tabel `deduplicatie_uitzonderingen` | Oudere database zonder migraties v18/v19. Zie [Bijwerken](#5-bijwerken). |
| Wijziging in `.env` heeft geen effect | `docker compose up -d` (niet `restart`): alleen dan worden containers met de nieuwe waarden opnieuw gemaakt. |
| Windows: `db-init` faalt met `/bin/bash^M: bad interpreter` | Het shell-script is met CRLF uitgecheckt. Controleer of `.gitattributes` aanwezig is, zet het script opnieuw neer met `rm docker-entrypoint.sh && git checkout -- docker-entrypoint.sh` en bouw opnieuw (`docker compose up -d --build`). |
| AI-zoeken of de chat vindt geen indicatoren | Er zijn geen embeddings. Kijk in `docker compose logs db-init` naar `Embeddings niet gegenereerd`; controleer met `/api/ai/health` of het model lokaal staat (anders: `docker compose build`). Draai daarna `docker compose run --rm db-init`: die vult alleen de ontbrekende embeddings aan. Na het goedkeuren van nieuwe beschrijvingen: `docker compose exec backend python scripts/ai/genereer_embeddings.py --opnieuw`. |
| AI-zoeken of de chat vindt geen indicatoren | Er zijn geen embeddings. Kijk in `docker compose logs db-init` naar `Embeddings niet gegenereerd`; meestal kon het model niet worden gedownload. Zorg voor internet en draai `docker compose run --rm db-init`: die vult alleen de ontbrekende embeddings aan. Na het goedkeuren van nieuwe beschrijvingen: `docker compose exec backend python scripts/ai/genereer_embeddings.py --opnieuw`. |
| AI-chat of samenvatting duurt minuten | Het model is een *thinking*-variant. Bij Ollama zijn `qwen3:4b` en `qwen3:30b` zonder toevoeging thinking-varianten; kies in **AI Configuratie** een `*-instruct`-variant (bijvoorbeeld `qwen3:30b-instruct`). Op een laptop zonder GPU blijft een samenvatting met een lokaal model ruim een minuut duren. |
| AI-chat geeft geen antwoord | Controleer in **AI Configuratie** de API-URL: vanuit de container is dat `http://host.docker.internal:11434`, niet `localhost`. Op Linux moet Ollama op alle interfaces luisteren (zie [LLM](#7-llm-optioneel)). |
| Ontwikkelmodus op Windows: backend start niet, `PermissionError: /app/logs/server.log` | De backend draait als niet-root-gebruiker en mag niet schrijven in de gemounte projectmap. Bijgewerkte `docker-compose.override.yml` gebruikt een apart logvolume (#59/#115). |
| Twee installaties op één host | Geef elke installatie een eigen map, een eigen `OMNITWIN_HTTP_PORT` en een eigen projectnaam (`COMPOSE_PROJECT_NAME=...` in `.env`). Traefik routeert alleen naar containers van het eigen project. |

---

## Beveiliging

Stel een installatie **niet** open voor internet of een breed netwerk zolang deze punten openstaan:

- **PostgREST geeft alle tabellen vrij.** `/api/data` draait als de database-eigenaar en toont en wijzigt zonder inloggen alle tabellen, ook `users` en `sessions`. Aparte rollen en een beperkt API-schema volgen in #57. Tot die tijd: alleen in een vertrouwd netwerk, of `/api/data` afschermen in een proxy ervoor.
- **Geen HTTPS in de stack.** Traefik luistert alleen op HTTP. Zet een reverse proxy met TLS ervoor (bijvoorbeeld de bestaande proxy of WAF van je organisatie) en zet dan `DEBUG=false`. Met `DEBUG=false` stuurt de browser het inlogcookie alleen via HTTPS (behalve op `localhost`).
- Houd `.env` geheim: het bevat het databasewachtwoord en de `ADMIN_API_KEY`.

### Wie mag wat

- **Beheerroutes** (`/api/admin/*` behalve inloggen, en `/api/visualisatie/admin/*`) vereisen een ingelogde gebruiker met `is_admin`, of een geldige `X-Admin-Key`. Zonder login: `401`; ingelogd zonder beheerrechten: `403`.
- Nieuwe gebruikers zijn standaard **geen** beheerder (`users.is_admin` standaard `false`). Het account uit `ADMIN_USER` is wel beheerder.
- Sessies staan gehasht in de database en verlopen na 12 uur; verlopen sessies worden bij het inloggen opgeruimd.

**Publiek, zonder inloggen**, zijn:

| Route | Wat |
|-------|-----|
| `/`, `/static/*`, `/admin/*` | De kaartapplicatie en de bestanden van de beheeromgeving (de beheerpagina's zelf vragen om inloggen) |
| `/admin/rapport/*`, `/admin/publiek-rapport/*` | Rapportpagina's |
| `/api/report/*` | Rapportdata en AI-rapportteksten |
| `/api/gebiedsmonitor/*`, `/api/kompas/*` | Gebieden, indicatoren en het Kompas |
| `/api/visualisatie/paletten`, `/api/visualisatie/config/*` | Kleurpaletten voor de kaart |
| `/api/externe-lagen`, `/api/externe-lagen/*` | Externe kaartlagen (lezen en buurten per laag) |
| `/api/chat`, `/api/ai/*` | Chat en AI-zoeken |
| `/api/3dbag/*` | 3D-panden |
| `/api/geo/*` | pg_featureserv (kaartgeometrie) |
| `/api/data/*` | PostgREST, zie het punt hierboven (#57) |
| `/api/admin/auth/login`, `/logout`, `/me` | Inloggen en sessiestatus |
| `/health`, `/api`, `/docs`, `/openapi.json` | Status en API-documentatie |

**Principe:** rapporten hebben dezelfde rechten als een anonieme bezoeker van de kaartapplicatie (besluit #65). Een rapport toont dus niet meer dan de publieke app: geen beheervelden (notities, wie iets beoordeelde of goedkeurde), geen inactieve indicatoren, geen logs of configuratie. De technische details van AI-teksten (`debug_info`: systeemprompts en model) krijgt alleen een ingelogde beheerder.

**Let op, AI-teksten:** `/api/report/narrative/*`, `/api/report/benchmark/narrative` en `/api/chat` starten zonder inloggen een aanroep naar het taalmodel. Rapportteksten worden per gebied een uur gecachet, maar er is geen rate-limit. Gebruik je een externe (betaalde) LLM-aanbieder, scherm deze routes dan af in de proxy ervoor of stel een limiet in.
- **Autorisatie op beheerroutes is nog niet overal op orde** (#65).
- **Standaard geen HTTPS.** Traefik luistert op HTTP. Zet HTTPS aan op een van de twee manieren hieronder, en zet dan `DEBUG=false`. Met `DEBUG=false` stuurt de browser het inlogcookie alleen via HTTPS (behalve op `localhost`).

### PostgREST en pg_featureserv (#57)

PostgREST (`/api/data`) en pg_featureserv (`/api/geo`) verbinden niet als database-eigenaar, maar met eigen rollen. `db-init` maakt ze aan en houdt ze bij (`db/migraties/R__api_rollen.sql`):

| Rol | Gebruikt door | Rechten |
|-----|---------------|---------|
| `authenticator` | PostgREST (verbinding) | `LOGIN`, `NOINHERIT`; mag alleen overschakelen naar `web_anon` |
| `web_anon` | PostgREST (anonieme verzoeken) | `NOLOGIN`; `USAGE` op schema `api`, `SELECT` op de views daarin, `EXECUTE` op `api.get_indicatoren_stats`. Geen schrijfrechten, geen rechten in `public` |
| `featureserv` | pg_featureserv | alleen-lezen op `public.vw_gebieden_features`, `public.omgevingsvisie_deelgebieden` en de functies in `postgisftw` |

PostgREST publiceert alleen schema `api`. Daarin staan alleen views en functies die de frontend en de beheeromgeving lezen: `gemeenten`, `gebiedstypes`, `gebieden` (zonder geometrie), `externe_kaartlagen`, `indicatoren` (zonder interne beheervelden), `vw_gebied_indicator_actueel` en `rpc/get_indicatoren_stats`. Applicatiedata zoals `users`, `sessions`, `api_keys`, `llm_config`, `system_prompts` en de logs is via `/api/data` niet bereikbaar, en schrijven kan anoniem niet. Een nieuw object publiceren: voeg een view of functie toe aan `schema_v23_api_rollen.sql` met de bijbehorende `GRANT` en draai `db-init` opnieuw (`docker compose up -d`).

**Wachtwoord:** `authenticator` en `featureserv` krijgen hetzelfde wachtwoord als `DATABASE_USER` (`DATABASE_PASSWORD`). Er is dus geen extra variabele in `.env`; `db-init` zet het wachtwoord bij elke start opnieuw. De containers van PostgREST en pg_featureserv kregen dat wachtwoord al. Een eigen wachtwoord per rol kan later, zonder de opzet te veranderen.

Kwetsbaarheden melden: zie [`SECURITY.md`](../../SECURITY.md).

### HTTPS aanzetten

HTTPS en HSTS zijn verplicht volgens de [Forum Standaardisatie](https://www.forumstandaardisatie.nl/open-standaarden/verplicht). Kies één manier:

**A. Achter de TLS-proxy van je organisatie (aanbevolen).** De proxy of WAF handelt het certificaat af en stuurt door naar `http://<host>:<OMNITWIN_HTTP_PORT>`. Laat de stack zoals hij is en zet `DEBUG=false`. De proxy moet zelf HSTS sturen (`Strict-Transport-Security: max-age=31536000`) en HTTP doorsturen naar HTTPS; Traefik ziet alleen HTTP en zet die header dan niet.

**B. Traefik zelf met Let's Encrypt.** Voor een server die direct bereikbaar is, met een DNS-naam en poort 80 en 443 open. Gebruik het voorbeeld [`deploy/traefik/tls.example.yml`](../../deploy/traefik/tls.example.yml). Zet in `.env`:

```bash
COMPOSE_FILE=docker-compose.yml:deploy/traefik/tls.example.yml   # Windows: ; in plaats van :
OMNITWIN_DOMAIN=omnitwin.example.nl
ACME_EMAIL=beheer@example.nl     # functioneel adres voor meldingen van Let's Encrypt
DEBUG=false
```

en draai `docker compose up -d`. HTTP gaat dan met een redirect naar HTTPS, en HSTS staat aan. `OMNITWIN_HTTP_PORT` moet hierbij `80` blijven. Een eigen certificaat in plaats van Let's Encrypt staat beschreven in de kop van het voorbeeldbestand.

### Security-headers

Traefik zet op **alle** routes (de app, `/api/data`, `/api/geo`, `/health`) deze headers, vastgelegd in [`deploy/traefik/dynamic.yml`](../../deploy/traefik/dynamic.yml):

| Header | Waarde |
|--------|--------|
| `Content-Security-Policy` | Alleen eigen bronnen (bibliotheken en lettertype zelf gehost, #117), plus api.pdok.nl en service.pdok.nl (achtergrondkaart). Geen framing (`frame-ancestors 'none'`), geen plugins (`object-src 'none'`). |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera, microfoon, locatie, betalen en USB uit |
| `Strict-Transport-Security` | `max-age=31536000`, alleen op HTTPS via Traefik (manier B) |

De CSP staat nog `'unsafe-inline'` toe: de frontend gebruikt inline scripts, `onclick=`-attributen en inline stijlen. Dat weghalen is een aparte klus in de frontend.

Voeg je een kaartlaag of bibliotheek toe die rechtstreeks een andere server aanroept, dan blokkeert de browser die. Neem de host dan op in `dynamic.yml` en draai `docker compose restart traefik`. Externe WFS-lagen lopen via de backend (`/api/externe-lagen/...`) en hebben dit niet nodig.

### security.txt

`/.well-known/security.txt` ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)) verwijst naar `SECURITY.md` in de GitHub-repository. Dat is het meldpunt voor fouten in de software. Beheer je een eigen installatie, vervang dan in [`static/.well-known/security.txt`](../../static/.well-known/security.txt) `Contact` en `Policy` door het meldpunt van je organisatie en voeg `Canonical: https://<host>/.well-known/security.txt` toe. Het veld `Expires` mag hooguit een jaar vooruit liggen; verleng het op tijd.

### Checklist vóór openstelling

- HTTPS aan (manier A of B), `DEBUG=false`, en HSTS zichtbaar in de response-headers.
- Het domein heeft DNSSEC en is via IPv6 bereikbaar (ook verplichte standaarden). Dat regel je bij je DNS- en hostingbeheer, niet in de stack.
- `security.txt` verwijst naar het juiste meldpunt.
- De punten bovenaan dit hoofdstuk (#57, #65) zijn opgelost of afgeschermd.
