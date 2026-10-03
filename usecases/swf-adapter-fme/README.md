# TC-07-009 — SWF-adapter: dezelfde FME-push naar D-OmniTwin

**Status:** actief (acceptatietest groen tegen een verse stack, 02-10-2026; #237)
**Versie:** 0.1.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-adapter-fme`

## Vraag

- **Gebruiker:** data-engineer DWH (SWF)
- **Vraag:** "Kan SWF de bestaande FME-workspaces laten leveren aan D-OmniTwin door alleen de basis-URL en de client te wijzigen, en is een herhaalde push veilig?"
- **Rechten:** `dataset:swf-monitor-definities:laden`, `dataset:swf-monitor-waarden:laden`

De bestaande FME-workspaces leveren aan D-OmniTwin door alleen het tokenendpoint, de client en de basis-URL te wijzigen (adapter [`swf-monitor-v1`](../../docs/api/laden/profielen/swf-monitor-v1.md)). Deze use case maakt dezelfde bodies als FME nu stuurt: één definities-JSON (drie arrays) en één JSON-array per indicator × gebiedstype (57 bestanden), en post ze op de compatibiliteitsingang.

| In FME | Wordt |
|---|---|
| `BEARER_AUTH_URL` | tokenendpoint van realm `omnitwin` (`/auth/realms/omnitwin/protocol/openid-connect/token`) |
| `BEARER_CREDENTIALS` | `client_id=etl-swf&client_secret=…&grant_type=client_credentials` (secret in een versleutelde FME Flow-parameter) |
| `KOMPAS_ENDPOINT_URL` | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen` |
| URL definities (vast in de HttpCaller) | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup/inlezen` |

Keycloak: machineclient `etl-swf` (alleen client credentials) met de client-rollen `dataset:swf-monitor-definities:laden` en `dataset:swf-monitor-waarden:laden` op `omnitwin-api`, en de audience-mapper zoals bij `etl-voorbeeld` ([installatie](../../docs/9-beheer/installatie.md)). Handleiding voor de workspaces: [FME omzetten naar D-OmniTwin](../../docs/api/laden/fme-omzetten.md).

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): een vergelijking van wat de monitor nu teruggeeft (GET) met wat D-OmniTwin teruggeeft.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-monitor-definities`](datasets/swf-monitor-definities.json) | compat | definities | swf-json | export van de huidige monitor ($SWF_DUMP_DIR), in het pushformaat | open | onbekend (navragen) | `dataset:swf-monitor-definities:laden` |
| [`swf-monitor-waarden`](datasets/swf-monitor-waarden.json) | compat | waarnemingen | swf-json | export van de huidige monitor ($SWF_DUMP_DIR), in het pushformaat | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-monitor-waarden:laden` |

Verwacht:

- `swf-monitor-definities`: aanroepen 1; http 200
- `swf-monitor-waarden`: aanroepen 57; regels 43097; http 200 per aanroep; 422 (gebied-onbekend) voor de 9 aanroepen op welstandsgebieden en buurten bebouwde komgrens zolang die gebiedsindelingen ontbreken; gepubliceerd 33041

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-adapter-fme` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-monitor-definities | definities.json: 228/11/263 | geldig (SwfDefinities) |
| variant ruw | status A ongewijzigd | ongeldig: onbekende status {'A': 10} (zoals bedoeld) |
| swf-monitor-waarden | 57 bestanden, 43.097 waarden (152 jaar 0 en 4 onbekende buurt weggelaten) | alle geldig (SwfWaarde) |

### Tegen de laad-API (FME-flow nagebootst)

Verse stack met Keycloak, 02-10-2026, machineclient met alleen de twee datasetrollen, token via `client_secret_post` zoals FME. Eerst `cbs-gebiedsindelingen` en `swf-definities` geïnstalleerd; welstandsgebieden en buurten bebouwde komgrens niet (`SWF_GEO_DIR` ontbreekt). Alleen aantallen.

