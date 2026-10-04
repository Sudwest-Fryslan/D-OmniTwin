"""
Unit test: labels A-E per indicator en thema (#256), classificatie label_ae.

Zonder database. Aanname tot de drempels van SWF zijn vastgesteld (#222, A3): kwintielen
binnen de referentiegroep; drempels in indicator_labels gaan voor.
Methodiek: docs/3-data-engineering/labels_methodiek.md.
"""
import json
from pathlib import Path

import pytest

from omnitwin.services import labelklasse as lk
from omnitwin.services import percentielklasse as pk

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


# ── Kwintielgrenzen ──────────────────────────────────────────────────────────

def test_vijf_waarden_vijf_labels():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert [lk.label(v, ref) for v in ref] == ["E", "D", "C", "B", "A"]


def test_tien_waarden_twee_per_label():
    ref = [float(i) for i in range(10)]
    assert [lk.label(v, ref) for v in ref] == ["E", "E", "D", "D", "C", "C", "B", "B", "A", "A"]


@pytest.mark.parametrize("p,verwacht", [
    (0.0, 1), (0.1999, 1), (0.2, 2), (0.3999, 2), (0.4, 3), (0.5, 3), (0.6, 4), (0.7999, 4), (0.8, 5), (1.0, 5),
])
def test_grenzen_op_20_procent(p, verwacht):
    assert lk.score_uit_percentiel(p) == verwacht


def test_score_en_label():
    assert [lk.score_naar_label(s) for s in (5, 4, 3, 2, 1)] == ["A", "B", "C", "D", "E"]
    assert lk.score_naar_label(None) is None
    assert [lk.label_naar_score(x) for x in "ABCDE"] == [5, 4, 3, 2, 1]
    assert lk.label_naar_score(" b ") == 4


def test_zonder_referentie_geen_label():
    assert lk.label(3.0, []) is None
    assert lk.label(None, [1.0, 2.0]) is None


# ── Polariteit ───────────────────────────────────────────────────────────────

def test_lager_is_beter_spiegelt_het_label():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert [lk.label(v, ref, hoger_beter=False) for v in ref] == ["A", "B", "C", "D", "E"]


def test_polariteit_uit_score_type():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    # Stedelijk hitte-eiland effect: score_type +/-, laagste waarde = A
    assert lk.label(1.0, ref, pk.hoger_is_beter("+/-")) == "A"
    assert lk.label(1.0, ref, pk.hoger_is_beter("+/+")) == "E"


# ── Gelijke waarden ──────────────────────────────────────────────────────────

