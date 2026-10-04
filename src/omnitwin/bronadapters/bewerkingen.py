"""
Declaratieve bewerkingen op Tabellen
====================================
Eén generieke transformer voor het blok `bewerkingen` in `usecases/<naam>/datasets/<id>.json`.
Een bewerking is een object met precies één bewerkingssleutel, plus optioneel:

- `id`: naam van de stap (een variant kan stappen overslaan, zie `varianten` in de dataset);
- `tabel`: alleen op deze tabel (standaard: alle tabellen).

Geen expressies en geen code: alleen de bewerkingen hieronder, met vaste parameters.
Een voorwaarde is {"veld": ..., <toets>: waarde} met toets gelijk, niet_gelijk, in, niet_in,
leeg (true/false), begint_met, niet_begint_met, kleiner_dan, groter_dan.

| Bewerking | Parameters | Wat |
|---|---|---|
| `hernoem` | {oud: nieuw} | velden hernoemen |
| `behoud` | [veld] | alleen deze velden (plus `geometry`) |
| `verwijder` | [veld] | velden weg |
| `constant` | {veld: waarde} | veld met een vaste waarde |
| `kopieer` | {van, naar} | waarde kopiëren |
| `tekst` / `getal` | [veld] | type omzetten (getal: int als het kan, anders float; leeg blijft leeg) |
| `waarde_map` | {veld, map, naar?, standaard?} | waarde vertalen via een tabel |
| `koppel` | {sleutel, bron, op, velden, tabel?, verplicht?, reden?, normaliseer?} | velden overnemen uit een andere bron (bijv. een mappingbestand in de use case); normaliseer: spaties en hoofdletters negeren |
| `afwijzen` | voorwaarde + reden | regels die voldoen eruit, geteld onder de reden |
| `filter` | voorwaarde | alleen regels die voldoen |
| `jaar_uit_datum` | {veld, jaar?, peildatum?} | `JJJJ-01-01` → jaar, andere datum → peildatum, ongeldig → afgewezen (jaar-ongeldig) |
| `jaar_naar_datum` | {veld, naar} | jaar → `JJJJ-01-01` |
| `iso_datumtijd` | [veld] | `JJJJ-MM-DD HH:MM` → `JJJJ-MM-DDTHH:MM:SS` |
| `prefix` | {veld, prefix, als?} | prefix voor codes die niet landelijk uniek zijn |
| `sjabloon` | {naar, sjabloon} | veld uit andere velden: `{veld}`-plaatshouders, verder letterlijk |
| `deel` | {veld, start, eind?, naar} | deel van een tekst (bijv. gemeentecode uit een buurtcode) |
| `snake_case` | true | alle veldnamen naar snake_case (max. 63 tekens) |
| `nummer` | {naar, start?} | volgnummer als sleutel, als de bron geen unieke sleutel heeft (een kaartlaag is een volledige snapshot) |
| `multipolygon` | true | geometrie naar geldige MultiPolygon; repareren telt als `gerepareerd`, leeg of zonder vlak valt af (`geometrie-leeg`, `geometrie-geen-vlak`) |
| `geometrietype` | [type] | alleen deze geometrietypen (bijv. Point, Polygon) |
| `binnen` | {bron, bewerkingen?} | alleen features waarvan een binnenpunt in de (vereniging van de) andere bron ligt |
| `splits_op` | {bron, bewerkingen?, veld, binnen, buiten} | feature opdelen in het deel binnen en buiten een andere bron, met nieuwe code via een sjabloon |
"""

import datetime as dt
import re
from collections import Counter

BEWERKINGEN = (
    "hernoem", "behoud", "verwijder", "constant", "kopieer", "tekst", "getal", "waarde_map", "koppel",
    "afwijzen", "filter", "jaar_uit_datum", "jaar_naar_datum", "iso_datumtijd", "prefix", "sjabloon", "deel",
    "snake_case", "multipolygon", "geometrietype", "binnen", "splits_op", "nummer",
)
TOETSEN = ("gelijk", "niet_gelijk", "in", "niet_in", "leeg", "begint_met", "niet_begint_met", "kleiner_dan", "groter_dan")


class BewerkingFout(ValueError):
    pass


def _leeg(w):
    return w is None or (isinstance(w, str) and w.strip() == "")


