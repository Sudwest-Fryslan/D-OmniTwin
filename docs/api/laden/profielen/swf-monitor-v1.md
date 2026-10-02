# Adapter `swf-monitor-v1`

Vertaalt het push-formaat van de huidige SWF-gebiedsmonitor naar de profielen `definities` en `waarnemingen`. Doel: de bestaande FME-workspaces kunnen naar D-OmniTwin leveren door alleen de basis-URL en de client (id en secret) te wijzigen. Daarna kan SWF in eigen tempo overstappen op het gewone leveringsformaat.

## De huidige stroom (samengevat)

De huidige monitor heeft per resource een laad- en een leesvariant:

| Resource | Laden | Lezen (back-up, voortgang) |
|---|---|---|
| definities (indicatoren, gebiedstypen, relaties; altijd de volledige set) | `POST /monitor_api/indicator/setup/inlezen` | `GET /monitor_api/indicator/setup` |
| waarden (één indicator × gebiedstype per aanroep) | `POST /monitor_api/indicator_waarde/inlezen` | `GET /monitor_api/indicator_waarde`, `GET /monitor_api/indicator_waarde/{indicator_id}` |

Token: standaard Keycloak OIDC-tokenendpoint, grant `client_credentials`, `client_secret` in de form-body. Eerst de definities, dan de waarden. Geen idempotentiesleutel, geen controle op de response, geen `n` in de waarden.

## De compatibiliteitsingang

D-OmniTwin spiegelt deze paden onder de laad-API:

```
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup/inlezen      POST
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup              GET
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen     POST
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde             GET
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/{id}        GET
```

Het deel na `compat/swf-monitor` is gelijk aan het huidige pad. Een FME-workspace vervangt dus alleen het begin van de URL.

| Aanroep | Wordt intern | Dataset | Vervangbereik |
|---|---|---|---|
| `POST …/indicator/setup/inlezen` | levering `vervangen`, `wacht=true` | `swf-monitor-definities` (profiel `definities`) | de hele set |
| `POST …/indicator_waarde/inlezen` | levering `vervangen`, `wacht=true` | `swf-monitor-waarden` (profiel `waarnemingen`) | de combinaties indicator × gebiedstype in de body |
| `GET …/indicator/setup` | export van de actuele versie in het SWF-formaat | `swf-monitor-definities` | – |
| `GET …/indicator_waarde[/{id}]` | export van de gepubliceerde waarden: `indicator_id`, `gebiedstype_id`, `gebieds_id`, `jaar`, `waarde` | `swf-monitor-waarden` | – |

**Response.** `200` met `status`, `leveringId`, `versie` en `aantallen` als de levering binnen 120 s gepubliceerd is (met `?alleenValideren=true`: `gevalideerd`, niets gepubliceerd). `422` (Problem Details met fouten per regel) als hij is afgekeurd: de HttpCaller zet dat op `<Rejected>` en de run stopt, zoals nu bij een HTTP-fout. `202` als de time-out verstrijkt; de levering loopt dan door en is te volgen via `Location`. Met de huidige omvang (gemiddeld ±760, maximaal ±5.900 regels per aanroep) komt dat niet voor. `400` als de body geen JSON in het SWF-formaat is, `404` als de dataset niet geregistreerd is met deze adapter. De body is altijd JSON, ook als FME geen `Content-Type` meestuurt.

**Rate-limit.** Een FME-run doet ±57 aanroepen achter elkaar, zonder retry. De compatibiliteitsingang heeft daarom een eigen limiet: `LADEN_COMPAT_RATE_LIMIT` per minuut per token (standaard 120), los van de 10 van de gewone leveringen.

**Herhalen is veilig.** Dezelfde body nog een keer sturen geeft geen nieuwe versie (sha256). Wie retry in de HttpCaller aanzet, kan ook een header `Idempotency-Key` meesturen.

**Back-up.** De `GET`-varianten geven terug wat D-OmniTwin heeft gepubliceerd: de definities uit de set die de dataset het laatst publiceerde (met de actuele velden; status `A` die als `O` is geleverd, komt terug als `O`), de waarden met `gebieds_id` zonder de `code_prefix` (welstand `WS728` → `728`) en `jaar` (bij een peildatum het jaar daarvan). Het letterlijk geleverde bestand is daarnaast op te halen via `GET /api/laden/v1/datasets/swf-monitor-definities/versies/actueel/bestand`.

## Wat SWF in FME wijzigt

Stap voor stap, met testen via `alleenValideren`: [FME omzetten naar D-OmniTwin](../fme-omzetten.md).

