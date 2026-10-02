# FME omzetten naar D-OmniTwin

Handleiding voor de data-engineer die de bestaande FME-workspaces van de SWF-gebiedsmonitor laat leveren aan D-OmniTwin. De workspaces blijven gelijk; per workspace wijzigen drie velden. D-OmniTwin vangt de aanroepen op met de compatibiliteitsingang (adapter [`swf-monitor-v1`](profielen/swf-monitor-v1.md)).

In deze tekst staat `<installatie>` voor de hostnaam van de D-OmniTwin-installatie. Geheimen horen nooit in de workspace zelf.

## 1. Client aanvragen

Vraag de beheerder van de installatie om een **machineclient** in Keycloak (realm `omnitwin`) met:

- grant `client_credentials` (geen andere flows);
- de client-rollen `dataset:swf-monitor-definities:laden` en `dataset:swf-monitor-waarden:laden` op `omnitwin-api`.

De beheerder maakt hem met `deploy/keycloak/machineclient.sh` (zie [installatie](../../9-beheer/installatie.md)) en geeft je de client-id en het secret via een veilig kanaal. De beheerder registreert ook de twee datasets `swf-monitor-definities` en `swf-monitor-waarden` (use case [`swf-adapter-fme`](../../../usecases/swf-adapter-fme/README.md)); zonder registratie geeft de ingang `404`.

## 2. Drie velden per workspace wijzigen

| Veld | Workspace | Was | Wordt |
|---|---|---|---|
| tokenendpoint (`BEARER_AUTH_URL`) | beide | tokenendpoint van de monitor | `https://<installatie>/auth/realms/omnitwin/protocol/openid-connect/token` |
| credentials (`BEARER_CREDENTIALS`) | beide | client van de monitor | `client_id=<client-id>&client_secret=<secret>&grant_type=client_credentials` |
| URL waarden (`KOMPAS_ENDPOINT_URL`) | waarden | `…/monitor_api/indicator_waarde/inlezen` | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen` |
| URL definities (vast in de HttpCaller) | definities | `…/monitor_api/indicator/setup/inlezen` | `https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup/inlezen` |

- Het secret in een **versleutelde FME Flow-parameter** of een webconnectie, nooit als standaardwaarde in de workspace. Het oude secret staat in platte tekst in de workspaces: laat het roteren.
- `scope=offline_access` mag weg. Laten staan werkt alleen als de beheerder die scope als optionele clientscope toewijst.
- Het tokenendpoint staat ook in `https://<installatie>/auth/realms/omnitwin/.well-known/openid-configuration`. Een token is 5 minuten geldig; FME haalt er per run een.
- De rest blijft gelijk: dezelfde bodies, `Content-Type: application/json`, `Authorization: Bearer …`, eerst de definities, dan de waarden.

## 3. Testen zonder te publiceren

Zet `?alleenValideren=true` achter de URL. D-OmniTwin controleert de body volledig (formaat, gebieden, indicatoren, jaren), maar publiceert niets:

```
https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen?alleenValideren=true
```

Antwoord `200` met `"status": "gevalideerd"`, of `422` met de fouten per regel. Draai zo één run, lees de fouten in `_response_body` en haal `?alleenValideren=true` weg als alles `200` geeft.

Met curl (dezelfde aanroep als FME, voor wie de workspace niet wil starten):

```bash
TOKEN=$(curl -s -d client_id="$CLIENT_ID" -d client_secret="$CLIENT_SECRET" -d grant_type=client_credentials \
  https://<installatie>/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
curl -s -X POST "https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde/inlezen?alleenValideren=true" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @waarden.json
```

## 4. Wat FME terugkrijgt

| HTTP | Betekenis | In FME |
|---|---|---|
| `200` | gepubliceerd (of gevalideerd); body `status`, `leveringId`, `versie`, `aantallen` | `<Output>` |
| `200` met `aantallen.ongewijzigd: true` | dezelfde body als de actieve versie: niets gewijzigd, geen nieuwe versie | `<Output>` |
| `422` | afgekeurd, niets gepubliceerd; de vorige stand blijft staan. Body: Problem Details met `fouten` per regel (`code`, `regel`, `veld`) | `<Rejected>`, de run stopt |
| `400` | body is geen JSON of niet in het SWF-formaat | `<Rejected>` |
| `401` / `403` | token ontbreekt of verlopen / client mist de datasetrol | `<Rejected>` |
| `404` | dataset niet geregistreerd met adapter `swf-monitor-v1` | `<Rejected>` |
| `202` | nog bezig na 120 s; volg de `Location`-header. Komt bij de huidige omvang niet voor | `<Output>` |
| `429` | meer dan `LADEN_COMPAT_RATE_LIMIT` aanroepen per minuut (standaard 120) | `<Rejected>` |

**Herhalen is veilig.** Een run nog een keer draaien geeft geen nieuwe versies (sha256). Wie retry in de HttpCaller aanzet, kan een header `Idempotency-Key` meesturen (bijvoorbeeld `<indicator>_<gebiedstype>_<datum>`).

**Veelvoorkomende fouten.** `jaar-ongeldig` (begingeldigheid `0000-01-01`), `gebied-onbekend` (gebiedscode bestaat niet in D-OmniTwin, of de gebiedsindeling van dat gebiedstype is nog niet geladen), `schema-ongeldig` op `status` (onbekende statuscode, zoals `A`). Zie [probleemtypen](README.md#probleemtypen).

## 5. Terugkijken

De leesvarianten werken met dezelfde client:

- `GET https://<installatie>/api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup`: de definities zoals D-OmniTwin ze heeft, in het formaat van het inlezen;
- `GET …/compat/swf-monitor/monitor_api/indicator_waarde` en `…/indicator_waarde/{indicator_id}`: de gepubliceerde waarden als `indicator_id`, `gebiedstype_id`, `gebieds_id`, `jaar`, `waarde`.

Elke aanroep is een levering in D-OmniTwin; status en fouten staan ook op `GET https://<installatie>/api/laden/v1/leveringen/{leveringId}`.
