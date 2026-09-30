"""
LLM-beloftes tegen een draaiende stack met een echt model (#88, ADR 0001).

Niet in de CI (geen GPU, geen model). Handmatig, per api_type:

    LLM_TEST=1 LLM_TEST_BASE_URL=http://localhost pytest -m llm tests/integration/test_llm.py

Omgeving:
    LLM_TEST=1                   verplicht, anders worden de tests overgeslagen
    LLM_TEST_BASE_URL            basis-URL van de app (standaard http://localhost)
    LLM_TEST_GEBIED              buurt voor het rapport (standaard BU19000400, sample-data)
    LLM_TEST_MAX_WORDS           max. woorden chat-narrative (standaard 120; prompt vraagt ≤ 80)
    LLM_TEST_MAX_WORDS_RAPPORT   max. woorden rapportsamenvatting (standaard 200; prompt vraagt ≤ 150)
    LLM_TEST_TIMEOUT             seconden per verzoek (standaard 900; lokaal model is traag)

Welke LLM-koppeling getest wordt, bepaalt llm_config in de database (api_type, api_url,
model_name); zie README, 'AI Instellen'.
"""
import os
import re

import pytest
import requests

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(os.getenv("LLM_TEST") != "1", reason="alleen met LLM_TEST=1 en een draaiende stack met model"),
]

BASE_URL = os.getenv("LLM_TEST_BASE_URL", "http://localhost").rstrip("/")
GEBIED = os.getenv("LLM_TEST_GEBIED", "BU19000400")
MAX_WORDS = int(os.getenv("LLM_TEST_MAX_WORDS", "120"))
MAX_WORDS_RAPPORT = int(os.getenv("LLM_TEST_MAX_WORDS_RAPPORT", "200"))
TIMEOUT = int(os.getenv("LLM_TEST_TIMEOUT", "900"))

NEDERLANDSE_WOORDEN = {
    "de", "het", "een", "en", "van", "in", "is", "dat", "op", "voor", "met", "niet",
    "zijn", "te", "er", "je", "ik", "wordt", "deze", "als", "ook", "om", "bij", "naar",
}
FOUTMELDINGEN = ("Error contacting", "LLM-server", "Generatie mislukt", "Fout bij")


def woorden(tekst):
    return re.findall(r"[\wÀ-ÿ'-]+", tekst.lower())


def controleer_tekst(tekst, max_woorden):
    assert isinstance(tekst, str) and tekst.strip(), "lege tekst"
    assert not any(f in tekst for f in FOUTMELDINGEN), f"foutmelding i.p.v. tekst: {tekst[:200]}"
    assert "<think>" not in tekst and "</think>" not in tekst, "denk-output in de tekst"
    w = woorden(tekst)
    assert len(w) <= max_woorden, f"{len(w)} woorden (max {max_woorden}): {tekst[:300]}"
    nl = {x for x in w if x in NEDERLANDSE_WOORDEN}
    assert len(nl) >= 3, f"lijkt geen Nederlands (gevonden: {sorted(nl)}): {tekst[:300]}"


def test_chat_geeft_geldige_acties_en_kort_nederlands_antwoord():
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"vraag": "Welke indicatoren zeggen iets over eenzaamheid bij ouderen in de buurt?",
              "context": {"huidig_gebied_id": GEBIED}},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:500]
    data = r.json()

    assert isinstance(data["intent"], str) and data["intent"]
    assert isinstance(data["acties"], list)
    for actie in data["acties"]:
        assert isinstance(actie.get("type"), str) and actie["type"]
        assert isinstance(actie.get("label"), str) and actie["label"]
    assert isinstance(data["indicatoren"], list)
    # intelligent_dispatcher = het model gaf geldige JSON; legacy_fallback = JSON onbruikbaar
    assert data.get("debug", {}).get("mode") == "intelligent_dispatcher", data.get("debug")

    controleer_tekst(data["narrative"], MAX_WORDS)


def test_rapport_narrative_kort_en_nederlands():
    r = requests.get(f"{BASE_URL}/api/report/narrative/{GEBIED}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert data.get("status") == "success"
    if not data.get("domain_summaries"):
        pytest.skip(f"geen significante domeinen voor {GEBIED}; kies een ander gebied via LLM_TEST_GEBIED")
    controleer_tekst(data["ai_summary"], MAX_WORDS_RAPPORT)
    for domein, tekst in data.get("domain_summaries", {}).items():
        assert tekst.strip(), f"lege samenvatting voor {domein}"
        assert not any(f in tekst for f in FOUTMELDINGEN), f"{domein}: {tekst[:200]}"
