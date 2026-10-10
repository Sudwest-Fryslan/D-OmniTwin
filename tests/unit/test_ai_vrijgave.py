"""
Unit-tests voor de AI-poort (#307): standaard dicht, open na een upload, dicht na geldig_tot,
noodstop, en geen aanroep van taalmodel of embeddingmodel in dichte toestand.

Zonder database: een nep-sessie die de paar statements van omnitwin.ai_vrijgave nadoet.
"""
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from omnitwin import ai_logboek, ai_vrijgave
from omnitwin.fouten import GebruikersFout

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
VANDAAG = date.today()
PDF = b"%PDF-1.4\n%test\n%%EOF\n"


class _Res:
    def __init__(self, rows=None, scalar=None):
        self._rows, self._scalar = rows or [], scalar

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


class NepDB:
    """Houdt usecases, verklaringen en het vrijgavelogboek in het geheugen bij."""

    def __init__(self):
        self.usecases = {c: {"code": c, "naam": n, "omschrijving": n, "stilgezet": False,
                             "status_door": None, "status_op": None} for c, n in ai_vrijgave.USECASES.items()}
        self.verklaringen, self.log, self.commits = [], [], 0

    def execute(self, sql, params=None):
        q, p = " ".join(str(sql).split()), params or {}
        if q.startswith("INSERT INTO public.ai_verklaringen"):
            vid = f"v{len(self.verklaringen) + 1}"
            self.verklaringen.append({**p, "id": vid, "volgorde": len(self.verklaringen)})
            return _Res(scalar=vid)
        if q.startswith("UPDATE public.ai_usecases"):
            self.usecases[p["code"]]["stilgezet"] = p.get("aan", False)
            self.usecases[p["code"]]["status_door"] = p["door"]
            return _Res()
        if q.startswith("INSERT INTO public.ai_vrijgave_log"):
            actie = re.search(r"'(verklaring_geupload|verlopen)'", q)
            self.log.append({**p, "actie": p.get("actie") or (actie.group(1) if actie else None)})
            return _Res()
        if q.startswith("SELECT 1 FROM public.ai_vrijgave_log"):
            return _Res([1] if any(r["actie"] == "verlopen" and r.get("v") == p["v"] for r in self.log) else [])
        if "FROM public.ai_usecases u" in q:
            return _Res(self.standen(p.get("code")))
        raise AssertionError(f"onverwachte SQL: {q[:80]}")

    def standen(self, code=None):
        uit = []
        for c, u in sorted(self.usecases.items()):
            if code and c != code:
                continue
            vs = [v for v in self.verklaringen if v["code"] == c]
            v = max(vs, key=lambda v: v["volgorde"]) if vs else {}
            uit.append({**u, "verklaring_id": v.get("id"), "versie": v.get("versie"), "geldig_tot": v.get("tot"),
                        "bestandsnaam": v.get("naam"), "grootte": v.get("grootte"), "sha256": v.get("sha"),
                        "geupload_door": v.get("door"), "geupload_op": None})
        return uit

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


@pytest.fixture
def db(monkeypatch):
    nep = NepDB()
    monkeypatch.setattr(ai_vrijgave, "_lees_standen", lambda code=None, db=None: nep.standen(code))
    return nep


@pytest.fixture
def logboek(monkeypatch):
    regels = []
    monkeypatch.setattr(ai_logboek, "schrijf", lambda *a, **k: regels.append((a, k)))
    return regels


# ── Beoordeling ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("geldig_tot, stilgezet, verwacht", [
    (None, False, (False, "geen_verklaring")),
    (VANDAAG + timedelta(days=30), False, (True, "open")),
    (VANDAAG, False, (True, "open")),                       # tot en met geldig_tot
    (VANDAAG - timedelta(days=1), False, (False, "verlopen")),
    (VANDAAG + timedelta(days=30), True, (False, "stilgezet")),
    (None, True, (False, "geen_verklaring")),
])
def test_beoordeel(geldig_tot, stilgezet, verwacht):
    assert ai_vrijgave.beoordeel(geldig_tot, stilgezet, VANDAAG) == verwacht


