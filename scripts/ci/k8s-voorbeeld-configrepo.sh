#!/usr/bin/env bash
# Voorbeeld-configuratierepo (#411): de overlay in deploy/voorbeeld-configrepo bouwen met de base
# van deze checkout, en controleren met kubeconform. Lokaal en in de CI (ci.yml, kubernetes-manifests).
#
#   scripts/ci/k8s-voorbeeld-configrepo.sh maak <doelmap>   configrepo met gevendorde base in <doelmap>
#   scripts/ci/k8s-voorbeeld-configrepo.sh controleer       bouwen (kustomize) + kubeconform + inhoud
#
# De base wordt gevendord zoals README.md van het voorbeeld beschrijft (kustomization.yaml en de
# genummerde manifests uit deploy/kubernetes), alleen uit deze checkout in plaats van een release-tag.
# Vereist: Docker (kustomize en kubeconform als image). Laat niets achter.
set -euo pipefail

REPO=$(git rev-parse --show-toplevel)
cd "$REPO"
KUSTOMIZE_IMAGE="${KUSTOMIZE_IMAGE:-registry.k8s.io/kustomize/kustomize:v5.6.0}"
KUBECONFORM_IMAGE="${KUBECONFORM_IMAGE:-ghcr.io/yannh/kubeconform:v0.7.0}"
dk() { MSYS_NO_PATHCONV=1 docker "$@"; }
# Git Bash: Windows-pad voor docker cp
pad() { if command -v cygpath >/dev/null; then cygpath -w "$1"; else echo "$1"; fi; }

maak() {
    local doel=$1
    mkdir -p "$doel"
    cp -r deploy/voorbeeld-configrepo/. "$doel/"
    local base="$doel/rancher/d-omnitwin/base"
    rm -rf "$base" && mkdir -p "$base"
    cp deploy/kubernetes/kustomization.yaml deploy/kubernetes/[0-9]*.yaml "$base/"
}

controleer() {
    local tmp; tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' RETURN
    maak "$tmp/configrepo"
    local uit="$tmp/gebouwd.yaml"
    # docker cp in plaats van een volume: werkt ook vanuit Git Bash op Windows
    local c; c=$(dk create "$KUSTOMIZE_IMAGE" build /r/rancher/d-omnitwin)
    dk cp "$(pad "$tmp/configrepo")" "$c:/r" >/dev/null
    if ! dk start -a "$c" > "$uit"; then dk rm "$c" >/dev/null; echo "❌ kustomize build mislukt"; exit 1; fi
    dk rm "$c" >/dev/null
    echo "Gebouwd: $(grep -c '^kind:' "$uit") objecten"
    dk run --rm -i "$KUBECONFORM_IMAGE" -strict -summary - < "$uit"

    # Inhoud: wat het voorbeeld belooft
    fout() { echo "❌ $1"; exit 1; }
    grep -q '^kind: Namespace' "$uit" && fout "Namespace hoort niet in de bundle (Fleet maakt hem)"
    grep -q 'ingressClassName: haproxy' "$uit" || fout "ingressClassName haproxy ontbreekt"
    grep -q 'cert-manager.io/cluster-issuer:' "$uit" || fout "annotatie van cert-manager ontbreekt"
    grep -q 'nginx.ingress.kubernetes.io' "$uit" && fout "annotatie van ingress-nginx staat er nog"
    [ "$(grep -c -- '- host: ' "$uit")" = 2 ] || fout "verwacht twee hostnamen in de Ingress"
    grep -q 'OIDC_ISSUER: https://login.microsoftonline.com/' "$uit" || fout "OIDC_ISSUER van Entra ontbreekt"
    grep -q 'DATABASE_HOST: postgres' "$uit" || fout "ConfigMap niet samengevoegd met de base"
    grep -qE 'name: omnitwin-config-[a-z0-9]+$' "$uit" && fout "ConfigMap heeft een hash in de naam"
    grep -qE 'kind: Secret$' "$uit" && fout "er staat een Secret in de bundle"
    local tags
    tags=$(grep -oE 'image: sudwestfryslan/d-omnitwin(-db|-web)?:[^ ]+' "$uit" | cut -d: -f3 | sort -u)
    [ "$(echo "$tags" | wc -l)" = 1 ] || fout "verschillende tags van de eigen images: $tags"
    echo "✅ Voorbeeld-configrepo geldig (images: $tags)"
}

case "${1:-}" in
    maak) maak "${2:?doelmap ontbreekt}" ;;
    controleer) controleer ;;
    *) sed -n '2,10p' "$0"; exit 2 ;;
esac
