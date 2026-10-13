"""Kubernetes-manifests (#406): wat kustomization.yaml noemt bestaat, één versie voor de eigen images,
geen :latest, de db-init-Job heeft de versie in de naam, de Secret-voorbeelden zijn leeg, en de
middlewares van de Traefik-gateway zijn gelijk aan deploy/traefik/dynamic.yml (compose).
De schemacheck doet kubeconform in de CI; de echte uitrol scripts/ci/k8s-rooktest.sh."""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
K8S = ROOT / "deploy" / "kubernetes"


def _docs(pad):
    return [d for d in yaml.safe_load_all(pad.read_text(encoding="utf-8")) if d]


def _alle_manifests():
    for pad in sorted(K8S.rglob("*.yaml")):
        if pad.name in ("kustomization.yaml", "fleet.yaml"):
            continue
        for d in _docs(pad):
            yield pad, d


def _containers(d):
    spec = d.get("spec", {})
    pod = spec.get("template", {}).get("spec", {})
    return pod.get("initContainers", []) + pod.get("containers", [])


def test_kustomization_noemt_bestaande_bestanden_en_niet_het_voorbeeld():
    for k in K8S.rglob("kustomization.yaml"):
        resources = yaml.safe_load(k.read_text(encoding="utf-8"))["resources"]
        for r in resources:
            assert (k.parent / r).exists(), f"{k}: {r} bestaat niet"
        assert "secret.example.yaml" not in resources


def test_alle_basisbestanden_staan_in_kustomization():
    resources = set(yaml.safe_load((K8S / "kustomization.yaml").read_text(encoding="utf-8"))["resources"])
    bestanden = {p.name for p in K8S.glob("[0-9]*.yaml")}
    assert bestanden == resources


def test_eigen_images_een_versie_en_geen_latest():
    tags = set()
    for pad, d in _alle_manifests():
        for c in _containers(d):
            assert not c["image"].endswith(":latest") and ":" in c["image"], f"{pad}: {c['image']}"
            if c["image"].startswith("sudwestfryslan/"):
                tags.add(c["image"].split(":")[1])
    assert len(tags) == 1, f"verschillende versies van de eigen images: {tags}"


def test_jobs_hebben_de_versie_in_de_naam():
    for pad, d in _alle_manifests():
        if d["kind"] == "Job":
            tag = _containers(d)[-1]["image"].split(":")[1]
            assert d["metadata"]["name"].endswith(tag.replace(".", "-")), f"{pad}: {d['metadata']['name']}"


def test_secret_voorbeeld_zonder_waarden():
    for d in _docs(K8S / "secret.example.yaml"):
        assert all(v == "" for v in d["stringData"].values())


def test_traefik_middlewares_gelijk_aan_compose():
    compose = yaml.safe_load((ROOT / "deploy" / "traefik" / "dynamic.yml").read_text(encoding="utf-8"))
    cm = next(d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch")
    k8s = yaml.safe_load(cm["data"]["middlewares.yml"])
    assert k8s == compose


def test_traefik_routes_dekken_de_compose_routers():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose_routers = set(re.findall(r"traefik\.http\.routers\.([a-z0-9_-]+)\.rule", compose)) - {"keycloak"}
    cm = next(d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch")
    routers = yaml.safe_load(cm["data"]["routes.yml"])["http"]["routers"]
    assert set(routers) == compose_routers
    for naam, r in routers.items():
        assert any(m in r["middlewares"] for m in ("security-headers", "keycloak-headers")), naam


def _compose_routers():
    """{router: {"rule", "service", "middlewares"}} uit de labels in docker-compose.yml."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    uit = {}
    for naam, veld, waarde in re.findall(
            r'"traefik\.http\.routers\.([a-z0-9_-]+)\.(rule|service|middlewares)=(.*)"$', compose, re.M):
        uit.setdefault(naam, {})[veld] = waarde
    return uit


def test_traefik_routes_gelijk_aan_compose():
    """Zelfde regel, service en middlewares (zonder @file) als in docker-compose.yml (#408)."""
    cm = next(d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch")
    routers = yaml.safe_load(cm["data"]["routes.yml"])["http"]["routers"]
    for naam, c in _compose_routers().items():
        if naam == "keycloak":
            continue
        r = routers[naam]
        assert r["rule"] == c["rule"], naam
        assert r["service"] == c["service"], naam
        assert r["middlewares"] == [m.removesuffix("@file") for m in c["middlewares"].split(",")], naam


def test_web_container_achter_de_gateway():
    """#408: alles wat geen andere router heeft gaat naar web; /rapport met de toegang van de viewer."""
    cm = next(d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch")
    routes = yaml.safe_load(cm["data"]["routes.yml"])["http"]
    assert routes["routers"]["web"]["rule"] == "PathPrefix(`/`)" and routes["routers"]["web"]["service"] == "web"
    assert "viewer-pagina" in routes["routers"]["rapport"]["middlewares"]
    assert routes["services"]["web"]["loadBalancer"]["servers"] == [{"url": "http://web:8080"}]
    deploy = next(d for _, d in _docs_van("45-web.yaml") if d["kind"] == "Deployment")
    c = _containers(deploy)[0]
    assert c["image"].startswith("sudwestfryslan/d-omnitwin-web:")
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert {"name": "tmp", "mountPath": "/tmp"} in c["volumeMounts"]
    assert "envFrom" not in c, "de web-image is generiek: geen ConfigMap of Secret"


def _docs_van(naam):
    return [(K8S / naam, d) for d in _docs(K8S / naam)]
