# Demodata naar open data

**Issue:** https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/236 · **RFC:** https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/182 ("de sample wordt overbodig")

De demo-use cases (`hittestress`, `energiearmoede`, `brede-welvaart`, `sociale-cohesie`, `beleidsadviseur-swf`) haalden hun waarden uit `init_data/sample/2_brondata/sample_indicatoren.csv` en laadden die direct in de database. Een groot deel daarvan is open data die we bij de installatie kunnen downloaden. Dit document is de inventaris per indicator en beschrijft wat er nu open, intern of nog zonder adapter is.

## Uitgangspunten

- **Open data staat niet in git.** De use case beschrijft de bron (DCAT: `dct:source`, `dct:license`), een kernadapter downloadt hem bij de installatie, met cache in `$DATA_CACHE` (in Docker het volume `bron-cache`).
- **Alles via de laadstraat.** Een verse installatie (`LOAD_SAMPLE_DATA=true`) draait `python -m omnitwin.usecases installeer --alle --inproces`: dezelfde validatie, versies en DCAT als de laad-API, in-process (backend en Keycloak draaien dan nog niet). Geen directe vulling van `gebied_data` meer.
- **Demodata is gemarkeerd.** Wat (nog) niet open is, blijft als demodata in `init_data/sample/`, als plaatsvervanger voor de interne bron: `dct:type` `demodata` in de DCAT van de dataset, en de `bron` van elke waarde begint met `DEMODATA`. Dat is zichtbaar in de API (`/api/data/v1/gebied_data?...&select=bron`) en overal waar de bron van een waarde getoond wordt.
- **Echte interne data blijft buiten git.** Een variant `intern` met `als_beschikbaar` laadt de echte interne bron als die lokaal beschikbaar is (`SWF_DUMP_DIR`); zonder die map valt de dataset terug op de demodata.
- **Stuurdata blijft.** Indicatordefinities (nu in `db/stuurdata/indicatoren.csv`, plus het CBS-recept) en het Kompas horen bij de software.

## Telling

**Sample (vóór deze wijziging): 56 indicatoren, 728 waarden, 13 buurten.**

| Categorie | Indicatoren | Waarden in de oude sample | Nu |
|---|---:|---:|---|
| Al uit `cbs-kerncijfers` (dubbel: Huisarts = Afstand tot huisarts) | 1 | 13 | vervallen; `cbs-kerncijfers` levert *Afstand tot huisarts* 2019-2026 |
| Open, **nieuwe adapter gebouwd** (`cbs-statline`): RIVM Gezondheidsmonitor | 11 | 143 | `rivm-gezondheidsmonitor`, heel Fryslân, 2012-2024 (37.056 waarden) |
| Open, **nieuwe adapter gebouwd** (`cbs-statline`): Politie | 4 | 52 | `politie-misdrijven`, heel Fryslân, 2019-2025 (26.068 waarden) |
| Open, **adapter ontbreekt nog**: Kadaster BAG (per buurt berekend) | 21 | 273 | in de sample, use case `sample-bronbibliotheek` |
| Open met API-sleutel, **adapter ontbreekt nog**: RVO EP-Online | 6 | 78 | in de sample, `sample-bronbibliotheek` |
| Open, **adapter ontbreekt nog**: OpenStreetMap (OV-haltes) | 5 | 65 | in de sample, `sample-bronbibliotheek` |
| **Niet open (intern)**: SWF-gebiedsmonitor (klimaat, onderwijs) | 8 | 104 | DEMODATA in de sample, `sample-bronbibliotheek`; variant `intern` met `SWF_DUMP_DIR` |
| **Totaal** | **56** | **728** | sample nu 40 indicatoren, 520 waarden |

Van de 728 waarden waren er 56 demodata (Bolsward-Zuidoost, één per indicator); daarvan zijn er nu 15 echt (RIVM en Politie) en vervalt er 1 (Huisarts). Bij de 32 open indicatoren zonder adapter is Bolsward-Zuidoost nog demodata (gemarkeerd), bij de 8 interne indicatoren is alles demodata.

