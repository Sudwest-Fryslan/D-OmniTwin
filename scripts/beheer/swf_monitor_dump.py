#!/usr/bin/env python3
"""
Export uit de database-dump van de huidige SWF-gebiedsmonitor (#316, #222)
==========================================================================
Leest een `pg_dump` van de database van de huidige gebiedsmonitor (custom format `-Fc`, of platte SQL)
en maakt daaruit de bestanden voor de swf-* use cases. Geen database nodig: het script leest de
COPY-blokken van de tabellen `indicator`, `gebiedstype`, `indicator_gebiedstype`, `indicator_waarde`,
`monitor` en `user_properties`. De echte data komt alleen in de exportmap (`SWF_DB_DUMP`), nooit in git.

    # 1. export (pg_restore uit PostgreSQL 16 of nieuwer, alleen om het custom format te lezen)
    python scripts/beheer/swf_monitor_dump.py exporteer --dump public.monitor.dmp --uit /pad/swf-db-dump \
        --dump-datum 2026-10-09 [--gebruikers-mapping gebruikers-mapping.csv]
    # 2. use cases: SWF_DB_DUMP=/pad/swf-db-dump python -m omnitwin.usecases controleer swf-definities
    # 3. gebruikersvoorkeuren (persoonlijke gegevens, niet via de laad-API), in de backend-container:
    python scripts/beheer/swf_monitor_dump.py laad-voorkeuren /pad/swf-db-dump/gebruikersvoorkeuren.json

| Bestand in `--uit` | Uit de dump | Gebruikt door |
|---|---|---|
| `definities.json` | indicator, gebiedstype, indicator_gebiedstype; `score_type` uit `omkeren` in de actieve monitorconfiguraties | swf-definities (variant `monitor-database`) |
| `waarden.json` | indicator_waarde | swf-basismonitor-waarden, swf-klimaatmonitor (variant `monitor-database`) |
| `kompasprofiel_monitor.csv` | monitor (actieve configuratie per monitor): één regel per indicator in de boom | swf-kompasprofiel (variant `monitor-database`) |
| `indicator_labels_monitor.json` | monitor: `labeling` (drempels A–E) per indicator, in het formaat van `db/stuurdata/indicator_labels_*.json` | `load_sample.py --stap drempels --drempels <bestand>` (keuze beheerder) |
| `monitorconfiguraties.json` | monitor: alle versies, zonder `vastgelegd_door` | archief (geen doel in D-OmniTwin) |
| `gebruikers-mapping.csv` | user_properties: de oude gebruikersnamen, kolom `eigenaar` leeg of uit `--gebruikers-mapping` | invullen door de beheerder (expliciete koppeling) |
| `gebruikersvoorkeuren.json` | user_properties, alleen gekoppelde gebruikers | `laad-voorkeuren` → `gebruiker_voorkeuren` (V035) |
| `export.json` | – | aantallen en controlesommen, zonder gebruikersnamen |

Gebruikersvoorkeuren: de oude gebruikersnaam wordt nooit geraden. Alleen wie in de mapping een
`eigenaar` heeft (de Keycloak-`sub`, of `lokaal:<users.id>`), gaat mee; een e-mailadres wordt
geweigerd (D-OmniTwin bewaart geen naam of e-mail). `laad-voorkeuren` vult aan en overschrijft nooit
(een gebruiker die D-OmniTwin al gebruikt, houdt zijn eigen voorkeuren).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

TABELLEN = ("gebiedstype", "indicator", "indicator_gebiedstype", "indicator_waarde", "monitor", "user_properties")
COPY = re.compile(r"^COPY (?:public\.)?(\w+) \((.*)\) FROM stdin;$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
LOKAAL = re.compile(r"^lokaal:\d+$")
# Drempel die in de monitor 'open' betekent (bijv. tot 9999 of van -9999)
OPEN_GRENS = 999
KOMPAS_KOLOMMEN = ("monitor", "monitor_id", "gebiedstype_id", "weergave_type", "volgorde", "niveau1", "niveau2",
                   "niveau3", "niveau4", "indicator_uuid", "indicator_naam", "omkeren", "labels")
MAPPING_KOLOMMEN = ("gebruikersnaam", "eigenaar")


class DumpFout(ValueError):
    pass


# ------------------------------------------------------------------ dump lezen

def _ontsnap(veld: str):
    r"""Tekstformaat van COPY: \N = NULL, backslash-escapes voor tab, newline enz."""
    if veld == r"\N":
        return None
    if "\\" not in veld:
        return veld
    vervang = {"t": "\t", "n": "\n", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "\\": "\\"}
    return re.sub(r"\\(.)", lambda m: vervang.get(m.group(1), m.group(1)), veld)


def lees_copy(regels) -> dict[str, list[dict]]:
    """COPY-blokken uit platte SQL (pg_dump/pg_restore -f) → {tabel: [record]} (alle waarden tekst of None)."""
    uit: dict[str, list[dict]] = {}
    kolommen, tabel = None, None
    for regel in regels:
        regel = regel.rstrip("\r\n")
        if tabel is None:
            m = COPY.match(regel)
            if m:
                tabel = m.group(1)
                kolommen = [k.strip().strip('"') for k in m.group(2).split(",")]
                uit[tabel] = []
            continue
        if regel == r"\.":
            tabel = None
            continue
        velden = regel.split("\t")
        if len(velden) != len(kolommen):
            raise DumpFout(f"{tabel}: {len(velden)} velden, verwacht {len(kolommen)}")
        uit[tabel].append(dict(zip(kolommen, (_ontsnap(v) for v in velden))))
    return uit


def lees_dump(pad: Path, pg_restore: str | None = None) -> dict[str, list[dict]]:
    """Platte SQL direct; een custom-format-dump via `pg_restore -f -` (alleen naar stdout, geen tijdelijk bestand)."""
    pad = Path(pad)
    with open(pad, "rb") as f:
        kop = f.read(5)
    if kop != b"PGDMP":
        with open(pad, encoding="utf-8") as f:
            tabellen = lees_copy(f)
    else:
        programma = pg_restore or os.environ.get("PG_RESTORE") or shutil.which("pg_restore")
        if not programma:
            raise DumpFout("pg_restore niet gevonden (PATH, PG_RESTORE of --pg-restore)")
        proc = subprocess.Popen([programma, "--data-only", "-f", "-", str(pad)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding="utf-8")
        tabellen = lees_copy(proc.stdout)
        fout = proc.stderr.read()
        if proc.wait() != 0:
            raise DumpFout(f"pg_restore faalde: {fout.strip()[:500]}")
    ontbreekt = [t for t in TABELLEN if t not in tabellen]
    if ontbreekt:
        raise DumpFout(f"tabel(len) ontbreken in de dump: {', '.join(ontbreekt)}")
    return tabellen


# ------------------------------------------------------------------ omzetten (getest)

def _leeg(w) -> bool:
    return w is None or str(w).strip() == ""


def _datumtijd(w) -> str:
    """'2024-11-20 00:00:00[.123]' → '2024-11-20 00:00' (zoals de export van de monitor-API)."""
    return "" if _leeg(w) else str(w).strip()[:16]


def _bool(w) -> bool:
    return str(w).strip().lower() in ("t", "true", "1", "ja")


def actieve_monitors(monitor: list[dict]) -> list[dict]:
    """Per monitor-id de geldige configuratie: zonder eindgeldigheid, anders de laatste versie."""
    per_id: dict[str, list[dict]] = defaultdict(list)
    for m in monitor:
        per_id[m["id"]].append(m)
    uit = []
    for versies in per_id.values():
        open_ = [m for m in versies if _leeg(m.get("eindgeldigheid"))]
        kies = open_ or versies
        uit.append(max(kies, key=lambda m: (int(m.get("volgnummer") or 0), m.get("begingeldigheid") or "")))
    return sorted(uit, key=lambda m: m["naam"])


def _config(m: dict) -> dict:
    c = m.get("configuratie")
    return json.loads(c) if isinstance(c, str) else (c or {})


def indicatorknopen(m: dict):
    """(pad van categorieën, knoop) voor elke indicator in de boom van een monitor, in volgorde."""
    def loop(knoop, pad):
        if knoop.get("type") == "indicator":
            yield pad, knoop
            return
        sub = pad if knoop.get("type") == "root" else pad + [str(knoop.get("text") or knoop.get("naam") or "").strip()]
        for kind in knoop.get("children") or []:
            yield from loop(kind, sub)
    yield from loop(_config(m), [])


def kompasregels(monitors: list[dict]) -> list[dict]:
    """Eén regel per indicator per actieve monitor, met de categorieën als niveau1..niveau4."""
    regels = []
    for m in monitors:
        c = _config(m)
        for volgorde, (pad, k) in enumerate(indicatorknopen(m), start=1):
            if len(pad) > 4:
                raise DumpFout(f"monitor {m['naam']}: meer dan 4 niveaus boven indicator {k.get('indicator_id')}")
            niveaus = (pad + ["", "", "", ""])[:4]
            regels.append({
                "monitor": m["naam"], "monitor_id": m["id"], "gebiedstype_id": c.get("gebiedstype_id") or m.get("gebiedstype_id") or "",
                "weergave_type": c.get("weergave_type") or "", "volgorde": volgorde,
                "niveau1": niveaus[0], "niveau2": niveaus[1], "niveau3": niveaus[2], "niveau4": niveaus[3],
                "indicator_uuid": str(k.get("indicator_id") or "").lower(), "indicator_naam": str(k.get("text") or "").strip(),
                "omkeren": "" if k.get("omkeren") is None else str(bool(k["omkeren"])).lower(),
                "labels": "ja" if k.get("labeling") else "",
            })
    return regels


def score_types(monitors: list[dict]) -> tuple[dict[str, str], list[str]]:
    """`omkeren` per indicator → score_type ('-/+' = lager is beter, '+/+' = hoger is beter).
    Tegenstrijdig over de knopen: geen score_type, wel gemeld."""
    gezien: dict[str, set] = defaultdict(set)
    for m in monitors:
        for _, k in indicatorknopen(m):
            if k.get("omkeren") is not None:
                gezien[str(k["indicator_id"]).lower()].add(bool(k["omkeren"]))
    uit, tegenstrijdig = {}, []
    for u, s in gezien.items():
        if len(s) > 1:
            tegenstrijdig.append(u)
        else:
            uit[u] = "-/+" if s.pop() else "+/+"
    return uit, sorted(tegenstrijdig)


def definities(tabellen: dict, monitors: list[dict] | None = None) -> dict:
    """Definities in de vorm van de export van de monitor-API (api_backup_dump.json): indicatoren, gebiedstypen, relaties."""
    scores, _ = score_types(monitors or [])
    indicatoren = []
    for i in tabellen["indicator"]:
        r = {"id": i["id"].lower(), "naam": i["naam"], "omschrijving": i.get("omschrijving") or "",
             "status": (i.get("status") or "").strip(), "begingeldigheid": _datumtijd(i.get("begingeldigheid")),
             "eindgeldigheid": _datumtijd(i.get("eindgeldigheid"))}
        if r["id"] in scores:
            r["score_type"] = scores[r["id"]]
        indicatoren.append(r)
    gebiedstypen = [{"id": g["id"].lower(), "naam": g["naam"], "wfs": (g.get("wfs") or "").strip(),
                     "typenames": (g.get("typenames") or "").strip(), "sleutel": (g.get("sleutel") or "").strip(),
                     "label": (g.get("label") or "").strip(), "actief": _bool(g.get("actief"))}
                    for g in tabellen["gebiedstype"]]
    relaties = [{"indicator_id": r["indicator_id"].lower(), "gebiedstype_id": r["gebiedstype_id"].lower()}
                for r in tabellen["indicator_gebiedstype"]]
    return {"indicatoren": indicatoren, "gebiedstypen": gebiedstypen, "relaties": relaties}


def _getal(w):
    if _leeg(w):
        return None
    f = float(w)
    return int(f) if f.is_integer() and "." not in str(w) else f


def waarden(tabellen: dict) -> list[dict]:
    """Waarden in de vorm van api_data_dump.json: indicator_id, gebiedstype_id, gebieds_id, waarde, jaar."""
    return [{"indicator_id": w["indicator_id"].lower(), "gebiedstype_id": w["gebiedstype_id"].lower(),
             "gebieds_id": w["gebieds_id"], "waarde": _getal(w.get("waarde")), "jaar": int(w["jaar"])}
            for w in tabellen["indicator_waarde"]]


def _grens(w):
    if w is None:
        return None
    w = float(w)
    return None if abs(w) >= OPEN_GRENS else w


def labels(monitors: list[dict], indicatornamen: dict[str, str], bron: str) -> dict:
    """`labeling` uit de monitorboom → formaat van db/stuurdata/indicator_labels_*.json.
    Per label (ondergrens, bovengrens) oplopend; een grens van |w| ≥ 999 is open (null)."""
    per: dict[str, dict] = {}
    for m in monitors:
        for _, k in indicatorknopen(m):
            lab = k.get("labeling")
            if not isinstance(lab, dict) or not lab:
                continue
            u = str(k["indicator_id"]).lower()
            rijen = []
            for letter in sorted(lab):
                v = lab[letter] or {}
                # Oplopend (de monitor heeft soms van > tot), daarna een open grens (±9999) als null
                grenzen = sorted(float(g) for g in (v.get("van"), v.get("tot")) if g is not None)
                a, b = (grenzen + [None, None])[:2] if len(grenzen) < 2 else grenzen
                rijen.append([letter, _grens(a), _grens(b)])
            item = {"indicator_uuid": u, "indicator_naam": indicatornamen.get(u, k.get("text") or ""),
                    "labels": rijen, "namen": {letter: (lab[letter] or {}).get("label") for letter in sorted(lab)}}
            if u in per and per[u]["labels"] != rijen:
                per[u]["opmerking"] = "verschillende drempels in de monitors; eerste aangehouden"
                continue
            per.setdefault(u, item)
    return {"bron": bron,
            "toelichting": "Drempels voor de labels A-E uit de configuratie van de huidige gebiedsmonitor (labeling). "
                           "ondergrens inclusief, bovengrens exclusief, null = open. Laden: init_data/scripts/load_sample.py "
                           "--stap drempels --drempels <dit bestand> (overschrijft de stuurdata voor deze indicatoren).",
            "indicatoren": sorted(per.values(), key=lambda i: i["indicator_naam"])}


def monitorarchief(monitor: list[dict]) -> list[dict]:
    """Alle versies van de monitorconfiguraties, zonder wie ze vastlegde."""
    return [{"id": m["id"], "naam": m["naam"], "gebiedstype_id": m.get("gebiedstype_id"),
             "volgnummer": int(m.get("volgnummer") or 0), "begingeldigheid": m.get("begingeldigheid"),
             "eindgeldigheid": m.get("eindgeldigheid"), "configuratie": _config(m)}
            for m in sorted(monitor, key=lambda m: (m["naam"], int(m.get("volgnummer") or 0)))]


# --- kaartpositie: RD (EPSG:28992) of Web Mercator → lengte/breedte en MapLibre-zoom

def rd_naar_wgs84(x: float, y: float) -> tuple[float, float]:
    """Benadering (Schreutelkamp en Strang van Hees), nauwkeurig tot ±1 m binnen Nederland: (lon, lat)."""
    dx, dy = (x - 155000) * 1e-5, (y - 463000) * 1e-5
    k = ((0, 1, 3235.65389), (2, 0, -32.58297), (0, 2, -0.24750), (2, 1, -0.84978), (0, 3, -0.06550),
         (2, 2, -0.01709), (1, 0, -0.00738), (4, 0, 0.00530), (2, 3, -0.00039), (4, 1, 0.00033), (1, 1, -0.00012))
    l_ = ((1, 0, 5260.52916), (1, 1, 105.94684), (1, 2, 2.45656), (3, 0, -0.81885), (1, 3, 0.05594),
          (3, 1, -0.05607), (0, 1, 0.01199), (3, 2, -0.00256), (1, 4, 0.00128), (0, 2, 0.00022), (2, 0, -0.00022),
          (5, 0, 0.00026))
    lat = 52.15517440 + sum(c * dx ** p * dy ** q for p, q, c in k) / 3600
    lon = 5.38720621 + sum(c * dx ** p * dy ** q for p, q, c in l_) / 3600
    return lon, lat


def mercator_naar_wgs84(x: float, y: float) -> tuple[float, float]:
    r = 6378137.0
    return math.degrees(x / r), math.degrees(2 * math.atan(math.exp(y / r)) - math.pi / 2)


def kaartpositie(waarde: str) -> dict | None:
    """{center: [x, y], resolution} (OpenLayers, meter per pixel) → {longitude, latitude, zoom} of None."""
    try:
        d = json.loads(waarde)
        x, y = (float(v) for v in d["center"])
        res = float(d["resolution"])
    except (TypeError, ValueError, KeyError):
        return None
    if 0 < x < 300000 and 300000 < y < 625000:
        lon, lat = rd_naar_wgs84(x, y)
    elif abs(y) > 1_000_000:
        lon, lat = mercator_naar_wgs84(x, y)
    else:
        return None
    if res <= 0:
        return None
    # MapLibre (tegels van 512 px): meter per pixel = 40075016.686 · cos(lat) / (512 · 2^zoom)
    zoom = math.log2(40075016.686 * math.cos(math.radians(lat)) / (512 * res))
    return {"longitude": round(lon, 6), "latitude": round(lat, 6), "zoom": round(min(max(zoom, 0.0), 24.0), 2)}


def lees_mapping(pad: Path | None) -> dict[str, str]:
    """gebruikersnaam → eigenaar (sub of lokaal:<id>). Leeg = niet koppelen. Een e-mailadres is een fout."""
    if not pad:
        return {}
    uit = {}
    with open(pad, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            naam, eigenaar = (r.get("gebruikersnaam") or "").strip(), (r.get("eigenaar") or "").strip()
            if not naam or not eigenaar:
                continue
            if "@" in eigenaar:
                raise DumpFout(f"mapping regel {i}: geef de Keycloak-sub (gebruikers-ID) of lokaal:<id>, geen e-mailadres")
            if not (UUID.match(eigenaar.lower()) or LOKAAL.match(eigenaar)) or len(eigenaar) > 255:
                raise DumpFout(f"mapping regel {i}: eigenaar is geen Keycloak-sub (UUID) of lokaal:<id>")
            uit[naam] = eigenaar
    return uit


def voorkeuren(user_properties: list[dict], mapping: dict[str, str], monitornamen: dict[str, str]) -> tuple[list[dict], dict]:
    """user_properties → gebruikersvoorkeuren per gekoppelde gebruiker, plus tellingen (zonder namen).

    | key | D-OmniTwin |
    |---|---|
    | last_map_coordinate | gebruiker_voorkeuren.kaartpositie |
    | selected_node_id, active_item, panel_visible, visible_base_layer | geen plek: `niet_overgenomen` |
    """
    per: dict[str, dict] = defaultdict(dict)
    for p in user_properties:
        per[p["username"]][p["key"]] = p["value"]
    uit, telling = [], Counter()
    sleutels = Counter(p["key"] for p in user_properties)
    for naam in sorted(per):
        props = per[naam]
        eigenaar = mapping.get(naam)
        if not eigenaar:
            telling["niet_gekoppeld"] += 1
            continue
        item = {"eigenaar": eigenaar}
        if "last_map_coordinate" in props:
            pos = kaartpositie(props["last_map_coordinate"])
            if pos:
                item["kaartpositie"] = pos
            else:
                telling["kaartpositie_onleesbaar"] += 1
        rest = {}
        if "selected_node_id" in props:
            rest["monitor"] = monitornamen.get(props["selected_node_id"], props["selected_node_id"])
        for oud, nieuw in (("active_item", "actief_paneel"), ("panel_visible", "paneel_zichtbaar"),
                           ("visible_base_layer", "basislaag")):
            if oud in props:
                rest[nieuw] = _bool(props[oud]) if oud == "panel_visible" else props[oud]
        onbekend = sorted(set(props) - {"last_map_coordinate", "selected_node_id", "active_item", "panel_visible",
                                         "visible_base_layer"})
        for k in onbekend:
            rest[k] = props[k]
        if rest:
            item["niet_overgenomen"] = rest
        telling["gekoppeld"] += 1
        uit.append(item)
    return uit, {"gebruikers": len(per), "sleutels": dict(sleutels), **telling}


def mapping_sjabloon(user_properties: list[dict], mapping: dict[str, str]) -> list[dict]:
    return [{"gebruikersnaam": n, "eigenaar": mapping.get(n, "")} for n in sorted({p["username"] for p in user_properties})]


# ------------------------------------------------------------------ export

def sha256(pad: Path) -> str:
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def _schrijf_json(pad: Path, data) -> None:
    pad.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _schrijf_csv(pad: Path, rijen: list[dict], kolommen) -> None:
    with open(pad, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(kolommen), lineterminator="\r\n")
        w.writeheader()
        w.writerows(rijen)


def dekking(w: list[dict]) -> dict:
    """Aantallen per gebiedstype (geen waarden): waarden, indicatoren, gebieden, jaren."""
    per: dict[str, dict] = defaultdict(lambda: {"waarden": 0, "indicatoren": set(), "gebieden": set(), "jaren": set()})
    for r in w:
        p = per[r["gebiedstype_id"]]
        p["waarden"] += 1
        p["indicatoren"].add(r["indicator_id"])
        p["gebieden"].add(r["gebieds_id"])
        p["jaren"].add(r["jaar"])
    return {gt: {"waarden": p["waarden"], "indicatoren": len(p["indicatoren"]), "gebieden": len(p["gebieden"]),
                 "jaren": [min(p["jaren"]), max(p["jaren"])]} for gt, p in sorted(per.items())}


def exporteer(tabellen: dict, uit: Path, mapping: dict[str, str], dump_datum: str | None = None) -> dict:
    uit.mkdir(parents=True, exist_ok=True)
    monitors = actieve_monitors(tabellen["monitor"])
    defs = definities(tabellen, monitors)
    _, tegenstrijdig = score_types(monitors)
    _schrijf_json(uit / "definities.json", defs)
    w = waarden(tabellen)
    (uit / "waarden.json").write_text(json.dumps(w, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    regels = kompasregels(monitors)
    _schrijf_csv(uit / "kompasprofiel_monitor.csv", regels, KOMPAS_KOLOMMEN)
    namen = {i["id"]: i["naam"] for i in defs["indicatoren"]}
    lab = labels(monitors, namen, f"Configuratie van de huidige gebiedsmonitor SWF (database-dump {dump_datum or 'onbekend'})")
    _schrijf_json(uit / "indicator_labels_monitor.json", lab)
    _schrijf_json(uit / "monitorconfiguraties.json", monitorarchief(tabellen["monitor"]))
    _schrijf_csv(uit / "gebruikers-mapping.csv", mapping_sjabloon(tabellen["user_properties"], mapping), MAPPING_KOLOMMEN)
    vk, vk_telling = voorkeuren(tabellen["user_properties"], mapping, {m["id"]: m["naam"] for m in monitors})
    _schrijf_json(uit / "gebruikersvoorkeuren.json", vk)
    status = Counter(i["status"] for i in defs["indicatoren"])
    samenvatting = {
        "gemaakt_op": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "bron": "database-dump van de huidige gebiedsmonitor SWF", "dump_datum": dump_datum,
        "gemaakt_met": "scripts/beheer/swf_monitor_dump.py exporteer",
        "definities": {"indicatoren": len(defs["indicatoren"]), "status": dict(sorted(status.items())),
                       "met_eindgeldigheid": sum(1 for i in defs["indicatoren"] if i["eindgeldigheid"]),
                       "gebiedstypen": len(defs["gebiedstypen"]), "relaties": len(defs["relaties"]),
                       "score_type_uit_monitor": sum(1 for i in defs["indicatoren"] if "score_type" in i),
                       "omkeren_tegenstrijdig": len(tegenstrijdig)},
        "waarden": {"totaal": len(w), "indicatoren": len({r["indicator_id"] for r in w}),
                    "combinaties": len({(r["indicator_id"], r["gebiedstype_id"]) for r in w}),
                    "per_gebiedstype": dekking(w)},
        "monitors": {"versies": len(tabellen["monitor"]),
                     "actief": [{"naam": m["naam"], "volgnummer": int(m.get("volgnummer") or 0),
                                 "indicatoren": sum(1 for r in regels if r["monitor_id"] == m["id"]),
                                 "met_labels": sum(1 for r in regels if r["monitor_id"] == m["id"] and r["labels"])}
                                for m in monitors]},
        "labels": {"indicatoren": len(lab["indicatoren"])},
        "gebruikersvoorkeuren": vk_telling,
    }
    samenvatting["bestanden"] = {p.name: sha256(p) for p in sorted(uit.iterdir()) if p.is_file() and p.name != "export.json"}
    _schrijf_json(uit / "export.json", samenvatting)
    return samenvatting


# ------------------------------------------------------------------ gebruikersvoorkeuren laden

GRENZEN = {"longitude": (-180.0, 180.0), "latitude": (-85.0, 85.0), "zoom": (0.0, 24.0)}


def geldige_positie(pos) -> dict | None:
    if not isinstance(pos, dict):
        return None
    uit = {}
    for veld, (laag, hoog) in GRENZEN.items():
        w = pos.get(veld)
        if not isinstance(w, (int, float)) or not laag <= float(w) <= hoog:
            return None
        uit[veld] = float(w)
    return uit


def laad_voorkeuren(cur, items: list[dict]) -> dict:
    """Aanvullen in gebruiker_voorkeuren: een eigenaar die al een rij heeft, blijft ongemoeid."""
    telling = Counter()
    for item in items:
        eigenaar = str(item.get("eigenaar") or "")
        if not (UUID.match(eigenaar.lower()) or LOKAAL.match(eigenaar)):
            telling["eigenaar_ongeldig"] += 1
            continue
        pos = geldige_positie(item.get("kaartpositie"))
        cur.execute("INSERT INTO public.gebruiker_voorkeuren (eigenaar, kaartpositie) VALUES (%s, %s::jsonb) "
                    "ON CONFLICT (eigenaar) DO NOTHING", (eigenaar, json.dumps(pos) if pos else None))
        telling["toegevoegd" if cur.rowcount == 1 else "al_aanwezig"] += 1
        if item.get("niet_overgenomen"):
            telling["met_niet_overgenomen_instellingen"] += 1
    return dict(telling)


def verbind(dsn: str):
    import psycopg2
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(host=os.environ.get("DATABASE_HOST", "127.0.0.1"),
                            port=int(os.environ.get("DATABASE_PORT", 5432)),
                            dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
                            user=os.environ.get("DATABASE_USER", "omnitwin_user"),
                            password=os.environ.get("DATABASE_PASSWORD", ""), connect_timeout=10)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="opdracht", required=True)
    e = sub.add_parser("exporteer", help="dump → bestanden voor de use cases (SWF_DB_DUMP)")
    e.add_argument("--dump", required=True, help="pg_dump van de monitor: custom format (-Fc) of platte SQL")
    e.add_argument("--uit", required=True, help="exportmap (SWF_DB_DUMP); nooit in git")
    e.add_argument("--gebruikers-mapping", help="CSV gebruikersnaam,eigenaar (Keycloak-sub of lokaal:<id>)")
    e.add_argument("--dump-datum", help="datum van de dump (JJJJ-MM-DD)")
    e.add_argument("--pg-restore", help="pad naar pg_restore (standaard PATH of PG_RESTORE)")
    v = sub.add_parser("laad-voorkeuren", help="gebruikersvoorkeuren.json → gebruiker_voorkeuren (aanvullen)")
    v.add_argument("bestand")
    v.add_argument("--dsn", default="", help="libpq-verbinding; leeg = DATABASE_* uit de omgeving")
    v.add_argument("--droog", action="store_true", help="alleen tellen, niets vastleggen")
    args = a.parse_args(argv)
    try:
        if args.opdracht == "exporteer":
            tabellen = lees_dump(Path(args.dump), args.pg_restore)
            mapping = lees_mapping(Path(args.gebruikers_mapping) if args.gebruikers_mapping else None)
            s = exporteer(tabellen, Path(args.uit), mapping, args.dump_datum)
            d, w, g = s["definities"], s["waarden"], s["gebruikersvoorkeuren"]
            print(f"definities: {d['indicatoren']} indicatoren {d['status']}, {d['gebiedstypen']} gebiedstypen, "
                  f"{d['relaties']} relaties")
            print(f"waarden: {w['totaal']} ({w['indicatoren']} indicatoren, {w['combinaties']} combinaties)")
            print(f"monitors: {s['monitors']['versies']} versies, actief: "
                  + ", ".join(f"{m['naam']} ({m['indicatoren']})" for m in s["monitors"]["actief"]))
            print(f"gebruikersvoorkeuren: {g.get('gekoppeld', 0)} van {g['gebruikers']} gebruikers gekoppeld"
                  + (f"; vul {Path(args.uit) / 'gebruikers-mapping.csv'} aan en exporteer opnieuw met --gebruikers-mapping"
                     if g.get("niet_gekoppeld") else ""))
            return 0
        items = json.loads(Path(args.bestand).read_text(encoding="utf-8"))
        conn = verbind(args.dsn)
        try:
            with conn.cursor() as cur:
                telling = laad_voorkeuren(cur, items)
            if args.droog:
                conn.rollback()
            else:
                conn.commit()
        finally:
            conn.close()
        print(f"gebruikersvoorkeuren{' (droog)' if args.droog else ''}: {telling}")
        return 0
    except DumpFout as e:
        print(f"FOUT: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
