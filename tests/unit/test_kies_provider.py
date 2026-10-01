"""Unit-tests voor scripts/llm/kies_provider.py (#88): beschikbaarheid zonder database of gateway."""
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PAD = Path(__file__).resolve().parents[2] / "scripts" / "llm" / "kies_provider.py"
_spec = importlib.util.spec_from_file_location("kies_provider", _PAD)
kp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kp)

ALIASSEN = {"d-omnitwin-default", "d-omnitwin-ollama", "d-omnitwin-claude", "d-omnitwin-openai", "d-omnitwin-gemini"}


@pytest.fixture
def env(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    return monkeypatch


@pytest.mark.parametrize("waarde", [None, "", "   "])
def test_lege_of_afwezige_sleutel_is_geen_key(env, waarde):
    if waarde is not None:
        env.setenv("ANTHROPIC_API_KEY", waarde)
    b = kp.beschikbaarheid("claude", ALIASSEN)
    assert not b["beschikbaar"] and "geen key" in b["reden"]


def test_gevulde_sleutel_en_bekende_alias(env):
    env.setenv("GEMINI_API_KEY", "x" * 39)
    b = kp.beschikbaarheid("gemini", ALIASSEN)
    assert b["beschikbaar"], b
    assert "x" * 39 not in str(b), "sleutelwaarde mag nooit in de uitvoer staan"


def test_gateway_onbereikbaar_of_alias_onbekend(env):
    env.setenv("OPENAI_API_KEY", "sk-x")
    assert "niet bereikbaar" in kp.beschikbaarheid("openai", None)["reden"]
    assert "onbekend" in kp.beschikbaarheid("openai", {"d-omnitwin-default"})["reden"]


def test_zonder_llm_api_key_geen_gateway(env):
    env.delenv("LLM_API_KEY")
    b = kp.beschikbaarheid("ollama", ALIASSEN)
    assert not b["beschikbaar"] and "LLM_API_KEY" in b["reden"]


def test_direct_ollama_en_config(env):
    assert kp.beschikbaarheid("direct-ollama", None)["beschikbaar"]
    assert kp.config_voor("direct-ollama") == ("ollama", "http://host.docker.internal:11434", "qwen3:4b-instruct")
    assert kp.config_voor("gemini") == ("openai", kp.GATEWAY_URL, "d-omnitwin-gemini")


def test_onderliggend_model_uit_gateway_config(env):
    assert kp.onderliggend_model("claude") == "anthropic/claude-haiku-4-5"
    assert kp.onderliggend_model("gemini").startswith("gemini/")
    assert kp.onderliggend_model("ollama") == "qwen3:4b-instruct"


@pytest.mark.parametrize("cfg,verwacht", [
    ({"api_type": "openai", "model_name": "d-omnitwin-gemini"}, "gemini"),
    ({"api_type": "openai", "model_name": "d-omnitwin-default"}, "anders"),
    ({"api_type": "ollama", "model_name": "qwen3:30b"}, "direct-ollama"),
])
def test_provider_van(cfg, verwacht):
    assert kp.provider_van(cfg) == verwacht
