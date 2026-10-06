# TC-07-025 — SWF-initialisatie: vulling uit een dump van de lokale D-OmniTwin-database

**Status:** actief (zonder `SWF_EXPORT_DIR` overgeslagen, geen fout)
**Versie:** 0.3.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `SWF_EXPORT_DIR=… python -m omnitwin.usecases controleer swf-initialisatie`

## Vraag

- **Gebruiker:** projectleider en functioneel beheerder SWF
- **Vraag:** "Ik wil de SWF-installatie vullen met de rijkere data uit mijn lokale D-OmniTwin-database, via de laad-API en herhaalbaar, zonder open data of demodata mee te kopiëren."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-init-indicatoren:laden`, `dataset:swf-init-waarnemingen:laden`

Aanname A1 van https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/222: de eerste vulling bij SWF komt uit de lokale D-OmniTwin-database van de projectleider. Die komt als dump (`pg_dump -Fc`, niet in git) en wordt **niet** teruggezet. Besluit van de projectleiding (04-10-2026): de data is openbaar, en wat niet online te downloaden is, staat als bestand bij de use case waar het hoort.

## Waar de data uit de dump terechtkomt

| Uit de lokale database | Waar | Hoe |
|---|---|---|
| Welstandsgebieden × buurt (756 vlakken) | [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), `swf-gebied-welstand-buurt` | bestand in git (`data/welstandsgebieden.gpkg`, 4,9 MB) |
| Volledig Kompas (247 plekken, 241 indicatoren) | [swf-kompasprofiel](../swf-kompasprofiel/README.md), `swf-kompas-volledig` | bestand in git (63 kB), beheerroute |
| Externe kaartlagen (8 WFS/WMS) | [swf-kaartlagen](../swf-kaartlagen/README.md), `swf-laag-extern` | bestand in git (5 kB), beheerroute |
| Kadaster BAG/BAG (30.228), RVO EP-Online en berekend (5.248), OpenStreetMap (2.475) | **deze use case**, `swf-init-waarnemingen` | via `SWF_EXPORT_DIR` (niet in git): online te halen, maar nog geen adapter |
| Waarden uit de SWF-gebiedsmonitor (10.365) | deze use case | via `SWF_EXPORT_DIR`; een deelverzameling van de monitorexport ([swf-basismonitor-waarden](../swf-basismonitor-waarden/README.md), [swf-klimaatmonitor](../swf-klimaatmonitor/README.md): 43.253 waarden), dus geen bestand in git |
| Definities die nog nergens vandaan komen (1: *Beperking*) | deze use case, `swf-init-indicatoren` | via `SWF_EXPORT_DIR` |
| CBS, Kerncijfers 2023, RIVM (200.240) | niet | open data: [cbs-kerncijfers](../cbs-kerncijfers/README.md) en [rivm-gezondheidsmonitor](../rivm-gezondheidsmonitor/README.md) downloaden zelf |
| Waarden zonder bron (4.931), op provincies (5), buiten Fryslân (263.524), demodata (0) | niet | niet herleidbaar of buiten de installatie |
| Kompas: extra onderdelen, tags, scoringsregels; lokale laag *Omgevingsvisie SWF*; system prompts, chat-scenario's, kleurschema's | niet | nog geen route, of een eigen route (stuurdata, swf-kaartlagen) |

**Keuze BAG, EP-Online en OpenStreetMap.** Die zijn online te halen, dus niet in git. Er is nog geen adapter (BAG en OpenStreetMap: per buurt berekend; EP-Online: API-sleutel). Tot die er is, gaan ze mee via deze use case uit een export (`SWF_EXPORT_DIR`), zodat de SWF-installatie ze nu al heeft voor heel Fryslân (de sample heeft ze voor 13 buurten). Vervolg: een adapter per bron, dan vervalt dat deel van deze use case.

Deze use case is daarmee het dunne pad "vul aan uit een nieuwe dump". Zonder `SWF_EXPORT_DIR` doet hij niets; de bestanden in git (welstand, Kompas, kaartlagen) laden hun eigen use cases.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-init-indicatoren`](datasets/swf-init-indicatoren.json) | laden | definities | datapackage | `$SWF_EXPORT_DIR/indicatoren.csv` | open | onbekend (navragen) | `dataset:swf-init-indicatoren:laden` |
| [`swf-init-waarnemingen`](datasets/swf-init-waarnemingen.json) | laden | waarnemingen | datapackage | `$SWF_EXPORT_DIR/gebied_data.csv` | open | per bron: BAG (Kadaster, CC0), RVO EP-Online (te bevestigen), OpenStreetMap (ODbL, © OpenStreetMap-bijdragers), SWF-gebiedsmonitor (gemeente) | `dataset:swf-init-waarnemingen:laden` |

Herkomst: de lokale D-OmniTwin-database van de projectleider (dump van 04-10-2026), openbaar volgens besluit van de projectleiding.

**Bewerkingen** (declaratief, geteld per reden). Het exportscript laat open data, waarden zonder bron en provincies al weg; de use case houdt dezelfde regels als controle (aantal 0, ook met `--alles`):

| Export | Levering | Regel |
|---|---|---|
| `bron` begint met `CBS`, `Kerncijfers wijken en buurten` of `Gezondheidsmonitor RIVM` | weggelaten (`open-data`) | open data downloadt de eigen use case |
| `bron` leeg | weggelaten (`bron-onbekend`) | niet herleidbaar |
| buurtcode niet in de CBS-buurten 2024 binnen Fryslân (zelfde bron als `cbs-gebied-buurten`, `koppel` + `binnen`) | weggelaten (`gebied-onbekend`, 1.587) | anders keurt de laad-API de hele levering af |
| welstand-id `728` | `WS728` | `code_prefix` van het gebiedstype welstand |
| geen `n` | `n` leeg | `bron-onderdrukt`; de drempel blijft in de ETL (A7) |
| status `A` | `O` | A = Actueel (A2); de lokale database kent geen `A` |

