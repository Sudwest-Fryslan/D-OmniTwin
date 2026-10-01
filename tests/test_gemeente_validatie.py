"""
Unit tests voor de validatie van SELECTEER_GEMEENTE-acties uit de chat (#140).
Pure Python: geen database, geen taalmodel.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omnitwin.services.gemeente_validatie import naam_uit_label, normaliseer, valideer_gemeente_actie

pytestmark = pytest.mark.unit

GEMEENTEN = {
    "0080": "Leeuwarden",
    "1900": "Súdwest-Fryslân",
    "0014": "Groningen",
    "1952": "Midden-Groningen",
    "0072": "Harlingen",
    "0093": "Terschelling",
}

GEBIEDEN = [
    ("Bolsward-Zuidoost", "1900"),
    ("Bolsward-Noord", "1900"),
    ("Bolswardervaart", "0080"),  # fictief: begint met 'Bolsward', maar is een andere plaats
    ("Workum", "1900"),
    ("Oosterend", "1900"),
    ("Oosterend", "0093"),  # zelfde naam in een andere gemeente
]


def gebieden_voor(naam):
    return [(n, c) for n, c in GEBIEDEN if normaliseer(n).startswith(normaliseer(naam))]


def actie(label, code):
    return {"type": "SELECTEER_GEMEENTE", "label": label, "gemeente_code": code}


def valideer(a):
    return valideer_gemeente_actie(a, GEMEENTEN, gebieden_voor)


def test_geldige_actie_blijft_ongewijzigd():
    a = actie("📍 Gemeente: Leeuwarden", "0080")
    assert valideer(a) == a


def test_geldig_zonder_accenten_in_label():
    a = actie("📍 Gemeente: Sudwest-Fryslan", "1900")
    assert valideer(a) == a


def test_bolsward_met_leeuwarden_code_wordt_sudwest_fryslan():
    """De bug uit #140: 'Gemeente: Bolsward' met 0080 → 1900."""
    a = valideer(actie("📍 Gemeente: Bolsward", "0080"))
    assert a["gemeente_code"] == "1900"
    assert a["label"] == "📍 Gemeente: Súdwest-Fryslân"


def test_woonplaats_zonder_code_wordt_herleid():
    a = valideer(actie("📍 Workum", None))
    assert a["gemeente_code"] == "1900"


def test_gemeentenaam_met_verkeerde_code_krijgt_juiste_code():
    a = valideer(actie("📍 Leeuwarden", "1900"))
    assert a["gemeente_code"] == "0080"


def test_deelnaam_van_andere_gemeente_telt_niet():
    """'Midden-Groningen' bevat 'Groningen', maar is een andere gemeente."""
    a = valideer(actie("📍 Gemeente: Midden-Groningen", "0014"))
    assert a["gemeente_code"] == "1952"


def test_onbekende_code_en_onbekende_plaats_vervalt():
    assert valideer(actie("📍 Gemeente: Atlantis", "9999")) is None


def test_bestaande_code_maar_label_noemt_andere_plaats_vervalt():
    assert valideer(actie("📍 Gemeente: Atlantis", "0080")) is None


def test_plaatsnaam_in_meerdere_gemeenten_vervalt():
    assert valideer(actie("📍 Oosterend", "0080")) is None


def test_lege_label_vervalt():
    assert valideer(actie("", "1234")) is None


def test_andere_actietypes_ongewijzigd():
    a = {"type": "OPEN_KOMPAS", "label": "🧭 Open Kompas"}
    assert valideer(a) is a


def test_naam_uit_label():
    assert naam_uit_label("📍 Gemeente: Bolsward") == "Bolsward"
    assert naam_uit_label("📍 Súdwest-Fryslân") == "Súdwest-Fryslân"
    assert naam_uit_label("Gemeente Harlingen") == "Harlingen"
