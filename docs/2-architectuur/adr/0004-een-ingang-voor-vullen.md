# 0004. Eén ingang voor het vullen van D-OmniTwin (push, interne ETL, virtualisatie, federatie)

- Status: voorgesteld
- Datum: 2026-10-01
- Issue: #195 (0.3.0), #182 fase 4; bouwt voort op ADR 0002

## Context

Data komt op vier manieren in D-OmniTwin:

1. **Push:** een externe ETL bij de bronhouder levert gegevens aan. Bij SWF draaien de ETL's intern (Oracle-DWH → FME/Python) en pushen ze nu naar de huidige gebiedsmonitor met velden als indicator-UUID, gebiedscode, peildatum, waarde en n; waarden met n < 10 worden niet getoond (#195).
2. **Interne ETL:** een bron als dataproduct (ADR 0002) haalt open data op en laadt die.
3. **Virtualisatie:** een bron wordt bij de bron bevraagd, met een cache.
4. **Federatie:** een vraag gaat door naar een andere databron of een andere D-OmniTwin-installatie (#20, #32).

Nu is er voor geen van deze routes een ingang. Alle data wordt direct in de database geschreven door scripts die als database-eigenaar verbinden (`scripts/import_metingen.py`, `init_data/scripts/laad_usecase.py`, `ETL/`), elk met een eigen `INSERT … ON CONFLICT`. Het enige upload-endpoint (`POST /api/admin/externe-lagen/upload`) is voor kaartbestanden, niet voor indicatorwaarden. De enige machine-authenticatie is één gedeelde `X-Admin-Key` die volledige beheerrechten geeft. Herkomst (`etl_runs`, `data_lineage`, #20) bestaat alleen op papier. `gebied_data` heeft geen kolom voor n en twee tegenstrijdige unieke sleutels (één zonder scenario).

Eisen:
- de SWF-monitor in 0.3.0 kunnen vullen zoals nu, met inloggen via Keycloak (#195);
- privacy: kleine aantallen nooit publiceren;
- herkomst per waarde herleidbaar (AVG, IAMA, bronvermelding);
- geen aparte paden per route: één datamodel, één catalogus, één autorisatiemodel;
- zo min mogelijk eigen code, passend bij de stack (PostgreSQL, PostgREST, pg_featureserv, Keycloak, Traefik);
- aansluiten op NL-standaarden (API Design Rules, NL GOV OAuth, FSC, DCAT-AP-NL) en voorbereid op een dataspace (DSP).

## Besluit

**1. Eén datacontract: de waarneming.** Elke route levert of levert terug in dezelfde vorm: `gebied_code`, `gebiedstype` (optioneel), `indicator_uuid`, `jaar` óf `peildatum`, `scenario` (standaard `current`), `waarde`, `n`, `kwaliteit`, `opmerking`. Vastgelegd als Frictionless Table Schema. Het bron-contract (ODCS, ADR 0002) zegt per bron welke indicatoren en gebiedstypen mogen, de eenheid, `minimum_n` en de vervangmodus.

**2. Eén ingang per bron:** `POST /api/v1/bronnen/{bron}/leveringen`. Body: CSV (basis), een Data Package (zip met CSV/Parquet), Parquet of JSON. Antwoord `202` met een status-resource; `proef=true` valideert zonder te publiceren; `Idempotency-Key` en een inhoudshash voorkomen dubbele publicatie; fouten als Problem Details (RFC 9457), per regel op te vragen.

**3. De verwerking zit in PostgreSQL**, in schema `ingest`: staging via `COPY`, set-based validatie (contract, codes, bereik, dubbele sleutels, n-drempel) en publicatie in één transactie per plak (bron × indicator × jaar/peildatum × scenario). De FastAPI-router is dun: authenticatie, bestand naar staging, status. De ingang gebruikt een eigen databaserol met alleen `EXECUTE` op `ingest.*`.

**4. Privacy bij de ingang.** Waarden onder `minimum_n` worden niet gepubliceerd en na publicatie uit de staging verwijderd. Aggregaten over meerdere gebieden gebruiken alleen gepubliceerde waarden en worden zelf ook aan de drempel getoetst.

**5. Herkomst per plak.** `gebied_data` krijgt `levering_id`; `etl_runs` en `data_lineage` (#20) registreren per levering en plak de bron, de agent (Keycloak-client of ETL-job) en de aantallen. Geen lineage-rij per waarde.

**6. Autorisatie uit Keycloak (OIDC).** Machines: client credentials (bij voorkeur `private_key_jwt`), client-rol `bron:{bron}:leveren` op resource-client `d-omnitwin-api`; FastAPI valideert het token via de JWKS van de realm. Mensen: authorization code + PKCE via de backend (BFF, HttpOnly-cookie). `X-Admin-Key` is geen ingang voor data en wordt uitgefaseerd (#34).

**7. Alle routes gebruiken deze ingang of dit contract:**
- route 1 (push): de HTTP-ingang;
- route 2 (interne ETL): dezelfde functie in-process (`omnitwin.ingest.lever`) of dezelfde HTTP-call met een eigen client;
- route 3 (virtualisatie): verversen van een virtuele bron (DuckDB, `ogr_fdw`) is een levering; alleen viewer-lagen buiten berekeningen worden zonder kopie on-demand gecachet;
- route 4 (federatie): `GET /api/v1/waarden` geeft hetzelfde contract terug; catalogus in DCAT-AP-NL (later DSP); transport tussen organisaties via FSC (#33).

**8. API-indeling met versie** (NL GOV API Design Rules): FastAPI onder `/api/v1` (publiek lezen, `/api/v1/beheer`, `/api/v1/bronnen`), spec op `/api/v1/openapi.json` met `securitySchemes`, header `API-Version`; PostgREST op `/api/data`, OGC API Features op `/api/geo`; één documentatieportaal op `/api/docs`. Oude paden één release als alias met `Deprecation`-header.

## Alternatieven

- **Schrijven direct in de database laten (zoals nu).** Geen werk, maar een externe partij krijgt het eigenaarswachtwoord, elke loader valideert anders, en er is geen herkomst of n-drempel. Afgewezen.
- **PostgREST als schrijf-API** (schema `ingest`, JWT met rol-claim, RLS). Geen eigen HTTP-code, maar geen zip/Parquet, geen streaming van grote bestanden, geen asynchrone status, JWKS-rotatie handmatig, en drie à vier calls per levering. Blijft mogelijk als tweede ingang op dezelfde SQL-functies.
- **OGC API – Features Part 4 (Create/Replace/Update/Delete).** Nog draft (1.0.0-draft.2), niet geïmplementeerd in pg_featureserv of GeoServer, per feature in plaats van per jaargang. Niet nu; wel voor geo-objecten als het standaard en beschikbaar is.
- **OGC SensorThings API.** Bedoeld voor sensorwaarnemingen; te zwaar voor jaarcijfers. Kandidaat als bron (route 3) voor sensordata.
- **Kafka/Redpanda of een andere event-bus.** Voor jaarcijfers en periodieke leveringen onnodige infrastructuur bij een gemeente.
- **Airbyte / Singer / Meltano als ingang.** Lost de connectoren aan de bronkant op, niet het contract en de autorisatie aan onze kant. Een Singer/Meltano-target is later een dunne wrapper om deze ingang.
- **dbt in de kern.** Transformaties horen bij de bron of de bronhouder (ADR 0002, Gold leest alleen het contract).
- **Forward-auth in Traefik als enige autorisatie.** Traefik weet niet welke bron een client mag vullen. Wel bruikbaar voor componenten zonder eigen auth (pg_featureserv voor beperkte lagen).
- **Virtualisatie met Trino of Apache Drill.** Een cluster is te zwaar voor een gemeentelijke installatie; DuckDB in-process volstaat.
- **iSHARE voor federatie.** Afgewezen in #32 ten gunste van DSP (catalogus/contract) met FSC (transport, identiteit, logging).

## Gevolgen

- **Makkelijker:**
  - een externe ETL aansluiten zonder databasetoegang, met rechten per bron;
  - één plek voor validatie, n-drempel en herkomst, ongeacht de route;
  - leveringen proefdraaien, herhalen (idempotent) en terugvinden;
  - de catalogus en het contract hergebruiken voor federatie en het API-register (#128).
- **Moeilijker:**
  - een bron vullen vraagt vooraf een contract en een Keycloak-client;
  - Keycloak wordt een vaste afhankelijkheid voor machine-toegang;
  - bestaande paden verhuizen naar `/api/v1` (overgangstermijn).
- **Migraties:** `gebied_data` krijgt `n` en `levering_id`; de unieke sleutel zonder scenario verdwijnt; `ON DELETE CASCADE` naar `indicatoren` wordt `RESTRICT`; `etl_bronnen`, `etl_runs`, `data_lineage` en schema `ingest` komen erbij.
- **Uitvoering:** 0.3.0 levert route 1 en route 2 via dezelfde ingang voor de SWF-monitor (issuelijst in de RFC "D-OmniTwin vullen"). Catalogus-export, intrekken, gebiedsindelingen, PostgREST-JWT, virtualisatie en federatie volgen later.
- **Open:**
  - n-drempel per indicator of globaal, en de regel voor aggregaten;
  - adapter voor het bestaande SWF-pushformaat, of FME aanpassen;
  - welke Keycloak-realm (SWF-realm, Entra-koppeling loopt af in december);
  - rollen per bron of per bron én gemeente (#34).
