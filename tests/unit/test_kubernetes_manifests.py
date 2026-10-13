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
    cm = next(
        d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch"
    )
    k8s = yaml.safe_load(cm["data"]["middlewares.yml"])
    assert k8s == compose


def test_traefik_routes_dekken_de_compose_routers():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose_routers = set(re.findall(r"traefik\.http\.routers\.([a-z0-9_-]+)\.rule", compose)) - {"keycloak"}
    cm = next(
        d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch"
    )
    routers = yaml.safe_load(cm["data"]["routes.yml"])["http"]["routers"]
    assert set(routers) == compose_routers
    for naam, r in routers.items():
        assert any(m in r["middlewares"] for m in ("security-headers", "keycloak-headers")), naam


def _compose_routers():
    """{router: {"rule", "service", "middlewares"}} uit de labels in docker-compose.yml."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    uit = {}
    for naam, veld, waarde in re.findall(
        r'"traefik\.http\.routers\.([a-z0-9_-]+)\.(rule|service|middlewares)=(.*)"$', compose, re.M
    ):
        uit.setdefault(naam, {})[veld] = waarde
    return uit


def test_traefik_routes_gelijk_aan_compose():
    """Zelfde regel, service en middlewares (zonder @file) als in docker-compose.yml (#408)."""
    cm = next(
        d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch"
    )
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
    cm = next(
        d for _, d in _alle_manifests() if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "traefik-dynamisch"
    )
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


# --- Voorbeeld van de Fleet-configrepo (#411) -------------------------------
# Het bouwen zelf (kustomize + kubeconform) doet scripts/ci/k8s-voorbeeld-configrepo.sh in de CI.

VOORBEELD = ROOT / "deploy" / "voorbeeld-configrepo" / "rancher" / "d-omnitwin"


def _voorbeeld():
    return yaml.safe_load((VOORBEELD / "kustomization.yaml").read_text(encoding="utf-8"))


def test_voorbeeld_fleet_en_namespace():
    fleet = yaml.safe_load((VOORBEELD / "fleet.yaml").read_text(encoding="utf-8"))
    k = _voorbeeld()
    assert fleet["defaultNamespace"] == k["namespace"] == "d-omnitwin"
    assert k["resources"] == ["base"], "Fleet haalt geen remote bases op: gevendorde kopie in base/"
    assert not (VOORBEELD / "base").exists(), "de base wordt gevendord in de configrepo, niet hier"


def test_voorbeeld_een_versie_voor_images_en_remote_base():
    k = _voorbeeld()
    tags = {i["name"]: i["newTag"] for i in k["images"]}
    assert set(tags) == {"sudwestfryslan/d-omnitwin", "sudwestfryslan/d-omnitwin-web", "sudwestfryslan/d-omnitwin-db"}
    assert len(set(tags.values())) == 1
    tekst = (VOORBEELD / "kustomization.yaml").read_text(encoding="utf-8")
    refs = re.findall(r"github\.com/Sudwest-Fryslan/D-OmniTwin//deploy/kubernetes\?ref=v([0-9.]+)", tekst)
    assert refs and set(refs) == set(tags.values())


def test_voorbeeld_instellingen_bestaan():
    """Elke instelling in de configMapGenerator is een bekende variabele (.env.example) en merget met de base."""
    k = _voorbeeld()
    (gen,) = k["configMapGenerator"]
    assert gen["name"] == "omnitwin-config" and gen["behavior"] == "merge"
    assert gen["options"]["disableNameSuffixHash"] is True
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    for regel in gen["literals"]:
        naam = regel.split("=", 1)[0]
        assert re.search(rf"^#?\s*{naam}=", env, re.M), f"{naam} staat niet in .env.example"
        assert naam not in {"DATABASE_PASSWORD", "ADMIN_PASSWORD", "OIDC_CLIENT_SECRET", "LLM_API_KEY"}, (
            f"{naam} is geheim en hoort in de Secret"
        )


def test_voorbeeld_ingress_haproxy_cert_manager_twee_hosts():
    (patch,) = _docs(VOORBEELD / "ingress-patch.yaml")
    assert patch["spec"]["ingressClassName"] == "haproxy"
    assert "cert-manager.io/cluster-issuer" in patch["metadata"]["annotations"]
    hosts = [r["host"] for r in patch["spec"]["rules"]]
    assert len(hosts) == 2 and set(patch["spec"]["tls"][0]["hosts"]) == set(hosts)
    basis = next(d for _, d in _docs_van("70-ingress.yaml"))
    assert patch["metadata"]["name"] == basis["metadata"]["name"]
    assert patch["spec"]["tls"][0]["secretName"] == basis["spec"]["tls"][0]["secretName"]


def test_voorbeeld_zonder_interne_namen_of_geheimen():
    for pad in VOORBEELD.parent.parent.rglob("*"):
        if not pad.is_file():
            continue
        tekst = pad.read_text(encoding="utf-8")
        for host in re.findall(r"\b(?:[a-z0-9-]+\.)+(?:nl|com|org|intern|local)\b", tekst):
            assert host.endswith(
                (
                    ".example.nl",
                    ".example.org",
                    "example.intern",
                    "github.com",
                    "microsoftonline.com",
                    "svc.cluster.local",
                    "k8s.io",
                )
            ) or host in ("login.microsoftonline.com",), f"{pad.name}: {host}"
        # Geen GUID's (tenant- of client-ID's): alleen placeholders
        assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", tekst), pad.name
