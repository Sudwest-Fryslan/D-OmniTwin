# TC-07-025 — SWF-initialisatie: eerste vulling uit de lokale D-OmniTwin-database

**Status:** actief
**Versie:** 0.2.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `SWF_EXPORT_DIR=… python -m omnitwin.usecases controleer swf-initialisatie`

## Vraag

- **Gebruiker:** projectleider en functioneel beheerder SWF
- **Vraag:** "Ik wil de SWF-installatie de eerste keer vullen met de rijkere data uit mijn lokale D-OmniTwin-database, via de laad-API en herhaalbaar, zonder open data of demodata mee te kopiëren."
- **Rechten:** `realm-rol beheerder (registreren, inrichten)`, `dataset:swf-init-indicatoren:laden`, `dataset:swf-init-welstandsgebieden:laden`, `dataset:swf-init-waarnemingen:laden`

Aanname A1 van https://github.com/TLaan/D-OmniTwin/issues/222: de eerste vulling bij SWF komt uit de lokale D-OmniTwin-database van de projectleider, die rijker is dan de export van de huidige gebiedsmonitor. Die database komt als dump (`pg_dump -Fc`, niet in git). **Geen 1-op-1 restore:** een script haalt eruit wat de use case nodig heeft, en de use case laadt dat als gewone leveringen via de laad-API en de beheerroute. Zo is de vulling herhaalbaar en herleidbaar (versies, herkomst, n-vlag, voorrang bij overlap) en komt er niets buiten de laadstraat om in de database. Doorlopende leveringen gaan daarna via de FME-route ([swf-adapter-fme](../swf-adapter-fme/README.md)) en de open-data-use cases.

## Wat er meegaat en wat niet

Gemeten op de dump van 04-10-2026 (518.603 waarden, 244 indicatoren, 3.756 gebieden):

