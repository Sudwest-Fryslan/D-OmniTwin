"""
Unit tests voor de evaluatie van de D-Omni Assistent (#233): de maten en de testset zelf.
De evaluatie tegen een draaiende stack staat in tests/integration/test_assistent_kwaliteit.py.
"""
import re

import pytest

from omnitwin import assistent_evaluatie as ev

pytestmark = pytest.mark.unit

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_precision_telt_alleen_wat_getoond_is():
    assert ev.precision_at_k(["a", "x"], ["a"], 3) == 0.5      # 2 getoond, 1 goed
    assert ev.precision_at_k(["a", "x", "y", "b"], ["a", "b"], 3) == pytest.approx(1 / 3)
    assert ev.precision_at_k([], ["a"], 3) == 0.0


def test_recall_met_noemer_min_k_en_relevant():
    assert ev.recall_at_k(["a"], ["a"], 3) == 1.0
    assert ev.recall_at_k(["a", "b", "c"], ["a", "b", "c", "d", "e"], 3) == 1.0  # meer relevant dan k
    assert ev.recall_at_k(["x", "a"], ["a", "b"], 3) == 0.5


def test_reciprocal_rank():
    assert ev.reciprocal_rank(["x", "a"], ["a"]) == 0.5
    assert ev.reciprocal_rank(["x"], ["a"]) == 0.0


def test_scoor_en_drempel():
    res = [{"type": "zoek", "relevant": ["a"], "gevonden": ["a"]},
           {"type": "datavraag", "relevant": ["b"], "gevonden": ["x", "b"], "gerouteerd": False}]
    s = ev.scoor(res, 3)
    assert s["mrr"] == 0.75 and s["routering"] == 0.0
    assert ev.onder_drempel(s, {"mrr": 0.8, "precision_at_k": 0.5}) == ["mrr 0.750 < 0.8"]


def test_evalueer_routeert_datavragen_naar_de_chat():
    testset = {"gebied": "BU19000002", "vragen": [
        {"vraag": "ouderen", "type": "zoek", "relevant": ["a"]},
        {"vraag": "hoeveel ouderen hier", "type": "datavraag", "relevant": ["a"]}]}
    chat = lambda v, g: {"intent": "DATAVRAAG", "indicatoren": [{"uuid": "a"}],  # noqa: E731
                         "gegevens": [{"gebied_id": x} for x in g], "narrative": "x"}
    res = ev.evalueer(testset, lambda v: ["a"], chat)
    assert [r["gerouteerd"] for r in res] == [None, True]


def test_gerouteerd_mijn_buurt_selectie_en_aanname():
    """#233: bij 'mijn buurt' met een (multi-)selectie zegt het antwoord van welke buurt(en) het uitgaat."""
    v = {"vraag": "hoeveel % is bejaard bij mij in de buurt?", "type": "datavraag", "mijn_buurt": True}
    namen = {"B1": "Noord", "B2": "Zuid"}
    goed = {"intent": "DATAVRAAG", "gegevens": [{"gebied_id": "B1"}, {"gebied_id": "B2"}],
            "aanname": "Ik ga uit van Noord en Zuid (geselecteerd op de kaart)."}
    assert ev.gerouteerd(v, goed, ["B1", "B2"], namen)
    assert not ev.gerouteerd(v, {**goed, "aanname": None}, ["B1", "B2"], namen)
    assert not ev.gerouteerd(v, {**goed, "gegevens": [{"gebied_id": "B1"}]}, ["B1", "B2"], namen)


def test_gerouteerd_zonder_selectie_vraagt_welke_buurt():
    v = {"vraag": "hoeveel % is bejaard bij mij in de buurt?", "type": "datavraag", "route": "vraag_buurt"}
    assert ev.gerouteerd(v, {"intent": "DATAVRAAG", "narrative": "Welke buurt is jouw buurt?"}, [])
    assert not ev.gerouteerd(v, {"intent": "DATAVRAAG", "narrative": "65+: 20%", "gegevens": [{"gebied_id": "X"}]}, [])


def test_drempels_apart_voor_afgestemd_en_holdout():
    """#336: de holdout haalt niet dezelfde drempel, maar een eigen, lagere (alleen tegen terugval)."""
    testset = {"k": 3, "drempels": {"recall_at_k": 0.8}, "drempels_holdout": {"recall_at_k": 0.5}}
    goed = {"type": "zoek", "relevant": ["a"], "gevonden": ["a"]}
    mis = {"type": "zoek", "relevant": ["a"], "gevonden": ["b"]}
    assert ev.drempelfouten([goed, {**goed, "holdout": True}, {**mis, "holdout": True}], testset) == []
    assert ev.drempelfouten([goed, mis], testset) == ["afgestemd: recall_at_k 0.500 < 0.8"]
    assert ev.drempelfouten([goed, {**mis, "holdout": True}], testset) == ["holdout: recall_at_k 0.000 < 0.5"]


def test_testset_is_volledig():
    t = ev.laad_testset()
    vragen = t["vragen"]
    assert len(vragen) >= 40
    assert {"precision_at_k", "recall_at_k", "mrr", "routering"} <= set(t["drempels"])
    assert {"precision_at_k", "recall_at_k", "mrr", "routering"} <= set(t["drempels_holdout"])
    sleutels = [(v["vraag"], tuple(v.get("selectie", ["standaard"]))) for v in vragen]
    assert len(set(sleutels)) == len(vragen), "dubbele vraag (zelfde vraag en selectie)"
    assert sum(1 for v in vragen if v["type"] == "datavraag") >= 5
    assert sum(1 for v in vragen if v.get("holdout")) >= 10
    for v in vragen:
        assert v["type"] in ("zoek", "datavraag") and v["relevant"], v
        assert all(UUID.match(u) for u in v["relevant"]), v
