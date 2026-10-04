"""
Frictionless Table Schema (v2), alleen wat de profielen gebruiken
=================================================================
Velden van het type string, integer, number, boolean, date en datetime, met `format: uuid`
en de constraints required, unique, minLength, maxLength, minimum, maximum en enum;
`missingValues`. Werkt op CSV-tekst (alles is tekst) en op JSON-waarden (al getypeerd).

Bewust een eigen, kleine validator in plaats van frictionless: geen extra afhankelijkheid in
de image en snel genoeg voor ±200.000 regels. De lokale controle (`omnitwin.laden.levering`,
`python -m omnitwin.usecases controleer`) gebruikt frictionless zelf, tegen dezelfde schema's
in `docs/api/laden/profielen/`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from omnitwin.laden.problemen import Fout

PROFIELEN = Path(__file__).resolve().parents[3] / "docs" / "api" / "laden" / "profielen"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
INT_RE = re.compile(r"^[+-]?\d+$")
WAAR, ONWAAR = {"true", "True", "TRUE", "1", "ja"}, {"false", "False", "FALSE", "0", "nee"}


def laad_schema(naam: str) -> dict:
    """Table Schema uit docs/api/laden/profielen/<naam>.schema.json."""
    return json.loads((PROFIELEN / f"{naam}.schema.json").read_text(encoding="utf-8"))


class Ongeldig(ValueError):
    pass


def _datumtijd(w: str) -> dt.datetime:
    t = w.strip().replace("Z", "+00:00")
    if len(t) == 16 and t[10] in " T":  # JJJJ-MM-DD HH:MM (SWF-monitor)
        t += ":00"
    d = dt.datetime.fromisoformat(t.replace(" ", "T", 1))
    return d.astimezone(dt.timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def converteer(waarde, veld: dict):
    """Waarde (tekst of JSON) naar het type van het veld; None voor een lege waarde. Ongeldig bij een typefout."""
    if waarde is None or (isinstance(waarde, str) and waarde == ""):
        return None
    t = veld.get("type", "string")
    try:
        if t == "string":
            w = waarde if isinstance(waarde, str) else (str(waarde) if not isinstance(waarde, (dict, list, bool)) else None)
            if w is None:
                raise Ongeldig("geen tekst")
            if veld.get("format") == "uuid" and not UUID_RE.match(w):
                raise Ongeldig("geen UUID")
            return w.lower() if veld.get("format") == "uuid" else w
        if t == "integer":
            if isinstance(waarde, bool):
                raise Ongeldig("geen geheel getal")
            if isinstance(waarde, int):
                return waarde
            if isinstance(waarde, float):
                if waarde != int(waarde):
                    raise Ongeldig("geen geheel getal")
                return int(waarde)
            if not INT_RE.match(str(waarde).strip()):
                raise Ongeldig("geen geheel getal")
            return int(str(waarde).strip())
        if t == "number":
            if isinstance(waarde, bool):
                raise Ongeldig("geen getal")
            if isinstance(waarde, (int, float)):
                f = float(waarde)
            else:
                f = float(str(waarde).strip())
            if f != f or f in (float("inf"), float("-inf")):
                raise Ongeldig("geen eindig getal")
            return waarde if isinstance(waarde, (int, float)) else str(waarde).strip()
        if t == "boolean":
            if isinstance(waarde, bool):
                return waarde
            if str(waarde) in WAAR:
                return True
            if str(waarde) in ONWAAR:
                return False
            raise Ongeldig("geen boolean")
        if t == "date":
            s = str(waarde).strip()
            if len(s) != 10:
                raise Ongeldig("geen datum (JJJJ-MM-DD)")
            return dt.date.fromisoformat(s)
        if t == "datetime":
            return _datumtijd(str(waarde))
    except Ongeldig:
        raise
    except (TypeError, ValueError):
        raise Ongeldig(f"geen geldige {t}")
    return waarde


def _getal(w) -> float:
    return float(w)


def controleer_waarde(w, veld: dict) -> str | None:
    """Constraints op een al geconverteerde waarde; None = goed, anders de melding (zonder de waarde)."""
    c = veld.get("constraints") or {}
    if w is None:
        return "verplicht veld is leeg" if c.get("required") else None
    if isinstance(w, str) and veld.get("type", "string") == "string":
        if "maxLength" in c and len(w) > c["maxLength"]:
            return f"langer dan {c['maxLength']} tekens"
        if "minLength" in c and len(w) < c["minLength"]:
            return f"korter dan {c['minLength']} tekens"
    if veld.get("type") in ("integer", "number"):
        if "minimum" in c and _getal(w) < c["minimum"]:
            return f"kleiner dan {c['minimum']}"
        if "maximum" in c and _getal(w) > c["maximum"]:
            return f"groter dan {c['maximum']}"
    if "enum" in c and w not in c["enum"]:
        return f"niet een van {', '.join(map(str, c['enum']))}"
    return None


class Tabel:
    """Validator voor één resource met een Table Schema."""

    def __init__(self, schema: dict, resource: str, extra_velden: dict | None = None):
        self.schema, self.resource = schema, resource
        self.velden = {f["name"]: f for f in schema["fields"]}
        self.extra = extra_velden or {}  # velden uit een eigen schema: naar metadata
        self.missing = set(schema.get("missingValues", [""]))
        self.uniek = {n: {} for n, f in self.velden.items() if (f.get("constraints") or {}).get("unique")}

    def controleer_kop(self, kop: list[str], strikt: bool = True) -> list[Fout]:
        """Kolommen: alle profielvelden aanwezig (CSV), geen onbekende kolommen."""
        fouten = []
        bekend = set(self.velden) | set(self.extra)
        onbekend = [k for k in kop if k not in bekend]
        if onbekend:
            fouten.append(Fout("schema-ongeldig", f"onbekende kolom(men): {', '.join(onbekend[:10])}; extra velden "
                               "alleen via een eigen schema in het laadprofiel", self.resource))
        if strikt:
            ontbreekt = [n for n in self.velden if n not in kop]
            if ontbreekt:
                fouten.append(Fout("schema-ongeldig", f"kolom(men) uit het profiel ontbreken: {', '.join(ontbreekt)}",
                                   self.resource))
        return fouten

    def rij(self, ruw: dict, regel: int) -> tuple[dict, list[Fout]]:
        """(geconverteerde rij, fouten). Extra velden komen onder '_metadata'."""
        uit, fouten = {}, []
        for naam, veld in self.velden.items():
            w = ruw.get(naam)
            if isinstance(w, str) and w in self.missing:
                w = None
            try:
                w = converteer(w, veld)
            except Ongeldig as e:
                fouten.append(Fout("schema-ongeldig", f"{naam}: {e}", self.resource, regel, naam))
                uit[naam] = None
                continue
            melding = controleer_waarde(w, veld)
            if melding:
                fouten.append(Fout("schema-ongeldig", f"{naam}: {melding}", self.resource, regel, naam))
            if naam in self.uniek and w is not None:
                eerder = self.uniek[naam].setdefault(w, regel)
                if eerder != regel:
                    fouten.append(Fout("dubbele-sleutel", f"{naam} komt ook voor in regel {eerder}",
                                       self.resource, regel, naam))
            uit[naam] = w
        if self.extra:
            meta = {}
            for naam, veld in self.extra.items():
                try:
                    w = converteer(ruw.get(naam), veld)
                except Ongeldig as e:
                    fouten.append(Fout("schema-ongeldig", f"{naam}: {e}", self.resource, regel, naam))
                    continue
                if w is not None:
                    meta[naam] = w.isoformat() if isinstance(w, (dt.date, dt.datetime)) else w
            uit["_metadata"] = meta or None
        return uit, fouten