def test_standaard_dicht(db):
    assert not any(ai_vrijgave.is_open(c) for c in "ABC")
    assert [s["reden"] for s in ai_vrijgave.standen(db)] == ["geen_verklaring"] * 3


def test_onbekend_en_buiten_altijd_dicht(db):
    assert not ai_vrijgave.is_open(ai_vrijgave.BUITEN)
    assert not ai_vrijgave.is_open("D")
    assert not ai_vrijgave.is_open(None)


def test_dicht_als_de_status_niet_te_lezen_is(monkeypatch):
    def kapot(code=None, db=None):
        raise RuntimeError("database weg")
    monkeypatch.setattr(ai_vrijgave, "_lees_standen", kapot)
    assert ai_vrijgave.is_open("A") is False


def test_open_na_upload_en_vastgelegd_wie(db):
    ai_vrijgave.upload(db, "A", " 0.4.0 ", VANDAAG + timedelta(days=10), "C:\\map\\DPIA A.pdf", PDF,
                       "application/pdf", "beheerder1")
    assert ai_vrijgave.is_open("A")
    assert not ai_vrijgave.is_open("B")
    v = db.verklaringen[0]
    assert (v["versie"], v["door"], v["naam"]) == ("0.4.0", "beheerder1", "DPIA A.pdf")
    assert db.log[-1]["actie"] == "verklaring_geupload" and db.log[-1]["door"] == "beheerder1"


def test_dicht_na_geldig_tot(db):
    ai_vrijgave.upload(db, "B", "1", VANDAAG, "b.pdf", PDF, "application/pdf", "x")
    assert ai_vrijgave.is_open("B")
    db.verklaringen[0]["tot"] = VANDAAG - timedelta(days=1)
    assert not ai_vrijgave.is_open("B")
    assert ai_vrijgave.registreer_verlopen(db) == 1
    assert ai_vrijgave.registreer_verlopen(db) == 0  # één keer vastgelegd
    assert db.log[-1]["actie"] == "verlopen" and db.log[-1].get("door") is None


def test_noodstop_en_hervatten(db):
    ai_vrijgave.upload(db, "C", "1", VANDAAG + timedelta(days=1), "c.pdf", PDF, "application/pdf", "x")
    ai_vrijgave.zet_noodstop(db, "C", True, "fb")
    assert not ai_vrijgave.is_open("C")
    assert [s for s in ai_vrijgave.standen(db) if s["code"] == "C"][0]["reden"] == "stilgezet"
    ai_vrijgave.zet_noodstop(db, "C", False, "fb")
    assert ai_vrijgave.is_open("C")
    assert [r["actie"] for r in db.log] == ["verklaring_geupload", "noodstop", "hervat"]


def test_hervatten_zonder_verklaring_blijft_dicht(db):
    ai_vrijgave.zet_noodstop(db, "A", False, "fb")
    assert not ai_vrijgave.is_open("A")


def test_upload_na_noodstop_opent_weer(db):
    ai_vrijgave.zet_noodstop(db, "A", True, "fb")
    ai_vrijgave.upload(db, "A", "2", VANDAAG + timedelta(days=1), "a.pdf", PDF, "application/pdf", "fb")
    assert ai_vrijgave.is_open("A")


@pytest.mark.parametrize("inhoud, ctype, fout", [
    (PDF, "text/plain", "PDF zijn"),
    (b"GIF89a....", "application/pdf", "geen PDF"),
    (b"", "application/pdf", "leeg"),
    (b"%PDF" + b"0" * ai_vrijgave.MAX_PDF, "application/pdf", "groter"),
], ids=["content-type", "magic", "leeg", "te-groot"])
def test_upload_alleen_pdf(db, inhoud, ctype, fout):
    with pytest.raises(GebruikersFout, match=fout):
        ai_vrijgave.upload(db, "A", "1", VANDAAG + timedelta(days=1), "a.pdf", inhoud, ctype, "x")
    assert not db.verklaringen and not ai_vrijgave.is_open("A")