def test_gelijke_waarden_zelfde_label():
    ref = [1.0, 2.0, 2.0, 2.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    # middenrang van 2,0: (1 + 0,5 x 4) / 10 = 0,3 -> D voor alle vier
    assert lk.label(2.0, ref) == "D"


def test_allemaal_gelijk_middenlabel():
    assert lk.label(7.0, [7.0] * 12) == "C"  # percentiel 0,5


# ── Overschreven drempels (indicator_labels) ─────────────────────────────────

# Lager is beter, absolute klassen: A < 5, B 5-10, C 10-15, D 15-20, E >= 25 (gat 20-25)
DREMPELS = [("E", 25.0, None), ("A", None, 5.0), ("B", 5.0, 10.0), ("C", 10.0, 15.0), ("D", 15.0, 20.0)]


@pytest.mark.parametrize("waarde,verwacht", [
    (0.0, "A"), (4.99, "A"), (5.0, "B"), (9.9, "B"), (10.0, "C"), (19.99, "D"), (25.0, "E"), (1e6, "E"),
])
def test_drempels_gaan_voor(waarde, verwacht):
    ref = [1.0, 2.0, 3.0]  # kwintielen zouden iets anders geven
    score, bron = lk.label_score(waarde, ref, hoger_beter=True, drempels=DREMPELS)
    assert lk.score_naar_label(score) == verwacht
    assert bron == lk.BRON_DREMPELS


def test_waarde_in_een_gat_tussen_drempels_krijgt_geen_label():
    assert lk.label_score(22.0, [], drempels=DREMPELS) == (None, lk.BRON_DREMPELS)


def test_drempels_negeren_polariteit_en_werken_zonder_referentie():
    assert lk.label(3.0, [], hoger_beter=False, drempels=DREMPELS) == "A"
    assert lk.label(3.0, [], hoger_beter=True, drempels=DREMPELS) == "A"


def test_middenband_als_gunstigst():
    # gevoelstemperatuur: 'comfortabel' is A, te koud en te warm ongunstiger
    drempels = [("A", 18.0, 24.0), ("B", 24.0, 28.0), ("C", 28.0, 32.0), ("D", 32.0, None), ("E", None, 18.0)]
    assert [lk.label(v, [], drempels=drempels) for v in (10.0, 20.0, 26.0, 30.0, 40.0)] == ["E", "A", "B", "C", "D"]


def test_bij_overlap_wint_het_gunstigste_label():
    assert lk.label(5.0, [], drempels=[("B", 0.0, 10.0), ("A", 4.0, 6.0)]) == "A"


def test_zonder_drempels_kwintiel():
    assert lk.label_score(5.0, [1.0, 5.0], drempels=None)[1] == lk.BRON_KWINTIEL
    assert lk.label_score(5.0, [1.0, 5.0], drempels=[])[1] == lk.BRON_KWINTIEL


# ── Themalabel (aggregatie) ──────────────────────────────────────────────────

def test_themalabel_gewogen_gemiddelde():
    # A (5) op 10 gebieden, E (1) op 30: (50 + 30) / 40 = 2,0 -> D
    assert lk.score_naar_label(lk.aggregeer([(5, 10), (1, 30)])) == "D"
    # x,5 naar boven: (4 + 3) / 2 = 3,5 -> 4 = B
    assert lk.score_naar_label(lk.aggregeer([(4, 1), (3, 1)])) == "B"
    assert lk.aggregeer([(None, 10)]) is None


def test_annoteer_boom_labels_en_bron():
    boom = {"name": "Klimaat", "type": "root", "children": [
        {"name": "Klimaat", "type": "titel", "children": [
            {"name": "Hittestress", "type": "thema", "children": [
                {"name": "Hitte", "type": "onderdeel", "children": [
                    {"name": "i1", "type": "indicator", "uuid": "u1"},
                    {"name": "i2", "type": "indicator", "uuid": "u2"},
                    {"name": "i3", "type": "indicator", "uuid": "u3"},
                ]},
            ]},
        ]},
    ]}
    kleuren = [f"#00000{k}" for k in range(1, 6)]
    paren = {"u1": [(5, 10)], "u2": [(2, 10)]}  # A en D; u3 onderdrukt
    uit = lk.annoteer_boom(boom, paren, {"u3": 1}, kleuren, "#grijs",
                           {"u1": lk.BRON_DREMPELS, "u2": lk.BRON_KWINTIEL})
    thema = uit["children"][0]["children"][0]
    i1, i2, i3 = thema["children"][0]["children"]
    assert (i1["label"], i1["klasse"], i1["color"], i1["label_bron"]) == ("A", 5, "#000005", "drempels")
    assert (i2["label"], i2["label_bron"]) == ("D", "kwintiel")
    assert (i3["label"], i3["klasse_status"], i3["color"]) == (None, "onderdrukt", "#grijs")
    assert thema["label"] == "B" and thema["klasse"] == 4   # (5 + 2) / 2 = 3,5 -> 4
    assert uit["label"] == "B"
    assert "label_bron" not in thema


# ── Palet en legenda ─────────────────────────────────────────────────────────

def test_palet_vijf_kleuren_kleurenblindvriendelijk():
    kleuren = lk.palet()
    assert len(kleuren) == 5 and len(set(kleuren)) == 5
    # E = rood (min), A = blauw (max): hetzelfde palet als percentiel_8
    assert kleuren[0] == pk.PALET_FALLBACK["min"] and kleuren[-1] == pk.PALET_FALLBACK["max"]


def test_legenda_a_tot_e_met_melding_voorlopig():
    kleuren = lk.palet()
    leg = lk.legenda(kleuren)
    assert [k["label"] for k in leg] == ["A", "B", "C", "D", "E"]
    assert [k["klasse"] for k in leg] == [5, 4, 3, 2, 1]
    assert leg[0]["kleur"] == kleuren[4] and leg[-1]["kleur"] == kleuren[0]
    assert leg[0]["omschrijving"] == "label A (gunstigst), kwintiel 80–100%"
    assert leg[-1]["omschrijving"] == "label E (ongunstigst), kwintiel 0–20%"
    assert "kwintiel" not in lk.legenda(kleuren, voorlopig=False)[0]["omschrijving"]
    assert "Voorlopige drempels (kwintielen)" in lk.MELDING_VOORLOPIG


def test_classificatie_label_ae_bekend():
    assert "label_ae" in pk.CLASSIFICATIES
    assert pk.normaliseer_classificatie("label_ae") == "label_ae"


# ── Stuurdata: Klimaat Kompas ────────────────────────────────────────────────

def test_kompasprofiel_klimaat_stuurdata():
    profiel = json.loads((ROOT / "db" / "stuurdata" / "kompasprofiel_klimaat.json").read_text(encoding="utf-8"))
    assert profiel["classificatie"] in pk.CLASSIFICATIES
    definities = (ROOT / "db" / "stuurdata" / "indicatoren.csv").read_text(encoding="utf-8")
    uuids = [i["indicator_uuid"] for i in profiel["indicatoren"]]
    assert len(uuids) == len(set(uuids))
    for i in profiel["indicatoren"]:
        assert {"kwadrant", "thema", "indicator_uuid"} <= set(i)
        assert i["indicator_uuid"] in definities, f"{i['indicator_naam']} ontbreekt in de definities"
    assert {i["thema"] for i in profiel["indicatoren"]} == {"Hittestress", "Hemelwateroverlast", "Droogte"}


def test_migratie_staat_label_ae_toe():
    sql = (ROOT / "db" / "migraties" / "V034__labels_ae.sql").read_text(encoding="utf-8")
    assert "'label_ae'" in sql and "indicator_labels" in sql