| Uit de lokale database | Wat de use case ermee doet | Aantal |
|---|---|---|
| Waarden uit de SWF-gebiedsmonitor (bron `<uuid>_d_*.json`, de pushbestanden) | **mee**, op buurt en welstandsgebied | 10.365 |
| Kadaster BAG en BAG (per buurt berekend) | **mee**: open, maar nog geen adapter | 30.228 |
| RVO EP-Online en *Berekend: EP-Online / BAG* | **mee**: open, nog geen adapter (API-sleutel) | 5.248 |
| OpenStreetMap / Overpass (OV-haltes) | **mee**: open (ODbL), nog geen adapter | 2.475 |
| CBS-tabellen (`CBS_*`), *Kerncijfers wijken en buurten 2023*, *Gezondheidsmonitor RIVM* | niet: open data, downloaden [cbs-kerncijfers](../cbs-kerncijfers/README.md) en [rivm-gezondheidsmonitor](../rivm-gezondheidsmonitor/README.md) zelf (`open-data`) | 200.240 |
| Waarden zonder bron | niet: niet herleidbaar; het zijn politiecijfers die [politie-misdrijven](../politie-misdrijven/README.md) open downloadt (`bron-onbekend`) | 4.931 |
| Buurtcodes buiten de CBS-indeling 2024 van Fryslân | niet: geen gebied in de installatie (`gebied-onbekend`) | 1.587 |
| Waarden op provincieniveau | niet: de installatie kent geen provincies (`gebiedstype-provincie`) | 5 |
| Waarden buiten Fryslân (Groningen, Drenthe) | niet: het script exporteert alleen Fryslân en de welstandsgebieden | 263.524 |
| Demodata (`DEMODATA…`) | niet (`demodata`) | 0 |
| **Waarden geladen** (`swf-init-waarnemingen`) | | **48.316** |
| Indicatordefinities | alleen wat nog nergens anders vandaan komt; 243 van de 244 gebruikte komen uit [swf-definities](../swf-definities/README.md) of de stuurdata en worden **niet** overschreven | 1 |
| Welstandsgebieden × buurt (gebiedstype welstand) | **mee** als gebiedsindeling, code 1–758 → WS1–WS758 | 756 |
| Volledig Kompas (kwadrant › thema › onderdeel, weging, actueel) | **mee**, aanvullend: wat er al is, blijft | 247 plekken, 241 indicatoren |
| Kompas: extra onderdelen, extra tags, scoringsregels | niet: nog geen route | 22, 53, 16 |
| Externe kaartlagen (WFS/WMS) | **mee**, aanvullend (zelfde naam blijft); toegang volgens B3 | 8 |
| Lokale kaartlaag *Omgevingsvisie SWF* | niet: verwijst naar een bestand in de oude installatie; komt via [swf-kaartlagen](../swf-kaartlagen/README.md) (`lokale-laag`) | 1 |
| `system_prompts`, `chat_scenarios`, `color_schemas`, `visualisatie_profielen`, `ov_haltes`, `omgevingsvisie_deelgebieden` | niet: inrichting of brondata met een eigen route (stuurdata, beheer, swf-gebiedsindelingen) | – |

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-init-indicatoren`](datasets/swf-init-indicatoren.json) | laden | definities | datapackage | `$SWF_EXPORT_DIR/indicatoren.csv` | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-init-indicatoren:laden` |
| [`swf-init-welstandsgebieden`](datasets/swf-init-welstandsgebieden.json) | laden | gebiedsindeling | geopackage | `$SWF_EXPORT_DIR/welstandsgebieden.gpkg` | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-init-welstandsgebieden:laden` |
| [`swf-init-waarnemingen`](datasets/swf-init-waarnemingen.json) | laden | waarnemingen | datapackage | `$SWF_EXPORT_DIR/gebied_data.csv` | beperkt (inloggen) | onbekend (per bron: BAG CC0, EP-Online te bevestigen, OSM ODbL, monitor intern) | `dataset:swf-init-waarnemingen:laden` |
| [`swf-init-kompas`](datasets/swf-init-kompas.json) | beheer | kompasprofiel | datapackage ([schema](kompasprofiel.schema.json)) | `$SWF_EXPORT_DIR/kompasprofiel_volledig_kompas.json` | beperkt (inloggen) | onbekend (navragen) | `realm-rol beheerder` |
| [`swf-init-kaartlagen`](datasets/swf-init-kaartlagen.json) | beheer | externe-kaartlagen | datapackage ([schema](externe-kaartlagen.schema.json)) | `$SWF_EXPORT_DIR/externe_kaartlagen.json` | openbaar (per laag `toegang`) | volgt de dienst (PDOK) | `realm-rol beheerder` |

**Bewerkingen** (declaratief in `datasets/*.json`, geteld per reden):

| Export | Levering | Regel |
|---|---|---|
| `bron` begint met `CBS`, `Kerncijfers wijken en buurten` of `Gezondheidsmonitor RIVM` | weggelaten (`open-data`) | open data downloadt de adapter van de eigen use case |
| `bron` leeg | weggelaten (`bron-onbekend`) | niet herleidbaar |
| buurtcode niet in de CBS-buurten 2024 binnen Fryslân (dezelfde bron als `cbs-gebied-buurten`, met `koppel` + `binnen`) | weggelaten (`gebied-onbekend`) | anders keurt de laad-API de hele levering af |
| welstand-id `728` | `WS728` | `code_prefix` van het gebiedstype welstand |
| geen `n` | `n` leeg | `bijOntbrekendeN: bron-onderdrukt`; de drempel blijft in de ETL (aanname A7) |
| status `A` | `O` | A = Actueel (aanname A2); `O` (Onderzoek) blijft `O`; de lokale database kent geen `A` |
| Kompas: *Waterdiepte op straat* `c4e1b3bb…` (vervallen) | `f6eafa70…` | de aangehouden UUID (aanname A4) |

**Overlap met andere bronnen** (aanname A6). Een waarde uit de initialisatie en een uit een andere dataset op dezelfde sleutel (gebied × indicator × jaar of peildatum × scenario): de nieuwste bronpeildatum wint, bij een gelijke bronpeildatum de laatst aangeleverde levering. De export heeft geen `dct:modified`, dus de bronpeildatum is de datum van ontvangst: de initialisatie wint van wat eerder geleverd is (zoals `sample-open-zonder-adapter`, inclusief de DEMODATA van Bolsward-Zuidoost) en verliest van elke latere levering (FME, open data). De andere waarde blijft zichtbaar als `andere_bronnen` (zie [voorrang bij overlap](../../docs/api/laden/README.md#voorrang-bij-overlap)).

**Toegang.** De waarden, definities, gebiedsindeling en het Kompas zijn `RESTRICTED` (intern). De externe kaartlagen zijn openbare diensten; per laag zet het script `toegang` (aanname B3: *GeoVisia Project Locaties* en projecten 'in plan' intern). Tot de toegang per laag er is (https://github.com/TLaan/D-OmniTwin/pull/274) wordt een interne laag niet actief gezet. In deze dump staat geen GeoVisia-laag; de GeoVisia-projecten komen uit [swf-kaartlagen](../swf-kaartlagen/README.md).

**Beheerroute.** Het Kompas en de externe kaartlagen zijn inrichting, geen brondata (ADR 0003). Ze gaan als Data Package naar de beheerroute (`/api/beheer/v1/kompasprofielen`, `/api/beheer/v1/externe-kaartlagen`). Die bestaat nu alleen in-process (`installeer --inproces`, `omnitwin.laden.beheer`): **aanvullen, nooit overschrijven**, idempotent.

## Stappen

Alles op de server van de installatie, in de map met `docker-compose.yml` en `.env`. De dump en de export bevatten interne data: buiten de repo houden en na afloop opruimen.

1. **Dump herstellen** in een tijdelijke database (zelfde image als de installatie, met PostGIS en pgvector), alleen lokaal bereikbaar:
   ```bash
   docker run -d --name swfdump -e POSTGRES_USER=omnitwin_user -e POSTGRES_DB=swfbron \
     -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" d-omnitwin-postgres
   docker cp omnitwin_swf_data.dump swfdump:/tmp/swf.dump
   docker exec swfdump pg_restore -U omnitwin_user -d swfbron --no-owner --no-privileges /tmp/swf.dump
   ```
2. **Export maken** met [`scripts/beheer/swf_export.py`](../../scripts/beheer/swf_export.py), in de backend-image (die heeft psycopg2 en fiona), naast de tijdelijke database. `SWF_DUMP_DIR` is de export van de huidige monitor (nodig om de definities van swf-definities niet nog eens te leveren):
   ```bash
   docker run --rm --network container:swfdump -e PGHOST=localhost -e PGUSER=omnitwin_user -e PGDATABASE=swfbron \
     -v "$PWD:/app:ro" -v "$SWF_DUMP_DIR:/monitor:ro" -v /pad/naar/swf-export:/uit \
     --entrypoint python d-omnitwin-backend /app/scripts/beheer/swf_export.py --uit /uit \
     --monitor-definities /monitor/output/api_backup_dump.json
   ```
   Uitvoer: `gebied_data.csv`, `indicatoren.csv`, `welstandsgebieden.gpkg`, `kompasprofiel_volledig_kompas.json`, `externe_kaartlagen.json` en `export.json` (aantallen en controlesommen).
3. **Lokaal controleren** tegen de profielen, zonder API (`frictionless` nodig voor de Data Packages):
   ```bash
   SWF_EXPORT_DIR=/pad/naar/swf-export python -m omnitwin.usecases controleer swf-initialisatie
   ```
   Alle controles van het type `aantal` en `bewerking` moeten `ok` zijn. Wijken de aantallen af (andere dump), lees dan `export.json` en pas de aantallen in `usecase.json` en hierboven aan.
4. **Installeren**, in-process (eerste installatie; zonder HTTP en token). De afhankelijkheden (`swf-definities`, `cbs-gebiedsindelingen`) gaan mee; `swf-definities` heeft `SWF_DUMP_DIR` nodig:
   ```bash
   docker compose run --rm -v /pad/naar/swf-export:/swf-export:ro -v "$SWF_DUMP_DIR:/swf-dump:ro" \
     -e SWF_EXPORT_DIR=/swf-export -e SWF_DUMP_DIR=/swf-dump \
     db-init python -m omnitwin.usecases installeer swf-initialisatie --inproces
   ```
   Verwacht: `swf-init-indicatoren`, `swf-init-welstandsgebieden` en `swf-init-waarnemingen` *gepubliceerd*, `swf-init-kompas` en `swf-init-kaartlagen` *verwerkt*. De waarden duren enkele minuten (proef: 6,5 minuut).
   Via HTTP kan ook, met de eenmalige machineclient `etl-initialisatie` (`docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh etl-initialisatie dataset:swf-init-indicatoren:laden dataset:swf-init-welstandsgebieden:laden dataset:swf-init-waarnemingen:laden`); het Kompas en de kaartlagen dan nog in-process (de beheer-API is er nog niet).
5. **Controleren** in de API en de viewer (zie Acceptatiecriteria).
6. **Opruimen:** `docker rm -f swfdump`, de export en de dump verwijderen, de client `etl-initialisatie` intrekken (als die gemaakt is).

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-init-indicatoren`, resource `indicatoren` | gelijk 1 |
| 2 | aantal | `swf-init-indicatoren`, resource `relaties` (relaties komen uit swf-definities) | gelijk 0 |
| 3 | bewerking | `swf-init-indicatoren`: `status: A → O` | gelijk 0 |
| 4 | aantal | `swf-init-welstandsgebieden` | gelijk 756 |
| 5 | aantal | `swf-init-waarnemingen` | gelijk 48.316 |
| 6 | bewerking | `swf-init-waarnemingen`: `open-data` | gelijk 200.240 |
| 7 | bewerking | `swf-init-waarnemingen`: `bron-onbekend` | gelijk 4.931 |
| 8 | bewerking | `swf-init-waarnemingen`: `gebied-onbekend` | gelijk 1.587 |
| 9 | bewerking | `swf-init-waarnemingen`: `gebiedstype-provincie` | gelijk 5 |
| 10 | bewerking | `swf-init-waarnemingen`: `demodata` | gelijk 0 |
| 11 | aantal | `swf-init-kompas`, resource `kompasprofiel` | gelijk 247 |
| 12 | bewerking | `swf-init-kompas`: vervallen UUID → aangehouden UUID (A4) | gelijk 1 |
| 13 | aantal | `swf-init-kaartlagen`, resource `externe_kaartlagen` | gelijk 8 |
| 14 | bewerking | `swf-init-kaartlagen`: `lokale-laag` | gelijk 1 |
| 15 | api | `GET /api/data/v1/gebied_data?gebied_id=eq.BU19000002&select=indicator_uuid,bron,andere_bronnen` — waarden op Bolsward-Zuidoost, met de tweede bron bij overlap | HTTP 200, ≥ 1 resultaat |
| 16 | api | `GET /api/data/v1/gebieden?id=eq.WS728&select=id,gebiedstype_id` — welstand × buurt in de namespace WS | HTTP 200, ≥ 1 resultaat |
| 17 | idempotent | `swf-init-waarnemingen` twee keer leveren | zelfde versie, geen tweede publicatie |
| 18 | viewer | Kompas *Volledig Kompas*, Bolsward-Zuidoost | 4 kwadranten, 12 thema's; monitor- en BAG/EP-Online/OSM-indicatoren gekleurd |
| 19 | viewer | gebiedsindeling *SWF welstandsgebieden*, *Verhouding oppervlakte water / verharding* | vlakken per welstandsgebied × buurt met waarden (na inloggen) |
| 20–24 | recht | `beheerder` registreert; `etl-initialisatie` levert de eigen dataset maar niet `swf-monitor-waarden` en registreert niet; `lezer` levert niet | toegestaan / 403 |

`aantal` en `bewerking` controleert `controleer` op de lokaal gemaakte levering (alleen met `SWF_EXPORT_DIR`; anders overgeslagen, geen fout); de rest vraagt een draaiende installatie.

**Proef** (04-10-2026, korte stack met Keycloak en de sample, in-process): 48.316 waarden gepubliceerd en allemaal zichtbaar (411 met een tweede bron), 756 welstandsgebieden (7.412 waarden op WS-codes), 1 definitie, Volledig Kompas van 23 naar 247 plekken (241 indicatoren, 4 kwadranten, 12 thema's, 33 onderdelen), 7 nieuwe externe kaartlagen naast *BAG Woonplaatsen*. Bolsward-Zuidoost: 62 waarden uit de initialisatie (35 indicatoren), 84 van de 247 Kompasplekken met een waarde. Tweede keer installeren: Kompas en kaartlagen ongewijzigd.

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-initialisatie`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- De aantallen in de controles gelden voor de dump van de lokale database van 04-10-2026. Een nieuwe export: eerst `controleer`, dan de aantallen in `usecase.json` en hier bijwerken.
- Open data gaat nooit mee, ook niet als de open-data-use cases hem (nog) niet laden: 45.239 waarden op wijk- en gemeenteniveau (CBS Kerncijfers, RIVM) en *Huisarts* (CBS, ook op buurtniveau). Vervolg: cbs-kerncijfers en rivm-gezondheidsmonitor uitbreiden met wijken en gemeenten.
- Waarden zonder bron (4.931) gaan niet mee: politiecijfers (die politie-misdrijven open downloadt) en 16 waarden *slachtoffer inbraak* op provincie en gemeente die niet herleidbaar zijn.
- Definities die al uit swf-definities of de stuurdata komen, worden niet overschreven. De lokale database wijkt af bij 100 omschrijvingen, 40 eenheden, 19 score_types, 8 statussen en 7 namen; die keuze ligt bij de projectleider (een aparte levering van definities).
- Kompas: alleen het *Volledig Kompas* heeft koppelingen in de lokale database; het *Klimaat Kompas* komt uit de stuurdata en [swf-kompasprofiel](../swf-kompasprofiel/README.md). Extra onderdelen (22), extra tags (53) en scoringsregels (16) hebben nog geen route.
- De beheerroute (Kompas, externe kaartlagen) bestaat alleen in-process. Over HTTP is er nog geen `/api/beheer/v1`; `installeer` zonder `--inproces` meldt die twee dan als niet geladen.
- `swf-init-welstandsgebieden` en `swf-gebied-welstand-buurt` ([swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), ontwerp) leveren hetzelfde gebiedstype; wie het laatst levert, bepaalt de indeling. Kies er één zodra de GeoServer-export er is (B1).
- De bron van de monitorwaarden is de bestandsnaam van de push (`<uuid>_d_cbs_buurten.json`), zoals in de lokale database.
- Zonder `n` in de lokale database: vlag bron-onderdrukt, de drempel blijft in de ETL (aanname A7).
