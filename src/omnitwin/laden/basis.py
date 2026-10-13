"""Gedeelde onderdelen van de laadstraat: foutenlijst, afkeuring, COPY naar staging."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from dataclasses import dataclass, field

from omnitwin.laden.problemen import MAX_FOUTEN, Fout

NULL = "\\N"


class Fouten:
    """Fouten van een levering: de eerste MAX_FOUTEN bewaard, het totaal en de foute regels geteld."""

    def __init__(self):
        self.lijst: list[Fout] = []
        self.totaal = 0
        self.regels: set[tuple[str | None, int]] = set()
        self.niet_opgesomd = 0  # foute regels die een SQL-controle telde maar niet opsomde (boven de limiet)

    def voeg(self, f: Fout) -> None:
        self.totaal += 1
        if f.regel is not None:
            self.regels.add((f.resource, f.regel))
        if len(self.lijst) < MAX_FOUTEN:
            self.lijst.append(f)

    def voeg_alle(self, fouten) -> None:
        for f in fouten:
            self.voeg(f)

    def __bool__(self) -> bool:
        return self.totaal > 0

    @property
    def foute_regels(self) -> int:
        return len(self.regels) + self.niet_opgesomd


class Afkeuring(Exception):
    """De levering voldoet niet; niets gepubliceerd."""

    def __init__(self, fouten: Fouten, aantallen: dict | None = None):
        super().__init__(f"{fouten.totaal} fouten")
        self.fouten, self.aantallen = fouten, aantallen or {}


def afkeuren(code: str, melding: str, aantallen: dict | None = None, **waar) -> Afkeuring:
    f = Fouten()
    f.voeg(Fout(code, melding, **waar))
    return Afkeuring(f, aantallen)


@dataclass
class Context:
    """Wat een profiel nodig heeft om een levering te verwerken."""

    levering: dict
    dataset: dict
    max_bytes: int = 200 * 1024 * 1024
    extra: dict = field(default_factory=dict)

    @property
    def laadprofiel(self) -> dict:
        return self.dataset["laadprofiel"] or {}

    @property
    def levering_id(self) -> str:
        return str(self.levering["id"])

    @property
    def dataset_id(self) -> str:
        return self.dataset["id"]


def _veld(w) -> str:
    if w is None:
        return NULL
    if isinstance(w, bool):
        return "true" if w else "false"
    if isinstance(w, (dict, list)):
        return json.dumps(w, ensure_ascii=False)
    if isinstance(w, (dt.date, dt.datetime)):
        return w.isoformat()
    return str(w)


def copy(cur, tabel: str, kolommen: list[str], rijen) -> int:
    """Rijen (tuples in de volgorde van kolommen) met COPY in een tabel. Geeft het aantal."""
    buf, n = io.StringIO(), 0
    w = csv.writer(buf, lineterminator="\n")
    for r in rijen:
        w.writerow([_veld(v) for v in r])
        n += 1
    if not n:
        return 0
    buf.seek(0)
    cur.copy_expert(f"COPY {tabel} ({', '.join(kolommen)}) FROM STDIN WITH (FORMAT csv, NULL '{NULL}')", buf)
    return n


def sql_fouten(
    cur, fouten: Fouten, sql: str, params: dict, code: str, resource: str, veld: str | None, melding: str
) -> int:
    """Voer een query uit die (regel, totaal = count(*) OVER ()) teruggeeft voor elke foute regel, met een
    LIMIT; voeg ze als fout toe en tel de rest mee. Geeft het aantal foute regels."""
    cur.execute(sql, params)
    n, totaal = 0, 0
    for r in cur.fetchall():
        n += 1
        totaal = r.get("totaal") or n
        fouten.voeg(Fout(code, melding.format(**r), resource, r["regel"], veld))
    if totaal > n:  # de query somt hooguit LIMIT regels op; count(*) OVER () telt ze allemaal
        fouten.totaal += totaal - n
        fouten.niet_opgesomd += totaal - n
    return totaal
