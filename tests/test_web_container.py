"""Web-container (#408): de bestanden van de viewer en de beheeromgeving in een eigen nginx-image.

Controleert zonder Docker dat de nginx-config hetzelfde doet als de backend deed: cachebeleid gelijk aan
src/omnitwin/statisch.py, de CSP gelijk aan Traefik (deploy/traefik/dynamic.yml), de security-headers in
elke location met een eigen add_header, en dat de backend-image geen frontend meer meekrijgt.
Het gedrag op een draaiende stack: tests/integration/test_web_container_stack.py."""

import re
from pathlib import Path

import pytest

from omnitwin.statisch import ONVERANDERLIJK, cache_control

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "deploy" / "web"
CONF = (WEB / "default.conf").read_text(encoding="utf-8")
HEADERS = (WEB / "headers.conf").read_text(encoding="utf-8")


def _locations():
    """(regel, inhoud) per location-blok (geen geneste blokken in deze config)."""
    return re.findall(r'^\s*location ((?:"[^"]*"|[^{"])+?)\s*\{(.*?)^\s*\}', CONF, re.M | re.S)


def _onveranderlijk_regexen():
    uit = []
    for regel, inhoud in _locations():
        if "immutable" in inhoud:
            m = re.fullmatch(r'~\s+"([^"]+)"', regel)
            assert m, f"location met immutable zonder regex: {regel}"
            uit.append(re.compile(m.group(1)))
    return uit


@pytest.mark.parametrize(
    "uri",
    [
        "/static/vendor/d3@7.9.0/d3.min.js",
        "/static/vendor/maplibre-gl@3.6.2/maplibre-gl.css",
        "/static/vendor/inter@5.3.0/inter.css",
        "/static/admin-panel/assets/index-D_76-aSi.js",
        "/static/admin-panel/assets/index-B5kdNBqP.css",
        "/static/css/styles.css",
        "/static/css/themes/swf.css",
        "/static/images/beeldmerk.svg",
        "/static/js/app.js",
        "/static/vendor/README.md",
        "/static/admin-panel/index.html",
        "/static/admin-panel/manifest.json",
        "/static/help.html",
    ],
)
def test_cachebeleid_gelijk_aan_statisch_py(uri):
    lang = any(r.search(uri) for r in _onveranderlijk_regexen())
    assert lang == (cache_control(uri) == ONVERANDERLIJK), uri


def test_standaard_no_cache():
    server = CONF.split("location", 1)[0]
    assert 'add_header Cache-Control "no-cache" always;' in server


def test_elke_location_met_add_header_heeft_de_security_headers():
    """nginx erft add_header niet als een location er zelf een heeft."""
    for regel, inhoud in _locations():
        if "add_header" in inhoud:
            assert "include /etc/nginx/omnitwin/headers.conf;" in inhoud, regel


def test_security_headers_als_de_backend():
    for kop in (
        'X-Content-Type-Options "nosniff"',
        'X-Frame-Options "DENY"',
        'Referrer-Policy "strict-origin-when-cross-origin"',
        "Content-Security-Policy",
    ):
        assert f"add_header {kop}" in HEADERS, kop
    regels = [r for r in HEADERS.splitlines() if r.startswith("add_header")]
    assert regels and all(r.endswith(" always;") for r in regels)


def test_csp_gelijk_aan_traefik():
    yaml = pytest.importorskip("yaml")
    dynamic = yaml.safe_load((ROOT / "deploy" / "traefik" / "dynamic.yml").read_text(encoding="utf-8"))
    traefik = dynamic["http"]["middlewares"]["security-headers"]["headers"]["contentSecurityPolicy"]
    nginx = re.search(r'add_header Content-Security-Policy "([^"]+)"', HEADERS).group(1)
    assert nginx == traefik


def test_geen_toegangslog_met_ip_adressen():
    """Het standaardformaat van nginx bevat X-Forwarded-For: het IP-adres van de bezoeker (#264)."""
    assert re.search(r"^\s*access_log off;", CONF, re.M)


def test_rapport_redirect_en_spa():
    assert "return 307 /rapport$rest$is_args$args;" in CONF
    assert re.search(r'location ~ "\^/rapport\(/\.\*\)\?\$"', CONF)


def test_backend_image_zonder_frontend():
    regels = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for r in ("admin-panel", "static", "!static/css/themes", "!static/images"):
        assert r in regels, r
    # De web-image krijgt alleen static/ en de nginx-config
    web = [
        r
        for r in (ROOT / "web.Dockerfile.dockerignore").read_text(encoding="utf-8").splitlines()
        if r and not r.startswith("#")
    ]
    assert web == ["*", "!static", "!deploy/web"]


def test_web_image_zonder_root_en_vaste_versie():
    df = (ROOT / "web.Dockerfile").read_text(encoding="utf-8")
    basis = re.search(r"^FROM (\S+)", df, re.M).group(1)
    assert basis.startswith("nginxinc/nginx-unprivileged:") and re.search(r":\d+\.\d+\.\d+", basis), basis
    assert re.findall(r"^USER (\S+)", df, re.M)[-1] == "101"