**Overlap** (A6): de nieuwste bronpeildatum wint; zonder `dct:modified` is dat de datum van ontvangst. De initialisatie wint dus van eerdere leveringen (bijv. `sample-open-zonder-adapter`, ook de DEMODATA van Bolsward-Zuidoost) en verliest van latere. De andere waarde staat in `andere_bronnen`.

## Stappen

Alles op de server van de installatie, in de map met `docker-compose.yml`. De dump bevat ook data die niet meegaat: buiten de repo houden en na afloop opruimen.

1. **Dump herstellen** in een tijdelijke database (zelfde image als de installatie):
   ```bash
   docker run -d --name swfdump -e POSTGRES_USER=omnitwin_user -e POSTGRES_DB=swfbron \
     -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" d-omnitwin-postgres
   docker cp omnitwin_swf_data.dump swfdump:/tmp/swf.dump
   docker exec swfdump pg_restore -U omnitwin_user -d swfbron --no-owner --no-privileges /tmp/swf.dump
   ```
2. **Export maken** met [`scripts/beheer/swf_export.py`](../../scripts/beheer/swf_export.py) in de backend-image (psycopg2, fiona), naast de tijdelijke database. `--uit` is de map voor deze use case; `--repo` werkt ook de bestanden in git bij (welstand, Kompas, kaartlagen; daarna een PR):
   ```bash
   docker run --rm --network container:swfdump -e PGHOST=localhost -e PGUSER=omnitwin_user -e PGDATABASE=swfbron \
     -v "$PWD:/app" -v "$SWF_DUMP_DIR:/monitor:ro" -v /pad/naar/swf-export:/uit \
     --entrypoint python d-omnitwin-backend /app/scripts/beheer/swf_export.py --uit /uit [--repo] \
     --dump-datum 2026-10-04 --monitor-definities /monitor/output/api_backup_dump.json
   ```
   Uitvoer: `gebied_data.csv` (49.903 regels, 6,6 MB), `indicatoren.csv`, `export.json` (aantallen, controlesommen).
3. **Lokaal controleren**: `SWF_EXPORT_DIR=/pad/naar/swf-export python -m omnitwin.usecases controleer swf-initialisatie`. Wijken de aantallen af (andere dump), pas ze dan aan in `usecase.json` en hier.
4. **Installeren**, in-process; `swf-definities` heeft `SWF_DUMP_DIR` nodig:
   ```bash
   docker compose run --rm -v /pad/naar/swf-export:/swf-export:ro -v "$SWF_DUMP_DIR:/swf-dump:ro" \
     -e SWF_EXPORT_DIR=/swf-export -e SWF_DUMP_DIR=/swf-dump \
     db-init python -m omnitwin.usecases installeer swf-initialisatie --inproces
   ```
   Of via HTTP met de eenmalige machineclient `etl-initialisatie` (`dataset:swf-init-indicatoren:laden`, `dataset:swf-init-waarnemingen:laden`).
5. **Opruimen:** `docker rm -f swfdump`, dump en export verwijderen, de client `etl-initialisatie` intrekken.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-init-indicatoren`, resource `indicatoren` | gelijk 1 |
| 2 | aantal | `swf-init-indicatoren`, resource `relaties` | gelijk 0 |
| 3 | bewerking | `swf-init-indicatoren`: `status: A → O` | gelijk 0 |
| 4 | aantal | `swf-init-waarnemingen` | gelijk 48.316 |
| 5–9 | bewerking | `swf-init-waarnemingen`: `open-data`, `bron-onbekend`, `gebiedstype-provincie`, `demodata` 0; `gebied-onbekend` 1.587 | zoals genoemd |
| 10 | api | `GET /api/data/v1/gebied_data?gebied_id=eq.BU19000002&select=indicator_uuid,bron,andere_bronnen` | ≥ 1 resultaat |
| 11 | idempotent | `swf-init-waarnemingen` twee keer leveren | zelfde versie |
| 12 | viewer | *Aantal energielabels* op de kaart, Bolsward | waarden voor alle buurten |
| 13–17 | recht | beheerder registreert; `etl-initialisatie` levert alleen de eigen datasets en registreert niet; `lezer` levert niet | toegestaan / 403 |

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-initialisatie`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- De aantallen gelden voor de dump van 04-10-2026; een nieuwe export: eerst `controleer`, dan de aantallen bijwerken.
- BAG, EP-Online en OpenStreetMap staan niet in git (online te halen) en hebben nog geen adapter: zonder `SWF_EXPORT_DIR` heeft een installatie ze alleen voor de 13 testbuurten (sample). Vervolg: adapters.
- Open data op wijk- en gemeenteniveau en *Huisarts* (45.239 waarden in de dump) laden de open-data-use cases nog niet; vervolg: cbs-kerncijfers en rivm-gezondheidsmonitor uitbreiden.
- Definities die al uit swf-definities of de stuurdata komen, worden niet overschreven; de lokale database wijkt af bij 100 omschrijvingen, 40 eenheden, 19 score_types, 8 statussen en 7 namen. Keuze bij de projectleider.
- De publicatie van de waarden duurt ±5,5 minuut, vrijwel geheel in `laden.herbouw_gebied_data()` (voorrang, A6).
- De bron van de monitorwaarden is de bestandsnaam van de push (`<uuid>_d_cbs_buurten.json`), zoals in de lokale database.
