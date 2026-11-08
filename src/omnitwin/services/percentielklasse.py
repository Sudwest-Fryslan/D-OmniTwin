"""
Percentielklasse (8 x 12,5%) en klasse-aggregatie (#255)
========================================================
Eén plek voor de classificatie `percentiel_8`, naast de huidige weergave `zscore`.
Kaart (gebiedsmonitor_service) en Kompas (kompas_service) gebruiken deze functies.

De referentiegroep komt uit dezelfde SQL-functie als de Z-score
(public.zscore_referentie_waarden, #66): gebiedstype + gemeente, zelfde jaar,
zonder waterbuurten, alleen scenario 'current'.

Aanname tot https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/222 antwoord geeft
(methodiek: docs/3-data-engineering/percentielklasse_methodiek.md):

- percentiel = middenrang: (aantal lager + de helft van het aantal gelijk) / n,
  over de referentiegroep (de waarde van het gebied zelf telt mee). Gelijke
  waarden krijgen zo hetzelfde percentiel en dezelfde klasse.
- polariteit: bij "lager is beter" geldt 1 - percentiel. Klasse 8 is altijd de
  gunstigste 12,5%, klasse 1 de ongunstigste.
- klasse = floor(percentiel x 8) + 1, begrensd op 1..8.
- waarden met n onder de drempel voor kleine aantallen (services/kleine_aantallen.py,
  instelbaar, standaard 10) tellen niet mee, niet in de referentie en niet als
  doelwaarde (klasse None, status 'onderdrukt').
- aggregatie (onderdeel, thema, kwadrant en multi-selectie): gewogen gemiddelde
  van de indicatorklassen eronder, gewicht = aantal gebieden met data in de
  referentiegroep van die indicator; daarna afronden naar de dichtstbijzijnde
  klasse (x,5 naar boven).
"""

import math
from collections.abc import Iterable, Sequence

from omnitwin import polariteit
from omnitwin.services import kleine_aantallen as ka

# label_ae: labels A-E per indicator en thema (#256), zie services/labelklasse.py
CLASSIFICATIES = ("zscore", "percentiel_8", "label_ae")
CLASSIFICATIE_STANDAARD = "zscore"
KLASSEN = 8
# Onderdrukking bij kleine aantallen: de standaard; de drempel van de instantie staat in
# organisatie.n_drempel (kleine_aantallen.drempel). De laad-API laat zulke waarden al weg
# (n-drempel per dataset); dit vangt waarden die buiten de laad-API zijn geladen.
N_DREMPEL = ka.N_DREMPEL_STANDAARD

# Kleurenblindvriendelijk palet: color_schemas.naam (stuurdata). Klasse 1 = 'min',
# klasse 8 = 'max'. Fallback = dezelfde kleuren, voor een database zonder dat schema.
PALET_SCHEMA = "colorblind-safe"
PALET_FALLBACK = {"min": "#ae2012", "mid": "#fdf0d5", "max": "#0077b6"}
# Kwadrant Samenstelling is neutraal (geen beter of slechter, methodiek SWF): een
# opeenvolgend blauw palet, en het telt niet mee in de klasse van de wortel.
PALET_NEUTRAAL_SCHEMA = "sequential-blue"
PALET_NEUTRAAL_FALLBACK = {"min": "#deebf7", "mid": "#4292c6", "max": "#08306b"}


def is_neutraal_kwadrant(naam: str | None) -> bool:
    return bool(naam) and "samenstelling" in naam.lower()


def hoger_is_beter(score_type: str | None, inverse: bool | None = False) -> bool:
    """Eén regel voor kaart, Kompas en rapporten (omnitwin.polariteit, #120)."""
    return not polariteit.lager_is_beter(score_type, inverse)


def richting(score_type: str | None, inverse: bool | None = False, kwadrant: str | None = None) -> str:
    """'hoger_is_beter' | 'lager_is_beter' | 'neutraal' (kwadrant Samenstelling of polariteit neutraal),
    voor de kleur van een afwijking (bijv. de Kompas-benchmark, #323, en de Gebiedsfactsheet, #441)."""
    if is_neutraal_kwadrant(kwadrant) or (not inverse and polariteit.uit_oud(score_type) == polariteit.NEUTRAAL):
        return "neutraal"
    return "hoger_is_beter" if hoger_is_beter(score_type, inverse) else "lager_is_beter"


def is_onderdrukt(n: int | None, drempel: int = N_DREMPEL) -> bool:
    return ka.is_onderdrukt(n, drempel)


def percentiel(waarde: float, referentie: Sequence[float]) -> float | None:
    """Middenrang-percentiel (0..1) van waarde in de referentie; None zonder referentie."""
    if waarde is None or not referentie:
        return None
    lager = sum(1 for r in referentie if r < waarde)
    gelijk = sum(1 for r in referentie if r == waarde)
    return (lager + 0.5 * gelijk) / len(referentie)


def klasse_uit_percentiel(p: float | None, hoger_beter: bool = True) -> int | None:
    if p is None:
        return None
    if not hoger_beter:
        p = 1.0 - p
    return max(1, min(KLASSEN, math.floor(p * KLASSEN) + 1))


