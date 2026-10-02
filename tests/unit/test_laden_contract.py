"""
Contracttest laad-API (#205): de router en docs/api/laden/openapi.yaml dekken dezelfde paden en
methoden (behalve /compat/*, stap 9), en de responses zonder database voldoen aan de schema's.

De responses met database toetst tests/integration/test_laden_api.py tegen dezelfde schema's.
"""

import re

import pytest

pytestmark = pytest.mark.unit

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("jwt")  # omnitwin.oidc (laad-API stap 5)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from omnitwin.laden.registratie import valideer  # noqa: E402
from omnitwin.routers import laden  # noqa: E402

METHODEN = {"get", "post", "put", "patch", "delete"}


def _norm(pad: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", pad)


def spec_operaties():
    spec = laden.specificatie()
    return {(m.upper(), _norm(p)) for p, item in spec["paths"].items() if not p.startswith("/compat/")
            for m in item if m in METHODEN}


def router_operaties():
    uit = set()
    for r in laden.router.routes:
        for m in r.methods - {"HEAD", "OPTIONS"}:
            uit.add((m, _norm(r.path[len(laden.PREFIX):])))
    return uit


def test_router_en_spec_hebben_dezelfde_operaties():
    spec, router = spec_operaties(), router_operaties()
    assert spec - router == set(), f"in de spec, niet in de router: {sorted(spec - router)}"
    assert router - spec == set(), f"in de router, niet in de spec: {sorted(router - spec)}"


def test_padparameter_heet_dataset_id():
    """oidc.vereis_rol vult {dataset_id} in uit de path-parameter dataset_id."""
    for r in laden.router.routes:
        if "dataset" in r.path and "{" in r.path and "/leveringen/{" not in r.path:
            assert "{dataset_id}" in r.path, r.path


@pytest.fixture
def client():
    app = FastAPI()
    from omnitwin.fouten import registreer_foutafhandeling
    registreer_foutafhandeling(app)
    laden.registreer(app)
    return TestClient(app)  # zonder context: geen startup (verwerker, database)


def schema(naam):
    spec = laden.specificatie()
    return spec["components"]["schemas"][naam], spec


def test_openapi_json_is_de_spec_als_json(client):
    r = client.get("/api/laden/v1/openapi.json")
    assert r.status_code == 200
    assert r.json()["openapi"].startswith("3.0")
    assert r.json()["paths"].keys() == laden.specificatie()["paths"].keys()
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["api-version"] == laden.specificatie()["info"]["version"]


def test_profielen_volgens_schema(client):
    r = client.get("/api/laden/v1/profielen")
    assert r.status_code == 200 and r.headers["api-version"]
    s, spec = schema("Profiel")
    for p in r.json()["profielen"]:
        assert valideer(p, s, spec) == []
    assert {p["id"] for p in r.json()["profielen"]} == {"waarnemingen", "definities", "gebiedsindeling", "kaartlaag"}
    r = client.get("/api/laden/v1/profielen/waarnemingen")
    assert valideer(r.json(), s, spec) == []
    assert "waarnemingen" in r.json()["tableSchemas"]


def test_onbekend_profiel_is_probleem_404(client):
    r = client.get("/api/laden/v1/profielen/bestaat-niet")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["api-version"]
    s, spec = schema("Probleem")
    assert valideer(r.json(), s, spec) == []
    assert r.json()["code"] == "niet-gevonden"


def test_zonder_token_401_als_probleem(client):
    r = client.get("/api/laden/v1/datasets")
    assert r.status_code in (401, 503)  # 503: OIDC niet ingesteld (vereis_rol)
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["api-version"]


def test_onbekend_pad_onder_prefix_is_probleem(client):
    r = client.get("/api/laden/v1/bestaat-niet")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["api-version"]


def test_merge_patch():
    doel = {"a": 1, "b": {"c": 2, "d": 3}}
    assert laden.merge_patch(doel, {"b": {"c": None, "e": 4}, "f": 5}) == {"a": 1, "b": {"d": 3, "e": 4}, "f": 5}
    assert doel == {"a": 1, "b": {"c": 2, "d": 3}}


def test_content_digest():
    import base64
    import hashlib
    h = hashlib.sha256(b"abc").digest()
    assert laden._digest_klopt(f"sha-256=:{base64.b64encode(h).decode()}:", h.hex())
    assert not laden._digest_klopt(f"sha-256=:{base64.b64encode(b'x' * 32).decode()}:", h.hex())
    assert laden._digest_klopt("sha-512=:abc:", h.hex())  # alleen sha-256 wordt gecontroleerd
