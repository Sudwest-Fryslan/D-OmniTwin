"""Profielen van de laad-API (GET /profielen): contract, mediatypes, Table Schema's, adapters."""

from __future__ import annotations

from omnitwin.laden.tabelschema import laad_schema

DOCS = "https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/docs/api/laden/profielen/"
GPKG, ZIP, CSV, JSON = "application/geopackage+sqlite3", "application/zip", "text/csv", "application/json"

PROFIELEN = {
    "waarnemingen": {"titel": "Waarnemingen: indicatorwaarden per gebied en moment",
                     "contract": "waarnemingen.schema.json", "mediatypes": [GPKG, ZIP, CSV, JSON],
                     "schemas": {"waarnemingen": "waarnemingen"}, "adapters": ["swf-monitor-v1"]},
    "definities": {"titel": "Definities: indicatoren, gebiedstypen en hun relaties",
                   "contract": "definities-indicatoren.schema.json", "mediatypes": [GPKG, ZIP, JSON],
                   "schemas": {"indicatoren": "definities-indicatoren", "gebiedstypen": "definities-gebiedstypen",
                               "relaties": "definities-relaties"}, "adapters": ["swf-monitor-v1"]},
    "gebiedsindeling": {"titel": "Gebiedsindeling: gebieden met geometrie van één gebiedstype",
                        "contract": "gebiedsindeling.md", "mediatypes": [GPKG, ZIP], "schemas": {}, "adapters": []},
    "kaartlaag": {"titel": "Kaartlaag: features voor de kaart", "contract": "kaartlaag.md",
                  "mediatypes": [GPKG, ZIP], "schemas": {}, "adapters": []},
}


def profiel_uri(code: str) -> str:
    return DOCS + PROFIELEN[code]["contract"]


def profiel(code: str) -> dict:
    p = PROFIELEN[code]
    schemas = {}
    for res, naam in p["schemas"].items():
        s = laad_schema(naam)
        s.pop("$schema", None)
        schemas[res] = s
    return {"id": code, "titel": p["titel"], "uri": profiel_uri(code), "mediatypes": list(p["mediatypes"]),
            "tableSchemas": schemas, "adapters": list(p["adapters"])}
