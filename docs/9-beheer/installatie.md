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

Genereer drie geheimen:

```bash
openssl rand -hex 24   # DATABASE_PASSWORD
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # ADMIN_API_KEY
```

Gebruik voor `DATABASE_PASSWORD` alleen letters en cijfers (zoals hierboven). Het wachtwoord komt in database-URL's terecht; tekens als `@ : / # % $` breken de verbinding. Gebruik daarom ook niet `init_data/scripts/setup_env.py`: die genereert wachtwoorden met zulke tekens.

Pas `.env` aan:

| Variabele | Wat invullen |
|-----------|--------------|
| `COMPOSE_FILE=docker-compose.yml` | **Verplicht voor een installatie.** Haal het `#` weg. Zonder deze regel laadt `docker compose` ook de ontwikkelinstellingen (zie [Ontwikkelmodus](#3-ontwikkelmodus)). |
| `OMNITWIN_HTTP_PORT` | Optioneel. Poort op de host, standaard `80`. |
| `DATABASE_PASSWORD` | **Verplicht.** Het gegenereerde wachtwoord. |
| `SECRET_KEY` | **Verplicht invullen**, al gebruikt de code hem nu nog niet. |
| `ADMIN_API_KEY` | **Verplicht.** Wie deze waarde in de header `X-Admin-Key` meestuurt, heeft beheerrechten. Laat de voorbeeldwaarde dus nooit staan. |
| `ADMIN_USER`, `ADMIN_PASSWORD` | Het eerste beheeraccount. Laat je `ADMIN_PASSWORD` op de voorbeeldwaarde staan of leeg, dan wordt er een wachtwoord gegenereerd (zie [2.4](#24-eerste-keer-inloggen)). |
| `DEBUG` | `true` zolang je zonder HTTPS draait, anders werkt inloggen in de browser niet (zie [Beveiliging](#beveiliging)). Met HTTPS: `false`. |
| `LOAD_SAMPLE_DATA` | `true`: de use cases (demodata) laden bij de eerste start. `false`: het product zonder data (indicatoren, Kompas, stuurdata). Zie [Data](#4-data). |
| `DATABASE_NAME`, `DATABASE_USER` | Mogen blijven staan. Wijzig ze alleen vóór de eerste start. |
| `DATABASE_HOST`, `DATABASE_PORT` | Laten staan. De containers negeren deze en gebruiken `postgres:5432`; ze gelden alleen voor scripts op de host in ontwikkelmodus. |
| `DATABASE_SSLMODE` | `prefer` laten staan. De database is alleen binnen het Docker-netwerk bereikbaar en heeft geen TLS; `require` werkt hier niet. |
| `CORS_ORIGINS` | Alleen nodig als andere websites de API aanroepen. De app zelf draait op hetzelfde adres. |
| `OLLAMA_*` | Optioneel, zie [LLM](#7-llm-optioneel). |
| `LOG_ALERT_*`, `SMTP_*` | Nog niet in gebruik (#47). |

Bescherm het bestand: `chmod 600 .env`.

### 2.3 Starten

```bash
docker compose up -d --build
```

De eerste keer duurt dit lang (10 tot 30 minuten): de backend-image installeert onder meer PyTorch en GDAL. Daarna starten de services in deze volgorde:

1. `postgres` (PostGIS met pgvector) wordt *healthy*.
2. `db-init` draait één keer en stopt. Bij een **lege** database maakt hij het schema aan (`init_data/schema/schema_latest.sql`, de views voor de kaart en de migraties v18 en v19), laadt de stuurdata en eventueel de sample dataset, en maakt het beheeraccount aan. Bestaat de tabel `gebieden` al, dan slaat hij dit allemaal over. Hij overschrijft dus nooit bestaande data.
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
| `http://<host>/api/data/` | PostgREST: tabellen en views als REST-API |
| `http://<host>/api/geo/` | pg_featureserv: OGC API Features, bijvoorbeeld `/api/geo/collections` |
| `http://<host>/health` | Healthcheck van de backend |

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

`db-init` draait opnieuw, ziet dat de database bestaat en doet niets. Schemawijzigingen worden bij een bestaande database dus **niet automatisch** doorgevoerd; geautomatiseerd migratiebeheer volgt in #54.

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

1. Installeer Ollama op de host en haal een model op, bijvoorbeeld `ollama pull qwen3:30b` (groot; een kleiner model kan ook).
2. Op Linux: laat Ollama op alle interfaces luisteren (`OLLAMA_HOST=0.0.0.0` in de service-omgeving van Ollama), anders kan de container er niet bij. Docker Desktop (Windows, macOS) regelt dit zelf.
3. Zet in `.env`: `OLLAMA_HOST=http://host.docker.internal:11434` en `OLLAMA_MODEL=<model>`, en herstart: `docker compose up -d`.
4. Zet in de beheeromgeving onder **AI Configuratie** de API-URL op `http://host.docker.internal:11434` en kies het model. **Dit is nodig:** de stuurdata zet hier `http://localhost:11434`, en deze instelling gaat vóór `OLLAMA_HOST`. Vanuit de container wijst `localhost` naar de container zelf.

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
| Twee installaties op één host | Geef elke installatie een eigen map, een eigen `OMNITWIN_HTTP_PORT` en een eigen projectnaam (`COMPOSE_PROJECT_NAME=...` in `.env`). Traefik routeert alleen naar containers van het eigen project. |

---

## Beveiliging

Stel een installatie **niet** open voor internet of een breed netwerk zolang deze punten openstaan:

- **PostgREST geeft alle tabellen vrij.** `/api/data` draait als de database-eigenaar en toont en wijzigt zonder inloggen alle tabellen, ook `users` en `sessions`. Aparte rollen en een beperkt API-schema volgen in #57. Tot die tijd: alleen in een vertrouwd netwerk, of `/api/data` afschermen in een proxy ervoor.
- **Autorisatie op beheerroutes is nog niet overal op orde** (#65).
- **Geen HTTPS in de stack.** Traefik luistert alleen op HTTP. Zet een reverse proxy met TLS ervoor (bijvoorbeeld de bestaande proxy of WAF van je organisatie) en zet dan `DEBUG=false`. Met `DEBUG=false` stuurt de browser het inlogcookie alleen via HTTPS (behalve op `localhost`).
- Houd `.env` geheim: het bevat het databasewachtwoord en de `ADMIN_API_KEY`.

Kwetsbaarheden melden: zie [`SECURITY.md`](../../SECURITY.md).
