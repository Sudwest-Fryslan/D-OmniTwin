"""Bestanden lezen voor de bronadapters: GeoPackage/GeoJSON (fiona, shapely), CSV en JSON (standaardbibliotheek)."""

import csv
import json
from pathlib import Path

GEO = {"gpkg", "geojson", "shp", "fgb"}


def _naar_28992(geom, epsg):
    from fiona.transform import transform_geom
    from shapely.geometry import mapping, shape

    if not epsg or epsg == 28992:
        return geom
    return shape(transform_geom(f"EPSG:{epsg}", "EPSG:28992", mapping(geom)))


def lees_geo(pad, laag=None):
    """Features als records: eigenschappen + `geometry` (shapely, EPSG:28992)."""
    try:
        import fiona
        from shapely.geometry import shape
    except ImportError as e:
        from omnitwin.bronadapters import GeenBron

        raise GeenBron(f"fiona/shapely ontbreekt: {e}")
    uit = []
    with fiona.open(pad, layer=laag or fiona.listlayers(pad)[0]) as src:
        epsg = src.crs.to_epsg() if src.crs else None
        for f in src:
            r = dict(f.properties)
            # Een kolom die de GeoPackage als primaire sleutel (FID) gebruikt, staat niet in de eigenschappen
            r.setdefault("fid", int(f.id) if str(f.id).isdigit() else f.id)
            r["geometry"] = _naar_28992(shape(f.geometry), epsg) if f.geometry else None
            uit.append(r)
    return uit


def lees_geojson(pad, epsg=None):
    """GeoJSON zonder GDAL (alleen shapely). `epsg`: CRS van de coördinaten als het bestand het niet noemt."""
    try:
        from shapely.geometry import shape
    except ImportError as e:  # slanke omgeving (CI): bron hier niet te lezen, overgeslagen
        from omnitwin.bronadapters import GeenBron

        raise GeenBron(f"shapely ontbreekt: {e}")
    data = json.loads(Path(pad).read_text(encoding="utf-8"))
    crs = ((data.get("crs") or {}).get("properties") or {}).get("name", "")
    bestand_epsg = int(crs.rsplit(":", 1)[-1]) if crs and crs.rsplit(":", 1)[-1].isdigit() else None
    epsg = bestand_epsg or epsg or 4326
    uit = []
    for f in data.get("features", []):
        r = dict(f.get("properties") or {})
        g = shape(f["geometry"]) if f.get("geometry") else None
        r["geometry"] = _naar_28992(g, epsg) if g is not None and epsg != 28992 else g
        uit.append(r)
    return uit


def lees_bestand(pad, formaat=None, laag=None, tabel="data", crs=None):
    """Lees een bestand als Tabellen ({naam: [record]}). crs: EPSG-code als een GeoJSON-bestand die niet noemt."""
    pad = Path(pad)
    formaat = (formaat or pad.suffix.lstrip(".")).lower()
    if formaat == "csv":
        with open(pad, encoding="utf-8-sig", newline="") as f:
            return {tabel: [{k.strip(): v for k, v in r.items()} for r in csv.DictReader(f)]}
    if formaat == "json":
        data = json.loads(pad.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {tabel: data}
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            return {tabel: lees_geojson(pad, epsg=crs)}
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    if formaat == "geojson":
        return {tabel: lees_geojson(pad, epsg=crs)}
    if formaat in GEO:
        return {tabel: lees_geo(pad, laag)}
    from omnitwin.bronadapters import BronFout

    raise BronFout(f"onbekend formaat {formaat!r} voor {pad.name}")
