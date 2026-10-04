# 0009. Viewer optioneel achter Keycloak-login, data-API's via Traefik forwardAuth

- Status: voorgesteld
- Datum: 2026-10-03
- Issue: https://github.com/TLaan/D-OmniTwin/issues/266
- Raakt: ADR 0008 (inloggen via Keycloak, backend als BFF), ADR 0005 (API's per doel), https://github.com/TLaan/D-OmniTwin/issues/254 (rechten per laag), https://github.com/TLaan/D-OmniTwin/issues/65 (wie mag wat)

## Context

De viewer (`/`) en de data-API's zijn openbaar. Sommige installaties willen alles achter een login, zoals de huidige SWF-monitor. De data komt niet alleen via FastAPI: de viewer haalt ook rechtstreeks bij PostgREST (`/api/data`) en pg_featureserv (`/api/geo`), die geen sessies kennen. Alleen de pagina dichtzetten is dus niet genoeg.

## Besluit

**1. Eén schakelaar `VIEWER_TOEGANG=open|inloggen`, standaard `open`.** Bij `inloggen` heeft alleen een sessie (of bearer-token, of `X-Admin-Key`) met realm-rol `lezer` of `beheerder` toegang tot de pagina en alle data-API's. Een lokale beheerder telt als `beheerder`. Een onbekende waarde telt als `inloggen` (dicht bij twijfel).

**2. Inloggen via dezelfde BFF als het beheerscherm (ADR 0008).** Zonder sessie stuurt `/` door naar `/api/admin/auth/oidc/login?terug=/`; na Keycloak komt de gebruiker terug op de kaart. Ingelogd zonder rol: pagina "Geen toegang" (403) met uitloggen, geen redirect-lus. Een API-verzoek zonder sessie krijgt `401` (Problem Details), zonder rol `403`. Uitloggen met `?terug=/` brengt je via Keycloak terug naar de kaart.

**3. Waar het gecontroleerd wordt.**

- Alles via de backend: een middleware in FastAPI (`omnitwin/viewer_toegang.py`).
- `/api/data` en `/api/geo`: Traefik forwardAuth (`viewer-toegang@file` in `deploy/traefik/dynamic.yml`) naar `GET /api/viewer/toegang` van de backend, met dezelfde beslisregel. De middleware staat altijd op die routers, vóór het strippen van prefix en `Authorization`; bij `open` antwoordt de backend direct `204`. Zo is er één schakelaar (in de backend) en hoeven compose-labels niet per modus te verschillen.

**4. Uitzonderingen.** Altijd open: `/health`, de inlogroutes (`/api/admin/auth/*`), de SPA van de beheeromgeving (de beheer-API's controleren zelf), de laad-API en `/api/oidc/ik` (eigen tokens), `/api/organisatie` (naam en thema voor de inlogpagina), `/static/*` (code, stijl, afbeeldingen; geen data) en `/.well-known/`. Keycloak (`/auth`) heeft een eigen router.

**5. In de kop van de viewer** staan, als Keycloak aan staat (ook bij `open`), de knop Inloggen of de gebruikersnaam met Uitloggen. De server rendert dat; de browser krijgt geen token.

## Alternatieven

- **Alleen FastAPI-dependencies.** Dekt PostgREST en pg_featureserv niet.
- **PostgREST en pg_featureserv zelf tokens laten controleren** (JWT-rol in PostgREST). pg_featureserv kan dat niet, en de browser heeft geen token (BFF). Afgewezen.
- **forwardAuth alleen bij `inloggen`** via een compose-variabele in het label (`viewer-${VIEWER_TOEGANG}@file`). Geen extra hop bij `open`, maar twee plekken die het eens moeten zijn (labels en backend); een tikfout of alleen de backend herstarten geeft een stille afwijking. Afgewezen; de extra interne aanroep per data-verzoek is klein.
- **oauth2-proxy voor de hele site.** Extra container en een tweede sessie naast die van de BFF. Mogelijk later.

## Gevolgen

- Bij `open` kost elk verzoek naar `/api/data` en `/api/geo` één interne aanroep naar de backend (zonder database). Staat de backend niet, dan werken die API's ook niet: dicht bij twijfel.
- Bij `inloggen` doet elk verzoek een sessie-opzoeking in de database (`oidc_sessies` of `sessions`).
- Rechten per laag (alleen `lezer` ziet niet-openbare lagen) vallen hier buiten; die staan in [ADR 0010](0010-toegang-per-laag-en-bron.md) (https://github.com/TLaan/D-OmniTwin/issues/254). Het forwardAuth-antwoord zet daarvoor ook de header `X-Omnitwin-Toegang`.
