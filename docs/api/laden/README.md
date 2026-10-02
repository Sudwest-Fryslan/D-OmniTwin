# Laad-API (`/api/laden/v1`)

Datasets registreren en leveringen laden in D-OmniTwin. **Status: ontwerp** (versie `1.0.0-concept`), nog niet gebouwd. Specificatie: [openapi.yaml](openapi.yaml). Besluiten: [ADR 0004](../../2-architectuur/adr/0004-een-ingang-voor-vullen.md) (vullen via registratie en leveringen) en [ADR 0005](../../2-architectuur/adr/0005-gescheiden-apis-per-doel.md) (gescheiden API's per doel). Plaats in het geheel: [API-landschap](../../2-architectuur/api-landschap.md).

## In het kort

| Stap | Aanroep | Wie |
|---|---|---|
| 1. Registreren: wat is de dataset en hoe wordt hij geladen | `POST /datasets` met DCAT-AP-NL (JSON-LD) en een laadprofiel | beheerder (realm-rol `beheerder`) |
| 2. Rol toekennen | Keycloak: client-rol `dataset:{datasetId}:laden` op `omnitwin-api` aanmaken en toekennen aan de leverende client | beheerder |
| 3. Leveren: een volledige snapshot | `POST /datasets/{datasetId}/leveringen` met GeoPackage, Data Package-zip, CSV of JSON | ETL (`dataset:{datasetId}:laden`) |
| 4. Volgen | `GET /leveringen/{leveringId}` | ETL |

Een levering gaat door **ruw bewaren → valideren → staging → atomisch publiceren**. Elke geslaagde levering is een nieuwe **versie**; bij een fout blijft de vorige versie actief. Alleen modus `vervangen` in v1.

Profielen (contracten): [profielen/](profielen/README.md). Adapter voor de huidige SWF-push: [swf-monitor-v1](profielen/swf-monitor-v1.md).

## Voorbeelden

Token halen (client credentials; de URL staat in `/.well-known/openid-configuration` van de realm):

```bash
TOKEN=$(curl -s -X POST "https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token" \
  -d grant_type=client_credentials -d client_id="$CLIENT_ID" -d client_secret="$CLIENT_SECRET" \
  | jq -r .access_token)
API=https://omnitwin.example.nl/api/laden/v1
```

GeoPackage leveren (kaartlaag of gebiedsindeling), asynchroon:

```bash
curl -s -X POST "$API/datasets/hittekaart-gevoelstemperatuur/leveringen" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: hittekaart-gevoelstemperatuur-2026-09" \
  -H "Content-Type: application/geopackage+sqlite3" \
  --data-binary @gevoelstemperatuur.gpkg -i
# HTTP/1.1 202 Accepted
# Location: /api/laden/v1/leveringen/7c1d2c4e-...
```

Data Package-zip met CSV-waarnemingen en `dcat.jsonld` ([voorbeeld](voorbeelden/waarnemingen-datapackage/)), eerst alleen valideren, synchroon:

```bash
(cd voorbeelden/waarnemingen-datapackage && zip -q ../levering.zip datapackage.json waarnemingen.csv dcat.jsonld)
curl -s -X POST "$API/datasets/voorbeeld-waarnemingen/leveringen?alleenValideren=true&wacht=true" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/zip" \
  --data-binary @voorbeelden/levering.zip
```

Huidig SWF-waardenformaat ([voorbeeld](voorbeelden/swf-waarden.json)), via de compatibiliteitsingang:

```bash
curl -s -X POST "$API/compat/swf-monitor/monitor_api/indicator_waarde/inlezen" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary @voorbeelden/swf-waarden.json
```

Status volgen (FME: HttpCaller in een lus tot `status` niet meer `ontvangen` of `bezig` is, of direct `wacht=true` gebruiken):

```bash
curl -s "$API/leveringen/7c1d2c4e-..." -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'
```

Foutrapport: [voorbeelden/foutrapport.json](voorbeelden/foutrapport.json).

## Probleemtypen

Fouten zijn Problem Details (RFC 9457, `application/problem+json`). `code` is stabiel; `type` verwijst naar deze tabel. Fouten per regel hebben `resource`, `regel` en `veld`; de waarde uit de regel wordt niet herhaald.

| Code | HTTP / niveau | Betekenis |
|---|---|---|
| <a id="levering-afgekeurd"></a>`levering-afgekeurd` | 422 | de levering heeft fouten; niets gepubliceerd, lijst in `fouten` |
| <a id="formaat-ongeldig"></a>`formaat-ongeldig` | 422 | zip, Data Package, GeoPackage of JSON is niet te lezen |
| <a id="mediatype-past-niet"></a>`mediatype-past-niet` | 415 | mediatype niet toegestaan voor het profiel |
| <a id="schema-ongeldig"></a>`schema-ongeldig` | regel | kolom ontbreekt, verkeerd type of buiten de constraints |
| <a id="gebied-onbekend"></a>`gebied-onbekend` | regel | gebiedscode bestaat niet (of niet in het opgegeven gebiedstype) |
| <a id="indicator-onbekend"></a>`indicator-onbekend` | regel | indicator bestaat niet of is niet gekoppeld aan het gebiedstype |
| <a id="jaar-ongeldig"></a>`jaar-ongeldig` | regel | jaar en peildatum allebei of geen van beide, of buiten bereik |
| <a id="dubbele-sleutel"></a>`dubbele-sleutel` | regel | twee regels met dezelfde sleutel |
| <a id="waarde-buiten-bereik"></a>`waarde-buiten-bereik` | regel | buiten `min_waarde`/`max_waarde` van de indicator |
| <a id="n-ontbreekt"></a>`n-ontbreekt` | regel | `n` leeg terwijl de dataset dat niet toestaat |
| <a id="n-onder-drempel"></a>`n-onder-drempel` | regel (alleen bij `bijNOnderDrempel: afkeuren`) | n onder de drempel; standaard wordt zo'n waarde stil onderdrukt en geteld |
| <a id="crs-niet-ondersteund"></a>`crs-niet-ondersteund` | 422 | GeoPackage niet in EPSG:28992 of EPSG:4326 |
| <a id="geometrie-ongeldig"></a>`geometrie-ongeldig` | regel | lege, ongeldige of verkeerd getypeerde geometrie |
| <a id="aantal-niet-plausibel"></a>`aantal-niet-plausibel` | 422 | minder regels dan `plausibiliteit` toestaat |
| <a id="relatie-in-gebruik"></a>`relatie-in-gebruik` | regel | definities: relatie of indicator vervalt terwijl er nog waarden aan hangen |
| <a id="idempotency-key-hergebruikt"></a>`idempotency-key-hergebruikt` | 422 | dezelfde `Idempotency-Key` met andere inhoud |
| <a id="levering-loopt"></a>`levering-loopt` | 409 | levering met dezelfde `Idempotency-Key` is nog in behandeling |
| <a id="profiel-vast"></a>`profiel-vast` | 409 | profiel of sleutel wijzigen na de eerste publicatie |
| <a id="niet-geauthenticeerd"></a>`niet-geauthenticeerd` | 401 | geen, verlopen of ongeldig token (handtekening, `iss`, `aud`, algoritme); met `WWW-Authenticate: Bearer` |
| <a id="geen-toegang"></a>`geen-toegang` | 403 | token geldig, maar zonder een van de benodigde rollen |
| <a id="oidc-niet-geconfigureerd"></a>`oidc-niet-geconfigureerd` | 503 | `OIDC_ISSUER` is niet ingesteld in deze installatie |
| <a id="oidc-niet-bereikbaar"></a>`oidc-niet-bereikbaar` | 503 | de sleutels (JWKS) van de identity provider zijn niet op te halen |

## Limieten en beveiliging

- Body maximaal 200 MB (JSON 20 MB), 10 leveringen per minuut per client (Traefik `buffering` en `rateLimit`, instelbaar per installatie). Het bestand wordt naar schijf gestreamd, niet in het geheugen gelezen.
- Alleen HTTPS buiten de container (NL GOV ADR, module Transport Security); TLS en HSTS bij Traefik of de proxy van de organisatie.
- Geen gevoelige gegevens in de URI: identificatie en rechten in het token, inhoud in de body.
- Ruwe leveringen staan op een eigen volume, niet in de container; bewaartermijn instelbaar (standaard: altijd de laatste 10 versies per dataset, oudere versies tot 1 jaar, afgekeurde leveringen 30 dagen).
- Het token heeft `aud` = `omnitwin-api`; FastAPI controleert handtekening (JWKS), `iss`, `aud`, `exp` en de rol per dataset.

## Linten

```bash
# Logius-ruleset (NL GOV API Design Rules 2.1); 0 errors vereist
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/w" -w /w stoplight/spectral:6 lint -r docs/api/.spectral.yaml docs/api/laden/openapi.yaml
# of zonder Docker
npx -y @stoplight/spectral-cli@6 lint -r docs/api/.spectral.yaml docs/api/laden/openapi.yaml
# OpenAPI-validatie, inclusief voorbeelden tegen de schema's
npx -y @redocly/cli@1 lint --extends minimal docs/api/laden/openapi.yaml
```

Bewust niet gehaald: `paths-kebab-case` (waarschuwing) op de vijf paden onder `/compat/swf-monitor/`. Die spiegelen de paden van de huidige SWF-monitor letterlijk (`monitor_api`, `indicator_waarde`), zodat een FME-workspace alleen de basis-URL hoeft te wijzigen. Ze vervallen in v2.

## Wijzigingen

| Versie | Datum | Wijziging |
|---|---|---|
| 1.0.0-concept | 2026-10-02 | eerste ontwerp (#205) |
