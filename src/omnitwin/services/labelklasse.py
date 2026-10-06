"""
Labels A-E per indicator en thema (#256): classificatie `label_ae`
===================================================================
Naast `zscore` en `percentiel_8` (services/percentielklasse.py). Kaart
(gebiedsmonitor_service, modus 'label') en Kompas (kompas_service) gebruiken deze functies.
Methodiek: docs/3-data-engineering/labels_methodiek.md.

Per indicator en gebied een label A (gunstigst) t/m E (ongunstigst):

- met drempels in tabel `indicator_labels` (data, migratie V034): het label waarvan
  ondergrens <= waarde < bovengrens (een lege grens is open). De drempels bepalen zelf de
  richting; polariteit speelt dan geen rol. Een waarde buiten alle drempels krijgt geen label.
- zonder drempels (voorlopig, aanname bij https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/222 A3):
  kwintielen binnen dezelfde referentiegroep als percentiel_8 (gebiedstype + gemeente,
  zelfde jaar, zonder waterbuurten, n < 10 telt niet mee), middenrang-percentiel,
  polariteit toegepast. 0-20% = E, ..., 80-100% = A.

Intern rekent de module met een labelscore 1..5 (5 = A, 1 = E), zodat de aggregatie
dezelfde is als bij percentiel_8: onderdeel, thema en kwadrant krijgen het gewogen
gemiddelde van de indicatorscores eronder (gewicht = aantal gebieden met data in de
referentiegroep), afgerond naar de dichtstbijzijnde score (x,5 naar boven), en dat label.
"""

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from omnitwin.services import percentielklasse as pk

CLASSIFICATIE = "label_ae"
LABELS = ("A", "B", "C", "D", "E")  # A = gunstigst
KLASSEN = len(LABELS)

BRON_KWINTIEL = "kwintiel"   # voorlopig: 20%-klassen binnen de referentiegroep
BRON_DREMPELS = "drempels"   # drempels uit indicator_labels

MELDING_VOORLOPIG = (
    "Voorlopige drempels (kwintielen): A = gunstigste 20% van de vergelijkbare gebieden, "
    "E = ongunstigste 20%. De drempels van de Klimaatmonitor volgen."
)

# Drempel: (label, ondergrens, bovengrens); None = open grens
Drempel = Tuple[str, Optional[float], Optional[float]]


def score_naar_label(score: Optional[int]) -> Optional[str]:
    """Labelscore 5..1 -> 'A'..'E'."""
    if score is None:
        return None
    return LABELS[KLASSEN - score]


def label_naar_score(label: str) -> int:
    return KLASSEN - LABELS.index(label.strip().upper())


def score_uit_percentiel(p: Optional[float], hoger_beter: bool = True) -> Optional[int]:
    """Kwintiel: floor(p x 5) + 1, begrensd op 1..5; bij 'lager is beter' eerst 1 - p."""
    if p is None:
        return None
    if not hoger_beter:
        p = 1.0 - p
    return max(1, min(KLASSEN, math.floor(p * KLASSEN) + 1))


def score_uit_drempels(waarde: Optional[float], drempels: Sequence[Drempel]) -> Optional[int]:
    """Score volgens absolute drempels: eerste label (A..E) met ondergrens <= waarde < bovengrens."""
    if waarde is None or not drempels:
        return None
    for label, onder, boven in sorted(drempels, key=lambda d: d[0]):
        if (onder is None or waarde >= onder) and (boven is None or waarde < boven):
            return label_naar_score(label)
    return None


def label_score(
    waarde: Optional[float],
    referentie: Sequence[float],
    hoger_beter: bool = True,
    drempels: Optional[Sequence[Drempel]] = None,
) -> Tuple[Optional[int], str]:
    """(score 1..5 of None, bron). Drempels gaan voor; anders kwintielen in de referentie."""
    if drempels:
        return score_uit_drempels(waarde, drempels), BRON_DREMPELS
    return score_uit_percentiel(pk.percentiel(waarde, referentie), hoger_beter), BRON_KWINTIEL


