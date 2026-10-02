# Laad-API (`/api/laden/v1`)

Datasets registreren en leveringen laden in D-OmniTwin. **Status: in opbouw** (versie `1.0.0-concept`): gebouwd in 0.3.0 (#228), behalve de compatibiliteitspaden voor de SWF-monitor (stap 9 van #205). Zie [Implementatie](#implementatie-030). Specificatie: [openapi.yaml](openapi.yaml). Besluiten: [ADR 0004](../../2-architectuur/adr/0004-een-ingang-voor-vullen.md) (vullen via registratie en leveringen) en [ADR 0005](../../2-architectuur/adr/0005-gescheiden-apis-per-doel.md) (gescheiden API's per doel). Plaats in het geheel: [API-landschap](../../2-architectuur/api-landschap.md).

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
| <a id="gebiedstype-onbekend"></a>`gebiedstype-onbekend` | regel of 422 | gebiedstype (code of UUID) bestaat niet; bij een gebiedsindeling: `doel.gebiedstypeId` bestaat niet |
| <a id="versie-meerdere-leveringen"></a>`versie-meerdere-leveringen` | 409 | het bestand van een versie opvragen die uit meerdere leveringen bestaat (vervangbereik) |
| <a id="registratie-ongeldig"></a>`registratie-ongeldig` | 422 | de registratie voldoet niet aan `DatasetRegistratie` of het profiel |
| <a id="dataset-bestaat"></a>`dataset-bestaat` | 409 | registreren van een `id` die al bestaat (gebruik PUT of PATCH) |
| <a id="ongeldig-verzoek"></a>`ongeldig-verzoek` | 400 | parameter, JSON of `Content-Digest` klopt niet |
| <a id="niet-gevonden"></a>`niet-gevonden` | 404 | dataset, levering, versie of bestand bestaat niet (of is niet zichtbaar voor deze client) |
| <a id="te-groot"></a>`te-groot` | 413 | body boven de limiet |
| <a id="te-veel-verzoeken"></a>`te-veel-verzoeken` | 429 | rate-limit bereikt |
| <a id="serverfout"></a>`serverfout` | 500, of `mislukt` | technische fout; details alleen in de serverlog onder de correlatie-id |
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

## Implementatie (0.3.0)

Code: `src/omnitwin/routers/laden.py` (HTTP) en `src/omnitwin/laden/` (laadstraat). Database: schema `laden` (migratie V024), rol `laden_schrijver`.

- **Rechten.** Registreren en wijzigen: realm-rol `beheerder`. Leveren: `dataset:{datasetId}:laden` of `datasets:laden`. Lezen van een dataset, zijn leveringen en versies: `beheerder`, `datasets:laden` of `dataset:{datasetId}:laden`; een levering (`GET /leveringen/{id}`) mag daarnaast de client lezen die hem leverde, anders `404`. `GET /datasets` met token toont de datasets waarop de client rechten heeft. `/openapi.json`, `/profielen` en de catalogusweergave (`Accept: application/ld+json`, alleen PUBLIC-datasets zonder token) zijn anoniem.
- **Verwerking.** Op de achtergrond in een threadpool in de backend (geen extra infrastructuur); per dataset na elkaar (advisory lock), ook met meerdere backend-processen. Na een herstart pakt de backend leveringen op `ontvangen` weer op; een levering die langer dan een uur op `bezig` staat, wordt `mislukt`. Bij veel of grote leveringen: een aparte worker-container (vervolg).
- **Publiceren.** Staging, controles in SQL, publicatie, nieuwe versie en status in één transactie. Waarnemingen gaan per dataset naar `laden.waarnemingen`; `gebied_data` wordt voor de geraakte sleutels opnieuw opgebouwd. Leveren twee datasets een waarde voor dezelfde sleutel (gebied, indicator, jaar of peildatum, scenario), dan gaat de dataset uit `LADEN_VOORRANG` voor (standaard `swf-monitor-waarden`, aanname A6 van #222), anders de laatst gepubliceerde; de andere waarde blijft in `laden.waarnemingen` (`aantallen.nietZichtbaarDoorVoorrang`).
- **Gelijk bestand.** Een levering met dezelfde sha256 als een levering in de actieve versie wordt `gepubliceerd` zonder nieuwe versie (`aantallen.ongewijzigd`).
- **Indicator en gebiedstype.** Een indicator met relaties in `indicator_gebiedstype_relaties` mag alleen waarden hebben op die gebiedstypen; een indicator zonder relaties (bijv. de CBS-indicatoren) op elk gebiedstype (aanname).
- **Indicatorstatus.** Alleen `C`, `O` en `B`; een andere code (bijv. `A`) is `schema-ongeldig` (de use case `swf-definities` zet `A` om naar `O`, aanname A2).
- **Kaartlaag (pre-release).** Na validatie wordt de GeoPackage de lokale kaartlaag `data-upload/laden/<datasetId>.gpkg` (volume `uploads`) met één rij in `externe_kaartlagen` (bron `lokaal`), zoals een upload in het beheer; zichtbaar alleen bij `dct:accessRights` PUBLIC. De eigen tabel in schema `laag` met OGC API Features ([kaartlaag.md](profielen/kaartlaag.md)) volgt.
- **Bewaartermijn.** De ruwe bestanden staan in het volume `leveringen`. Na elke publicatie verwijdert de laadstraat wat buiten de termijn valt: altijd de laatste 10 versies per dataset, oudere tot 365 dagen, afgekeurde en alleen-gevalideerde leveringen 30 dagen (`LADEN_BEWAAR_*`). De registratie van de levering blijft.
- **Limieten.** Traefik: 200 MB per body, 10 leveringen (POST) per minuut per token (`LADEN_RATE_LIMIT`). Backend: `LADEN_MAX_MB` (JSON een tiende), `wacht=true` tot `LADEN_WACHT_SECONDEN`.
- **Niet gebouwd:** de compatibiliteitspaden (`/compat/swf-monitor/...`, stap 9), Data Package-resources in andere formaten dan CSV en GeoPackage.

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
| 1.0.0-concept | 2026-10-02 | `GET /datasets` ook als DCAT-catalogus (`Accept: application/ld+json`, schema `DcatCatalogus`); extra probleemtypen; implementatie (#228) |