def klasse(waarde: float | None, referentie: Sequence[float], hoger_beter: bool = True) -> int | None:
    """Percentielklasse 1..8 (8 = gunstigst) van waarde binnen de referentie."""
    return klasse_uit_percentiel(percentiel(waarde, referentie), hoger_beter)


def rond_klasse(x: float, klassen: int = KLASSEN) -> int:
    """Afronden naar de dichtstbijzijnde klasse, x,5 naar boven."""
    return max(1, min(klassen, math.floor(x + 0.5)))


def gemiddelde_score(klassen_met_gewicht: Iterable[tuple[int | None, float | None]]) -> float | None:
    """
    Onafgerond gewogen gemiddelde van klassen (op schaal 1,0..8,0). Paren zonder klasse of
    met gewicht <= 0 tellen niet mee. None als er niets overblijft.
    """
    som = gewicht = 0.0
    for k, w in klassen_met_gewicht:
        if k is None or not w or w <= 0:
            continue
        som += k * w
        gewicht += w
    if gewicht == 0:
        return None
    return som / gewicht


def aggregeer(klassen_met_gewicht: Iterable[tuple[int | None, float | None]], klassen: int = KLASSEN) -> int | None:
    """
    Gewogen gemiddelde van klassen, afgerond naar een klasse. Paren zonder klasse of
    met gewicht <= 0 tellen niet mee. None als er niets overblijft.
    """
    gem = gemiddelde_score(klassen_met_gewicht)
    if gem is None:
        return None
    return rond_klasse(gem, klassen)


def klasse_label(k: int, neutraal: bool = False) -> str:
    """Bijv. 'klasse 1: 0-12,5% (ongunstigst)'; neutraal (Samenstelling): '(laagst)'/'(hoogst)'."""
    van = (k - 1) * 100 / KLASSEN
    tot = k * 100 / KLASSEN

    def fmt(x: float) -> str:
        return f"{x:g}".replace(".", ",")

    label = f"klasse {k}: {fmt(van)}–{fmt(tot)}%"
    if k == 1:
        label += " (laagst)" if neutraal else " (ongunstigst)"
    elif k == KLASSEN:
        label += " (hoogst)" if neutraal else " (gunstigst)"
    return label


def palet(color_service=None, neutraal: bool = False, klassen: int = KLASSEN) -> list[str]:
    """Kleuren voor klasse 1..klassen (standaard 8), uit color_schemas
    (kleurenblindvriendelijk; neutraal: blauw)."""
    from omnitwin.services.color_scale_service import ColorScaleService

    schema, fallback = (PALET_NEUTRAAL_SCHEMA, PALET_NEUTRAAL_FALLBACK) if neutraal else (PALET_SCHEMA, PALET_FALLBACK)
    kleuren = None
    if color_service is not None and color_service.db is not None:
        kleuren = color_service.schema_kleuren(schema)
    svc = color_service or ColorScaleService(db=None)
    return svc.generate_color_ramp(kleuren or fallback, klassen)


def legenda(kleuren: list[str], neutraal: bool = False) -> list[dict[str, object]]:
    return [{"klasse": k, "label": klasse_label(k, neutraal), "kleur": kleuren[k - 1]} for k in range(1, KLASSEN + 1)]


def normaliseer_classificatie(waarde: str | None) -> str:
    return waarde if waarde in CLASSIFICATIES else CLASSIFICATIE_STANDAARD


# ── Referentie uit de database ───────────────────────────────────────────────
# Dezelfde referentiefunctie als de Z-score (#66); per gemeente één aanroep (LATERAL),
# zodat het peiljaar en de minimum-n per gemeente gelden. Waarden met n onder de
# drempel vallen eruit.
_SQL_REFERENTIE = """
    SELECT gm.code AS gemeente_code, rw.gebied_id, rw.indicator_uuid::text AS indicator_uuid,
           rw.waarde, rw.jaar
    FROM unnest(CAST(:pk_gemeenten AS varchar[])) AS gm(code)
    CROSS JOIN LATERAL public.zscore_referentie_waarden(
        CAST(:zs_gebiedstype_id AS uuid), gm.code, CAST(:zs_jaarlogica AS text),
        CAST(:zs_scenario_id AS varchar), CAST(:zs_indicator_uuids AS uuid[]),
        CAST(:zs_min_n AS integer)) rw
    WHERE (CAST(:pk_jaar AS integer) IS NULL OR rw.jaar = CAST(:pk_jaar AS integer))
      AND NOT EXISTS (
        SELECT 1 FROM public.gebied_data gd
        WHERE gd.gebied_id = rw.gebied_id AND gd.indicator_uuid = rw.indicator_uuid
          AND gd.jaar = rw.jaar AND COALESCE(gd.scenario_id, 'current') = CAST(:zs_scenario_id AS varchar)
          AND gd.n < CAST(:pk_drempel AS integer))
"""

