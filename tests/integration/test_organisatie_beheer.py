"""
Organisatie en thema instellen via de API (#253), tegen een draaiende stack.

- anoniem: 401 op PUT /api/organisatie, /themas, /logos, /export en /import; lezen blijft publiek;
- beheerder: 200 (thema's met voorbeeldkleuren, logo's), ongeldig thema of logo 422 zonder wijziging,
  export -> wijzigen -> import geeft de oorspronkelijke instelling terug;
- lezer (rol `lezer` in Keycloak): 403.

Beheerder = bearer-token van een testaccount met rol `beheerder` (Keycloak, OMNITWIN_TESTACCOUNTS=1 en
KEYCLOAK_ADMIN_PASSWORD, zoals test_beheer_keycloak.py), anders `X-Admin-Key` (ADMIN_API_KEY). De lezer
alleen met testaccounts; anders overgeslagen. De test zet de instelling na afloop terug (import van de
export van vóór de test).

    OMNITWIN_BASE_URL=http://localhost:8124 ADMIN_API_KEY=... pytest -m integration tests/integration/test_organisatie_beheer.py
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "omnitwin")
TIMEOUT = 30
UC = "organisatie-beheer"
ORG = f"{BASE_URL}/api/organisatie"

try:
    _CONFIG = requests.get(f"{BASE_URL}/api/admin/auth/config", timeout=TIMEOUT).json()
except (requests.RequestException, ValueError) as e:  # pragma: no cover - geen stack
    pytest.skip(f"stack niet bereikbaar: {e}", allow_module_level=True)


def _testaccounts_mogelijk() -> bool:
    return (bool(_CONFIG.get("oidc")) and os.environ.get("OMNITWIN_TESTACCOUNTS") == "1"
            and os.environ.get("OMNITWIN_OMGEVING", "").lower() != "productie"
            and bool(os.environ.get("KEYCLOAK_ADMIN_PASSWORD") or os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")))


@pytest.fixture(scope="module")
def accounts(tmp_path_factory):
    """Bearer-headers voor een beheerder en een lezer uit Keycloak, of None zonder testaccounts."""
    if not _testaccounts_mogelijk():
        yield None
        return
    from omnitwin import testaccounts as ta
    beheer = ta.KeycloakBeheer(kc=f"{BASE_URL}/auth", realm_=REALM)
    pad = tmp_path_factory.mktemp("accounts") / "accounts.json"
    uc = {"actoren": [{"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]},
                      {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}]}
    uit = ta.maak(UC, uc, beheer=beheer, pad=pad)
    url = f"{BASE_URL}/auth/realms/{REALM}/protocol/openid-connect/token"
    yield {naam: {"Authorization": f"Bearer {ta.token(uit[naam], ta.loginclient(UC), url)}"}
           for naam in ("beheerder", "lezer")}
    ta.opruimen(UC, beheer=beheer, pad=pad)


@pytest.fixture(scope="module")
def beheerder(accounts):
    if accounts:
        return accounts["beheerder"]
    key = os.environ.get("ADMIN_API_KEY", "")
    if len(key) < 32 or key.startswith("<"):
        pytest.skip("geen beheerder: testaccounts (Keycloak) of een geldige ADMIN_API_KEY nodig")
    return {"X-Admin-Key": key}


@pytest.fixture(scope="module")
def oorspronkelijk(beheerder):
    """De export van vóór de test; na afloop teruggezet."""
    r = requests.get(f"{ORG}/export", headers=beheerder, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    export = r.json()
    yield export
    terug = requests.post(f"{ORG}/import", json=export, headers=beheerder, timeout=TIMEOUT)
    assert terug.status_code == 200, terug.text[:300]


SCHRIJVEN = [
    ("PUT", "", {"code": "x", "naam": "x"}),
    ("GET", "/themas", None),
    ("GET", "/logos", None),
    ("GET", "/export", None),
    ("POST", "/import", {"formaat": "d-omnitwin/organisatie", "versie": 1, "organisatie": {}}),
]


@pytest.mark.parametrize("methode,pad,body", SCHRIJVEN)
def test_anoniem_401(methode, pad, body):
    r = requests.request(methode, f"{ORG}{pad}", json=body, timeout=TIMEOUT)
    assert r.status_code == 401, r.text[:200]


def test_lezen_blijft_publiek():
    assert requests.get(ORG, timeout=TIMEOUT).status_code == 200


@pytest.mark.parametrize("methode,pad,body", SCHRIJVEN)
def test_lezer_403(accounts, methode, pad, body):
    if not accounts:
        pytest.skip("lezer alleen met testaccounts in Keycloak (OMNITWIN_TESTACCOUNTS=1)")
    r = requests.request(methode, f"{ORG}{pad}", json=body, headers=accounts["lezer"], timeout=TIMEOUT)
    assert r.status_code == 403, r.text[:200]


def test_beheerder_themas_en_logos(beheerder):
    themas = requests.get(f"{ORG}/themas", headers=beheerder, timeout=TIMEOUT)
    assert themas.status_code == 200, themas.text[:300]
    namen = {t["naam"]: t for t in themas.json()}
    assert {"d-omnitwin", "swf"} <= set(namen)
    assert namen["swf"]["kleuren"]["licht"]["--d-omnitwin-header-background-color-start"] == "#2b2b2b"
    logos = requests.get(f"{ORG}/logos", headers=beheerder, timeout=TIMEOUT)
    assert logos.status_code == 200
    assert "/static/images/SWF-logo.png" in logos.json()


def test_beheerder_ongeldig_thema_422(beheerder, oorspronkelijk):
    voor = requests.get(ORG, timeout=TIMEOUT).json()
    for fout in ({"thema": "bestaat-niet"}, {"logos": [{"pad": "/static/images/../css/styles.css"}]},
                 {"contact_email": "geen-adres"}, {"gemeente_codes": ["GM1900"]}):
        r = requests.put(ORG, json={**oorspronkelijk["organisatie"], **fout}, headers=beheerder, timeout=TIMEOUT)
        assert r.status_code == 422, (fout, r.text[:300])
    assert requests.get(ORG, timeout=TIMEOUT).json() == voor


def test_beheerder_put_export_import_rondreis(beheerder, oorspronkelijk):
    org = oorspronkelijk["organisatie"]
    ander = "d-omnitwin" if org["thema"] != "d-omnitwin" else "swf"
    r = requests.put(ORG, json={**org, "thema": ander, "korte_naam": "Proef"}, headers=beheerder, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["thema"] == ander
    # De viewer laadt meteen het nieuwe themabestand (geen herstart nodig)
    assert f'/static/css/themes/{ander}.css' in requests.get(f"{BASE_URL}/", timeout=TIMEOUT).text

    r = requests.post(f"{ORG}/import", json=oorspronkelijk, headers=beheerder, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    na = requests.get(f"{ORG}/export", headers=beheerder, timeout=TIMEOUT).json()
    assert na["organisatie"] == org


def test_import_onbekend_formaat_422(beheerder, oorspronkelijk):
    r = requests.post(f"{ORG}/import", json={**oorspronkelijk, "formaat": "iets-anders"}, headers=beheerder,
                      timeout=TIMEOUT)
    assert r.status_code == 422
