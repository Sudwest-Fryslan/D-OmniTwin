"""
AI herkenbaar maken (#312): de API zegt bij elk resultaat welke AI-usecase meedeed, zodat de
viewer en het beheer het label AI, de verklaring en "Melden" tonen. De meldplek is per instantie
instelbaar (organisatie.meld_url).
"""

from pathlib import Path

import pytest

from omnitwin import ai_vrijgave

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def logboek(monkeypatch):
    from omnitwin import ai_logboek

    monkeypatch.setattr(ai_logboek, "schrijf", lambda *a, **k: True)


def _chat(monkeypatch, open_usecases, llm_antwoord=None):
    from omnitwin.routers import chat as chat_mod

    monkeypatch.setattr(ai_vrijgave, "is_open", lambda u: u in open_usecases)
    monkeypatch.setattr(chat_mod, "beantwoord_datavraag_route", lambda *a: None)
    monkeypatch.setattr(chat_mod, "match_scenario", lambda *a: None)

    def zoek(self, q, limit=5):
        self.zonder_betekenis = "C" not in open_usecases
        return [{"uuid": "u-1", "naam": "Groen (%)", "score": 0.7, "relevantie": "sterk"}]

    monkeypatch.setattr(chat_mod.AISearchService, "search_indicators", zoek)
    monkeypatch.setattr(chat_mod.LLMService, "detect_intent_and_actions", lambda self, **k: llm_antwoord)
    return chat_mod.chat(chat_mod.ChatRequest(vraag="toon groen op de kaart"), db=None)


def test_chat_met_taalmodel_en_betekenis(monkeypatch, logboek):
    antwoord = _chat(
        monkeypatch, {"A", "C"}, {"intent": "TOON_OP_KAART", "narrative": "Hier is groen.", "acties": [], "debug": {}}
    )
    assert antwoord.ai_usecases == ["A", "C"]


def test_chat_zonder_ai(monkeypatch, logboek):
    assert _chat(monkeypatch, set()).ai_usecases == []


def test_chat_alleen_zoeken_op_betekenis(monkeypatch, logboek):
    assert _chat(monkeypatch, {"C"}).ai_usecases == ["C"]


def test_rapport_dicht_heeft_geen_ai_label(monkeypatch, logboek):
    from omnitwin.routers import report

    monkeypatch.setattr(ai_vrijgave, "is_open", lambda u: False)
    uit = report.generate_report_narrative("BU1", request=None, db=None)
    assert uit["ai_uit"] and not uit.get("ai")


def test_rapport_met_samenvatting_heeft_ai_label(monkeypatch, logboek):
    from omnitwin.routers import report

    monkeypatch.setattr(ai_vrijgave, "is_open", lambda u: True)
    monkeypatch.setattr(report, "_is_beheerder", lambda *a: False)
    monkeypatch.setattr(report, "_cache_get", lambda k: None)
    monkeypatch.setattr(report, "_cache_put", lambda k, v: None)

    class Data:
        def __init__(self, db):
            pass

        def generate_report_payload(self, gebied_id):
            return {"significante_domeinen": {"Wonen": [{"uuid": "u-1"}]}, "metadata": {"gebied": "X"}}

    class LLM:
        def __init__(self, db):
            pass

        def generate_domain_summary(self, d, i):
            return {"text": "Wonen is goed.", "debug": {}, "error": False}

        def generate_overall_summary(self, s, m):
            return {"text": "Alles goed.", "debug": {}, "error": False}

    monkeypatch.setattr(report, "ReportDataService", Data)
    monkeypatch.setattr(report, "LLMService", LLM)
    uit = report.generate_report_narrative("BU1", request=None, db=None)
    assert uit["ai"] == {"usecase": "B"}


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://meld.voorbeeld.nl/nieuw", True),
        ("mailto:ai-meldingen@voorbeeld.nl", True),
        ("", True),
        ("http://onveilig.nl", False),
        ("javascript:alert(1)", False),
        ("https://x.nl/" + "a" * 600, False),
    ],
)
def test_meld_url_validatie(url, ok):
    from pydantic import ValidationError

    from omnitwin.routers.organisatie import OrganisatieInvoer

    basis = {"code": "test", "naam": "Test", "gemeente_codes": ["0080"], "thema": "d-omnitwin"}
    if ok:
        invoer = OrganisatieInvoer(**basis, meld_url=url)
        assert invoer.meld_url == (url or None)
    else:
        with pytest.raises(ValidationError):
            OrganisatieInvoer(**basis, meld_url=url)


def test_standaard_meldplek_wordt_niet_opgeslagen():
    from omnitwin.routers.organisatie import OrganisatieInvoer
    from omnitwin.services.organisatie import STANDAARD_MELD_URL

    invoer = OrganisatieInvoer(code="t", naam="T", gemeente_codes=["0080"], meld_url=STANDAARD_MELD_URL)
    assert invoer.meld_url is None


def test_viewer_laadt_melden_en_label():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "/static/js/core/melden.js" in html and "/static/js/core/ai-label.js" in html
    assert 'name="d-omnitwin-versie"' in html
