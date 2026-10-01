#!/usr/bin/env python3
"""
Kies de LLM-aanbieder van D-OmniTwin (#88, ADR 0001).

Voegt een nieuwe rij toe aan llm_config (de app gebruikt altijd de nieuwste rij):

    ollama         api_type=openai  http://llm-gateway:4000  d-omnitwin-ollama   (lokaal Ollama via gateway)
    claude         api_type=openai  http://llm-gateway:4000  d-omnitwin-claude   (ANTHROPIC_API_KEY)
    openai         api_type=openai  http://llm-gateway:4000  d-omnitwin-openai   (OPENAI_API_KEY)
    gemini         api_type=openai  http://llm-gateway:4000  d-omnitwin-gemini   (GEMINI_API_KEY)
    direct-ollama  api_type=ollama  OLLAMA_HOST              OLLAMA_MODEL        (zonder gateway)

Gebruik (in de backend-container: daar zijn database, .env en gateway bereikbaar):

    docker compose exec backend python scripts/llm/kies_provider.py gemini
    docker compose exec backend python scripts/llm/kies_provider.py status
    docker compose exec backend python scripts/llm/kies_provider.py beschikbaar

Een aanbieder via de gateway wordt geweigerd als
  - de sleutel van de aanbieder leeg of afwezig is (alleen aanwezigheid wordt gecontroleerd,
    de waarde wordt nooit getoond),
  - LLM_API_KEY leeg is (de backend moet zich bij de gateway aanmelden met LITELLM_MASTER_KEY),
  - de gateway niet bereikbaar is of de alias niet kent (start met --profile llm-gateway).

Databaseverbinding via DATABASE_HOST/PORT/NAME/USER/PASSWORD, zoals init_data/scripts/load_sample.py.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://llm-gateway:4000").rstrip("/")

# naam -> (gateway-alias of None, omgevingsvariabele met de sleutel of None)
PROVIDERS = {
    "ollama": ("d-omnitwin-ollama", None),
    "claude": ("d-omnitwin-claude", "ANTHROPIC_API_KEY"),
    "openai": ("d-omnitwin-openai", "OPENAI_API_KEY"),
    "gemini": ("d-omnitwin-gemini", "GEMINI_API_KEY"),
    "direct-ollama": (None, None),
}


def gezet(naam: str) -> bool:
    """Is de omgevingsvariabele gevuld? Toont nooit de waarde."""
    return bool((os.environ.get(naam) or "").strip())


def get_db_connection():
    import psycopg2

    host = os.environ.get("DATABASE_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    return psycopg2.connect(
        host=host,
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
        connect_timeout=10,
    )


def gateway_aliassen():
    """Aliassen die de gateway kent (via /v1/models), of None als de gateway onbereikbaar is."""
    import requests

    headers = {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"} if gezet("LLM_API_KEY") else {}
    try:
        r = requests.get(f"{GATEWAY_URL}/v1/models", headers=headers, timeout=10)
        r.raise_for_status()
        return {m.get("id") for m in r.json().get("data", [])}
    except Exception:
        return None


def onderliggend_model(naam: str):
    """Model achter een aanbieder (uit OLLAMA_MODEL of deploy/litellm/config.yaml), voor rapportage."""
    alias, _ = PROVIDERS[naam]
    if alias is None or naam == "ollama":
        return os.environ.get("OLLAMA_MODEL")
    config = Path(__file__).resolve().parent.parent.parent / "deploy" / "litellm" / "config.yaml"
    try:
        tekst = config.read_text(encoding="utf-8")
    except OSError:
        return None
    import re
    m = re.search(rf"model_name:\s*{re.escape(alias)}\s*\n\s*litellm_params:\s*\n(?:\s*#.*\n)*\s*model:\s*(\S+)", tekst)
    return m.group(1) if m else None


def beschikbaarheid(naam: str, aliassen="?") -> dict:
    uit = _beschikbaarheid(naam, aliassen)
    uit["model"] = onderliggend_model(naam)
    return uit


def _beschikbaarheid(naam: str, aliassen="?") -> dict:
    """{'beschikbaar': bool, 'reden': str} voor één aanbieder."""
    alias, sleutel = PROVIDERS[naam]
    if alias is None:
        if not gezet("OLLAMA_HOST") or not gezet("OLLAMA_MODEL"):
            return {"beschikbaar": False, "reden": "OLLAMA_HOST of OLLAMA_MODEL niet gezet"}
        return {"beschikbaar": True, "reden": "direct naar Ollama"}
    if sleutel and not gezet(sleutel):
        return {"beschikbaar": False, "reden": f"geen key ({sleutel} leeg of afwezig in .env)"}
    if not gezet("LLM_API_KEY"):
        return {"beschikbaar": False, "reden": "LLM_API_KEY leeg (moet gelijk zijn aan LITELLM_MASTER_KEY)"}
    if aliassen == "?":
        aliassen = gateway_aliassen()
    if aliassen is None:
        return {"beschikbaar": False, "reden": f"gateway niet bereikbaar op {GATEWAY_URL} (profiel llm-gateway?)"}
    if alias not in aliassen:
        return {"beschikbaar": False, "reden": f"alias {alias} onbekend bij de gateway"}
    return {"beschikbaar": True, "reden": f"via gateway, alias {alias}"}


def actieve_config(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
        rij = cur.fetchone()
        if not rij:
            return {}
        kolommen = [d[0] for d in cur.description]
    r = dict(zip(kolommen, rij))
    return {"id": r["id"], "api_type": r.get("api_type") or "ollama",
            "api_url": r["api_url"], "model_name": r["model_name"]}


def zet_config(conn, api_type: str, api_url: str, model_name: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO llm_config (api_url, model_name, api_type) VALUES (%s, %s, %s)",
            (api_url, model_name, api_type),
        )
    conn.commit()
    return actieve_config(conn)


def config_voor(naam: str) -> tuple:
    alias, _ = PROVIDERS[naam]
    if alias is None:
        return "ollama", os.environ["OLLAMA_HOST"].rstrip("/"), os.environ["OLLAMA_MODEL"]
    return "openai", GATEWAY_URL, alias


def provider_van(cfg: dict) -> str:
    """Terugvertaling van een llm_config-rij naar een aanbiedernaam (of 'anders')."""
    if cfg.get("api_type") == "openai":
        for naam, (alias, _) in PROVIDERS.items():
            if alias and cfg.get("model_name") == alias:
                return naam
    elif cfg.get("api_type") == "ollama":
        return "direct-ollama"
    return "anders"


def toon(cfg: dict, als_json: bool, extra: dict = None):
    uit = {**cfg, "provider": provider_van(cfg), **(extra or {})}
    if als_json:
        print(json.dumps(uit, ensure_ascii=False))
    else:
        print(f"Actief: {uit['provider']}  (llm_config id {cfg.get('id')}: api_type={cfg.get('api_type')}, "
              f"api_url={cfg.get('api_url')}, model={cfg.get('model_name')})")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Kies de LLM-aanbieder (nieuwe rij in llm_config).")
    p.add_argument("opdracht", choices=[*PROVIDERS, "status", "beschikbaar", "herstel"],
                   help="aanbieder, of status/beschikbaar/herstel")
    p.add_argument("--json", action="store_true", help="uitvoer als JSON (voor scripts)")
    p.add_argument("--api-type", help="alleen bij herstel")
    p.add_argument("--api-url", help="alleen bij herstel")
    p.add_argument("--model", help="alleen bij herstel")
    a = p.parse_args(argv)

    if a.opdracht == "beschikbaar":
        aliassen = gateway_aliassen()
        uit = {naam: beschikbaarheid(naam, aliassen) for naam in PROVIDERS}
        if a.json:
            print(json.dumps(uit, ensure_ascii=False))
        else:
            for naam, b in uit.items():
                print(f"{naam:14} {'ja ' if b['beschikbaar'] else 'nee'}  {b['reden']}")
        return 0

    conn = get_db_connection()
    try:
        if a.opdracht == "status":
            toon(actieve_config(conn), a.json)
            return 0

        if a.opdracht == "herstel":
            if not (a.api_type and a.api_url and a.model):
                p.error("herstel vraagt --api-type, --api-url en --model")
            toon(zet_config(conn, a.api_type, a.api_url, a.model), a.json)
            return 0

        b = beschikbaarheid(a.opdracht)
        if not b["beschikbaar"]:
            if a.json:
                print(json.dumps({"fout": b["reden"], "provider": a.opdracht}, ensure_ascii=False))
            else:
                print(f"Geweigerd: {a.opdracht}: {b['reden']}", file=sys.stderr)
            return 2
        cfg = zet_config(conn, *config_voor(a.opdracht))
        toon(cfg, a.json)
        if not a.json and a.opdracht in ("claude", "openai", "gemini"):
            print("Let op: vragen, kaartcontext en indicatorwaarden gaan nu naar een externe aanbieder (AVG/IAMA).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
