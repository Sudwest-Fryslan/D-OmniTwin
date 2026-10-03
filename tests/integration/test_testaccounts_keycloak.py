"""
Integratietest testaccounts (#223) tegen een draaiende stack met Keycloak (compose-profiel keycloak)
en de laad-API (OIDC_ISSUER gezet).

Maakt de actoren van use case swf-definities aan als testaccounts in realm omnitwin, controleert hun
tokens en rollen, voert de rechtencontroles uit het manifest uit (beheerder registreert, de ETL-client
alleen zijn eigen dataset, de lezer niets) en ruimt ze op. Er wordt niets geladen: de rechtencontroles
worden na de rolcontrole afgewezen. Overgeslagen zonder laad-API, zonder OMNITWIN_TESTACCOUNTS=1 of
zonder toegang tot de admin-API (KEYCLOAK_ADMIN_PASSWORD, of KEYCLOAK_ADMIN_CLIENT_ID/SECRET).

    OMNITWIN_BASE_URL=http://localhost OMNITWIN_TESTACCOUNTS=1 KEYCLOAK_ADMIN_PASSWORD=... \\
    OMNITWIN_TESTACCOUNTS_BESTAND=/tmp/accounts.json pytest -m integration tests/integration/test_testaccounts_keycloak.py
"""

import os

import pytest
import requests

from omnitwin import testaccounts as ta
from omnitwin import usecases as uc

pytestmark = pytest.mark.integration

NAAM = "swf-definities"

if not uc.laad_api_beschikbaar():
    pytest.skip(f"laad-API niet beschikbaar op {uc.basis_url()}", allow_module_level=True)
if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1" or os.environ.get("OMNITWIN_OMGEVING", "").lower() == "productie":
    pytest.skip("testaccounts niet toegestaan (OMNITWIN_TESTACCOUNTS=1, niet in productie)", allow_module_level=True)
if not (os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")):
    pytest.skip("geen toegang tot de admin-API van Keycloak", allow_module_level=True)


@pytest.fixture(scope="module")
def ucs():
    return uc.lees_usecases()


@pytest.fixture(scope="module")
def api(ucs):
    apis = uc.maak_actor_apis([NAAM], ucs)
    yield apis[NAAM]
    uc.opruimen([NAAM], ucs)


def ik(laad_api):
    r = laad_api.s.get(f"{laad_api.basis}/api/oidc/ik", timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_accounts_bestaan_met_de_juiste_rollen(api):
    assert set(api.accounts) == {"beheerder", "etl-swf", "lezer"}
    assert api.accounts["etl-swf"]["id"] == "uc-swf-definities-etl-swf"
    rollen = {naam: set(ik(api.actor(naam)).get("rollen", [])) for naam in api.accounts}
    assert "beheerder" in rollen["beheerder"]
    assert "dataset:swf-monitor-definities:laden" in rollen["etl-swf"]
    assert not rollen["etl-swf"] & {"beheerder", "datasets:laden"}
    assert "lezer" in rollen["lezer"] and not rollen["lezer"] & {"beheerder", "datasets:laden"}


@pytest.mark.parametrize("controle", [c for c in uc.lees_usecases()[NAAM]["controles"] if c["type"] == "recht"],
                         ids=lambda c: f"{c['actor']}-{c['actie']}-{c.get('dataset', '')}-{c['toegestaan']}")
def test_rechten(controle, api, ucs):
    assert uc.controle_api(controle, api, ucs[NAAM]) is None


def test_opruimen_verwijdert_de_accounts(ucs):
    apis = uc.maak_actor_apis([NAAM], ucs)
    etl = apis[NAAM].accounts["etl-swf"]
    url = uc.token_url()
    assert ta.token(etl, ta.loginclient(NAAM), url)
    weg = uc.opruimen([NAAM], ucs)[NAAM]
    assert sorted(weg) == ["uc-swf-definities--login", "uc-swf-definities-beheerder", "uc-swf-definities-etl-swf",
                           "uc-swf-definities-lezer"]
    r = requests.post(url, data={"grant_type": "client_credentials"}, auth=(etl["id"], etl["geheim"]), timeout=30)
    assert r.status_code in (400, 401)
    assert NAAM not in ta.lees()
