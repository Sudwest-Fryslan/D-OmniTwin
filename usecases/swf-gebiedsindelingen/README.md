# TC-07-004 — SWF-gebiedsindelingen als GeoPackage-leveringen

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.1.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-gebiedsindelingen`

## Vraag

- **Gebruiker:** functioneel beheerder SWF / GIS-specialist
- **Vraag:** "Ik wil de gebiedsindelingen van de monitor (welstand × buurt, buurtdelen binnen/buiten de kom, woonplaatsen, postcodes, bebouwde kom, deelgebieden, coördinatorgebieden) als gebieden met geometrie in D-OmniTwin, in plaats van live uit de WFS."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-gebied-welstand-buurt:laden`, `dataset:swf-gebied-buurt-bebouwde-kom:laden`, `dataset:swf-gebied-woonplaats:laden`, `dataset:swf-gebied-postcode:laden`, `dataset:swf-gebied-bebouwde-kom:laden`, `dataset:swf-gebied-deelgebieden:laden`, `dataset:swf-gebied-coordinatorgebieden:laden`

De monitor haalt gebieden live uit de WFS van de GeoServer van SWF. D-OmniTwin slaat ze op als gebieden met geometrie (profiel `gebiedsindeling`). Open bronnen gaan vóór lokale bestanden: woonplaatsen (BAG) en postcodes (CBS PC4) komen van PDOK, de CBS-buurten uit [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md). Alleen wat echt SWF-intern is, komt uit `$SWF_GEO_DIR` (export uit de GeoServer) of `$SWF_DOCS_DIR` (projectmap).

