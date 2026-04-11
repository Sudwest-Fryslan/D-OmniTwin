# Tooling richting D-OmniTwin

**Auteur:** Eduard Witteveen (Solutions Innovator, Súdwest-Fryslân)  
**Rol:** Architect  
**Datum:** april 2026  
**Status:** Richtingsdocument — geen definitieve keuzes

> **Dit document beschrijft richting, geen definitieve keuzes.** De kern van die richting is: zo min mogelijk eigen code schrijven en onderhouden. Bestaande, goed onderhouden tooling doet het werk. Eigen code alleen waar het echt maatwerk is.

---

## Leidend principe

De huidige Python-backend bevat veel code die eigenlijk commoditie is: CRUD-endpoints, geo-queries, auth. Die code moet je zelf onderhouden, testen en patchen. Elke router die je vervangt door een bestaand product is één ding minder om wakker van te liggen.

Wat overblijft in eigen code: Z-score berekeningen, Kompas-scoring, LLM-orchestratie, rapportage-aggregatie. Dat is het echte maatwerk.

---

## 1. Deployment en runtime

**Docker Compose** als primaire runtime. Begrijpelijk, geen overhead, past bij de huidige schaal.

Een volledige stack ziet er globaal zo uit:

```yaml
services:
  traefik:          # reverse proxy, TLS, routing
  postgres:         # PostgreSQL + PostGIS + pgvector
  backend:          # FastAPI / Uvicorn
  postgrest:        # auto-REST vanuit Postgres schema
  pg_featureserv:   # OGC API Features vanuit Postgres
  ollama:           # lokale LLM
  redis:            # cache
  keycloak:         # identity (fase 2)
  minio:            # object storage (fase 2)
  geonetwork:       # catalogus (fase 3)
```

**Traefik** als reverse proxy. Werkt met Docker-labels, past routing automatisch aan op draaiende containers, handelt TLS af. Geen aparte configuratiefiles per service nodig.

**Niet nu:** Kubernetes, service mesh, cloud-native orchestratie. Pas relevant bij meerdere teams of zware schaalproblemen. Nu ballast.

---

## 2. Datakern

**PostgreSQL + PostGIS** blijft de kern. Operationele data, geometrie, metadata, kwaliteit, lineage, embeddings — alles in één beheerde database.

**pgvector** erbij voor semantisch zoeken. Geen apart vectorplatform nodig.

**Redis** als cachelaag voor kaartdata en API-responses die niet bij elk request opnieuw berekend hoeven te worden.

---

## 3. Eigen code verminderen: PostgREST en pg_featureserv

Dit ontbreekt in veel tooling-overzichten maar is het belangrijkste punt.

**PostgREST** genereert automatisch een volledige REST API vanuit het PostgreSQL-schema. Geen Python-code schrijven voor CRUD-endpoints op gebieden, indicatoren, gemeenten, metadata. Gewoon een container draaien.

**pg_featureserv** doet hetzelfde maar specifiek voor OGC API Features. Geometrieën als GeoJSON serveren zonder eigen code.

Samen vervangen deze twee een groot deel van de huidige routers in FastAPI. De Python-backend houdt dan alleen de logica die nergens anders kan: Z-scores, Kompas-scoring, LLM, rapportage.

Dit is de directe uitwerking van het principe "zo min mogelijk eigen code".

---

## 4. Geoservices

Voor OGC-publicatie aan externe systemen: begin met **pygeoapi**. Python-native, licht, ondersteunt OGC API Features, Tiles en Records, draait in Compose. Past beter bij de huidige stack dan GeoServer.

**GeoServer** pas toevoegen als er echt complexe WMS/WFS-publicatie nodig is voor externe GIS-systemen. Het is een zware Java-applicatie met veel configuratie. Niet als vanzelfsprekende keuze.

**GeoServer Cloud** niet nu. Pas logisch als geoservices zelf een apart schaalbaar platformonderdeel worden.

---

## 5. Metadata en semantiek

Eerste stap: eigen metadata registry in PostgreSQL. Tabellen voor datasets, services, indicatordefinities, begrippen, eigenaarschap, kwaliteitsstatus, publicatiestatus, versies.

Aligneer dit direct op **DCAT** — de W3C-standaard voor datacatalogi. Dat voorkomt dat je later alles moet omschrijven als je naar GeoNetwork of CKAN wil.

Geen extern semantisch platform in fase 1. Eerst de binnenkant op orde.

---

