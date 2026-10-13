"""
Polariteit van een indicator: is hoger beter? (#120)

Eén codering: ``hoger_is_beter`` | ``lager_is_beter`` | ``neutraal`` (kolom
``indicatoren.polariteit``, migratie V046). De oude kolommen ``score_type`` en
``interpretatie_logica`` volgen die kolom via een trigger; laders die ze nog schrijven,
zetten daarmee de polariteit.

``uit_oud`` is dezelfde regel als de SQL-functie ``polariteit_uit_score_type``: alle
code die nog een score_type (of een Kompas-scoringregel) krijgt, leidt de richting
hiermee af, zodat kaart, Kompas, rapporten en chat hetzelfde zeggen.
"""

from __future__ import annotations

HOGER_IS_BETER = "hoger_is_beter"
LAGER_IS_BETER = "lager_is_beter"
NEUTRAAL = "neutraal"
POLARITEITEN = (HOGER_IS_BETER, LAGER_IS_BETER, NEUTRAAL)

# Kompas-scoringregel (kompas_indicator_scoring_regels.score_type): per profiel
_KOMPAS = {"positive_ascending": HOGER_IS_BETER, "positive_descending": LAGER_IS_BETER}


def uit_oud(score_type: str | None, interpretatie_logica: str | None = None) -> str:
    """Oude codering naar polariteit. Neutraal (logica 'neutraal'/'N/A') gaat voor; dan
    '+/+' (of '+=+') hoger is beter, elke andere score_type lager is beter."""
    logica = (interpretatie_logica or "").strip()
    if logica.lower() in ("neutraal", "n/a"):
        return NEUTRAAL
    st = (score_type or "").strip()
    if st in POLARITEITEN:
        return st
    if st in _KOMPAS:
        return _KOMPAS[st]
    if not st:
        return LAGER_IS_BETER if logica == "-/+" else HOGER_IS_BETER
    return HOGER_IS_BETER if st in ("+/+", "+=+") else LAGER_IS_BETER


def score_type_van(polariteit: str) -> str:
    """De afgeleide score_type (zoals de trigger hem zet)."""
    return "+/-" if polariteit == LAGER_IS_BETER else "+/+"


def lager_is_beter(score_type: str | None, inverse: bool | None = False) -> bool:
    """Kleur omkeren? Ja bij lager-is-beter, of als een Kompas-regel ``inverse`` zet."""
    return bool(inverse) or uit_oud(score_type) == LAGER_IS_BETER
