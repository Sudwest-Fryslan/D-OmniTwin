"""Eén configuratie voor losse scripts (#69): alleen .env met DATABASE_*.

omnitwin.scriptdb leest dezelfde variabelen als de applicatie, en geen script in ETL/,
scripts/, tools/ of init_data/ leest nog config.ini, db.ini of DB_*-variabelen."""

import re
from pathlib import Path

import pytest

from omnitwin import scriptdb

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_verbindingsparameters_uit_database_variabelen(monkeypatch):
    for naam, waarde in {"DATABASE_HOST": "db.test", "DATABASE_PORT": "6543", "DATABASE_NAME": "testdb",
                         "DATABASE_USER": "tester", "DATABASE_PASSWORD": "geheim",
                         "DATABASE_SSLMODE": "require"}.items():
        monkeypatch.setenv(naam, waarde)
    assert scriptdb.verbindingsparameters() == {
        "host": "db.test", "port": "6543", "dbname": "testdb",
        "user": "tester", "password": "geheim", "sslmode": "require",
    }


def test_oude_db_variabelen_tellen_niet(monkeypatch):
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.setenv("DB_HOST", "oud.test")
    assert scriptdb.verbindingsparameters()["host"] == "localhost"


def test_verbind_geeft_parameters_door(monkeypatch):
    gezien = {}
    psycopg2 = pytest.importorskip("psycopg2")
    monkeypatch.setattr(psycopg2, "connect", lambda **kw: gezien.update(kw) or "verbinding")
    monkeypatch.setenv("DATABASE_NAME", "testdb")
    assert scriptdb.verbind(connect_timeout=3) == "verbinding"
    assert gezien["dbname"] == "testdb" and gezien["connect_timeout"] == 3


OUDE_CONFIG = re.compile(
    r"config\.ini|db\.ini|configparser|(?:getenv|environ\.get)\(\s*['\"]DB_(?:HOST|PORT|NAME|USER|PASSWORD)['\"]"
)


def test_geen_script_leest_config_ini_of_db_variabelen():
    mappen = ["ETL", "scripts", "tools", "init_data"]
    fout = [
        f"{pad.relative_to(ROOT)}: {m.group(0)}"
        for map_ in mappen
        for pad in (ROOT / map_).rglob("*.py")
        for m in [OUDE_CONFIG.search(pad.read_text(encoding="utf-8", errors="ignore"))]
        if m
    ]
    assert not fout, f"Lees de database alleen uit .env (DATABASE_*, omnitwin.scriptdb): {fout}"
