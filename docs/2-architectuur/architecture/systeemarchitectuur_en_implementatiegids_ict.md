# Systeemarchitectuur & Implementatiegids D-OmniTwin
> **Documenttype:** Technische & Functionele Systeemarchitectuur  
> **Doelgroep:** ICT-Architecten, Informatieadviseurs, Security Officers & Systeembeheerders  
> **Status:** Actueel / Referentie-implementatie  
> **Licentie & Openheid:** EUPL 1.2 (Open Source Software) | CC BY 4.0 (Open Methodiek)

---

## 1. 🎯 Managementsamenvatting & Context

**D-OmniTwin** is een open, datagedreven gebiedsmonitor en interactielaag voor het integraal verkennen van leefomgevingsvraagstukken (zoals brede welvaart, leefbaarheid, energietransitie en klimaatadaptatie). 

Voor de **informatieadviseur** en **ICT-architect** zijn drie uitgangspunten leidend:
1. **Data blijft bij de bron (Dataspace-gedachte):** In plaats van een nieuw geïsoleerd data-eiland te creëren, ontsluit D-OmniTwin landelijke en regionale open databronnen (CBS, RIVM, PDOK) via open standaarden (OData, OGC WFS).
2. **Open standaarden & Geen vendor lock-in:** Het platform is gebouwd met bewezen open-source componenten (PostGIS, MapLibre, FastAPI, Traefik, PostgREST) onder de Europese **EUPL 1.2 licentie**.
3. **Naadloze integratie met de gemeentelijke werkplek:** Veilige toegang via **Microsoft Entra ID (Single Sign-On)** door inzet van **Keycloak** als betrouwbare Identity Broker.

---

## 2. 🏛️ Architectuuroverzicht & Systeemdiagram

