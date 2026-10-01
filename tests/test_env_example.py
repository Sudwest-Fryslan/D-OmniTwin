"""
.env.example moet in de pas lopen met wat de app en de compose-bestanden lezen.

- Elke omgevingsvariabele die de app (main.py, src/, routers/, services/) of
  docker-compose*.yml gebruikt, staat in .env.example (ingevuld of als commentaar).
- .env.example noemt geen variabelen die nergens gebruikt worden.

Daarnaast docker-entrypoint.sh en de init-scripts die het aanroept.
Scripts in ETL/ en scripts/ vallen buiten deze toets (zie #69).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]

# Variabelen die Docker Compose zelf leest, of die alleen binnen containers bestaan.
COMPOSE_EIGEN = {"COMPOSE_FILE", "COMPOSE_PROJECT_NAME"}
NIET_VOOR_GEBRUIKER = {
    "POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "PYTHONDONTWRITEBYTECODE",
    # Gezet in de Dockerfile voor het offline embeddingmodel (#118), geen gebruikersinstelling
    "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "EMBEDDING_MODEL_PAD",
}

PY_ENV = re.compile(r"""os\.(?:getenv|environ\.get)\(\s*['"]([A-Z][A-Z0-9_]+)['"]|os\.environ\[\s*['"]([A-Z][A-Z0-9_]+)['"]""")
COMPOSE_ENV = re.compile(r"(?<!\$)\$\{([A-Z][A-Z0-9_]+)")
EXAMPLE_VAR = re.compile(r"^#?\s*([A-Z][A-Z0-9_]+)=", re.MULTILINE)


def gebruikt():
    namen = set()
    bestanden = [ROOT / "main.py", *(ROOT / "src").rglob("*.py"),
                 *(ROOT / "routers").glob("*.py"), *(ROOT / "services").glob("*.py")]
    for f in bestanden:
        for m in PY_ENV.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            namen.add(m.group(1) or m.group(2))
    # init (db-init): entrypoint + de scripts die het aanroept
    for f in [ROOT / "init_data/scripts/load_sample.py", ROOT / "init_data/scripts/create_admin.py"]:
        for m in PY_ENV.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            namen.add(m.group(1) or m.group(2))
    for f in [*ROOT.glob("docker-compose*.yml"), ROOT / "docker-entrypoint.sh"]:
        namen.update(COMPOSE_ENV.findall(f.read_text(encoding="utf-8")))
    return namen - NIET_VOOR_GEBRUIKER


def gedocumenteerd():
    return set(EXAMPLE_VAR.findall((ROOT / ".env.example").read_text(encoding="utf-8")))


def test_elke_gebruikte_variabele_staat_in_env_example():
    ontbreekt = sorted(gebruikt() - gedocumenteerd())
    assert not ontbreekt, f"Gebruikt in code/compose maar niet in .env.example: {ontbreekt}"


def test_env_example_bevat_geen_ongebruikte_variabelen():
    overbodig = sorted(gedocumenteerd() - gebruikt() - COMPOSE_EIGEN)
    assert not overbodig, f"In .env.example maar nergens gebruikt: {overbodig}"


def test_verplichte_waarde_heeft_geen_voorbeeldwaarde():
    """Placeholders als <jouw-wachtwoord> werken als echte waarde (#65); verplichte velden staan leeg."""
    tekst = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert not re.search(r"^[A-Z_]+=<", tekst, re.MULTILINE), "Geen <placeholder>-waarden in actieve regels"
