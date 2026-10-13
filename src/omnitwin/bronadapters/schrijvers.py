"""
Leveringen schrijven
====================
Van Tabellen naar het bestand dat naar de laad-API gaat, volgens `levering.formaat` in de dataset:

| Formaat | Profiel | Bestand |
|---|---|---|
| `datapackage` | waarnemingen, definities, kompasprofiel | Data Package-zip (v2) met één CSV per resource en `dcat.jsonld` |
| `geopackage` | gebiedsindeling, kaartlaag | GeoPackage in EPSG:28992 met één featuretabel (`laadprofiel.doel.featureTabel`) |
| `swf-json` | definities, waarnemingen (adapter swf-monitor-v1) | het huidige SWF-pushformaat: `definities.json`, of één JSON per indicator × gebiedstype in `waarden/` |
"""

import csv
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROFIELEN = ROOT / "docs" / "api" / "laden" / "profielen"
PROFIEL_URL = "https://raw.githubusercontent.com/Sudwest-Fryslan/D-OmniTwin/main/docs/api/laden/profielen"
RESOURCES = {
    "waarnemingen": {"waarnemingen": "waarnemingen"},
    "definities": {
        "indicatoren": "definities-indicatoren",
        "gebiedstypen": "definities-gebiedstypen",
        "relaties": "definities-relaties",
    },
}


def profiel_velden(schema_pad):
    return [f["name"] for f in json.loads(Path(schema_pad).read_text(encoding="utf-8"))["fields"]]


def _csv(rijen, velden):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=velden, lineterminator="\r\n", extrasaction="ignore")  # RFC 4180
    w.writeheader()
    for r in rijen:
        w.writerow({v: ("" if r.get(v) is None else r.get(v)) for v in velden})
    return buf.getvalue().encode("utf-8")


def dcat(registratie, tabellen=None):
    """dcat.jsonld bij de levering: de beschrijving uit de registratie, met de periode als er jaren zijn."""
    d = {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
    }
    d.update({k: v for k, v in (registratie.get("beschrijving") or {}).items() if k != "@context"})
    jaren = sorted(
        {
            int(r["jaar"])
            for rs in (tabellen or {}).values()
            for r in rs
            if str(r.get("jaar", "")).isdigit() and int(r["jaar"]) > 0
        }
    )
    if jaren:
        d["dct:temporal"] = {
            "@type": "dct:PeriodOfTime",
            "dcat:startDate": {"@value": f"{jaren[0]}-01-01", "@type": "xsd:date"},
            "dcat:endDate": {"@value": f"{jaren[-1]}-12-31", "@type": "xsd:date"},
        }
    return d


def datapackage(tabellen, dataset, uit, schema_paden=None):
    """Data Package-zip. Resources en kolommen volgen het profiel (of `schema_paden` voor een eigen profiel)."""
    profiel = (dataset.get("laadprofiel") or {}).get("profiel")
    resources = schema_paden or {naam: PROFIELEN / f"{s}.schema.json" for naam, s in RESOURCES[profiel].items()}
    pad = Path(uit) / dataset["levering"].get("bestand", f"{dataset['id']}.zip")
    pakket = {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "name": dataset["id"],
        "title": (dataset.get("beschrijving") or {}).get("dct:title", dataset["id"]),
        "resources": [],
    }
    with zipfile.ZipFile(pad, "w", zipfile.ZIP_DEFLATED) as z:
        enige = next(iter(tabellen.values())) if len(tabellen) == 1 and len(resources) == 1 else []
        for naam, schema_pad in resources.items():
            # Eén tabel en één resource: de tabel is de resource, ongeacht de naam die de bron gaf
            z.writestr(f"{naam}.csv", _csv(tabellen.get(naam, enige), profiel_velden(schema_pad)))
            schema_url = (
                f"{PROFIEL_URL}/{Path(schema_pad).name}"
                if Path(schema_pad).parent == PROFIELEN
                else Path(schema_pad).name
            )
            pakket["resources"].append(
                {
                    "name": naam,
                    "path": f"{naam}.csv",
                    "format": "csv",
                    "mediatype": "text/csv",
                    "encoding": "utf-8",
                    "schema": schema_url,
                }
            )
        z.writestr("datapackage.json", json.dumps(pakket, ensure_ascii=False, indent=2))
        z.writestr("dcat.jsonld", json.dumps(dcat(dataset, tabellen), ensure_ascii=False, indent=2))
    return [pad]