**Namespace voor codes:** `gebieden.id` is uniek over alle gebiedstypen. Welstand-id's (volgnummers 1–758) worden `WS1`–`WS758`, woonplaatscodes `WP…`, postcodes `PC…`, bebouwde kom `BK…`, deelgebieden `DG1`–`DG6`, coördinatorgebieden `CO…`. De levering bevat de ruwe code; D-OmniTwin zet de prefix ervoor (`laadprofiel.doel.codePrefix`). Zonder prefix: `WS` + id, zonder voorloopnullen (dus `WS728`, niet `WS0728`).

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): de geometrie van welstand × buurt en de buurtdelen binnen/buiten de kom (nu alleen live in de WFS), zonder export uit de GeoServer.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-gebied-welstand-buurt`](datasets/swf-gebied-welstand-buurt.json) | laden | gebiedsindeling | geopackage | SWF-intern: export GeoServer ($SWF_GEO_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-gebied-welstand-buurt:laden` |
| [`swf-gebied-buurt-bebouwde-kom`](datasets/swf-gebied-buurt-bebouwde-kom.json) | laden | gebiedsindeling | geopackage | CBS-buurten (PDOK, open) × bebouwde kom (SWF-intern, $SWF_GEO_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-gebied-buurt-bebouwde-kom:laden` |
| [`swf-gebied-woonplaats`](datasets/swf-gebied-woonplaats.json) | laden | gebiedsindeling | geopackage | BAG woonplaatsen via PDOK (open, CC0) | open | CC0 | `dataset:swf-gebied-woonplaats:laden` |
| [`swf-gebied-postcode`](datasets/swf-gebied-postcode.json) | laden | gebiedsindeling | geopackage | CBS Postcode-4 2023 via PDOK (open, CC BY 4.0) | open | CC BY 4.0 | `dataset:swf-gebied-postcode:laden` |
| [`swf-gebied-bebouwde-kom`](datasets/swf-gebied-bebouwde-kom.json) | laden | gebiedsindeling | geopackage | SWF-intern: export GeoServer ($SWF_GEO_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-gebied-bebouwde-kom:laden` |
| [`swf-gebied-deelgebieden`](datasets/swf-gebied-deelgebieden.json) | laden | gebiedsindeling | geopackage | repo: data-upload/Deelgebieden_omgevingsvisie.gpkg | open | onbekend (navragen) | `dataset:swf-gebied-deelgebieden:laden` |
| [`swf-gebied-coordinatorgebieden`](datasets/swf-gebied-coordinatorgebieden.json) | laden | gebiedsindeling | geopackage | SWF-intern: projectmap ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-gebied-coordinatorgebieden:laden` |

Verwacht:

- `swf-gebied-welstand-buurt`: features ±758 (755 met waarden); codes 1–758 → WS1–WS758
- `swf-gebied-buurt-bebouwde-kom`: features ±273 (alle met waarden); codes BU1900xxxx_BBKJ / _BBKN
- `swf-gebied-woonplaats`: features 82 woonplaatsen (BAG, oktober 2026)
- `swf-gebied-postcode`: features 97 PC4-gebieden (CBS 2023)
- `swf-gebied-deelgebieden`: features 6
- `swf-gebied-coordinatorgebieden`: features 146; weggelaten 1 geometrie zonder vlak (geometrie-geen-vlak)

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-gebiedsindelingen` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-gebied-woonplaats | 295 binnen de bbox → 82 in de gemeente | geldig |
| swf-gebied-postcode | 336 → 97 | geldig |
| swf-gebied-deelgebieden | 6 | geldig |
| swf-gebied-coordinatorgebieden | 147 → 146 (1 geometrie zonder vlak) | geldig |
| swf-gebied-welstand-buurt | – | overgeslagen: SWF_GEO_DIR niet gezet |
| swf-gebied-buurt-bebouwde-kom | – | overgeslagen: SWF_GEO_DIR niet gezet |
| swf-gebied-bebouwde-kom | – | overgeslagen: SWF_GEO_DIR niet gezet |

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-gebiedsindelingen --uit /tmp/swf-gebiedsindelingen
   ```
2. Token halen (client credentials; tokenendpoint uit `/.well-known/openid-configuration` van realm `omnitwin`):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   API=https://omnitwin.example.nl/api/laden/v1
   ```
3. Registreren (eenmalig, realm-rol `beheerder`; de uitvoerder stuurt alleen `id`, `bronId`, `beschrijving` en `laadprofiel`):
   ```bash
   jq '{id, bronId, beschrijving, laadprofiel}' datasets/swf-gebied-welstand-buurt.json | \
     curl -s -X POST "$API/datasets" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
   ```
   Daarna in Keycloak de client-rol `dataset:swf-gebied-welstand-buurt:laden` op `omnitwin-api` aanmaken en toekennen aan de machineclient `etl-swf`.
4. Leveren:
   ```bash
   curl -s -X POST "$API/datasets/swf-gebied-welstand-buurt/leveringen?wacht=true" -H "Authorization: Bearer $TOKEN" \
     -H "Idempotency-Key: swf-gebied-welstand-buurt-$(date +%Y%m%d)" -H "Content-Type: application/geopackage+sqlite3" \
     --data-binary @/tmp/swf-gebiedsindelingen/swf-gebied-welstand-buurt/swf-gebied-welstand-buurt.gpkg
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-gebied-deelgebieden` | gelijk 6 |
| 2 | aantal | `swf-gebied-coordinatorgebieden` — 147 in de bron; 1 geometrie zonder vlak valt af | gelijk 146 |
| 3 | aantal | `swf-gebied-woonplaats` | minimaal 80 |
| 4 | aantal | `swf-gebied-postcode` | gelijk 97 |
| 5 | aantal | `swf-gebied-welstand-buurt` — alle welstand-id's met waarden | minimaal 755 |
| 6 | aantal | `swf-gebied-buurt-bebouwde-kom` — alle buurtdelen met waarden | minimaal 273 |
| 7 | api | `GET /api/data/v1/gebieden?id=eq.WS728&select=id,gebiedstype_id` (met token) — welstand-id 728 heet in D-OmniTwin WS728 (namespace) | HTTP 200, ≥ 1 resultaten |
| 8 | api | `GET /api/data/v1/gebieden?gebiedstype_id=eq.e7ebeee1-fe68-5731-a112-ee82f5a37f1b&select=id` (anoniem) | HTTP 200, ≥ 6 resultaten |
| 9 | viewer | gebiedsindeling 'Welstand per buurt' kiezen en inzoomen op Bolsward | vlakken per welstandsgebied × buurt, alleen na inloggen |
| 10 | idempotent | `swf-gebied-deelgebieden` twee keer leveren | zelfde versie, geen tweede publicatie |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Niet geleverd (geen waarden, inactief, en de codes botsen met de bestaande gebiedstypen Gemeente/Provincie): CBS gemeentegrenzen (1e6b3c18), CBS provinciegrenzen (e1de90ae), SWF gemeentegrens 1 januari 2018 (f9e2bd26), SWF gemeentegrens zonder littens (82525652).
- Welstand × buurt, bebouwde kom en de kom voor de buurtdelen staan alleen in de GeoServer van SWF: nodig is een export als GeoPackage ($SWF_GEO_DIR) of de database-dump ($SWF_DB_DUMP). Zonder die bron worden deze datasets overgeslagen.
- Welke bebouwde kom de monitor voor _BBKJ/_BBKN gebruikt, is niet bekend (Wegenverkeerswet, Wet natuurbescherming of BAG-woonplaats).
- De gebiedstypen 'Deelgebieden Omgevingsvisie' en 'Dorps- en wijkcoördinatorgebieden' zijn nieuw (uuid5); ze zitten niet in de SWF-definities en moeten in de stuurdata van D-OmniTwin.
- Postcode: het open CBS-PC4 vervangt 'ESRI postcode SWF' (licentie); PC6 alleen als SWF dat wil.
