"""
Levering lokaal controleren tegen het profiel van de dataset
============================================================
Doet vooraf wat de laad-API bij het valideren doet, voor zover dat zonder database kan:

- Data Package-zip (waarnemingen, definities): Table Schema en sleutels per resource met
  frictionless, tegen het profiel in `docs/api/laden/profielen/` (niet tegen de URL in het pakket);
  plus de regels die Table Schema niet uitdrukt (precies één van jaar en peildatum, n-regels,
  unieke sleutel van waarnemingen);
- GeoPackage (gebiedsindeling, kaartlaag): featuretabel, CRS, geometrietype en -geldigheid,
  sleutel gevuld en uniek, label gevuld, attribuutnamen (met fiona en shapely);
- JSON in het adapterformaat swf-monitor-v1: tegen de schema's in `openapi.yaml`.

Niet lokaal te controleren (wel door de API): of gebieden en indicatoren bestaan, de
plausibiliteit ten opzichte van de vorige versie, en relaties die nog in gebruik zijn.

frictionless is optioneel (niet in de requirements): zonder frictionless worden
Data Package-leveringen overgeslagen met een melding. fiona en shapely zitten in de app.

Gebruik:
    python -m omnitwin.laden.levering <datasets/<id>.json> <levering> [<levering> ...]
    (levering: .zip, .gpkg, .json of een map met .json-bestanden)
"""

import csv
import json
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from omnitwin.laden.registratie import laad_openapi, valideer, valideer_schema

ROOT = Path(__file__).resolve().parents[3]
PROFIELEN = ROOT / "docs" / "api" / "laden" / "profielen"
RESOURCES = {
    "waarnemingen": {"waarnemingen": "waarnemingen"},
    "definities": {"indicatoren": "definities-indicatoren", "gebiedstypen": "definities-gebiedstypen",
                   "relaties": "definities-relaties"},
}
MAX_FOUTEN = 50


def _schema(naam_of_pad):
    pad = naam_of_pad if isinstance(naam_of_pad, Path) else PROFIELEN / f"{naam_of_pad}.schema.json"
    s = json.loads(pad.read_text(encoding="utf-8"))
    s.pop("$schema", None)  # frictionless v5 kent de v2-profiel-URL niet; inhoud is gelijk
    s.pop("uniqueKeys", None)  # v2; hieronder zelf gecontroleerd
    return s


def _rapport(pad, profiel):
    return {"bestand": Path(pad).name, "profiel": profiel, "geldig": True, "aantallen": {}, "fouten": []}


def _fout(rapport, tekst):
    rapport["geldig"] = False
    if len(rapport["fouten"]) < MAX_FOUTEN:
        rapport["fouten"].append(tekst)


class OntbrekendPakket(Exception):
    """Een optioneel pakket (frictionless, fiona) ontbreekt."""


def valideer_datapackage(pad, registratie, schema_paden=None):
    try:
        from frictionless import Package, system
    except ImportError:
        raise OntbrekendPakket("frictionless ontbreekt: pip install frictionless (alleen nodig om Data Packages te controleren)")
    lp = registratie.get("laadprofiel") or {}
    profiel = lp.get("profiel", "eigen schema")
    rapport = _rapport(pad, profiel)
    verwacht = {k: Path(v) for k, v in schema_paden.items()} if schema_paden else RESOURCES[profiel]
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(pad) as z:
            z.extractall(tmp)
        dp = json.loads((Path(tmp) / "datapackage.json").read_text(encoding="utf-8"))
        namen = [r["name"] for r in dp["resources"]]
        if sorted(namen) != sorted(verwacht):
            _fout(rapport, f"resources {namen}, verwacht {sorted(verwacht)}")
            return rapport
        descriptor = {"name": dp.get("name", "levering"), "resources": []}
        for r in dp["resources"]:
            descriptor["resources"].append({"name": r["name"], "path": r["path"], "format": "csv",
                                            "encoding": "utf-8", "schema": _schema(verwacht[r["name"]])})
        with system.use_context(trusted=True):
            pkg = Package(descriptor, basepath=tmp)
            rep = pkg.validate(limit_errors=MAX_FOUTEN)
        for task in rep.tasks:
            # Zelf tellen: frictionless stopt met tellen bij de foutlimiet
            with open(Path(tmp) / next(r["path"] for r in dp["resources"] if r["name"] == task.name), encoding="utf-8", newline="") as f:
                rapport["aantallen"][task.name] = max(sum(1 for _ in csv.reader(f)) - 1, 0)
            for e in task.errors:
                veld = getattr(e, "field_name", None)
                _fout(rapport, f"{task.name} regel {getattr(e, 'row_number', '-')}{f' veld {veld}' if veld else ''}: {e.type}: {e.note or e.message}")
        for e in rep.errors:
            _fout(rapport, f"pakket: {e.type}: {e.message}")
        if profiel == "waarnemingen":
            _waarnemingen_regels(Path(tmp) / "waarnemingen.csv", lp, rapport)
    return rapport


