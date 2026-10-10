"""
Use-case-uitvoerder
===================
Eén ingang voor alle use cases (`usecases/<naam>/`). Een use case is een pakket met een
manifest (`usecase.json`), zoals een app: naam,
versie, afhankelijkheden, rechten, datasets en controles. **Een use case bevat geen code:**
waar de data vandaan komt en hoe hij wordt bewerkt, staat declaratief in
`datasets/<id>.json`; de kern voert dat uit met de
bronadapters (`omnitwin.bronadapters`) en de laad-API-validatie (`omnitwin.laden`).
Leidend is de Use Case Specificatie (`docs/specificaties/usecase/README.md`) met de
schema's in `docs/specificaties/usecase/<versie>/`.

    python -m omnitwin.usecases lijst
    python -m omnitwin.usecases boom <naam>
    python -m omnitwin.usecases index [--controleer]
    python -m omnitwin.usecases controleer <naam> [--uit MAP] [--variant NAAM]
    python -m omnitwin.usecases installeer <naam> [...] | --alle [--inproces | --testaccounts]
    python -m omnitwin.usecases test <naam> [--testaccounts]
    python -m omnitwin.usecases opruimen <naam> [...]
    python -m omnitwin.usecases bewijs <naam> [...] | --alle [--zip PAD]
    python -m omnitwin.usecases galerij [--controleer]

`controleer` werkt zonder draaiende stack: manifest, bestanden in de map, afhankelijkheden,
registraties, en de levering(en) maken en valideren tegen het profiel. Bronnen komen uit
de omgeving: `SWF_DUMP_DIR`, `SWF_DOCS_DIR`, `SWF_GEO_DIR`, `SWF_DB_DUMP`, `SWF_EXPORT_DIR`, `DATA_CACHE`
(standaard ./data-cache), en open bronnen via https (allowlist in `omnitwin.bronadapters`).
Ontbreekt een bron, dan is die dataset 'overgeslagen', geen fout.

`installeer` en `test` gebruiken de laad-API (`OMNITWIN_BASE_URL`, standaard http://localhost)
met een token van een machineclient (client credentials: `OMNITWIN_CLIENT_ID`,
`OMNITWIN_CLIENT_SECRET`; tokenendpoint `OMNITWIN_TOKEN_URL` of via discovery van realm
`KEYCLOAK_REALM`, standaard omnitwin). Zolang `/api/laden/v1/openapi.json` er niet is, melden
ze dat. Met `--inproces` (eerste installatie, `db-init`) gebruikt `installeer` dezelfde laadstraat
zonder HTTP en zonder token (`omnitwin.laden.inproces`). Demopakketten zonder `datasets` installeert
`installeer` via `init_data/scripts/laad_usecase.py`, zodat er één ingang is; de inrichting van een
demopakket met `datasets` (richting van de indicatoren uit `data.indicatoren`) ook.

Testaccounts (#223, alleen test en dev): met `--testaccounts` maakt de uitvoerder de `actoren` van de
use case (en zijn afhankelijkheden) aan in Keycloak als `uc-<usecase>-<actor>` en installeert en
controleert als die actoren: registreren als beheerder, leveren als de client van de dataset;
controles met `actor` en de rechtencontroles (`type: recht`) draaien als die actor. Zie
`omnitwin.testaccounts`. `opruimen <naam>` verwijdert ze weer.

Varianten (`varianten` in `datasets/<id>.json`): `sla_over` (stappen overslaan), `bron` en
`bewerkingen` (een andere bron, bijv. de echte interne bron naast demodata) en `als_beschikbaar`
(zonder `--variant` eerst deze variant; is zijn bron hier niet beschikbaar, dan de standaardbron).

`bewijs` voert de bewijsstappen uit met Playwright en schrijft screenshots en `bewijs.json`;
`galerij` werkt de galerij in de root-README en de screenshots in de README's van de use cases bij
(zie `omnitwin.usecase_bewijs`, #225).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USECASES_DIR = ROOT / "usecases"
SPECIFICATIE = ROOT / "docs" / "specificaties" / "usecase" / "1.0"  # normatieve schema's (één bron)
SCHEMA = SPECIFICATIE / "usecase.schema.json"
DATASET_SCHEMA = SPECIFICATIE / "dataset.schema.json"
README = USECASES_DIR / "README.md"
INDEX_START, INDEX_EINDE = "<!-- usecase-index:start -->", "<!-- usecase-index:end -->"
VOLLEDIG = ("naam", "versie", "titel", "vraag", "gebruiker", "status", "afhankelijk_van", "rechten", "datasets", "controles")
# Een use case is declaratief: alleen deze bestanden. bewijs/ wordt gevuld door de uitvoerder
# (in git alleen bewijs/*.webp, bewijs/bewijs.json en bewijs/README.md; #225).
TOEGESTAAN = {".json", ".md", ".csv"}
TOEGESTAAN_BEWIJS = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
# In data/ ook een GeoPackage: geometrie die niet online te downloaden is (bijv. welstand × buurt, #222),
# en een kleine PDF als voorbeelddocument (bijv. een testverklaring voor de AI-vrijgave, #314)
TOEGESTAAN_DATA = TOEGESTAAN | {".gpkg", ".pdf"}
MAX_PDF_BYTES = 100 * 1024
# Bestaande code in use cases, uit te faseren naar een kernadapter (niet nieuw toevoegen).
UIT_TE_FASEREN = set()
# Sleutels in datasets/<id>.json die niet naar POST /api/laden/v1/datasets gaan
NIET_REGISTREREN = ("bron", "bewerkingen", "levering", "varianten", "$schema")


class UseCaseFout(Exception):
    """Manifest of afhankelijkheden kloppen niet (onbekend, cyclus, versie, extern)."""


# ------------------------------------------------------------------ manifesten en afhankelijkheden

def lees_usecases(map_=USECASES_DIR):
    """Alle manifesten, op naam (= mapnaam). `_map` wijst naar de map van de use case."""
    uit = {}
    for pad in sorted(Path(map_).glob("*/usecase.json")):
        uc = json.loads(pad.read_text(encoding="utf-8"))
        uc["_map"] = pad.parent
        uit[pad.parent.name] = uc
    return uit


def versie_tuple(v):
    delen = re.findall(r"\d+", str(v))[:3]
    if not delen:
        raise UseCaseFout(f"geen versie: {v!r}")
    return tuple(int(d) for d in delen) + (0,) * (3 - len(delen))


def voldoet(versie, eis):
    """Versie tegen een eis als '>=0.1.0', '<1.0.0', '==0.2.0', '0.2.0' of '>=0.1,<1' (alle delen moeten kloppen)."""
    if not eis:
        return True
    v = versie_tuple(versie)
    for deel in str(eis).split(","):
        m = re.fullmatch(r"\s*(>=|<=|==|=|>|<)?\s*([0-9][0-9.]*)\s*", deel)
        if not m:
            raise UseCaseFout(f"onbekende versie-eis: {eis!r}")
        op, w = m.group(1) or "==", versie_tuple(m.group(2))
        if not {">=": v >= w, "<=": v <= w, ">": v > w, "<": v < w, "==": v == w, "=": v == w}[op]:
            return False
    return True


def afhankelijkheden(uc, met_optioneel=False):
    """[(naam, versie-eis of None)] uit `afhankelijk_van`: een naam, of {"naam", "versie", "optioneel"}.
    Met met_optioneel: [(naam, eis, optioneel)]. Een object met `bron` (externe use case: absolute
    URL + vaste versie) wordt nog niet ondersteund."""
    uit = []
    for a in uc.get("afhankelijk_van", []):
        if isinstance(a, str):
            uit.append((a, None, False))
        elif isinstance(a, dict) and "bron" in a:
            raise UseCaseFout(f"externe use cases nog niet ondersteund: {a.get('naam')} uit {a['bron']}")
        elif isinstance(a, dict) and "naam" in a:
            uit.append((a["naam"], a.get("versie"), bool(a.get("optioneel"))))
        else:
            raise UseCaseFout(f"ongeldige afhankelijkheid: {a!r}")
    return uit if met_optioneel else [(n, e) for n, e, _ in uit]


def volgorde(namen, ucs):
    """Topologische volgorde: eerst de afhankelijkheden (in de volgorde van `afhankelijk_van`), elke
    use case één keer. Fout bij een onbekende naam, een cyclus of een versie die niet voldoet."""
    uit, bezig = [], []

    def bezoek(naam, eis=None, door=None):
        if naam not in ucs:
            raise UseCaseFout(f"onbekende use case '{naam}'" + (f" (in afhankelijk_van van {door})" if door else ""))
        if eis and not voldoet(ucs[naam].get("versie", "0.0.0"), eis):
            raise UseCaseFout(f"{door} vraagt {naam} {eis}, beschikbaar is {ucs[naam].get('versie', 'geen versie')}")
        if naam in uit:
            return
        if naam in bezig:
            raise UseCaseFout("cyclus: " + " -> ".join(bezig[bezig.index(naam):] + [naam]))
        bezig.append(naam)
        for dep, dep_eis in afhankelijkheden(ucs[naam]):
            bezoek(dep, dep_eis, naam)
        bezig.pop()
        uit.append(naam)

    for n in namen:
        bezoek(n)
    return uit


def plan(namen, ucs, alle=False):
    """(te laden in volgorde, {naam: reden overgeslagen}). Een use case met status 'ontwerp' en
    alles wat er (niet-optioneel) van afhangt, wordt overgeslagen."""
    orde = volgorde(sorted(ucs) if alle else list(namen), ucs)
    overgeslagen = {}
    for n in orde:
        if ucs[n].get("status") == "ontwerp":
            overgeslagen[n] = "status ontwerp"
            continue
        # Een optionele afhankelijkheid die overgeslagen wordt, blokkeert niet: de use case
        # werkt dan via zijn eigen route (bijv. de demopakketten met laad_cbs.py).
        geblokt = [d for d, _, opt in afhankelijkheden(ucs[n], True) if d in overgeslagen and not opt]
        if geblokt:
            overgeslagen[n] = f"hangt af van {', '.join(geblokt)} (overgeslagen)"
    return [n for n in orde if n not in overgeslagen], overgeslagen


def boom(naam, ucs, _diepte=0, _pad=(), _optioneel=False):
    if naam in _pad:
        raise UseCaseFout("cyclus: " + " -> ".join(_pad + (naam,)))
    uc = ucs.get(naam)
    if uc is None:
        raise UseCaseFout(f"onbekende use case '{naam}'")
    regel = f"{'    ' * max(_diepte - 1, 0)}{'└── ' if _diepte else ''}{naam} {uc.get('versie', '')}".rstrip()
    if uc.get("status"):
        regel += f" [{uc['status']}]"
    if _optioneel:
        regel += " (optioneel)"
    regels = [regel]
    for dep, _, opt in afhankelijkheden(uc, True):
        regels.append(boom(dep, ucs, _diepte + 1, _pad + (naam,), opt))
    return "\n".join(regels)


def gebruiker(uc):
    return uc.get("gebruiker") or (uc.get("persona") or {}).get("rol", "")


def index_markdown(ucs):
    regels = ["| Use case | ID | Titel | Gebruiker | Status | Versie | Afhankelijk van |",
              "|---|---|---|---|---|---|---|"]
    for naam, uc in sorted(ucs.items()):
        deps = ", ".join(f"{d}{' (opt.)' if o else ''}" for d, _, o in afhankelijkheden(uc, True)) or "–"
        regels.append(f"| [{naam}](./{naam}/README.md) | {uc.get('id', '–')} | {uc.get('titel', '')} | "
                      f"{gebruiker(uc)} | {uc.get('status', '–')} | {uc.get('versie', '–')} | {deps} |")
    return "\n".join(regels)


def werk_index_bij(controleer=False, readme=README, ucs=None):
    """Index tussen de markers in usecases/README.md bijwerken (of alleen vergelijken). True = actueel."""
    tekst = Path(readme).read_text(encoding="utf-8").replace("\r\n", "\n")
    if INDEX_START not in tekst or INDEX_EINDE not in tekst:
        raise UseCaseFout(f"markers {INDEX_START} / {INDEX_EINDE} ontbreken in {readme}")
    voor, rest = tekst.split(INDEX_START, 1)
    _, na = rest.split(INDEX_EINDE, 1)
    nieuw = f"{voor}{INDEX_START}\n{index_markdown(ucs or lees_usecases())}\n{INDEX_EINDE}{na}"
    if nieuw == tekst:
        return True
    if controleer:
        return False
    Path(readme).write_text(nieuw, encoding="utf-8", newline="\n")
    return True


# ------------------------------------------------------------------ controleren

def _schema_fouten(data, schema_pad):
    from omnitwin.laden.registratie import valideer
    schema = json.loads(Path(schema_pad).read_text(encoding="utf-8"))
    return valideer({k: v for k, v in data.items() if not k.startswith("_")}, schema, schema)


def bestandsfouten(map_, naam=None):
    """Een use case is declaratief: geen code of uitvoerbare bestanden in de map."""
    map_ = Path(map_)
    naam = naam or map_.name
    fouten = []
    for p in sorted(map_.rglob("*")):
        if p.is_dir() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(map_).as_posix()
        if f"{naam}/{rel}" in UIT_TE_FASEREN:
            continue
        toegestaan = (TOEGESTAAN_BEWIJS if rel.startswith("bewijs/")
                      else TOEGESTAAN_DATA if rel.startswith("data/") else TOEGESTAAN)
        if p.suffix.lower() not in toegestaan:
            fouten.append(f"{rel}: bestandstype {p.suffix or '(geen)'} niet toegestaan in een use case "
                          f"(alleen {', '.join(sorted(toegestaan))}); code hoort in de kern (omnitwin.bronadapters)")
        elif p.suffix.lower() == ".pdf" and (p.stat().st_size > MAX_PDF_BYTES or not p.read_bytes().startswith(b"%PDF")):
            fouten.append(f"{rel}: een PDF in een use case is een klein voorbeelddocument (geldige PDF, "
                          f"hoogstens {MAX_PDF_BYTES // 1024} KB)")
    return fouten


def _bron_fouten(bron, pad):
    """Bekende adapter, toegestane map of domein (zonder iets op te halen)."""
    from omnitwin.bronadapters import ADAPTERS, TOEGESTANE_MAPPEN, BronFout, controleer_url
    if not isinstance(bron, dict) or bron.get("adapter") not in ADAPTERS:
        return [f"{pad}: onbekende adapter {(bron or {}).get('adapter')!r} (bekend: {', '.join(sorted(ADAPTERS))})"]
    fouten = []
    if bron.get("url"):
        try:
            controleer_url(bron["url"])
        except BronFout as e:
            fouten.append(f"{pad}: {e}")
    if bron["adapter"] == "lokaal-bestand":
        m = re.fullmatch(r"\$\{([A-Z_]+)\}/.+", str(bron.get("pad", "")))
        if not m or m.group(1) not in TOEGESTANE_MAPPEN or ".." in bron["pad"]:
            fouten.append(f"{pad}: pad moet ${{VAR}}/... zijn met VAR uit {TOEGESTANE_MAPPEN}")
    if bron["adapter"] == "usecase-bestand" and (
            ".." in str(bron.get("pad", "")) or not str(bron.get("pad", "")).endswith((".json", ".csv"))):
        fouten.append(f"{pad}: usecase-bestand alleen .json/.csv in de use case")
    return fouten


def _stappen_fouten(stappen, pad):
    from omnitwin.bronadapters.bewerkingen import BewerkingFout, naam_van
    fouten = []
    for i, stap in enumerate(stappen or []):
        try:
            naam = naam_van(stap)
        except BewerkingFout as e:
            fouten.append(f"{pad}.bewerkingen[{i}]: {e}")
            continue
        p = stap[naam]
        if isinstance(p, dict) and isinstance(p.get("bron"), dict):
            fouten += _bron_fouten(p["bron"], f"{pad}.bewerkingen[{i}].{naam}.bron")
            fouten += _stappen_fouten(p.get("bewerkingen"), f"{pad}.bewerkingen[{i}].{naam}")
    return fouten


def lees_dataset(uc, ds):
    return json.loads((Path(uc["_map"]) / ds["registratie"]).read_text(encoding="utf-8"))


def registratie_voor_api(dataset):
    """De registratie zoals POST /api/laden/v1/datasets hem krijgt: zonder bron, bewerkingen, levering."""
    return {k: v for k, v in dataset.items() if k not in NIET_REGISTREREN}


def dataset_fouten(uc, ds, spec=None):
    from omnitwin.laden.registratie import valideer_registratie
    pad = ds.get("registratie", "?")
    if not ds.get("registratie") or not (Path(uc["_map"]) / ds["registratie"]).exists():
        return [f"{pad}: ontbreekt"]
    d = lees_dataset(uc, ds)
    fouten = [f"{pad}: {f}" for f in _schema_fouten(d, DATASET_SCHEMA)]
    if d.get("id") != ds["id"]:
        fouten.append(f"{pad}: id {d.get('id')!r} is niet {ds['id']!r}")
    if ds.get("route") in ("laden", "compat"):
        fouten += [f"{pad}: registratie: {f}" for f in valideer_registratie(registratie_voor_api(d), spec)]
    if ds.get("toegang"):
        # Toegang per laag (#254): het manifest toont hem, dct:accessRights in de registratie bepaalt hem
        from omnitwin.laden.catalogus import toegang_van
        echt = toegang_van(d.get("beschrijving") or {})
        if echt != ds["toegang"]:
            fouten.append(f"{pad}: toegang {ds['toegang']!r} in het manifest, maar dct:accessRights geeft {echt!r}")
    fouten += _bron_fouten(d.get("bron"), f"{pad}.bron")
    fouten += _stappen_fouten(d.get("bewerkingen"), pad)
    for vnaam, v in (d.get("varianten") or {}).items():
        stappen = v.get("bewerkingen", d.get("bewerkingen", []))
        onbekend = set(v.get("sla_over", [])) - {s.get("id") for s in stappen}
        if onbekend:
            fouten.append(f"{pad}.varianten.{vnaam}: onbekende stappen {sorted(onbekend)}")
        if "bron" in v:
            fouten += _bron_fouten(v["bron"], f"{pad}.varianten.{vnaam}.bron")
        if "bewerkingen" in v:
            fouten += _stappen_fouten(v["bewerkingen"], f"{pad}.varianten.{vnaam}")
    return fouten


def valideer_manifest(uc, naam=None):
    fouten = _schema_fouten(uc, SCHEMA)
    if naam and uc.get("naam") not in (None, naam):
        fouten.append(f"$.naam: '{uc.get('naam')}' is niet gelijk aan de mapnaam '{naam}'")
    if "datasets" in uc:
        fouten += [f"$: verplicht veld '{v}' ontbreekt (volledige vorm)" for v in VOLLEDIG if v not in uc]
    if uc.get("_map"):
        fouten += bestandsfouten(uc["_map"], naam)
    ids = [ds.get("id") for ds in uc.get("datasets", [])]
    actoren = [a.get("naam") for a in uc.get("actoren", [])]
    for dubbel in sorted({a for a in actoren if actoren.count(a) > 1}):
        fouten.append(f"actoren: naam {dubbel} komt meer dan eens voor")
    for c in uc.get("controles", []):
        # Een rechtencontrole mag juist een dataset van een ander noemen (403 op een andere dataset)
        if c.get("dataset") and c["dataset"] not in ids and c["type"] != "recht":
            fouten.append(f"controle {c['type']}: dataset {c['dataset']} niet in datasets")
        if c.get("actor") and c["actor"] not in actoren:
            fouten.append(f"controle {c['type']}: actor {c['actor']} niet in actoren")
        if c["type"] == "recht":
            extra = {"registreren": (), "bekijken": ("pad",)}.get(c.get("actie"), ("dataset",))
            nodig = ("actor", "actie", "toegestaan") + extra
            fouten += [f"controle recht: veld {v} ontbreekt" for v in nodig if v not in c]
    return fouten


def bronnen():
    return {k: os.environ.get(k) for k in ("SWF_DUMP_DIR", "SWF_DOCS_DIR", "SWF_GEO_DIR", "SWF_DB_DUMP", "SWF_EXPORT_DIR",
                                        "DATA_CACHE")}


def schema_paden(uc, dataset):
    return {k: Path(uc["_map"]) / v for k, v in (dataset["levering"].get("schema") or {}).items()} or None


def met_variant(d, variant):
    """De dataset zoals de variant hem levert: andere bron, bewerkingen en beschrijving (DCAT) als de
    variant die noemt. Geeft (dataset, sla_over)."""
    if not variant:
        return d, []
    v = (d.get("varianten") or {}).get(variant)
    if v is None:
        raise UseCaseFout(f"{d['id']}: onbekende variant {variant!r}")
    d = {**d, "bron": v.get("bron", d["bron"]), "bewerkingen": v.get("bewerkingen", d.get("bewerkingen", []))}
    if v.get("beschrijving"):
        d["beschrijving"] = {**(d.get("beschrijving") or {}), **v["beschrijving"]}
    return d, v.get("sla_over", [])


def maak_levering(uc, ds, uit, variant=None, bron_env=None):
    """Bron ophalen, bewerken en als levering schrijven. Geeft (paden, rapport van de bewerkingen).
    Zonder variant: eerst een variant met `als_beschikbaar` (bijv. de echte interne bron), anders de
    standaardbron. Gooit omnitwin.bronadapters.GeenBron (LookupError) als de bron hier niet beschikbaar is."""
    from omnitwin.bronadapters import haal
    from omnitwin.bronadapters.bewerkingen import voer_uit
    from omnitwin.bronadapters.schrijvers import schrijf
    basis = lees_dataset(uc, ds)
    ctx = {"bronnen": bron_env if bron_env is not None else bronnen(), "usecase_map": uc["_map"]}
    pogingen = [variant] if variant else [n for n, v in (basis.get("varianten") or {}).items()
                                           if v.get("als_beschikbaar")] + [None]
    for i, naam in enumerate(pogingen):
        d, sla_over = met_variant(basis, naam)
        try:
            tabellen = haal(d["bron"], ctx)
        except LookupError:
            if i == len(pogingen) - 1:
                raise
            continue  # variant niet beschikbaar: volgende (uiteindelijk de standaardbron)
        gelezen = {t: len(r) for t, r in tabellen.items()}
        tabellen, rapport = voer_uit(tabellen, d.get("bewerkingen", []), ctx, sla_over)
        paden = schrijf(tabellen, d, uit, schema_paden(uc, d))
        return paden, {"gelezen": gelezen, "geschreven": {t: len(r) for t, r in tabellen.items()},
                       "bewerkingen": rapport, "variant": naam}


def controleer(naam, uit=None, ucs=None, variant=None, bron_env=None):
    """Manifest, bestanden, afhankelijkheden, registraties en de lokaal gemaakte leveringen. Zonder API."""
    from omnitwin.bronadapters import BronFout
    from omnitwin.laden.levering import OntbrekendPakket, valideer_levering
    from omnitwin.laden.registratie import laad_openapi
    ucs = ucs or lees_usecases()
    if naam not in ucs:
        raise UseCaseFout(f"onbekende use case '{naam}'")
    uc = ucs[naam]
    r = {"naam": naam, "versie": uc.get("versie"), "manifest": valideer_manifest(uc, naam), "datasets": {}, "controles": []}
    try:
        r["volgorde"] = volgorde([naam], ucs)
    except UseCaseFout as e:
        r["manifest"].append(str(e))
    spec = laad_openapi() if uc.get("datasets") else None
    uit = Path(uit) if uit else Path(tempfile.mkdtemp(prefix=f"usecase-{naam}-"))
    uit.mkdir(parents=True, exist_ok=True)
    for ds in uc.get("datasets", []):
        d = r["datasets"][ds["id"]] = {"fouten": dataset_fouten(uc, ds, spec), "leveringen": [], "status": "ok"}
        if d["fouten"]:
            d["status"] = "fout"
            continue
        try:
            paden, d["bewerkingen"] = maak_levering(uc, ds, uit / ds["id"], variant, bron_env)
        except LookupError as e:
            d["status"] = f"overgeslagen: {e}"
            continue
        except (BronFout, ValueError) as e:
            d["status"], d["fouten"] = "fout", [f"levering maken: {e}"]
            continue
        dataset = lees_dataset(uc, ds)
        for p in paden:
            try:
                d["leveringen"] += valideer_levering(registratie_voor_api(dataset), p, schema_paden(uc, dataset))
            except OntbrekendPakket as e:
                # Niet gecontroleerd (bijv. frictionless ontbreekt), maar wel geteld: anders geeft elke
                # aantal-controle 0 en daarmee een valse fout
                d["leveringen"].append({"bestand": p.name, "geldig": None, "aantallen": tel_regels(p), "fouten": [str(e)]})
        if any(lv["geldig"] is False for lv in d["leveringen"]):
            d["status"] = "fout"
    for c in uc.get("controles", []):
        r["controles"].append(controle_lokaal(c, r))
    r["geldig"] = not r["manifest"] and all(d["status"] != "fout" for d in r["datasets"].values()) \
        and all(c["resultaat"] != "fout" for c in r["controles"])
    r["uitvoer"] = str(uit)
    (uit / "controle.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return r


def tel_regels(pad):
    """Regels per resource in een Data Package-zip, zonder validatie ({} voor andere bestanden)."""
    import csv
    import io
    import zipfile
    if Path(pad).suffix != ".zip":
        return {}
    uit = {}
    with zipfile.ZipFile(pad) as z:
        for r in json.loads(z.read("datapackage.json")).get("resources", []):
            tekst = z.read(r["path"]).decode("utf-8-sig")
            uit[r["name"]] = sum(1 for _ in csv.DictReader(io.StringIO(tekst)))
    return uit


def _aantal(d, resource):
    """Aantal regels of features in de leveringen van een dataset (eventueel van één resource)."""
    tot = 0
    for lv in d["leveringen"]:
        a = lv.get("aantallen") or {}
        if resource:
            tot += a.get(resource) or 0
        else:
            tot += a.get("features") or a.get("waarnemingen") or a.get("waarden") or a.get("kompasprofiel") or 0
    return tot


def _vergelijk(waarde, c):
    if "gelijk" in c and waarde != c["gelijk"]:
        return f"{waarde} ≠ {c['gelijk']}"
    if "minimaal" in c and waarde < c["minimaal"]:
        return f"{waarde} < {c['minimaal']}"
    if "maximaal" in c and waarde > c["maximaal"]:
        return f"{waarde} > {c['maximaal']}"
    return None


def controle_lokaal(c, r):
    """Controles die zonder API kunnen: aantal (op de gemaakte levering) en bewerking (telling per reden)."""
    uit = {"controle": c, "resultaat": "alleen-api"}
    d = r["datasets"].get(c.get("dataset"))
    if d is None or c["type"] not in ("aantal", "bewerking"):
        return uit
    if not d["leveringen"]:
        uit["resultaat"] = "overgeslagen"
        return uit
    if c["type"] == "aantal":
        waarde = _aantal(d, c.get("resource"))
    else:
        waarde = (d.get("bewerkingen") or {}).get("bewerkingen", {}).get(c["reden"], 0)
    verschil = _vergelijk(waarde, c)
    uit.update(resultaat="fout" if verschil else "ok", waarde=waarde, melding=verschil)
    return uit


# ------------------------------------------------------------------ installeren en testen (laad-API)

LAAD_API = "/api/laden/v1"
MEDIATYPE = {".zip": "application/zip", ".gpkg": "application/geopackage+sqlite3", ".csv": "text/csv",
             ".json": "application/json"}


def basis_url():
    return os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")


def laad_api_beschikbaar(basis=None):
    """True als de laad-API zijn specificatie serveert (GET /api/laden/v1/openapi.json → 200)."""
    import requests
    try:
        return requests.get(f"{basis or basis_url()}{LAAD_API}/openapi.json", timeout=10).status_code == 200
    except requests.RequestException:
        return False


def token_url(basis=None):
    """Tokenendpoint: OMNITWIN_TOKEN_URL, of via discovery van realm KEYCLOAK_REALM (standaard omnitwin)."""
    import requests
    url = os.environ.get("OMNITWIN_TOKEN_URL")
    if not url:
        realm = os.environ.get("KEYCLOAK_REALM", "omnitwin")
        disc = requests.get(f"{basis or basis_url()}/auth/realms/{realm}/.well-known/openid-configuration", timeout=30)
        disc.raise_for_status()
        url = disc.json()["token_endpoint"]
    return url


def token(basis=None):
    """Token voor de machineclient (client credentials) uit OMNITWIN_CLIENT_ID/OMNITWIN_CLIENT_SECRET."""
    import requests
    cid, geheim = os.environ.get("OMNITWIN_CLIENT_ID"), os.environ.get("OMNITWIN_CLIENT_SECRET")
    if not cid or not geheim:
        raise UseCaseFout("OMNITWIN_CLIENT_ID en OMNITWIN_CLIENT_SECRET (machineclient) zijn niet gezet")
    r = requests.post(token_url(basis), data={"grant_type": "client_credentials"}, auth=(cid, geheim), timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


class LaadApi:
    """Dunne client voor /api/laden/v1, de compat-ingang en de beheer-API."""

    def __init__(self, basis=None, tok=None, tokenbron=None):
        """tokenbron: functie die een (nieuw) token geeft; standaard de machineclient uit de omgeving.
        Bij 401 haalt de client eenmaal een nieuw token (access tokens leven 5 minuten)."""
        import requests
        self.basis, self.s = basis or basis_url(), requests.Session()
        self.tokenbron = tokenbron or (None if tok else (lambda: token(self.basis)))
        self.s.headers["Authorization"] = f"Bearer {tok or self.tokenbron()}"
        self.s.hooks["response"].append(self._bij_429)

    def _bij_429(self, r, *args, **kwargs):
        """Rate-limit van de laad-API (Traefik, 429): wachten volgens Retry-After en opnieuw (hooguit 10 keer).
        Bij 401 met een tokenbron: eenmaal een nieuw token en opnieuw."""
        if r.status_code == 401 and self.tokenbron and not getattr(r.request, "_ververst", False):
            self.s.headers["Authorization"] = f"Bearer {self.tokenbron()}"
            nieuw = r.request.copy()
            nieuw.headers["Authorization"] = self.s.headers["Authorization"]
            nieuw._ververst = True
            return self.s.send(nieuw, timeout=kwargs.get("timeout"))
        poging = getattr(r.request, "_poging", 0)
        if r.status_code != 429 or poging >= 10:
            return r
        time.sleep(min(int(r.headers.get("Retry-After", "6") or 6), 60))
        nieuw = r.request.copy()
        nieuw._poging = poging + 1
        return self.s.send(nieuw, timeout=kwargs.get("timeout"))

    @staticmethod
    def _json(r):
        try:
            return {"http": r.status_code, **(r.json() if r.content else {})}
        except ValueError:
            return {"http": r.status_code, "tekst": r.text[:500]}

    def registreer(self, registratie):
        url = f"{self.basis}{LAAD_API}/datasets"
        bestaat = self.s.get(f"{url}/{registratie['id']}", timeout=30).status_code == 200
        r = (self.s.put(f"{url}/{registratie['id']}", json=registratie, timeout=30) if bestaat
             else self.s.post(url, json=registratie, timeout=30))
        r.raise_for_status()
        return r.json()

    def lever(self, ds_id, pad, route="laden", alleen_valideren=False):
        import hashlib
        pad = Path(pad)
        inhoud = pad.read_bytes()
        headers = {"Content-Type": MEDIATYPE[pad.suffix],
                   "Idempotency-Key": f"{ds_id}-{hashlib.sha256(inhoud).hexdigest()[:16]}"}
        if route == "compat":
            soort = "indicator/setup" if pad.name == "definities.json" else "indicator_waarde"
            r = self.s.post(f"{self.basis}{LAAD_API}/compat/swf-monitor/monitor_api/{soort}/inlezen",
                            data=inhoud, headers=headers, timeout=180)
        else:
            r = self.s.post(f"{self.basis}{LAAD_API}/datasets/{ds_id}/leveringen", data=inhoud, headers=headers,
                            params={"wacht": "true", "alleenValideren": str(alleen_valideren).lower()}, timeout=180)
        if r.status_code == 202 and r.headers.get("Location"):
            return self.volg(r.headers["Location"])
        return self._json(r)

    def volg(self, locatie, maximaal=600):
        eind = time.time() + maximaal
        while time.time() < eind:
            r = self.s.get(locatie if locatie.startswith("http") else f"{self.basis}{locatie}", timeout=30)
            r.raise_for_status()
            if r.json().get("status") not in ("ontvangen", "bezig"):
                return self._json(r)
            time.sleep(int(r.headers.get("Retry-After", 5)))
        raise UseCaseFout(f"levering {locatie} niet klaar binnen {maximaal} s")

    def beheer(self, pad_api, bestand):
        r = self.s.put(f"{self.basis}{pad_api}", data=Path(bestand).read_bytes(),
                       headers={"Content-Type": MEDIATYPE[Path(bestand).suffix]}, timeout=60)
        return self._json(r)


class ActorApi:
    """De laad-API met de testaccounts van één use case (#223): registreren als de actor met de realm-rol
    beheerder, leveren als de `client` van de dataset (of de actor met `dataset:<id>:laden` of
    `datasets:laden`), de beheer-route als de client of de beheerder. Ontbreekt zo'n actor, dan de
    machineclient uit de omgeving (OMNITWIN_CLIENT_ID/SECRET)."""

    def __init__(self, uc, accounts=None, basis=None, maak_api=None):
        """accounts: {loginclient, actoren} zoals in .usecase-accounts.json."""
        self.uc, self.basis = uc, basis or basis_url()
        self.accounts = (accounts or {}).get("actoren", {})
        self.loginclient = (accounts or {}).get("loginclient")
        self._maak_api = maak_api or (lambda tokenbron=None: LaadApi(self.basis, tokenbron=tokenbron))
        self._apis = {}

    def actor(self, naam):
        if naam not in self._apis:
            acc = self.accounts.get(naam)
            if acc is None:
                raise UseCaseFout(f"{self.uc.get('naam')}: actor {naam!r} heeft geen testaccount "
                                  "(niet in actoren, of zonder --testaccounts)")
            from omnitwin import testaccounts
            url = token_url(self.basis)
            self._apis[naam] = self._maak_api(tokenbron=lambda: testaccounts.token(acc, self.loginclient, url))
        return self._apis[naam]

    def _terugval(self, wat):
        if "" not in self._apis:
            try:
                self._apis[""] = self._maak_api()
            except UseCaseFout as e:
                raise UseCaseFout(f"{self.uc.get('naam')}: geen actor voor {wat}, en {e}") from None
        return self._apis[""]

    def _met_rol(self, rollen, wat):
        for a in self.uc.get("actoren", []):
            if a["naam"] in self.accounts and set(a["rollen"]) & set(rollen):
                return self.actor(a["naam"])
        return self._terugval(wat)

    def beheerder(self):
        return self._met_rol(("beheerder",), "registreren (realm-rol beheerder)")

    def leverancier(self, ds_id):
        ds = next((d for d in self.uc.get("datasets", []) if d["id"] == ds_id), {})
        if ds.get("client") in self.accounts:
            return self.actor(ds["client"])
        rollen = (f"dataset:{ds_id}:laden", "datasets:laden") + (("beheerder",) if ds.get("route") == "beheer" else ())
        return self._met_rol(rollen, f"leveren van {ds_id}")

    def registreer(self, registratie):
        return self.beheerder().registreer(registratie)

    def lever(self, ds_id, pad, route="laden", alleen_valideren=False):
        return self.leverancier(ds_id).lever(ds_id, pad, route, alleen_valideren)

    def beheer(self, pad_api, bestand):
        return self.leverancier(pad_api.rstrip("/").rsplit("/", 1)[-1]).beheer(pad_api, bestand)

    @property
    def s(self):
        """Sessie voor de lezende controles (aantal, api): die van de beheerder."""
        return self.beheerder().s


def maak_actor_apis(namen, ucs, beheer=None):
    """Testaccounts voor de use cases (met hun afhankelijkheden) die actoren declareren, en per use case
    een ActorApi. Weigert buiten test en dev (omnitwin.testaccounts.toegestaan)."""
    from omnitwin import testaccounts
    apis = {}
    try:
        testaccounts.toegestaan()
        for n in volgorde(namen, ucs):
            accounts = {}
            if ucs[n].get("actoren"):
                actoren = testaccounts.maak(n, ucs[n], beheer)
                accounts = {"loginclient": testaccounts.loginclient(n), "actoren": actoren}
                print(f"👤 {n}: testaccounts {', '.join(a['id'] for a in actoren.values())} "
                      f"(geheimen in {testaccounts.bestand().name}, niet in git)", flush=True)
            apis[n] = ActorApi(ucs[n], accounts)
    except testaccounts.TestaccountFout as e:
        raise UseCaseFout(str(e)) from None
    return apis


def opruimen(namen, ucs, beheer=None):
    """Testaccounts van de use cases (met hun afhankelijkheden) verwijderen. Geeft {naam: [accounts]}."""
    from omnitwin import testaccounts
    try:
        return {n: testaccounts.opruimen(n, beheer) for n in volgorde(namen, ucs) if ucs[n].get("actoren")}
    except testaccounts.TestaccountFout as e:
        raise UseCaseFout(str(e)) from None


def bestanden_van(paden):
    """Leveringsbestanden: een map (swf-json waarden) wordt de JSON-bestanden erin."""
    uit = []
    for p in paden:
        uit += sorted(Path(p).glob("*.json")) if Path(p).is_dir() else [Path(p)]
    return uit


def oude_route(namen, alleen_inrichting=False):
    """Demopakketten zonder `datasets`: via laad_usecase.py (directe databasevulling). Met
    alleen_inrichting: alleen de richting van de indicatoren (de data komt via de laad-API)."""
    if namen:
        extra = ["--inrichting"] if alleen_inrichting else []
        subprocess.run([sys.executable, str(ROOT / "init_data" / "scripts" / "laad_usecase.py"), *extra, *namen],
                       check=True)


def heeft_inrichting(uc):
    """Demopakket met indicatoren in `data.indicatoren` waarvan de richting gezet moet worden."""
    return bool((uc.get("data") or {}).get("indicatoren"))


def installeer_dataset(api, uc, ds, uit, variant=None):
    """Levering maken, registreren (route laden/compat) en leveren. Geeft de status per bestand.
    Eerst de levering: is de bron hier niet beschikbaar, dan wordt er ook niets geregistreerd."""
    route = ds.get("route", "laden")
    paden, rapport = maak_levering(uc, ds, Path(uit) / ds["id"], variant)
    if route in ("laden", "compat"):
        api.registreer(registratie_voor_api(met_variant(lees_dataset(uc, ds), rapport.get("variant"))[0]))
    if route == "beheer":
        return [api.beheer(f"{ds['beheerpad']}/{ds['id']}", p) for p in bestanden_van(paden)]
    return [api.lever(ds["id"], p, route) for p in bestanden_van(paden)]


def _kort(res):
    if isinstance(res, str):
        return res
    return ", ".join(str(lv.get("status", lv.get("http"))) for lv in res)


def mislukt(resultaat):
    """Datasets die fout gingen of afgekeurd werden (niet: overgeslagen omdat de bron hier ontbreekt)."""
    uit = []
    for n, per_ds in (resultaat or {}).items():
        for ds, res in (per_ds if isinstance(per_ds, dict) else {}).items():
            if (isinstance(res, str) and res.startswith("fout")) or (
                    isinstance(res, list) and any(lv.get("status") != "overgeslagen" and (
                        lv.get("status") in ("afgekeurd", "mislukt") or (lv.get("http") or 0) >= 400) for lv in res)):
                uit.append(f"{n}/{ds}")
    return uit


def installeer(namen, alle=False, ucs=None, api=None, uit=None, ook_ontwerp=False, inproces=False, apis=None):
    """Use cases met afhankelijkheden installeren, in volgorde: demopakketten zonder `datasets` via
    laad_usecase.py, use cases met `datasets` via de laad-API, daarna de inrichting van de demopakketten
    met `datasets`. Zonder laad-API: een melding, geen fout. ook_ontwerp: ook use cases met status
    ontwerp (voor `test`). inproces: de laadstraat zonder HTTP (eerste installatie, db-init).
    Een bron die hier niet beschikbaar is (geen netwerk, geen SWF_DUMP_DIR): 'overgeslagen', geen fout.
    apis: {naam: api} per use case (testaccounts, zie maak_actor_apis); anders api voor alles."""
    ucs = ucs or lees_usecases()
    orde, overgeslagen = (volgorde(namen, ucs), {}) if ook_ontwerp else plan(namen, ucs, alle)
    for n, reden in overgeslagen.items():
        print(f"⏭️  {n}: overgeslagen ({reden})")
    oude_route([n for n in orde if "datasets" not in ucs[n]])
    nieuw = [n for n in orde if ucs[n].get("datasets")]
    if nieuw and api is None and apis is None and not inproces and not laad_api_beschikbaar():
        print(f"⏸️  laad-API nog niet beschikbaar ({basis_url()}{LAAD_API}/openapi.json); niet geïnstalleerd: {', '.join(nieuw)}")
        return {n: "laad-API nog niet beschikbaar" for n in nieuw}
    if api is None and apis is None and nieuw:
        if inproces:
            from omnitwin.laden.inproces import InprocesLaadApi
            api = InprocesLaadApi()
        else:
            api = LaadApi()
    uit = Path(uit or tempfile.mkdtemp(prefix="usecases-"))
    resultaat = {}
    for n in nieuw:
        resultaat[n] = {}
        for ds in ucs[n]["datasets"]:
            begin = time.time()
            try:
                resultaat[n][ds["id"]] = installeer_dataset((apis or {}).get(n, api), ucs[n], ds, uit / n)
            except LookupError as e:
                resultaat[n][ds["id"]] = f"overgeslagen: {e}"
            except Exception as e:  # één dataset mag de rest niet tegenhouden (eerste installatie)
                resultaat[n][ds["id"]] = f"fout: {type(e).__name__}: {e}"
            print(f"📦 {n} / {ds['id']}: {_kort(resultaat[n][ds['id']])} ({time.time() - begin:.0f} s)", flush=True)
    try:
        oude_route([n for n in orde if "datasets" in ucs[n] and heeft_inrichting(ucs[n])], alleen_inrichting=True)
    except subprocess.CalledProcessError:  # bijv. installeren op afstand, zonder databasetoegang
        print("⚠️  inrichting (richting van de indicatoren) niet gezet: laad_usecase.py --inrichting faalde "
              "(geen databasetoegang?); de data is wel geladen")
    return resultaat


COMPAT_SOORT = {"swf-monitor-definities": "indicator/setup", "swf-monitor-waarden": "indicator_waarde"}


def controle_recht(c, api, uc):
    """Rechtencontrole (#223): mag `actor` de `actie` op `dataset`? Het verzoek wordt direct na de
    rolcontrole afgewezen (ongeldige parameter of body), dus er verandert niets. Toegestaan = geen 401/403."""
    if not isinstance(api, ActorApi):
        return "overgeslagen: rechtencontrole vraagt testaccounts (test --testaccounts)"
    a = api.actor(c["actor"])
    ds_id, actie = c.get("dataset"), c["actie"]
    if actie == "registreren":
        r = a.s.post(f"{a.basis}{LAAD_API}/datasets", json=[], timeout=30)
    elif actie == "lezen":
        r = a.s.get(f"{a.basis}{LAAD_API}/datasets/{ds_id}", timeout=30)
    elif actie == "bekijken":
        # Toegang per laag (#254): gepubliceerde data lezen zoals de viewer, met het token van de actor
        r = a.s.get(f"{a.basis}{c['pad']}", timeout=60)
        if (r.status_code not in (401, 403)) != c["toegestaan"]:
            return f"HTTP {r.status_code}, verwacht {'toegestaan' if c['toegestaan'] else '401 of 403'}"
        return None
    else:
        route = next((d.get("route") for d in uc.get("datasets", []) if d["id"] == ds_id), "laden")
        url = (f"{a.basis}{LAAD_API}/compat/swf-monitor/monitor_api/{COMPAT_SOORT[ds_id]}/inlezen"
               if route == "compat" and ds_id in COMPAT_SOORT else f"{a.basis}{LAAD_API}/datasets/{ds_id}/leveringen")
        r = a.s.post(url, params={"alleenValideren": "rechtencontrole"}, data=b"",
                     headers={"Content-Type": "application/json"}, timeout=30)
    if r.status_code == 401:
        return f"HTTP 401: token van {c['actor']} geweigerd"
    if (r.status_code != 403) != c["toegestaan"]:
        return f"HTTP {r.status_code}, verwacht {'toegestaan' if c['toegestaan'] else '403'}"
    return None


def controle_api(c, api, uc):
    """Een controle uit het manifest tegen een draaiende installatie. None = geslaagd, anders de melding.
    Met testaccounts (ActorApi) voert `actor` de controle uit; zonder testaccounts wordt `actor`
    genegeerd (de machineclient uit de omgeving) en zijn rechtencontroles overgeslagen."""
    import requests
    t = c["type"]
    if t == "recht":
        return controle_recht(c, api, uc)
    if c.get("actor") and isinstance(api, ActorApi):
        api = api.actor(c["actor"])
    if t == "api":
        headers = {} if c.get("anoniem") else dict(api.s.headers)
        r = requests.get(f"{api.basis}{c['pad']}", headers=headers, timeout=60)
        if r.status_code != c.get("status", 200):
            return f"HTTP {r.status_code}, verwacht {c.get('status', 200)}"
        grenzen = (c.get("minimaal_aantal"), c.get("maximaal_aantal"))
        if grenzen != (None, None) and r.status_code == 200:
            data = r.json()
            n = len(data.get("features", data.get("datasets", data.get("indicatoren", [])))) if isinstance(data, dict) else len(data)
            if c.get("minimaal_aantal") is not None and n < c["minimaal_aantal"]:
                return f"{n} resultaten, verwacht ≥ {c['minimaal_aantal']}"
            if c.get("maximaal_aantal") is not None and n > c["maximaal_aantal"]:
                return f"{n} resultaten, verwacht ≤ {c['maximaal_aantal']}"
        return None
    if t == "aantal":
        if c.get("resource"):
            return None  # per resource alleen lokaal (controleer); de API telt de hele levering
        r = api.s.get(f"{api.basis}{LAAD_API}/datasets/{c['dataset']}", timeout=30)
        r.raise_for_status()
        laatste = (r.json().get("laatsteLevering") or {}).get("id")
        lv = api.s.get(f"{api.basis}{LAAD_API}/leveringen/{laatste}", timeout=30).json()
        return _vergelijk((lv.get("aantallen") or {}).get("gepubliceerd", 0), c)
    if t in ("afkeuring", "idempotent"):
        ds = next(d for d in uc["datasets"] if d["id"] == c["dataset"])
        route = ds.get("route", "laden")
        paden, _ = maak_levering(uc, ds, Path(tempfile.mkdtemp()), c.get("variant"))
        bestanden = bestanden_van(paden)
        if t == "afkeuring":
            lv, codes = {}, set()
            for p in bestanden:
                lv = api.lever(c["dataset"], p, route, alleen_valideren=route == "laden")
                codes = {f.get("code") for f in lv.get("fouten", [])}
                if lv.get("http") == 422 and c["code"] in codes:
                    return None
            return f"geen levering afgekeurd met {c['code']} (laatste: HTTP {lv.get('http')}, codes {sorted(x for x in codes if x)})"
        een, twee = (api.lever(c["dataset"], bestanden[0], route) for _ in range(2))
        if een.get("versie") != twee.get("versie"):
            return f"tweede levering gaf versie {twee.get('versie')}, eerste {een.get('versie')}"
        return None
    if t in ("chat", "viewer"):
        return f"overgeslagen: {t}-controles nog niet in de uitvoerder (handmatig, met screenshot in bewijs/)"
    if t == "bewerking":
        return None  # lokaal gecontroleerd (controleer)
    return f"onbekend controletype {t}"


def test(naam, ucs=None, api=None, testaccounts=False, apis=None):
    """Installeer de use case (met afhankelijkheden) en voer de controles uit tegen de API.
    None als de laad-API (nog) niet beschikbaar is. testaccounts: eerst de actoren als testaccounts
    aanmaken (alleen test/dev); installeren en controleren gebeurt dan als die actoren."""
    ucs = ucs or lees_usecases()
    if ("datasets" in ucs[naam] or testaccounts) and not laad_api_beschikbaar():
        print(f"⏸️  laad-API nog niet beschikbaar; {naam} niet getest")
        return None
    if testaccounts and apis is None:
        apis = maak_actor_apis([naam], ucs)
    installeer([naam], ucs=ucs, api=api, ook_ontwerp=True, apis=apis)
    api = (apis or {}).get(naam) or api or LaadApi()
    uit = []
    for c in ucs[naam].get("controles", []):
        try:
            melding = controle_api(c, api, ucs[naam])
        except LookupError as e:  # bron hier niet beschikbaar (afkeuring/idempotent maken een levering)
            melding = f"overgeslagen: {e}"
        resultaat = "ok" if melding is None else ("overgeslagen" if str(melding).startswith("overgeslagen") else "fout")
        uit.append({"controle": c, "resultaat": resultaat, "melding": melding})
        teken = {"ok": "✅", "overgeslagen": "⏭️ ", "fout": "❌"}[resultaat]
        wat = c.get("omschrijving", c.get("pad", c.get("dataset", c.get("stap", ""))))
        print(f"{teken} {c['type']}: {wat} {melding or ''}".rstrip())
    return uit


# ------------------------------------------------------------------ CLI

def _print_controle(r):
    for f in r["manifest"]:
        print(f"❌ manifest: {f}")
    for ds, d in r["datasets"].items():
        teken = "✅" if d["status"] == "ok" else ("⏭️ " if d["status"].startswith("overgeslagen") else "❌")
        print(f"{teken} {ds}: {d['status']}")
        for f in d["fouten"]:
            print(f"     {f}")
        if d.get("bewerkingen"):
            b = d["bewerkingen"]
            print(f"     bron {b['gelezen']} → levering {b['geschreven']}; {b['bewerkingen']}")
        for lv in d["leveringen"]:
            status = {True: "geldig", False: "ONGELDIG", None: "niet gecontroleerd"}[lv["geldig"]]
            print(f"     {lv['bestand']}: {status} {lv.get('aantallen', {})}")
            for f in lv.get("fouten", [])[:5]:
                print(f"         {f}")
    for cr in r["controles"]:
        if cr["resultaat"] != "alleen-api":
            c = cr["controle"]
            print(f"   controle {c['type']} {c.get('dataset', '')} {c.get('resource', c.get('reden', ''))}: "
                  f"{cr['resultaat']} {cr.get('waarde', '')} {cr.get('melding') or ''}".rstrip())
    print(f"{'✅ geldig' if r['geldig'] else '❌ niet geldig'}; uitvoer: {r['uitvoer']}")


def bewijs_cli(a, ucs, p):
    """`bewijs`: stappen uitvoeren tegen OMNITWIN_BASE_URL, daarna de galerij bijwerken. Exit 1 als een
    use case niet geslaagd is."""
    from omnitwin import usecase_bewijs
    if not a.namen and not a.alle:
        p.error("geef een of meer namen, of --alle")
    onbekend = [n for n in a.namen if n not in ucs]
    if onbekend:
        raise UseCaseFout(f"onbekende use case: {', '.join(onbekend)}")
    namen = a.namen or [n for n, uc in sorted(ucs.items())
                        if uc.get("status") == "actief" and usecase_bewijs.stappen(uc)]
    tok = None
    if os.environ.get("OMNITWIN_CLIENT_ID"):
        tok = token  # functie: tokens verlopen tijdens een lange run
    else:
        print("⚠️  geen machineclient (OMNITWIN_CLIENT_ID/OMNITWIN_CLIENT_SECRET): geen leveringsstatus en "
              "geen controles van type aantal")
    res = usecase_bewijs.maak(namen, ucs, basis_url(), tok, volledig=not a.zonder_volledig)
    usecase_bewijs.werk_galerij_bij(ucs)
    if a.zip:
        print(f"📦 volledig bewijs: {usecase_bewijs.zip_volledig(Path(a.zip), namen)}")
    mislukt_ = [n for n, v in res.items() if isinstance(v, dict) and not v["geslaagd"]]
    if mislukt_:
        print(f"❌ niet geslaagd: {', '.join(mislukt_)}")
        return 1
    return 0


def main(argv=None):
    from omnitwin.testaccounts import TestaccountFout
    p = argparse.ArgumentParser(prog="python -m omnitwin.usecases", description="Use-case-uitvoerder")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lijst", help="naam, versie, status, titel en afhankelijkheden")
    b = sub.add_parser("boom", help="afhankelijkheden als boom")
    b.add_argument("naam")
    i = sub.add_parser("index", help="index-tabel in usecases/README.md bijwerken")
    i.add_argument("--controleer", action="store_true", help="alleen controleren (exit 1 als hij niet actueel is)")
    c = sub.add_parser("controleer", help="manifest, afhankelijkheden en levering lokaal controleren (zonder API)")
    c.add_argument("naam")
    c.add_argument("--uit", help="map voor de leveringen (standaard een tijdelijke map)")
    c.add_argument("--variant", help="variant van de leveringen (zie varianten in datasets/<id>.json)")
    ins = sub.add_parser("installeer", help="use case(s) met afhankelijkheden installeren (laad-API of laad_usecase.py)")
    ins.add_argument("namen", nargs="*")
    ins.add_argument("--alle", action="store_true")
    ins.add_argument("--inproces", action="store_true",
                     help="laadstraat zonder HTTP en token (eerste installatie in db-init; vereist databasetoegang)")
    TA = ("actoren als tijdelijke testaccounts in Keycloak (alleen test/dev: OMNITWIN_TESTACCOUNTS=1, "
          "niet OMNITWIN_OMGEVING=productie); geheimen in .usecase-accounts.json")
    ins.add_argument("--testaccounts", action="store_true", help=TA)
    t = sub.add_parser("test", help="installeren en de controles tegen de API uitvoeren")
    t.add_argument("naam")
    t.add_argument("--testaccounts", action="store_true", help=TA + "; ook de rechtencontroles")
    op = sub.add_parser("opruimen", help="testaccounts van de use case(s) en hun afhankelijkheden verwijderen")
    op.add_argument("namen", nargs="+")
    bw = sub.add_parser("bewijs", help="bewijsstappen uitvoeren: screenshots en bewijs.json (Playwright, #225)")
    bw.add_argument("namen", nargs="*")
    bw.add_argument("--alle", action="store_true", help="alle actieve use cases met bewijs.stappen")
    bw.add_argument("--zonder-volledig", action="store_true", help="geen originelen in bewijs/volledig/")
    bw.add_argument("--zip", help="daarna het volledige bewijs als zip (voor de GitHub-release)")
    g = sub.add_parser("galerij", help="galerij in README.md en screenshots in de README's van de use cases bijwerken")
    g.add_argument("--controleer", action="store_true", help="alleen controleren (exit 1 als hij niet actueel is)")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # Windows-console zonder UTF-8
    try:
        ucs = lees_usecases()
        if a.cmd == "lijst":
            for n, uc in sorted(ucs.items()):
                deps = ", ".join(d for d, _ in afhankelijkheden(uc)) or "-"
                print(f"{n:26} {uc.get('versie', '-'):7} {uc.get('status', '-'):8} {uc.get('titel', '')}  [afh.: {deps}]")
        elif a.cmd == "boom":
            print(boom(a.naam, ucs))
        elif a.cmd == "index":
            actueel = werk_index_bij(controleer=a.controleer, ucs=ucs)
            print(("index actueel" if a.controleer else "index bijgewerkt") if actueel
                  else "index niet actueel: python -m omnitwin.usecases index")
            return 0 if actueel else 1
        elif a.cmd == "controleer":
            r = controleer(a.naam, a.uit, ucs, a.variant)
            _print_controle(r)
            return 0 if r["geldig"] else 1
        elif a.cmd == "installeer":
            if not a.namen and not a.alle:
                p.error("geef een of meer namen, of --alle")
            apis = None
            if a.testaccounts:
                if a.inproces:
                    p.error("--testaccounts gaat via de laad-API, niet met --inproces")
                if not laad_api_beschikbaar():
                    print(f"⏸️  laad-API nog niet beschikbaar ({basis_url()}{LAAD_API}/openapi.json); geen testaccounts")
                    return 0
                apis = maak_actor_apis(sorted(ucs) if a.alle else a.namen, ucs)
            fout = mislukt(installeer(a.namen, a.alle, ucs, inproces=a.inproces, apis=apis))
            if fout:
                print(f"❌ niet geladen: {', '.join(fout)}")
                return 1
        elif a.cmd == "test":
            uit = test(a.naam, ucs, testaccounts=a.testaccounts)
            return 0 if uit is None or all(c["resultaat"] != "fout" for c in uit) else 1
        elif a.cmd == "opruimen":
            for n, weg in opruimen(a.namen, ucs).items():
                print(f"🧹 {n}: {', '.join(weg) if weg else 'geen testaccounts'}")
        elif a.cmd == "bewijs":
            return bewijs_cli(a, ucs, p)
        elif a.cmd == "galerij":
            from omnitwin import usecase_bewijs
            actueel = usecase_bewijs.werk_galerij_bij(ucs, controleer=a.controleer)
            print(("galerij actueel" if a.controleer else "galerij bijgewerkt") if actueel
                  else "galerij niet actueel: python -m omnitwin.usecases galerij")
            return 0 if actueel else 1
    except (UseCaseFout, TestaccountFout) as e:
        print(f"❌ {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
