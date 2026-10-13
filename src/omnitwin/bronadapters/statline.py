"""
Adapter `cbs-statline`: een tabel uit StatLine (CBS en de 'derden' op dataderden.cbs.nl: RIVM, Politie, ...)
=========================================================================================================
Generiek voor elke StatLine-tabel met een regio-dimensie (bijv. `WijkenEnBuurten`). Via de
ODataFeed-ingang, die pagineert (`odata.nextLink`); de ODataApi-ingang weigert meer dan 10.000 regels.

Parameters (`bron` in `datasets/<id>.json`):

| Parameter | Wat |
|---|---|
| `url` | `https://<host>/ODataFeed/odata/<tabel>` (host op de allowlist) |
| `kolommen` | onderwerpen (Topic-keys, bijv. `Eenzaam_25`) die als waarde worden uitgepakt |
| `regio` | naam van de regio-dimensie (standaard `WijkenEnBuurten`) |
| `gemeenten` | gemeentecodes (4 cijfers): alleen regio's `<prefix><code>...` |
| `gebieden` | of: precies deze regiocodes |
| `regio_prefix` | soorten regio bij `gemeenten` (standaard `["BU"]`; ook `WK`, `GM`) |
| `filter` | {dimensie: key of [keys]}, bijv. `{"Leeftijd": "20300", "Marges": "MW00000"}`; keys zonder opvulspaties |
| `jaren` | alleen deze jaren (perioden `<jaar>JJ00`); leeg = alle jaren |

Uitvoer: één record per regio x periode x dimensiewaarden x kolom met een waarde:
`{gebied_code, jaar, periode, kolom, waarde, <dimensie>: key}`; keys en codes zonder opvulspaties.
Lege waarden (onderdrukt of niet berekend) vallen weg. Welke kolom of dimensiewaarde bij welke
indicator hoort, staat in de dataset (bewerking `waarde_map`), niet hier.
Cache: `$DATA_CACHE/bronnen/statline/<hash>.json`.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

PERIODE_JAAR = re.compile(r"^(\d{4})JJ00$")
FEED = re.compile(r"^/ODataFeed/odata/[0-9A-Za-z]+/?$", re.IGNORECASE)


def _q(w):
    return "'" + str(w).replace("'", "''") + "'"


def _of(veld, keys):
    return "(" + " or ".join(f"{veld} eq {_q(k)}" for k in keys) + ")"


def odata_filter(bron, dim_keys):
    """$filter voor de regio's, de dimensiefilters en de jaren. dim_keys: {dimensie: {kale key: echte key}}."""
    regio = bron.get("regio", "WijkenEnBuurten")
    delen = []
    if bron.get("gebieden"):
        delen.append(_of(regio, [str(g).strip() for g in bron["gebieden"]]))
    elif bron.get("gemeenten"):
        delen.append(
            "("
            + " or ".join(
                f"startswith({regio},{_q(p + str(g).zfill(4))})"
                for p in bron.get("regio_prefix", ["BU"])
                for g in bron["gemeenten"]
            )
            + ")"
        )
    for dim, waarde in (bron.get("filter") or {}).items():
        keys = waarde if isinstance(waarde, list) else [waarde]
        echt = dim_keys.get(dim, {})
        delen.append(_of(dim, [echt.get(str(k).strip(), str(k)) for k in keys]))
    if bron.get("jaren"):
        delen.append(_of("Perioden", [f"{int(j)}JJ00" for j in bron["jaren"]]))
    return " and ".join(delen)


def records(rijen, bron):
    """OData-rijen -> lange records (zie module-docstring). Perioden die geen jaar zijn vallen weg."""
    regio = bron.get("regio", "WijkenEnBuurten")
    dims = list((bron.get("filter") or {}).keys())
    uit = []
    for r in rijen:
        m = PERIODE_JAAR.match(str(r.get("Perioden", "")).strip())
        if not m:
            continue
        basis = {
            "gebied_code": str(r.get(regio, "")).strip(),
            "jaar": int(m.group(1)),
            "periode": str(r["Perioden"]).strip(),
        }
        for d in dims:
            basis[d] = str(r.get(d, "")).strip()
        for k in bron["kolommen"]:
            w = r.get(k)
            if w is None or (isinstance(w, str) and not w.strip()):
                continue
            uit.append({**basis, "kolom": k, "waarde": w})
    return uit


def _json(sessie, url, params=None):
    r = sessie.get(url, params=params, headers={"Accept": "application/json"}, timeout=180)
    r.raise_for_status()
    return r.json()


def cbs_statline(bron, ctx):
    from omnitwin.bronadapters import BronFout, GeenBron, cache_pad, controleer_url

    url = controleer_url(str(bron["url"]).rstrip("/"))
    if not FEED.match(urlparse(url).path):
        raise BronFout(f"cbs-statline: url moet https://<host>/ODataFeed/odata/<tabel> zijn: {url}")
    if not bron.get("kolommen"):
        raise BronFout("cbs-statline: kolommen ontbreekt")
    sleutel = {
        k: bron.get(k) for k in ("url", "kolommen", "regio", "gemeenten", "gebieden", "regio_prefix", "filter", "jaren")
    }
    cache = cache_pad(ctx.get("bronnen"), "statline", sleutel, ".json")
    if cache.exists():
        rijen = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            import requests
        except ImportError as e:
            raise GeenBron(f"requests ontbreekt: {e}")
        regio = bron.get("regio", "WijkenEnBuurten")
        select = [regio, "Perioden", *(bron.get("filter") or {}).keys(), *bron["kolommen"]]
        try:
            with requests.Session() as s:
                # Echte keys van de dimensies (CBS vult ze soms op met spaties, bijv. '1.1.1 ')
                dim_keys = {
                    d: {str(x["Key"]).strip(): x["Key"] for x in _json(s, f"{url}/{d}").get("value", [])}
                    for d in (bron.get("filter") or {})
                }
                for d, gevraagd in (bron.get("filter") or {}).items():
                    onbekend = {str(k).strip() for k in (gevraagd if isinstance(gevraagd, list) else [gevraagd])} - set(
                        dim_keys[d]
                    )
                    if onbekend:
                        raise BronFout(f"cbs-statline: {d} kent {sorted(onbekend)} niet ({url})")
                params = {"$select": ",".join(select), "$format": "json"}
                f = odata_filter(bron, dim_keys)
                if f:
                    params["$filter"] = f
                data = _json(s, f"{url}/TypedDataSet", params)
                rijen = list(data.get("value", []))
                volgende = data.get("odata.nextLink")
                while volgende:
                    controleer_url(volgende)
                    data = _json(s, volgende)
                    rijen += data.get("value", [])
                    volgende = data.get("odata.nextLink")
        except requests.RequestException as e:
            raise GeenBron(f"StatLine {url} niet bereikbaar: {e}")
        cache.write_text(json.dumps(rijen, ensure_ascii=False), encoding="utf-8")
    return {bron.get("tabel", "waarnemingen"): records(rijen, bron)}
