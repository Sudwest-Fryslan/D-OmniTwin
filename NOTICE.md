# 🔔 Third-Party Notices - D-OmniTwin

Dit bestand bevat de vermeldingen van de belangrijkste bibliotheken en frameworks die worden gebruikt in de D-OmniTwin applicatie, conform de vereisten van de EUPL 1.2 licentie.

## 🐍 Backend (Python)
- **FastAPI**: [MIT License](https://github.com/fastapi/fastapi/blob/master/LICENSE)
- **Uvicorn**: [BSD 3-Clause License](https://github.com/encode/uvicorn/blob/master/LICENSE.md)
- **PostgreSQL / PostGIS / pgvector**: [PostgreSQL License](https://www.postgresql.org/about/licence/) / [GPL v2+](https://postgis.net/docs/manual-3.4/postgis_introduction.html#idm29) / [PostgreSQL License](https://github.com/pgvector/pgvector/blob/master/LICENSE)
- **Pandas**: [BSD 3-Clause License](https://github.com/pandas-dev/pandas/blob/main/LICENSE)
- **Pydantic**: [MIT License](https://github.com/pydantic/pydantic/blob/main/LICENSE)
- **SQLAlchemy**: [MIT License](https://github.com/sqlalchemy/sqlalchemy/blob/master/LICENSE)

## 🌐 API Gateway & Microservices
- **Traefik**: [MIT License](https://github.com/traefik/traefik/blob/master/LICENSE.md)
- **PostgREST**: [MIT License](https://github.com/PostgREST/postgrest/blob/main/LICENSE)
- **pg_featureserv**: [Apache License 2.0](https://github.com/CrunchyData/pg_featureserv/blob/master/LICENSE.md)

## 🎨 Frontend (JavaScript/React)
MapLibre GL JS, deck.gl, D3.js, Chart.js en Inter worden zelf gehost in `static/vendor/`, met het licentiebestand per pakket; zie `static/vendor/README.md`.

- **MapLibre GL JS**: [BSD 3-Clause License](https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt)
- **Deck.gl**: [MIT License](https://github.com/visgl/deck.gl/blob/master/LICENSE)
- **D3.js**: [ISC License](https://github.com/d3/d3/blob/main/LICENSE)
- **Chart.js**: [MIT License](https://github.com/chartjs/Chart.js/blob/master/LICENSE.md)
- **Inter** (lettertype, via Fontsource): [SIL Open Font License 1.1](https://github.com/rsms/inter/blob/master/LICENSE.txt)
- **Tailwind CSS** (gegenereerde CSS in `static/css/colors/`): [MIT License](https://github.com/tailwindlabs/tailwindcss/blob/main/LICENSE)
- **React**: [MIT License](https://github.com/facebook/react/blob/main/LICENSE)
- **TypeScript**: [Apache License 2.0](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt)

## 🤖 AI & LLM
- **Ollama**: [MIT License](https://github.com/ollama/ollama/blob/main/LICENSE)
- **Sentence-Transformers**: [Apache License 2.0](https://github.com/UKPLab/sentence-transformers/blob/master/LICENSE)

## 📊 Data
- **CBS Kerncijfers wijken en buurten 2019-2026** (recept in `init_data/cbs/`; de data wordt bij het laden gedownload): Centraal Bureau voor de Statistiek (CBS), tabellen 84583NED, 84799NED, 85039NED, 85318NED, 85618NED, 85984NED, 86165NED en 86358NED via [opendata.cbs.nl](https://opendata.cbs.nl). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Bewerkt: alleen buurten in Fryslân, kolommen gemapt op D-OmniTwin-indicatoren, `65+ jaar (%)` afgeleid. Zie [`docs/3-data-engineering/cbs_kerncijfers.md`](docs/3-data-engineering/cbs_kerncijfers.md).
- **CBS Gebiedsindelingen 2024** (`init_data/fryslan/buurten_fryslan.geojson`): CBS via PDOK. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **RIVM Gezondheidsmonitor** (`init_data/fryslan/indicatorwaarden_fryslan.csv`): RIVM via dataderden.cbs.nl. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
## 🗺️ Databronnen en licenties

De software valt onder EUPL 1.2. De data die D-OmniTwin meelevert (`init_data/`) of ophaalt, valt onder de licentie van de bron. Per meting staat de bron in de kolom `bron`; zie ook `init_data/sample/datapackage.json`. Licenties gecontroleerd op 1 oktober 2026.

| Bron | Gebruikt voor | Licentie | Bronvermelding | Gecontroleerd via |
|------|---------------|----------|----------------|-------------------|
| CBS StatLine (o.a. 86165NED, 85618NED, 85984NED, Kerncijfers wijken en buurten) | Indicatoren per buurt | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.nl) | "Bron: Centraal Bureau voor de Statistiek (CBS)" | [cbs.nl/copyright](https://www.cbs.nl/nl-nl/over-ons/website/copyright) |
| CBS Wijken en Buurten (gebiedsindelingen) via PDOK | Buurtgeometrie (`sample_buurten.geojson`, `init_data/fryslan/`) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.nl) | "Bron: CBS, via PDOK" | [PDOK OGC API CBS Wijken en Buurten 2024](https://api.pdok.nl/cbs/wijken-en-buurten-2024/ogc/v1) (link `rel=license`) |
| Kadaster BAG via PDOK | Indicatoren over gebouwen en adressen | [Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/deed.nl) (geen auteursrecht; bronvermelding niet verplicht, wel gebruikelijk) | "Bron: Kadaster, BAG" | [PDOK OGC API BAG](https://api.pdok.nl/kadaster/bag/ogc/v2) (link `rel=license`) |
| RIVM/GGD Gezondheidsmonitor Volwassenen en Ouderen (RIVM StatLine, o.a. 50150NED) | Gezondheidsindicatoren per buurt | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.nl) | "Bron: Gezondheidsmonitor Volwassenen en Ouderen, GGD'en, CBS en RIVM" (exacte tekst te bevestigen) | [data.overheid.nl, Gezondheid per wijk en buurt](https://data.overheid.nl/dataset/70128-gezondheid-per-wijk-en-buurt--2012-2016-2020-2022-2024--indeling-2024-) |
| RVO EP-Online | Energielabels per buurt | **Te bevestigen.** data.overheid.nl vermeldt "Geen open licentie", toegang "Beperkt" (API-sleutel); de algemene open-datapagina van RVO zegt dat hergebruik mag | "Bron: RVO, EP-Online" | [data.overheid.nl, EP-Online webservice](https://data.overheid.nl/dataset/ep-online-webservice--geregistreerde-energielabels-), [rvo.nl open data](https://www.rvo.nl/onderwerpen/over-ons/auteursrecht/open-data) |
| OpenStreetMap via Overpass API | OV-haltes per buurt (5 indicatoren, 60 regels in de sample) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | "© OpenStreetMap-bijdragers", met link naar [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright) | [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright/nl), [attributierichtlijn OSMF](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) |
| 3DBAG (TU Delft 3D geoinformation en 3DGI) | 3D-panden, live opgehaald via api.3dbag.nl (niet opgeslagen in de repo) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | "© 3DBAG by tudelft3d and 3DGI", met link naar de copyrightpagina | [docs.3dbag.nl/en/copyright](https://docs.3dbag.nl/en/copyright/) |
| PDOK BRT-Achtergrondkaart (Kadaster) | Achtergrondkaart | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.nl) | "© Kadaster" | [PDOK OGC API BRT Achtergrondkaart](https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1) (link `rel=license`) |

### Wat de OpenStreetMap-licentie (ODbL) betekent

- **Naamsvermelding.** Waar OSM-afgeleide data wordt getoond (in de kaart, in exports, in rapportages) staat "© OpenStreetMap-bijdragers" met een link naar de copyrightpagina. De applicatie toont dit rechtsonder op de kaart.
- **Share-alike voor afgeleide databases.** De OV-halte-indicatoren zijn berekend uit OSM-data en vormen daarmee een afgeleide database. Wie die verspreidt (de sample-CSV in deze repo, een release-asset, een databasedump of een API die de ruwe waarden levert), moet dat deel aanbieden onder de ODbL, met deze naamsvermelding. Dat geldt alleen voor de OSM-afgeleide regels, niet voor de CBS-, RIVM- of BAG-regels in hetzelfde bestand: `datapackage.json` vermeldt per bron de licentie.
- **Kaartbeelden en rapportages** zijn een "produced work": die mogen onder een andere licentie, mits met naamsvermelding.
- Verwijder of wijzig de licentievermelding van OSM-afgeleide data niet bij hergebruik.

### Aandachtspunten

- **Demodata.** Buurt BU19000002 (Bolsward-Zuidoost) bevat in de sample geen echte cijfers maar demodata (bron "DEMO: ...", gemiddelde van Bolsward-Noord en Bolsward-Noordoost). Niet gebruiken voor analyse of beleid.
- **Onbekende herkomst.** 48 regels in de sample hebben geen bron en 96 regels hebben een uploadbestandsnaam als bron (vermoedelijk CBS). Licentie te bevestigen; zie `init_data/sample/KWALITEIT.md` en #60.
- **BAG-licentie.** PDOK vermeldt voor de BAG de Public Domain Mark 1.0; `datapackage.json` noemt CC0 1.0. Praktisch gelijk (vrij te gebruiken), maar de vermelding is te bevestigen en gelijk te trekken.
- **Tabel 50150NED** staat in `datapackage.json` als CBS-tabel, maar is een RIVM StatLine-tabel (Gezondheidsmonitor). Licentie is in beide gevallen CC BY 4.0.

---

**Opmerking:** Elk van deze componenten behoudt zijn eigen oorspronkelijke licentie. Het gebruik van deze componenten binnen D-OmniTwin tast hun respectievelijke licenties niet aan.
