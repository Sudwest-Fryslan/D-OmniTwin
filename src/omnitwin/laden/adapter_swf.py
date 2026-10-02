"""
Adapter swf-monitor-v1: het pushformaat van de SWF-gebiedsmonitor naar de profielen
===================================================================================
Mapping: `docs/api/laden/profielen/swf-monitor-v1.md`. Gebruikt door de laadstraat als een
dataset `laadprofiel.adapter = swf-monitor-v1` heeft en de levering JSON in dat formaat is;
de compatibiliteitspaden (`/compat/swf-monitor/...`, stap 9 van #205) gebruiken dezelfde
functies.

- waarden (array van SwfWaarde) → regels van profiel waarnemingen;
- definities (SwfDefinities) → resources indicatoren, gebiedstypen en relaties van profiel definities;
- terug: de gepubliceerde stand van een dataset → SwfDefinities of een array van SwfWaardeTerug.

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


# ── terug in het SWF-formaat (leesvarianten van de compatibiliteitsingang) ────

DATUMTIJD = "YYYY-MM-DD HH24:MI"


def definities_terug(cur, dataset_id: str) -> dict:
    """De set die de dataset als laatste publiceerde (laden.dataset_objecten), met de actuele velden."""
    p = {"ds": dataset_id, "f": DATUMTIJD}
    cur.execute("""SELECT i.uuid::text AS id, i.naam, i.omschrijving, i.status,
                          to_char(i.begingeldigheid, %(f)s) AS begingeldigheid,
                          to_char(i.eindgeldigheid, %(f)s) AS eindgeldigheid
                   FROM public.indicatoren i
                   JOIN laden.dataset_objecten o ON o.dataset_id = %(ds)s AND o.soort = 'indicator'
                                                AND o.sleutel = i.uuid::text
                   ORDER BY i.naam, i.uuid""", p)
    indicatoren = [dict(r) for r in cur.fetchall()]
    cur.execute("""SELECT t.id::text AS id, t.naam, t.metadata->>'wfs' AS wfs, t.metadata->>'typenames' AS typenames,
                          t.metadata->>'sleutel' AS sleutel, t.metadata->>'label' AS label, t.actief
                   FROM public.gebiedstypes t
                   JOIN laden.dataset_objecten o ON o.dataset_id = %(ds)s AND o.soort = 'gebiedstype'
                                                AND o.sleutel = t.id::text
                   ORDER BY t.naam, t.id""", p)
    gebiedstypen = [dict(r) for r in cur.fetchall()]
    cur.execute("""SELECT split_part(sleutel, '|', 1) AS indicator_id, split_part(sleutel, '|', 2) AS gebiedstype_id
                   FROM laden.dataset_objecten WHERE dataset_id = %(ds)s AND soort = 'relatie'
                   ORDER BY 1, 2""", p)
    return {"indicatoren": indicatoren, "gebiedstypen": gebiedstypen, "relaties": [dict(r) for r in cur.fetchall()]}


def waarden_terug(cur, dataset_id: str, indicator_id: str | None = None) -> list[dict]:
    """De gepubliceerde waarden van de dataset (zonder de onderdrukte), gebieds_id zonder code_prefix."""
    cur.execute("""SELECT w.indicator_uuid::text AS indicator_id, w.gebiedstype_id::text AS gebiedstype_id,
                          CASE WHEN coalesce(t.metadata->>'code_prefix', '') <> ''
                                AND starts_with(w.gebied_id, t.metadata->>'code_prefix')
                               THEN substr(w.gebied_id, length(t.metadata->>'code_prefix') + 1)
                               ELSE w.gebied_id END AS gebieds_id,
                          coalesce(w.jaar, extract(year FROM w.datum)::int) AS jaar, w.waarde::float8 AS waarde
                   FROM laden.waarnemingen w
                   LEFT JOIN public.gebiedstypes t ON t.id = w.gebiedstype_id
                   WHERE w.dataset_id = %(ds)s AND (%(ind)s::uuid IS NULL OR w.indicator_uuid = %(ind)s::uuid)
                   ORDER BY w.indicator_uuid, w.gebiedstype_id, w.gebied_id, w.jaar, w.datum""",
                {"ds": dataset_id, "ind": indicator_id})
    return [dict(r) for r in cur.fetchall()]