## 6. Catalogus en publicatie

**Fase 1:** eigen metadata registry in de applicatie.  
**Fase 2:** **GeoNetwork** als externe catalogus voor geo- en dataservice-publicatie. Sterk in discovery, metadata editing, CSW, RDF/DCAT.  
**Fase 3:** **CKAN** alleen als er ook een breed open dataportaal nodig is buiten het geodomein.

Niet nu allebei. Dat is te veel.

---

## 7. Identity en toegang

Nu: API keys voor intern admin-gebruik, prima voor MVP.

Snel daarna: **Keycloak** voor echte identity. OpenID Connect, rollen, machine-to-machine. Geen eigen auth-systeem knutselen — daar zit weinig eer in en veel gedoe.

Later: dezelfde laag voor partners en federatieve aansluiting.

---

## 8. Object storage

**MinIO** voor bestanden, exports, kaartartefacten, AI-gegenereerde bijlagen. S3-compatible, vervangbaar door echte S3 of Cloudflare R2 als het ooit in de cloud gaat.

---

## 9. Viewer en frontend

**deck.gl + D3.js** houden. Sterk voor high-performance geo-visualisatie.

**MapLibre** als open alternatief voor Mapbox. Dit is urgenter dan het lijkt: Mapbox GL JS heeft een commerciële licentie met actieve map loads. Voor een EUPL open source project is dat een risico nu al. Migratie naar MapLibre is de juiste stap, niet later maar snel.

**Niet doen:** nieuwe frontendstack om "moderner" te zijn.

---

## 10. Async verwerking

LLM-calls zijn nu synchroon en blokkeren de server. Bij meerdere gebruikers tegelijk is dat een probleem.

Eerste stap: FastAPI `BackgroundTasks` voor LLM-calls die niet realtime hoeven.  
Fase 2: lichte job queue met **Celery + Redis** voor langlopende taken (rapportgeneratie, LLM-narratieven, embedding-berekeningen).

---

## 11. Observability

**OpenTelemetry** in de Python-laag — maar pas in fase 2, als de applicatie stabiel staat en productie-zichtbaarheid nodig is. Nu is basislogging voldoende.

---

## 12. Federatieve tooling

**Niet nu.** Eclipse Dataspace Components, FIWARE/NGSI-LD, Orion-LD: pas relevant als er echt gecontroleerde uitwisseling met externe dataspaces nodig is. Eerst de binnenkant op orde.

---

## 13. Standaarden

De stack moet aansluiten op deze standaarden. Geen nice-to-have — dit bepaalt of federatieve aansluiting later werkt:

- **GGM** (Gemeentelijk Gegevensmodel) — interoperabiliteit met andere gemeenten
- **iSHARE / Gaia-X** — trust framework voor data-uitwisseling in dataspaces
- **Common Ground** — ontkoppelde overheidsarchitectuur
- **NORA** — Nederlandse Overheid Referentie Architectuur
- **DCAT** — W3C-standaard voor metadata; aligneer de eigen metadata registry hierop
- **EUPL** — licentie voor alle gepubliceerde code

Praktisch: begin met DCAT-alignering in de metadata registry. De rest volgt zodra federatieve koppelingen actueel worden.

---

## Overzicht

| Bouwsteen | Wanneer | Vervangt |
|---|---|---|
| Docker Compose + Traefik | Nu | Handmatige deployment |
| PostgREST | Nu/snel | CRUD Python-routers |
| pg_featureserv | Nu/snel | Geo Python-routers |
| Redis | Snel | Geen caching |
| MapLibre | Snel | Mapbox (licentierisico) |
| Keycloak | Snel | Eigen auth |
| MinIO | Snel | Exports op disk |
| pygeoapi | Fase 2 | Handmatige OGC-endpoints |
| Celery + Redis | Fase 2 | Synchrone LLM-calls |
| OpenTelemetry | Fase 2 | Basislogging |
| GeoNetwork | Fase 3 | Geen externe catalogus |
| GeoServer | Fase 3 | Alleen bij WMS/WFS-behoefte |
| CKAN | Fase 3 | Alleen bij open dataportaal |
| EDC / FIWARE | Later | Federatieve tooling |

**Kern:** PostGIS + FastAPI (alleen maatwerk) + PostgREST + pg_featureserv + Traefik + Keycloak + eigen metadata/DCAT + deck.gl/MapLibre. Zo min mogelijk zelf schrijven, zo veel mogelijk draaien wat al bestaat.
