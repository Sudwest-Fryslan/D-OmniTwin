# Architectuur Migratieplan: Naar een Dataspace Platform

Dit plan schetst de impact en de stappen voor de transitie van de huidige "monolithische" FastAPI architectuur naar de modulaire "legoblokken" architectuur (volgens het doelbeeld van Eduard).

Het doel is: minder eigen code onderhouden, standaard functionaliteit (CRUD & Geo) afvangen met bewezen componenten, en het platform gereed maken voor veilige productie-deployment.

## 1. Open Vragen voor Besluitvorming

Om de exacte start aan te kleden, moeten de volgende punten nog worden afgestemd voordat we in september starten met de uitvoering:
1. **Database:** Willen we de database (PostgreSQL) ook migreren naar een Docker container (dit is standaard voor deze opzet), of draait deze momenteel ergens centraal en willen we die buiten de Docker stack houden?
2. **MapLibre migratie:** Mogen we Mapbox in Fase 2 direct vervangen door MapLibre, of wil je dat we eerst de API's overzetten en de frontend later pas aanraken?

---

## 2. Impact Analyse per Component

De migratie raakt vrijwel elk onderdeel van de applicatie, maar voornamelijk aan de "achterkant". Voor de eindgebruiker verandert er visueel (voorlopig) niets, maar de motor onder de motorkap wordt vervangen.

### 2.1 Infrastructuur & Deployment (Nieuw)
- **Huidig:** Handmatig starten via `python run_dev.py` in een virtuele omgeving.
- **Nieuw:** Eén `docker-compose.yml` bestand dat de hele stack start (`docker compose up`).
- **Impact:** We introduceren **Traefik**. Traefik luistert op poort 80/443 en routeert verkeer. Bijvoorbeeld:
  - `/api/data` -> PostgREST container
  - `/api/geo` -> pg_featureserv container
  - `/api/custom` -> Onze afgeslankte FastAPI container

### 2.2 De Python Backend (FastAPI)
- **Huidig:** ~4800 regels code verdeeld over 18 routers. Doet letterlijk alles (data ophalen, geojson maken, LLM, logica).
- **Nieuw:** Een sterk afgeslankte backend die *alleen nog maar maatwerk doet*.
- **Impact (Zeer Hoog):** 
  - Routers zoals `gemeenten.py`, `omgevingsvisie.py`, en delen van `admin.py` (puur voor het uitlezen of schrijven van database rijen) kunnen we **volledig verwijderen**.
  - De backend wordt omgezet in een Docker container (vereist een `Dockerfile`).

### 2.3 De Frontend (JavaScript / React Admin)
- **Huidig:** Praat exclusief met `/api/...` (FastAPI). Gebruikt Mapbox GL JS voor de kaarten.
- **Nieuw:** Praat met Traefik, die het verkeer slim verdeelt. Gebruikt MapLibre.
- **Impact (Gemiddeld):** 
  - In de JavaScript bestanden (`app.js`, React API calls) moeten we de URL's aanpassen. Bijvoorbeeld `fetch('/api/gemeenten')` wordt `fetch('/api/data/gemeenten')` (richting PostgREST).
  - Mapbox GL JS wordt vervangen door MapLibre GL JS om licentierisico's te vermijden. De overstap voor Deck.gl is doorgaans heel soepel (het is een drop-in replacement).

### 2.4 Database (PostgreSQL / PostGIS)
- **Huidig:** Bevat tabellen en data. Beveiliging gebeurt in Python.
- **Nieuw:** Bevat tabellen, data én metadata (DCAT).
- **Impact (Laag):**
  - De tabellen blijven intact.
  - Omdat PostgREST direct op de database werkt, moeten we in PostgreSQL *rollen* (database users) instellen om te zorgen dat PostgREST veilig (read-only voor publiek, write voor admin) data ontsluit.

---

## 3. Voorgestelde Fasering (Uitvoeringsplan Roadmap)

Om de applicatie operationeel te houden, knippen we dit op in logische en veilige fases. Dit vormt de basis voor de roadmap na de zomer.

### Fase 1: Infrastructuur Fundament (Docker & Traefik)
1. Aanmaken van `Dockerfile` voor de huidige FastAPI backend.
2. Aanmaken van `docker-compose.yml` met Traefik en de FastAPI container.
3. Testen of de applicatie lokaal exact hetzelfde werkt, maar dan draaiend binnen Docker in plaats van via `run_dev.py`.
*(Impact: Alleen deployment, applicatiecode blijft gelijk)*

### Fase 2: De "Legoblokken" inpluggen (PostgREST & pg_featureserv)
1. Toevoegen van de PostgREST en pg_featureserv containers aan `docker-compose.yml`.
2. Traefik configureren om routes door te sturen (bijv. `/api/data` naar PostgREST, `/api/geo` naar pg_featureserv).
3. Beveiliging (Database rollen) instellen voor PostgREST zodat de frontend veilig data kan ophalen.
*(Impact: Nieuwe services draaien passief naast de oude, nog niets gebroken)*

### Fase 3: Frontend Omkatten & Backend Afslanken
1. **Frontend:** API-calls in `app.js` en het Admin panel ombouwen naar de nieuwe endpoints (PostgREST / pg_featureserv).
2. **Frontend:** Mapbox vervangen door MapLibre.
3. **Backend:** Alle overbodige Python routers (`gemeenten.py`, `externe_lagen.py` CRUD, etc.) rigoureus verwijderen.
*(Impact: Actieve code-wijzigingen, applicatie is nu gemigreerd)*

---

## 4. Verificatie Plan

- **Na Fase 1:** Applicatie draait foutloos via `docker compose up` en Traefik reverse proxy.
- **Na Fase 2:** We kunnen via de browser direct data uit PostgREST en pg_featureserv benaderen.
- **Na Fase 3:** Het hele Kompas, de kaart, en het Admin paneel functioneren volledig. De Python backend is drastisch afgeslankt (>40% kleiner) en MapLibre toont de kaarten zonder Mapbox licentiemeldingen of errors.