| Parameter | Wijziging |
|---|---|
| tokenendpoint (`BEARER_AUTH_URL`) | het tokenendpoint van de D-OmniTwin-realm |
| credentials (`BEARER_CREDENTIALS`) | client-id en secret van de nieuwe machineclient in die realm. Het secret in een versleutelde FME Flow-parameter of webconnectie, niet als standaardwaarde in de workspace. `scope=offline_access` kan weg; laten staan werkt als de beheerder die scope als optionele clientscope toewijst |
| URL waarden (`KOMPAS_ENDPOINT_URL`) | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen` |
| URL definities (nu vast in de HttpCaller) | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup/inlezen` |

Keycloak-inrichting: de machineclient krijgt de client-rollen `dataset:swf-monitor-definities:laden` en `dataset:swf-monitor-waarden:laden` op `omnitwin-api` (realm `omnitwin`); `omnitwin-api` staat via de audience-mapper van de realm in `aud`. Opzet als de voorbeeldclient `etl-voorbeeld`. Clientauthenticatie `client_secret_post` (wat FME nu doet) of `client_secret_basic`; `private_key_jwt` wordt de voorkeur zodra Keycloak en de workspace dat ondersteunen.

## Mapping waarden → `waarnemingen`

| SWF-veld | Waarneming | Regel |
|---|---|---|
| `indicator_id` | `indicator_uuid` | moet bestaan en gekoppeld zijn aan het gebiedstype |
| `gebiedstype_id` | `gebiedstype` (UUID) | moet bestaan |
| `gebieds_id` | `gebied_code` | met de `code_prefix` van het gebiedstype als die is gezet (welstand-id `728` → `WS728`); het gebied moet bestaan en van dat type zijn |
| `waarde` | `waarde` | |
| `begingeldigheid` | `jaar` of `peildatum` | `JJJJ-01-01` → `jaar = JJJJ`; een andere datum → `peildatum`. Jaar `0` of een ongeldige datum → fout `jaar-ongeldig` |
| `eindgeldigheid` | – | genegeerd; als hij gevuld is, een waarschuwing in de status |
| `n` (nieuw, optioneel) | `n` | gevuld: gewone n-drempel. Ontbreekt: `n` leeg en vlag **`bron-onderdrukt`** (de dataset staat dat toe met `bijOntbrekendeN: bron-onderdrukt`); de bron verklaart waarden met n < 10 zelf weg te laten |
| – | `scenario` | `current` |
| – | `bron` | leeg; de bronvermelding komt van de dataset |

## Mapping definities → `definities`

| SWF | D-OmniTwin | Regel |
|---|---|---|
| `indicatoren[].id`, `naam`, `omschrijving` | `indicatoren.uuid`, `naam`, `omschrijving` | upsert op `uuid` |
| `indicatoren[].status` | `status` | alleen bekende codes; onbekende codes (bijv. `A`) afgekeurd tot de betekenis is vastgelegd |
| `indicatoren[].begingeldigheid`/`eindgeldigheid` (`JJJJ-MM-DD HH:MM`) | `begingeldigheid`/`eindgeldigheid` | geldigheid van de definitie, los van de peildatum van waarden |
| indicator niet meer in de set | – | `eindgeldigheid` = moment van publicatie; niet verwijderd (waarden blijven herleidbaar) |
| `gebiedstypen[].id`, `naam` | `gebiedstypes.id`, `naam` | upsert op `id` |
| `gebiedstypen[].actief` | `gebiedstypes.actief` (nieuw) | |
| `gebiedstypen[].wfs`, `typenames`, `sleutel`, `label` | `gebiedstypes.metadata` (nieuw, jsonb) | bewaard als herkomst van de indeling. De geometrie komt via een dataset met profiel `gebiedsindeling`, niet live uit de WFS |
| `relaties[]` | `indicator_gebiedstype_relaties` | volledige set: ontbrekende relaties vervallen, tenzij er nog waarden aan hangen (dan fout `relatie-in-gebruik`) |

Velden die D-OmniTwin wel heeft en de push niet (eenheid, richting, bron per indicator) blijven zoals ze zijn; aanvullen via de beheer-UI of door SWF later in het gewone `definities`-profiel te leveren.

## Overstap

1. **Nu:** compatibiliteitsingang; FME wijzigt URL en client. Eerste vulling: de bestaande dump als levering(en) via dezelfde adapter.
2. **Daarna:** één run per bron in plaats van ±57: alle waarden als Data Package-zip (CSV, met `n` als de datamart die heeft) op `POST /api/laden/v1/datasets/swf-monitor-waarden/leveringen`, met `wacht=true`.
3. **Laad-API v2:** de compatibiliteitsingang vervalt, na aankondiging met `Deprecation`- en `Sunset`-headers.
