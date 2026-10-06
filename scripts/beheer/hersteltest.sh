#!/bin/sh
# Hersteltest: back-up maken, ALLES weggooien, herstellen en vergelijken
# (https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/257).
#
#   sh scripts/beheer/hersteltest.sh --wegwerp
#
# ALLEEN voor een test- of wegwerpstack: het script draait `docker compose down -v` en
# verwijdert dus de database en alle volumes van het project. Het weigert als
# COMPOSE_PROJECT_NAME leeg of `d-omnitwin` is. Verwacht een draaiende stack met data
# (bijvoorbeeld LOAD_SAMPLE_DATA=true), eventueel met het profiel keycloak.
#
# Stappen: aantallen en health vastleggen -> backup.sh -> down -v -> restore.sh ->
# up --wait -> aantallen, health, inloggen en (met Keycloak) de realm opnieuw controleren.
# Exitcode 0 = hersteltest geslaagd.
set -eu

# Git Bash: alleen docker zonder padomzetting (curl moet /dev/null wel omgezet krijgen)
docker() { MSYS_NO_PATHCONV=1 command docker "$@"; }

fout() { echo "HERSTELTEST MISLUKT: $*" >&2; exit 1; }
stap() { echo; echo "######## $*"; }

[ "${1:-}" = "--wegwerp" ] || fout "dit script gooit de stack weg; start het met --wegwerp."

cd "$(dirname "$0")/../.."
[ -f .env ] || fout ".env niet gevonden."
env_waarde() { sed -n "s/^$1=//p" .env | tail -n 1 | tr -d '\r"'; }

PROJECT="${COMPOSE_PROJECT_NAME:-$(env_waarde COMPOSE_PROJECT_NAME)}"
case "$PROJECT" in
    ''|d-omnitwin) fout "zet een eigen COMPOSE_PROJECT_NAME voor de test (nu: '${PROJECT:-leeg}')." ;;
esac
POORT="${OMNITWIN_HTTP_PORT:-$(env_waarde OMNITWIN_HTTP_PORT)}"
POORT="${POORT:-80}"
BASIS="http://localhost:$POORT"

psql_waarde() {
    docker compose exec -T postgres sh -c 'psql -X -At -U "$POSTGRES_USER" -d "${2:-$POSTGRES_DB}" -c "$1"' sh "$@" | tr -d '\r'
}
KEYCLOAK="$(psql_waarde "SELECT count(*) FROM pg_database WHERE datname = 'keycloak'")"

meting() {
    for t in gebieden gebied_data indicatoren users schema_migraties laden.leveringen laden.versies organisatie; do
        echo "$t=$(psql_waarde "SELECT count(*) FROM $t")"
    done
    echo "bestanden_leveringen=$(docker compose exec -T backend sh -c 'find /leveringen -type f | wc -l' | tr -d '\r ')"
    echo "bestanden_uploads=$(docker compose exec -T backend sh -c 'find /app/data-upload -type f | wc -l' | tr -d '\r ')"
    if [ "$KEYCLOAK" = "1" ]; then
        echo "keycloak_realms=$(psql_waarde "SELECT count(*) FROM realm" keycloak)"
        echo "keycloak_clients=$(psql_waarde "SELECT count(*) FROM client" keycloak)"
        echo "keycloak_gebruikers=$(psql_waarde "SELECT count(*) FROM user_entity" keycloak)"
    fi
}

controle_http() {
    for _ in $(seq 1 60); do
        curl -fsS "$BASIS/health" >/dev/null 2>&1 && break
        sleep 2
    done
    curl -fsS "$BASIS/health" >/dev/null || fout "/health antwoordt niet"
    echo "health: ok"
    code="$(curl -s -o /dev/null -w '%{http_code}' "$BASIS/api/geo/collections")"
    [ "$code" = 200 ] || fout "/api/geo/collections gaf $code"
    echo "geo-api: ok"
    code="$(curl -s -o /dev/null -w '%{http_code}' "$BASIS/api/data/gebiedstypes")"
    [ "$code" = 200 ] || fout "/api/data/gebiedstypes gaf $code"
    echo "data-api: ok"
    ADMIN_USER_W="$(env_waarde ADMIN_USER)"
    ADMIN_PASSWORD_W="$(env_waarde ADMIN_PASSWORD)"
    if [ -n "$ADMIN_PASSWORD_W" ]; then
        # Wachtwoord via stdin (niet in de proceslijst of de uitvoer)
        code="$(printf 'username=%s&password=%s' "${ADMIN_USER_W:-admin}" "$ADMIN_PASSWORD_W" \
            | curl -s -o /dev/null -w '%{http_code}' --data-binary @- \
              -H 'Content-Type: application/x-www-form-urlencoded' "$BASIS/api/admin/auth/login")"
        [ "$code" = 200 ] || fout "inloggen als beheerder gaf $code"
        echo "inloggen beheerder: ok"
    fi
    if [ "$KEYCLOAK" = "1" ]; then
        for _ in $(seq 1 60); do
            curl -fsS "$BASIS/auth/realms/omnitwin/.well-known/openid-configuration" >/dev/null 2>&1 && break
            sleep 3
        done
        curl -fsS "$BASIS/auth/realms/omnitwin/.well-known/openid-configuration" >/dev/null \
            || fout "Keycloak-realm omnitwin niet bereikbaar"
        echo "keycloak realm omnitwin: ok"
    fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

stap "1. Voor de back-up ($PROJECT, $BASIS)"
controle_http
meting > "$TMP/voor.txt"
cat "$TMP/voor.txt"
[ "$(sed -n 's/^gebied_data=//p' "$TMP/voor.txt")" -gt 0 ] || fout "geen data in gebied_data; laad eerst data (LOAD_SAMPLE_DATA=true)."

stap "2. Back-up"
sh scripts/beheer/backup.sh | tee "$TMP/backup.log"
MAP="$(sed -n 's/^Back-up klaar: //p' "$TMP/backup.log")"
[ -d "$MAP" ] || fout "back-upmap niet gevonden"

stap "3. Alles weg: docker compose down -v"
docker compose down -v
[ -z "$(docker volume ls -q --filter "name=^${PROJECT}_pgdata$")" ] || fout "volume pgdata bestaat nog"
echo "volumes verwijderd"

stap "4. Herstel in een lege installatie"
sh scripts/beheer/restore.sh "$MAP"

stap "5. Stack healthy?"
docker compose up -d --wait --wait-timeout 600
controle_http

stap "6. Vergelijken"
meting > "$TMP/na.txt"
if diff "$TMP/voor.txt" "$TMP/na.txt"; then
    cat "$TMP/na.txt"
    echo
    echo "HERSTELTEST GESLAAGD (back-up: $MAP)"
else
    fout "aantallen na herstel wijken af (links voor, rechts na)"
fi
