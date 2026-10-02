"""
Use-case-uitvoerder
===================
Eén ingang voor alle use cases (`usecases/<naam>/`). Een use case is een pakket met een
manifest (`usecase.json`, schema `usecases/usecase.schema.json`), zoals een app: naam,
versie, afhankelijkheden, rechten, datasets en controles. **Een use case bevat geen code:**
waar de data vandaan komt en hoe hij wordt bewerkt, staat declaratief in
`datasets/<id>.json` (schema `usecases/dataset.schema.json`); de kern voert dat uit met de
bronadapters (`omnitwin.bronadapters`) en de laad-API-validatie (`omnitwin.laden`).

    python -m omnitwin.usecases lijst
    python -m omnitwin.usecases boom <naam>
    python -m omnitwin.usecases index [--controleer]
    python -m omnitwin.usecases controleer <naam> [--uit MAP] [--variant NAAM]
    python -m omnitwin.usecases bewijs <naam>

`controleer` werkt zonder draaiende stack: manifest, bestanden in de map, afhankelijkheden,
registraties, en de levering(en) maken en valideren tegen het profiel. Bronnen komen uit
de omgeving: `SWF_DUMP_DIR`, `SWF_DOCS_DIR`, `SWF_GEO_DIR`, `SWF_DB_DUMP`, `DATA_CACHE`
(standaard ./data-cache), en open bronnen via https (allowlist in `omnitwin.bronadapters`).
Ontbreekt een bron, dan is die dataset 'overgeslagen', geen fout.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USECASES_DIR = ROOT / "usecases"
SCHEMA = USECASES_DIR / "usecase.schema.json"
DATASET_SCHEMA = USECASES_DIR / "dataset.schema.json"
README = USECASES_DIR / "README.md"
INDEX_START, INDEX_EINDE = "<!-- usecase-index:start -->", "<!-- usecase-index:end -->"
VOLLEDIG = ("naam", "versie", "titel", "vraag", "gebruiker", "status", "afhankelijk_van", "rechten", "datasets", "controles")
# Een use case is declaratief: alleen deze bestanden. bewijs/ wordt gevuld door de uitvoerder (niet in git).
TOEGESTAAN = {".json", ".md", ".csv"}
TOEGESTAAN_BEWIJS = {".json", ".md", ".png", ".jpg", ".jpeg", ".webp"}
# Bestaande code in use cases, uit te faseren naar een kernadapter (niet nieuw toevoegen).
UIT_TE_FASEREN = {"hittestress/maak_data.py"}
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
        toegestaan = TOEGESTAAN_BEWIJS if rel.startswith("bewijs/") else TOEGESTAAN
        if p.suffix.lower() not in toegestaan:
            fouten.append(f"{rel}: bestandstype {p.suffix or '(geen)'} niet toegestaan in een use case "
                          f"(alleen {', '.join(sorted(toegestaan))}); code hoort in de kern (omnitwin.bronadapters)")
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
    fouten += _bron_fouten(d.get("bron"), f"{pad}.bron")
    fouten += _stappen_fouten(d.get("bewerkingen"), pad)
    ids = {s.get("id") for s in d.get("bewerkingen", [])}
    for vnaam, v in (d.get("varianten") or {}).items():
        onbekend = set(v.get("sla_over", [])) - ids
        if onbekend:
            fouten.append(f"{pad}.varianten.{vnaam}: onbekende stappen {sorted(onbekend)}")
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
    for c in uc.get("controles", []):
        if c.get("dataset") and c["dataset"] not in ids:
            fouten.append(f"controle {c['type']}: dataset {c['dataset']} niet in datasets")
    return fouten


def bronnen():
    return {k: os.environ.get(k) for k in ("SWF_DUMP_DIR", "SWF_DOCS_DIR", "SWF_GEO_DIR", "SWF_DB_DUMP", "DATA_CACHE")}


def schema_paden(uc, dataset):
    return {k: Path(uc["_map"]) / v for k, v in (dataset["levering"].get("schema") or {}).items()} or None


def maak_levering(uc, ds, uit, variant=None, bron_env=None):
    """Bron ophalen, bewerken en als levering schrijven. Geeft (paden, rapport van de bewerkingen).
    Gooit omnitwin.bronadapters.GeenBron (LookupError) als een bron hier niet beschikbaar is."""
    from omnitwin.bronadapters import haal
    from omnitwin.bronadapters.bewerkingen import voer_uit
    from omnitwin.bronadapters.schrijvers import schrijf
    d = lees_dataset(uc, ds)
    ctx = {"bronnen": bron_env if bron_env is not None else bronnen(), "usecase_map": uc["_map"]}
    sla_over = ((d.get("varianten") or {}).get(variant) or {}).get("sla_over", []) if variant else []
    tabellen = haal(d["bron"], ctx)
    gelezen = {t: len(r) for t, r in tabellen.items()}
    tabellen, rapport = voer_uit(tabellen, d.get("bewerkingen", []), ctx, sla_over)
    paden = schrijf(tabellen, d, uit, schema_paden(uc, d))
    return paden, {"gelezen": gelezen, "geschreven": {t: len(r) for t, r in tabellen.items()}, "bewerkingen": rapport}


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
                d["leveringen"].append({"bestand": p.name, "geldig": None, "aantallen": {}, "fouten": [str(e)]})
        if any(lv["geldig"] is False for lv in d["leveringen"]):
            d["status"] = "fout"
    for c in uc.get("controles", []):
        r["controles"].append(controle_lokaal(c, r))
    r["geldig"] = not r["manifest"] and all(d["status"] != "fout" for d in r["datasets"].values()) \
        and all(c["resultaat"] != "fout" for c in r["controles"])
    r["uitvoer"] = str(uit)
    (uit / "controle.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return r


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


def main(argv=None):
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
    bw = sub.add_parser("bewijs", help="bewijs maken (nog niet in de uitvoerder)")
    bw.add_argument("naam")
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
        elif a.cmd == "bewijs":
            print("Nog niet in de uitvoerder (vervolg). Bewijs (screenshots, bewijs.json) maken: "
                  f"scripts/docs/maak_usecase_bewijs.py; uitvoer in usecases/{a.naam}/bewijs/ (niet in git).")
    except UseCaseFout as e:
        print(f"❌ {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
