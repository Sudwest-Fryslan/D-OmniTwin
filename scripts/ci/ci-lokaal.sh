#!/usr/bin/env bash
# CI lokaal: test één branch met dezelfde stappen als .github/workflows/ci.yml
# (publiccode, unit 3.11/3.12, admin-panel, verse stack, integratie, browser-e2e).
# Werkt op Linux, macOS en Windows (Git Bash); nodig: git, docker (compose v2), curl, openssl.
#
# Gebruik:
#   scripts/ci/ci-lokaal.sh <branch> [projectnaam] [poort]
#   scripts/ci/ci-lokaal.sh feature/290-rapporten            # projectnaam ci-290, poort 8290
#   scripts/ci/ci-lokaal.sh feature/290-rapporten ci290b 8291  # tweede run ernaast
#
# De branch wordt van origin opgehaald en in een aparte worktree naast de repo getest
# (../ci-<projectnaam>); je eigen werkmap en .env blijven onaangeroerd. Meerdere runs
# tegelijk kan, mits elke run een eigen projectnaam en poort heeft (2-3 op een laptop).
# Log: ../ci-<projectnaam>.log. Aan het eind: RESULTAAT en de tijd per stap.
set -u

BRANCH=${1:?gebruik: ci-lokaal.sh <branch> [projectnaam] [poort]}
NR=$(printf '%s' "$BRANCH" | grep -oE '[0-9]+' | head -1)
PROJ=${2:-ci-${NR:-lokaal}}
PORT=${3:-$((8000 + ${NR:-80} % 1000))}

REPO=$(git rev-parse --show-toplevel) || exit 2
BASIS=$(dirname "$REPO")
WT="$BASIS/ci-$PROJ"
LOG="$BASIS/ci-$PROJ.log"
export MSYS_NO_PATHCONV=1   # Git Bash: paden in docker-argumenten niet omzetten

# Pad zoals Docker het wil zien (Git Bash: C:/..., elders gewoon pwd)
dockerpad() { if pwd -W >/dev/null 2>&1; then pwd -W; else pwd; fi; }
morgen() { date -d '+1 day' +%F 2>/dev/null || date -v+1d +%F; }

exec > >(tee "$LOG") 2>&1
echo "== CI lokaal $BRANCH (project $PROJ, poort $PORT) $(date '+%F %H:%M')"

TIJDEN=""
START=$SECONDS
stap() { # stap <naam>: sluit de vorige stap af en begint een nieuwe
  [ -n "${STAP:-}" ] && TIJDEN="$TIJDEN$(printf '  %-14s %4ss' "$STAP" $((SECONDS - STAP_START)))\n"
  STAP=${1:-}; STAP_START=$SECONDS; [ -n "$STAP" ] && echo "-- $STAP"
}

cd "$REPO" || exit 2
git fetch -q origin || { sleep 5; git fetch -q origin; } || true
git worktree remove --force "$WT" 2>/dev/null
[ -e "$WT" ] && { rm -rf "$WT" || { echo "map $WT is nog in gebruik (draait er nog een container?); kies een andere projectnaam"; exit 2; }; }
for _ in 1 2 3; do git worktree add -q --detach "$WT" "origin/$BRANCH" && break; sleep 5; done
git -C "$WT" rev-parse --verify -q HEAD >/dev/null || { echo "== RESULTAAT $BRANCH: WORKTREE_FAALT"; exit 2; }
cd "$WT" || exit 2
echo "commit: $(git rev-parse --short HEAD)"
W=$(dockerpad)

export COMPOSE_PROJECT_NAME=$PROJ OMNITWIN_HTTP_PORT=$PORT
cp .env.example .env
set_env() { if grep -Eq "^#? ?$1=" .env; then sed -i.bak -E "s|^#? ?$1=.*|$1=$2|" .env && rm -f .env.bak; else echo "$1=$2" >> .env; fi; }
set_env COMPOSE_FILE docker-compose.yml
set_env DATABASE_PASSWORD "$(openssl rand -hex 16)"
set_env DATABASE_SSLMODE prefer
set_env ADMIN_API_KEY "$(openssl rand -hex 32)"
set_env ADMIN_PASSWORD "$(openssl rand -hex 16)"
set_env LOAD_SAMPLE_DATA true
set_env OMNITWIN_HTTP_PORT "$PORT"

RESULT=OK
UNIT_UIT=$(mktemp)

stap publiccode
docker run --rm -v "$W":/data italia/publiccode-parser-go:v5.4.3 -no-network /data/publiccode.yml || RESULT=PUBLICCODE_FAALT

