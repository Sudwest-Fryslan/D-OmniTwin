"""
Unit-tests voor services/llm_service.py (#88, ADR 0001): Ollama- en OpenAI-pad.

Geen database en geen echt model: een nep-LLM-server (http.server in een thread)
en een nep-databasesessie. Draait in de CI met `pytest -m unit`.
"""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import omnitwin.services.llm_service as llm_mod
from omnitwin.services.llm_service import LLMService, openai_base_url, strip_think, veilige_host

pytestmark = pytest.mark.unit


# ─── Nep-LLM-server ─────────────────────────────────────────────────────────

class FakeLLM:
    """Houdt verzoeken bij en geeft per pad een vooraf ingesteld antwoord."""

    def __init__(self):
        self.requests = []          # (method, path, headers, body)
        self.responses = {}         # path -> (status, body: dict|str)

    def set(self, path, body, status=200):
        self.responses[path] = (status, body)


@pytest.fixture
def fake_llm():
    state = FakeLLM()

    class Handler(BaseHTTPRequestHandler):
        def _antwoord(self, method):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else None
            state.requests.append((method, self.path, dict(self.headers), body))
            status, resp = state.responses.get(self.path, (404, {"error": "niet gevonden"}))
            data = resp if isinstance(resp, str) else json.dumps(resp)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))

        def do_POST(self):
            self._antwoord("POST")

        def do_GET(self):
            self._antwoord("GET")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()
    server.server_close()


# ─── Nep-database ───────────────────────────────────────────────────────────

class _Result:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row

    def fetchall(self):
        return [] if self._row is None else [self._row]


class FakeDB:
    """Minimale Session: llm_config-rij en (lege) system_prompts."""

    def __init__(self, config_row):
        self.config_row = config_row

    def execute(self, query, params=None):
        sql = str(query)
        if "information_schema.columns" in sql:
            return _Result((1,) if self.config_row and "api_type" in self.config_row else None)
        if "llm_config" in sql:
            return _Result(self.config_row)
        return _Result(None)  # system_prompts: val terug op de standaardprompt

    def rollback(self):
        pass

    def commit(self):
        pass


@pytest.fixture(autouse=True)
def stille_logger(monkeypatch):
    """AppLogger schrijft naar de database; in unit-tests alleen stil wegschrijven."""
    class Stil:
        @staticmethod
        def _noop(*args, **kwargs):
            pass
        debug = info = warning = error = critical = _noop

    monkeypatch.setattr(llm_mod, "AppLogger", Stil)
    # AI-vrijgave (#307) en AI-logboek (#313) zonder database: hier alle usecases open, logboek stil
    monkeypatch.setattr(llm_mod.ai_vrijgave, "is_open", lambda usecase: usecase in ("A", "B", "C"))
    monkeypatch.setattr(llm_mod.ai_logboek, "schrijf", lambda *a, **k: None)
    for var in ("LLM_API_KEY", "LLM_THINK", "LLM_REASONING_EFFORT"):
        monkeypatch.delenv(var, raising=False)


def service(api_url, api_type="ollama", model="testmodel"):
    row = {"api_url": api_url, "model_name": model}
    if api_type is not None:
        row["api_type"] = api_type
    return LLMService(FakeDB(row))


def chat_antwoord(content):
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}


# ─── Hulpfuncties ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("url, verwacht", [
    ("http://host:11434", "http://host:11434/v1"),
    ("http://host:11434/", "http://host:11434/v1"),
    ("http://llm-gateway:4000/v1", "http://llm-gateway:4000/v1"),
    ("http://llm-gateway:4000/v1/", "http://llm-gateway:4000/v1"),
    ("https://api.example.org/openai/v1", "https://api.example.org/openai/v1"),
])
def test_openai_base_url_geen_dubbele_v1(url, verwacht):
    assert openai_base_url(url) == verwacht