Het systeem is opgebouwd volgens een moderne, modulaire **microservices-architectuur** in Docker. Het scheidt strikt tussen de presentatielaag (Frontend), de centrale toegangspoort (Reverse Proxy / Gateway), de verwerkingslogica (BFF & Data API's) en de ruimtelijke datalaag (PostGIS).

### Visueel Systeemoverzicht (Container Stack)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  GEBRUIKERSLAAG & CLIENT BROWSER (Werkplek Beleidsadviseur / Strateeg / Beheerder)                     │
│                                                                                                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Kaart & 3D Visualisatie│  │  D-Omni Kompas (D3.js)  │  │  Scenario Chat   │  │  Admin Panel     │  │
│  │  MapLibre GL + Deck.gl  │  │  Sunburst (244 indicat.)│  │  Zijpaneel       │  │  React 18 + TS   │  │
│  │  app.js                 │  │  kompas.js              │  │  chat.js         │  │  Beheer & Upload │  │
│  └────────────┬────────────┘  └────────────┬────────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│               └────────────────────────────┴─────┬──────────────────┴─────────────────────┘             │
│                                                  ▼                                                     │
│                                      EventBus (event-bus.js)                                           │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                                   │ HTTPS / REST (Poort 80 / 443)
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  TRAEFIK REVERSE PROXY & API GATEWAY (omnitwin_traefik)                                                │
│  • SSL/TLS Offloading & Certificaten  • Dynamic Service Routing  • Centrale Beveiliging                │
└──────┬───────────────────────────┬───────────────────────────┬──────────────────────────┬──────────────┘
       │ /api/data/*               │ /api/geo/*                │ /api/* & / (Webapp)      │ /auth/* (SSO)
       ▼                           ▼                           ▼                          ▼
┌──────────────┐          ┌──────────────────┐       ┌────────────────────────┐  ┌───────────────────────┐
│  PostgREST   │          │  pg_featureserv  │       │  FastAPI Backend (8000)│  │  Keycloak IAM         │
│  (Data API)  │          │  (OGC Geo API)   │       │  BFF, Statistiek,      │  │  Identity Broker      │
│  REST / OData│          │  Vector GeoJSON  │       │  Dossiers, PDF Export  │  │  OIDC & RBAC Rollen   │
└──────┬───────┘          └────────┬─────────┘       └───────────┬────────────┘  └───────────┬───────────┘
       │                           │                             │ SQLAlchemy                │ OIDC Sync
       └───────────────────────────┼─────────────────────────────┘                           │
                                   ▼                                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐  ┌──────────────────┐
│  DATABASE (PostgreSQL 16 + PostGIS 3.4) (omnitwin_db)                            │  │ Microsoft        │
│                                                                                  │  │ Entra ID         │
│  • Ruimtelijke Gebieden (RD New EPSG:28992 & WGS84 EPSG:4326)                   │  │ (Gemeentelijke   │
│  • 244 Gevalideerde Indicatoren & Historische Tijdreeksen (2020-2025)            │  │  Azure AD SSO)   │
│  • Kompas Hiërarchie, Thematische Classificaties & Data Lineage Metadata         │  └──────────────────┘
│  • Geoptimaliseerde Ruimtelijke Spatial Views (GIST Indexering)                  │
│  • Persistent Docker Volume: pgdata                                              │
└──────────────────────────────────────────────────┬───────────────────────────────┘
                                                   │ Uitgaande synchronisatie & WFS queries
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  EXTERNE DATAPORTALEN & DATASPACES (Data blijft bij de bron)                                           │
│  • CBS OData v4 API  • RIVM StatLine  • PDOK WFS (Natura 2000, Bodemdaling)  • Fryslân Data Space / FDS│
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 🧩 Beschrijving van Alle Componenten

### A. Presentatielaag (Frontend)

| Component | Technologie | Doel voor de Organisatie | Interactie & Relaties |
|---|---|---|---|
| **Hoofdapplicatie (Web UI)** | Vanilla JavaScript (ES6+), Modern CSS, `window.EventBus` | De centrale interactieve werkomgeving voor beleidsadviseurs, strategen en wijkwerkers. | Communiceert via een interne eventbus. Haalt thematische data op via de FastAPI backend en kaartlagen via pg_featureserv/PDOK. |
| **Kaartmotor** | **MapLibre GL JS + Deck.gl** | Snelle 2D- en 3D-visualisatie van buurten, wijken, polygonen, thematische vlakken en datalagen. Geen licentiekosten of tracking. | Rendert vector geodata direct in de browser via WebGL. |
| **D-Omni Kompas Visualisatie** | **D3.js (SVG)** | Interactief 'sunburst'-wiel dat complexe indicatoren (244 stuks) ordent in 12 thema's en 4 leefwerelddomeinen. Toont direct afwijkingen via Z-scores en percentielen. | Ontvangt gestructureerde hiërarchische JSON vanuit de FastAPI service. |
| **Beheeromgeving (Admin Panel)** | **React 18, TypeScript, Vite** | Veilige beheerinterface voor data-kwaliteitscontroles, indicator-definities, lineage-audits en geodata-uploads. | Gebuild naar statische bestanden (`static/admin-panel/`). Communiceert met `/api/admin/` endpoints. |
| **Assistent & Dialoogmodule** | Vanilla JS (`chat.js`) | Biedt contextuele hulp en voorgedefinieerde scenario-profielen (bijv. specifiek voor een beleidsmedewerker of wijkcontactpersoon). | Communiceert met de dialoogrouter in de backend (`routers/chat.py`). |

---

### B. Ingress, Gateway & Beveiliging

| Component / Container | Poort (Extern ➔ Intern) | Doel voor de Organisatie |
|---|---|---|
| **Traefik Reverse Proxy** (`omnitwin_traefik`) | `80:80` (HTTP)<br>`443:443` (HTTPS)<br>`8081:8080` *(Beheer)* | • **Centrale Toegangspoort:** Vangt al het inkomende verkeer af en verdeelt dit over de achterliggende containers op basis van URL-paden.<br>• **SSL/TLS Beveiliging:** Zorgt voor versleutelde verbindingen (HTTPS) en kan gebruikmaken van automatische certificaten of gemeentelijke TLS-certificaten.<br>• **Ontkoppeling:** Interne applicatiepoorten worden niet rechtstreeks blootgesteld aan het bedrijfsnetwerk. |

---

### C. Identiteit & Toegang (IAM & Single Sign-On)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  SINGLE SIGN-ON (SSO) & IDENTITEITS-FLOW                                               │
│                                                                                        │
│   ┌───────────────┐     1. Inloggen      ┌─────────────────┐     2. Auth Request       │
│   │ Gemeentelijke │ ───────────────────> │  D-OmniTwin     │ ───────────────────────┐  │
│   │ Medewerker    │ <─────────────────── │  (Traefik / BFF)│ <──────────────────┐   │  │
│   └───────────────┘   6. Sessie Cookie   └─────────────────┘   5. JWT Token     │   │  │
│                                                                                 │   │  │
│                                                                                 ▼   │  │
│   ┌────────────────────────────────┐     3. OIDC / SAML SSO     ┌───────────────────┴┐ │
│   │  Microsoft Entra ID (Azure AD) │ <───────────────────────── │  Keycloak Identity │ │
│   │  (Gemeentelijke Werkplek)      │ ─────────────────────────> │  Broker            │ │
│   └────────────────────────────────┘     4. Bevestigde Ident.   └────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Component / Container | Technologie | Doel voor de Organisatie |
|---|---|---|
| **Keycloak Identity Broker** (`omnitwin_keycloak`) | Keycloak (OpenID Connect / OAuth2) | • **Gemeentelijke Single Sign-On (SSO):** Medewerkers loggen veilig in via hun bestaande **Microsoft Entra ID (Azure AD)** account.<br>• **Rollen & Rechten (RBAC):** Bepaalt wie wat mag zien en bewerken (bijvoorbeeld beheerder, beleidsadviseur, raadpleger).<br>• **Standaardisatie:** Geen eigen wachtwoordopslag; 100% conform moderne overheidsbeveiligingsrichtlijnen (BIO / AVG). |

---

### D. Applicatie- & Verwerkingslaag (Backend Services)

| Component / Container | Technologie | Doel voor de Organisatie | Interactie & Relaties |
|---|---|---|---|
| **FastAPI Backend Service** (`omnitwin_backend`) | Python 3.11, FastAPI, Pydantic, SQLAlchemy | • **BFF (Backend-for-Frontend):** Levert geoptimaliseerde API's aan de gebruikersinterface.<br>• **Statistische Motor:** Berekent Z-scores, normalisaties, percentielen en benchmark-vergelijkingen tussen kernen.<br>• **Rapportage:** Genereert integrale gebiedsdossiers inclusief automatische bronverantwoording (colofon). | • Communiceert intern via Docker DNS met PostgreSQL (`5432`).<br>• Valideert tokens vanuit Keycloak.<br>• Voert geplande data-synchronisaties uit met CBS en RIVM. |
| **PostgREST Data Engine** (`omnitwin_postgrest`) | PostgREST (Haskell) | • **Gestandaardiseerde Data API:** Genereert direct een filterbare, snelle REST/OData API over de PostgreSQL tabellen en SQL-views.<br>• **Dataspace Interoperabiliteit:** Maakt data direct herbruikbaar voor eventuele externe gemeentelijke dashboards of analyses. | • Leest rechtstreeks op de PostgreSQL database conform gedefinieerde rechten.<br>• Wordt via Traefik gerouteerd op `/api/data/`. |
| **pg_featureserv** (`omnitwin_featureserv`) | pg_featureserv (Go / Crunchy Data) | • **OGC API Features Endpoint:** Snelle en lichtgewicht streaming van geografische vectorgrenzen (buurten, wijken, kernen) in GeoJSON-formaat. | • Leest ruimtelijke kolommen (`geom`) uit PostGIS.<br>• Wordt via Traefik gerouteerd op `/api/geo/`. |

---

### E. Data- & Ruimtelijke Opslaglaag

| Component / Container | Technologie | Doel voor de Organisatie |
|---|---|---|
| **PostgreSQL / PostGIS Database** (`omnitwin_db`) | **PostgreSQL 16 + PostGIS 3.4** | • **Ruimtelijk Geheugen:** Beheert alle geografische grenzen in zowel het officiële Rijksdriehoekstelsel (RD New, `EPSG:28992`) als WGS84 (`EPSG:4326`).<br>• **Indicatorenhuis:** Beheert 244 gevalideerde indicatoren, historische tijdreeksen (2020–2025) en complete data-lineage.<br>• **Performance:** Voorzien van ruimtelijke GIST-indexen en samengestelde views (`v_kompas_hierarchie`) voor snelle query-afhandeling. |
| **Volume: `pgdata`** | Docker Named Volume | Zorgt dat alle database-data permanent behouden blijft bij het herstarten of updaten van containers. |

---

## 4. 🔌 Netwerk-, Poorten- & Communicatieschema

In onderstaande tabel staat exact welk verkeer plaatsvindt. Binnen de Docker-omgeving verloopt al het onderlinge containerverkeer over een geïsoleerd intern netwerk (`bridge`).

| Bron | Bestemming | Poort & Protocol | Type Verkeer | Doel / Toelichting |
|---|---|---|---|---|
| **Gebruikersbrowser** | **Traefik Proxy** | `80/TCP` (HTTP) ➔ `443/TCP` (HTTPS) | Inkomend (Extern) | Toegang tot webapp en API's |
| **Traefik Proxy** | **FastAPI Backend** | `8000/TCP` (HTTP) | Intern netwerk | Webpagina's, BFF API en rapporten |
| **Traefik Proxy** | **PostgREST** | `3000/TCP` (HTTP) | Intern netwerk | `/api/data/` REST query endpoints |
| **Traefik Proxy** | **pg_featureserv** | `9000/TCP` (HTTP) | Intern netwerk | `/api/geo/` OGC Vector data streaming |
| **Traefik Proxy** | **Keycloak** | `8080/TCP` (HTTP) | Intern netwerk | `/auth/` SSO inlogscherm & token exchange |
| **Backend Services** | **PostgreSQL** | `5432/TCP` (PostgreSQL) | Intern netwerk | Database queries & ruimtelijke analyses |
| **Host / Beheer *(optioneel)*** | **PostgreSQL** | `5433:5432/TCP` | Lokaal beheer | Direct beheer via DBeaver / pgAdmin |
| **Keycloak IAM** | **Microsoft Entra ID** | `443/TCP` (HTTPS) | Uitgaand internet | Single Sign-On authenticatie (Azure AD) |
| **FastAPI Backend** | **PDOK / CBS / RIVM** | `443/TCP` (HTTPS) | Uitgaand internet | Ophalen WFS lagen, CBS/RIVM data-updates |

---

## 5. 🛠️ Installatie- & Implementatievereisten voor de Gemeentelijke Docker-omgeving

### Hosting- & Netwerkinrichting

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  GEMEENTELIJKE INFRASTRUCTUUR / HOSTING OMGEVING                                       │
│                                                                                        │
│   Bedrijfsnetwerk / Internet                                                           │
│           │                                                                            │
│           │ HTTPS (Poort 443 / 80)                                                     │
│           ▼                                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Optionele Gemeentelijke Reverse Proxy / WAF (F5, NGINX of Azure App Gateway)   │   │
│   └───────────────────────────────────────┬────────────────────────────────────────┘   │
│                                           │                                            │
│                                           ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LINUX HOST SERVER (Ubuntu 22.04/24.04 of RHEL 8/9 — Min. 4-8 vCPU / 16GB RAM)  │   │
│   │                                                                                │   │
│   │  ┌──────────────────────────────────────────────────────────────────────────┐  │   │
│   │  │ DOCKER ENGINE & BRIDGE NETWORK (Geïsoleerd intern netwerk)               │  │   │
│   │  │                                                                          │  │   │
│   │  │  [traefik] ──> [backend] ──> [postgres (PostGIS)] <── Named Volume:      │  │   │
│   │  │     │             │                    ▲              pgdata (SSD)      │  │   │
│   │  │     ├──> [postgrest] ──────────────────┤                                │  │   │
│   │  │     ├──> [pg_featureserv] ─────────────┤                                │  │   │
│   │  │     └──> [keycloak] ───────────────────┘                                │  │   │
│   │  └──────────────────────────────────────────────────────────────────────────┘  │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Systeemvereisten (Host Server)
* **Besturingssysteem:** Linux (Ubuntu Server 22.04 / 24.04 LTS of Red Hat Enterprise Linux 8/9).
* **Hardware Sizing:**
  * *Minimaal (Pilot / Test):* 4 vCPU's, 8 GB RAM, 40 GB SSD.
  * *Aanbevolen (Productie met SSO & intensieve GIS-analyses):* **8 vCPU's, 16 GB RAM, 80 GB SSD**.
* **Container Runtime:** Docker Engine 24.0+ en Docker Compose v2.20+.

### 2. Netwerkinrichting & Firewalling
* **Inkomend verkeer (Inbound):**
  * Poort `80` en `443` openstellen vanaf het gemeentelijke netwerk naar de server.
  * *Optioneel:* Indien de gemeente al een centrale Web Application Firewall (WAF) of centrale loadbalancer (zoals F5 of NGINX) gebruikt, kan Traefik daar naadloos achter worden geplaatst (Traefik fungeert dan als interne service-router).
* **Uitgaand verkeer (Outbound internet):**
  * De server heeft uitgaande HTTPS-toegang (`443`) nodig naar:
    * `https://login.microsoftonline.com` (Voor Microsoft Entra ID SSO).
    * `https://opendata.cbs.nl` (CBS OData API).
    * `https://statline.rivm.nl` (RIVM Gezondheidsmonitor).
    * `https://api.pdok.nl` (PDOK Geodata WFS/WMS).

### 3. Identiteitskoppeling (Microsoft Entra ID / Azure AD)
Voor de Single Sign-On koppeling met de gemeentelijke werkplek is een eenmalige configuratie nodig:
1. Registratie van een **Enterprise App / App Registration** in Microsoft Entra ID.
2. Genereren van een `Client ID` en `Client Secret`.
3. Instellen van de Redirect URI naar Keycloak: `https://[domein]/auth/realms/omnitwin/broker/entra/endpoint`.
4. Toekennen van standaard OpenID Connect scopes (`openid`, `profile`, `email`).

### 4. Configuratie- & Geheimenbeheer (`.env`)
Alle configuratieparameters worden extern aangeleverd via omgevingsvariabelen (geen geheimen of wachtwoorden in de container-images):
* Database accountgegevens (`DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`)
* Domeinnaam & TLS instellingen (`DOMAIN_NAME`)
* IAM & Entra ID geheimen (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `JWT_SECRET`)
* *Advies:* Deze variabelen kunnen worden beheerd via de standaard geheimenopslag van de organisatie (bijv. Azure Key Vault, HashiCorp Vault of een beveiligd `.env` bestand met `chmod 600`).

### 5. Persistentie, Back-up & Beheer
* **Data-opslag:** De database maakt gebruik van het Docker volume `pgdata`. Dit volume bevindt zich standaard onder `/var/lib/docker/volumes/` en kan direct worden meegenomen in de reguliere VM-backups.
* **Geautomatiseerde Database Back-up:** Er kan eenvoudig een dagelijkse `pg_dump` cronjob worden ingericht die gecomprimeerde SQL-dumps exporteert naar een centrale gemeentelijke backuplocatie:
  ```bash
  docker exec omnitwin_db pg_dump -U omnitwin_user omnitwin_db | gzip > /backups/omnitwin_db_$(date +%Y%m%d).sql.gz
  ```

---

## 6. 💡 Belangrijke Gesprekspunten voor het Overleg

1. **Privacy & AVG-Proof:** Data wordt uitsluitend getoond op geaggregeerd niveau (buurten, wijken, woonplaatsen). Er worden geen persoonsgegevens verwerkt of opgeslagen in de database.
2. **Dataspace-compatibel:** D-OmniTwin is ontworpen om in de toekomst naadloos aan te sluiten op regionale dataspaces (zoals de Fryslân Data Space) en het landelijke Federatief Datastelsel (FDS). Data blijft waar mogelijk bij de bron.
3. **Beheerslast & Onderhoud:** Door de volledige containerisatie in Docker is de installatie, het updaten en het beheer eenduidig en reproduceerbaar. Geen complexe lokale software-afhankelijkheden op de host server.
