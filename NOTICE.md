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
- **MapLibre GL JS**: [BSD 3-Clause License](https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt)
- **Deck.gl**: [MIT License](https://github.com/visgl/deck.gl/blob/master/LICENSE)
- **D3.js**: [ISC License](https://github.com/d3/d3/blob/main/LICENSE)
- **React**: [MIT License](https://github.com/facebook/react/blob/main/LICENSE)
- **TypeScript**: [Apache License 2.0](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt)

## 🤖 AI & LLM
- **Ollama**: [MIT License](https://github.com/ollama/ollama/blob/main/LICENSE)
- **Sentence-Transformers**: [Apache License 2.0](https://github.com/UKPLab/sentence-transformers/blob/master/LICENSE)

## 📊 Data
- **CBS Kerncijfers wijken en buurten 2019-2026** (`init_data/cbs/`, ook in `init_data/sample/`): Centraal Bureau voor de Statistiek (CBS), tabellen 84583NED, 84799NED, 85039NED, 85318NED, 85618NED, 85984NED, 86165NED en 86358NED via [opendata.cbs.nl](https://opendata.cbs.nl). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Bewerkt: alleen buurten in Fryslân, kolommen gemapt op D-OmniTwin-indicatoren, `65+ jaar (%)` afgeleid. Zie [`docs/3-data-engineering/cbs_kerncijfers.md`](docs/3-data-engineering/cbs_kerncijfers.md).
- **CBS Gebiedsindelingen 2024** (`init_data/fryslan/buurten_fryslan.geojson`): CBS via PDOK. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **RIVM Gezondheidsmonitor** (`init_data/fryslan/indicatorwaarden_fryslan.csv`): RIVM via dataderden.cbs.nl. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

**Opmerking:** Elk van deze componenten behoudt zijn eigen oorspronkelijke licentie. Het gebruik van deze componenten binnen D-OmniTwin tast hun respectievelijke licenties niet aan.
