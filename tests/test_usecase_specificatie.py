"""
Use Case Specificatie 1.0 (docs/specificaties/usecase/): de schema's zijn de enige bron, alle
use cases voldoen eraan, de specificatie noemt elk schemaveld en de voorbeelden zijn geldig.
Geen stack, geen netwerk.
"""

import json
import re
from pathlib import Path

import pytest

from omnitwin import usecases as uc
from omnitwin.laden.registratie import laad_openapi, valideer, valideer_registratie

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specificaties" / "usecase"
VERSIE = "1.0"
SCHEMAS = ("usecase.schema.json", "dataset.schema.json", "bewijs.schema.json")
README = (SPEC / "README.md").read_text(encoding="utf-8")
ID_BASIS = f"https://raw.githubusercontent.com/TLaan/D-OmniTwin/main/docs/specificaties/usecase/{VERSIE}/"


def schema(naam):
    return json.loads((SPEC / VERSIE / naam).read_text(encoding="utf-8"))


def velden(knoop, uit=None):
    """Alle veldnamen (sleutels van `properties`) in een schema, recursief."""
    uit = set() if uit is None else uit
    if isinstance(knoop, dict):
        for naam, sub in (knoop.get("properties") or {}).items():
            uit.add(naam)
            velden(sub, uit)
        for k, v in knoop.items():
            if k != "properties":
                velden(v, uit)
    elif isinstance(knoop, list):
        for v in knoop:
            velden(v, uit)
    return uit


def enums(knoop, sleutel, uit=None):
    """Enum-waarden van een veld met deze naam, recursief."""
    uit = set() if uit is None else uit
    if isinstance(knoop, dict):
        for naam, sub in (knoop.get("properties") or {}).items():
            if naam == sleutel and isinstance(sub, dict):
                uit.update(sub.get("enum", []))
        for v in knoop.values():
            enums(v, sleutel, uit)
    elif isinstance(knoop, list):
        for v in knoop:
            enums(v, sleutel, uit)
    return uit


def voorbeelden(soort):
    """JSON-blokken in de README direct na <!-- voorbeeld: <soort> -->."""
    return [json.loads(m) for m in re.findall(
        rf"<!-- voorbeeld: {soort} -->\s*```json\n(.*?)\n```", README.replace("\r\n", "\n"), re.S)]


# ---------------------------------------------------------------- één bron

def test_uitvoerder_gebruikt_de_schemas_van_de_specificatie():
    assert uc.SCHEMA == SPEC / VERSIE / "usecase.schema.json"
    assert uc.DATASET_SCHEMA == SPEC / VERSIE / "dataset.schema.json"


@pytest.mark.parametrize("naam", SCHEMAS)
def test_schema_heeft_absolute_stabiele_id(naam):
    s = schema(naam)
    assert s["$id"] == ID_BASIS + naam
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_geen_tweede_exemplaar_van_de_schemas():
    for naam in SCHEMAS:
        kopieen = [p for p in ROOT.rglob(naam)
                   if not {"node_modules", ".git", ".claude"} & set(p.parts) and p.parent != SPEC / VERSIE]
        assert not kopieen, f"dubbel schema: {kopieen}"


# ---------------------------------------------------------------- de use cases

@pytest.mark.parametrize("naam", sorted(uc.lees_usecases()))
def test_use_case_voldoet_aan_de_specificatie(naam):
    u = uc.lees_usecases()[naam]
    assert u.get("specificatie") == VERSIE
    s = schema("usecase.schema.json")
    fouten = valideer({k: v for k, v in u.items() if not k.startswith("_")}, s, s)
    assert not fouten, "\n".join(fouten)


def test_onbekend_veld_en_onbekende_specificatie_worden_afgekeurd():
    s = schema("usecase.schema.json")
    goed = {"specificatie": "1.0", "naam": "x-y", "versie": "0.1.0", "titel": "Voorbeeld"}
    assert valideer(goed, s, s) == []
    assert any("onbekend veld 'extra'" in f for f in valideer({**goed, "extra": 1}, s, s))
    assert any("specificatie" in f for f in valideer({**goed, "specificatie": "9.0"}, s, s))
    assert any("'specificatie' ontbreekt" in f for f in valideer({k: v for k, v in goed.items() if k != "specificatie"}, s, s))


