"""
Bronadapters: data ophalen voor een levering, gestuurd door het `bron`-blok van een dataset
============================================================================================
Een use case bevat geen code (usecases/README.md). Waar de data vandaan komt, staat
declaratief in `usecases/<naam>/datasets/<id>.json` onder `bron`; de vaste set adapters
hieronder voert dat uit. Een nieuwe soort bron = een nieuwe adapter hier, via een PR met tests.

| Adapter | Wat | Parameters |
|---|---|---|
| `swf-dump` | export van de huidige SWF-gebiedsmonitor (definities of waarden) | `export` |
| `cbs-odata` | CBS Kerncijfers wijken en buurten (recept `init_data/cbs/datapackage.json`) | `gemeenten`, `jaren` |
| `wfs` | WFS 2.0 (bijv. PDOK), GeoJSON in EPSG:28992 | `url`, `laag`, `bbox`, `filter` |
| `download` | een bestand via https (gpkg, geojson, csv, json) | `url`, `sha256`, `formaat`, `laag`, `crs` |
| `lokaal-bestand` | een bestand onder een toegestane map (`${SWF_DOCS_DIR}/...`) | `pad`, `formaat`, `laag`, `crs` |
| `usecase-bestand` | een statisch JSON- of CSV-bestand in de use case zelf (mapping, sjabloon) | `pad` |

Elke adapter geeft `Tabellen`: {tabelnaam: [record]}, records zijn dicts; een geometrie staat
als shapely-object onder `geometry`, altijd in EPSG:28992.

Veiligheid:
- paden alleen onder de mappen van de omgevingsvariabelen in `TOEGESTANE_MAPPEN` (of de repo
  via `${REPO}`); `..` en symlinks die eruit wijzen worden geweigerd;
- downloads alleen via https van een domein uit `TOEGESTANE_DOMEINEN` (uit te breiden met
  `OMNITWIN_BRON_DOMEINEN`, kommagescheiden), met optionele sha256;
- geen expressies of code uit het manifest; bewerkingen staan in `bewerkingen.py`.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
TOEGESTANE_MAPPEN = ("SWF_DUMP_DIR", "SWF_DOCS_DIR", "SWF_GEO_DIR", "SWF_DB_DUMP", "DATA_CACHE", "REPO")
TOEGESTANE_DOMEINEN = (
    "opendata.cbs.nl", "datasets.cbs.nl", "www.cbs.nl",
    "service.pdok.nl", "api.pdok.nl",
    "data.rivm.nl",
    "www.klimaateffectatlas.nl", "klimaateffectatlas.nl",
)


class BronFout(ValueError):
    """Het bron-blok is ongeldig of niet toegestaan (onbekende adapter, pad of domein)."""


class GeenBron(LookupError):
    """De bron is (hier) niet beschikbaar: omgevingsvariabele niet gezet, bestand ontbreekt,
    geen netwerk. De uitvoerder meldt dat als 'overgeslagen', niet als fout."""


def map_van(var, bronnen=None):
    if var not in TOEGESTANE_MAPPEN:
        raise BronFout(f"${{{var}}} is geen toegestane map ({', '.join(TOEGESTANE_MAPPEN)})")
    if var == "REPO":
        return ROOT
    waarde = (bronnen or {}).get(var) or os.environ.get(var)
    if var == "DATA_CACHE" and not waarde:
        waarde = str(ROOT / "data-cache")
    if not waarde:
        raise GeenBron(f"{var} is niet gezet (zie de README van de use case)")
    return Path(waarde)


def veilig_pad(sjabloon, bronnen=None):
    """'${VAR}/sub/bestand' → absoluut pad binnen de map van VAR. Andere vormen worden geweigerd."""
    m = re.fullmatch(r"\$\{([A-Z_]+)\}/(.+)", str(sjabloon))
    if not m:
        raise BronFout(f"pad moet beginnen met ${{VAR}}/ uit {TOEGESTANE_MAPPEN}: {sjabloon!r}")
    basis = map_van(m.group(1), bronnen).resolve()
    pad = (basis / m.group(2)).resolve()
    if basis != pad and basis not in pad.parents:
        raise BronFout(f"pad buiten ${{{m.group(1)}}}: {sjabloon!r}")
    return pad


def toegestane_domeinen():
    extra = [d.strip() for d in os.environ.get("OMNITWIN_BRON_DOMEINEN", "").split(",") if d.strip()]
    return tuple(TOEGESTANE_DOMEINEN) + tuple(extra)


def controleer_url(url):
    u = urlparse(url)
    if u.scheme != "https":
        raise BronFout(f"alleen https: {url}")
    if u.hostname not in toegestane_domeinen():
        raise BronFout(f"domein {u.hostname} niet toegestaan (OMNITWIN_BRON_DOMEINEN om uit te breiden)")
    return url


def cache_pad(bronnen, soort, sleutel, achtervoegsel):
    h = hashlib.sha256(json.dumps(sleutel, sort_keys=True).encode()).hexdigest()[:16]
    pad = map_van("DATA_CACHE", bronnen) / "bronnen" / soort / f"{h}{achtervoegsel}"
    pad.parent.mkdir(parents=True, exist_ok=True)
    return pad


# ------------------------------------------------------------------ adapters

def swf_dump(bron, ctx):
    """Export van de huidige monitor: `export` = definities (3 tabellen) of waarden (1 tabel)."""
    basis = map_van("SWF_DUMP_DIR", ctx.get("bronnen"))
    bestand = {"definities": "output/api_backup_dump.json", "waarden": "output/api_data_dump.json"}.get(bron.get("export"))
    if not bestand:
        raise BronFout("swf-dump: export moet definities of waarden zijn")
    pad = veilig_pad(f"${{SWF_DUMP_DIR}}/{bestand}", ctx.get("bronnen"))
    if not pad.exists():
        raise GeenBron(f"{pad} ontbreekt in SWF_DUMP_DIR={basis}")
    data = json.loads(pad.read_text(encoding="utf-8"))
    if bron["export"] == "definities":
        return {k: [dict(r) for r in data.get(k, [])] for k in ("indicatoren", "gebiedstypen", "relaties")}
    return {"waarden": [dict(r) for r in data]}


def lokaal_bestand(bron, ctx):
    pad = veilig_pad(bron["pad"], ctx.get("bronnen"))
    if not pad.exists():
        raise GeenBron(f"{pad} ontbreekt")
    from omnitwin.bronadapters.bestanden import lees_bestand
    return lees_bestand(pad, bron.get("formaat"), bron.get("laag"), bron.get("tabel", "data"), bron.get("crs"))


def usecase_bestand(bron, ctx):
    basis = Path(ctx["usecase_map"]).resolve()
    pad = (basis / bron["pad"]).resolve()
    if basis not in pad.parents or pad.suffix not in (".json", ".csv"):
        raise BronFout(f"usecase-bestand: alleen .json/.csv in de use case: {bron['pad']!r}")
    from omnitwin.bronadapters.bestanden import lees_bestand
    return lees_bestand(pad, None, None, bron.get("tabel", "data"))


def wfs(bron, ctx):
    """WFS 2.0 GetFeature als GeoJSON in EPSG:28992, gepagineerd, met cache in $DATA_CACHE/bronnen/wfs."""
    controleer_url(bron["url"])
    sleutel = {k: bron.get(k) for k in ("url", "laag", "bbox")}
    cache = cache_pad(ctx.get("bronnen"), "wfs", sleutel, ".geojson")
    if not cache.exists():
        try:
            import requests
        except ImportError as e:
            raise GeenBron(f"requests ontbreekt: {e}")
        feats, start, pagina = [], 0, int(bron.get("pagina", 1000))
        while True:
            params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": bron["laag"],
                      "outputFormat": "application/json", "srsName": "EPSG:28992", "count": pagina, "startIndex": start}
            if bron.get("bbox"):
                params["bbox"] = ",".join(map(str, bron["bbox"])) + ",urn:ogc:def:crs:EPSG::28992"
            try:
                r = requests.get(bron["url"], params=params, timeout=180)
                r.raise_for_status()
            except requests.RequestException as e:
                raise GeenBron(f"WFS {bron['url']} niet bereikbaar: {e}")
            fs = r.json().get("features", [])
            feats += fs
            if len(fs) < pagina:
                break
            start += pagina
        cache.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    from omnitwin.bronadapters.bestanden import lees_geojson
    return {bron.get("tabel", "data"): lees_geojson(cache, epsg=28992)}


def download(bron, ctx):
    controleer_url(bron["url"])
    formaat = bron.get("formaat") or Path(urlparse(bron["url"]).path).suffix.lstrip(".")
    cache = cache_pad(ctx.get("bronnen"), "download", {"url": bron["url"]}, f".{formaat}")
    if not cache.exists():
        import requests
        try:
            r = requests.get(bron["url"], timeout=300)
            r.raise_for_status()
        except requests.RequestException as e:
            raise GeenBron(f"{bron['url']} niet bereikbaar: {e}")
        cache.write_bytes(r.content)
    if bron.get("sha256"):
        h = hashlib.sha256(cache.read_bytes()).hexdigest()
        if h != bron["sha256"]:
            cache.unlink()
            raise BronFout(f"sha256 van {bron['url']} is {h}, verwacht {bron['sha256']}")
    from omnitwin.bronadapters.bestanden import lees_bestand
    return lees_bestand(cache, formaat, bron.get("laag"), bron.get("tabel", "data"), bron.get("crs"))


def cbs_odata(bron, ctx):
    """CBS Kerncijfers wijken en buurten via init_data/scripts/download_cbs_kerncijfers.py (met cache).
    `gemeenten`: gemeentecodes (4 cijfers) of leeg = heel Fryslân; `jaren`: optioneel filter."""
    import sys
    scripts = str(ROOT / "init_data" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    cache = ctx.get("bronnen", {}).get("DATA_CACHE")
    if cache:
        os.environ.setdefault("DATA_CACHE", cache)
    try:
        import download_cbs_kerncijfers as cbs
    except ImportError as e:
        raise GeenBron(f"CBS-downloader niet te laden: {e}")
    gemeenten = [str(g).zfill(4) for g in bron.get("gemeenten") or []]
    codes = sorted(c for c in cbs.geometrie_codes() if not gemeenten or c[2:6] in gemeenten)
    try:
        rijen = cbs.rijen_voor(codes, log=lambda *a, **k: None)
    except Exception as e:  # netwerk, CBS onbereikbaar
        raise GeenBron(f"CBS OData niet bereikbaar: {type(e).__name__}: {e}")
    jaren = {int(j) for j in bron.get("jaren") or []}
    return {bron.get("tabel", "waarnemingen"): [dict(r) for r in rijen if not jaren or int(r["jaar"]) in jaren]}


ADAPTERS = {
    "swf-dump": swf_dump,
    "cbs-odata": cbs_odata,
    "wfs": wfs,
    "download": download,
    "lokaal-bestand": lokaal_bestand,
    "usecase-bestand": usecase_bestand,
}


def haal(bron, ctx):
    """Voer een bron-blok uit: {adapter: ..., ...}. ctx: {'bronnen': {...}, 'usecase_map': Path}."""
    adapter = ADAPTERS.get((bron or {}).get("adapter"))
    if adapter is None:
        raise BronFout(f"onbekende adapter {bron.get('adapter')!r}; bekend: {sorted(ADAPTERS)}")
    return adapter(bron, ctx)
