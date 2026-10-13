"""Databaseverbinding voor losse scripts (ETL, tools, init_data), alleen uit `.env` (#69).

Zelfde variabelen en standaardwaarden als de applicatie (`omnitwin.config`):
DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD en
DATABASE_SSLMODE. Geen `config.ini`, `db.ini` of `DB_*`-variabelen meer.

Gebruik in een script buiten het pakket:

    sys.path.insert(0, str(Path(__file__).resolve().parents[N] / "src"))
    from omnitwin.scriptdb import verbind
"""
from __future__ import annotations

from typing import Any

from omnitwin.config import instellingen  # laadt ook .env uit de projectmap


def verbindingsparameters() -> dict[str, str]:
    """psycopg2-parameters uit de omgeving (.env)."""
    i = instellingen()
    return {
        "host": i.database_host,
        "port": i.database_port,
        "dbname": i.database_name,
        "user": i.database_user,
        "password": i.database_password,
        "sslmode": i.database_sslmode,
    }


def verbind(**extra: Any):
    """Open een psycopg2-verbinding met de gegevens uit .env."""
    import psycopg2

    return psycopg2.connect(**verbindingsparameters(), **extra)