# Doelwaarden met n onder de drempel (gebied, indicator, jaar)
_SQL_ONDERDRUKT = """
    SELECT gd.gebied_id, gd.indicator_uuid::text AS indicator_uuid, gd.jaar
    FROM public.gebied_data gd
    WHERE gd.gebied_id = ANY(CAST(:pk_gebied_ids AS varchar[]))
      AND (CAST(:pk_indicator_uuids AS uuid[]) IS NULL OR gd.indicator_uuid = ANY(CAST(:pk_indicator_uuids AS uuid[])))
      AND COALESCE(gd.scenario_id, 'current') = 'current'
      AND gd.n < CAST(:pk_drempel AS integer)
"""


def referentie_waarden(
    db,
    gebiedstype_id,
    gemeente_codes: Iterable[str | None],
    indicator_uuids: Iterable[str] | None = None,
    jaar: int | None = None,
    drempel: int | None = None,
) -> dict[tuple[str | None, str], list[float]]:
    """
    Referentiewaarden per (gemeentecode, indicator_uuid). Zonder jaar: jaarlogica
    'zelfde_jaar' (zoals de Z-score); met jaar: alle waarden van dat jaar.
    Zonder drempel: die van de instantie.
    """
    from sqlalchemy import text

    from omnitwin.services.zscore_referentie import referentie_params

    gemeenten = sorted({g for g in gemeente_codes}, key=lambda g: g or "")
    if not gemeenten:
        return {}
    params = referentie_params(gebiedstype_id, indicator_uuids=list(indicator_uuids) if indicator_uuids else None)
    if jaar is not None:
        params["zs_jaarlogica"] = "alle_jaren"  # filter op het gekozen jaar hieronder
    if drempel is None:
        drempel = ka.drempel(db)
    params.update({"pk_gemeenten": gemeenten, "pk_jaar": jaar, "pk_drempel": int(drempel)})
    uit: dict[tuple[str | None, str], list[float]] = {}
    for r in db.execute(text(_SQL_REFERENTIE), params):
        uit.setdefault((r.gemeente_code, r.indicator_uuid), []).append(float(r.waarde))
    return uit


def onderdrukte_waarden(
    db,
    gebied_ids: Iterable[str],
    indicator_uuids: Iterable[str] | None = None,
    drempel: int | None = None,
) -> set:
    """{(gebied_id, indicator_uuid, jaar)} met n onder de drempel (zonder drempel: die van de instantie)."""
    from sqlalchemy import text

    ids = list(gebied_ids)
    if not ids:
        return set()
    if drempel is None:
        drempel = ka.drempel(db)
    rows = db.execute(
        text(_SQL_ONDERDRUKT),
        {
            "pk_gebied_ids": ids,
            "pk_indicator_uuids": [str(u) for u in indicator_uuids] if indicator_uuids else None,
            "pk_drempel": int(drempel),
        },
    )
    return {(r.gebied_id, r.indicator_uuid, r.jaar) for r in rows}


def annoteer_boom(
    boom: dict,
    paren: dict[str, list[tuple[int | None, float]]],
    n_onderdrukt: dict[str, int],
    kleuren: list[str],
    geen_data_kleur: str,
    kleuren_neutraal: list[str] | None = None,
    klassen: int = KLASSEN,
) -> dict:
    """
    Zet de percentielklasse in een kompasboom (kopie). Indicator: klasse over zijn eigen
    paren (bij een selectie: over de gebieden), kleur = klassekleur. Onderdeel, thema,
    kwadrant en wortel: klasse over alle indicatorparen eronder (niet over de afgeronde
    klassen van de tussenniveaus); hun 'color' (bijv. de kwadrantkleur) blijft staan.
    Een neutraal kwadrant (Samenstelling) krijgt kleuren_neutraal en telt niet mee
    in de wortel.
    """
    standaard_kleuren = kleuren

    def annoteer(node: dict, kleuren: list[str] = standaard_kleuren):
        node = dict(node)
        neutraal = node.get("type") == "titel" and is_neutraal_kwadrant(node.get("name"))
        if neutraal:
            kleuren = kleuren_neutraal or standaard_kleuren
        if node.get("type") == "indicator" and node.get("uuid"):
            eigen = list(paren.get(node["uuid"], []))
            k = aggregeer(eigen, klassen)
            node["klasse"] = k
            node["klasse_kleur"] = kleuren[k - 1] if k else None
            node["color"] = node["klasse_kleur"] or geen_data_kleur
            node["klasse_status"] = "onderdrukt" if k is None and n_onderdrukt.get(node["uuid"]) else None
            return node, eigen
        onder: list = []
        if node.get("children"):
            kinderen = []
            for kind in node["children"]:
                kind_node, kind_paren = annoteer(kind, kleuren)
                kinderen.append(kind_node)
                onder.extend(kind_paren)
            node["children"] = kinderen
        k = aggregeer(onder, klassen)
        node["klasse"] = k
        node["klasse_kleur"] = kleuren[k - 1] if k else None
        return node, ([] if neutraal else onder)

    return annoteer(boom)[0]
