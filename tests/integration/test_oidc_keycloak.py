"""
Integratietest OIDC (#205): een echt token van Keycloak wordt door de backend geaccepteerd.

Vereist de stack met profiel keycloak en OIDC_ISSUER in .env (de issuer zoals die van buiten
in de tokens staat, bijv. http://localhost/auth/realms/omnitwin). Anders overgeslagen.

Secret van de voorbeeld-machineclient etl-voorbeeld: OIDC_TEST_CLIENT_SECRET (of
KEYCLOAK_ETL_SECRET); anders opgevraagd met
`docker compose exec keycloak bash /opt/keycloak/omnitwin/client-secret.sh etl-voorbeeld`.
Het secret en het token worden nooit geprint.

    OMNITWIN_BASE_URL=http://localhost pytest -m integration tests/integration/test_oidc_keycloak.py
"""

import base64
import json
import os
import shutil
import subprocess

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "omnitwin")
REALM_URL = f"{BASE_URL}/auth/realms/{REALM}"
IK = f"{BASE_URL}/api/oidc/ik"
TIMEOUT = 30


@pytest.fixture(scope="module")
def keycloak():
    try:
        r = requests.get(f"{REALM_URL}/.well-known/openid-configuration", timeout=TIMEOUT)
    except requests.RequestException as e:
        pytest.skip(f"Keycloak niet bereikbaar: {e}")
    if r.status_code != 200 or "json" not in r.headers.get("Content-Type", ""):
        pytest.skip(f"Keycloak niet actief (profiel keycloak): HTTP {r.status_code}")
    r = requests.get(IK, timeout=TIMEOUT)
    if r.status_code == 503:
        pytest.skip("OIDC_ISSUER niet ingesteld in de backend")
    return r


def _secret():
    for naam in ("OIDC_TEST_CLIENT_SECRET", "KEYCLOAK_ETL_SECRET"):
        if os.environ.get(naam):
            return os.environ[naam]
    if shutil.which("docker"):
        p = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "keycloak",
                "bash",
                "/opt/keycloak/omnitwin/client-secret.sh",
                "etl-voorbeeld",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip().splitlines()[-1]
    pytest.skip("Geen secret voor etl-voorbeeld (OIDC_TEST_CLIENT_SECRET)")


@pytest.fixture(scope="module")
def token(keycloak):
    r = requests.post(
        f"{REALM_URL}/protocol/openid-connect/token",
        data={"grant_type": "client_credentials"},
        auth=("etl-voorbeeld", _secret()),
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"token ophalen: HTTP {r.status_code}"
    token = r.json()["access_token"]
    deel = token.split(".")[1]
    iss = json.loads(base64.urlsafe_b64decode(deel + "=" * (-len(deel) % 4)))["iss"]
    verwacht = os.environ.get("OIDC_ISSUER", "").rstrip("/")
    if verwacht and iss != verwacht:
        pytest.skip(f"Token via een ander adres opgehaald (iss {iss}) dan OIDC_ISSUER ({verwacht})")
    return token


def test_zonder_token_401(keycloak):
    assert keycloak.status_code == 401
    assert keycloak.headers["Content-Type"].startswith("application/problem+json")
    assert keycloak.headers["WWW-Authenticate"].startswith("Bearer")
    assert keycloak.json()["code"] == "niet-geauthenticeerd"


def test_token_van_keycloak_geaccepteerd(token):
    r = requests.get(IK, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    ik = r.json()
    assert ik["client_id"] == "etl-voorbeeld"
    assert "dataset:voorbeeld:laden" in ik["rollen"]
    assert "datasets:laden" not in ik["rollen"] and "beheerder" not in ik["rollen"]
    assert set(ik) == {"client_id", "rollen"}  # geen sub of andere claims


def test_gewijzigd_token_geweigerd(token):
    kop, inhoud, handtekening = token.split(".")
    vervalst = f"{kop}.{inhoud}.{handtekening[:-4]}AAAA"
    r = requests.get(IK, headers={"Authorization": f"Bearer {vervalst}"}, timeout=TIMEOUT)
    assert r.status_code == 401
    assert r.json()["code"] == "niet-geauthenticeerd"