for v in 3.11 3.12; do
  stap "unit $v"
  docker run --rm -v "$W":/app -w /app -e PYTHONDONTWRITEBYTECODE=1 "python:$v-slim" sh -c \
    "pip install -q --root-user-action=ignore -r requirements-ci.txt && pip install -q --root-user-action=ignore -e . --no-deps && pytest -p no:cacheprovider -m unit -q --tb=short 2>&1 | tail -3" | tee "$UNIT_UIT"
  { grep -q " passed" "$UNIT_UIT" && ! grep -q " failed\| error" "$UNIT_UIT"; } || RESULT=UNIT_FAALT
done

stap admin-panel
docker run --rm -v "$W":/app -w /app/admin-panel node:24 sh -c \
  "npm ci --no-audit --no-fund >/dev/null && npm run -s typecheck && npm run -s lint && npm test --silent 2>&1 | grep -E 'Tests|failed' && npm run -s build:static >/dev/null" || RESULT=ADMIN_FAALT
# De gecommitte build moet gelijk zijn aan een Linux-build (bouw zelf dus ook in node:24)
git add -A static/admin-panel
a=$(git diff --cached --name-only -- static/admin-panel | head -5)
[ -n "$a" ] && { echo "$a"; echo "static/admin-panel wijkt af: bouw met 'docker run --rm -v \$PWD:/app -w /app/admin-panel node:24 sh -c \"npm ci && npm run build:static\"'"; RESULT=ADMIN_BUILD_NIET_ACTUEEL; }

stap stack
docker compose up -d --build --wait --wait-timeout 900 || RESULT=STACK_FAALT

if [ "$RESULT" = OK ]; then
  for _ in $(seq 1 60); do curl -fsS "http://localhost:$PORT/health" >/dev/null && break; sleep 2; done
  # Zoals de CI: AI-usecase C (zoeken op betekenis) vrijgeven met een testverklaring
  if grep -q "usecases/C/verklaring" .github/workflows/ci.yml; then
    printf '%%PDF-1.4\n%% testverklaring CI\n%%%%EOF\n' > ci-verklaring.pdf
    KEY=$(grep -E '^ADMIN_API_KEY=' .env | cut -d= -f2-)
    curl -fsS -H "X-Admin-Key: $KEY" -F "bestand=@ci-verklaring.pdf;type=application/pdf" -F versie=ci \
      -F geldig_tot="$(morgen)" "http://localhost:$PORT/api/admin/ai/usecases/C/verklaring" >/dev/null \
      && echo "-- AI-usecase C vrijgegeven (testverklaring)" || RESULT=VRIJGAVE_C_FAALT
    rm -f ci-verklaring.pdf
  fi

  stap integratie
  docker run --rm --network "${PROJ}_default" -v "$W":/app -w /app --env-file .env \
    -e DATABASE_HOST=postgres -e DATABASE_PORT=5432 -e OMNITWIN_BASE_URL=http://traefik -e PYTHONDONTWRITEBYTECODE=1 \
    python:3.11-slim sh -c "pip install -q --root-user-action=ignore pytest requests psycopg2-binary python-dotenv sqlalchemy bcrypt pyyaml && pytest -p no:cacheprovider -m integration tests/integration" \
    || RESULT=INTEGRATIE_FAALT

  stap e2e
  for pad in / /health /api/data/gebiedstypes "/api/ai/kompas/search?q=groen"; do curl -s -o /dev/null --max-time 120 "http://localhost:$PORT$pad"; done
  docker run --rm --network "${PROJ}_default" -v "$W":/work -w /work -e OMNITWIN_BASE_URL=http://traefik -e PYTHONDONTWRITEBYTECODE=1 \
    -e E2E_EXPECT_TIMEOUT_MS=45000 -e E2E_TIMEOUT_MS=90000 \
    mcr.microsoft.com/playwright/python:v1.63.0-noble sh -c "pip install -q --root-user-action=ignore -r tests/e2e/requirements.txt && pytest -p no:cacheprovider -m e2e tests/e2e -rs" \
    || { [ "$RESULT" = OK ] && RESULT=E2E_FAALT; }
fi

stap opruimen
[ "$RESULT" = OK ] || docker compose logs --no-color --tail 80 backend db-init
docker compose down -v --remove-orphans >/dev/null 2>&1
rm -f "$UNIT_UIT"
cd "$REPO" && git worktree remove --force "$WT"
stap

echo "== Tijd per stap"
printf "%b" "$TIJDEN"
printf '  %-14s %4ss\n' totaal $((SECONDS - START))
echo "== RESULTAAT $BRANCH: $RESULT $(date '+%H:%M')"
[ "$RESULT" = OK ]