def test_upload_geldig_tot_in_het_verleden_en_lege_versie(db):
    with pytest.raises(GebruikersFout, match="verleden"):
        ai_vrijgave.upload(db, "A", "1", VANDAAG - timedelta(days=1), "a.pdf", PDF, "application/pdf", "x")
    with pytest.raises(GebruikersFout, match="Versie"):
        ai_vrijgave.upload(db, "A", "  ", VANDAAG, "a.pdf", PDF, "application/pdf", "x")
    with pytest.raises(GebruikersFout, match="Onbekende"):
        ai_vrijgave.upload(db, "D", "1", VANDAAG, "a.pdf", PDF, "application/pdf", "x")


def test_poort_logt_weigering(db, logboek):
    assert ai_vrijgave.poort("A", "Chat", taak="hoeveel groen?") is False
    (usecase, functie, status), velden = logboek[0]
    assert (usecase, functie, status) == ("A", "Chat", "geweigerd")
    assert velden["taak"] == "hoeveel groen?"
    assert ai_vrijgave.poort(ai_vrijgave.BUITEN, "Ontologie") is False
    assert logboek[1][0][0] == "X"


def test_poort_open_logt_geen_weigering(db, logboek):
    ai_vrijgave.upload(db, "A", "1", VANDAAG, "a.pdf", PDF, "application/pdf", "x")
    assert ai_vrijgave.poort("A", "Chat") is True
    assert logboek == []


# ── Geen AI-aanroep in dichte toestand ───────────────────────────────────────

class _LLMDB:
    def execute(self, *a, **k):
        raise AssertionError("dicht: de LLM-configuratie hoort niet eens gelezen te worden")


def test_call_llm_dicht_doet_geen_aanroep(db, logboek, monkeypatch):
    import omnitwin.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod.requests, "post", lambda *a, **k: pytest.fail("taalmodel aangeroepen"))
    res = llm_mod.LLMService(_LLMDB())._call_llm("sys", "vraag", "test", usecase="A", bronnen=["u1"])
    assert res["error"] and res["geweigerd"] and "staat uit" in res["text"]
    assert logboek[0][0] == ("A", "test", "geweigerd")


class _PromptDB:
    """Alleen de systeemprompt mag gelezen worden (geen rij: de standaardprompt)."""
    def execute(self, sql, params=None):
        assert "system_prompts" in str(sql), str(sql)
        return _Res()


def test_call_llm_buiten_altijd_dicht(monkeypatch, logboek):
    import omnitwin.services.llm_service as llm_mod
    monkeypatch.setattr(ai_vrijgave, "_lees_standen", lambda code=None, db=None: pytest.fail("niet nodig"))
    monkeypatch.setattr(llm_mod.requests, "post", lambda *a, **k: pytest.fail("taalmodel aangeroepen"))
    svc = llm_mod.LLMService(_PromptDB())
    assert svc.validate_duplicates([{"uuid": "u1", "naam": "x"}])["is_duplicaat"] is False
    from omnitwin.utils.ai_generator import generate_indicator_description
    assert generate_indicator_description(svc, "n", "c", "o", "b") == ""


def test_call_llm_vraagt_een_usecase():
    from omnitwin.services.llm_service import LLMService
    with pytest.raises(TypeError):
        LLMService(_LLMDB())._call_llm("sys", "vraag", "test")


class _ZoekDB:
    def __init__(self):
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(str(sql))
        if "indicator_embeddings" in str(sql):
            raise AssertionError("dicht: geen gelijkenis via embeddings")
        return _Rows([("u-1", "65+ jaar (%)", "Aandeel ouderen", "Bevolking", None, None, "draft", "%", "+/-"),
                      ("u-2", "Gemiddeld energielabel", "Energie", "Wonen", None, None, "draft", "", "+/-")])


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


def test_zoeken_dicht_zonder_embeddingmodel(db, logboek, monkeypatch):
    from omnitwin.services import ai_search_service, embedding_model
    monkeypatch.setattr(ai_search_service, "_model", None)
    monkeypatch.setattr(embedding_model, "gedeeld_model", lambda: pytest.fail("embeddingmodel geladen"))
    svc = ai_search_service.AISearchService(_ZoekDB(), functie="Kompas-zoeken")
    uit = svc.search_indicators("energielabels", limit=5)
    assert svc.zonder_betekenis
    assert uit and uit[0]["uuid"] == "u-2" and "betekenis" not in uit[0]["redenen"]
    assert logboek[0][0] == ("C", "Kompas-zoeken", "geweigerd")