| Run | Definities (1 POST) | Waarden (57 POST's) |
|---|---|---|
| 1 | 200, gepubliceerd | 48× 200 (33.041 waarden gepubliceerd), 9× 422 `gebied-onbekend` (7 welstand, 2 buurten bebouwde komgrens), ±31 s |
| 2 (zelfde bodies) | 200, zelfde versie, `ongewijzigd` | 48× 200 `ongewijzigd`, zelfde versie; 9× 422 |

Terug (GET): definities 228/11/263, waarden 33.041 (precies de geleverde set op CBS-buurten), één indicator 154, onbekende indicator 404. Client zonder de datasetrol: 403; zonder token: 401.

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-adapter-fme --uit /tmp/swf-adapter-fme
   ```
2. Token halen (client credentials; tokenendpoint uit `/.well-known/openid-configuration` van realm `omnitwin`):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   API=https://omnitwin.example.nl/api/laden/v1
   ```
3. Registreren (eenmalig, realm-rol `beheerder`; de uitvoerder stuurt alleen `id`, `bronId`, `beschrijving` en `laadprofiel`):
   ```bash
   jq '{id, bronId, beschrijving, laadprofiel}' datasets/swf-monitor-definities.json | \
     curl -s -X POST "$API/datasets" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
   ```
   Daarna in Keycloak de client-rol `dataset:swf-monitor-definities:laden` op `omnitwin-api` aanmaken en toekennen aan de machineclient `etl-swf`.
4. Leveren (de route van FME):
   ```bash
   curl -s -X POST "$API/compat/swf-monitor/monitor_api/indicator/setup/inlezen" -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" --data-binary @/tmp/swf-adapter-fme/swf-monitor-definities/definities.json
   for f in /tmp/swf-adapter-fme/swf-monitor-waarden/waarden/*.json; do
     curl -s -o /dev/null -w "%{http_code} $f\n" -X POST "$API/compat/swf-monitor/monitor_api/indicator_waarde/inlezen" \
       -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @"$f"
   done
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-monitor-definities`, resource `indicatoren` | gelijk 228 |
| 2 | aantal | `swf-monitor-waarden`, resource `waarden` — geleverd in 57 aanroepen: 43.253 − 152 (jaar 0) − 4 (onbekende buurten) | gelijk 43097 |
| 3 | afkeuring | `swf-monitor-definities`, variant `ruw` — de huidige push met status A: 422, FME zet hem op Rejected; niets gepubliceerd | 422, fout `schema-ongeldig`, niets gepubliceerd |
| 4 | afkeuring | `swf-monitor-waarden`, variant `met-fouten` | 422, fout `jaar-ongeldig`, niets gepubliceerd |
| 5 | idempotent | `swf-monitor-definities` twee keer leveren — dezelfde body nog een keer: geen nieuwe versie (sha256) | zelfde versie, geen tweede publicatie |
| 6 | idempotent | `swf-monitor-waarden` twee keer leveren | zelfde versie, geen tweede publicatie |
| 7 | api | `GET /api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup` (met token) — back-up terug in het SWF-formaat (GET), met 228 indicatoren | HTTP 200 |
| 8 | api | `GET /api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c` (met token) — waarden van één indicator terug | HTTP 200, ≥ 1 resultaten |
| 9 | api | `GET /api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde` (met token) — gepubliceerd en terug in het SWF-formaat: minstens de 33.041 waarden op CBS-buurten; 43.097 als ook de welstandsgebieden en buurten bebouwde komgrens er zijn (swf-gebiedsindelingen) | HTTP 200, ≥ 33041 resultaten |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-adapter-fme`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Status A: de push zoals hij nu is, wordt afgekeurd (profiel definities kent A niet). SWF zet A om in de SQL, of D-OmniTwin legt de betekenis van A vast.
- Jaar 0 en de 2 onbekende buurtcodes moeten in de DWH weg; anders wordt die ene aanroep (indicator × gebiedstype) afgekeurd en blijft de vorige versie van die combinatie staan.
- Welstandsgebieden (7 aanroepen, 7.686 waarden) en buurten bebouwde komgrens (2 aanroepen, 2.370 waarden): 422 gebied-onbekend tot de gebiedsindelingen er zijn (use case swf-gebiedsindelingen, SWF_GEO_DIR). Dan komt swf-gebiedsindelingen in afhankelijk_van en geeft controle 9 43.097.
- De response gaat van 'niets' naar JSON met status, leveringId en versie; FME hoeft alleen de HTTP-status te controleren.
- Tokenendpoint, client-id en secret: per installatie, nooit als standaardwaarde in de workspace (analyse: het huidige secret staat in platte tekst en moet geroteerd worden).
- Rate-limit: de compatibiliteitsingang heeft een eigen limiet (LADEN_COMPAT_RATE_LIMIT, standaard 120 per minuut per token); met de gewone 10 per minuut zou de 11e aanroep van een FME-run een 429 krijgen en de run stoppen (FME heeft geen retry aan).
