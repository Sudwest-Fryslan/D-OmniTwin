# Installatie en beheer van D-OmniTwin

Dit is de installatiegids voor beheerders. Andere installatiedocumenten in deze repository (`BUILD.md`, `GETTING_STARTED.md`, het stappenplan voor dump-migratie) zijn verouderd of aanvullend; bij verschillen geldt deze gids.

De gids gaat uit van een Linux-server of een werkplek met Docker. Alle commando's draai je in de map van de repository.

**Status:** D-OmniTwin is een pre-release. Lees [Beveiliging](#beveiliging) voordat je de installatie buiten je eigen netwerk bereikbaar maakt.

---

## 1. Vereisten

| Wat | Minimaal |
|-----|----------|
| Docker Engine met Compose v2 (`docker compose`, niet `docker-compose`) | Docker 24, Compose 2.20. Op Windows en macOS: Docker Desktop |
| Git | elke recente versie |
| Geheugen | 4 GB vrij voor de stack, 8 GB aanbevolen. Een lokaal taalmodel (Ollama) komt daar bovenop |
| Schijf | ± 10 GB vrij: backend-image ± 4,2 GB, database-image ± 1,1 GB, overige images ± 0,4 GB, plus de database en de build-cache |
| Poort | 80 op de host vrij (of een andere poort, zie `OMNITWIN_HTTP_PORT`) |
| Internet tijdens de installatie | voor Docker Hub, PyPI en de PyTorch-index (images bouwen). De kaart gebruikt PDOK-achtergrondkaarten in de browser; een token is niet nodig |

Controleer:

```bash
docker --version
docker compose version
```

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
2. `db-init` draait één keer en stopt. Bij een **lege** database maakt hij het schema aan (`init_data/schema/schema_latest.sql`, de views voor de kaart en de migraties v18 en v19), laadt de stuurdata en eventueel de sample dataset, en maakt het beheeraccount aan. Bestaat de tabel `gebieden` al, dan slaat hij dit allemaal over. Hij overschrijft dus nooit bestaande data.
   Daarna werkt hij altijd de databaserollen en het schema `api` voor PostgREST en pg_featureserv bij (`migrations/schema_v23_api_rollen.sql`, zie [Beveiliging](#beveiliging)). Dat raakt geen data.
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

De log van `db-init` toont ook een `ADMIN_API_KEY` ("BEWAAR DEZE KEY"). Die wordt nu niet gebruikt: de backend accepteert alleen de `ADMIN_API_KEY` uit `.env`.

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

De sample is bedoeld om de installatie te testen en te demonstreren, niet voor beleid.

### Volledige Fryslân-data

De repository bevat de CBS-buurten (indeling 2024) en indicatorwaarden voor heel Fryslân (`init_data/fryslan/`, zie [`init_data/README.md`](../../init_data/README.md)). Laad ze na de eerste start, als `db-init` klaar is en de backend draait:

```bash
docker compose exec backend python init_data/scripts/seed_fryslan.py --stap alle
```

Dit duurt enkele seconden (gemeten: 5 à 10 s). Het werkt met en zonder sample (`LOAD_SAMPLE_DATA`); de sample-buurten worden dan overschreven door dezelfde buurten uit de Fryslân-data. Verwachte aantallen in de database na sample + Fryslân:

| Tabel | Aantal |
|-------|--------|
| `gemeenten` | 18 (alle Friese gemeenten) |
| `gebieden` | 931 buurten |
| `indicatoren` | 244 (238 uit `indicatoren_seed.json`; namen die de sample al heeft worden aangevuld, niet gedupliceerd) |
| `kompas_indicator_mapping` | 185 |
| `gebied_data` | ± 46.500 (45.591 metingen uit de Fryslân-CSV, voor 870 buurten) |

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

`db-init` draait opnieuw, ziet dat de database bestaat en laat schema en data met rust. Alleen de rollen en het schema `api` voor PostgREST en pg_featureserv werkt hij altijd bij (v23, zie [Beveiliging](#beveiliging)). Andere schemawijzigingen worden bij een bestaande database **niet automatisch** doorgevoerd; geautomatiseerd migratiebeheer volgt in #54.

Tot die tijd voer je migraties handmatig uit. Een database van vóór september 2026 mist mogelijk v18 (`pg_trgm`, nodig voor de deduplicatie) en v19. Beide zijn veilig om opnieuw te draaien:

```bash
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < migrations/schema_v18_trigram.sql
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < migrations/schema_v19_deduplicatie_uitzonderingen.sql
```

Maak eerst een backup (zie hieronder). Lees bij een nieuwe versie [`CHANGELOG.md`](../../CHANGELOG.md) voor nieuwe migraties.

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
| AI-zoeken of de chat vindt geen indicatoren | Er zijn geen embeddings. Kijk in `docker compose logs db-init` naar `Embeddings niet gegenereerd`; meestal kon het model niet worden gedownload. Zorg voor internet en draai `docker compose run --rm db-init`: die vult alleen de ontbrekende embeddings aan. Na het goedkeuren van nieuwe beschrijvingen: `docker compose exec backend python scripts/ai/genereer_embeddings.py --opnieuw`. |
| AI-chat of samenvatting duurt minuten | Het model is een *thinking*-variant. Bij Ollama zijn `qwen3:4b` en `qwen3:30b` zonder toevoeging thinking-varianten; kies in **AI Configuratie** een `*-instruct`-variant (bijvoorbeeld `qwen3:30b-instruct`). Op een laptop zonder GPU blijft een samenvatting met een lokaal model ruim een minuut duren. |
| AI-chat geeft geen antwoord | Controleer in **AI Configuratie** de API-URL: vanuit de container is dat `http://host.docker.internal:11434`, niet `localhost`. Op Linux moet Ollama op alle interfaces luisteren (zie [LLM](#7-llm-optioneel)). |
| Ontwikkelmodus op Windows: backend start niet, `PermissionError: /app/logs/server.log` | De backend draait als niet-root-gebruiker en mag niet schrijven in de gemounte projectmap. Bijgewerkte `docker-compose.override.yml` gebruikt een apart logvolume (#59/#115). |
| Twee installaties op één host | Geef elke installatie een eigen map, een eigen `OMNITWIN_HTTP_PORT` en een eigen projectnaam (`COMPOSE_PROJECT_NAME=...` in `.env`). Traefik routeert alleen naar containers van het eigen project. |

---

## Beveiliging

Stel een installatie **niet** open voor internet of een breed netwerk zolang deze punten openstaan:

- **Autorisatie op beheerroutes is nog niet overal op orde** (#65).
- **Standaard geen HTTPS.** Traefik luistert op HTTP. Zet HTTPS aan op een van de twee manieren hieronder, en zet dan `DEBUG=false`. Met `DEBUG=false` stuurt de browser het inlogcookie alleen via HTTPS (behalve op `localhost`).
- Houd `.env` geheim: het bevat het databasewachtwoord en de `ADMIN_API_KEY`.

### PostgREST en pg_featureserv (#57)

PostgREST (`/api/data`) en pg_featureserv (`/api/geo`) verbinden niet als database-eigenaar, maar met eigen rollen. `db-init` maakt ze aan en houdt ze bij (`migrations/schema_v23_api_rollen.sql`):

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
| `Content-Security-Policy` | Alleen eigen bronnen, plus unpkg.com en cdn.jsdelivr.net (bibliotheken met SRI-hash), api.pdok.nl en service.pdok.nl (achtergrondkaart) en Google Fonts (helppagina). Geen framing (`frame-ancestors 'none'`), geen plugins (`object-src 'none'`). |
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
