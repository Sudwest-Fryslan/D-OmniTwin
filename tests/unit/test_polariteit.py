"""
Unit test: één polariteitscodering (#120).

Kaart (kleurschaal), Kompas, percentielklassen, rapporten en chat leiden de richting af
met dezelfde regel (omnitwin.polariteit.uit_oud). Voorheen las de kaart '-/+' als
"hoger is beter" en de rapporten als "lager is beter".
"""

from pathlib import Path

import pytest

from omnitwin import polariteit as pol
from omnitwin.services import chat_datavraag as dv
from omnitwin.services import percentielklasse as pk
from omnitwin.services.kompas_service import KompasScoringService
from omnitwin.services.report_service import ReportDataService

pytestmark = pytest.mark.unit

V046 = Path(__file__).resolve().parents[2] / "db" / "migraties" / "V046__polariteit.sql"

# (score_type, interpretatie_logica) -> polariteit
GEVALLEN = [
    ("+/+", "pos_is_pos", pol.HOGER_IS_BETER),
    ("+=+", None, pol.HOGER_IS_BETER),
    ("+/-", "-/+", pol.LAGER_IS_BETER),
    ("-/+", None, pol.LAGER_IS_BETER),  # SWF-monitor: omkeren (#342)
    ("-/-", None, pol.LAGER_IS_BETER),
    ("-=-", None, pol.LAGER_IS_BETER),  # energielabel e.d.: lager getal = beter
    ("+/+", "neutraal", pol.NEUTRAAL),
    ("+/+", "N/A", pol.NEUTRAAL),
    (None, "-/+", pol.LAGER_IS_BETER),
    (None, None, pol.HOGER_IS_BETER),
    ("", "pos_is_pos", pol.HOGER_IS_BETER),
    ("positive_ascending", None, pol.HOGER_IS_BETER),
    ("positive_descending", None, pol.LAGER_IS_BETER),
    ("lager_is_beter", None, pol.LAGER_IS_BETER),
]


@pytest.mark.parametrize("score_type,logica,verwacht", GEVALLEN)
def test_uit_oud(score_type, logica, verwacht):
    assert pol.uit_oud(score_type, logica) == verwacht


@pytest.mark.parametrize("score_type", ["+/+", "+/-", "-/+", "-/-", "-=-", "+=+", None])
def test_alle_plekken_zelfde_richting(score_type):
    """Kaart/percentiel, Kompas-kleur, rapport en chat zeggen hetzelfde over één score_type."""
    lager = pol.uit_oud(score_type) == pol.LAGER_IS_BETER
    assert pk.hoger_is_beter(score_type) is not lager
    assert pol.lager_is_beter(score_type) is lager
    assert (dv.richting(score_type, None) == pol.LAGER_IS_BETER) is lager

    impact = ReportDataService._determine_impact(None, 1.5, score_type)
    assert impact == ("bovengemiddeld negatief" if lager else "bovengemiddeld positief")

    drempels = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    kompas = KompasScoringService()
    hoog = kompas.get_color_for_value(100.0, score_type=score_type, thresholds=drempels)
    laag = kompas.get_color_for_value(0.0, score_type=score_type, thresholds=drempels)
    assert (hoog, laag) == (("#D73027", "#1A9850") if lager else ("#1A9850", "#D73027"))


def test_score_type_van():
    assert pol.score_type_van(pol.LAGER_IS_BETER) == "+/-"
    assert pol.score_type_van(pol.HOGER_IS_BETER) == "+/+"
    assert pol.score_type_van(pol.NEUTRAAL) == "+/+"


def test_migratie_heeft_codelijst_en_dezelfde_regel():
    """V046: check-constraint met precies de codelijst, en de SQL-regel noemt dezelfde codes."""
    sql = V046.read_text(encoding="utf-8")
    assert "CHECK (polariteit IN ('hoger_is_beter', 'lager_is_beter', 'neutraal'))" in sql
    assert "('neutraal', 'n/a')" in sql and "('+/+', '+=+')" in sql
    assert "public." not in sql  # schema volgt het search_path (#137)
    assert set(pol.POLARITEITEN) == {"hoger_is_beter", "lager_is_beter", "neutraal"}
