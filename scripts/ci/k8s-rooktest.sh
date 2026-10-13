#!/usr/bin/env bash
# Kubernetes-rooktest (#406): rolt deploy/kubernetes uit op een tijdelijk kind-cluster in Docker
# en controleert dat D-OmniTwin werkt. Lokaal en in de CI (.github/workflows/k8s-rooktest.yml).
#
#   scripts/ci/k8s-rooktest.sh [clusternaam]
#
# Stappen: images bouwen (code van deze checkout) -> kind-cluster -> images laden -> manifests
# toepassen met fictieve, per run gegenereerde secrets -> wachten op db-init en de deployments ->
# /health, data-API en geo-API via de Traefik-gateway -> upgrade naspelen (nieuwe db-init-Job,
# backend opnieuw starten) -> nogmaals controleren -> bewijs schrijven -> cluster opruimen.
#
# Instellingen (omgeving):
#   K8S_ROOKTEST_TAG=rooktest    image-tag van de zelf gebouwde images
#   K8S_ROOKTEST_BOUWEN=ja       nee = de Docker Hub-images met de tag uit de manifests
#   K8S_ROOKTEST_BEWIJS=<pad>    bewijsbestand (standaard usecases/uitrol-kubernetes/bewijs/rooktest.json)
#   KIND_VERSIE=v0.27.0          versie van kind (wordt gedownload als kind ontbreekt)
# Vereist: Docker. Raakt geen andere containers of clusters aan.
set -euo pipefail

START=$(date +%s)
REPO=$(git rev-parse --show-toplevel)
cd "$REPO"
CLUSTER="${1:-omnitwin-rooktest-$$}"
TAG="${K8S_ROOKTEST_TAG:-rooktest}"
BOUWEN="${K8S_ROOKTEST_BOUWEN:-ja}"
BEWIJS="${K8S_ROOKTEST_BEWIJS:-usecases/uitrol-kubernetes/bewijs/rooktest.json}"
KIND_VERSIE="${KIND_VERSIE:-v0.27.0}"
NS=d-omnitwin
NODE="${CLUSTER}-control-plane"
# Git Bash: geen padconversie voor argumenten van docker (zoals /rooktest in de node)
dk() { MSYS_NO_PATHCONV=1 docker "$@"; }

stap() { echo; echo "── $(date +%H:%M:%S) $* ──"; }

# kind zoeken of downloaden (Linux, macOS, Windows/Git Bash)
KIND=$(command -v kind || true)
if [ -z "$KIND" ]; then
    os=$(uname -s | tr '[:upper:]' '[:lower:]'); arch=amd64; ext=""
    case "$(uname -m)" in aarch64|arm64) arch=arm64 ;; esac
    case "$os" in mingw*|msys*|cygwin*) os=windows; ext=.exe ;; esac
    KIND="${TMPDIR:-/tmp}/kind-${KIND_VERSIE}${ext}"
    if [ ! -x "$KIND" ]; then
        stap "kind $KIND_VERSIE downloaden"
        curl -fsSLo "$KIND" "https://kind.sigs.k8s.io/dl/${KIND_VERSIE}/kind-${os}-${arch}"
        chmod +x "$KIND"
    fi
fi

opruimen() {
    stap "Cluster $CLUSTER opruimen"
    "$KIND" delete cluster --name "$CLUSTER" >/dev/null 2>&1 || true
}
trap opruimen EXIT

