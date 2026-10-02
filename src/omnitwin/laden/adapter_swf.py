"""
Adapter swf-monitor-v1: het pushformaat van de SWF-gebiedsmonitor naar de profielen
===================================================================================
Mapping: `docs/api/laden/profielen/swf-monitor-v1.md`. Gebruikt door de laadstraat als een
dataset `laadprofiel.adapter = swf-monitor-v1` heeft en de levering JSON in dat formaat is;
de compatibiliteitspaden (`/compat/swf-monitor/...`, stap 9 van #205) gebruiken dezelfde
functies.

- waarden (array van SwfWaarde) → regels van profiel waarnemingen;
- definities (SwfDefinities) → resources indicatoren, gebiedstypen en relaties van profiel definities.

De vertaling controleert alleen wat het pushformaat anders doet (begingeldigheid → jaar of
peildatum, code_prefix op gebieds_id); de rest gaat daarna door de gewone validatie.
"""

from __future__ import annotations

import datetime as dt

from omnitwin.laden.problemen import Fout

ADAPTER = "swf-monitor-v1"


def is_waarden(data) -> bool:
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) \
        and "indicator_id" in data[0] and "gebieds_id" in data[0]


def is_definities(data) -> bool:
    return isinstance(data, dict) and {"indicatoren", "gebiedstypen", "relaties"} <= set(data)


def _peil(begin) -> tuple[int | None, str | None]:
    """begingeldigheid → (jaar, peildatum). JJJJ-01-01 = jaar; jaar 0 of ongeldig → ValueError."""
    d = dt.date.fromisoformat(str(begin)[:10])
    if d.year < 1900:
        raise ValueError
    return (d.year, None) if (d.month, d.day) == (1, 1) else (None, d.isoformat())


def waarden_naar_waarnemingen(rijen: list[dict], prefixen: dict[str, str]) -> tuple[list[dict], list[Fout], int]:
    """(regels profiel waarnemingen, fouten, aantal met eindgeldigheid). prefixen: gebiedstype-id → code_prefix."""
    uit, fouten, eind = [], [], 0
    for i, r in enumerate(rijen, start=1):
        try:
            jaar, peildatum = _peil(r.get("begingeldigheid"))
        except (TypeError, ValueError):
            fouten.append(Fout("jaar-ongeldig", "begingeldigheid is geen geldige datum vanaf 1900",
                               "waarden", i, "begingeldigheid"))
            jaar, peildatum = None, None
        if r.get("eindgeldigheid"):
            eind += 1
        gt = str(r.get("gebiedstype_id") or "").lower()
        code = "" if r.get("gebieds_id") is None else str(r.get("gebieds_id"))
        prefix = prefixen.get(gt) or ""
        if prefix and code and not code.startswith(prefix):
            code = prefix + code
        uit.append({"gebied_code": code, "gebiedstype": gt or None, "indicator_uuid": r.get("indicator_id"),
                    "jaar": jaar, "peildatum": peildatum, "scenario": "current", "waarde": r.get("waarde"),
                    "n": r.get("n"), "kwaliteit": None, "bron": None, "opmerking": None})
    return uit, fouten, eind


def _datumtijd(w):
    return None if w in (None, "") else str(w)


def definities_naar_resources(data: dict) -> dict[str, list[dict]]:
    """SwfDefinities → {indicatoren, gebiedstypen, relaties} in de velden van profiel definities."""
    indicatoren = [{"uuid": i.get("id"), "naam": i.get("naam"), "omschrijving": i.get("omschrijving"),
                    "status": i.get("status"), "begingeldigheid": _datumtijd(i.get("begingeldigheid")),
                    "eindgeldigheid": _datumtijd(i.get("eindgeldigheid"))}
                   for i in data.get("indicatoren", [])]
    gebiedstypen = [{"id": g.get("id"), "naam": g.get("naam"), "actief": g.get("actief"),
                     "_metadata": {k: g[k] for k in ("wfs", "typenames", "sleutel", "label") if g.get(k)} or None}
                    for g in data.get("gebiedstypen", [])]
    relaties = [{"indicator_uuid": r.get("indicator_id"), "gebiedstype_id": r.get("gebiedstype_id")}
                for r in data.get("relaties", [])]
    return {"indicatoren": indicatoren, "gebiedstypen": gebiedstypen, "relaties": relaties}
