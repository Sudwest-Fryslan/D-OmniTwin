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
                         "gegevens": [{"gebied_id": g}], "narrative": "x"}
    res = ev.evalueer(testset, lambda v: ["a"], chat)
    assert [r["gerouteerd"] for r in res] == [None, True]


def test_testset_is_volledig():
    t = ev.laad_testset()
    vragen = t["vragen"]
    assert len(vragen) >= 40
    assert {"precision_at_k", "recall_at_k", "mrr", "routering"} <= set(t["drempels"])
    assert len({v["vraag"] for v in vragen}) == len(vragen), "dubbele vraag"
    assert sum(1 for v in vragen if v["type"] == "datavraag") >= 5
    assert sum(1 for v in vragen if v.get("holdout")) >= 10
    for v in vragen:
        assert v["type"] in ("zoek", "datavraag") and v["relevant"], v
        assert all(UUID.match(u) for u in v["relevant"]), v