def label(
    waarde: Optional[float],
    referentie: Sequence[float],
    hoger_beter: bool = True,
    drempels: Optional[Sequence[Drempel]] = None,
) -> Optional[str]:
    return score_naar_label(label_score(waarde, referentie, hoger_beter, drempels)[0])


def aggregeer(scores_met_gewicht: Iterable[Tuple[Optional[int], Optional[float]]]) -> Optional[int]:
    """Themalabel: dezelfde regel als percentiel_8 (gewogen gemiddelde, afgerond)."""
    return pk.aggregeer(scores_met_gewicht, KLASSEN)


def palet(color_service=None) -> List[str]:
    """5 kleuren voor score 1..5 (E..A), kleurenblindvriendelijk uit color_schemas."""
    return pk.palet(color_service, klassen=KLASSEN)


def legenda(kleuren: List[str], voorlopig: bool = True) -> List[Dict[str, object]]:
    """A..E (gunstigst eerst), met kleur; 'klasse' = labelscore (5 = A)."""
    uit = []
    for lbl in LABELS:
        s = label_naar_score(lbl)
        tekst = f"label {lbl}"
        if lbl == LABELS[0]:
            tekst += " (gunstigst)"
        elif lbl == LABELS[-1]:
            tekst += " (ongunstigst)"
        if voorlopig:
            van, tot = (s - 1) * 100 // KLASSEN, s * 100 // KLASSEN
            tekst += f", kwintiel {van}–{tot}%"
        uit.append({"klasse": s, "label": lbl, "omschrijving": tekst, "kleur": kleuren[s - 1]})
    return uit


# ── Drempels uit de database ─────────────────────────────────────────────────

_SQL_DREMPELS = """
    SELECT indicator_uuid::text AS indicator_uuid, label, ondergrens, bovengrens
    FROM public.indicator_labels
    WHERE CAST(:il_uuids AS uuid[]) IS NULL OR indicator_uuid = ANY(CAST(:il_uuids AS uuid[]))
"""


def drempels_uit_db(db, indicator_uuids: Optional[Iterable[str]] = None) -> Dict[str, List[Drempel]]:
    """{indicator_uuid: [(label, ondergrens, bovengrens)]} uit indicator_labels."""
    from sqlalchemy import text

    uuids = [str(u) for u in indicator_uuids] if indicator_uuids is not None else None
    if uuids is not None and not uuids:
        return {}
    uit: Dict[str, List[Drempel]] = {}
    for r in db.execute(text(_SQL_DREMPELS), {"il_uuids": uuids}):
        uit.setdefault(r.indicator_uuid, []).append((
            r.label,
            float(r.ondergrens) if r.ondergrens is not None else None,
            float(r.bovengrens) if r.bovengrens is not None else None,
        ))
    return uit


def annoteer_boom(
    boom: Dict,
    paren: Dict[str, List[Tuple[Optional[int], float]]],
    n_onderdrukt: Dict[str, int],
    kleuren: List[str],
    geen_data_kleur: str,
    bron_per_indicator: Dict[str, str],
    kleuren_neutraal: Optional[List[str]] = None,
) -> Dict:
    """Labels in een kompasboom: de klasse-aggregatie van percentiel_8 met 5 scores, plus
    'label' op elke node en 'label_bron' (kwintiel/drempels) op de indicatoren."""
    boom = pk.annoteer_boom(boom, paren, n_onderdrukt, kleuren, geen_data_kleur, kleuren_neutraal, KLASSEN)

    def zet(node: Dict):
        node["label"] = score_naar_label(node.get("klasse"))
        if node.get("type") == "indicator" and node.get("uuid"):
            node["label_bron"] = bron_per_indicator.get(node["uuid"], BRON_KWINTIEL)
        for kind in node.get("children") or []:
            zet(kind)

    zet(boom)
    return boom
