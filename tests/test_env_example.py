"""
.env.example moet in de pas lopen met wat de app en de compose-bestanden lezen.

- Elke omgevingsvariabele die de app (src/omnitwin/: main, routers, services, ...) of
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
COMPOSE_EIGEN = {"COMPOSE_FILE", "COMPOSE_PROJECT_NAME", "COMPOSE_PROFILES"}
NIET_VOOR_GEBRUIKER = {
    "POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "PYTHONDONTWRITEBYTECODE",
    # Gezet in de Dockerfile voor het offline embeddingmodel (#118), geen gebruikersinstelling
    "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "EMBEDDING_MODEL_PAD",
    # Projectmap voor docker-entrypoint.sh; alleen gezet door init_database.sh (zonder Docker, #69)
    "APP_DIR",
}

PY_ENV = re.compile(r"""os\.(?:getenv|environ\.get)\(\s*['"]([A-Z][A-Z0-9_]+)['"]|os\.environ\[\s*['"]([A-Z][A-Z0-9_]+)['"]""")
COMPOSE_ENV = re.compile(r"(?<!\$)\$\{([A-Z][A-Z0-9_]+)")
EXAMPLE_VAR = re.compile(r"^#?\s*([A-Z][A-Z0-9_]+)=", re.MULTILINE)


def gebruikt():
    namen = set()
    bestanden = [*(ROOT / "src").rglob("*.py")]  # pakket omnitwin: main, routers, services, ...
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


def _variabelen_in_installatiegids():
    """Variabelen in de tabel van sectie 2.2 van de installatiegids (#204)."""
    tekst = (ROOT / "docs/9-beheer/installatie.md").read_text(encoding="utf-8")
    sectie = tekst.split("### 2.2", 1)[1].split("\n### ", 1)[0]
    rijen = [r for r in sectie.splitlines() if r.startswith("| `")]
    return {naam for r in rijen for naam in re.findall(r"`([A-Z][A-Z0-9_]+)(?:=[^`]*)?`", r.split("|")[1])}


def test_installatiegids_noemt_alleen_variabelen_uit_env_example():
    onbekend = sorted(_variabelen_in_installatiegids() - gedocumenteerd())
    assert not onbekend, f"In installatie.md (2.2) maar niet in .env.example: {onbekend}"


def test_installatiegids_beschrijft_elke_variabele_uit_env_example():
    ontbreekt = sorted(gedocumenteerd() - _variabelen_in_installatiegids())
    assert not ontbreekt, f"In .env.example maar niet in de tabel van installatie.md (2.2): {ontbreekt}"
