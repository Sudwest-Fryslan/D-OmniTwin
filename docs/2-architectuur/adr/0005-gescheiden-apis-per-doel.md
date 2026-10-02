# 0005. Gescheiden API's per doel volgens de NL GOV API Design Rules

- Status: voorgesteld
- Datum: 2026-10-02
- Issue: #205 (0.3.0); hangt samen met ADR 0004

## Context

D-OmniTwin heeft nu drie API's die los van elkaar staan: FastAPI (alle eigen routes, spec op `/openapi.json` en Swagger UI op `/docs`, allebei in de root), PostgREST op `/api/data` (Swagger 2.0) en pg_featureserv op `/api/geo` (OGC API Features). De FastAPI-spec mengt publieke leesroutes, beheer, AI en HTML-pagina's, heeft geen versie in het pad, geen `API-Version`-header en geen `securitySchemes`. Een afnemer kan niet zien welke routes voor hem bedoeld zijn, wat stabiel is en welke rechten nodig zijn.

Met de laad-API (ADR 0004) komt er een API bij met andere gebruikers (machines van bronhouders), andere autorisatie (rol per dataset) en andere eisen (grote bestanden, asynchroon). Op termijn moeten backend, viewer en beheer los deploybaar zijn. D-OmniTwin wil herbruikbaar zijn voor andere gemeenten en aansluiten op het API-register van developer.overheid.nl (#128).

## Besluit

1. **Eén API per doel**: `laden`, `catalogus`, `data`, `geo`, `analyse`, `chat`, `beheer` en een interne `viewer`-API. Indeling, gebruikers en migratie: [API-landschap](../api-landschap.md).
2. **Elke API heeft**: een eigen basispad `/api/<naam>/v<major>`; een eigen OpenAPI-specificatie op `<basispad>/openapi.json` (OAS 3.0.3, anoniem, CORS open, `info.contact`, `securitySchemes`); een eigen semver-versie in de header `API-Version`; een eigen wijzigingslog; eigen autorisatie via rollen in Keycloak.
3. **Standaarden:** waar een domeinstandaard bestaat, die (OGC API Features voor `geo`, DCAT-AP-NL voor `catalogus`, Frictionless/GeoPackage/DCAT voor `laden`). Daarnaast voor alle API's de NL GOV REST API Design Rules 2.1 met de modules Geospatial en Transport Security, Problem Details (RFC 9457) en het NL GOV OAuth-profiel.
4. **Specificatie eerst.** De bron van een spec is `docs/api/<naam>/openapi.yaml`. Een wijziging aan een API begint met een wijziging van die spec. Elke spec haalt 0 errors met de Spectral-ruleset van Logius; afwijkingen (waarschuwingen) staan met reden in de README van de API.
5. **Eén portaal op `/api`**: overzicht van alle API's, Swagger UI met een keuzelijst van alle specs en `/.well-known/api-catalog` (RFC 9727). `/docs` in de root verdwijnt.
6. **Traefik routeert per API** (één router per basispad), zodat een API later een eigen container kan krijgen zonder URL-wijziging. Oude paden worden één minor-release in Traefik herschreven naar de nieuwe, met `Deprecation`- en `Sunset`-headers.
7. **Volgorde:** eerst `laden` (nieuw) en het portaal, dan `beheer` (met Keycloak), dan `data`/`geo` (alleen routering), dan `analyse`/`chat`/`viewer`.

## Alternatieven

- **Eén API `/api/v1` met autorisatie per subpad** (het eerdere voorstel in ADR 0004 en de RFC). Minder basispaden, maar één spec en één versie voor alles: een breuk in de beheer-API geeft ook de publieke lees-API een nieuwe major, en de API's zijn niet los te deployen of te documenteren. Afgewezen.
- **Alles via PostgREST** (ook schrijven en beheer). Minste eigen code, maar geen bestandsuploads, geen asynchrone verwerking en een spec in Swagger 2.0. Blijft de keuze voor `data`.
- **Een API-gateway (Kong, Tyk, Gravitee) of een developer-portaal (Backstage).** Lost routering, rate-limits en documentatie op, maar is een extra component om te beheren bij elke gemeente. Traefik en een statisch portaal volstaan; een gemeente met een eigen gateway kan die ervoor zetten.
- **Engelse paden.** Internationaal gangbaarder, maar de ADR schrijft de taal van de doelgroep voor en de doelgroep is Nederlandse overheid. Domeintermen uit standaarden (`datasets`, `collections` in OGC) blijven zoals de standaard ze noemt.
- **GraphQL voor lezen.** Flexibel voor de frontend, maar geen overheidsstandaard, lastiger te cachen en te autoriseren per veld. Niet nu.

## Gevolgen

- **Makkelijker:** een afnemer ziet per doel wat stabiel is en welke rechten nodig zijn; API's krijgen onafhankelijk een nieuwe versie; een API kan naar een eigen container; registratie in het API-register; lint in de CI mogelijk.
- **Moeilijker:** meer specs om bij te houden; FastAPI genereert OpenAPI 3.1 terwijl de Logius-linter 3.0 eist, dus de spec wordt met de hand bijgehouden en een test controleert dat routes en spec overeenkomen; de frontend en het admin-panel moeten naar nieuwe paden.
- **Werk:** portaal en `/.well-known/api-catalog`; Traefik-routers en aliassen; per API een `docs/api/<naam>/`-map; een OAS 3.0-spec voor PostgREST; JWT-validatie in FastAPI (gedeeld door alle API's); lint-commando in AGENTS.md en later in de CI.
- **Open:** pg_featureserv met versie in het basispad en CRS-ondersteuning (Part 2) toetsen; **Besloten (02-10-2026):** `catalogus` is eerst een representatie (`Accept: application/ld+json`) van `laden/datasets`; een eigen API pas als er een tweede bron van metadata is.