**Demo-use cases: 26 indicatoren** (`data.indicatoren`, plus *Eenpersoonshuishoudens (%)*).

| Categorie | Indicatoren | Welke |
|---|---:|---|
| Uit `cbs-kerncijfers` (bestond al) | 11 | 65+ jaar, 65+ jaar (%), Huishoudens met laag inkomen, Inkomen per inwoner, Netto arbeidsparticipatie, Eenpersoonshuishoudens, Eenpersoonshuishoudens (%), Afstand tot huisarts, Afstand tot grote supermarkt, Woningvoorraad, Participatiewet totaal |
| Uit `cbs-kerncijfers`, kleine uitbreiding van het recept | 1 | 80 jaar of ouder (%) (2026, `k_80JaarOfOuder_13`) |
| Nieuwe adapter `cbs-statline` (RIVM) | 6 | Ervaren gezondheid, Moeite met rondkomen, Eenzaamheid, Vrijwilliger, Mantelzorger (Ervaren gezondheid telt in twee use cases) |
| Nieuwe adapter `wcs-zonaal` (RIVM Atlas Natuurlijk Kapitaal) | 2 | Boomkroonbedekking, Stedelijk hitte-eiland effect (vervangt `usecases/hittestress/maak_data.py`) |
| Open, adapter ontbreekt (sample) | 4 | Gemiddeld energielabel, Woningen gebouwd vóór 1945 (BAG), Diversiteit Functies (Simpson Index), Aantal OV-haltes (totaal) |
| Intern, DEMODATA (sample) | 3 | Afstand tot koele plek, Oppervlak groen per inwoner, Verhouding oppervlakte water / verharding |

## Per demo-use case

| Use case | Afhankelijk van | Eigen datasets | Open | Open, adapter ontbreekt | Intern (demodata) |
|---|---|---|---|---|---|
| `hittestress` | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek | `rivm-boomkroon-buurten`, `rivm-hitte-eiland-buurten` (`wcs-zonaal`) | 65+ jaar, 65+ jaar (%), 80 jaar of ouder (%), Ervaren gezondheid, Boomkroonbedekking, Stedelijk hitte-eiland effect | – | Afstand tot koele plek, Oppervlak groen per inwoner, Verhouding water/verharding |
| `energiearmoede` | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek | – | Huishoudens met laag inkomen, Moeite met rondkomen | Gemiddeld energielabel (EP-Online), Woningen vóór 1945 (BAG) | – |
| `brede-welvaart` | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek | – | Inkomen per inwoner, Netto arbeidsparticipatie, Ervaren gezondheid | Diversiteit Functies (BAG) | – |
| `sociale-cohesie` | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor | – | Eenzaamheid, Vrijwilliger, Mantelzorger, Eenpersoonshuishoudens (+ %) | – | – |
| `beleidsadviseur-swf` | cbs-gebiedsindelingen, cbs-kerncijfers, sample-bronbibliotheek | – | Afstand tot huisarts, Afstand tot grote supermarkt, Woningvoorraad, Participatiewet totaal | Aantal OV-haltes (OpenStreetMap) | – |

`sociale-cohesie` draait daarmee volledig op open data; `hittestress` op 6 van de 9 indicatoren.

## Gebouwde kernadapters

