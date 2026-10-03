# TC-07-003 — SWF-definities: indicatoren, gebiedstypen en relaties

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.2.0 · **Afhankelijk van:** –
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-definities`

## Vraag

- **Gebruiker:** data-engineer DWH (SWF)
- **Vraag:** "Ik wil alle 228 indicatordefinities van de huidige monitor met dezelfde UUID's in D-OmniTwin, met de 11 gebiedstypen en op welk gebiedstype elke indicator waarden heeft."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-monitor-definities:laden`

De eerste stap van de huidige stroom (eerst definities, dan waarden): de volledige set indicatoren, gebiedstypen en relaties uit de datamart, met dezelfde UUID's. Geleverd als Data Package-zip (drie CSV-resources) op de gewone ingang; de FME-route met hetzelfde formaat als nu staat in [swf-adapter-fme](../swf-adapter-fme/README.md). Beide leveren op dezelfde dataset `swf-monitor-definities`.

**UUID-conflict `d210c084…`:** in de stuurdata van D-OmniTwin is dit "Custom Gebied Type" (code `CUSTOM`, nergens in de code gebruikt); in de monitor "CBS buurten bebouwde komgrens" met 2.370 waarden. De levering zet naam, code (`CBS_BUURT_BBK`) en niveau via een upsert op `id`; de monitor is de bronhouder van deze UUID. De stuurdata moet mee, zodat een verse installatie niet weer "Custom Gebied Type" zet.

**Mapping gebiedstypen** (`gebiedstypen.json`, statisch): per gebiedstype een unieke code (`gebiedstypes.code` is uniek), het niveau, de dataset die de gebieden levert en een prefix voor codes die niet landelijk uniek zijn (welstand `WS`, woonplaats `WP`, postcode `PC`, bebouwde kom `BK`).

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): de definities rechtstreeks uit de monitor-database, inclusief velden die de export mist (eenheid, richting, bron, code).

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-monitor-definities`](datasets/swf-monitor-definities.json) | laden | definities | datapackage | export van de huidige monitor ($SWF_DUMP_DIR) | open | onbekend (navragen) | `dataset:swf-monitor-definities:laden` |

Verwacht:

- `swf-monitor-definities`: indicatoren 228; gebiedstypen 11; relaties 263; status A naar O 10

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-definities` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-monitor-definities | 228 indicatoren, 11 gebiedstypen, 263 relaties; status A → O: 10 | geldig (Table Schema en foreign keys) |

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-definities --uit /tmp/swf-definities
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
4. Leveren:
   ```bash
   curl -s -X POST "$API/datasets/swf-monitor-definities/leveringen?wacht=true" -H "Authorization: Bearer $TOKEN" \
     -H "Idempotency-Key: swf-monitor-definities-$(date +%Y%m%d)" -H "Content-Type: application/zip" \
     --data-binary @/tmp/swf-definities/swf-monitor-definities/swf-monitor-definities.zip
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-monitor-definities`, resource `indicatoren` | gelijk 228 |
| 2 | aantal | `swf-monitor-definities`, resource `gebiedstypen` | gelijk 11 |
| 3 | aantal | `swf-monitor-definities`, resource `relaties` | gelijk 263 |
| 4 | bewerking | `swf-monitor-definities`: regels met reden `status: A → O` — de 10 klimaatindicatoren | gelijk 10 |
| 5 | bewerking | `swf-monitor-definities`: regels met reden `gebiedstype-zonder-mapping` | gelijk 0 |
| 6 | api | `GET /api/data/v1/indicatoren?uuid=eq.97f53738-3439-4c28-8cac-046a52c65248&select=uuid,naam,status` (anoniem) — Oppervlak groen per inwoner, zelfde UUID als in de monitor | HTTP 200, ≥ 1 resultaten |
| 7 | api | `GET /api/data/v1/gebiedstypes?id=eq.d210c084-506b-48b4-87c9-b7d4bf422553&select=naam,code` (anoniem) — UUID-conflict opgelost: d210c084 is 'CBS buurten bebouwde komgrens', niet meer 'Custom Gebied Type' | HTTP 200, ≥ 1 resultaten, code = CBS_BUURT_BBK, naam = CBS buurten bebouwde komgrens |
| 8 | afkeuring | `swf-monitor-definities`, variant `status-a` — onbekende status A wordt afgekeurd; vorige versie blijft actief | 422, fout `schema-ongeldig`, niets gepubliceerd |
| 9 | idempotent | `swf-monitor-definities` twee keer leveren | zelfde versie, geen tweede publicatie |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Status A (10 klimaatindicatoren) wordt O; de betekenis van A is een open vraag (gat-analyse, vraag 3).
- UUID d210c084: in de stuurdata van D-OmniTwin 'Custom Gebied Type' (code CUSTOM, nergens gebruikt); in de monitor 'CBS buurten bebouwde komgrens' met 2.370 waarden. De levering zet naam en code (CBS_BUURT_BBK); de stuurdata moet mee (migratie).
- Eenheid, richting, bron en code per indicator zitten niet in de export; aanvullen via beheer of het gewone profiel definities.
- Eén testdefinitie (status B) en één dubbele indicatornaam gaan mee zoals ze zijn.
