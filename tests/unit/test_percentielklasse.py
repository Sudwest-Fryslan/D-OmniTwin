"""
Unit test: percentielklasse (8 x 12,5%) en klasse-aggregatie (#255).

Zonder database. De aanname (tot #222 antwoord geeft) staat in
docs/3-data-engineering/percentielklasse_methodiek.md.
"""
import pytest

from omnitwin.services import percentielklasse as pk

pytestmark = pytest.mark.unit


# ── Klassegrenzen ────────────────────────────────────────────────────────────

def test_acht_waarden_geven_acht_klassen():
    ref = [float(i) for i in range(1, 9)]
    assert [pk.klasse(v, ref) for v in ref] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_zestien_waarden_twee_per_klasse():
    ref = [float(i) for i in range(16)]
    klassen = [pk.klasse(v, ref) for v in ref]
    assert klassen == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8]


@pytest.mark.parametrize("p,verwacht", [
    (0.0, 1), (0.1249, 1), (0.125, 2), (0.4999, 4), (0.5, 5), (0.8749, 7), (0.875, 8), (0.9999, 8), (1.0, 8),
])
def test_grenzen_op_12_5_procent(p, verwacht):
    assert pk.klasse_uit_percentiel(p) == verwacht


def test_percentiel_is_middenrang():
    assert pk.percentiel(5.0, [1.0, 5.0, 9.0]) == pytest.approx(0.5)
    assert pk.percentiel(1.0, [1.0, 5.0, 9.0]) == pytest.approx(1 / 6)


def test_uitschieter_verschuift_de_klasse_niet():
    # rangorde, geen gemiddelde: een extreme waarde verandert de klasse van de rest niet
    ref = [float(i) for i in range(1, 9)]
    met_uitschieter = ref[:-1] + [1e6]
    assert [pk.klasse(v, ref) for v in ref[:-1]] == [pk.klasse(v, met_uitschieter) for v in ref[:-1]]


def test_zonder_referentie_geen_klasse():
    assert pk.klasse(3.0, []) is None
    assert pk.klasse(None, [1.0, 2.0]) is None


# ── Gelijke waarden ──────────────────────────────────────────────────────────

def test_gelijke_waarden_zelfde_klasse():
    ref = [1.0, 2.0, 2.0, 2.0, 2.0, 3.0, 4.0, 5.0]
    klassen = {pk.klasse(2.0, ref) for _ in range(4)}
    assert len(klassen) == 1
    assert pk.klasse(2.0, ref) == 4  # middenrang (1 + 0,5 x 4) / 8 = 0,375: klasse 4 (37,5-50%)


def test_allemaal_gelijk_middenklasse():
    ref = [7.0] * 12
    assert pk.klasse(7.0, ref) == 5  # percentiel 0,5


# ── Polariteit ───────────────────────────────────────────────────────────────

def test_lager_is_beter_spiegelt_de_klasse():
    ref = [float(i) for i in range(1, 9)]
    hoger = [pk.klasse(v, ref, hoger_beter=True) for v in ref]
    lager = [pk.klasse(v, ref, hoger_beter=False) for v in ref]
    assert lager == [9 - k for k in hoger]
    assert pk.klasse(1.0, ref, hoger_beter=False) == 8  # laagste waarde = gunstigst


@pytest.mark.parametrize("score_type,inverse,verwacht", [
    ("+/+", False, True), (None, None, True), ("positive_ascending", False, True),
    ("-/+", False, False),  # lager is beter, zoals rapporten en chat (SWF omkeren, #120)
    ("+/-", False, False), ("-/-", False, False), ("-=-", False, False), ("positive_descending", False, False),
    ("+/+", True, False),
])
def test_hoger_is_beter(score_type, inverse, verwacht):
    assert pk.hoger_is_beter(score_type, inverse) is verwacht


@pytest.mark.parametrize("score_type,inverse,kwadrant,verwacht", [
    ("+/+", False, "Welzijn", "hoger_is_beter"),
    ("+/-", False, "Welzijn", "lager_is_beter"),
    ("+/+", True, None, "lager_is_beter"),
    ("+/+", False, "Samenstelling", "neutraal"),
    ("+/-", False, "Samenstelling bevolking", "neutraal"),
])
def test_richting_voor_benchmarkkleur(score_type, inverse, kwadrant, verwacht):
    # #323: de Kompas-benchmark kleurt de afwijking op deze richting
    assert pk.richting(score_type, inverse, kwadrant) == verwacht


# ── Onderdrukking (n < 10) ───────────────────────────────────────────────────

@pytest.mark.parametrize("n,verwacht", [(None, False), (0, True), (9, True), (10, False), (250, False)])
def test_onderdrukt_onder_de_drempel(n, verwacht):
    assert pk.is_onderdrukt(n) is verwacht


def test_onderdrukte_waarde_telt_niet_mee_in_de_aggregatie():
    # een onderdrukte indicator levert geen paar (klasse None): het thema rust op de rest
    assert pk.aggregeer([(None, 100), (6, 100)]) == 6


# ── Aggregatie ───────────────────────────────────────────────────────────────