def voldoet(r, v):
    """Voorwaarde {veld, <toets>: waarde} tegen record r."""
    w = r.get(v["veld"])
    for toets in TOETSEN:
        if toets not in v:
            continue
        x = v[toets]
        if toets == "gelijk" and not (w == x or str(w) == str(x)):
            return False
        if toets == "niet_gelijk" and (w == x or str(w) == str(x)):
            return False
        if toets == "in" and str(w) not in {str(i) for i in x}:
            return False
        if toets == "niet_in" and str(w) in {str(i) for i in x}:
            return False
        if toets == "leeg" and _leeg(w) != bool(x):
            return False
        if toets == "begint_met" and not str(w or "").startswith(x):
            return False
        if toets == "niet_begint_met" and str(w or "").startswith(x):
            return False
        if toets == "kleiner_dan" and not (not _leeg(w) and float(w) < x):
            return False
        if toets == "groter_dan" and not (not _leeg(w) and float(w) > x):
            return False
    return True


def snake(naam):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(naam))
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    if not s or s[0].isdigit():
        s = f"v_{s}"
    return s[:63]


def _getal(w):
    if _leeg(w):
        return ""
    f = float(w)
    return int(f) if f == int(f) and "." not in str(w) else f


def _sjabloon(tekst, r):
    """{veld} vervangen door de waarde; geen attribuut- of indextoegang (geen str.format)."""
    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: str(r.get(m.group(1), "")), tekst)


def _vereniging(bron, ctx, stappen=None):
    from shapely.ops import unary_union
    from omnitwin.bronadapters import haal
    tab, _ = voer_uit(haal(bron, ctx), stappen or [], ctx)
    geoms = [r["geometry"] for rs in tab.values() for r in rs if r.get("geometry") is not None]
    return unary_union(geoms) if geoms else None


