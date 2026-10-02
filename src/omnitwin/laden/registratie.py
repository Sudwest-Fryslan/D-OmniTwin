"""
Registratie controleren tegen de laad-API-specificatie
======================================================
Controleert een registratie (usecases/<naam>/datasets/<id>.json) zoals `POST /api/laden/v1/datasets` hem verwacht tegen
het schema `DatasetRegistratie` in `docs/api/laden/openapi.yaml`, plus de regels
uit de profielen die het schema niet uitdrukt (verplichte velden in `laadprofiel.doel`).

Kleine validator voor de subset van OpenAPI 3.0 die de specificatie gebruikt
($ref, type, required, enum, pattern, min/maxLength, minimum/maximum, items,
properties, additionalProperties, nullable, oneOf, allOf, format). Alleen PyYAML
nodig, zodat de unittests ook in de slanke CI-omgeving draaien.

Gebruik:
    python -m omnitwin.laden.registratie usecases/swf-definities/datasets/swf-monitor-definities.json [...]
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
OPENAPI = ROOT / "docs" / "api" / "laden" / "openapi.yaml"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Velden in laadprofiel.doel die het profiel verplicht stelt (profielen/gebiedsindeling.md, kaartlaag.md)
DOEL_VERPLICHT = {
    "gebiedsindeling": ("gebiedstypeId", "featureTabel", "sleutelveld", "labelveld"),
    "kaartlaag": ("featureTabel", "sleutelveld"),
}


def laad_openapi(pad=OPENAPI):
    import yaml  # PyYAML: in requirements-ci.txt via uvicorn[standard]
    return yaml.safe_load(Path(pad).read_text(encoding="utf-8"))


def _los_op(ref, spec):
    if not ref.startswith("#/"):
        raise ValueError(f"alleen interne $ref: {ref}")
    knoop = spec
    for deel in ref[2:].split("/"):
        knoop = knoop[deel]
    return knoop


def _type_klopt(waarde, t):
    return {
        "object": isinstance(waarde, dict),
        "array": isinstance(waarde, list),
        "string": isinstance(waarde, str),
        "boolean": isinstance(waarde, bool),
        "integer": isinstance(waarde, int) and not isinstance(waarde, bool),
        "number": isinstance(waarde, (int, float)) and not isinstance(waarde, bool),
    }.get(t, True)


def _format_klopt(waarde, fmt):
    try:
        if fmt == "uuid":
            return bool(UUID_RE.match(waarde))
        if fmt == "uri":
            u = urlparse(waarde)
            return bool(u.scheme and (u.netloc or u.scheme in ("urn", "mailto")))
        if fmt == "date":
            dt.date.fromisoformat(waarde)
        elif fmt == "date-time":
            dt.datetime.fromisoformat(waarde.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    return True


def valideer(waarde, schema, spec, pad="$"):
    """Fouten (lijst van teksten) van `waarde` tegen een OpenAPI-schema."""
    if "$ref" in schema:
        return valideer(waarde, _los_op(schema["$ref"], spec), spec, pad)
    fouten = []
    if waarde is None:
        return [] if schema.get("nullable") else [f"{pad}: null niet toegestaan"]
    for deel in schema.get("allOf", []):
        fouten += valideer(waarde, deel, spec, pad)
    if "oneOf" in schema:
        passend = sum(1 for deel in schema["oneOf"] if not valideer(waarde, deel, spec, pad))
        if passend != 1:
            fouten.append(f"{pad}: past op {passend} van de oneOf-varianten (precies 1 vereist)")
    t = schema.get("type")
    if t and not _type_klopt(waarde, t):
        return fouten + [f"{pad}: verwacht {t}, gekregen {type(waarde).__name__}"]
    if "enum" in schema and waarde not in schema["enum"]:
        fouten.append(f"{pad}: {waarde!r} niet in {schema['enum']}")
    if isinstance(waarde, str):
        if "pattern" in schema and not re.search(schema["pattern"], waarde):
            fouten.append(f"{pad}: past niet op patroon {schema['pattern']}")
        if len(waarde) < schema.get("minLength", 0):
            fouten.append(f"{pad}: korter dan {schema['minLength']}")
        if "maxLength" in schema and len(waarde) > schema["maxLength"]:
            fouten.append(f"{pad}: langer dan {schema['maxLength']}")
        if "format" in schema and not _format_klopt(waarde, schema["format"]):
            fouten.append(f"{pad}: geen geldige {schema['format']}")
    if isinstance(waarde, (int, float)) and not isinstance(waarde, bool):
        if "minimum" in schema and waarde < schema["minimum"]:
            fouten.append(f"{pad}: kleiner dan {schema['minimum']}")
        if "maximum" in schema and waarde > schema["maximum"]:
            fouten.append(f"{pad}: groter dan {schema['maximum']}")
    if isinstance(waarde, list):
        if "maxItems" in schema and len(waarde) > schema["maxItems"]:
            fouten.append(f"{pad}: meer dan {schema['maxItems']} elementen")
        if "items" in schema:
            for i, el in enumerate(waarde):
                fouten += valideer(el, schema["items"], spec, f"{pad}[{i}]")
    if isinstance(waarde, dict):
        props = schema.get("properties", {})
        for veld in schema.get("required", []):
            if veld not in waarde:
                fouten.append(f"{pad}: verplicht veld '{veld}' ontbreekt")
        for veld, w in waarde.items():
            if veld in props:
                fouten += valideer(w, props[veld], spec, f"{pad}.{veld}")
            elif schema.get("additionalProperties") is False:
                fouten.append(f"{pad}: onbekend veld '{veld}'")
    return fouten


def valideer_schema(waarde, naam, spec=None):
    """Valideer tegen components/schemas/<naam> van de laad-API."""
    spec = spec or laad_openapi()
    return valideer(waarde, spec["components"]["schemas"][naam], spec)


def valideer_registratie(registratie, spec=None):
    """Fouten in een registratie: schema DatasetRegistratie plus de profielregels."""
    fouten = valideer_schema(registratie, "DatasetRegistratie", spec)
    lp = registratie.get("laadprofiel") or {}
    doel = lp.get("doel") or {}
    for veld in DOEL_VERPLICHT.get(lp.get("profiel"), ()):
        if not doel.get(veld):
            fouten.append(f"$.laadprofiel.doel: '{veld}' is verplicht bij profiel {lp.get('profiel')}")
    if lp.get("profiel") in ("waarnemingen", "definities") and doel:
        fouten.append("$.laadprofiel.doel: alleen voor gebiedsindeling en kaartlaag")
    if lp.get("adapter") and lp.get("profiel") not in ("waarnemingen", "definities"):
        fouten.append("$.laadprofiel.adapter: swf-monitor-v1 vertaalt alleen naar definities en waarnemingen")
    return fouten


def main(paden):
    spec = laad_openapi()
    fout = False
    for p in paden:
        fouten = valideer_registratie(json.loads(Path(p).read_text(encoding="utf-8")), spec)
        print(f"{'OK  ' if not fouten else 'FOUT'} {p}")
        for f in fouten:
            print(f"     {f}")
        fout = fout or bool(fouten)
    return 1 if fout else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
