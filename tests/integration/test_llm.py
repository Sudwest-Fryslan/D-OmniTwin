"""
LLM-beloftes tegen een draaiende stack met een echt model (#88, ADR 0001).

Niet in de CI (geen GPU, geen model). Handmatig, per api_type:

    LLM_TEST=1 LLM_TEST_BASE_URL=http://localhost pytest -m llm tests/integration/test_llm.py

Omgeving:
    LLM_TEST=1                   verplicht, anders worden de tests overgeslagen
    LLM_TEST_BASE_URL            basis-URL van de app (standaard http://localhost)
    LLM_TEST_GEBIED              buurt(en) voor het rapport, komma-gescheiden (standaard BU19000400, sample-data)
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

from tests.grounding import grounding_melding, ongegronde_getallen

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(os.getenv("LLM_TEST") != "1", reason="alleen met LLM_TEST=1 en een draaiende stack met model"),
]

BASE_URL = os.getenv("LLM_TEST_BASE_URL", "http://localhost").rstrip("/")
GEBIEDEN = [g.strip() for g in os.getenv("LLM_TEST_GEBIED", "BU19000400").split(",") if g.strip()]
MAX_WORDS = int(os.getenv("LLM_TEST_MAX_WORDS", "120"))
MAX_WORDS_RAPPORT = int(os.getenv("LLM_TEST_MAX_WORDS_RAPPORT", "200"))
TIMEOUT = int(os.getenv("LLM_TEST_TIMEOUT", "900"))

NEDERLANDSE_WOORDEN = {
    "de",
    "het",
    "een",
    "en",
    "van",
    "in",
    "is",
    "dat",
    "op",
    "voor",
    "met",
    "niet",
    "zijn",
    "te",
    "er",
    "je",
    "ik",
    "wordt",
    "deze",
    "als",
    "ook",
    "om",
    "bij",
    "naar",
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


CHAT_VRAAG = "Welke indicatoren zeggen iets over eenzaamheid bij ouderen in de buurt?"


@pytest.fixture(scope="module", params=GEBIEDEN)
def gebied(request):
    return request.param


@pytest.fixture(scope="module")
def chat(gebied):
    """Eén chat-verzoek per gebied, gedeeld door de chat-tests (model is traag)."""
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"vraag": CHAT_VRAAG, "context": {"huidig_gebied_id": gebied}},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:500]
    return r.json()


@pytest.fixture(scope="module")
def rapport(gebied):
    """Rapport-narrative plus de brondata waaruit de prompts zijn opgebouwd."""
    r = requests.get(f"{BASE_URL}/api/report/narrative/{gebied}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:500]
    narrative = r.json()
    assert narrative.get("status") == "success"
    if not narrative.get("domain_summaries"):
        pytest.skip(f"geen significante domeinen voor {gebied}; kies een ander gebied via LLM_TEST_GEBIED")
    # Zelfde payload als ReportDataService.generate_report_payload() in de narrative-route
    d = requests.get(f"{BASE_URL}/api/report/data/{gebied}", timeout=TIMEOUT)
    assert d.status_code == 200, d.text[:500]
    return narrative, d.json()


def test_chat_geeft_geldige_acties_en_kort_nederlands_antwoord(chat):
    data = chat
    assert isinstance(data["intent"], str) and data["intent"]
    assert isinstance(data["acties"], list)
    for actie in data["acties"]:
        assert isinstance(actie.get("type"), str) and actie["type"]
        assert isinstance(actie.get("label"), str) and actie["label"]
    assert isinstance(data["indicatoren"], list)
    # intelligent_dispatcher = het model gaf geldige JSON; legacy_fallback = JSON onbruikbaar
    assert data.get("debug", {}).get("mode") == "intelligent_dispatcher", data.get("debug")

    controleer_tekst(data["narrative"], MAX_WORDS)


def test_chat_narrative_getallen_uit_prompt(chat, gebied):
    """De chat-prompt bevat geen indicatorwaarden: elk getal moet uit vraag, context of indicator-metadata komen."""
    bron = {
        "vraag": CHAT_VRAAG,
        "context": {"huidig_gebied_id": gebied},
        "indicatoren": [
            {k: i.get(k) for k in ("naam", "beschrijving", "categorie", "eenheid")} for i in chat["indicatoren"]
        ],
    }
    ongegrond = ongegronde_getallen(chat["narrative"], bron)
    assert not ongegrond, grounding_melding(f"chat ({gebied})", chat["narrative"], bron, ongegrond)


def test_rapport_narrative_kort_en_nederlands(rapport):
    narrative, _ = rapport
    controleer_tekst(narrative["ai_summary"], MAX_WORDS_RAPPORT)
    for domein, tekst in narrative.get("domain_summaries", {}).items():
        assert tekst.strip(), f"lege samenvatting voor {domein}"
        assert not any(f in tekst for f in FOUTMELDINGEN), f"{domein}: {tekst[:200]}"


def test_rapport_narrative_getallen_uit_brondata(rapport, gebied):
    """Hallucinatie-check: elk getal in de AI-tekst moet (afgerond) in de brondata staan."""
    narrative, payload = rapport
    meldingen = []
    domeinen = payload.get("significante_domeinen", {})
    for domein, tekst in narrative.get("domain_summaries", {}).items():
        # De domein-prompt kreeg alleen de indicatoren van dit domein
        bron = {"domein": domein, "indicatoren": domeinen.get(domein, [])}
        ongegrond = ongegronde_getallen(tekst, bron)
        if ongegrond:
            meldingen.append(grounding_melding(f"domein '{domein}' ({gebied})", tekst, bron, ongegrond))
    # De overkoepelende prompt kreeg de domeinteksten + metadata; die zijn zelf uit de payload afgeleid
    ongegrond = ongegronde_getallen(narrative["ai_summary"], payload)
    if ongegrond:
        meldingen.append(grounding_melding(f"ai_summary ({gebied})", narrative["ai_summary"], payload, ongegrond))
    assert not meldingen, "\n\n".join(meldingen)
