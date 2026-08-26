# CI/CD Pipeline & Docker Hub — Uitlevering van D-OmniTwin

> **Documenttype:** Implementatiegids & Architectuurnotitie  
> **Doelgroep:** Ontwikkelaars, DevOps, Projectbeheerders  
> **Status:** Concept — implementatie gepland (Issues #27 & #28)  
> **Gerelateerde issues:** [#27 Semantic versioning](https://github.com/TLaan/D-OmniTwin/issues/27) · [#28 CI/CD-pipeline](https://github.com/TLaan/D-OmniTwin/issues/28) · [#22 Epic: SWF productie-gereedheid](https://github.com/TLaan/D-OmniTwin/issues/22)

---

## 1. Waarom deze aanpak?

De huidige werkwijze voor het uitleveren van D-OmniTwin aan een externe organisatie vereist dat de
ontvangende server de volledige broncode compileert: Docker images bouwen, npm packages installeren,
Python dependencies compileren. Dat is foutgevoelig, tijdrovend en vereist dat de doelserver
bouwgereedschap heeft.

De nieuwe aanpak volgt de industriestandaard: **bouwen doe je één keer, centraal en geautomatiseerd.
Uitleveren doe je met een kant-en-klaar, getest pakket.**

### De nieuwe flow in één schema

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  Developer    →   GitHub Repo   →   GitHub Actions   →   Docker Hub                 │
│  (git push)       (broncode)        (bouw + test)        (kant-en-klaar image)       │
│                                                              │                       │
│                                                              ▼                       │
│                                                   Externe organisatie                │
│                                                   (docker compose pull + up)         │
│                                                   + database dump restore            │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Wat verandert er voor de externe organisatie?

| Situatie | Oud (bouwen op locatie) | Nieuw (pull van Docker Hub) |
|---|---|---|
| Benodigde software op server | Docker, Git, Node.js, Python, gcc | Alleen Docker |
| Installatietijd applicatie | 10–30 minuten | < 2 minuten |
| Risico op bouwfouten | Hoog (afhankelijk van server) | Geen (image is vooraf getest) |
| Garantie dat het werkt | Geen | Ja — dezelfde image die CI/CD heeft getest |
| Wat ze ontvangen | Broncode + instructies | `docker-compose.prod.yml` + `.env` + DB dump |

> [!IMPORTANT]
> De database dump (zie [stappenplan_docker_installatie_externe_organisatie.md](./stappenplan_docker_installatie_externe_organisatie.md))
> blijft nodig en is **niet** onderdeel van de Docker image. De image bevat de applicatiecode;
> de data (indicatoren, geometrieën, Kompas-hiërarchie) wordt via de dump in het `pgdata` volume
> geladen. Dat stappenplan is nog steeds geldig — alleen stap 3.1 ("Docker images bouwen")
> vervalt en wordt vervangen door `docker compose pull`.

---

## 2. Welke containers worden gepubliceerd naar Docker Hub?

D-OmniTwin bestaat uit 5 containers. Niet alle 5 hoeven door ons gebouwd en gepubliceerd te worden:

| Container | Huidige situatie | Na CI/CD |
|---|---|---|
| `traefik` | `image: traefik:latest` — al publiek op Docker Hub | Ongewijzigd |
| `omnitwin_backend` | `build: .` — bouwen op locatie | ✅ Gepubliceerd als `sudwest-fryslan/d-omnitwin-backend:v1.x.x` |
| `omnitwin_db` | `build: db.Dockerfile` — bouwen op locatie | ✅ Gepubliceerd als `sudwest-fryslan/d-omnitwin-db:v1.x.x` |
| `postgrest` | `image: postgrest/postgrest:latest` — al publiek | Ongewijzigd |
| `pg_featureserv` | `image: pramsey/pg_featureserv:latest` — al publiek | Ongewijzigd |

Onze CI/CD pipeline hoeft dus alleen **twee eigen images** te bouwen en te publiceren: `backend` en `db`.

---

## 3. Afhankelijkheid: Issue #27 komt eerst (Semantic Versioning)

Vóór de CI/CD pipeline (#28) opgezet kan worden, moet semantic versioning (#27) op orde zijn.
De pipeline heeft een versienummer nodig om de Docker image mee te taggen. Zonder dat weet
Docker Hub niet of het om `latest`, `v1.0.0` of `v1.1.2` gaat.

### Wat is Semantic Versioning?

Een versienummer heeft drie cijfers: `vMAJOR.MINOR.PATCH`

- **PATCH** (laatste cijfer) — kleine bugfix, niets breekt: `v1.0.0` → `v1.0.1`
- **MINOR** (middelste cijfer) — nieuwe functionaliteit, achterwaarts compatibel: `v1.0.0` → `v1.1.0`
- **MAJOR** (eerste cijfer) — breaking change, dingen kunnen breken: `v1.0.0` → `v2.0.0`

### Hoe bepaalt het systeem het versienummer automatisch?

Via **Conventional Commits**: de tekst van een commit-boodschap bepaalt de versie-stap.

| Commit prefix | Betekenis | Versie-effect |
|---|---|---|
| `fix: herstel kaartlaadprobleem` | bugfix | PATCH +1 |
| `feat: voeg tijdslider toe` | nieuwe feature | MINOR +1 |
| `feat!:` of `BREAKING CHANGE:` in commit body | breekt bestaande API | MAJOR +1 |
| `chore:`, `docs:`, `refactor:` | geen release | geen versie-stap |

Het tooling-voorstel van Eduard (`semantic-release`, patroon van `WebformulierenVerwerker`) leest
deze commit-teksten en schrijft het nieuwe versienummer automatisch naar een bestand en een Git tag.

### Wat te doen voor #27

1. Team-afspraak vastleggen: altijd conventional commit-formaat gebruiken bij commits naar `main`.
2. `semantic-release` configureren in een `.releaserc` of `package.json`.
3. Versienummer doorschrijven naar een `BuildInfo`-bestand zodat het in de UI zichtbaar is.
4. Gedocumenteerd in `CONTRIBUTING.md` (issue #29).

---

## 4. De CI/CD Pipeline — stap voor stap (Issue #28)

De pipeline draait automatisch als GitHub Actions workflow bij elke push naar een branch en bij elke
merge naar `main`. Hieronder de vijf stappen zoals Eduard ze heeft beschreven, met uitleg.

```
Push naar GitHub
      |
      v
+-----------------------------------------------------+
|  STAP 1: Bouwen (elke branch, elke push)            |
|  docker build -t omnitwin-backend .                 |
|  docker build -t omnitwin-db -f db.Dockerfile .     |
+------------------------+----------------------------+
                         | geslaagd?
                         v
+-----------------------------------------------------+
|  STAP 2: Draaien & Healthcheck (elke branch)        |
|  docker compose up -d                               |
|  curl http://localhost/docs  -> verwacht HTTP 200   |
+------------------------+----------------------------+
                         | geslaagd?
                         v
+-----------------------------------------------------+
|  STAP 3: Testen (elke branch)                       |
|  +-- Unit:        pytest -m unit                    |
|  +-- Regressie:   pytest -m regression              |
|  +-- Performance: pytest -m performance             |
+------------------------+----------------------------+
                         | geslaagd?
                         v
+-----------------------------------------------------+
|  STAP 4: Goedkeuring (PR vereist review)            |
|  Branch protection: geen self-merge,                |
|  minimaal 1 reviewer vereist (issue #29)            |
+------------------------+----------------------------+
                         | merge naar main?
                         v
+-----------------------------------------------------+
|  STAP 5: Publiceren (ALLEEN op main, na stap 1-4)   |
|  docker push sudwest-fryslan/d-omnitwin-backend:v1.x|
|  docker push sudwest-fryslan/d-omnitwin-db:v1.x     |
+-----------------------------------------------------+
```

### Wat betekent dit in de praktijk?

- Een feature-branch kan gebouwd en getest worden zonder dat er iets naar Docker Hub gaat.
- Pas als alle checks groen zijn **en** de PR is gereviewed en gemerged naar `main`, wordt de
  image gepubliceerd.
- De `publish-docker` stap (stap 5) wordt **overgeslagen** (`skipped`) bij pushes op
  feature-branches — precies wat je ziet in de schermafbeelding van `WebformulierenVerwerker`.

---

## 5. Testmethodiek (onderdeel van #28)

Eduard's issue is expliciet: de test-suites zijn **projectcode**, niet alleen CI-configuratie.
Ze moeten geschreven en onderhouden worden in `tests/`, naast de twee bestaande testbestanden
(`tests/test_zscore.py`, `tests/test_canvas.py`).

### Voorgestelde tooling

| Tool | Doel | Equivalent in Java/Spring |
|---|---|---|
| `pytest` met markers | Scheidt unit/regressie/performance | JUnit categories |
| `fastapi.testclient.TestClient` | Test de API zonder echte server | Spring MockMvc |
| `testcontainers-python` | Start echte PostgreSQL/PostGIS voor tests | Testcontainers-java |
| `pytest-cov` | Codedekking meten | JaCoCo |
| `pytest-benchmark` | Performance baselines meten | JMH (initieel minimaal) |

### Structuur in `tests/`

```
tests/
├── conftest.py              # gedeelde fixtures (DB-connectie, test-client)
├── test_zscore.py           # bestaand — unit test
├── test_canvas.py           # bestaand — unit test
├── test_api_regression.py   # nieuw — regressie: Kompas, kaartlagen, rapporten
└── test_performance.py      # nieuw — performance baselines kritieke endpoints
```

### Markers in `pyproject.toml`

```toml
[tool.pytest.ini_options]
markers = [
    "unit: snelle unit tests zonder externe afhankelijkheden",
    "regression: regressietests op bestaande functionaliteit",
    "performance: performance baselines voor kritieke endpoints",
]
```

---

## 6. Stap 0: Docker Hub inrichten (vereiste voorbereiding)

Voer dit eenmalig uit voordat de pipeline kan publiceren.

### 6a. Docker Hub organisatie en repositories aanmaken

1. Ga naar [hub.docker.com](https://hub.docker.com) en log in als `sudwest-fryslan`
   (of maak een organisatieaccount aan).
2. Maak twee repositories aan:
   - `sudwest-fryslan/d-omnitwin-backend`
   - `sudwest-fryslan/d-omnitwin-db`
3. Stel beide in op **Public** — zodat externe organisaties geen Docker Hub-account nodig
   hebben om images te kunnen downloaden.

### 6b. Docker Hub Access Token aanmaken

1. Ga in Docker Hub naar **Account Settings → Security → New Access Token**.
2. Naam: `github-actions-d-omnitwin`, rechten: **Read & Write**.
3. Kopieer het token direct (het wordt maar één keer getoond).

### 6c. Token opslaan als GitHub Secret

1. Ga in de GitHub repository naar **Settings → Secrets and variables → Actions**.
2. Voeg twee secrets toe:
   - `DOCKERHUB_USERNAME` — de Docker Hub gebruikersnaam (bijv. `sudwest-fryslan`)
   - `DOCKERHUB_TOKEN` — het Access Token uit stap 6b

In de workflow zijn ze beschikbaar als `${{ secrets.DOCKERHUB_USERNAME }}` en
`${{ secrets.DOCKERHUB_TOKEN }}`.

---

## 7. Productie `docker-compose.prod.yml` voor externe organisaties

Na het publiceren van de images vervalt de `build:` instructie in de compose file.
De externe organisatie gebruikt alleen nog de gepubliceerde images van Docker Hub.

```yaml
# D-OmniTwin — Productie Docker Compose
# Gebruik: docker compose -f docker-compose.prod.yml up -d
# Vereist: .env bestand met DATABASE_PASSWORD, SECRET_KEY, etc.

version: '3.8'
name: "d-omnitwin"

services:
  traefik:
    image: traefik:latest
    container_name: traefik
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
      - "127.0.0.1:8081:8080"   # dashboard: alleen lokaal bereikbaar
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
    restart: unless-stopped

  backend:
    image: sudwest-fryslan/d-omnitwin-backend:latest  # van Docker Hub, geen build
    container_name: omnitwin_backend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/`)"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
    env_file:
      - .env
    environment:
      - DATABASE_HOST=postgres
    restart: unless-stopped
    depends_on:
      - postgres

  postgres:
    image: sudwest-fryslan/d-omnitwin-db:latest       # van Docker Hub, geen build
    container_name: omnitwin_db
    environment:
      POSTGRES_USER: ${DATABASE_USER:-omnitwin_user}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
      POSTGRES_DB: ${DATABASE_NAME:-omnitwin_db}
    ports:
      - "127.0.0.1:5433:5432"   # alleen lokaal bereikbaar
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  postgrest:
    image: postgrest/postgrest:latest
    container_name: postgrest
    environment:
      PGRST_DB_URI: postgres://${DATABASE_USER:-omnitwin_user}:${DATABASE_PASSWORD}@postgres:5432/${DATABASE_NAME:-omnitwin_db}
      PGRST_DB_SCHEMA: public
      PGRST_DB_ANON_ROLE: ${DATABASE_USER:-omnitwin_user}
      PGRST_SERVER_PROXY_URI: http://localhost/api/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.postgrest.rule=PathPrefix(`/api/data`)"
      - "traefik.http.middlewares.postgrest-strip.stripprefix.prefixes=/api/data"
      - "traefik.http.routers.postgrest.middlewares=postgrest-strip"
      - "traefik.http.services.postgrest.loadbalancer.server.port=3000"
    depends_on:
      - postgres
    restart: unless-stopped

  pg_featureserv:
    image: pramsey/pg_featureserv:latest
    container_name: pg_featureserv
    environment:
      DATABASE_URL: postgres://${DATABASE_USER:-omnitwin_user}:${DATABASE_PASSWORD}@postgres:5432/${DATABASE_NAME:-omnitwin_db}
      PGFS_SERVER_BASEPATH: /api/geo
      PGFS_PAGING_LIMITMAX: 10000
      PGFS_PAGING_LIMITDEFAULT: 10000
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pg_featureserv.rule=PathPrefix(`/api/geo`)"
      - "traefik.http.services.pg_featureserv.loadbalancer.server.port=9000"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  pgdata:
```

---

## 8. Installatieprocedure externe organisaties — wat wijzigt?

Het [stappenplan_docker_installatie_externe_organisatie.md](./stappenplan_docker_installatie_externe_organisatie.md)
blijft grotendeels van kracht. Eén stap verandert:

**Fase 3, Stap 3.1 — Oud (bouwen op locatie):**
```bash
docker compose build
```

**Fase 3, Stap 3.1 — Nieuw (kant-en-klare image ophalen):**
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d postgres
```

Alle overige fasen — met name **Fase 4 (database dump restore)** en **Fase 6 (acceptatietesten)** —
zijn ongewijzigd van toepassing. De database dump is en blijft de manier om de data in de lege
`pgdata` volume te laden.

---

## 9. Implementatievolgorde

```
#27 Semantic Versioning    →    #28 CI/CD Pipeline    →    Uitlevering gereed
 (commit-conventie,              (GitHub Actions              (docker-compose.prod.yml
  .releaserc config,              YAML + testsuite,            + .env + DB dump
  versie in BuildInfo)            Docker Hub push)             naar externe org)
```

> [!WARNING]
> **#27 is een blocker voor #28.** De publish-stap in de pipeline tagt de Docker image met het
> semantische versienummer. Zonder werkende versioning weet de pipeline niet welke tag te gebruiken.

**#29 (CONTRIBUTING.md)** loopt parallel aan #27 en documenteert de commit-conventie en
branch-strategie voor het hele team.

---

## 10. Referentie-implementatie

Eduard verwijst expliciet naar `Sudwest-Fryslan/WebformulierenVerwerker` als het te volgen patroon.
Dit project heeft de volledige pipeline al operationeel en productie-bewezen:

- **GitHub repository:** [github.com/Sudwest-Fryslan/WebformulierenVerwerker](https://github.com/Sudwest-Fryslan/WebformulierenVerwerker)
- **Docker Hub image:** [hub.docker.com/r/wearefrank/webformulierenverwerker](https://hub.docker.com/r/wearefrank/webformulierenverwerker)
- **Startpunt workflow:** `.github/workflows/ci-build.yml` in die repository — dit bestand
  als basis nemen en aanpassen voor onze Python/FastAPI/PostGIS stack.

De checks die in de schermafbeelding te zien zijn (`analyze-commits`, `docker/build`,
`checkov-linter`, `run-till-healthy`, `publish-docker`, `release`) komen rechtstreeks uit
dat workflow-bestand.
