# D-OmniTwin — Sample (wat nog niet open is of nog geen adapter heeft)

Sinds https://github.com/TLaan/D-OmniTwin/issues/236 komt alles wat open en te downloaden is uit de use cases met een kernadapter: CBS Kerncijfers (`cbs-kerncijfers`), RIVM Gezondheidsmonitor (`rivm-gezondheidsmonitor`), Politie (`politie-misdrijven`), RIVM-rasters (`hittestress`) en de buurtgrenzen (`cbs-gebiedsindelingen`). Deze map bevat alleen nog wat **niet open** is, of **open maar nog zonder adapter**, voor 13 buurten in Súdwest-Fryslân. De use case [`sample-bronbibliotheek`](../../usecases/sample-bronbibliotheek/README.md) laadt het via de laad-API, gemarkeerd. De inventaris per indicator staat in [demodata naar open data](../../docs/3-data-engineering/demodata-naar-open-data.md).

## Inhoud

```
init_data/sample/
├── README.md                           # Deze documentatie
├── datapackage.json                    # Frictionless Data Package: resources, schema, licenties, herkomst
├── KWALITEIT.md                        # Datakwaliteitsbevindingen
└── 2_brondata/
    ├── sample_buurten.geojson          # 13 buurtgrenzen (WGS84); alleen nog voor load_sample.py --stap buurten (offline/test)
    └── sample_indicatoren.csv          # 40 indicatoren x 13 buurten = 520 waarden
```

| Groep | Indicatoren | Status | Dataset |
|---|---:|---|---|
| Kadaster BAG, per buurt berekend (gebruiksfuncties, bouwjaren, woonoppervlakte) | 21 | open, adapter ontbreekt | `sample-open-zonder-adapter` |
| RVO EP-Online, per buurt berekend (energielabels) | 6 | open met API-sleutel, adapter ontbreekt | `sample-open-zonder-adapter` |
| OpenStreetMap, per buurt geteld (OV-haltes) | 5 | open (ODbL), adapter ontbreekt | `sample-open-zonder-adapter` |
| SWF-gebiedsmonitor (klimaat, onderwijs) | 8 | **intern**: DEMODATA als plaatsvervanger | `sample-intern-demodata` (variant `intern` met `SWF_DUMP_DIR`) |

## Demodata: gemarkeerd

- De kolom `bron` begint met `DEMODATA` bij elke waarde die geen echt cijfer is: alle waarden van de 8 interne indicatoren (plaatsvervanger voor de SWF-gebiedsmonitor) en de waarden van Bolsward-Zuidoost (`BU19000002`) bij BAG, EP-Online en OpenStreetMap (gemiddelde van Bolsward-Noord en Bolsward-Noordoost). Die tekst komt via de laadstraat in de bron van de waarde in D-OmniTwin; de assistent meldt het ook.
- De dataset `sample-intern-demodata` heeft in de DCAT `dct:type` `demodata`.
- Met `SWF_DUMP_DIR` (export van de huidige gebiedsmonitor) laadt de use case de echte interne waarden in plaats van de demodata. Die echte data komt nooit in git.

## Laden

Een verse installatie met `LOAD_SAMPLE_DATA=true` laadt alle use cases (`python -m omnitwin.usecases installeer --alle --inproces` in `db-init`), ook deze. Handmatig:

```bash
python -m omnitwin.usecases controleer sample-bronbibliotheek     # zonder stack
python -m omnitwin.usecases installeer sample-bronbibliotheek     # tegen een draaiende installatie
```

De indicatordefinities (naam, eenheid, richting, herkomst) staan niet meer hier maar in de stuurdata: [`db/stuurdata/indicatoren.csv`](../../db/stuurdata/indicatoren.csv) (`load_sample.py --stap definities`). `load_sample.py --stap alle` laadt deze map nog direct in de database (zonder laadstraat), voor offline testen.

## Datapakket (Frictionless)

`datapackage.json` beschrijft de bestanden als resources, met licentie per resource en een Table Schema voor `sample_indicatoren.csv`. Valideren (vanuit de repo-root):

```bash
docker run --rm -v "$PWD":/data -w /data python:3.11-slim \
  sh -c "pip install -q frictionless && frictionless validate init_data/sample/datapackage.json"
```

Op Windows (Git Bash) met `MSYS_NO_PATHCONV=1` en `"$(pwd -W)"` in plaats van `"$PWD"`.

## Bronvermelding en licenties

- **Kadaster BAG** via PDOK: Public Domain Mark 1.0 / CC0 (te bevestigen, zie `NOTICE.md`).
- **RVO EP-Online**: open data met API-sleutel; licentie te bevestigen (zie `NOTICE.md`).
- **OpenStreetMap**: ODbL 1.0, "© OpenStreetMap-bijdragers"; de OSM-afgeleide regels vallen onder de ODbL.
- **Buurtgrenzen** (`sample_buurten.geojson`): CBS via PDOK, CC BY 4.0.
- **Demodata**: geen bron, geen licentie; niet gebruiken als echte cijfers.