| Adapter | Wat | Gebruikt door | Tests |
|---|---|---|---|
| `cbs-statline` (`src/omnitwin/bronadapters/statline.py`) | elke StatLine-tabel (CBS `opendata.cbs.nl`, derden op `dataderden.cbs.nl`: RIVM, Politie) via de ODataFeed-ingang (pagineert; de ODataApi weigert meer dan 10.000 regels), uitgepakt per kolom; filter op gemeenten, dimensies en jaren | `rivm-gezondheidsmonitor`, `politie-misdrijven` | `tests/test_bronadapters.py` (filter, uitpakken, paginering, cache, foute key/url, geen netwerk) |
| `wcs-zonaal` (`src/omnitwin/bronadapters/raster.py`) | gemiddelde van een WCS 2.0.1-raster (GeoTIFF, EPSG:28992) per gebied; de gebieden zijn zelf een bron-blok (hier de CBS-buurten van PDOK) | `hittestress` | `tests/test_bronadapters.py` (zonaal gemiddelde met nodata, georeferentie, allowlist) |

Allowlist: `dataderden.cbs.nl` toegevoegd. De uitzondering voor code in een use case (`hittestress/maak_data.py`) is vervallen.

## Wat nog niet open is of nog geen adapter heeft (vervolg)

| Bron | Indicatoren | Waarom nog niet | Voorstel |
|---|---|---|---|
| Kadaster BAG (PDOK WFS/OGC API) | 21 (gebruiksfuncties, bouwjaren, woonoppervlakte, Simpson-index, % vóór 1945) | open, maar de waarden zijn per buurt berekend (tellen en middelen van verblijfsobjecten en panden); daarvoor is een ruimtelijke aggregatie nodig (bewerking `per_gebied`: punt-in-vlak, tellen/gemiddelde/aandeel) | kernbewerking `per_gebied` + `wfs` op `bag:verblijfsobject`; definities van de afgeleide indicatoren (Simpson) vastleggen |
| RVO EP-Online | 6 (aantallen labels, gemiddeld label, dekking) | open data, maar alleen via een API-sleutel (gratis aan te vragen); licentie op data.overheid.nl "geen open licentie" (te bevestigen) | adapter met sleutel uit de omgeving (nooit in git), daarna dezelfde `per_gebied`-aggregatie |
| OpenStreetMap (Overpass API) | 5 (OV-haltes) | open (ODbL), aggregatie per buurt nodig; ODbL share-alike voor afgeleide databases | adapter `overpass` + `per_gebied`; naamsvermelding in de DCAT |
| SWF-gebiedsmonitor (intern) | 8 (afstand tot koele plek, groen per inwoner, water/verharding, grondwaterstand GLG en verandering, hemelwater, definitief energielabel, achterstand leerlingen) | interne uploads in de huidige gebiedsmonitor; deels afgeleid van open bronnen (Klimaateffectatlas, CBS, DUO), maar herkomst en methode niet herleidbaar | blijft demodata met variant `intern` (`SWF_DUMP_DIR`); per indicator de open bron en methode uitzoeken (o.a. Klimaateffectatlas: voor Fryslân geen WCS of download) |
| Gevoelstemperatuur (Klimaateffectatlas) | (hittestress, ontbreekt) | voor Fryslân geen open download of WCS | blijft vervangen door het stedelijk hitte-eiland effect (RIVM) |

## Demodata: herkenbaar en vervangbaar

- Dataset `sample-intern-demodata` (`usecases/sample-bronbibliotheek/datasets/`): `dct:type` `demodata`, `dct:description` "Demodata als plaatsvervanger voor de interne bron 'SWF-gebiedsmonitor' …, niet de echte waarden", `prov:wasDerivedFrom` met de functionele naam van de interne bron, licentie onbekend.
- Per waarde: `bron` = `DEMODATA: plaatsvervanger voor de interne bron SWF-gebiedsmonitor, geen echte cijfers` (of `DEMODATA: gemiddelde van Bolsward-Noord en Bolsward-Noordoost, …` bij Bolsward-Zuidoost). Die tekst komt via de laadstraat in `gebied_data.bron` en is zichtbaar in de data-API en in de viewer waar de bron getoond wordt.
- Variant `intern` (`als_beschikbaar: true`): adapter `swf-dump` op `${SWF_DUMP_DIR}/output/api_data_dump.json`, alleen deze 8 indicatoren op CBS-buurten, met eigen DCAT (`dct:type` `brondata`, toegang `RESTRICTED`). Zonder `SWF_DUMP_DIR` laadt de uitvoerder de demodata. Niet getest met echte data (geen export beschikbaar in deze omgeving).
- De Use Case Specificatie kende geen manier om dit vast te leggen. Toegevoegd (voorstel, formeel een minor): `varianten.<naam>.bron`, `.bewerkingen`, `.beschrijving` en `.als_beschikbaar` (zie de [specificatie, 6.5](../specificaties/usecase/README.md)). Een eigen veld voor de soort data (bijv. `bron.soort: demodata`) is er niet; nu via DCAT `dct:type`.

