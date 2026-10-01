"""Configuratie (#130, #203): standaardwaarden, losse instellingen in plaats van DEBUG."""

import pytest
from starlette.requests import Request

from omnitwin import config
from omnitwin.config import instellingen

pytestmark = pytest.mark.unit

VARIABELEN = [
    "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD",
    "DATABASE_SSLMODE", "CORS_ORIGINS", "COOKIE_SECURE", "LLM_RATE_LIMIT", "ADMIN_API_KEY",
    "LOG_LEVEL", "OLLAMA_HOST", "OLLAMA_MODEL", "LLM_THINK", "LLM_REASONING_EFFORT",
    "LLM_API_KEY", "DEBUG",
]


@pytest.fixture
def schone_omgeving(monkeypatch):
    for naam in VARIABELEN:
        monkeypatch.delenv(naam, raising=False)
    return monkeypatch


def test_standaardwaarden(schone_omgeving):
    i = instellingen()
    assert (i.database_host, i.database_port, i.database_name, i.database_user) == (
        "localhost", "5432", "omnitwin_db", "omnitwin_user")
    assert i.database_password == "" and i.database_sslmode == "prefer"
    assert i.database_url == "postgresql+psycopg2://omnitwin_user:@localhost:5432/omnitwin_db?sslmode=prefer"
    assert i.cors_origins == ("http://localhost:8000",)
    assert i.cookie_secure == "auto"
    assert i.llm_rate_limit == 60
    assert i.admin_api_key == "" and i.log_level == "INFO"
    assert i.ollama_host == "http://localhost:11434" and i.ollama_model == "qwen3:30b-instruct"
    assert i.llm_think is False and i.llm_reasoning_effort == "none" and i.llm_api_key == ""


def test_cors_expliciete_lijst_zonder_wildcard(schone_omgeving):
    schone_omgeving.setenv("CORS_ORIGINS", " https://a.example.nl, ,https://b.example.nl ")
    assert instellingen().cors_origins == ("https://a.example.nl", "https://b.example.nl")
    assert "X-Admin-Key" in config.CORS_ALLOW_HEADERS


def test_debug_heeft_geen_invloed_meer(schone_omgeving):
    schone_omgeving.setenv("DEBUG", "true")
    i = instellingen()
    assert i.cookie_secure == "auto"
    assert i.cors_origins == ("http://localhost:8000",)


@pytest.mark.parametrize("waarde,verwacht", [
    ("true", "true"), ("1", "true"), ("false", "false"), ("0", "false"),
    ("auto", "auto"), ("", "auto"), ("onzin", "auto"),
])
def test_cookie_secure_waarden(schone_omgeving, waarde, verwacht):
    schone_omgeving.setenv("COOKIE_SECURE", waarde)
    assert instellingen().cookie_secure == verwacht


@pytest.mark.parametrize("waarde,verwacht", [("10", 10), ("0", 0), ("-5", 0), ("abc", 60)])
def test_llm_rate_limit(schone_omgeving, waarde, verwacht):
    schone_omgeving.setenv("LLM_RATE_LIMIT", waarde)
    assert instellingen().llm_rate_limit == verwacht


def _verzoek(scheme="http", headers=None):
    return Request({
        "type": "http", "scheme": scheme, "method": "POST", "path": "/", "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
    })


def test_cookie_secure_auto_volgt_https(schone_omgeving):
    from omnitwin.routers.auth import cookie_secure
    assert cookie_secure(_verzoek()) is False
    assert cookie_secure(_verzoek(scheme="https")) is True
    assert cookie_secure(_verzoek(headers={"X-Forwarded-Proto": "https"})) is True
    schone_omgeving.setenv("COOKIE_SECURE", "true")
    assert cookie_secure(_verzoek()) is True
    schone_omgeving.setenv("COOKIE_SECURE", "false")
    assert cookie_secure(_verzoek(scheme="https")) is False
