# CBS Kerncijfers wijken en buurten: alle jaargangen (#159)

De CBS Kerncijfers wijken en buurten van alle jaargangen vanaf 2019, voor alle buurten in Fryslân, gemapt op de indicatoren van D-OmniTwin.

**Principe: wat bij CBS te downloaden is, staat niet in git.** In [`init_data/cbs/`](../../init_data/cbs/) staat alleen het recept: tabel-ID's per jaar, de kolom-mapping, licentie en codecontrole. De data wordt gedownload op het moment dat een use case geladen wordt, en gecachet. Daarmee werken trends (tijdslider in het Kompas, "Trending (5j+)" in het dashboard).

## Waarom

Tot #159 kwamen de Kerncijfers uit één tabel, `85039NED`, met het label "Kerncijfers wijken en buurten 2023". Volgens CBS (`TableInfos.Period`) is dat de tabel van **2021**. Bolsward-Noord had in de app 1.770 inwoners "in 2023"; de tabel van 2023 geeft 1.920. Daarnaast deelde de afgeleide indicator `65+ jaar (%)` een teller uit 2025 door een noemer uit "2023" (= 2021).

## Recept en cache

| Waar | Inhoud |
|---------|--------|
| `init_data/cbs/datapackage.json` (git) | Bron, licentie, tabellen per jaar, mapping per indicator, codecontrole en de verwachte omvang van een volledige download. |
| `init_data/scripts/download_cbs_kerncijfers.py` (git) | De mapping en de download (alleen `opendata.cbs.nl`). |
| `$DATA_CACHE/cbs/` (niet in git) | De gedownloade reeksen: per set buurten, of `kerncijfers_fryslan.csv` (± 187.000 waarden) na `--alle`. In Docker het volume `bron-cache`. |

