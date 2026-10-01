"""
Unit test: robuuste installatie (#201), zonder database.

- schema_latest.sql zet geen eigenaar of rechten voor een vaste rol (andere DATABASE_USER);
- create_admin.py maakt geen API-key en zet geen secrets in de log;
- docker-entrypoint.sh slikt een mislukte admin-aanmaak niet in en markeert de
  installatie pas als voltooid na de laatste verplichte stap;
- geüploade kaartlagen staan in een volume.
"""
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parent.parent


def sql_zonder_commentaar(pad: Path) -> str:
    return "\n".join(r for r in pad.read_text(encoding="utf-8").splitlines() if not r.lstrip().startswith("--"))


@pytest.mark.parametrize("naam", ["schema_latest.sql", "06_pg_featureserv_views.sql", "07_postgisftw_functions.sql"])
def test_schema_zonder_vaste_eigenaar(naam):
    sql = sql_zonder_commentaar(ROOT / "db" / "schema" / naam)
    assert "OWNER TO" not in sql
    assert "omnitwin_user" not in sql


def test_migraties_zonder_vaste_eigenaar():
    for pad in (ROOT / "db" / "migraties").glob("*.sql"):
        assert "omnitwin_user" not in sql_zonder_commentaar(pad), pad.name


def test_create_admin_zonder_api_key_in_log():
    code = (ROOT / "init_data" / "scripts" / "create_admin.py").read_text(encoding="utf-8")
    assert "plain_key" not in code and "ADMIN_API_KEY=" not in code
    assert "api_keys" not in code
    assert "token_hex" not in code


def test_entrypoint_slikt_admin_fout_niet_in():
    sh = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    regel = next(r for r in sh.splitlines() if "create_admin.py" in r and not r.lstrip().startswith(("#", "docker")))
    assert "||" not in regel, regel


def test_entrypoint_markeert_pas_na_de_rollen():
    sh = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    hoofd = sh[sh.index('if [ "$1" = "init" ]'):]
    assert hoofd.index("init_db") < hoofd.index("setup_api_rollen") < hoofd.index("markeer_voltooid")
    # schema in één transactie: een fout laat geen half schema achter
    assert re.search(r"--single-transaction -f /app/db/schema/schema_latest\.sql", sh)


def test_uploads_in_volume():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"^\s+- uploads:/app/data-upload\s*$", compose, re.MULTILINE)
    assert re.search(r"^volumes:\n(?:\s+.*\n)*?\s+uploads:", compose, re.MULTILINE)
