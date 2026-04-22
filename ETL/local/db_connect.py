#!/usr/bin/env python3
"""
D-OmniTwin ETL — Gedeelde Database Connector
=============================================
Centraal hulpmodule voor alle standalone ETL scripts in ETL/local/.

Laad-volgorde voor database configuratie:
  1. Omgevingsvariabelen (DATABASE_HOST, DATABASE_NAME, etc.)
  2. .env bestand in project root (als aanwezig)
  3. ETL/local/db.ini (aanbevolen voor losse ETL runs)
  4. Fout + duidelijke uitleg als niets gevonden

Gebruik in een ander script:
    from db_connect import get_connection, get_etl_config

    conn = get_connection()
    cfg  = get_etl_config()
    gemeente_codes = cfg['gemeente_codes']
"""

import os
import sys
import configparser
from pathlib import Path

# ─── Paden ──────────────────────────────────────────────────────────────────
LOCAL_DIR   = Path(__file__).resolve().parent           # ETL/local/
ETL_DIR     = LOCAL_DIR.parent                          # ETL/
PROJECT_ROOT = ETL_DIR.parent                           # D-OmniTwin/

DB_INI_PATH  = LOCAL_DIR / "db.ini"
ENV_PATH     = PROJECT_ROOT / ".env"


# ─── Hulpfuncties ────────────────────────────────────────────────────────────

def _load_dotenv(path: Path) -> dict:
    """Laad key=value paren uit een .env bestand (zonder python-dotenv)."""
    env = {}
    if not path.exists():
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _load_ini(path: Path) -> configparser.ConfigParser:
    """Laad een .ini configuratiebestand."""
    cfg = configparser.ConfigParser()
    if path.exists():
        cfg.read(path, encoding="utf-8")
    return cfg


def get_connection(section: str = "DATABASE", verbose: bool = True):
    """
    Maak een psycopg2 database verbinding.

    Laadvolgorde: omgevingsvariabelen → .env → db.ini

    Args:
        section: Sectienaam in db.ini (standaard: DATABASE)
        verbose: Print verbindingsinformatie

    Returns:
        psycopg2 connection object

    Raises:
        SystemExit als verbinding mislukt of configuratie ontbreekt
    """
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 niet gevonden. Installeer met:")
        print("   pip install psycopg2-binary")
        sys.exit(1)

    # ── 1. Omgevingsvariabelen (hoogste prioriteit) ──
    params = {
        "host":     os.environ.get("DATABASE_HOST"),
        "port":     os.environ.get("DATABASE_PORT"),
        "dbname":   os.environ.get("DATABASE_NAME"),
        "user":     os.environ.get("DATABASE_USER"),
        "password": os.environ.get("DATABASE_PASSWORD"),
        "sslmode":  os.environ.get("DATABASE_SSLMODE"),
    }

    # ── 2. .env bestand (als omgevingsvariabelen ontbreken) ──
    if not all([params["host"], params["dbname"], params["user"]]):
        env = _load_dotenv(ENV_PATH)
        params["host"]     = params["host"]     or env.get("DATABASE_HOST")
        params["port"]     = params["port"]     or env.get("DATABASE_PORT")
        params["dbname"]   = params["dbname"]   or env.get("DATABASE_NAME")
        params["user"]     = params["user"]     or env.get("DATABASE_USER")
        params["password"] = params["password"] or env.get("DATABASE_PASSWORD")
        params["sslmode"]  = params["sslmode"]  or env.get("DATABASE_SSLMODE")

    # ── 3. db.ini (als bovenstaande nog steeds ontbreken) ──
    if not all([params["host"], params["dbname"], params["user"]]):
        ini = _load_ini(DB_INI_PATH)
        if ini.has_section(section):
            db = ini[section]
            params["host"]     = params["host"]     or db.get("host")
            params["port"]     = params["port"]     or db.get("port")
            params["dbname"]   = params["dbname"]   or db.get("dbname")
            params["user"]     = params["user"]     or db.get("user")
            params["password"] = params["password"] or db.get("password")
            params["sslmode"]  = params["sslmode"]  or db.get("sslmode", "prefer")
        elif DB_INI_PATH.exists():
            print(f"⚠️  Sectie [{section}] niet gevonden in {DB_INI_PATH}")

    # ── Valideer minimale vereisten ──
    missing = [k for k in ("host", "dbname", "user") if not params.get(k)]
    if missing:
        print("\n❌ Database configuratie incompleet.")
        print(f"   Ontbrekende velden: {', '.join(missing)}")
        print()
        print("   Oplossingen (kies één):")
        print(f"   A) Maak {DB_INI_PATH.name} aan:")
        print(f"      cp ETL/local/db.ini.example ETL/local/db.ini")
        print(f"      → vul de waarden in")
        print()
        print("   B) Stel omgevingsvariabelen in:")
        print("      export DATABASE_HOST=localhost")
        print("      export DATABASE_NAME=omnitwin_db")
        print("      export DATABASE_USER=omnitwin_user")
        print("      export DATABASE_PASSWORD=jouw_wachtwoord")
        print()
        print("   C) Zorg dat .env aanwezig is in de project root")
        sys.exit(1)

    # ── Bouw verbinding ──
    connect_params = {k: v for k, v in params.items() if v}
    connect_params.setdefault("port", "5432")

    if verbose:
        print(f"🔌 Verbinden met {connect_params['user']}@{connect_params['host']}:{connect_params.get('port', 5432)}/{connect_params['dbname']} ...")

    try:
        conn = psycopg2.connect(**connect_params)
        if verbose:
            print("✅ Database verbinding OK")
        return conn
    except Exception as e:
        print(f"\n❌ Database verbinding mislukt: {e}")
        print()
        print("   Controleer:")
        print("   • Is PostgreSQL actief? (systemctl status postgresql)")
        print("   • Klopt het wachtwoord in db.ini / .env?")
        print("   • Is de firewall open voor poort 5432?")
        sys.exit(1)


