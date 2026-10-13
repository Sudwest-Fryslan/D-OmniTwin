"""
Integratietests voor Keycloak (compose-profiel keycloak, #214).

Alleen als Keycloak via Traefik bereikbaar is (OMNITWIN_BASE_URL + /auth); anders
worden ze overgeslagen. De CI start Keycloak niet standaard mee.

Het secret van de voorbeeld-machineclient etl-voorbeeld komt uit KEYCLOAK_ETL_SECRET,
of wordt opgevraagd via de admin-API met KEYCLOAK_ADMIN_PASSWORD (uit .env). Zonder
beide wordt de tokentest overgeslagen.

    docker run --rm --network <project>_default -v "$PWD":/app -w /app --env-file .env \
        -e OMNITWIN_BASE_URL=http://traefik \
        python:3.11-slim sh -c "pip install -q pytest requests \
        && pytest -m integration tests/integration/test_keycloak.py"
"""

import base64
import json
import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "omnitwin")
KC = f"{BASE_URL}/auth"
REALM_URL = f"{KC}/realms/{REALM}"
TIMEOUT = 30


@pytest.fixture(scope="module")
def discovery():
    try:
        r = requests.get(f"{REALM_URL}/.well-known/openid-configuration", timeout=TIMEOUT)
    except requests.RequestException as e:
        pytest.skip(f"Keycloak niet bereikbaar: {e}")
    if r.status_code != 200 or "json" not in r.headers.get("Content-Type", ""):
        pytest.skip(f"Keycloak niet actief (profiel keycloak): HTTP {r.status_code} op {r.url}")
    return r.json()


def _jwt_payload(token):
    deel = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(deel + "=" * (-len(deel) % 4)))


@pytest.fixture(scope="module")
def etl_secret(discovery):
    if os.environ.get("KEYCLOAK_ETL_SECRET"):
        return os.environ["KEYCLOAK_ETL_SECRET"]
    wachtwoord = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
    if not wachtwoord:
        pytest.skip("Geen KEYCLOAK_ETL_SECRET of KEYCLOAK_ADMIN_PASSWORD")
    r = requests.post(
        f"{KC}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": wachtwoord},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip(f"Tijdelijke beheerder admin kan niet inloggen (HTTP {r.status_code})")
    kop = {"Authorization": f"Bearer {r.json()['access_token']}"}
    clients = requests.get(
        f"{KC}/admin/realms/{REALM}/clients", params={"clientId": "etl-voorbeeld"}, headers=kop, timeout=TIMEOUT
    ).json()
    assert clients, "client etl-voorbeeld ontbreekt in de realm"
    r = requests.get(
        f"{KC}/admin/realms/{REALM}/clients/{clients[0]['id']}/client-secret", headers=kop, timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()["value"]


def test_discovery(discovery):
    assert discovery["issuer"].endswith(f"/auth/realms/{REALM}")
    assert "client_credentials" in discovery["grant_types_supported"]
    assert "S256" in discovery["code_challenge_methods_supported"]


def test_jwks(discovery):
    r = requests.get(f"{REALM_URL}/protocol/openid-connect/certs", timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(k.get("use") == "sig" for k in r.json()["keys"])


def test_client_credentials_token_met_rol(etl_secret):
    r = requests.post(
        f"{REALM_URL}/protocol/openid-connect/token",
        data={"grant_type": "client_credentials"},
        auth=("etl-voorbeeld", etl_secret),
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    antwoord = r.json()
    assert "refresh_token" not in antwoord
    assert antwoord["expires_in"] <= 600

    claims = _jwt_payload(antwoord["access_token"])
    assert claims["azp"] == "etl-voorbeeld"
    assert claims["iss"].endswith(f"/auth/realms/{REALM}")
    aud = claims["aud"] if isinstance(claims["aud"], list) else [claims["aud"]]
    assert "omnitwin-api" in aud
    rollen = claims.get("resource_access", {}).get("omnitwin-api", {}).get("roles", [])
    assert "dataset:voorbeeld:laden" in rollen
    assert "datasets:laden" not in rollen
    assert "beheerder" not in claims.get("realm_access", {}).get("roles", [])


def test_fout_secret_geweigerd(discovery):
    r = requests.post(
        f"{REALM_URL}/protocol/openid-connect/token",
        data={"grant_type": "client_credentials"},
        auth=("etl-voorbeeld", "fout"),
        timeout=TIMEOUT,
    )
    assert r.status_code == 401


def test_geen_password_grant(discovery):
    """Geen wachtwoord via de client (Resource Owner Password Credentials) op omnitwin-web."""
    r = requests.post(
        f"{REALM_URL}/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "omnitwin-web", "username": "x", "password": "y"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (400, 401)
    assert r.json().get("error") in ("unauthorized_client", "invalid_client")


def test_loginpagina_headers(discovery):
    """Keycloak zet zelf de CSP (frames op eigen adres); Traefik zet de overige headers."""
    r = requests.get(
        f"{REALM_URL}/protocol/openid-connect/auth",
        params={
            "client_id": "omnitwin-web",
            "response_type": "code",
            "redirect_uri": "http://localhost/",
            "scope": "openid",
            "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            "code_challenge_method": "S256",
        },
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy", "")
    assert csp.count("frame-ancestors") == 1, csp
    assert "frame-ancestors 'self'" in csp
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
