"""
Integratietests voor security-headers en security.txt (Issue #121).

De headers komen uit de Traefik-middleware in deploy/traefik/dynamic.yml en
moeten op alle routes staan, ook op /api/data (PostgREST) en /api/geo
(pg_featureserv), die niet via FastAPI lopen.

Draaien tegen een draaiende stack, zoals tests/integration/test_sample_stack.py:

    docker run --rm --network d-omnitwin_default -v "$PWD":/app -w /app \
        -e OMNITWIN_BASE_URL=http://traefik \
        python:3.11-slim sh -c "pip install -q pytest requests \
        && pytest -m integration tests/integration/test_security_headers.py"
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 30

ROUTES = ["/", "/api/data/", "/api/geo/", "/health"]
# Viewer achter de login (#266): dan ook de headers op de weigering (302 voor de pagina, 401 voor de
# API's, ook via forwardAuth van Traefik). Geef dezelfde VIEWER_TOEGANG mee als de stack heeft.
DICHT = os.environ.get("VIEWER_TOEGANG", "open").strip().lower() not in ("", "open")


def _verwacht(pad):
    if not DICHT or pad == "/health":
        return 200
    return 302 if pad == "/" else 401


@pytest.fixture(scope="module", params=ROUTES)
def response(request):
    # Alleen de pagina als browser opvragen (redirect naar de login); PostgREST kent geen text/html (406)
    kop = {"Accept": "text/html"} if request.param == "/" else {}
    r = requests.get(f"{BASE_URL}{request.param}", headers=kop, timeout=TIMEOUT, allow_redirects=False)
    assert r.status_code == _verwacht(request.param), f"{request.param}: HTTP {r.status_code}"
    return r


def test_nosniff(response):
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_referrer_policy(response):
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_frame_options(response):
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_permissions_policy(response):
    pp = response.headers.get("Permissions-Policy", "")
    assert "camera=()" in pp and "geolocation=()" in pp


def test_csp(response):
    csp = response.headers.get("Content-Security-Policy", "")
    # Eén beleid (van Traefik), niet samengevoegd met dat van de backend
    assert csp.count("default-src") == 1, csp
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_geen_hsts_op_http(response):
    """HSTS hoort alleen op HTTPS; de standaardinstallatie draait op HTTP."""
    if BASE_URL.startswith("http://"):
        assert "Strict-Transport-Security" not in response.headers


# ── security.txt (RFC 9116) ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def security_txt():
    r = requests.get(f"{BASE_URL}/.well-known/security.txt", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/plain")
    velden = {}
    for regel in r.text.splitlines():
        if regel.startswith("#") or ":" not in regel:
            continue
        naam, waarde = regel.split(":", 1)
        velden.setdefault(naam.strip().lower(), []).append(waarde.strip())
    return velden


def test_security_txt_contact(security_txt):
    contacts = security_txt.get("contact", [])
    assert contacts, "Contact: ontbreekt"
    for c in contacts:
        assert c.startswith(("https://", "mailto:", "tel:")), c


def test_security_txt_expires(security_txt):
    expires = security_txt.get("expires", [])
    assert len(expires) == 1, "precies één Expires: verplicht"
    datum = datetime.fromisoformat(expires[0].replace("Z", "+00:00"))
    nu = datetime.now(timezone.utc)
    assert datum > nu + timedelta(days=30), f"Expires {datum} verloopt binnen 30 dagen: verlengen"
    assert datum < nu + timedelta(days=366), "Expires hooguit een jaar vooruit (RFC 9116)"