k() { dk exec -i "$NODE" kubectl "$@"; }
geheim() { head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' | head -c 48; }

if [ "$BOUWEN" = "ja" ]; then
    stap "Images bouwen (tag $TAG)"
    docker build -q -t "sudwestfryslan/d-omnitwin:$TAG" .
    docker build -q -f db.Dockerfile -t "sudwestfryslan/d-omnitwin-db:$TAG" .
fi

stap "kind-cluster $CLUSTER maken"
"$KIND" create cluster --name "$CLUSTER" --wait 180s

if [ "$BOUWEN" = "ja" ]; then
    stap "Images in het cluster laden"
    "$KIND" load docker-image --name "$CLUSTER" "sudwestfryslan/d-omnitwin:$TAG" "sudwestfryslan/d-omnitwin-db:$TAG"
fi

stap "Manifests toepassen"
dk cp deploy/kubernetes "$NODE:/rooktest"
manifests=$(k kustomize /rooktest)
if [ "$BOUWEN" = "ja" ]; then
    # Alleen de image-tag van de eigen images vervangen; de manifests zelf blijven ongewijzigd
    manifests=$(echo "$manifests" | sed -E "s#(sudwestfryslan/d-omnitwin(-db)?):[0-9A-Za-z._-]+#\1:$TAG#")
fi
GEBRUIKTE_TAG=$(echo "$manifests" | grep -oE 'sudwestfryslan/d-omnitwin:[0-9A-Za-z._-]+' | head -1 | cut -d: -f2)
k apply -f /rooktest/00-namespace.yaml
# Fictieve test-secrets, per run nieuw; ze verlaten het tijdelijke cluster niet
k -n "$NS" create secret generic omnitwin-secrets \
    --from-literal=DATABASE_PASSWORD="$(geheim)" \
    --from-literal=ADMIN_PASSWORD="$(geheim)"
echo "$manifests" | k apply -f -

diagnose() {
    echo "❌ $1"
    k -n "$NS" get pods -o wide || true
    k -n "$NS" logs job/"$JOB" --all-containers --tail=80 || true
    k -n "$NS" logs deploy/backend --all-containers --tail=80 || true
    exit 1
}

wacht_klaar() {
    JOB=$1
    stap "Wachten op Job $JOB"
    k -n "$NS" wait --for=condition=complete "job/$JOB" --timeout=1200s || diagnose "Job $JOB niet klaar"
    for d in backend postgrest pg-featureserv traefik; do
        stap "Wachten op deployment $d"
        k -n "$NS" rollout status "deploy/$d" --timeout=600s || diagnose "deployment $d niet klaar"
    done
}

CONTROLES=()
controleer() {
    local pad=$1 verwacht=$2 code
    local ip; ip=$(k -n "$NS" get svc traefik -o jsonpath='{.spec.clusterIP}')
    code=$(dk exec "$NODE" curl -s -o /dev/null -w '%{http_code}' --max-time 30 "http://$ip$pad" || echo 000)
    echo "   $pad -> HTTP $code (verwacht $verwacht)"
    CONTROLES+=("{\"pad\": \"$pad\", \"http\": $code, \"verwacht\": $verwacht}")
    [ "$code" = "$verwacht" ] || diagnose "$pad gaf HTTP $code"
}

JOB=$(echo "$manifests" | awk '/^kind: Job/{j=1} j && /^  name:/{print $2; exit}')
wacht_klaar "$JOB"
stap "Controleren via de Traefik-gateway"
controleer /health 200
controleer /api/geo/collections 200
controleer /api/data/ 200

stap "Upgrade naspelen: nieuwe db-init-Job en backend opnieuw starten"
echo "$manifests" | sed "s/name: $JOB/name: ${JOB}-upgrade/" | k apply -f -
k -n "$NS" rollout restart deploy/backend
wacht_klaar "${JOB}-upgrade"
controleer /health 200

DUUR=$(( $(date +%s) - START ))
stap "Bewijs schrijven: $BEWIJS"
mkdir -p "$(dirname "$BEWIJS")"
{
    echo "{"
    echo "  \"usecase\": \"uitrol-kubernetes\","
    echo "  \"tijdstip\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"versie\": \"$(tr -d '\r\n' < VERSION)\","
    echo "  \"commit\": \"$(git rev-parse --short HEAD)\","
    echo "  \"image_tag\": \"$GEBRUIKTE_TAG\","
    echo "  \"zelf_gebouwd\": $([ "$BOUWEN" = "ja" ] && echo true || echo false),"
    echo "  \"kubernetes\": \"$(k version -o json 2>/dev/null | grep -m1 gitVersion | cut -d'"' -f4)\","
    echo "  \"stappen\": [\"manifests toepassen\", \"db-init\", \"deployments klaar\", \"endpoints\", \"upgrade\", \"endpoints na upgrade\"],"
    echo "  \"controles\": [$(IFS=,; echo "${CONTROLES[*]}")],"
    echo "  \"duur_seconden\": $DUUR,"
    echo "  \"resultaat\": \"geslaagd\""
    echo "}"
} > "$BEWIJS"
cat "$BEWIJS"
echo "✅ Kubernetes-rooktest geslaagd in ${DUUR}s"
