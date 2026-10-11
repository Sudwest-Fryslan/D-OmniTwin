# TC-07-007 — SWF-klimaatmonitor: welstand × buurt met labels A–E

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.4.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), [swf-kompasprofiel](../swf-kompasprofiel/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-klimaatmonitor`

## Vraag

- **Gebruiker:** adviseur klimaatadaptatie
- **Vraag:** "Welk label (A–E) heeft een welstandsgebied in Bolsward voor hittestress, droogte en hemelwateroverlast, en welke indicator trekt het omlaag?"
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-monitor-waarden:laden`, `realm-rol lezer (de Klimaatmonitor is intern)`

De Klimaatmonitor draait op welstandsgebieden opgeknipt per CBS-buurt, met 3 thema's (hemelwateroverlast, hittestress, droogte) en 10 indicatoren (status A). Deze use case levert de waarden op welstand × buurt (7 indicatoren hebben er waarden) op dezelfde dataset als de Basis monitor, met vervangbereik indicator × gebiedstype. De labels A–E komen uit het kompasprofiel *SWF Klimaat* ([swf-kompasprofiel](../swf-kompasprofiel/README.md)) met classificatie `label_ae` ([#256](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/256)). De drempels laadt SWF als data in tabel `indicator_labels`; tot dan rekent D-OmniTwin met kwintielen en meldt het *voorlopige drempels* ([labels_methodiek.md](../../docs/3-data-engineering/labels_methodiek.md)).

**Namespace:** welstand-id `728` wordt `WS728` (bewerking `prefix`), want `gebieden.id` is uniek over alle gebiedstypen. De variant `zonder-namespace` laat de prefix weg; de laad-API hoort die levering af te keuren (`gebied-onbekend`).

**Met de database-dump van de monitor** (`$SWF_DB_DUMP`, variant `monitor-database`, heeft voorrang; [#316](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/316)): dezelfde 7.686 waarden op welstand × buurt als de export. Exporteren: [`scripts/beheer/swf_monitor_dump.py`](../../scripts/beheer/swf_monitor_dump.py) `exporteer --dump public.monitor.dmp --uit <map>` (geen database nodig; `pg_restore` alleen om het custom format te lezen), daarna `SWF_DB_DUMP=<map>`. De map bevat echte data en komt nooit in git.

**Drempels in de monitor.** De monitorconfiguratie bewaart per indicator `labeling` (A–E met van, tot, kleur en naam: *Robuust*, *Acceptabel*, *Risicovol*, *Onacceptabel*, *Ontwrichting*): voor 6 van de 10 klimaatindicatoren en in de Basis monitor ook voor *Waterdiepte tegen gevel*, *Aandeel bladerdek per buurt*, *Gemiddeld Laagste Grondwaterstand* en *Gemiddeld energielabel*. Het exportscript zet ze in `indicator_labels_monitor.json` (formaat van `db/stuurdata/indicator_labels_*.json`). Verschil met de stuurdata (vastgesteld, A3): *Aandeel water t.o.v. verhard* staat in de monitor als fractie (0,1) en in de stuurdata als procent (10); *Waterdiepte tegen gevel* heeft in de monitor geen gat tussen D en E (D 14,99–24,99); een open grens is in de monitor 0, 99, 999 of 9999. *Waterdiepte op straat* heeft in de monitor geen drempels. De stuurdata (*Monitoring KA SWF - dialoog 2*) is leidend en blijft de standaard (besluit [#342](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/342)); de drempels uit de monitor laden blijft mogelijk, als keuze van de beheerder: `python init_data/scripts/load_sample.py --stap drempels --drempels <map>/indicator_labels_monitor.json`. De polariteit volgt wel de monitor: `omkeren` gaat voor op de stuurdata (via `score_type` in swf-definities). *Waterdiepte op straat* staat in de stuurdata met `c4e1b3bb…` ([#341](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341)).

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-monitor-waarden`](datasets/swf-monitor-waarden.json) | laden | waarnemingen | datapackage | export van de huidige monitor ($SWF_DUMP_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-monitor-waarden:laden` |

Verwacht:

- `swf-monitor-waarden`: regels 7686; indicatoren 7; gebieden 755; jaren 2020–2025; codes WS1–WS758

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-klimaatmonitor` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-monitor-waarden | 43.253 → 7.686 (welstand × buurt), codes WS1–WS758 | geldig |
| *database-dump* (`SWF_DB_DUMP`, 10-10-2026, dump van 09-10-2026) | 81.373 → 7.686 (welstand × buurt) | geldig |

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-klimaatmonitor --uit /tmp/swf-klimaatmonitor
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
     --data-binary @/tmp/swf-klimaatmonitor/swf-monitor-waarden/swf-monitor-waarden-klimaat.zip
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-monitor-waarden` | gelijk 7686 |
| 2 | bewerking | `swf-monitor-waarden`: regels met reden `jaar-ongeldig` | gelijk 0 |
| 3 | afkeuring | `swf-monitor-waarden`, variant `zonder-namespace` | 422, fout `gebied-onbekend`, niets gepubliceerd |
| 4 | api | `GET /api/data/v1/gebied_data?gebied_id=like.WS*&indicator_uuid=eq.bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c&select=gebied_id&limit=1` (met token) — Afstand tot koele plek op welstand × buurt | HTTP 200, ≥ 1 resultaten |
| 5 | api | `GET /api/data/v1/gebied_data?gebied_id=like.WS*&select=gebied_id&limit=1` (anoniem) — anoniem: geen klimaatwaarden zichtbaar zolang de dataset RESTRICTED is (vergt RLS) | HTTP 200 |
| 6 | viewer | Kompas 'SWF Klimaat', welstand × buurt in Bolsward kiezen | per thema en indicator een label A–E en de indicator die het laagst scoort |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Labels A–E: classificatie label_ae (#256). De drempels van SWF staan nog niet in indicator_labels (#222, A3); tot ze geladen zijn, rekent D-OmniTwin met kwintielen en meldt het voorlopige drempels.
- Dezelfde dataset als swf-basismonitor-waarden (swf-monitor-waarden); vervangBereik indicator × gebiedstype houdt de twee leveringen uit elkaar. De registratie moet in beide use cases gelijk zijn (unittest).
- Gevoelstemperatuur en Afstand tot koele plek zijn SWF-bewerkingen; de open Klimaateffectatlas heeft voor Fryslân geen download (zie hittestress).