def get_etl_config() -> dict:
    """
    Laad ETL-specifieke configuratie (gemeente codes, output dir, etc.).

    Returns:
        Dictionary met ETL-instellingen
    """
    defaults = {
        "gemeente_codes": [],
        "output_dir": str(LOCAL_DIR / "output"),
        "default_jaar": 2023,
        "cbs_endpoint_public": "opendata.cbs.nl",
        "cbs_endpoint_derden": "dataderden.cbs.nl",
        "cbs_timeout": 60,
    }

    ini = _load_ini(DB_INI_PATH)

    if ini.has_section("ETL"):
        etl = ini["ETL"]
        codes_str = etl.get("gemeente_codes", "")
        defaults["gemeente_codes"] = [
            c.strip() for c in codes_str.split(",") if c.strip()
        ]
        defaults["output_dir"]   = etl.get("output_dir", defaults["output_dir"])
        defaults["default_jaar"] = int(etl.get("default_jaar", defaults["default_jaar"]))

    if ini.has_section("CBS"):
        cbs = ini["CBS"]
        defaults["cbs_endpoint_public"] = cbs.get("endpoint_public", defaults["cbs_endpoint_public"])
        defaults["cbs_endpoint_derden"] = cbs.get("endpoint_derden", defaults["cbs_endpoint_derden"])
        defaults["cbs_timeout"]         = int(cbs.get("timeout", defaults["cbs_timeout"]))

    return defaults


def test_connection():
    """Test de verbinding en toon database statistieken."""
    conn = get_connection()
    cur = conn.cursor()

    print("\n📊 Database Status:")
    print("─" * 50)

    checks = [
        ("PostgreSQL versie",    "SELECT version()"),
        ("Indicatoren",          "SELECT COUNT(*) FROM indicatoren"),
        ("Gebieden",             "SELECT COUNT(*) FROM gebieden"),
        ("Metingen (gebied_data)", "SELECT COUNT(*) FROM gebied_data"),
        ("Kompas mappings",      "SELECT COUNT(*) FROM kompas_indicator_mapping"),
        ("PostGIS actief",       "SELECT PostGIS_Version()"),
        ("pgvector actief",      "SELECT extversion FROM pg_extension WHERE extname='vector'"),
    ]

    for label, sql in checks:
        try:
            cur.execute(sql)
            result = cur.fetchone()[0]
            if "versie" in label.lower():
                # Alleen eerste deel van versie string
                result = str(result).split(",")[0]
            print(f"  {'✅':<4} {label:<28} {result}")
        except Exception as e:
            print(f"  {'❌':<4} {label:<28} FOUT: {e}")

    cur.close()
    conn.close()
    print("─" * 50)


if __name__ == "__main__":
    test_connection()