def test_chat_dicht_regelgebaseerd_zonder_taalmodel(db, logboek, monkeypatch):
    from omnitwin.routers import chat as chat_mod
    monkeypatch.setattr(chat_mod, "beantwoord_datavraag_route", lambda *a: None)
    monkeypatch.setattr(chat_mod, "match_scenario", lambda *a: None)
    monkeypatch.setattr(chat_mod.AISearchService, "search_indicators",
                        lambda self, q, limit=5: [{"uuid": "u-1", "naam": "Groen (%)", "score": 0.7, "relevantie": "sterk"}])
    monkeypatch.setattr(chat_mod.LLMService, "_call_llm", lambda *a, **k: pytest.fail("taalmodel aangeroepen"))
    antwoord = chat_mod.chat(chat_mod.ChatRequest(vraag="toon groen op de kaart"), db=None)
    assert antwoord.debug["mode"] == "zonder_ai"
    assert "Groen (%)" in antwoord.narrative
    assert antwoord.melding.startswith("De AI-assistent staat uit")
    assert antwoord.acties and antwoord.acties[0].indicator_uuid == "u-1"
    assert ("A", "Chat", "geweigerd") in [r[0] for r in logboek]


def test_rapport_dicht_zonder_samenvatting(db, logboek, monkeypatch):
    from omnitwin.routers import report
    monkeypatch.setattr(report, "LLMService", lambda *a: pytest.fail("taalmodel aangeroepen"))
    monkeypatch.setattr(report, "ReportDataService", lambda *a: pytest.fail("niet nodig"))
    uit = report.generate_report_narrative("BU19000002", request=None, db=None)
    assert uit["ai_uit"] and uit["ai_summary"] == ai_vrijgave.melding("B") and uit["domain_summaries"] == {}
    uit = report.get_benchmark_narrative(request=None, gebied_a="BU19000002", mode="gebieden", gebieden_b=None,
                                         referentie_gemeente=None, db=None)
    assert uit["ai_uit"] and uit["ai_narrative"] == ai_vrijgave.melding("B")
    assert [r[0][0] for r in logboek] == ["B", "B"]


# ── Geen pad om de poort heen ────────────────────────────────────────────────

def _python_bestanden():
    for map_ in ("src", "scripts", "ETL", "init_data"):
        yield from (ROOT / map_).rglob("*.py")


def test_elke_llm_aanroep_noemt_een_usecase():
    """Elke aanroep van _call_llm geeft usecase= mee, en alleen llm_service.py praat met de LLM-server."""
    for pad in _python_bestanden():
        tekst = pad.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\._call_llm\(", tekst):
            aanroep = tekst[m.start(): m.start() + 400]
            assert "usecase=" in aanroep, f"{pad}: _call_llm zonder usecase"
        if pad.name != "llm_service.py":
            assert "/api/generate" not in tekst and "chat/completions" not in tekst, \
                f"{pad}: eigen aanroep van een taalmodel buiten LLMService"
            assert "_call_ollama" not in tekst and "_call_openai" not in tekst, f"{pad}: omzeilt _call_llm"


def test_embeddingmodel_alleen_achter_de_poort():
    """Een vraag van een gebruiker gaat alleen via AISearchService (achter usecase C) naar het model;
    indicator_embeddings.py berekent embeddings van indicatoren bij het laden (geen gebruikersinvoer)."""
    toegestaan = {"ai_search_service.py", "indicator_embeddings.py", "embedding_model.py"}
    for pad in _python_bestanden():
        if pad.name in toegestaan:
            continue
        tekst = pad.read_text(encoding="utf-8", errors="ignore")
        assert "gedeeld_model(" not in tekst and "SentenceTransformer(" not in tekst, \
            f"{pad}: embeddingmodel buiten de AI-poort"
