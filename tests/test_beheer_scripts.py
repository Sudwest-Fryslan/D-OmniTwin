"""
Back-up en herstel (#257): de beheerscripts blijven geldig en in de pas met docker-compose.yml.

De echte hersteltest (back-up, down -v, herstel, vergelijken) draait tegen een
wegwerpstack: scripts/beheer/hersteltest.sh --wegwerp (zie docs/9-beheer/beheerhandleiding.md).
Deze unittest controleert zonder Docker:
- de scripts zijn POSIX sh (sh -n) en hebben LF-regeleinden;
- de volumes en paden die ze gebruiken bestaan in docker-compose.yml;
- de hersteltest weigert zonder --wegwerp.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
BEHEER = ROOT / "scripts" / "beheer"
SCRIPTS = ["backup.sh", "restore.sh", "hersteltest.sh"]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


@pytest.mark.parametrize("naam", SCRIPTS)
def test_lf_en_posix_shebang(naam):
    data = (BEHEER / naam).read_bytes()
    assert b"\r\n" not in data, f"{naam} heeft CRLF; .gitattributes zet *.sh op LF"
    assert data.startswith(b"#!/bin/sh\n")
    assert b"set -eu" in data
    assert b"pipefail" not in data and b"[[" not in data, "geen bash-constructies"


@pytest.mark.skipif(not shutil.which("sh"), reason="geen sh beschikbaar")
@pytest.mark.parametrize("naam", SCRIPTS)
def test_syntax(naam):
    r = subprocess.run(["sh", "-n", str(BEHEER / naam)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_volumes_en_paden_bestaan_in_compose():
    for volume in ("pgdata", "leveringen", "uploads"):
        assert re.search(rf"^  {volume}:", COMPOSE, re.M), f"volume {volume} ontbreekt in docker-compose.yml"
    assert "leveringen:/leveringen" in COMPOSE
    assert "uploads:/app/data-upload" in COMPOSE
    backup = (BEHEER / "backup.sh").read_text(encoding="utf-8")
    restore = (BEHEER / "restore.sh").read_text(encoding="utf-8")
    for pad in ("/leveringen", "/app/data-upload"):
        assert pad in backup and pad in restore


def test_backup_en_restore_gebruiken_dezelfde_bestanden():
    backup = (BEHEER / "backup.sh").read_text(encoding="utf-8")
    restore = (BEHEER / "restore.sh").read_text(encoding="utf-8")
    for bestand in ("database.dump", "keycloak.dump", "rollen.sql", "leveringen.tar.gz",
                    "uploads.tar.gz", "info.txt", "SHA256SUMS"):
        assert bestand in backup and bestand in restore, bestand
    # Rollen zonder wachtwoorden; db-init en keycloak-db-init zetten ze opnieuw
    assert "--no-role-passwords" in backup


@pytest.mark.skipif(not shutil.which("sh"), reason="geen sh beschikbaar")
def test_hersteltest_weigert_zonder_wegwerp():
    r = subprocess.run(["sh", str(BEHEER / "hersteltest.sh")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0
    assert "--wegwerp" in r.stderr
