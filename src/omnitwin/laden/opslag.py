"""
Opslag van ruwe leveringen
==========================
Elk geleverd bestand wordt ongewijzigd bewaard, met sha256, op het volume `leveringen`
(`LEVERINGEN_DIR`, in de container `/leveringen`):

    <LEVERINGEN_DIR>/<dataset>/<levering_id>/<bestand>

Het bestand wordt eerst naar `<LEVERINGEN_DIR>/.ontvangst/` gestreamd (zonder het in het
geheugen te lezen; limiet `LADEN_MAX_MB`), daarna met een rename op zijn plek gezet en
alleen-lezen gemaakt. Een levering wordt nooit overschreven.

Bewaartermijn (`ruim_op`, na elke publicatie en aan te roepen door een periodieke taak):
- altijd de bestanden van de laatste `LADEN_BEWAAR_VERSIES` versies per dataset (en de actieve);
- andere gepubliceerde leveringen tot `LADEN_BEWAAR_DAGEN` na afronding;
- afgekeurde, mislukte en alleen-gevalideerde leveringen tot `LADEN_BEWAAR_AFGEKEURD_DAGEN`.
De registratie van de levering (status, aantallen, fouten, sha256) blijft; alleen het bestand gaat weg.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

from omnitwin.config import instellingen

logger = logging.getLogger("omnitwin.laden.opslag")

EXTENSIE = {
    "application/zip": ".zip",
    "application/geopackage+sqlite3": ".gpkg",
    "text/csv": ".csv",
    "application/json": ".json",
}
BLOK = 1024 * 1024


class TeGroot(Exception):
    """De body is groter dan de limiet."""


@dataclass
class Ontvangen:
    pad: Path  # tijdelijk bestand in .ontvangst/
    sha256: str
    grootte: int


def basis() -> Path:
    return Path(instellingen().leveringen_dir)


def _ontvangst() -> Path:
    p = basis() / ".ontvangst"
    p.mkdir(parents=True, exist_ok=True)
    return p


def veilige_bestandsnaam(naam: str | None, mediatype: str) -> str:
    """Alleen de bestandsnaam, zonder map of vreemde tekens; standaard levering.<ext>."""
    ext = EXTENSIE.get(mediatype, ".bin")
    naam = Path((naam or "").replace("\\", "/")).name
    naam = re.sub(r"[^A-Za-z0-9._-]", "_", naam).lstrip(".")[:120]
    return naam or f"levering{ext}"


class Schrijver:
    """Schrijft blokken naar een tijdelijk bestand en telt sha256 en grootte; TeGroot boven de limiet."""

    def __init__(self, limiet: int):
        self.limiet, self.grootte, self.h = limiet, 0, hashlib.sha256()
        self.pad = _ontvangst() / f"{uuid.uuid4().hex}.deel"
        self.f = open(self.pad, "wb")

    def schrijf(self, blok: bytes) -> None:
        self.grootte += len(blok)
        if self.grootte > self.limiet:
            self.weg()
            raise TeGroot()
        self.h.update(blok)
        self.f.write(blok)

    def klaar(self) -> Ontvangen:
        self.f.close()
        return Ontvangen(self.pad, self.h.hexdigest(), self.grootte)

    def weg(self) -> None:
        try:
            self.f.close()
        finally:
            self.pad.unlink(missing_ok=True)


def ontvang_bestand(fileobj, limiet: int) -> Ontvangen:
    """Kopieer een (spooled) bestand naar de ontvangstmap, met sha256."""
    s = Schrijver(limiet)
    try:
        while True:
            blok = fileobj.read(BLOK)
            if not blok:
                break
            s.schrijf(blok)
    except TeGroot:
        raise
    except BaseException:
        s.weg()
        raise
    return s.klaar()


def pad(dataset_id: str, levering_id: str, bestandsnaam: str) -> Path:
    return basis() / dataset_id / str(levering_id) / bestandsnaam


def bewaar(ontvangen: Ontvangen, dataset_id: str, levering_id: str, bestandsnaam: str) -> Path:
    """Zet het ontvangen bestand op zijn definitieve plek, alleen-lezen. Nooit overschrijven."""
    doel = pad(dataset_id, levering_id, bestandsnaam)
    doel.parent.mkdir(parents=True, exist_ok=False)
    os.replace(ontvangen.pad, doel)
    doel.chmod(stat.S_IRUSR | stat.S_IRGRP)
    return doel


def verwijder_tijdelijk(ontvangen: Ontvangen | None) -> None:
    if ontvangen:
        ontvangen.pad.unlink(missing_ok=True)


def _verwijder(p: Path) -> bool:
    try:
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)
        p.unlink()
        try:
            p.parent.rmdir()
        except OSError:
            pass
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        logger.warning("Levering %s niet verwijderd: %s", p, e)
        return False


TE_VERWIJDEREN_SQL = """
WITH recent AS (
    SELECT dataset_id, unnest(levering_ids) AS levering_id
    FROM (SELECT dataset_id, levering_ids, actief,
                 row_number() OVER (PARTITION BY dataset_id ORDER BY versie DESC) AS rang
          FROM laden.versies) v
    WHERE rang <= %(versies)s OR actief
)
SELECT l.id::text AS id, l.dataset_id, l.bestandsnaam
FROM laden.leveringen l
WHERE l.bestand_verwijderd_op IS NULL
  AND l.klaar_op IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM recent r WHERE r.levering_id = l.id)
  AND (
        (l.status IN ('afgekeurd', 'mislukt', 'gevalideerd')
         AND l.klaar_op < now() - make_interval(days => %(afgekeurd)s))
     OR (l.status = 'gepubliceerd' AND l.klaar_op < now() - make_interval(days => %(dagen)s))
  )
"""


def ruim_op(cur) -> int:
    """Verwijder de bestanden waarvan de bewaartermijn verstreken is. Geeft het aantal."""
    inst = instellingen()
    cur.execute(
        TE_VERWIJDEREN_SQL,
        {
            "versies": inst.laden_bewaar_versies,
            "dagen": inst.laden_bewaar_dagen,
            "afgekeurd": inst.laden_bewaar_afgekeurd_dagen,
        },
    )
    weg = [r for r in cur.fetchall() if _verwijder(pad(r["dataset_id"], r["id"], r["bestandsnaam"]))]
    if weg:
        cur.execute(
            "UPDATE laden.leveringen SET bestand_verwijderd_op = now() WHERE id = ANY(%s::uuid[])",
            ([r["id"] for r in weg],),
        )
        logger.info("Bewaartermijn: %d ruwe leveringen verwijderd", len(weg))
    return len(weg)
