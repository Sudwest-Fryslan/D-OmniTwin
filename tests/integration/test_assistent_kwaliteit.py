"""
Kwaliteit van de D-Omni Assistent (#233), tegen een draaiende stack met sample-data.

- de evaluatieset (tests/data/assistent_evaluatie.json): precision@k, recall@k, MRR en routering
  moeten boven de drempels uit dat bestand liggen;
- de controles uit usecases/assistent-kwaliteit/usecase.json: api (de uuid staat bovenaan) en
  chat (het antwoord bevat de teksten uit 'bevat'), zonder taalmodel (context geen_llm).

    OMNITWIN_BASE_URL=http://localhost:8105 pytest -m integration tests/integration/test_assistent_kwaliteit.py
"""
import json
import os
from pathlib import Path

import pytest
import requests

from omnitwin import assistent_evaluatie as ev

pytestmark = pytest.mark.integration

BASE_URL = (os.environ.get("OMNITWIN_BASE_URL") or "http://localhost").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "usecases" / "assistent-kwaliteit" / "usecase.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def uitslag():
    testset = ev.laad_testset()
    zoek, chat = ev.http_zoek_en_chat(BASE_URL, timeout=300)
    resultaten = ev.evalueer(testset, zoek, chat)
    return testset, resultaten, ev.scoor(resultaten, testset.get("k", 3))


def test_evaluatie_boven_de_drempels(uitslag):
    testset, resultaten, scores = uitslag
    print(f"\nEvaluatie: {json.dumps({k: round(v, 3) for k, v in scores.items()})}")
    missers = [r["vraag"] for r in resultaten if ev.reciprocal_rank(r["gevonden"], r["relevant"]) == 0]
    assert ev.onder_drempel(scores, testset["drempels"]) == [], f"geen relevante indicator bij: {missers}"


def test_datavragen_gaan_naar_de_datavraagroute(uitslag):
    _, resultaten, _ = uitslag
    fout = [(r["vraag"], r.get("intent")) for r in resultaten if r["gerouteerd"] is False]
    assert len(fout) <= 1, f"niet als datavraag beantwoord: {fout}"


def _id(c):
    return f"{c['type']}:{c.get('pad') or c.get('vraag') or c.get('stap')}"[:80]


@pytest.mark.parametrize("controle", [c for c in MANIFEST["controles"] if c["type"] == "api"], ids=_id)
def test_api_controle(controle):
    r = requests.get(f"{BASE_URL}{controle['pad']}", timeout=120)
    assert r.status_code == controle.get("status", 200), r.text[:300]
    data = r.json()
    assert len(data) >= controle.get("minimaal_aantal", 0)
    if controle.get("uuid"):
        assert data[0]["uuid"] == controle["uuid"], [d["naam"] for d in data]
        assert data[0]["relevantie"] == "sterk"


@pytest.mark.parametrize("controle", [c for c in MANIFEST["controles"] if c["type"] == "chat"], ids=_id)
def test_chat_controle(controle):
    r = requests.post(f"{BASE_URL}/api/chat", json={"vraag": controle["vraag"], "context": {"geen_llm": True}},
                      timeout=300)
    assert r.status_code == 200, r.text[:300]
    antwoord = r.json()
    tekst = antwoord["narrative"] + " " + " ".join(i["naam"] for i in antwoord["indicatoren"])
    for deel in controle["bevat"]:
        assert deel in tekst, f"{deel!r} ontbreekt in: {tekst}"
    if controle.get("uuid"):
        assert antwoord["indicatoren"][0]["uuid"] == controle["uuid"]


def test_vraag_van_eduard_met_geselecteerde_buurt():
    """'hoeveel % is bejaard bij mij in de buurt?' met Bolsward-Zuidoost geselecteerd (#233)."""
    r = requests.post(f"{BASE_URL}/api/chat", json={
        "vraag": "hoeveel % is bejaard bij mij in de buurt?",
        "context": {"huidig_gebied_id": "BU19000002", "geen_llm": True}}, timeout=300)
    assert r.status_code == 200
    a = r.json()
    assert a["intent"] == "DATAVRAAG"
    assert [i["naam"] for i in a["indicatoren"]] == ["65+ jaar (%)"]
    assert all(i["relevantie_label"] in ("sterk", "matig") for i in a["indicatoren"])
    eigen = [g for g in a["gegevens"] if g["gebied_id"] == "BU19000002"]
    assert eigen and eigen[0]["jaar"] and a["bronnen"][0]["bron"].startswith("CBS")
    assert a["narrative"].split("): ", 1)[1].startswith("Bolsward-Zuidoost: ")


def test_zoeken_toont_geen_ruis():
    """Niets dat past: liever niets dan acht matige resultaten."""
    r = requests.get(f"{BASE_URL}/api/ai/kompas/search", params={"q": "windmolens op zee", "limit": 10}, timeout=120)
    assert r.status_code == 200
    assert len(r.json()) <= 3