De indicatordefinities (namen, UUID's, eenheid, richting) horen bij de stuurdata en worden altijd geladen (`load_sample.py --stap definities`), ook zonder download.

### Tabellen

Elk ID is bij elke download gecontroleerd via `TableInfos`: `Period` moet het peiljaar zijn.

| Peiljaar | Tabel |
|----------|-------|
| 2019 | `84583NED` |
| 2020 | `84799NED` |
| 2021 | `85039NED` |
| 2022 | `85318NED` |
| 2023 | `85618NED` |
| 2024 | `85984NED` |
| 2025 | `86165NED` |
| 2026 | `86358NED` |

Per waarde:
- `jaar` = peiljaar van de tabel;
- `bron` = `CBS Kerncijfers wijken en buurten <jaar> (<tabel>)`;
- `gebied_data.metadata.bron_tabel` = het tabel-ID (gezet door `laad_cbs.py`).

CBS vult een tabel na publicatie nog aan, bijvoorbeeld met inkomen en arbeid. Recente jaren hebben daardoor nog niet alle variabelen; 2026 bevat vooral bevolking en huishoudens.

### Mapping

Eén mapping in het script (`MAPPING`): per indicator en per jaar de CBS-kolom. Kolomnamen verschillen per jaar door het volgnummer, bijvoorbeeld `Koopwoningen_40` in 2022 en `Koopwoningen_47` in 2024. De indicatornamen en UUID's zijn die van de sample, dus er komen geen dubbele indicatoren bij: het zijn dezelfde indicatoren, met meer jaren.

| Indicator | Jaren | Opmerking |
|-----------|-------|-----------|
| Inwoners, 0-15, 15-25, 25-45, 45-65, 65+ jaar | 2019-2026 | 65+ in 2026 = 65-80 + 80+ (som, zelfde tabel) |
| 65+ jaar (%) | 2019-2026 | afgeleid: 65+ jaar ÷ Inwoners, **zelfde jaar** |
| Huishoudens totaal, Eenpersoonshuishoudens, met/zonder kind, Bevolkingsdichtheid | 2019-2026 | |
| Woningvoorraad, Gemiddelde WOZ-waarde, Koopwoningen, Woningcorporatie bezit, Particulier huurbezit | 2019-2025 | percentages zoals CBS ze geeft |
| Netto arbeidsparticipatie, Percentage werknemers, Percentage zelfstandigen, Inkomen per inwoner | 2019-2024 | |
| Huishoudens met laag inkomen | 2019-2023 | na 2023 niet meer in de Kerncijfers |
| Opleidingsniveau laag/middelbaar/hoog | 2019-2024 | vanaf 2023 heet het "basisonderwijs/vmbo/mbo1", "havo/vwo/mbo2-4", "hbo/wo"; mogelijke breuk in de reeks |
| Participatiewet totaal | 2019-2025 | CBS: personen met bijstand |
| Personenauto's per huishouden / naar oppervlakte | 2019-2025 | |
| Afstand tot huisarts, grote supermarkt, kinderdagverblijf, school | 2019-2025 | |

De indicator `Huisarts` (een tweede indicator voor dezelfde CBS-kolom) zit niet in het pakket; die houdt zijn waarde uit 2024 in de sample.

### Buurtcodes per jaar

Buurtcodes veranderen per jaar. Het pakket bevat alleen codes die in de geometrie van 2024 bestaan (`init_data/fryslan/buurten_fryslan.geojson`). Wat wegvalt, per jaar en gemeente (ook in `datapackage.json`, onder `codecontrole`):

| Peiljaar | Weggevallen codes | Waarden |
|----------|-------------------|---------|
| 2019-2021 | Smallingerland 31 | ± 910 per jaar |
| 2022-2023 | Smallingerland 31, Leeuwarden 3 | ± 930 per jaar |
| 2024 | 0 | 0 |
| 2025-2026 | Leeuwarden 5 (nieuwe buurten na 2024) | 68 / 54 |

Smallingerland heeft per 2024 een nieuwe buurtindeling: de 61 buurten van Smallingerland in de geometrie 2024 hebben geen waarden vóór 2024. De andere 870 buurten hebben een reeks vanaf 2019 (één vanaf 2020). Omrekenen tussen indelingen is een vervolgstap (#159, "later"). Een code die in beide jaren bestaat, kan een iets andere grens hebben; dat controleert het pakket niet.

## Laden

`laad_cbs.py` haalt de reeksen voor de gebieden in de database uit de cache, of downloadt ze bij CBS (enkele seconden voor de 13 use-casebuurten) en vult de cache. Zonder internet en zonder cache: een waarschuwing, de rest van de installatie gaat door. Voor een installatie zonder internet: vul de cache op een machine met internet (`download_cbs_kerncijfers.py --alle`) en kopieer `$DATA_CACHE/cbs` naar het volume.

| Wanneer | Wat | Hoe |
|---------|-----|-----|
| `db-init`, `LOAD_SAMPLE_DATA=true` | de reeksen voor de gebieden in de database (de 13 use-casebuurten) | `laad_usecase.py --alle`, daarna `laad_cbs.py` (download of cache) |
| expliciet, heel Fryslân | 931 buurten, alle jaren | `docker compose run --rm db-init python init_data/scripts/seed_fryslan.py --stap alle` (stap `cbs`) |
| alleen de CBS-reeksen | voor alle of genoemde gebieden in de database | `docker compose run --rm db-init python init_data/scripts/laad_cbs.py [BU...]` |

`laad_cbs.py` is idempotent. Het koppelt op UUID (anders op naam), schrijft `metadata.bron_tabel`, en verwijdert oude rijen met het verkeerde label "Kerncijfers wijken en buurten 2023".

De sample (`init_data/sample/2_brondata/sample_indicatoren.csv`) bevat voor zijn 13 buurten dezelfde reeks; de unittest controleert dat. Bolsward-Zuidoost had demodata; voor de CBS-indicatoren zijn dat nu echte waarden.

Afgeleide indicatoren in use cases (`laad_usecase.py`) nemen teller en noemer uit **hetzelfde jaar**.

## Bijwerken

```bash
python init_data/scripts/download_cbs_kerncijfers.py --controle          # tabellen (Period) en kolommen controleren
python init_data/scripts/download_cbs_kerncijfers.py --alle              # heel Fryslân naar de cache, recept (datapackage.json) bijwerken
python init_data/scripts/download_cbs_kerncijfers.py BU19000001 ...      # alleen deze buurten naar de cache
```

Nieuwe jaargang: voeg het tabel-ID toe aan `TABELLEN` en de kolommen aan `MAPPING`. `--controle` faalt als `Period` of een kolom niet klopt; de unittest faalt als een jaar zonder kolom niet in `NIET_GEPUBLICEERD` staat.

Let op: filter in CBS OData op de dimensie `WijkenEnBuurten`. Een `$filter` op `Codering_3` negeert CBS stil, en dan komt heel Nederland mee. Daardoor was de oude `indicatorwaarden_fryslan.csv` 29 MB.

## Tests

- `tests/test_cbs_kerncijfers.py`: mapping per jaar compleet, codes in de geometrie 2024, jaar = peiljaar, geen dubbele UUID's, sample gelijk aan het pakket, `65+ jaar (%)` uit hetzelfde jaar.
- `tests/integration/test_cbs_trends.py`: de history-endpoint geeft ≥ 3 jaren voor Inwoners en 65+ jaar (%) in Bolsward-Noord, 2023 = 1.920 (`85618NED`), en "Trending (5j+)" > 0.

## Licentie

Centraal Bureau voor de Statistiek (CBS), Kerncijfers wijken en buurten 2019-2026, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Zie [`NOTICE.md`](../../NOTICE.md).
