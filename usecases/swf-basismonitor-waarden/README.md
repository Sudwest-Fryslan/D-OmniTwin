# TC-07-006 — SWF-basismonitor: waarden per indicator × gebiedstype

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.1.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-basismonitor-waarden`

## Vraag

- **Gebruiker:** data-engineer DWH (SWF)
- **Vraag:** "Ik wil alle waarden van de Basis monitor (CBS-buurten en buurtdelen binnen/buiten de kom) in één levering in D-OmniTwin, zonder de fouten uit de huidige export, en met de n<10-afspraak vastgelegd."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-monitor-waarden:laden`

Alle waarden van de Basis monitor (CBS-buurten en buurtdelen binnen/buiten de bebouwde kom) als één Data Package-levering op `swf-monitor-waarden`, in plaats van ±57 losse FME-runs (eis E9). Het vervangbereik is indicator × gebiedstype: deze levering vervangt alleen de combinaties die erin zitten, zodat [swf-klimaatmonitor](../swf-klimaatmonitor/README.md) (welstand × buurt) ernaast kan bestaan.

**Transformaties** (declaratief in `datasets/swf-monitor-waarden.json`):

| Huidig | Levering | Regel |
|---|---|---|
| `jaar = 0` (152 waarden van één indicator) | weggelaten | de laad-API keurt af met `jaar-ongeldig`; variant `met-fouten` bewijst dat |
| `BU19009997`, `BU19009998` (4 waarden) | weggelaten | bestaan niet in de CBS-buurtindeling 2024 (`gebied-onbekend`) |
| `begingeldigheid` `JJJJ-01-01` | `jaar` | de lees-dump heeft het jaar al; via de adapter: `JJJJ-01-01` → jaar |
| geen `n` | `n` leeg | dataset `bijOntbrekendeN: bron-onderdrukt`: de DWH laat n<10 zelf weg |
| `indicator_id`, `gebiedstype_id`, `gebieds_id` | `indicator_uuid`, `gebiedstype`, `gebied_code` | hernoemen |

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): alle waarden in één keer, eventueel met `n` als de monitor die bewaart; dan kan de vlag bron-onderdrukt weg.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-monitor-waarden`](datasets/swf-monitor-waarden.json) | laden | waarnemingen | datapackage | export van de huidige monitor ($SWF_DUMP_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-monitor-waarden:laden` |

Verwacht:

- `swf-monitor-waarden`: gelezen basis 35567; jaar 0 152; gebied onbekend 4; regels 35411; combinaties ±41 indicator × gebiedstype; jaren 2012–2025; n leeg → bron-onderdrukt

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-basismonitor-waarden` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-monitor-waarden | 43.253 → 35.567 (Basis) → 35.411 (152 jaar 0, 4 onbekende buurt) | geldig; n leeg → bron-onderdrukt 35.411 |
| variant met-fouten | 35.567 | ongeldig: veld jaar onder minimum 1900 (zoals bedoeld) |

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-basismonitor-waarden --uit /tmp/swf-basismonitor-waarden
   ```
2. Token halen (client credentials; tokenendpoint uit `/.well-known/openid-configuration` van realm `omnitwin`):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   API=https://omnitwin.example.nl/api/laden/v1
   ```
3. Registreren (eenmalig, realm-rol `beheerder`; de uitvoerder stuurt alleen `id`, `bronId`, `beschrijving` en `laadprofiel`):
   ```bash
   jq '{id, bronId, beschrijving, laadprofiel}' datasets/swf-monitor-waarden.json | \
     curl -s -X POST "$API/datasets" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
   ```
   Daarna in Keycloak de client-rol `dataset:swf-monitor-waarden:laden` op `omnitwin-api` aanmaken en toekennen aan de machineclient `etl-swf`.
4. Leveren:
   ```bash
   curl -s -X POST "$API/datasets/swf-monitor-waarden/leveringen?wacht=true" -H "Authorization: Bearer $TOKEN" \
     -H "Idempotency-Key: swf-monitor-waarden-$(date +%Y%m%d)" -H "Content-Type: application/zip" \
     --data-binary @/tmp/swf-basismonitor-waarden/swf-monitor-waarden/swf-monitor-waarden-basis.zip
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-monitor-waarden` | gelijk 35411 |
| 2 | bewerking | `swf-monitor-waarden`: regels met reden `jaar-ongeldig` | gelijk 152 |
| 3 | bewerking | `swf-monitor-waarden`: regels met reden `gebied-onbekend` | gelijk 4 |
| 4 | afkeuring | `swf-monitor-waarden`, variant `met-fouten` — met jaar 0 wordt de hele levering afgekeurd; vorige versie blijft actief | 422, fout `jaar-ongeldig`, niets gepubliceerd |
| 5 | afkeuring | `swf-monitor-waarden`, variant `met-fouten` | 422, fout `gebied-onbekend`, niets gepubliceerd |
| 6 | api | `GET /api/data/v1/gebied_data?gebied_id=eq.BU19000002&indicator_uuid=eq.461d542b-b8be-4510-9dd0-5ba554b818cb&select=jaar,waarde` (met token) — Personenauto's per huishouden voor Bolsward-Zuidoost | HTTP 200, ≥ 1 resultaten |
| 7 | api | `GET /api/laden/v1/datasets/swf-monitor-waarden` (met token) — laatste levering gepubliceerd, aantallen.bronOnderdrukt = aantallen.gepubliceerd | HTTP 200 |
| 8 | idempotent | `swf-monitor-waarden` twee keer leveren | zelfde versie, geen tweede publicatie |
| 9 | viewer | Kompas 'SWF Basis', Bolsward-Zuidoost | de 41 indicatoren met waarden zijn gekleurd, de rest grijs |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Jaar 0 (152 waarden van één indicator) en 2 buurtcodes zonder CBS-buurt (4 waarden) laat de ETL weg; de variant met-fouten toont dat de laad-API ze afkeurt.
- n ontbreekt in de export: alle waarden krijgen de vlag bron-onderdrukt (de DWH laat n<10 weg). Met n in de datamart kan de vlag weg.
- Overlap met cbs-kerncijfers: 5 indicatoren in de SWF-export hebben dezelfde UUID als het CBS-recept (2.598 waarden vanaf 2019). gebied_data heeft één waarde per gebied × indicator × jaar × scenario; twee datasets op dezelfde sleutel vragen een regel (bron per waarde, of één dataset leidend).
- Float-ruis tot 16 decimalen gaat ongewijzigd mee.