def test_actoren_en_bewijsstappen_zonder_geheimen_of_code():
    s = schema("usecase.schema.json")
    basis = {"specificatie": "1.0", "naam": "x", "versie": "0.1.0", "titel": "Voorbeeld"}
    actor = {"naam": "etl", "soort": "machineclient", "rollen": ["dataset:x:laden"]}
    assert valideer({**basis, "actoren": [actor]}, s, s) == []
    assert valideer({**basis, "actoren": [{**actor, "wachtwoord": "geheim"}]}, s, s)
    stap = {"id": "kaart", "actie": "kaart", "gebied": "BU19000002"}
    assert valideer({**basis, "bewijs": {"stappen": [stap]}}, s, s) == []
    assert valideer({**basis, "bewijs": {"stappen": [{**stap, "script": "document.body"}]}}, s, s)
    assert valideer({**basis, "bewijs": {"stappen": [{"id": "a", "actie": "open", "pad": "https://host/x"}]}}, s, s)
    assert valideer({**basis, "bewijs": {"stappen": [stap] * 5}}, s, s), "maximaal 4 schermen"


# ---------------------------------------------------------------- documentatie volgt het schema

@pytest.mark.parametrize("naam", SCHEMAS)
def test_specificatie_noemt_elk_schemaveld(naam):
    ontbreekt = sorted(v for v in velden(schema(naam)) if f"`{v}`" not in README)
    assert not ontbreekt, f"velden uit {naam} die niet in docs/specificaties/usecase/README.md staan: {ontbreekt}"


@pytest.mark.parametrize("naam,veld", [
    ("usecase.schema.json", "status"), ("usecase.schema.json", "type"), ("usecase.schema.json", "route"),
    ("usecase.schema.json", "profiel"), ("usecase.schema.json", "soort"), ("usecase.schema.json", "actie"),
    ("dataset.schema.json", "adapter"), ("dataset.schema.json", "formaat"), ("dataset.schema.json", "export"),
    ("bewijs.schema.json", "resultaat"), ("bewijs.schema.json", "omgeving"),
])
def test_specificatie_noemt_elke_enumwaarde(naam, veld):
    waarden = enums(schema(naam), veld)
    assert waarden, f"geen enum voor {veld} in {naam}"
    ontbreekt = sorted(str(w) for w in waarden if f"`{w}`" not in README)
    assert not ontbreekt, f"{naam} {veld}: {ontbreekt}"


def test_specificatie_noemt_alle_adapters_en_bewerkingen_van_de_kern():
    from omnitwin.bronadapters import ADAPTERS
    from omnitwin.bronadapters.bewerkingen import BEWERKINGEN, TOETSEN
    for naam in [*ADAPTERS, *BEWERKINGEN, *TOETSEN]:
        assert f"`{naam}`" in README, naam
    assert set(ADAPTERS) == enums(schema("dataset.schema.json"), "adapter")


def test_specificatie_noemt_de_bestandstypen_van_de_uitvoerder():
    for ext in uc.TOEGESTAAN | uc.TOEGESTAAN_BEWIJS:
        assert f"`{ext}`" in README, ext


# ---------------------------------------------------------------- voorbeelden

def test_voorbeelden_zijn_geldig():
    s = schema("usecase.schema.json")
    manifesten = voorbeelden("usecase")
    assert len(manifesten) == 2, "een minimale en een volledige use case"
    for m in manifesten:
        assert valideer(m, s, s) == [], m["naam"]
        assert [v for v in uc.VOLLEDIG if v not in m] == [], m["naam"]
        assert not uc.valideer_manifest(m, m["naam"])
    ds = schema("dataset.schema.json")
    (dataset,) = voorbeelden("dataset")
    assert valideer(dataset, ds, ds) == []
    assert valideer_registratie(uc.registratie_voor_api(dataset), laad_openapi()) == []
    bs = schema("bewijs.schema.json")
    (verslag,) = voorbeelden("bewijs")
    assert valideer(verslag, bs, bs) == []
    volledig = manifesten[1]
    assert {c["dataset"] for c in volledig["controles"] if "dataset" in c and c["type"] != "recht"}         <= {d["id"] for d in volledig["datasets"]}
    assert {c["actor"] for c in volledig["controles"] if "actor" in c} <= {a["naam"] for a in volledig["actoren"]}
    assert {c.get("variant") for c in volledig["controles"] if c.get("variant")} <= set(dataset["varianten"])
