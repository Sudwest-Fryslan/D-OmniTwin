# Installatie en beheer van D-OmniTwin

Dit is de installatiegids voor beheerders. Andere installatiedocumenten in deze repository (`docs/archief/BUILD.md`, `docs/archief/GETTING_STARTED.md`, het stappenplan voor dump-migratie) zijn verouderd of aanvullend; bij verschillen geldt deze gids.

De gids gaat uit van een Linux-server of een werkplek met Docker. Alle commando's draai je in de map van de repository.

Na de installatie: de [beheerhandleiding](beheerhandleiding.md) (back-up en herstel met scripts, bijwerken en terugrollen, Keycloak-beheer, leveringen, incidenten, acceptatie naast productie), de [privacy-quickscan](../5-secops/privacy-quickscan.md) en de [toegankelijkheidsstatus](../4-ux-design/toegankelijkheid.md).

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
| Internet tijdens de installatie | Voor het bouwen: Docker Hub, PyPI, de PyTorch-index en HuggingFace. Bij de eerste start met use cases: CBS (Kerncijfers) en RIVM (hittestress), zie [Data](#4-data). Daarna draait de stack zonder internet, ook AI-zoeken. De kaart gebruikt PDOK-achtergrondkaarten in de browser; een token is niet nodig |

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
openssl rand -hex 24   # waarde voor DATABASE_PASSWORD
```

Vul in `.env` het databasewachtwoord in, en bij voorkeur ook `ADMIN_PASSWORD`. Al het andere heeft een werkende standaard. Gebruik alleen letters en cijfers (zoals `openssl rand -hex` geeft): tekens als `@ : / # % $` breken de database-URL's.

De tabel volgt de volgorde van `.env.example`. Optionele regels staan daar als commentaar (`# NAAM=standaard`); haal het `#` weg om ze te gebruiken.

| Variabele | Wat invullen |
|-----------|--------------|
| `DATABASE_PASSWORD` | **Verplicht.** Het gegenereerde wachtwoord. Wijzig het niet meer na de eerste start: het geldt alleen bij het aanmaken van de database. |
| `ADMIN_PASSWORD` | Aanbevolen. Wachtwoord van het eerste beheeraccount. Leeg: er wordt eenmalig een wachtwoord gegenereerd (zie [2.4](#24-eerste-keer-inloggen)). |
| `COMPOSE_FILE` | Staat op `docker-compose.yml`: alleen de installatie-instellingen. Laat staan. Ontwikkelaars halen de regel weg (zie [Ontwikkelmodus](#3-ontwikkelmodus)). Extra compose-bestanden voeg je hier toe, gescheiden door `:` (Windows: `;`), zie [Eigen logo](#eigen-logo) en [HTTPS aanzetten](#https-aanzetten). |
| `OMNITWIN_OMGEVING` | Optioneel, standaard `productie`. `demo`: standaardaccounts met bekende wachtwoorden en een demobalk, alleen om te proberen; `test`: zoals productie, maar zwakke wachtwoorden geven alleen een waarschuwing. Bij `productie` weigert de installatie een zwak `ADMIN_PASSWORD` of `KEYCLOAK_ADMIN_PASSWORD`. Zie [2.6](#26-demo-test-of-productie). |
| `VIEWER_TOEGANG` | Optioneel, standaard `open`: de kaart en de data-API's zijn openbaar. `inloggen`: alleen na inloggen via Keycloak met de rol `lezer` of `beheerder`. Zie [Toegang tot de viewer](#toegang-tot-de-viewer-open-of-dicht). |
| `OMNITWIN_HTTP_PORT` | Optioneel. Poort op de host, standaard `80`. |
| `LOAD_SAMPLE_DATA` | Optioneel, standaard `true`: de use cases laden bij de eerste start. `false`: alleen het product zonder data. Zie [Data](#4-data). |
| `LOG_LEVEL` | Optioneel, standaard `INFO`. |
| `ADMIN_USER` | Optioneel. Naam van het eerste beheeraccount, standaard `admin`. |
| `ADMIN_API_KEY` | Optioneel, alleen voor scripts: wie deze waarde in de header `X-Admin-Key` meestuurt, heeft beheerrechten. Minimaal 32 tekens (`openssl rand -hex 32`). Leeg of een voorbeeldwaarde: de header werkt niet. De beheeromgeving gebruikt hem niet; die werkt met inloggen. |
| `COMPOSE_PROJECT_NAME` | Optioneel. Alleen nodig voor meerdere installaties op één machine (zie [Problemen oplossen](#8-problemen-oplossen)). |
| `CORS_ORIGINS` | Optioneel. Alleen nodig als andere websites de API aanroepen: een kommagescheiden lijst met volledige adressen, geen wildcards. De app zelf draait op hetzelfde adres. |
| `COOKIE_SECURE` | Optioneel, standaard `auto`: het inlogcookie krijgt `Secure` (alleen via HTTPS) als de verbinding HTTPS is. Achter een eigen TLS-proxy die over HTTP naar de stack doorstuurt: `true` (zie [HTTPS aanzetten](#https-aanzetten)). |
| `LLM_RATE_LIMIT` | Optioneel, standaard `60`: zoveel verzoeken per minuut per IP-adres op de chat en de AI-teksten; daarboven `429`. `0` = geen limiet. |
| `LOG_BEWAAR_DAGEN`, `LOG_IP_BEWAAR_DAGEN` | Optioneel, standaard `30` en `7`: logregels in de database (alle niveaus) worden na 30 dagen verwijderd, DEBUG na 7; IP-adressen daarin worden na 7 dagen ingekort (IPv4 laatste octet `0`, IPv6 `/48`). Zie [Status en logs](#status-en-logs). |
| `TRUSTED_PROXIES` | Optioneel. Adressen of netwerken (CIDR, kommagescheiden) waarvan de backend `X-Forwarded-For` overneemt. Standaard loopback en de privé-reeksen: Traefik op het Docker-netwerk. Van andere adressen geldt het directe adres. Leeg = nooit. Laat staan, tenzij je de backend zonder Docker draait op een netwerk met gebruikers: zet dan het adres van je proxy of leeg. |
| `TRAEFIK_TRUSTED_IPS` | Optioneel, alleen achter een eigen TLS-proxy of WAF (manier A in [HTTPS aanzetten](#https-aanzetten)): het adres daarvan (CIDR, kommagescheiden). Traefik neemt dan diens `X-Forwarded-For` over; anders ziet de app voor iedereen het adres van de proxy, ook de rate limiting. |
| `COMPOSE_PROFILES` | Optioneel. `keycloak` start Keycloak mee (zie [Keycloak](#keycloak-optioneel)). |
| `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_DB_PASSWORD` | Alleen met Keycloak, dan verplicht: wachtwoord van de tijdelijke beheerder `admin` in de admin-console, en van de databaserol `keycloak`. Genereer ze met `openssl rand -hex 24`. |
| `KEYCLOAK_HOSTNAME` | Alleen met Keycloak. Hostnaam (`omnitwin.example.nl`) of volledige URL (`https://omnitwin.example.nl/auth`) waarop gebruikers Keycloak bereiken; standaard `localhost`. Bepaalt de issuer van de tokens. |
| `OIDC_ISSUER` | Alleen met Keycloak (of een andere OIDC-provider). De issuer zoals die in de tokens staat: het publieke adres van Keycloak + `/realms/omnitwin`, bijvoorbeeld `http://localhost/auth/realms/omnitwin` of `https://omnitwin.example.nl/auth/realms/omnitwin`. Zet je het, dan controleert de backend tokens op de nieuwe API's (laad-API); leeg = uit, die API's geven dan `503`. Zie [Keycloak](#keycloak-optioneel). |
| `OIDC_CLIENT_ID`, `LOKAAL_INLOGGEN` | Optioneel, bij `OIDC_ISSUER`: inloggen in de beheeromgeving via Keycloak. `OIDC_CLIENT_ID`: de client waarmee mensen inloggen, standaard `omnitwin-web`. `LOKAAL_INLOGGEN=true`: noodtoegang, de lokale accounts (`ADMIN_USER`) mogen dan ook inloggen; standaard uit zodra `OIDC_ISSUER` gezet is. Zie [Keycloak](#keycloak-optioneel), *Inloggen in de beheeromgeving*. |
| `OIDC_AUDIENCE`, `OIDC_INTERN_URL`, `OIDC_JWKS_URL` | Optioneel, bij `OIDC_ISSUER`. `OIDC_AUDIENCE`: vereiste `aud`, standaard `omnitwin-api`. `OIDC_INTERN_URL`: adres waarop de backend de issuer intern bereikt voor discovery en sleutels; `docker-compose.yml` zet standaard `http://keycloak:8080/auth/realms/omnitwin`. Bij een externe identity provider: `OIDC_INTERN_URL=` (leeg). `OIDC_JWKS_URL`: alleen als de provider geen discovery heeft. |
| `OMNITWIN_BRON_DOMEINEN` | Optioneel. Extra domeinen (kommagescheiden) waarvan de bronadapters van de use cases via https mogen downloaden, naast de vaste lijst (CBS, PDOK, RIVM, Klimaateffectatlas). Zie [use cases](../../usecases/README.md#bronnen). |
| `OMNITWIN_BASE_URL`, `OMNITWIN_CLIENT_ID`, `OMNITWIN_CLIENT_SECRET`, `OMNITWIN_TOKEN_URL`, `KEYCLOAK_REALM` | Optioneel. `OMNITWIN_BASE_URL` is het adres van de installatie (standaard `http://localhost`); met Keycloak neemt de realmimport het op als redirect-URI van `omnitwin-web`. De rest alleen voor `python -m omnitwin.usecases installeer` en `test`: een machineclient (client credentials, zie [Keycloak](#keycloak-optioneel)). Het tokenendpoint komt standaard uit de discovery van realm `KEYCLOAK_REALM` (standaard `omnitwin`). |
| `BEWIJS_TIMEOUT_MS`, `BEWIJS_CHAT_TIMEOUT_MS` | Optioneel, alleen voor `python -m omnitwin.usecases bewijs` (screenshots met Playwright, bij een release): wachttijd per scherm (standaard 90000) en voor een chatantwoord (standaard 300000), in milliseconden. |
| `OMNITWIN_TESTACCOUNTS`, `KEYCLOAK_ADMIN_CLIENT_ID`, `KEYCLOAK_ADMIN_CLIENT_SECRET`, `KEYCLOAK_ADMIN`, `KEYCLOAK_URL`, `OMNITWIN_TESTACCOUNTS_UUR`, `OMNITWIN_TESTACCOUNTS_BESTAND` | Optioneel, alleen voor `--testaccounts` van de uitvoerder in test en dev (zie [Keycloak](#keycloak-optioneel), *Testaccounts*); de uitvoerder weigert bij `OMNITWIN_OMGEVING=productie`. Niet in een productie-`.env`. |
| `LEVERINGEN_DIR`, `LADEN_MAX_MB`, `LADEN_RATE_LIMIT`, `LADEN_COMPAT_RATE_LIMIT`, `LADEN_WACHT_SECONDEN` | Optioneel, laad-API ([docs/api/laden](../api/laden/README.md)): map voor de ruwe leveringen (standaard het volume `leveringen` op `/leveringen`), bodylimiet (standaard 200 MB, JSON een tiende), leveringen per minuut per client (standaard 10; op de compatibiliteitsingang voor de SWF-monitor 120) en de time-out van `wacht=true` (standaard 60 s). |
| `LADEN_BEWAAR_VERSIES`, `LADEN_BEWAAR_DAGEN`, `LADEN_BEWAAR_AFGEKEURD_DAGEN` | Optioneel. Bewaartermijn van de ruwe leveringen: altijd de laatste 10 versies per dataset, oudere tot 365 dagen, afgekeurde en alleen-gevalideerde leveringen 30 dagen. |
| `OLLAMA_HOST`, `OLLAMA_MODEL`, `LLM_THINK`, `LLM_REASONING_EFFORT` | Optioneel, lokale AI. Zie [LLM](#7-llm-optioneel). |
| `LITELLM_MASTER_KEY`, `LLM_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` | Optioneel, alleen met de LiteLLM-gateway. Zie [Andere aanbieders](#andere-aanbieders-via-de-litellm-gateway). |
| `DATABASE_NAME`, `DATABASE_USER` | Optioneel, standaard `omnitwin_db` en `omnitwin_user`. Wijzig ze alleen vóór de eerste start. |
| `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_SSLMODE` | Alleen voor scripts op de host in ontwikkelmodus. De containers gebruiken `postgres:5432`. Laat `DATABASE_SSLMODE` op `prefer`: de database is alleen binnen het Docker-netwerk bereikbaar en heeft geen TLS, `require` werkt hier niet. |

Bescherm het bestand: `chmod 600 .env`.

### 2.3 Starten

```bash
docker compose up -d --build
```

De eerste keer duurt dit lang (10 tot 30 minuten, afhankelijk van de verbinding): de backend-image installeert onder meer PyTorch en GDAL. Daarna starten de services in deze volgorde:

1. `postgres` (PostGIS met pgvector) wordt *healthy*.
2. `db-init` draait één keer en stopt. Hij kijkt eerst in wat voor database hij terechtkomt:
   - **Lege database:** hij maakt het schema aan (`db/schema/schema_latest.sql` en de views en functies voor pg_featureserv), past de schemamigraties uit `db/migraties/` toe, laadt de stuurdata (`db/stuurdata/`), met `LOAD_SAMPLE_DATA=true` de use cases en de CBS-reeksen, en maakt het beheeraccount aan.
   - **Bestaande database** (eerdere installatie voltooid): hij laat de data met rust en past alleen de schemamigraties toe die nog niet in de tabel `schema_migraties` staan (`python -m omnitwin.migraties`, #54).
   - **Half ingerichte database** (een eerdere eerste start is halverwege mislukt): hij stopt met een foutmelding en een herstelinstructie. Zie [Problemen oplossen](#8-problemen-oplossen).

   Daarna werkt hij altijd de databaserollen en het schema `api` voor PostgREST en pg_featureserv bij (`db/migraties/R__api_rollen.sql`, zie [Beveiliging](#beveiliging)). Dat raakt geen data. Bij een nieuwe installatie legt hij dan in de tabel `installatie_status` vast dat de installatie voltooid is.

   Tot slot maakt hij, ook bij een bestaande database, de embeddings voor AI-zoeken en de chat aan (`scripts/ai/genereer_embeddings.py`), voor alle actieve indicatoren zonder embedding of waarvan de tekst, de synoniemen of het model veranderd is, ook concepten. Het model daarvoor (`multilingual-e5-small`) zit al in de image; zie [Embeddingmodel](#embeddingmodel-offline). Lukt dit niet, dan staat er een waarschuwing in de log en gaat de installatie gewoon door; AI-zoeken en de chat vinden dan geen indicatoren.
3. `backend` (FastAPI), `postgrest` en `pg_featureserv` starten, `traefik` stuurt het verkeer door. Stopt `db-init` met een fout, dan starten deze drie niet.

Controleer:

```bash
docker compose ps -a
```

Goed is: `postgres` en `backend` staan op `Up ... (healthy)`, `traefik`, `postgrest` en `pg_featureserv` op `Up`, en `db-init` op `Exited (0)`. De backend heeft tot een minuut nodig om *healthy* te worden.

### 2.4 Eerste keer inloggen

Demo-omgeving (`OMNITWIN_OMGEVING=demo`, zie [2.6](#26-demo-test-of-productie)): log in met `admin`/`admin`.

Staat [Keycloak](#keycloak-optioneel) aan (met `OIDC_ISSUER`), dan log je in via Keycloak met een gebruiker uit realm `omnitwin`; zie daar. Het lokale account hieronder werkt dan alleen als noodtoegang.

Heb je `ADMIN_PASSWORD` ingevuld, dan log je in met `ADMIN_USER` (standaard `admin`) en dat wachtwoord.

Heb je dat niet gedaan, dan staat het gegenereerde wachtwoord **eenmalig** in de log van `db-init`:

```bash
docker compose logs db-init
```

Zoek naar `ADMIN_PASSWORD niet ingesteld. Gegenereerd wachtwoord voor 'admin'`. Het wachtwoord staat op de regel daaronder. Het wordt niet opgeslagen; bewaar het direct.

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
| `http://<host>/auth/` | Keycloak, alleen met het profiel `keycloak` (zie [Keycloak](#keycloak-optioneel)) |

Alleen Traefik publiceert een poort. De database en de afzonderlijke services zijn van buiten Docker niet bereikbaar.

### 2.6 Demo, test of productie

`OMNITWIN_OMGEVING` in `.env` zegt wat voor installatie dit is (#245):

| Waarde | Accounts | Wachtwoorden |
|--------|----------|--------------|
| `productie` (standaard) | Geen standaardaccounts. Lokaal alleen `ADMIN_USER` met `ADMIN_PASSWORD` (of een gegenereerd wachtwoord). | `db-init` weigert te starten met een bekend zwak `ADMIN_PASSWORD` of `KEYCLOAK_ADMIN_PASSWORD` (zoals `admin`, `wachtwoord`, `welkom`, gelijk aan de gebruikersnaam of korter dan 8 tekens); de stack start dan niet. |
| `test` | Geen standaardaccounts. | Zwak geeft alleen een waarschuwing in de log van `db-init`. |
| `demo` | Standaardaccounts met bekende wachtwoorden (hieronder) en een gele balk *Demo-omgeving — standaardwachtwoorden, niet voor productie* in de kaart en de beheeromgeving. | Versoepeld beleid in Keycloak (minimaal 5 tekens). |

Accounts bij `demo`:

| Account | Waar | Rollen |
|---------|------|--------|
| `admin` / `admin` | Keycloak (realm `omnitwin`) | `beheerder` (beheeromgeving) en `gebruikersbeheerder` (gebruikers beheren in de Keycloak-console) |
| `gebruiker` / `gebruiker` | Keycloak (realm `omnitwin`) | `lezer` (kaart, ook als die dicht staat; geen beheer) |
| `admin` / `admin` | Lokaal (zonder Keycloak, of als noodtoegang) | beheerder; alleen als `ADMIN_PASSWORD` leeg is |

De Keycloak-accounts zet de eenmalige service `keycloak-demo` (profiel `keycloak`) na elke start van Keycloak: bestaan ze niet, dan maakt hij ze aan; bestaan ze wel, dan zet hij wachtwoord en rollen terug. Een eigen gebruiker `admin` of `gebruiker` die je zelf hebt aangemaakt, raakt hij niet aan (de demo-accounts herkent hij aan de voornaam `Demo`). Zet je de omgeving daarna op `test` of `productie` en start je opnieuw (`docker compose up -d`), dan verwijdert hij de demo-accounts en zet hij het wachtwoordbeleid terug op dat uit de realmexport. Hij gebruikt de tijdelijke beheerder van Keycloak (`KEYCLOAK_ADMIN_PASSWORD`). Controle: `docker compose logs keycloak-demo`.

Bij een bestaande database maakt `db-init` in demo de lokale `admin` aan als die ontbreekt; een bestaand account houdt zijn wachtwoord.

Een demo hoort niet op een netwerk dat anderen kunnen bereiken: iedereen kent de wachtwoorden.

---

## 3. Ontwikkelmodus

Zonder `COMPOSE_FILE` in `.env` laadt `docker compose` naast `docker-compose.yml` ook `docker-compose.override.yml`. Die voegt toe:

- een bind-mount van de repository over `/app` in `backend` en `db-init`: codewijzigingen zijn direct zichtbaar na een herstart van de backend;
- de database op de host op poort **5433** (`DATABASE_HOST=localhost`, `DATABASE_PORT=5433` in `.env`, voor scripts en tools zoals pgAdmin of QGIS);
- het Traefik-dashboard op **http://localhost:8081**.

```bash
docker compose up -d --build
```

Gebruik dit niet voor een installatie: de database en het dashboard zijn dan onbeveiligd bereikbaar.

Ontwikkelen zonder Docker (Python venv, `run_dev.py`, admin-panel met `npm start`) staat in de [README](../../README.md#ontwikkelen) en [`AGENTS.md`](../../AGENTS.md).

---

## 4. Data

Alle data komt binnen via een **use case**: een map in [`usecases/`](../../usecases/README.md) met de datasets (bron, bewerkingen, beschrijving), de inrichting en de controles. De laadstraat valideert, versioneert en publiceert de data, met DCAT-metadata. Dezelfde laadstraat zit achter de [laad-API](../api/laden/README.md).

### Bij de eerste start

`db-init` laadt bij de eerste start altijd het product zonder data: stuurdata (scenario's, profielen, prompts), de indicatordefinities en de Kompas-indeling. Met `LOAD_SAMPLE_DATA=true` (standaard) installeert hij daarna alle actieve use cases in-process (`python -m omnitwin.usecases installeer --alle --inproces`, zonder HTTP en token). Dat is open data, gedownload bij de bron (https://github.com/TLaan/D-OmniTwin/issues/236):

- de **CBS-buurten, -wijken en -gemeenten** van Fryslân (PDOK, `cbs-gebiedsindelingen`);
- de **CBS Kerncijfers 2019-2026** voor heel Fryslân (`cbs-kerncijfers`, zie [`cbs_kerncijfers.md`](../3-data-engineering/cbs_kerncijfers.md));
- de **RIVM Gezondheidsmonitor** 2012-2024 (`rivm-gezondheidsmonitor`) en de **Politie**-cijfers 2019-2025 (`politie-misdrijven`), voor heel Fryslân;
- de **RIVM-kaarten** (boomkroonbedekking, hitte-eiland) voor de testbuurten (`hittestress`).

Wat nog niet open is of nog geen adapter heeft (BAG, EP-Online, OpenStreetMap, interne indicatoren), komt uit [`init_data/sample/`](../../init_data/sample/README.md) via de use case `sample-bronbibliotheek`. Die waarden zijn gemarkeerd: de bron begint met `DEMODATA` (zie [demodata naar open data](../3-data-engineering/demodata-naar-open-data.md)). Niet gebruiken voor beleid.

De downloads staan daarna in het volume `bron-cache`; opnieuw installeren werkt dan ook offline. Gemeten op een verse installatie (02-10-2026, lege cache): `db-init` 80 seconden, waarvan 37 voor de CBS Kerncijfers. Zonder internet slaat `db-init` een bron over met een melding; de installatie blijft werken.

### Use cases installeren of bijwerken

Op de server, in-process (zelfde validatie als de laad-API):

```bash
docker compose run --rm db-init python -m omnitwin.usecases lijst                              # wat is er
docker compose run --rm db-init python -m omnitwin.usecases installeer --alle --inproces       # alles (opnieuw)
docker compose run --rm db-init python -m omnitwin.usecases installeer cbs-kerncijfers --inproces
```

Opnieuw installeren is veilig: een ongewijzigde levering wordt herkend, een gewijzigde wordt een nieuwe versie. Via de laad-API van een draaiende installatie, met een machineclient: `python -m omnitwin.usecases installeer hittestress` (zie [use cases, Uitvoeren](../../usecases/README.md#uitvoeren)).

### Eigen data aanleveren

Een eigen bron (bijvoorbeeld een export uit FME of een eigen database) levert aan via de [laad-API](../api/laden/README.md): een machineclient in Keycloak met de rol `dataset:<id>:laden` (zie [Keycloak](#keycloak-optioneel)), daarna leveren en de status volgen. Een nieuwe soort data begint met een use case volgens de [Use Case Specificatie](../specificaties/usecase/README.md); zie ook [CONTRIBUTING.md](../../CONTRIBUTING.md).

### Eerste SWF-vulling

Bij SWF komt de eerste vulling uit de lokale D-OmniTwin-database van de projectleider (https://github.com/TLaan/D-OmniTwin/issues/222, A1; openbaar volgens besluit van de projectleiding). Wat daarvan niet online te downloaden is, staat als bestand in git bij de use case waar het hoort en laadt dus vanzelf bij de eerste start (`LOAD_SAMPLE_DATA=true`):

- welstandsgebieden × buurt: [`swf-gebiedsindelingen`](../../usecases/swf-gebiedsindelingen/README.md);
- het Volledig Kompas zoals de projectleider het inrichtte: [`swf-kompasprofiel`](../../usecases/swf-kompasprofiel/README.md);
- de externe kaartlagen (WFS/WMS): [`swf-kaartlagen`](../../usecases/swf-kaartlagen/README.md).

Het Kompas en de kaartlagen gaan via de beheerroute, die nu alleen in-process bestaat (`installeer --inproces`, zoals `db-init`). Met de export van de huidige monitor (`SWF_DUMP_DIR`) komen daar de SWF-definities bij, en daarmee de monitorindicatoren in het Kompas.

Wat online te halen is maar nog geen adapter heeft (BAG, RVO EP-Online, OpenStreetMap), komt eenmalig uit de dump via [`swf-initialisatie`](../../usecases/swf-initialisatie/README.md): dump herstellen in een tijdelijke container, [`scripts/beheer/swf_export.py --uit`](../../scripts/beheer/swf_export.py) en

```bash
docker compose run --rm -v <export>:/swf-export:ro -v <monitorexport>:/swf-dump:ro \
  -e SWF_EXPORT_DIR=/swf-export -e SWF_DUMP_DIR=/swf-dump \
  db-init python -m omnitwin.usecases installeer swf-initialisatie --inproces
```

De precieze stappen staan in de [README van swf-initialisatie](../../usecases/swf-initialisatie/README.md#stappen). Een nieuwere dump: hetzelfde script met `--repo` werkt de bestanden in git bij (via een PR). Open data gaat nooit mee (die downloadt de eigen use case), demodata ook niet.

De oude routes `init_data/scripts/seed_fryslan.py` en het ETL-framework in `ETL/` zijn niet meer de weg om een installatie te vullen (https://github.com/TLaan/D-OmniTwin/issues/69). `ETL/` bevat nog bronscripts voor ontwikkelaars.

---

## 5. Bijwerken

1. **Maak een backup** van de database en de geüploade kaartlagen (zie [Backup](#backup)).
2. **Lees de [`CHANGELOG.md`](../../CHANGELOG.md)** voor elke versie tussen de jouwe en de nieuwe, vooral de paragraaf "Migreren". Gebruik je een eigen compose-bestand (bijvoorbeeld voor het logo of HTTPS), controleer dan of het nog past.
3. **Werk bij:**

   ```bash
   git pull
   docker compose up -d --build
   ```

4. **Controleer:** `docker compose ps -a` (zoals in [2.3](#23-starten)) en de migraties:

   ```bash
   docker compose run --rm db-init python -m omnitwin.migraties --status
   ```

`db-init` draait opnieuw, ziet dat de database bestaat en laat de data met rust. Wel past hij de nieuwe schemamigraties toe: elk bestand `db/migraties/V<nnn>__<naam>.sql` dat nog niet in de tabel `schema_migraties` staat, op volgorde, en registreert het daar (#54). De rollen en het schema `api` voor PostgREST en pg_featureserv werkt hij altijd bij (`R__api_rollen.sql`, zie [Beveiliging](#beveiliging)).

**Vanaf 0.1.x.** Een database van vóór 0.2.0 heeft nog geen tabel `schema_migraties`. De eerste keer maakt de runner die aan en draait hij V018 t/m V022 opnieuw; die zijn idempotent. Zie "Migreren vanaf 0.1.x" in de CHANGELOG.

**Geüploade kaartlagen.** Vanaf 0.2.1 staan bestanden die via beheer > externe lagen zijn geüpload in het volume `uploads` en overleven ze een update. In eerdere versies staan ze in de container en zijn ze na `--build` weg. Kopieer ze bij een update vanaf zo'n versie vóór stap 3 uit de container (dat doet de backup in stap 1) en zet ze daarna terug:

```bash
docker compose cp backups/data-upload-JJJJ-MM-DD/. backend:/app/data-upload
```

Wat er is toegepast, rechtstreeks in de database:

```bash
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM schema_migraties"'
```

### Embeddingmodel (offline)

AI-zoeken en de chat gebruiken het meertalige model [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small) (licentie MIT, 384 dimensies; tot #233 het Engelstalige `all-MiniLM-L6-v2`). Het model en de revisie (een commit-hash van HuggingFace) staan op één plek: `src/omnitwin/services/embedding_model.py`. Hoe zoeken werkt (begrippen en synoniemen uit `db/stuurdata/synoniemen.json`, woorden uit de naam en betekenis) staat in `src/omnitwin/services/zoektaal.py`; de kwaliteit meet je met `python scripts/ai/evalueer_assistent.py --url http://localhost` (zie [use case assistent-kwaliteit](../../usecases/assistent-kwaliteit/README.md)).

- `docker compose build` downloadt die revisie naar `/opt/models/multilingual-e5-small` in de image en slaat de gewichten op als float16 (225 MB in plaats van 450 MB; bij het laden weer float32, zonder meetbaar verschil). Het model maakt de image circa 250 MB groot (totaal ± 1,8 GB uitgepakt, grens in CI 1900 MiB). Alleen bij het bouwen is HuggingFace nodig.
- Backend en `db-init` draaien met `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` en `HF_HUB_DISABLE_TELEMETRY=1`: geen download en geen telemetrie, ook niet bij een nieuwe container. AI-zoeken werkt zonder internet.
- Het model staat buiten `/app`, dus ook in ontwikkelmodus (bind-mount van de repo over `/app`) blijft het zichtbaar.
- Controleren: `/api/ai/health` toont onder `embedding_model` de revisie, `lokaal` en `offline`.

Model bijwerken naar een nieuwere revisie:

1. Zoek de commit-hash op `https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/commits/main` en zet die in `MODEL_REVISIE` in `src/omnitwin/services/embedding_model.py`.
2. Bouw opnieuw: `docker compose up -d --build`.
3. De embeddings worden bij de volgende `db-init` vanzelf opnieuw berekend: per indicator staat in `indicator_embeddings.tekst_hash` een hash van model, revisie en tekst (migratie V028). Meteen: `docker compose exec backend python scripts/ai/genereer_embeddings.py`.

Een ander model met een andere dimensie (niet 384) vraagt ook een schemawijziging van `indicator_embeddings`. Een ander model vraagt ook nieuwe waarden voor `GELIJKENIS_MARGE_ONDER/BOVEN` en de voorvoegsels in `embedding_model.py`: meet met de evaluatie.

**Na een levering met nieuwe of gewijzigde indicatoren** (laad-API, profiel `definities`): roep `herbereken_embeddings(db, indicator_uuids)` uit `src/omnitwin/services/indicator_embeddings.py` aan na de commit van de publicatie. Die berekent alleen wat nieuw of gewijzigd is, laadt het model alleen als er iets te doen is, en commit zelf. Zonder die aanroep vindt de assistent de nieuwe indicatoren pas na de volgende `db-init` op betekenis (op naam en synoniemen wel meteen).

---

## 6. Beheer

### Status en logs

```bash
docker compose ps -a
docker compose logs -f backend          # of: db-init, postgres, postgrest, pg_featureserv, traefik
docker compose logs --tail 100 backend
```

De backend schrijft ook naar de databasetabel voor logs (`app_logs`); die zijn in te zien via de beheeromgeving.

Bewaartermijnen (#264):

- **Database-logs:** alle niveaus worden na `LOG_BEWAAR_DAGEN` (standaard 30) verwijderd, DEBUG na 7 dagen. In waarschuwingen staan IP-adressen (elk verzoek met status 4xx) en gebruikersnamen (geblokkeerde logins); het IP-adres wordt na `LOG_IP_BEWAAR_DAGEN` (standaard 7) ingekort. De opruimtaak draait 5 minuten na de start van de backend en daarna elke 24 uur; in de beheeromgeving (Logs > Nu uitvoeren) kan het meteen.
- **Containerlogs** (`docker compose logs`): per container hoogstens 3 bestanden van 10 MB (`x-logging` in `docker-compose.yml`). Daarin staan geen IP-adressen van bezoekers.
- **Het IP-adres** komt van Traefik (`X-Forwarded-For`) en wordt alleen vertrouwd als het verzoek van een vertrouwde proxy komt (`TRUSTED_PROXIES`; achter een eigen TLS-proxy ook `TRAEFIK_TRUSTED_IPS`). Een bezoeker kan het dus niet zelf invullen.

### Stoppen en starten

```bash
docker compose stop        # stoppen, alles blijft bewaard
docker compose up -d       # weer starten
docker compose down        # containers verwijderen; de volumes (database, uploads) blijven bewaard
```

### Backup

Voor productie: gebruik `sh scripts/beheer/backup.sh` en `restore.sh` (met Keycloak, de volumes, controlesommen en bewaartermijn), zie de [beheerhandleiding](beheerhandleiding.md#2-back-up-en-herstel). Hieronder de losse commando's.

De data staat in twee Docker-volumes: `pgdata` (de database) en `uploads` (geüploade kaartlagen, in de container `/app/data-upload`). Het volume `bron-cache` hoeft niet mee: dat is opnieuw te downloaden.

```bash
mkdir -p backups
# Database
docker compose exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/omnitwin.dump'
docker compose cp postgres:/tmp/omnitwin.dump backups/omnitwin-$(date +%F).dump
docker compose exec postgres sh -c 'rm /tmp/omnitwin.dump'
# Geüploade kaartlagen
docker compose cp backend:/app/data-upload backups/data-upload-$(date +%F)
```

- `backups/` en `*.dump` staan in `.gitignore`; zet een backup nooit in git. Een dump bevat gebruikers, gehashte wachtwoorden en sessies, logs en de AI-configuratie: bewaar hem net zo zorgvuldig als `.env`.
- Bewaar `.env` apart en veilig. Een restore in een nieuwe installatie werkt ook met een nieuw `DATABASE_PASSWORD`.
- Dit werkt ook op Windows (Git Bash). Gebruik in PowerShell geen `pg_dump ... > bestand`: PowerShell 5 verminkt binaire uitvoer bij omleiden. De `sh -c '...'`-vorm voorkomt ook dat Git Bash `/tmp/...` omzet naar een Windows-pad.

### Restore

Terugzetten in een lege installatie:

```bash
docker compose down -v                 # LET OP: verwijdert de huidige database en uploads
docker compose up -d postgres
docker compose cp backups/omnitwin-JJJJ-MM-DD.dump postgres:/tmp/omnitwin.dump
docker compose exec postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner /tmp/omnitwin.dump'
docker compose up -d
docker compose cp backups/data-upload-JJJJ-MM-DD/. backend:/app/data-upload
```

Wacht na `up -d postgres` tot `docker compose ps` voor `postgres` *healthy* toont. `pg_restore` eindigt met drie meldingen `schema "tiger" / "tiger_data" / "topology" already exists` en `errors ignored on restore: 3` (exitcode 1). Die zijn onschuldig: de PostGIS-image maakt deze schema's zelf al aan. Andere fouten zijn dat niet. Na de restore herkent `db-init` de bestaande database: hij laat de data met rust en past alleen de migraties toe die nog openstaan (zie [Bijwerken](#5-bijwerken)).

Voor het overzetten van een complete database naar een andere organisatie, zie ook [`stappenplan_docker_installatie_externe_organisatie.md`](./stappenplan_docker_installatie_externe_organisatie.md) (aanvullend).

### Opnieuw beginnen

```bash
docker compose down -v
docker compose up -d
```

`-v` verwijdert alle volumes van dit project: de database (`pgdata`), de geüploade kaartlagen (`uploads`) en de download-cache (`bron-cache`). `db-init` richt de database daarna opnieuw in.

### Eigen organisatie

Elke organisatie draait een eigen instantie (ADR 0007). Wie die instantie beheert, staat als data in de tabel `organisatie`: naam, korte naam, OIN (optioneel), CBS-gemeentecode(s) van het eigen gebied, standaard-benchmarkprovincie, contactadres, de logo's in de footer en het thema (huisstijl: `static/css/themes/<thema>.css`, alleen `a-z`, `0-9` en `-`; standaard `d-omnitwin`). Standaard staat daar Súdwest-Fryslân. Lezen: `GET /api/organisatie`. Een eigen thema maken en welke tokens erin horen: [Thema's](thema-s.md).

De eerste gemeentecode is de standaard-referentie in de rapporten ("⌀ Gemeente ...") en bepaalt welke buurten bij een omgevingsvisie-deelgebied horen.

- **Nieuwe installatie:** pas vóór de eerste start `db/stuurdata/organisatie.sql` aan. `db-init` laadt het bestand alleen als de tabel nog leeg is. Met een kant-en-klare image (zonder eigen build): mount je eigen bestand in `db-init` op `/app/db/stuurdata/organisatie.sql`, of gebruik de SQL hieronder.
- **In het beheerscherm** (aanbevolen, [#253](https://github.com/TLaan/D-OmniTwin/issues/253)): **Organisatie** in het menu, alleen voor beheerders. Thema kiezen (met voorbeeld in licht en donker), naam, korte naam, code, contactadres, OIN, gemeenten van het eigen gebied (met de standaardgemeente), standaard-benchmarkprovincie en de footer-logo's (volgorde, toevoegen uit bestaande bestanden onder `static/images/`, verwijderen). Ongeldige invoer (een thema of logo dat niet bestaat, een ongeldig e-mailadres, een gemeentecode die geen vier cijfers is) wordt geweigerd. Na opslaan een gewone herlaadactie; geen herstart. Elke wijziging staat in de log (categorie `ADMIN`, met gebruikersnaam en `sub`). Het inlogthema van Keycloak wisselt niet mee: zie [Thema's](thema-s.md#thema-kiezen-in-het-beheerscherm).
- **Overnemen van of naar een andere instantie:** **Exporteren (JSON)** geeft een bestand `organisatie-<code>.json` (`GET /api/organisatie/export`, zonder geheimen); **Importeren (JSON)** in de andere instantie zet het over (`POST /api/organisatie/import`), met dezelfde controles. Thema en logo's moeten daar ook als bestand bestaan, anders weigert de import. Of je een instelling overneemt, beslist de organisatie van die instantie (ADR 0007).
- **Bestaande installatie, met SQL:** wijzig de rij met SQL (`docker compose exec postgres psql -U <DATABASE_USER> -d <DATABASE_NAME>`), bijvoorbeeld:

  ```sql
  UPDATE organisatie SET
      code = 'lwd', naam = 'Gemeente Leeuwarden', korte_naam = 'Leeuwarden',
      gemeente_codes = ARRAY['0080'], contact_email = 'info@example.nl',
      logos = '[{"pad": "/static/images/mijn-logo.png", "naam": "Gemeente Leeuwarden", "rol": "eigen"}]';
  ```

  Een eigen logobestand zet je onder `static/images/` (of mount je, zoals bij het beeldmerk hieronder). Herlaad de pagina; een herstart is niet nodig.

Nog niet uit deze instelling: de benchmarkmodus `fryslan`, de welkomsttekst en de startpositie van de kaart (zie [#231](https://github.com/TLaan/D-OmniTwin/issues/231)).

### Eigen logo

Het logo linksboven, het favicon en het logo in het beheerscherm en de rapporten komen uit één bestand: `static/images/beeldmerk.svg`. Standaard staat daar een neutraal, tijdelijk D-OmniTwin-beeldmerk (#83). Er is geen instelling in `.env` voor nodig.

Linksboven krijgt het beeldmerk de kleuren van het thema: de tokens `--d-omnitwin-beeldmerk-vlak`, `--d-omnitwin-beeldmerk-lijn` en `--d-omnitwin-beeldmerk-kern` (in het SWF-thema wit met SWF-rood). Het favicon, het beheerscherm en de rapporten tonen de vaste kleuren uit het bestand. Een eigen SVG-logo zet zijn inhoud in een groep `<g id="beeldmerk">…</g>`, anders blijft de plek linksboven leeg; gebruikt je logo de tokens niet, dan houdt het zijn eigen kleuren.

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


### Keycloak (optioneel)

Keycloak is de identity provider voor 0.3.0: inloggen via OIDC voor mensen, en client credentials voor machines, zoals een ETL die data aanlevert (#214, #205). Het zit in de stack als compose-profiel `keycloak`; zonder dat profiel start de stack zoals altijd. De backend controleert tokens op de nieuwe API's (laad-API) zodra `OIDC_ISSUER` is ingevuld (zie hieronder). Met `OIDC_ISSUER` log je ook in de beheeromgeving in via Keycloak, en beheer je gebruikers en rollen in Keycloak (zie *Inloggen in de beheeromgeving*). In de kaartapplicatie kun je dan ook inloggen, en desgewenst de hele kaart achter de login zetten (zie [Toegang tot de viewer](#toegang-tot-de-viewer-open-of-dicht)).

**Opzet**

- Image `quay.io/keycloak/keycloak` (vaste versie in `docker-compose.yml`), in productiemodus (`start`) achter Traefik op **`/auth`**. Alleen HTTP binnen het Docker-netwerk. Health en metrics staan op de interne poort 9000 en zijn van buiten niet bereikbaar. In [ontwikkelmodus](#3-ontwikkelmodus) draait hij als `start-dev`.
- Database: in dezelfde PostgreSQL een eigen database `keycloak` met een eigen rol `keycloak`. De eenmalige service `keycloak-db-init` maakt die aan (alleen met het profiel). Andere rollen kunnen er niet bij.
- Bij de eerste start importeert Keycloak de realm **`omnitwin`** uit [`deploy/keycloak/realm-omnitwin.json`](../../deploy/keycloak/realm-omnitwin.json). Een bestaande realm laat hij staan; wijzigingen daarna doe je in de admin-console. Een andere realmnaam: pas `realm` in het bestand aan vóór de eerste start.

| In de realm | Wat |
|---|---|
| client `omnitwin-web` | Inloggen van mensen (kaart en beheer): public client, authorization code + PKCE (S256). Redirect-URI's: `http://localhost/*` en `OMNITWIN_BASE_URL/*` (het adres van de installatie, zie [2.2](#22-env-aanmaken)), bij de import ingevuld. Ander adres na de eerste start: aanpassen in de admin-console (Clients > omnitwin-web > *Valid redirect URIs*, ook *Valid post logout redirect URIs*). |
| client `omnitwin-api` | Staat voor de API van D-OmniTwin: draagt de rollen voor het laden van data en is de audience (`aud`) van de tokens. Zelf geen inlogflow. |
| client `etl-voorbeeld` | Voorbeeld-machineclient: alleen client credentials, rol `dataset:voorbeeld:laden`. Keycloak genereert het secret bij de import; het staat niet in de repo. |
| realm-rollen `beheerder`, `gebruikersbeheerder`, `lezer` | Voor mensen. `beheerder` geeft beheerrechten in de beheeromgeving en op de beheer-API's. `gebruikersbeheerder` geeft gebruikersbeheer in de Keycloak-console (gebruikers en groepen, geen clients of realm-instellingen); bewust een aparte rol, zodat je dat recht los toekent. Elke nieuwe gebruiker krijgt `lezer` (geen beheer). De koppeling rol → rechten staat in de realmexport, dus is als data uitwisselbaar tussen instanties. |
| client-rollen op `omnitwin-api` | `datasets:laden` (alle datasets) en per dataset `dataset:<id>:laden`. |
| inlogpagina | `loginTheme` `swf`: de huisstijl van het organisatiethema (`deploy/keycloak/themes/`, zie [Thema's](thema-s.md#inlogpagina-keycloak)). |
| instellingen | Access token 5 minuten, geen implicit of password grant (behalve de tijdelijke loginclient van testaccounts, zie onder), brute-force-detectie aan (na 5 mislukte pogingen oplopend wachten), geen zelfregistratie, wachtwoorden minimaal 12 tekens (in een [demo-omgeving](#26-demo-test-of-productie) 5). |

**Aanzetten**

1. Zet in `.env` (zie [2.2](#22-env-aanmaken)) `COMPOSE_PROFILES=keycloak`, `KEYCLOAK_ADMIN_PASSWORD` en `KEYCLOAK_DB_PASSWORD` (beide met `openssl rand -hex 24`). Buiten je eigen machine ook `KEYCLOAK_HOSTNAME`: de hostnaam waaronder gebruikers de stack bereiken. Achter HTTPS (manier A of B in [HTTPS aanzetten](#https-aanzetten)) de volledige URL: `KEYCLOAK_HOSTNAME=https://omnitwin.example.nl/auth`.
2. `docker compose up -d`. `docker compose ps -a` toont `keycloak` als *healthy* (na ongeveer een halve minuut) en `keycloak-db-init` als `Exited (0)`.
3. Controle: `http://<host>/auth/realms/omnitwin/.well-known/openid-configuration` geeft JSON.
4. Tokens laten controleren door de backend: zet `OIDC_ISSUER` op de waarde van `issuer` uit die JSON zoals je hem van buiten opvraagt, bijvoorbeeld `http://localhost/auth/realms/omnitwin` (met een andere poort dan 80: `http://localhost:<poort>/auth/realms/omnitwin`; achter HTTPS: `https://omnitwin.example.nl/auth/realms/omnitwin`), en herstart met `docker compose up -d`. De backend haalt de sleutels intern op (`http://keycloak:8080/auth/...`) en controleert handtekening, `iss`, `aud` (`omnitwin-api`), `exp` en de rol. Controle met een token van een machineclient (zie hieronder): `curl -H "Authorization: Bearer <token>" http://<host>/api/oidc/ik` geeft de client en de rollen.

**Inloggen in de beheeromgeving** (#251, [ADR 0008](../2-architectuur/adr/0008-inloggen-beheer-via-keycloak-bff.md)). Met `OIDC_ISSUER` gezet toont `http://<host>/admin/login` de knop **Inloggen met Keycloak**. Je logt in op het formulier van Keycloak en komt terug in de beheeromgeving. Wat je mag, komt uit de realm-rol:

- `beheerder`: alle beheerpagina's en beheer-API's;
- alleen `lezer`: ingelogd, maar geen beheer; de inlogpagina meldt dat de rol ontbreekt;
- intrekken werkt binnen enkele minuten: de backend ververst de sessie bij Keycloak elke 5 minuten (levensduur van het access token); een uitgeschakelde gebruiker of beëindigde sessie is dan uitgelogd. Na 30 minuten zonder activiteit of 12 uur in totaal moet je opnieuw inloggen.

Uitloggen beëindigt ook de sessie bij Keycloak. Wie ingelogd is via Keycloak, wijzigt zijn wachtwoord in Keycloak (menu rechtsboven: *Mijn account*), niet in de beheeromgeving. Een script kan de beheer-API's ook met een token aanroepen: `Authorization: Bearer <token>` van een gebruiker of machineclient met de rol `beheerder` (naast de bestaande `X-Admin-Key`).

De browser krijgt geen token: de backend doet het inloggen bij Keycloak en zet een sessiecookie (`HttpOnly`), net als bij het lokale inloggen. In de log staan bij inloggen en weigeren alleen `sub` en de gebruikersnaam, nooit e-mail of tokens; zet de categorie `AUTH` in de Log Viewer op `INFO` als je ook geslaagde logins wilt bewaren (standaard alleen waarschuwingen).

**Gebruikers en rollen beheren** doe je in de admin-console van Keycloak, niet in D-OmniTwin; in de beheeromgeving staat de link *Gebruikers en rollen beheren* in het menu rechtsboven (`http://<host>/auth/admin/omnitwin/console/`). Een gebruiker aanmaken: realm `omnitwin` > Users > *Create new user*, daarna tab *Credentials* > *Set password* en tab *Role mapping* > *Assign role* > `beheerder`. Die link opent de console van realm `omnitwin`; daar log je in met een gebruiker uit die realm met de realm-rol `gebruikersbeheerder` (samengesteld uit `realm-management` > `manage-users`, `view-users`, `query-users`, `query-groups` en `view-realm`). De rol `beheerder` geeft die rechten niet: wie gebruikers mag beheren, ken je bewust toe (minste rechten). Een bestaande realm (van vóór deze versie) heeft de rol nog niet: maak hem aan onder Realm roles > *Create role* > `gebruikersbeheerder`, zet *Composite* aan en voeg de vijf client-rollen van `realm-management` toe. De beheerder van Keycloak zelf (realm `master`, zie hieronder) gebruikt `http://<host>/auth/admin/`.

**Noodtoegang.** Met Keycloak aan staan de lokale accounts (`ADMIN_USER`, tabel `users`) uit. Werkt Keycloak niet, zet dan tijdelijk `LOKAAL_INLOGGEN=true` in `.env` en `docker compose up -d`. De inlogpagina toont dan ook het formulier met gebruikersnaam en wachtwoord, met een waarschuwing; de log meldt het bij de start en bij elke lokale login. Zet het daarna weer uit. Zonder Keycloak (geen `OIDC_ISSUER`) werkt het lokale inloggen zoals altijd.

**Bestaande installatie.** De realm wordt alleen bij de eerste start geïmporteerd. Draaide Keycloak al vóór deze versie, controleer dan bij Clients > omnitwin-web of je eigen adres in *Valid redirect URIs* en *Valid post logout redirect URIs* staat (bijvoorbeeld `https://omnitwin.example.nl/*`). Zet vóór het aanzetten van `OIDC_ISSUER` minstens één gebruiker met de rol `beheerder` klaar, anders kan niemand meer beheren (behalve via noodtoegang).

**Eerste login op de admin-console.** Ga naar `http://<host>/auth/admin/` en log in als `admin` met `KEYCLOAK_ADMIN_PASSWORD`. Dat is een tijdelijke beheerder in realm `master`. Maak een eigen beheerder aan (realm `master` > Users, rol `admin`) en verwijder daarna de tijdelijke. Gebruikers voor D-OmniTwin maak je aan in realm `omnitwin` (Users); een beheerder krijgt de rol `beheerder`.

**Machineclient voor een ETL.** Per ETL of aanleverende partij een eigen client, niet één gedeelde:

1. Realm `omnitwin` > Clients > Create client: OpenID Connect, client-id bijvoorbeeld `etl-<bron>`.
2. *Client authentication* aan, alleen *Service accounts roles* aangevinkt (geen standard flow, geen direct access grants).
3. Tab *Service accounts roles* > Assign role > filter op clients: `omnitwin-api` > `dataset:<id>:laden`. Een nieuwe datasetrol maak je bij Clients > omnitwin-api > Roles.
4. Tab *Client scopes* > `etl-<bron>-dedicated` > Configure a new mapper > *Audience*, included client audience `omnitwin-api` (zoals bij `etl-voorbeeld`).

Secret opvragen (met `--nieuw` erachter: eerst een nieuw secret maken), met de tijdelijke beheerder:

```bash
docker compose exec keycloak bash /opt/keycloak/omnitwin/client-secret.sh etl-voorbeeld
```

Heb je de tijdelijke beheerder al verwijderd, zet dan `-e KC_BEHEERDER=<naam>` na `exec` (het wachtwoord wordt gevraagd), of kijk in de admin-console bij Clients > `<client>` > Credentials. Geef het secret via een veilig kanaal door, nooit per mail of in git. De ETL haalt er zo een token mee op (5 minuten geldig):

```bash
curl -s -u etl-voorbeeld:<secret> -d grant_type=client_credentials \
  http://<host>/auth/realms/omnitwin/protocol/openid-connect/token
```

**Rollen voor een use case.** Een use case noemt in `actoren` welke gebruikers en machineclients hij nodig heeft, met hun rollen (zie [Use cases](../../usecases/README.md#actoren-en-testaccounts)), nooit wachtwoorden. In productie maak je die accounts zelf aan zoals hierboven en wijs je de rollen toe; de use case laat alleen zien welke nodig zijn.

**Testaccounts (alleen test en dev).** De use-case-uitvoerder kan de actoren van een use case tijdelijk aanmaken in realm `omnitwin` en daarmee installeren en de rechten controleren (https://github.com/TLaan/D-OmniTwin/issues/223):

```bash
export OMNITWIN_TESTACCOUNTS=1                    # expliciete toestemming; geweigerd bij OMNITWIN_OMGEVING=productie
export OMNITWIN_BASE_URL=http://localhost         # of het adres van de teststack
export KEYCLOAK_ADMIN_PASSWORD=...                # uit .env, niet tonen of loggen
python -m omnitwin.usecases test swf-definities --testaccounts
python -m omnitwin.usecases opruimen swf-definities
```

- Accounts heten `uc-<usecase>-<actor>` (gebruiker of machineclient), plus per use case een loginclient `uc-<usecase>--login` met alleen de wachtwoordgrant, zodat de uitvoerder tokens van de testgebruikers kan halen. Dat is de enige plek met een password grant, en alleen zolang de testaccounts bestaan. De clients hebben de attributen `omnitwin.usecase` en `omnitwin.testaccount.tot` (standaard 24 uur, `OMNITWIN_TESTACCOUNTS_UUR`); `opruimen` verwijdert alles met het prefix en het kenmerk van de use case.
- Wachtwoorden en secrets zijn willekeurig en staan alleen in `.usecase-accounts.json` in de map waar je de uitvoerder draait (in `.gitignore`, alleen leesbaar voor jou; ander pad: `OMNITWIN_TESTACCOUNTS_BESTAND`). De uitvoerder logt ze niet.
- Toegang tot de admin-API: standaard de tijdelijke beheerder `admin` uit realm `master` (`KEYCLOAK_ADMIN_PASSWORD`, eventueel `KEYCLOAK_ADMIN` voor een andere naam). Is die weg, maak dan in realm `omnitwin` een machineclient met *Service accounts roles* `realm-management` > `manage-users`, `manage-clients`, `view-realm`, `view-clients` en `query-users`, en geef `KEYCLOAK_ADMIN_CLIENT_ID` en `KEYCLOAK_ADMIN_CLIENT_SECRET` mee. Keycloak zelf: `KEYCLOAK_URL` (standaard `OMNITWIN_BASE_URL` + `/auth`).
- Zonder `OMNITWIN_TESTACCOUNTS=1`, of met `OMNITWIN_OMGEVING=productie`, weigert de uitvoerder (exitcode 2) en maakt hij niets aan.

**Entra ID of een andere identity provider koppelen.** Realm `omnitwin` > Identity providers > *Microsoft* (Entra ID) of *OpenID Connect v1.0*. Vul de client-id, het secret en (bij OIDC) de discovery-URL van de andere partij in. Registreer bij die partij de *Redirect URI* die Keycloak toont (`https://<host>/auth/realms/omnitwin/broker/<alias>/endpoint`). Rollen ken je per gebruiker toe, of leid je af uit een groep of claim met een *mapper* op de identity provider. Op de inlogpagina verschijnt dan een knop.

**Backup.** De Keycloak-gegevens (realm, gebruikers, clients en secrets) staan in de database `keycloak`, niet in de dump uit [Backup](#backup). Maak er een eigen dump van:

```bash
docker compose exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d keycloak -Fc -f /tmp/keycloak.dump'
docker compose cp postgres:/tmp/keycloak.dump backups/keycloak-$(date +%F).dump
docker compose exec postgres sh -c 'rm /tmp/keycloak.dump'
```

**Openstellen.** Naast de [checklist](#checklist-vóór-openstelling): de admin-console (`/auth/admin`) hoeft niet van buiten bereikbaar te zijn; scherm hem bij voorkeur af in de proxy ervoor. Achter een TLS-proxy die over HTTP doorstuurt (manier A) ziet Keycloak alleen HTTP; zet `KEYCLOAK_HOSTNAME` daarom op de volledige `https://`-URL.

### Toegang tot de viewer (open of dicht)

Standaard (`VIEWER_TOEGANG=open`) is de kaart op `http://<host>/` voor iedereen open (#266, [ADR 0009](../2-architectuur/adr/0009-viewer-achter-login-forwardauth.md)). Staat [Keycloak](#keycloak-optioneel) aan (met `OIDC_ISSUER`), dan leidt **Beheer** rechtsboven in de kaart naar het inloggen; ingelogd zie je je gebruikersnaam en **Uitloggen**. Er is geen aparte inlogknop.

**Viewer dichtzetten**, zoals de huidige SWF-monitor: zet in `.env`

```bash
VIEWER_TOEGANG=inloggen
```

en `docker compose up -d`. Daarna:

- `http://<host>/` stuurt je door naar het inlogformulier van Keycloak en daarna terug naar de kaart;
- toegang alleen met de realm-rol `lezer` of `beheerder` (elke nieuwe Keycloak-gebruiker krijgt `lezer`); ingelogd zonder die rol: pagina *Geen toegang* met uitloggen;
- ook de data-API's zijn dicht: de API's van de backend (`/api/gebiedsmonitor`, `/api/kompas`, `/api/chat`, `/api/report`, ...), `/api/data` (PostgREST), `/api/geo` (pg_featureserv) en `/docs`. Zonder sessie geven ze `401`, zonder rol `403`. Scripts kunnen met een bearer-token met de rol `lezer` of `beheerder`, of met `X-Admin-Key`;
- open blijven: `/health`, het inloggen zelf, de beheeromgeving (vraagt zelf om inloggen), de laad-API (eigen tokens), `/api/organisatie` (naam en thema voor de inlogpagina) en `/static/` (code en opmaak, geen data).

Zonder Keycloak (geen `OIDC_ISSUER`) kan bij `inloggen` alleen een lokale beheerder de kaart zien (inloggen via `/admin/login`); gebruik dan Keycloak. `/api/data` en `/api/geo` lopen via een controle in Traefik (forwardAuth naar de backend, `deploy/traefik/dynamic.yml`); die staat altijd aan en laat bij `open` alles door (behalve interne lagen, hieronder).

### Toegang per laag en bron (openbaar of intern)

Ook bij een open viewer kan een deel van de data intern zijn: alleen zichtbaar na inloggen met de realm-rol `lezer` of `beheerder` (#254, [ADR 0010](../2-architectuur/adr/0010-toegang-per-laag-en-bron.md)). Wat intern is, staat als data bij de dataset, niet in een instelling:

- **Via de laad-API** bepaalt `dct:accessRights` in de registratie het: `http://publications.europa.eu/resource/authority/access-right/PUBLIC` is openbaar, `RESTRICTED` (of `NON_PUBLIC`) is intern. Dat geldt voor de kaartlaag van de dataset, de indicatoren die hij definieert of waarvan hij alle waarden levert, en zijn waarden. `GET /api/laden/v1/datasets/{id}` toont het afgeleide veld `toegang`. Wijzig je `dct:accessRights` (PUT of PATCH), dan volgt wat de dataset al publiceerde direct.
- **Een eigen externe laag** (beheer > externe lagen) is standaard openbaar; via de beheer-API zet je `"toegang": "intern"` (`PUT /api/admin/externe-lagen/{id}`).
- Alles wat niet via de laad-API kwam (stuurdata, eerdere uploads, PDOK-lagen), is openbaar. Na het bijwerken naar deze versie (migratie V032) verandert er daarom niets, behalve voor datasets die al `RESTRICTED` waren: hun data is nu intern, en hun kaartlaag (die tot nu toe uit stond) staat aan voor ingelogden.

Zonder inloggen staan interne lagen en indicatoren niet in de lijsten van de kaart, Kompas, rapporten en chat, en geeft een directe aanroep `401` (ingelogd zonder rol: `403`): de backend leest anonieme verzoeken als databaserol `omnitwin_openbaar`, met row level security op `indicatoren`, `gebied_data` en `externe_kaartlagen`. PostgREST filtert in de views van schema `api` op de header `X-Omnitwin-Toegang`, die alleen de forwardAuth zet (Traefik verwijdert een meegestuurde header). Ingelogd met `lezer` of `beheerder` zie je alles, met het label *intern* in de lagenlijst en de indicatorkeuze. De use case [`rechten-per-laag`](../../usecases/rechten-per-laag/README.md) laadt een interne voorbeeldlaag en -indicator (DEMODATA) om het te zien.

Let op: Keycloak geeft elke nieuwe gebruiker én elk service account (machineclient) standaard de rol `lezer` (`default-roles-omnitwin`). Een ETL-client ziet dan ook interne data. Wil je dat niet, haal dan in de admin-console bij de client > *Service accounts roles* de rol `default-roles-omnitwin` weg.

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
| `db-init` meldt "De database is half geïnitialiseerd" | Een eerdere eerste start is halverwege gestopt; de oorzaak staat in de log van die run. Nieuwe installatie: `docker compose down -v` en `docker compose up -d --build`. Bestaande installatie waar alleen de beheerder ontbreekt: `docker compose run --rm db-init python /app/init_data/scripts/create_admin.py` en daarna `docker compose up -d`. De melding zelf geeft dezelfde stappen. |
| `backend` wordt niet *healthy* | `docker compose logs backend`. De backend heeft bij de start tot een minuut nodig. Blijft hij *unhealthy*, controleer de databaseverbinding en `.env`. |
| Kaart laadt geen buurten | Controleer `http://<host>/api/geo/collections`. Leeg of fout: kijk in `docker compose logs pg_featureserv`. Na een restore of handmatige schemawijziging: `docker compose restart pg_featureserv postgrest`. |
| Inloggen lukt, maar je blijft op het inlogscherm | Het sessiecookie heeft `Secure` en de verbinding is HTTP. Staat `COOKIE_SECURE=true` in `.env` zonder HTTPS ervoor? Zet het op `auto` (standaard) en draai `docker compose up -d`. |
| `function similarity(...) does not exist` of ontbrekende tabel `deduplicatie_uitzonderingen` | Oudere database zonder migraties V018/V019. Zie [Bijwerken](#5-bijwerken). |
| Geüploade kaartlaag geeft "Lokaal bestand niet gevonden" | Het bestand is weg, bijvoorbeeld na een update vanaf een versie zonder volume `uploads`. Zet het terug uit de backup (zie [Bijwerken](#5-bijwerken)) of upload het opnieuw. |
| Wijziging in `.env` heeft geen effect | `docker compose up -d` (niet `restart`): alleen dan worden containers met de nieuwe waarden opnieuw gemaakt. |
| Windows: `db-init` faalt met `/bin/bash^M: bad interpreter` | Het shell-script is met CRLF uitgecheckt. Controleer of `.gitattributes` aanwezig is, zet het script opnieuw neer met `rm docker-entrypoint.sh && git checkout -- docker-entrypoint.sh` en bouw opnieuw (`docker compose up -d --build`). |
| AI-zoeken of de chat vindt geen indicatoren | Er zijn geen embeddings. Kijk in `docker compose logs db-init` naar `Embeddings niet gegenereerd`; controleer met `/api/ai/health` of het model lokaal staat (anders: `docker compose build`). Draai daarna `docker compose run --rm db-init`: die vult alleen de ontbrekende embeddings aan. Na het goedkeuren van nieuwe beschrijvingen: `docker compose exec backend python scripts/ai/genereer_embeddings.py --opnieuw`. |
| AI-chat of samenvatting duurt minuten | Het model is een *thinking*-variant. Bij Ollama zijn `qwen3:4b` en `qwen3:30b` zonder toevoeging thinking-varianten; kies in **AI Configuratie** een `*-instruct`-variant (bijvoorbeeld `qwen3:30b-instruct`). Op een laptop zonder GPU blijft een samenvatting met een lokaal model ruim een minuut duren. |
| AI-chat geeft geen antwoord | Controleer in **AI Configuratie** de API-URL: vanuit de container is dat `http://host.docker.internal:11434`, niet `localhost`. Op Linux moet Ollama op alle interfaces luisteren (zie [LLM](#7-llm-optioneel)). |
| Ontwikkelmodus op Windows: backend start niet, `PermissionError: /app/logs/server.log` | De backend draait als niet-root-gebruiker en mag niet schrijven in de gemounte projectmap. Bijgewerkte `docker-compose.override.yml` gebruikt een apart logvolume (#59/#115). |
| Twee installaties op één host | Geef elke installatie een eigen map, een eigen `OMNITWIN_HTTP_PORT` en een eigen projectnaam (`COMPOSE_PROJECT_NAME=...` in `.env`). Traefik routeert alleen naar containers van het eigen project. |

---

## Beveiliging

Stel een installatie **niet** open voor internet of een breed netwerk voordat deze punten geregeld zijn:

- **HTTPS.** Traefik luistert in de standaardopzet alleen op HTTP. Zet HTTPS aan (zie [HTTPS aanzetten](#https-aanzetten)). Het inlogcookie krijgt dan `Secure`, zodat de browser het alleen via HTTPS stuurt: bij manier B vanzelf (`COOKIE_SECURE=auto`), bij manier A met `COOKIE_SECURE=true`.
- **Begrenzing van anonieme verzoeken.** De backend begrenst inloggen en de AI-routes zelf (zie hieronder). De tellers staan per backend-proces in het geheugen; wil je strakkere of gedeelde grenzen (meerdere backends, een externe betaalde LLM-aanbieder), zet dan ook een limiet in de proxy ervoor.
- **`.env` geheim houden.** Het bevat het databasewachtwoord en eventueel de `ADMIN_API_KEY` en sleutels van LLM-aanbieders.

Verder nog open: de CSP staat `'unsafe-inline'` toe (zie [Security-headers](#security-headers)), en de rollen voor PostgREST en pg_featureserv delen het databasewachtwoord (zie [hieronder](#postgrest-en-pg_featureserv)).

### Wie mag wat

- **Beheerroutes** (`/api/admin/*` behalve inloggen, en `/api/visualisatie/admin/*`) vereisen een ingelogde beheerder (lokaal: `is_admin`; via Keycloak: realm-rol `beheerder`), een bearer-token van Keycloak met de rol `beheerder`, of een geldige `X-Admin-Key`. Zonder login of token: `401`; zonder beheerrechten: `403`.
- Nieuwe gebruikers zijn standaard **geen** beheerder (`users.is_admin` standaard `false`). Het account uit `ADMIN_USER` is wel beheerder.
- Sessies staan gehasht in de database en verlopen na 12 uur; verlopen sessies worden bij het inloggen opgeruimd.

**Publiek, zonder inloggen**, zijn (bij `VIEWER_TOEGANG=open`, de standaard; met `inloggen` zijn de kaart en alle data-API's alleen toegankelijk met de rol `lezer` of `beheerder`, zie [Toegang tot de viewer](#toegang-tot-de-viewer-open-of-dicht)):

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
| `/api/geo/*` | pg_featureserv (kaartgeometrie), alleen-lezen |
| `/api/data/*` | PostgREST, alleen-lezen views in schema `api` (zie hieronder) |

Interne lagen, indicatoren en waarden (`toegang` intern) zijn op al deze routes alleen zichtbaar met de rol `lezer` of `beheerder`; zie [Toegang per laag en bron](#toegang-per-laag-en-bron-openbaar-of-intern).
| `/api/admin/auth/login`, `/logout`, `/me`, `/config`, `/oidc/login`, `/oidc/callback` | Inloggen (lokaal en via Keycloak) en sessiestatus |
| `/health`, `/api`, `/docs`, `/openapi.json` | Status en API-documentatie |

**Principe:** rapporten hebben dezelfde rechten als een anonieme bezoeker van de kaartapplicatie (besluit #65). Een rapport toont dus niet meer dan de publieke app: geen beheervelden (notities, wie iets beoordeelde of goedkeurde), geen inactieve indicatoren, geen logs of configuratie. De technische details van AI-teksten (`debug_info`: systeemprompts en model) krijgt alleen een ingelogde beheerder.

**Let op, AI-teksten:** `/api/report/narrative/*`, `/api/report/benchmark/narrative` en `/api/chat` starten zonder inloggen een aanroep naar het taalmodel. Rapportteksten worden per gebied een uur gecachet, en per IP-adres zijn hoogstens `LLM_RATE_LIMIT` verzoeken per minuut toegestaan (standaard 60; daarboven 429). Gebruik je een externe (betaalde) LLM-aanbieder, zet de limiet dan lager of scherm deze routes af in de proxy ervoor.

**Grenzen (#203):** na 5 mislukte inlogpogingen per IP-adres en gebruikersnaam (of 20 per IP-adres) binnen 15 minuten geeft inloggen 429, en elke mislukte poging wacht 1 seconde. PostgREST geeft hoogstens 10.000 rijen per antwoord (`PGRST_DB_MAX_ROWS`). Een query mag duren: 10 seconden voor PostgREST (`web_anon`), 30 seconden voor pg_featureserv en 60 seconden voor de backend. Een interne fout geeft een generieke melding met een correlatie-id; de details staan in de log (`docker compose logs backend`, zoek op de id).

### PostgREST en pg_featureserv

PostgREST (`/api/data`) en pg_featureserv (`/api/geo`) verbinden niet als database-eigenaar, maar met eigen rollen (#57). `db-init` maakt ze aan en houdt ze bij (`db/migraties/R__api_rollen.sql`):

| Rol | Gebruikt door | Rechten |
|-----|---------------|---------|
| `authenticator` | PostgREST (verbinding) | `LOGIN`, `NOINHERIT`; mag alleen overschakelen naar `web_anon` |
| `web_anon` | PostgREST (anonieme verzoeken) | `NOLOGIN`; `USAGE` op schema `api`, `SELECT` op de views daarin, `EXECUTE` op `api.get_indicatoren_stats`. Geen schrijfrechten, geen rechten in `public` |
| `featureserv` | pg_featureserv | alleen-lezen op `public.vw_gebieden_features`, `public.omgevingsvisie_deelgebieden` en de functies in `postgisftw` |

PostgREST publiceert alleen schema `api`. Daarin staan alleen views en functies die de frontend en de beheeromgeving lezen: `gemeenten`, `gebiedstypes`, `gebieden` (zonder geometrie), `externe_kaartlagen`, `indicatoren` (zonder interne beheervelden), `vw_gebied_indicator_actueel`, `gebied_data` en `rpc/get_indicatoren_stats`. De views met `toegang` tonen interne rijen alleen als de forwardAuth `X-Omnitwin-Toegang: intern` zette (#254); PostgREST en pg_featureserv mogen daarom niet buiten Traefik om bereikbaar zijn (de standaard-compose publiceert geen poort voor ze). Applicatiedata zoals `users`, `sessions`, `api_keys`, `llm_config`, `system_prompts` en de logs is via `/api/data` niet bereikbaar, en schrijven kan anoniem niet. Een nieuw object publiceren: voeg een view of functie toe aan `db/migraties/R__api_rollen.sql` met de bijbehorende `GRANT` en draai `db-init` opnieuw (`docker compose up -d`).

**Wachtwoord:** `authenticator` en `featureserv` krijgen hetzelfde wachtwoord als `DATABASE_USER` (`DATABASE_PASSWORD`). Er is dus geen extra variabele in `.env`; `db-init` zet het wachtwoord bij elke start opnieuw. Wie de omgeving van de PostgREST- of pg_featureserv-container kan lezen, heeft daarmee ook het wachtwoord van de database-eigenaar. Een eigen wachtwoord per rol kan later, zonder de opzet te veranderen.

Kwetsbaarheden melden: zie [`SECURITY.md`](../../SECURITY.md).

### HTTPS aanzetten

HTTPS en HSTS zijn verplicht volgens de [Forum Standaardisatie](https://www.forumstandaardisatie.nl/open-standaarden/verplicht). Kies één manier:

**A. Achter de TLS-proxy van je organisatie (aanbevolen).** De proxy of WAF handelt het certificaat af en stuurt door naar `http://<host>:<OMNITWIN_HTTP_PORT>`. Laat de stack zoals hij is en zet `COOKIE_SECURE=true` (Traefik ziet alleen HTTP, dus `auto` herkent de HTTPS-verbinding niet). De proxy moet zelf HSTS sturen (`Strict-Transport-Security: max-age=31536000`) en HTTP doorsturen naar HTTPS; Traefik ziet alleen HTTP en zet die header dan niet. Zet ook `TRAEFIK_TRUSTED_IPS` op het adres van de proxy (bijv. `10.1.2.3/32`), zodat de logs en de rate limiting het adres van de bezoeker zien en niet dat van de proxy.

**B. Traefik zelf met Let's Encrypt.** Voor een server die direct bereikbaar is, met een DNS-naam en poort 80 en 443 open. Gebruik het voorbeeld [`deploy/traefik/tls.example.yml`](../../deploy/traefik/tls.example.yml). Zet in `.env`:

```bash
COMPOSE_FILE=docker-compose.yml:deploy/traefik/tls.example.yml   # Windows: ; in plaats van :
OMNITWIN_DOMAIN=omnitwin.example.nl
ACME_EMAIL=beheer@example.nl     # functioneel adres voor meldingen van Let's Encrypt
```

en draai `docker compose up -d`. HTTP gaat dan met een redirect naar HTTPS, en HSTS staat aan. `OMNITWIN_HTTP_PORT` moet hierbij `80` blijven. Een eigen certificaat in plaats van Let's Encrypt staat beschreven in de kop van het voorbeeldbestand.

### Security-headers

Traefik zet op **alle** routes (de app, `/api/data`, `/api/geo`, `/health`) deze headers, vastgelegd in [`deploy/traefik/dynamic.yml`](../../deploy/traefik/dynamic.yml) (middleware `security-headers`, per router):

| Header | Waarde |
|--------|--------|
| `Content-Security-Policy` | Alleen eigen bronnen (bibliotheken en lettertype zelf gehost, #117), plus api.pdok.nl en service.pdok.nl (achtergrondkaart). Geen framing (`frame-ancestors 'none'`), geen plugins (`object-src 'none'`). |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera, microfoon, locatie, betalen en USB uit |
| `Strict-Transport-Security` | `max-age=31536000`, alleen op HTTPS via Traefik (manier B) |

De CSP staat nog `'unsafe-inline'` toe: de frontend gebruikt inline scripts, `onclick=`-attributen en inline stijlen. Dat weghalen is een aparte klus in de frontend.

Keycloak (`/auth`, profiel `keycloak`) krijgt de middleware `keycloak-headers`: dezelfde headers, maar zonder CSP, `X-Frame-Options` en `Referrer-Policy`. Die zet Keycloak zelf (per realm: Realm settings > Security defenses), met `frame-ancestors 'self'` in plaats van `'none'`: de admin-console en de sessiecontrole gebruiken iframes op hetzelfde adres. Elke Traefik-router heeft een van beide middlewares; `tests/test_traefik_routers.py` controleert dat.

Voeg je een kaartlaag of bibliotheek toe die rechtstreeks een andere server aanroept, dan blokkeert de browser die. Neem de host dan op in `dynamic.yml` en draai `docker compose restart traefik`. Externe WFS-lagen lopen via de backend (`/api/externe-lagen/...`) en hebben dit niet nodig.

### security.txt

`/.well-known/security.txt` ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)) verwijst naar `SECURITY.md` in de GitHub-repository. Dat is het meldpunt voor fouten in de software. Beheer je een eigen installatie, vervang dan in [`static/.well-known/security.txt`](../../static/.well-known/security.txt) `Contact` en `Policy` door het meldpunt van je organisatie en voeg `Canonical: https://<host>/.well-known/security.txt` toe. Het veld `Expires` mag hooguit een jaar vooruit liggen; verleng het op tijd.

### Checklist vóór openstelling

- HTTPS aan (manier A of B), het inlogcookie met `Secure` (manier A: `COOKIE_SECURE=true`), en HSTS zichtbaar in de response-headers.
- `LLM_RATE_LIMIT` passend bij je LLM-aanbieder; bij meerdere backends of een externe aanbieder ook een limiet in de proxy op inloggen (`/api/admin/auth/login`) en de AI-routes (`/api/chat`, `/api/report/*narrative*`).
- Het domein heeft DNSSEC en is via IPv6 bereikbaar (ook verplichte standaarden). Dat regel je bij je DNS- en hostingbeheer, niet in de stack.
- `security.txt` verwijst naar het juiste meldpunt.
- `OMNITWIN_OMGEVING` staat op `productie` (of ontbreekt): geen demo-accounts met bekende wachtwoorden.
- Moet de data niet openbaar zijn: `VIEWER_TOEGANG=inloggen` (zie [Toegang tot de viewer](#toegang-tot-de-viewer-open-of-dicht)). Is alleen een deel intern: `dct:accessRights` `RESTRICTED` bij die datasets (zie [Toegang per laag en bron](#toegang-per-laag-en-bron-openbaar-of-intern)), en controleer zonder inloggen dat ze niet zichtbaar zijn.
- Er is een backup (database en uploads) en een geteste restore.