def _fiona_type(waarden):
    w = [v for v in waarden if v not in (None, "")]
    if w and all(isinstance(v, int) and not isinstance(v, bool) for v in w):
        return "int"
    if w and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w):
        return "float"
    return "str"


def geopackage(tabellen, dataset, uit):
    try:
        import fiona
        from fiona.crs import CRS
        from shapely.geometry import mapping
    except ImportError as e:  # slanke omgeving zonder GDAL
        from omnitwin.bronadapters import GeenBron

        raise GeenBron(f"fiona/shapely niet beschikbaar ({e}); GeoPackage niet gemaakt")
    doel = dataset["laadprofiel"]["doel"]
    rijen = [r for rs in tabellen.values() for r in rs if r.get("geometry") is not None]
    pad = Path(uit) / dataset["levering"].get("bestand", f"{dataset['id']}.gpkg")
    if pad.exists():
        pad.unlink()
    velden = [k for k in (rijen[0] if rijen else {}) if k != "geometry"]
    typen = {r["geometry"].geom_type for r in rijen}
    geom_type = dataset["levering"].get("geometrie") or (
        "MultiPolygon" if typen <= {"Polygon", "MultiPolygon"} else sorted(typen)[0] if len(typen) == 1 else "Unknown"
    )
    schema = {"geometry": geom_type, "properties": {v: _fiona_type([r.get(v) for r in rijen]) for v in velden}}
    with fiona.open(
        pad, "w", driver="GPKG", layer=doel["featureTabel"], crs=CRS.from_epsg(28992), schema=schema
    ) as dst:
        dst.writerecords(
            {
                "geometry": mapping(r["geometry"]),
                "properties": {v: (None if r.get(v) == "" else r.get(v)) for v in velden},
            }
            for r in rijen
        )
    return [pad]


def swf_json(tabellen, dataset, uit):
    """Het huidige SWF-pushformaat (adapter swf-monitor-v1)."""
    uit = Path(uit)
    if dataset["laadprofiel"]["profiel"] == "definities":
        pad = uit / dataset["levering"].get("bestand", "definities.json")
        pad.write_text(
            json.dumps(
                {k: tabellen.get(k, []) for k in ("indicatoren", "gebiedstypen", "relaties")},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        return [pad]
    velden = ("indicator_id", "gebiedstype_id", "gebieds_id", "waarde", "begingeldigheid", "eindgeldigheid")
    per = {}
    for r in next(iter(tabellen.values()), []):
        per.setdefault((r["indicator_id"], r["gebiedstype_id"]), []).append({v: r.get(v) for v in velden})
    map_ = uit / dataset["levering"].get("bestand", "waarden")
    map_.mkdir(parents=True, exist_ok=True)
    for (ind, gt), rijen in sorted(per.items()):
        (map_ / f"{ind}_{gt}.json").write_text(json.dumps(rijen, ensure_ascii=False), encoding="utf-8")
    return [map_]


SCHRIJVERS = {"datapackage": datapackage, "geopackage": geopackage, "swf-json": swf_json}


def schrijf(tabellen, dataset, uit, schema_paden=None):
    formaat = dataset["levering"]["formaat"]
    if formaat not in SCHRIJVERS:
        raise ValueError(f"onbekend leveringsformaat {formaat!r}; bekend: {sorted(SCHRIJVERS)}")
    Path(uit).mkdir(parents=True, exist_ok=True)
    if formaat == "datapackage":
        return datapackage(tabellen, dataset, uit, schema_paden)
    return SCHRIJVERS[formaat](tabellen, dataset, uit)