@pytest.mark.parametrize("invoer, verwacht", [
    ("<think>\nredeneren...\n</think>\n\nHet antwoord.", "Het antwoord."),
    ("Voor <think>a</think>na", "Voor na"),
    ("alleen denken</think>Antwoord", "Antwoord"),
    ("<think></think>{\"intent\": \"X\"}", "{\"intent\": \"X\"}"),
    ("Geen denkblok.", "Geen denkblok."),
    ("", ""),
])
def test_strip_think(invoer, verwacht):
    assert strip_think(invoer) == verwacht


def test_veilige_host_zonder_pad_en_inlog():
    assert veilige_host("http://user:geheim@llm:4000/v1") == "http://llm:4000"


# ─── Configuratie ───────────────────────────────────────────────────────────

def test_config_zonder_api_type_kolom_is_ollama():
    """Database zonder migratie v20: gedrag als voorheen."""
    cfg = service("http://x:11434", api_type=None).get_llm_config()
    assert cfg["api_type"] == "ollama"


def test_config_zonder_rij_valt_terug_op_env():
    cfg = LLMService(FakeDB(None)).get_llm_config()
    assert cfg["api_type"] == "ollama"
    assert cfg["api_url"] == llm_mod.DEFAULT_OLLAMA_HOST


# ─── Ollama-pad (ongewijzigd gedrag) ────────────────────────────────────────

