# TC-07-006 — SWF-basismonitor: waarden per indicator × gebiedstype

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.4.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
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

**Met de database-dump van de monitor** (`$SWF_DB_DUMP`, variant `monitor-database`, heeft voorrang; [#316](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/316)): alle waarden uit de tabel `indicator_waarde`, met dezelfde bewerkingen plus `oude-buurtcodes`. Ook de database bewaart geen `n`; de vlag bron-onderdrukt blijft. Exporteren: [`scripts/beheer/swf_monitor_dump.py`](../../scripts/beheer/swf_monitor_dump.py) `exporteer --dump public.monitor.dmp --uit <map>` (geen database nodig; `pg_restore` alleen om het custom format te lezen), daarna `SWF_DB_DUMP=<map>`. De map bevat echte data en komt nooit in git.

| | Export feb. 2026 | Database-dump 09-10-2026 |
|---|---|---|
| waarden (alle gebiedstypen) | 43.253 | 81.373 |
| CBS-buurten / buurtdelen bebouwde kom / welstand × buurt | 33.197 / 2.370 / 7.686 | 71.317 / 2.370 / 7.686 |
| indicatoren met waarden / combinaties indicator × gebiedstype | 49 / 57 | 61 / 69 |
| jaren | 2012–2025 | 2011–2026 |
| jaar 0 / BU19009997-98 | 152 / 4 | 152 / 4 |
| codes zonder BU (2011–2012) | – | 795 waarden op 133 numerieke codes; definitief weggelaten bij de export (#342) |
| levering Basis (deze use case) | 35.411 | 72.736 |

Nieuw met waarden: de vijf leeftijdsgroepen, *diefstal fiets*, *inbraak auto*, *inbraak woning*, *dronken personen*, *drugs*, *geluid* en *jongeren*; geen indicator die in februari waarden had, ontbreekt. De numerieke codes zijn `11` + buurtcode (10 cijfers), wijkcode (8) of gemeentecode (6), opgeslagen op het gebiedstype CBS-buurten; ze zijn legacy van vóór 2013 en worden definitief weggelaten (besluit [#342](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/342)): `swf_monitor_dump.py exporteer` neemt ze niet op in `waarden.json` (telling `legacy_2011_2012_weggelaten` in `export.json`). De bewerking `oude-buurtcodes` (reden `buurtcode-oud`) blijft als vangnet.

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
| *database-dump* (`SWF_DB_DUMP`, 10-10-2026, dump van 09-10-2026) | 81.373 → 73.687 (Basis) → 72.736 (152 jaar 0, 4 onbekende buurt, 795 buurtcode-oud) | geldig; n leeg → bron-onderdrukt 72.736 |

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
| 1 | aantal | `swf-monitor-waarden` — 35.411 uit de export, 72.736 uit de database-dump | minimaal 35411 |
| 2 | bewerking | `swf-monitor-waarden`: regels met reden `jaar-ongeldig` | gelijk 152 |
| 3 | bewerking | `swf-monitor-waarden`: regels met reden `gebied-onbekend` | gelijk 4 |
| 3a | bewerking | `swf-monitor-waarden`: regels met reden `buurtcode-oud` — vangnet; de export laat de legacy van 2011–2012 al weg (#342) | maximaal 795 |
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
- Database-dump: 795 waarden uit 2011–2012 op numerieke codes (voorloop `11`) zijn legacy van vóór 2013 en worden definitief weggelaten, al bij de export (besluit https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/342).
- Database-dump: overlap met het CBS-recept (A6) is 5 indicatoren met 3.614 waarden vanaf 2013 (export: 2.598 vanaf 2019); de nieuwste peildatum wint.
