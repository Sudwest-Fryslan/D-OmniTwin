"""
Elke Traefik-router in de compose-bestanden heeft een headers-middleware (#214).

De security-headers (CSP, X-Frame-Options, nosniff, ...) staan niet meer op het
entrypoint maar per router, zodat Keycloak (/auth) eigen headers kan krijgen. Een
nieuwe router zonder security-headers@file of keycloak-headers@file zou zonder
die headers live gaan; deze test voorkomt dat.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [*ROOT.glob("docker-compose*.yml"), *ROOT.glob("deploy/traefik/*.yml")]
HEADERS = {"security-headers@file", "keycloak-headers@file"}

ROUTER = re.compile(r"traefik\.http\.routers\.([\w-]+)\.rule=")
MIDDLEWARES = re.compile(r"traefik\.http\.routers\.([\w-]+)\.middlewares=([^\"'\s]+)")


def _routers():
    routers, middlewares = set(), {}
    for f in COMPOSE:
        tekst = f.read_text(encoding="utf-8")
        routers.update(ROUTER.findall(tekst))
        for naam, lijst in MIDDLEWARES.findall(tekst):
            middlewares[naam] = set(lijst.split(","))
    return routers, middlewares


def test_er_zijn_routers():
    routers, _ = _routers()
    assert {"backend", "postgrest", "pg_featureserv", "keycloak"} <= routers


def test_elke_router_heeft_een_headers_middleware():
    routers, middlewares = _routers()
    zonder = sorted(r for r in routers if not middlewares.get(r, set()) & HEADERS)
    assert not zonder, f"Router(s) zonder security-headers@file of keycloak-headers@file: {zonder}"


def test_alleen_keycloak_krijgt_keycloak_headers():
    _, middlewares = _routers()
    met = sorted(r for r, m in middlewares.items() if "keycloak-headers@file" in m)
    assert met == ["keycloak"], met


def test_geen_headers_middleware_op_het_entrypoint():
    """Op het entrypoint zou hij de headers van Keycloak overschrijven."""
    for f in COMPOSE:
        assert "http.middlewares=security-headers" not in f.read_text(encoding="utf-8"), f.name
