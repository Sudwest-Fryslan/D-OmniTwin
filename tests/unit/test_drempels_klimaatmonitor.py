"""Drempels labels A–E van de Klimaatmonitor als data (#256, #222 A3)."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
BESTAND = ROOT / "db" / "stuurdata" / "indicator_labels_klimaatmonitor_swf.json"


def test_drempelbestand_is_geldig():
    data = json.loads(BESTAND.read_text(encoding="utf-8"))
    assert data["bron"] and len(data["indicatoren"]) == 9
    uuids = [i["indicator_uuid"] for i in data["indicatoren"]]
    assert len(set(uuids)) == len(uuids)
    for ind in data["indicatoren"]:
        labels = [lab[0] for lab in ind["labels"]]
        assert labels == ["A", "B", "C", "D", "E"], ind["indicator_naam"]
        for _, onder, boven in ind["labels"]:
            assert onder is None or boven is None or onder < boven, ind["indicator_naam"]


def test_banden_overlappen_niet():
    data = json.loads(BESTAND.read_text(encoding="utf-8"))
    for ind in data["indicatoren"]:
        banden = sorted(((o if o is not None else float("-inf")), (b if b is not None else float("inf")))
                        for _, o, b in ind["labels"])
        for (o1, b1), (o2, b2) in zip(banden, banden[1:]):
            assert b1 <= o2, f"{ind['indicator_naam']}: banden overlappen"
