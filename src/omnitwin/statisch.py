"""Cachebeleid voor statische bestanden (#246).

Zonder Cache-Control kiest de browser zelf hoe lang hij een bestand bewaart; na een upgrade
toonde hij dan het oude thema of een oud beeldmerk tot een harde herlaadactie. Daarom:

- bestanden met een versie of hash in het pad (``vendor/<pakket>@<versie>/``, de Vite-assets
  van het beheerscherm ``admin-panel/assets/<naam>-<hash>.<ext>``): een jaar, ``immutable``;
- al het andere (eigen css/js, beeldmerk, thema's, HTML): ``no-cache``, dus elke keer
  opnieuw valideren met de ETag; ongewijzigd kost dat alleen een 304.
"""

import re

from fastapi.staticfiles import StaticFiles

ONVERANDERLIJK = "public, max-age=31536000, immutable"
OPNIEUW_VALIDEREN = "no-cache"

_VENDOR = re.compile(r"(^|/)vendor/[^/]+@[^/]+/")
_VITE_ASSET = re.compile(r"(^|/)admin-panel/assets/[^/]+-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$")


def cache_control(pad: str) -> str:
    """Cache-Control voor een pad relatief aan /static (of /admin met prefix admin-panel/)."""
    pad = pad.replace("\\", "/").lstrip("/")
    if _VENDOR.search(pad) or _VITE_ASSET.search(pad):
        return ONVERANDERLIJK
    return OPNIEUW_VALIDEREN


class StatischeBestanden(StaticFiles):
    """StaticFiles met het cachebeleid hierboven."""

    def file_response(self, full_path, stat_result, scope, status_code=200):
        antwoord = super().file_response(full_path, stat_result, scope, status_code)
        antwoord.headers["Cache-Control"] = cache_control(scope.get("path", ""))
        return antwoord