def _waarnemingen_regels(csv_pad, lp, rapport):
    """Regels van het profiel waarnemingen die Table Schema niet uitdrukt."""
    sleutels, n_stat = Counter(), Counter()
    minimum_n, per_indicator = lp.get("minimumN", 10), lp.get("minimumNPerIndicator") or {}
    with open(csv_pad, encoding="utf-8", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            if bool(r["jaar"]) == bool(r["peildatum"]):
                _fout(rapport, f"waarnemingen regel {i}: jaar-ongeldig: precies één van jaar en peildatum")
            if r["n"] == "":
                if lp.get("bijOntbrekendeN", "afkeuren") == "afkeuren":
                    _fout(rapport, f"waarnemingen regel {i}: n-ontbreekt")
                n_stat["bronOnderdrukt"] += 1
            elif int(r["n"]) < per_indicator.get(r["indicator_uuid"], minimum_n):
                n_stat["onderdrukt"] += 1
            sleutels[(r["gebied_code"], r["indicator_uuid"], r["jaar"], r["peildatum"], r["scenario"] or "current")] += 1
    dubbel = sum(v - 1 for v in sleutels.values() if v > 1)
    if dubbel:
        _fout(rapport, f"waarnemingen: dubbele-sleutel: {dubbel} regels")
    rapport["aantallen"].update(n_stat)


def valideer_gpkg(pad, registratie):
    try:
        import fiona
        from shapely.geometry import shape
    except ImportError:
        raise OntbrekendPakket("fiona of shapely ontbreekt (pip install fiona shapely)")
    lp = registratie["laadprofiel"]
    doel = lp.get("doel") or {}
    rapport = _rapport(pad, lp["profiel"])
    lagen = fiona.listlayers(pad)
    tabel = doel.get("featureTabel")
    if tabel not in lagen:
        _fout(rapport, f"featureTabel '{tabel}' ontbreekt (lagen: {lagen})")
        return rapport
    sleutel, label = doel.get("sleutelveld"), doel.get("labelveld")
    with fiona.open(pad, layer=tabel) as src:
        epsg = src.crs.to_epsg() if src.crs else None
        if epsg not in (28992, 4326):
            _fout(rapport, f"crs-niet-ondersteund: EPSG:{epsg}")
        velden = list(src.schema["properties"])
        for v in velden:
            if lp["profiel"] == "kaartlaag" and (len(v) > 63 or not re.fullmatch(r"[a-z][a-z0-9_]*", v)):
                _fout(rapport, f"attribuut '{v}': geen snake_case of langer dan 63 tekens")
        for v in (sleutel, label):
            if v and v not in velden:
                _fout(rapport, f"veld '{v}' ontbreekt in {tabel}")
        codes, typen, n = Counter(), Counter(), 0
        for f in src:
            n += 1
            p = f.properties
            if f.geometry is None:
                _fout(rapport, f"feature {n}: geometrie-ongeldig: leeg")
                continue
            g = shape(f.geometry)
            typen[g.geom_type] += 1
            if g.is_empty or not g.is_valid:
                _fout(rapport, f"feature {n}: geometrie-ongeldig")
            if sleutel in p:
                if p[sleutel] in (None, ""):
                    _fout(rapport, f"feature {n}: sleutelveld leeg")
                codes[p[sleutel]] += 1
            if lp["profiel"] == "gebiedsindeling" and label and label in p and p[label] in (None, ""):
                _fout(rapport, f"feature {n}: labelveld leeg")
    dubbel = [k for k, v in codes.items() if v > 1]
    if dubbel:
        _fout(rapport, f"dubbele-sleutel: {len(dubbel)} codes")
    if lp["profiel"] == "gebiedsindeling" and set(typen) - {"Polygon", "MultiPolygon"}:
        _fout(rapport, f"geometrie-ongeldig: typen {dict(typen)}, alleen (Multi)Polygon")
    if lp["profiel"] == "kaartlaag" and len({t.replace("Multi", "") for t in typen}) > 1:
        _fout(rapport, f"geometrie-ongeldig: meer dan één geometrietype {dict(typen)}")
    minimum = (lp.get("plausibiliteit") or {}).get("minRegels")
    if minimum is not None and n < minimum:
        _fout(rapport, f"aantal-niet-plausibel: {n} < minRegels {minimum}")
    rapport["aantallen"] = {"features": n, "codes": len(codes), "geometrie": dict(typen), "crs": f"EPSG:{epsg}"}
    return rapport


def valideer_swf_json(pad, registratie, spec=None):
    """Adapterformaat swf-monitor-v1: definities-object of waarden-array."""
    spec = spec or laad_openapi()
    data = json.loads(Path(pad).read_text(encoding="utf-8"))
    rapport = _rapport(pad, registratie["laadprofiel"]["profiel"])
    if isinstance(data, dict):
        fouten = valideer_schema(data, "SwfDefinities", spec)
        rapport["aantallen"] = {k: len(data.get(k, [])) for k in ("indicatoren", "gebiedstypen", "relaties")}
        bekend = {"C", "O", "B"}
        onbekend = Counter(i.get("status") for i in data.get("indicatoren", []) if i.get("status") not in bekend)
        if onbekend:
            fouten.append(f"indicatoren: onbekende status {dict(onbekend)} (laad-API: schema-ongeldig)")
    else:
        fouten = valideer(data, {"type": "array", "items": {"$ref": "#/components/schemas/SwfWaarde"}}, spec)
        jaar0 = sum(1 for w in data if str(w.get("begingeldigheid", "")).startswith("0000"))
        if jaar0:
            fouten.append(f"jaar-ongeldig: {jaar0} regels met jaar 0")
        rapport["aantallen"] = {"waarden": len(data),
                                "combinaties": len({(w.get("indicator_id"), w.get("gebiedstype_id")) for w in data})}
    for f in fouten:
        _fout(rapport, f)
    return rapport


def valideer_levering(registratie, pad, schema_paden=None):
    pad = Path(pad)
    if pad.is_dir():
        spec = laad_openapi()
        return [valideer_swf_json(p, registratie, spec) for p in sorted(pad.glob("*.json"))]
    if pad.suffix == ".zip":
        return [valideer_datapackage(pad, registratie, schema_paden)]
    if pad.suffix == ".gpkg":
        return [valideer_gpkg(pad, registratie)]
    if pad.suffix == ".json":
        return [valideer_swf_json(pad, registratie)]
    raise ValueError(f"onbekend leveringsformaat: {pad}")


def samenvatting(rapporten):
    geldig = all(r["geldig"] for r in rapporten)
    return {"geldig": geldig, "bestanden": len(rapporten),
            "afgekeurd": [r["bestand"] for r in rapporten if not r["geldig"]], "rapporten": rapporten}


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    registratie = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    alles = []
    for p in argv[1:]:
        alles += valideer_levering(registratie, p)
    s = samenvatting(alles)
    for r in alles:
        print(f"{'OK  ' if r['geldig'] else 'FOUT'} {r['bestand']} ({r['profiel']}): {r['aantallen']}")
        for f in r["fouten"][:10]:
            print(f"     {f}")
    return 0 if s["geldig"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