def _stap(naam, p, rijen, rapport, ctx):
    """Eén bewerking op een lijst records. Geeft de nieuwe lijst."""
    if naam == "hernoem":
        return [{p.get(k, k): w for k, w in r.items()} for r in rijen]
    if naam == "behoud":
        houd = set(p) | {"geometry"}
        return [{k: w for k, w in r.items() if k in houd} for r in rijen]
    if naam == "verwijder":
        return [{k: w for k, w in r.items() if k not in set(p)} for r in rijen]
    if naam == "constant":
        return [{**r, **p} for r in rijen]
    if naam == "kopieer":
        return [{**r, p["naar"]: r.get(p["van"])} for r in rijen]
    if naam == "tekst":
        return [{**r, **{v: ("" if r.get(v) is None else str(r[v]).strip()) for v in p if v in r}} for r in rijen]
    if naam == "getal":
        return [{**r, **{v: _getal(r.get(v)) for v in p if v in r}} for r in rijen]
    if naam == "waarde_map":
        naar = p.get("naar", p["veld"])
        m = {str(k): w for k, w in p["map"].items()}
        uit = []
        for r in rijen:
            w = r.get(p["veld"])
            nieuw = m.get(str(w), p.get("standaard", w))
            if str(w) in m and nieuw != w:
                rapport[f"{p['veld']}: {w} → {nieuw}"] += 1
            uit.append({**r, naar: nieuw})
        return uit
    if naam == "koppel":
        from omnitwin.bronadapters import haal
        tab = haal(p["bron"], ctx)
        norm = (lambda w: " ".join(str(w).split()).casefold()) if p.get("normaliseer") else str
        opzoek = {}
        for rec in tab.get(p.get("tabel"), next(iter(tab.values()), [])) if tab else []:
            opzoek.setdefault(norm(rec.get(p["op"])), rec)
        uit = []
        for r in rijen:
            gevonden = opzoek.get(norm(r.get(p["sleutel"])))
            if gevonden is None and p.get("verplicht"):
                rapport[p.get("reden", "niet-gekoppeld")] += 1
                continue
            uit.append({**r, **{nieuw: (gevonden or {}).get(oud, "") for oud, nieuw in p["velden"].items()}})
        return uit
    if naam == "afwijzen":
        uit = []
        for r in rijen:
            if voldoet(r, p):
                rapport[p.get("reden", "afgewezen")] += 1
            else:
                uit.append(r)
        return uit
    if naam == "filter":
        uit = [r for r in rijen if voldoet(r, p)]
        rapport["gefilterd"] += len(rijen) - len(uit)
        return uit
    if naam == "jaar_uit_datum":
        uit = []
        for r in rijen:
            w = str(r.get(p["veld"]) or "")[:10]
            try:
                d = dt.date.fromisoformat(w)
            except ValueError:
                rapport["jaar-ongeldig"] += 1
                continue
            if d.month == 1 and d.day == 1:
                uit.append({**r, p.get("jaar", "jaar"): d.year, p.get("peildatum", "peildatum"): ""})
            else:
                uit.append({**r, p.get("jaar", "jaar"): "", p.get("peildatum", "peildatum"): d.isoformat()})
        return uit
    if naam == "jaar_naar_datum":
        return [{**r, p["naar"]: f"{int(r[p['veld']]):04d}-01-01"} for r in rijen]
    if naam == "iso_datumtijd":
        def iso(w):
            if _leeg(w):
                return ""
            w = str(w).strip().replace(" ", "T")
            return w + ":00" if len(w) == 16 else w
        return [{**r, **{v: iso(r.get(v)) for v in p}} for r in rijen]
    if naam == "prefix":
        uit = []
        for r in rijen:
            w = str(r.get(p["veld"], ""))
            if (not p.get("als") or voldoet(r, p["als"])) and not w.startswith(p["prefix"]):
                r = {**r, p["veld"]: p["prefix"] + w}
            uit.append(r)
        return uit
    if naam == "sjabloon":
        return [{**r, p["naar"]: _sjabloon(p["sjabloon"], r)} for r in rijen]
    if naam == "deel":
        return [{**r, p["naar"]: str(r.get(p["veld"]) or "")[p["start"]:p.get("eind")]} for r in rijen]
    if naam == "nummer":
        return [{**r, p["naar"]: i} for i, r in enumerate(rijen, start=p.get("start", 1))]
    if naam == "snake_case":
        return [{(k if k == "geometry" else snake(k)): w for k, w in r.items()} for r in rijen]
    if naam == "multipolygon":
        from shapely import make_valid
        from shapely.geometry import MultiPolygon, Polygon
        uit = []
        for r in rijen:
            g = r.get("geometry")
            if g is None or g.is_empty:
                rapport["geometrie-leeg"] += 1
                continue
            if not g.is_valid:
                g = make_valid(g)
                rapport["gerepareerd"] += 1
            delen = [g] if isinstance(g, Polygon) else [d for d in getattr(g, "geoms", []) if isinstance(d, (Polygon, MultiPolygon))]
            polys = [q for d in delen for q in (d.geoms if isinstance(d, MultiPolygon) else [d]) if not q.is_empty]
            if not polys:
                rapport["geometrie-geen-vlak"] += 1
                continue
            uit.append({**r, "geometry": MultiPolygon(polys)})
        return uit
    if naam == "geometrietype":
        uit = [r for r in rijen if r.get("geometry") is not None and r["geometry"].geom_type in set(p)]
        rapport["ander geometrietype"] += len(rijen) - len(uit)
        return uit
    if naam == "binnen":
        gebied = _vereniging(p["bron"], ctx, p.get("bewerkingen"))
        if gebied is None:
            raise BewerkingFout("binnen: de bron heeft geen geometrie")
        uit = [r for r in rijen if r.get("geometry") is not None and gebied.contains(r["geometry"].representative_point())]
        rapport["buiten het gebied"] += len(rijen) - len(uit)
        return uit
    if naam == "splits_op":
        gebied = _vereniging(p["bron"], ctx, p.get("bewerkingen"))
        uit = []
        for r in rijen:
            g = r.get("geometry")
            for deel, sjabloon in ((g.intersection(gebied), p["binnen"]), (g.difference(gebied), p["buiten"])):
                if not deel.is_empty and deel.area > 0:
                    uit.append({**r, p["veld"]: _sjabloon(sjabloon, r), "geometry": deel})
        return uit
    raise BewerkingFout(f"onbekende bewerking {naam!r}; bekend: {', '.join(BEWERKINGEN)}")


def naam_van(stap):
    sleutels = [k for k in stap if k not in ("id", "tabel", "omschrijving")]
    if len(sleutels) != 1 or sleutels[0] not in BEWERKINGEN:
        raise BewerkingFout(f"een bewerking heeft precies één sleutel uit {BEWERKINGEN}: {sorted(stap)}")
    return sleutels[0]


def voer_uit(tabellen, stappen, ctx=None, sla_over=()):
    """Bewerkingen op Tabellen; geeft (tabellen, rapport). sla_over: id's van stappen die niet draaien."""
    ctx = ctx or {}
    rapport = Counter()
    for stap in stappen:
        naam = naam_van(stap)
        if stap.get("id") in sla_over:
            continue
        for t in list(tabellen):
            if stap.get("tabel") and stap["tabel"] != t:
                continue
            tabellen[t] = _stap(naam, stap[naam], tabellen[t], rapport, ctx)
    return tabellen, dict(rapport)