def test_ollama_pad_gebruikt_api_generate(fake_llm):
    fake_llm.set("/api/generate", {"response": "```json\n{\"summary\": \"Kort verhaal.\"}\n```"})
    res = service(fake_llm.url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")

    method, path, _, body = fake_llm.requests[-1]
    assert (method, path) == ("POST", "/api/generate")
    assert body["system"] == "sys" and body["prompt"] == "vraag"
    assert body["options"]["temperature"] == 0.3 and body["stream"] is False
    assert res["text"] == "Kort verhaal."


def test_ollama_pad_denken_standaard_uit(fake_llm):
    """Qwen3 e.d. denken anders duizenden tokens vooraf (minuten per antwoord)."""
    fake_llm.set("/api/generate", {"response": "ok"})
    service(fake_llm.url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")
    assert fake_llm.requests[-1][3]["think"] is False


def test_ollama_pad_denken_aan_laat_veld_weg(fake_llm, monkeypatch):
    """LLM_THINK=true: geen think-veld, het model beslist (think=true breekt niet-denkende modellen)."""
    monkeypatch.setenv("LLM_THINK", "true")
    fake_llm.set("/api/generate", {"response": "ok"})
    service(fake_llm.url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")
    assert "think" not in fake_llm.requests[-1][3]


def test_ollama_pad_haalt_leeg_denkblok_weg(fake_llm):
    fake_llm.set("/api/generate", {"response": "<think>\n\n</think>\n\nHet antwoord."})
    assert service(fake_llm.url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")["text"] == "Het antwoord."


def test_ollama_pad_stuurt_geen_api_key(fake_llm, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-geheim")
    fake_llm.set("/api/generate", {"response": "ok"})
    service(fake_llm.url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")
    headers = {k.lower(): v for k, v in fake_llm.requests[-1][2].items()}
    assert "authorization" not in headers


def test_ollama_pad_foutmelding_zonder_interne_url():
    """Geen interne URL of fouttekst in de response (#65); details staan in de log."""
    url = f"http://127.0.0.1:{_vrije_poort()}"
    res = service(url, "ollama")._call_llm("sys", "vraag", "test", usecase="A")
    assert res["text"] == "De AI-samenvatting is nu niet beschikbaar."
    assert res["error"] is True
    assert url not in res["text"]


# ─── OpenAI-pad ─────────────────────────────────────────────────────────────

def test_openai_pad_chat_completions(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord("Dit is het antwoord."))
    res = service(fake_llm.url, "openai", model="d-omnitwin-default")._call_llm("sys", "vraag", "test", usecase="A")

    method, path, headers, body = fake_llm.requests[-1]
    assert (method, path) == ("POST", "/v1/chat/completions")
    assert body["model"] == "d-omnitwin-default"
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "vraag"},
    ]
    assert body["temperature"] == 0.3 and body["stream"] is False
    assert "authorization" not in {k.lower() for k in headers}
    assert res["text"] == "Dit is het antwoord."
    assert res["debug"]["model"] == "d-omnitwin-default"


def test_openai_pad_denken_standaard_uit(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    body = fake_llm.requests[-1][3]
    assert body["reasoning_effort"] == "none"
    assert "think" not in body  # geen standaardveld in de OpenAI-API


def test_openai_pad_qwen3_krijgt_no_think(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url, "openai", model="qwen3:4b")._call_llm("sys", "vraag", "test", usecase="A")
    assert fake_llm.requests[-1][3]["messages"][0] == {"role": "system", "content": "sys\n\n/no_think"}


def test_openai_pad_reasoning_effort_leeg_laat_veld_weg(fake_llm, monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "")
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert "reasoning_effort" not in fake_llm.requests[-1][3]


def test_openai_pad_denken_aan(fake_llm, monkeypatch):
    monkeypatch.setenv("LLM_THINK", "true")
    fake_llm.set("/v1/chat/completions", chat_antwoord("<think>lang</think>Antwoord"))
    res = service(fake_llm.url, "openai", model="qwen3:4b")._call_llm("sys", "vraag", "test", usecase="A")
    body = fake_llm.requests[-1][3]
    assert "reasoning_effort" not in body
    assert body["messages"][0]["content"] == "sys"
    assert res["text"] == "Antwoord"  # denk-output nooit in de tekst


def test_openai_pad_zonder_systeemprompt(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url, "openai")._call_llm("", "vraag", "test", usecase="A")
    assert fake_llm.requests[-1][3]["messages"] == [{"role": "user", "content": "vraag"}]


def test_openai_pad_url_met_v1_niet_verdubbeld(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url + "/v1/", "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert fake_llm.requests[-1][1] == "/v1/chat/completions"


def test_openai_pad_bearer_uit_env(fake_llm, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-123")
    fake_llm.set("/v1/chat/completions", chat_antwoord("ok"))
    service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    headers = {k.lower(): v for k, v in fake_llm.requests[-1][2].items()}
    assert headers["authorization"] == "Bearer sk-test-123"


def test_openai_pad_haalt_think_weg_en_pakt_json_uit(fake_llm):
    inhoud = "<think>\nEerst nadenken.\n</think>\n```json\n{\"summary\": \"Samenvatting.\"}\n```"
    fake_llm.set("/v1/chat/completions", chat_antwoord(inhoud))
    res = service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert res["text"] == "Samenvatting."


def test_openai_pad_intent_json(fake_llm):
    """detect_intent_and_actions parseert het JSON-antwoord ook via het OpenAI-pad."""
    antwoord = {"intent": "MAAK_RAPPORT", "narrative": "Ik open het rapport.",
                "acties": [{"type": "MAAK_RAPPORT", "label": "Rapport openen"}]}
    fake_llm.set("/v1/chat/completions", chat_antwoord("<think>x</think>" + json.dumps(antwoord)))
    res = service(fake_llm.url, "openai").detect_intent_and_actions("maak een rapport", [])
    assert res["intent"] == "MAAK_RAPPORT"
    assert res["acties"][0]["type"] == "MAAK_RAPPORT"


def test_openai_pad_null_content(fake_llm):
    fake_llm.set("/v1/chat/completions", chat_antwoord(None))
    assert service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")["text"] == ""


# ─── Foutafhandeling OpenAI-pad ─────────────────────────────────────────────

@pytest.mark.parametrize("status, fragment", [
    (401, "weigert toegang (401); controleer LLM_API_KEY"),
    (403, "weigert toegang (403)"),
    (500, "gaf een fout (500)"),
    (404, "gaf een fout (404)"),
])
def test_openai_http_fout_nette_melding(fake_llm, monkeypatch, status, fragment):
    monkeypatch.setenv("LLM_API_KEY", "sk-mag-niet-lekken")
    fake_llm.set("/v1/chat/completions", {"error": {"message": "intern detail"}}, status=status)
    res = service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert fragment in res["text"]
    assert fake_llm.url in res["text"]
    assert "sk-mag-niet-lekken" not in res["text"]
    assert "intern detail" not in res["text"]


def test_openai_onbereikbaar():
    url = f"http://127.0.0.1:{_vrije_poort()}"
    res = service(url + "/v1", "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert res["text"] == f"LLM-server niet bereikbaar op {url}"


@pytest.mark.parametrize("body", ["geen json", {"choices": []}, {"iets": "anders"}])
def test_openai_onverwacht_antwoord(fake_llm, body):
    fake_llm.set("/v1/chat/completions", body)
    res = service(fake_llm.url, "openai")._call_llm("sys", "vraag", "test", usecase="A")
    assert res["text"] == f"Onverwacht antwoord van LLM-server op {fake_llm.url}"


# ─── Admin: modellen ophalen ────────────────────────────────────────────────

def _models(db):
    admin = pytest.importorskip("omnitwin.routers.admin")
    return admin.get_ollama_models(db=db)


def test_admin_models_ollama(fake_llm):
    fake_llm.set("/api/tags", {"models": [{"name": "qwen3:4b"}, {"name": "gemma4"}]})
    res = _models(FakeDB({"api_url": fake_llm.url, "model_name": "qwen3:4b", "api_type": "ollama"}))
    assert res == {"models": ["qwen3:4b", "gemma4"]}
    assert fake_llm.requests[-1][1] == "/api/tags"


def test_admin_models_openai(fake_llm, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-abc")
    fake_llm.set("/v1/models", {"object": "list", "data": [{"id": "d-omnitwin-default", "object": "model"}]})
    res = _models(FakeDB({"api_url": fake_llm.url + "/v1", "model_name": "x", "api_type": "openai"}))
    assert res == {"models": ["d-omnitwin-default"]}
    method, path, headers, _ = fake_llm.requests[-1]
    assert (method, path) == ("GET", "/v1/models")
    assert {k.lower(): v for k, v in headers.items()}["authorization"] == "Bearer sk-abc"


def test_admin_models_geen_json(fake_llm):
    fake_llm.set("/v1/models", "geen json")
    res = _models(FakeDB({"api_url": fake_llm.url, "model_name": "m", "api_type": "openai"}))
    assert res["error"] == f"Onverwacht antwoord van LLM-server op {fake_llm.url}"


def test_admin_models_onbereikbaar_valt_terug_op_huidig_model():
    url = f"http://127.0.0.1:{_vrije_poort()}"
    res = _models(FakeDB({"api_url": url, "model_name": "qwen3:4b", "api_type": "openai"}))
    assert res["models"] == ["qwen3:4b"]
    assert res["error"] == f"LLM-server niet bereikbaar op {url}"


def test_admin_llmconfig_valideert_api_type():
    admin = pytest.importorskip("omnitwin.routers.admin")
    assert admin.LLMConfig(api_url="http://x", model_name="m").api_type == "ollama"
    assert admin.LLMConfig(api_url="http://x", model_name="m", api_type="openai").api_type == "openai"
    with pytest.raises(Exception):
        admin.LLMConfig(api_url="http://x", model_name="m", api_type="anthropic")


def test_admin_opslaan_zonder_v20_weigert_openai():
    admin = pytest.importorskip("omnitwin.routers.admin")
    db = FakeDB({"api_url": "http://x", "model_name": "m"})  # geen api_type-kolom
    cfg = admin.LLMConfig(api_url="http://x", model_name="m", api_type="openai")
    with pytest.raises(admin.HTTPException) as exc:
        admin.update_llm_config(cfg, db=db)
    assert exc.value.status_code == 409
    ok = admin.LLMConfig(api_url="http://x", model_name="m", api_type="ollama")
    assert admin.update_llm_config(ok, db=db) == ok


def _vrije_poort():
    """Een poort waar (vrijwel zeker) niets luistert."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