## Installatie zonder netwerk

Een bron die niet bereikbaar is (geen netwerk, CBS of PDOK plat) wordt *overgeslagen* met een melding; de installatie gaat door. Zonder `cbs-gebiedsindelingen` zijn er geen buurten, en dan keurt de laadstraat de waarden van de andere use cases af (`gebied-onbekend`); ook dat is een melding, geen kapotte installatie. Later opnieuw, met netwerk:

```bash
docker compose run --rm db-init python -m omnitwin.usecases installeer --alle --inproces
```

De downloads staan in de cache (`bron-cache`); een tweede installatie gebruikt die.

## Inventaris per indicator (oude sample)

Bron in de oude sample → open bron, licentie, adapter, status en use case nu. Kolom-key of soort misdrijf tussen haakjes.

| Indicator | Bron in de oude sample | Open bron | Licentie | Adapter | Status | Use case |
|---|---|---|---|---|---|---|
| Bewegen | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`VoldoetAanDeBeweegrichtlijn_40`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Eenzaamheid | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`Eenzaam_25`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Ervaren gezondheid | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`GoedErvarenGezondheid_4`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Gezondheid | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`HoogRisicoAngststoornisOfDepressie_14`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Mantelzorger | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`Mantelzorger_30`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Moeite met rondkomen | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`MoeiteMetRondkomen_32`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Obesitas | `CBS_50150NED` | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`ErnstigOvergewichtObesitas_34`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Overgewicht | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`Overgewicht_33`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Overmatig drinken | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`OvermatigDrinken_37`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Roken | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`RooktTabak_35`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| Vrijwilliger | Gezondheidsmonitor RIVM 2024 | RIVM, GGD en CBS: Gezondheidsmonitor, StatLine 50150NED (`Vrijwilligerswerk_31`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `rivm-gezondheidsmonitor` |
| beschadiging auto's | (leeg) | Politie, StatLine 47018NED (`2.2.1`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `politie-misdrijven` |
| diefstal fiets | (leeg) | Politie, StatLine 47018NED (`1.2.3`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `politie-misdrijven` |
| inbraak auto | (leeg) | Politie, StatLine 47018NED (`1.2.1`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `politie-misdrijven` |
| inbraak woning | (leeg) | Politie, StatLine 47018NED (`1.1.1`) | open, CC BY 4.0 | `cbs-statline` (gebouwd) | open | `politie-misdrijven` |
| Huisarts | `CBS_85984NED` | CBS Kerncijfers 2024 (85984NED), = Afstand tot huisarts | open, CC BY 4.0 | `cbs-odata` (bestaat) | open (dubbel) | `cbs-kerncijfers` |
| Bijeenkomstfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Bouwjaar 1915-1945 | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Bouwjaar 1945-1984 | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Bouwjaar vanaf 1985 | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Bouwjaar voor 1915 | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Celfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Diversiteit Functies (Simpson Index) | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Gemiddeld bouwjaar woningen (BAG) | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Gemiddelde woonoppervlakte (BAG) | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Gezondheidszorgfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Huishoudens (BAG woonfunctie) | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Industriefunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Kantoorfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Logiesfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Onderwijsfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Overige gebruiksfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Percentage woonfunctie (BAG) | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Sportfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Winkelfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Woningen gebouwd vóór 1945 (BAG) | Kadaster BAG Fryslân 2026 | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Woonfunctie | BAG | Kadaster BAG, per buurt berekend | open, PDM 1.0/CC0 | ontbreekt: BAG-aggregatie per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal energielabels | RVO EP-Online 2026-02 | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal energielabels (definitief) | RVO EP-Online 2026-02 | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal energielabels (totaal) | RVO EP-Online 2026-02 | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal energielabels (voorlopig) | RVO EP-Online 2026-02 | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Energielabel coverage | Berekend: EP-Online / BAG Fryslân | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Gemiddeld energielabel | RVO EP-Online 2026-02 | RVO EP-Online, per buurt berekend | open data, API-sleutel nodig; licentie te bevestigen | ontbreekt: EP-Online (met sleutel) | open met sleutel, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal bushaltes | OpenStreetMap / Overpass API 2026 | OpenStreetMap (Overpass), per buurt geteld | open, ODbL 1.0 | ontbreekt: Overpass-telling per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal OV-haltes (totaal) | OpenStreetMap / Overpass API 2026 | OpenStreetMap (Overpass), per buurt geteld | open, ODbL 1.0 | ontbreekt: Overpass-telling per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal tramhaltes | OpenStreetMap / Overpass API 2026 | OpenStreetMap (Overpass), per buurt geteld | open, ODbL 1.0 | ontbreekt: Overpass-telling per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal treinhaltes | OpenStreetMap / Overpass API 2026 | OpenStreetMap (Overpass), per buurt geteld | open, ODbL 1.0 | ontbreekt: Overpass-telling per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Aantal veerboten | OpenStreetMap / Overpass API 2026 | OpenStreetMap (Overpass), per buurt geteld | open, ODbL 1.0 | ontbreekt: Overpass-telling per buurt | open, adapter ontbreekt | `sample-bronbibliotheek` |
| Achterstand leerlingen | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Afstand tot koele plek | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Definitief energielabel | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Gemiddeld Laagste Grondwaterstand | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Oppervlak groen per inwoner | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Verandering GLG nu t.o.v. 2050 | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Verhouding oppervlakte water / verharding | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |
| Verwerken hemelwater exc. schade | upload `<uuid>_d_cbs_buurten.json` | SWF-gebiedsmonitor (upload, klimaatmonitor/onderwijs) | intern, niet openbaar | `swf-dump` (bestaat) | intern (demodata-plaatsvervanger) | `sample-bronbibliotheek` |

Opmerkingen:

- **Gezondheid** is in de bron *Hoog risico angststoornis of depressie* (`HoogRisicoAngststoornisOfDepressie_14`); de naam en de richting (hoger is beter) in de definities kloppen niet. Vervolg: definitie corrigeren.
- **beschadiging auto's** is in de bron *Vernieling cq. zaakbeschadiging* (2.2.1), niet alleen auto's; **inbraak auto** is *Diefstal uit/vanaf motorvoertuigen* (1.2.1). Zo stonden de waarden in de oude sample; het Kompas noemt bij *inbraak auto* 1.2.2.
- **Obesitas** week in de oude sample 0,1 af van de huidige tabel (RIVM heeft 50150NED op 18-11-2025 verbeterd).
- **Huisarts** (85984NED, 2024) is dezelfde CBS-variabele als *Afstand tot huisarts* uit `cbs-kerncijfers`; de definitie blijft (Kompas), de waarden vervallen. Vervolg: Kompas naar *Afstand tot huisarts* laten wijzen.

Indicatoren van de demo-use cases buiten de sample: zie [Telling](#telling). De CBS-indicatoren staan in het recept [`init_data/cbs/datapackage.json`](../../init_data/cbs/datapackage.json) (zie [CBS Kerncijfers](cbs_kerncijfers.md)).