def test_aggregatie_voorbeeld_methodiek():
    # methodiek.md: scores 1, 3 en 4 op 88, 100 en 155 buurten geven 2,9 -> klasse 3
    assert pk.aggregeer([(1, 88), (3, 100), (4, 155)]) == 3


def test_aggregatie_weegt_naar_aantal_gebieden():
    assert pk.aggregeer([(1, 10), (8, 90)]) == 7  # 7,3
    assert pk.aggregeer([(1, 90), (8, 10)]) == 2  # 1,7


def test_afronden_half_naar_boven():
    assert pk.aggregeer([(1, 1), (2, 1)]) == 2   # 1,5
    assert pk.aggregeer([(4, 1), (5, 1)]) == 5   # 4,5


def test_aggregatie_zonder_data():
    assert pk.aggregeer([]) is None
    assert pk.aggregeer([(None, 10), (3, 0)]) is None


def test_annoteer_boom_aggregeert_over_alle_indicatoren_eronder():
    boom = {"name": "Root", "type": "root", "children": [
        {"name": "Kwadrant", "type": "titel", "color": "#123456", "children": [
            {"name": "Thema", "type": "thema", "children": [
                {"name": "Onderdeel A", "type": "onderdeel", "children": [
                    {"name": "i1", "type": "indicator", "uuid": "u1"},
                    {"name": "i2", "type": "indicator", "uuid": "u2"},
                ]},
                {"name": "Onderdeel B", "type": "onderdeel", "children": [
                    {"name": "i3", "type": "indicator", "uuid": "u3"},
                    {"name": "i4", "type": "indicator", "uuid": "u4"},
                ]},
            ]},
        ]},
    ]}
    kleuren = [f"#00000{k}" for k in range(1, 9)]
    # selectie van twee gebieden: i1 klasse 2 en 4 (gemiddeld 3), i3 onderdrukt in beide
    paren = {"u1": [(2, 10), (4, 10)], "u2": [(8, 30)], "u3": []}
    uit = pk.annoteer_boom(boom, paren, {"u3": 2}, kleuren, "#grijs")

    kwadrant = uit["children"][0]
    thema = kwadrant["children"][0]
    a, b = thema["children"]
    i1, i2 = a["children"]
    i3, i4 = b["children"]
    assert (i1["klasse"], i1["color"]) == (3, "#000003")
    assert i2["klasse"] == 8
    assert (i3["klasse"], i3["klasse_status"], i3["color"]) == (None, "onderdrukt", "#grijs")
    assert (i4["klasse"], i4["klasse_status"]) == (None, None)
    # onderdeel A: (2*10 + 4*10 + 8*30) / 50 = 6,0
    assert a["klasse"] == 6 and a["klasse_kleur"] == "#000006"
    assert b["klasse"] is None and b["klasse_kleur"] is None
    # thema en kwadrant: over de indicatorparen, niet over de afgeronde onderdelen
    assert thema["klasse"] == 6
    assert kwadrant["klasse"] == 6 and kwadrant["color"] == "#123456"  # kwadrantkleur blijft
    assert "klasse" not in boom["children"][0]  # origineel ongewijzigd


# ── Labels en palet ──────────────────────────────────────────────────────────

def test_labels():
    assert pk.klasse_label(1) == "klasse 1: 0–12,5% (ongunstigst)"
    assert pk.klasse_label(4) == "klasse 4: 37,5–50%"
    assert pk.klasse_label(8) == "klasse 8: 87,5–100% (gunstigst)"


def test_palet_kleurenblindvriendelijk_uit_fallback():
    kleuren = pk.palet()
    assert len(kleuren) == 8
    assert kleuren[0] == pk.PALET_FALLBACK["min"] and kleuren[-1] == pk.PALET_FALLBACK["max"]
    assert len(set(kleuren)) == 8
    legenda = pk.legenda(kleuren)
    assert [k["klasse"] for k in legenda] == list(range(1, 9))


def test_onbekende_classificatie_wordt_standaard():
    assert pk.normaliseer_classificatie("percentiel_8") == "percentiel_8"
    assert pk.normaliseer_classificatie("label") == "zscore"
    assert pk.normaliseer_classificatie(None) == "zscore"


def test_samenstelling_neutraal_palet_en_niet_in_de_wortel():
    boom = {"name": "Root", "type": "root", "children": [
        {"name": "Kwaliteit", "type": "titel", "children": [
            {"name": "i1", "type": "indicator", "uuid": "u1"}]},
        {"name": "Samenstelling", "type": "titel", "children": [
            {"name": "i2", "type": "indicator", "uuid": "u2"}]},
    ]}
    kleuren = [f"#00000{k}" for k in range(1, 9)]
    neutraal = [f"#0000a{k}" for k in range(1, 9)]
    uit = pk.annoteer_boom(boom, {"u1": [(2, 10)], "u2": [(8, 10)]}, {}, kleuren, "#grijs", neutraal)
    kwaliteit, samenstelling = uit["children"]
    assert kwaliteit["children"][0]["color"] == "#000002"
    assert samenstelling["klasse"] == 8 and samenstelling["klasse_kleur"] == "#0000a8"
    assert samenstelling["children"][0]["color"] == "#0000a8"
    assert uit["klasse"] == 2  # alleen Kwaliteit telt mee in de wortel
