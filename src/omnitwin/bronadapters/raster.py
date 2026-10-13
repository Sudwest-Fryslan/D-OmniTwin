"""
Adapter `wcs-zonaal`: gemiddelde van een raster (OGC WCS 2.0) per gebied
========================================================================
Haalt per gebied een GeoTIFF-uitsnede in EPSG:28992 op (WCS 2.0.1 GetCoverage met `subset` op X en
Y) en geeft het gemiddelde over de cellen waarvan het middelpunt in het gebied ligt. Voor bijv. de
RIVM Atlas Natuurlijk Kapitaal (boomkroonbedekking, stedelijk hitte-eiland effect).

Parameters (`bron` in `datasets/<id>.json`):

| Parameter | Wat |
|---|---|
| `url` | WCS-endpoint (https, domein op de allowlist) |
| `coverage` | CoverageId |
| `gebieden` | {`bron`, `bewerkingen`?, `sleutel`?}: de gebieden (polygonen), zelf een bron-blok met bewerkingen; `sleutel` = veld met de gebiedscode (standaard `code`) |
| `celgrootte` | celgrootte in meters (standaard 10), voor de marge rond de uitsnede |
| `nodata` | waarden kleiner dan of gelijk aan dit getal zijn nodata (standaard -9999) |
| `nodata_als` | nodata telt als deze waarde (bijv. 0: geen bomen = 0%); zonder: nodata telt niet mee |
| `decimalen` | afronding (standaard 2) |
| `max_cellen` | weiger een uitsnede groter dan dit (standaard 25.000.000, ±50 x 50 km bij 10 m) |

Uitvoer: `{gebied_code, waarde, cellen}` per gebied (geen record als er geen geldige cel is).
Cache: `$DATA_CACHE/bronnen/wcs/<hash>.tif`.
"""

from __future__ import annotations

import io
import math


def geotiff(inhoud):
    """(array, (originx, celx, originy, cely)) uit een GeoTIFF (Pillow). Ondersteunt
    ModelTransformationTag (34264) en ModelTiepoint (33922) + ModelPixelScale (33550)."""
    import numpy as np
    from PIL import Image

    im = Image.open(io.BytesIO(inhoud))
    tags = im.tag_v2
    if 34264 in tags:
        m = tags[34264]
        transform = (m[3], m[0], m[7], m[5])
    elif 33922 in tags and 33550 in tags:
        tp, sc = tags[33922], tags[33550]
        transform = (tp[3] - tp[0] * sc[0], sc[0], tp[4] + tp[1] * sc[1], -sc[1])
    else:
        raise ValueError("GeoTIFF zonder georeferentie (tag 34264 of 33922/33550)")
    return np.array(im, dtype="float64"), transform


def zonaal(a, transform, polys, nodata=-9999, nodata_als=None, decimalen=2):
    """Gemiddelde per polygoon over de cellen met het middelpunt erin. polys: {code: shapely-geometrie}."""
    import numpy as np
    import shapely

    ox, cx, oy, cy = transform
    rij, kol = np.indices(a.shape)
    xs, ys = ox + (kol + 0.5) * cx, oy + (rij + 0.5) * cy
    leeg = a <= nodata
    if nodata_als is not None:
        a = np.where(leeg, float(nodata_als), a)
        leeg = np.zeros_like(leeg)
    uit = {}
    for code, poly in polys.items():
        binnen = shapely.contains_xy(poly, xs, ys) & ~leeg
        n = int(binnen.sum())
        if n:
            uit[code] = (round(float(a[binnen].mean()), decimalen), n)
    return uit


def uitsnede(bounds, cel):
    """Uitsnede op hele cellen met een marge van twee cellen."""
    x0, y0, x1, y1 = bounds
    return (
        int(math.floor(x0 / cel) * cel - 2 * cel),
        int(math.floor(y0 / cel) * cel - 2 * cel),
        int(math.ceil(x1 / cel) * cel + 2 * cel),
        int(math.ceil(y1 / cel) * cel + 2 * cel),
    )


def wcs_zonaal(bron, ctx):
    from omnitwin.bronadapters import BronFout, GeenBron, cache_pad, controleer_url, haal
    from omnitwin.bronadapters.bewerkingen import voer_uit

    controleer_url(bron["url"])
    g = bron.get("gebieden") or {}
    if not isinstance(g.get("bron"), dict):
        raise BronFout("wcs-zonaal: gebieden.bron ontbreekt")
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
        import shapely  # noqa: F401
    except ImportError as e:
        raise GeenBron(f"numpy/Pillow/shapely ontbreekt: {e}")
    tab, _ = voer_uit(haal(g["bron"], ctx), g.get("bewerkingen") or [], ctx)
    sleutel = g.get("sleutel", "code")
    polys = {str(r[sleutel]): r["geometry"] for rs in tab.values() for r in rs if r.get("geometry") is not None}
    if not polys:
        raise BronFout("wcs-zonaal: geen gebieden met geometrie")
    cel = float(bron.get("celgrootte", 10))
    max_cellen = int(bron.get("max_cellen", 25_000_000))
    import requests

    uit = []
    for code, poly in sorted(polys.items()):
        x0, y0, x1, y1 = uitsnede(poly.bounds, cel)
        if (x1 - x0) / cel * (y1 - y0) / cel > max_cellen:
            raise BronFout(f"wcs-zonaal: uitsnede voor {code} groter dan max_cellen ({max_cellen})")
        params = [
            ("service", "WCS"),
            ("version", "2.0.1"),
            ("request", "GetCoverage"),
            ("CoverageId", bron["coverage"]),
            ("format", "image/tiff"),
            ("subset", f"X({x0},{x1})"),
            ("subset", f"Y({y0},{y1})"),
        ]
        cache = cache_pad(ctx.get("bronnen"), "wcs", {"url": bron["url"], "params": params}, ".tif")
        if not cache.exists():
            try:
                r = requests.get(bron["url"], params=params, timeout=180, headers={"User-Agent": "D-OmniTwin"})
                r.raise_for_status()
            except requests.RequestException as e:
                raise GeenBron(f"WCS {bron['url']} niet bereikbaar: {e}")
            if not r.content.startswith((b"II*\x00", b"MM\x00*")):
                raise GeenBron(f"WCS {bron['url']} gaf geen GeoTIFF voor {code}: {r.content[:200]!r}")
            cache.write_bytes(r.content)
        a, transform = geotiff(cache.read_bytes())
        res = zonaal(
            a, transform, {code: poly}, bron.get("nodata", -9999), bron.get("nodata_als"), int(bron.get("decimalen", 2))
        )
        if code in res:
            uit.append({"gebied_code": code, "waarde": res[code][0], "cellen": res[code][1]})
    return {bron.get("tabel", "waarnemingen"): uit}
