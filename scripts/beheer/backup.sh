#!/bin/sh
# Back-up van een D-OmniTwin-installatie (https://github.com/TLaan/D-OmniTwin/issues/257).
#
#   sh scripts/beheer/backup.sh            # in de map van de installatie (naast .env)
#
# Maakt een map <BACKUP_DIR>/omnitwin-<project>-<JJJJMMDD-UUMMSS>/ met:
#   database.dump      pg_dump -Fc van de database (DATABASE_NAME)
#   keycloak.dump      pg_dump -Fc van de database keycloak (alleen als die bestaat)
#   rollen.sql         de databaserollen, zonder wachtwoorden (pg_dumpall --roles-only)
#   leveringen.tar.gz  het volume leveringen (ruwe leveringen van de laad-API)
#   uploads.tar.gz     het volume uploads (geüploade kaartlagen)
#   info.txt           datum, versie, projectnaam, database-eigenaar en aantallen
#   SHA256SUMS         controlesommen van alle bestanden hierboven
#
# Daarna verwijdert hij back-ups van dit project die ouder zijn dan BACKUP_BEWAAR_DAGEN.
# Terugzetten: scripts/beheer/restore.sh. Uitleg: docs/9-beheer/beheerhandleiding.md.
#
# Instellingen (omgeving of .env):
#   BACKUP_DIR            doelmap (standaard ./backups, staat in .gitignore)
#   BACKUP_BEWAAR_DAGEN   bewaartermijn in dagen (standaard 30; 0 = niets verwijderen)
#
# Vereist: docker compose v2, een draaiende postgres-service en een gebouwde backend-image.
# Werkt met POSIX sh (Linux, macOS, Git Bash op Windows). Niet vanuit PowerShell omleiden.
set -eu

# Git Bash: paden in de argumenten voor de container niet omzetten naar Windows-paden
MSYS_NO_PATHCONV=1
export MSYS_NO_PATHCONV

cd "$(dirname "$0")/../.."

fout() { echo "FOUT: $*" >&2; exit 1; }
stap() { echo "== $*"; }

# Waarde uit .env, als die niet al in de omgeving staat
env_waarde() {
    eval "huidig=\${$1:-}"
    if [ -n "$huidig" ]; then echo "$huidig"; return; fi
    [ -f .env ] && sed -n "s/^$1=//p" .env | tail -n 1 | tr -d '\r"' || true
}

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi
}

[ -f docker-compose.yml ] || fout "docker-compose.yml niet gevonden; draai het script in een D-OmniTwin-map."
[ -f .env ] || fout ".env niet gevonden."

PROJECT="$(env_waarde COMPOSE_PROJECT_NAME)"
PROJECT="${PROJECT:-d-omnitwin}"
BACKUP_DIR="$(env_waarde BACKUP_DIR)"
BACKUP_DIR="${BACKUP_DIR:-backups}"
BEWAAR="$(env_waarde BACKUP_BEWAAR_DAGEN)"
BEWAAR="${BEWAAR:-30}"
case "$BEWAAR" in *[!0-9]*|'') fout "BACKUP_BEWAAR_DAGEN moet een geheel getal zijn." ;; esac

# Draait postgres?
docker compose exec -T postgres pg_isready -q >/dev/null 2>&1 \
    || fout "De service postgres draait niet (docker compose up -d postgres)."

psql_waarde() {
    docker compose exec -T postgres sh -c 'psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"' sh "$1" | tr -d '\r'
}

STEMPEL="$(date +%Y%m%d-%H%M%S)"
DOEL="$BACKUP_DIR/omnitwin-$PROJECT-$STEMPEL"
mkdir -p "$DOEL"
chmod 700 "$DOEL" 2>/dev/null || true
# Bij een fout geen halve back-up laten staan
trap 'if [ "${klaar:-}" != ja ]; then rm -rf "$DOEL"; echo "Back-up mislukt; $DOEL is verwijderd." >&2; fi' EXIT

stap "Database ($PROJECT)"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DOEL/database.dump"
# Leesbaar archief? (pg_restore --list leest de inhoudsopgave)
docker compose exec -T postgres pg_restore --list < "$DOEL/database.dump" > /dev/null \
    || fout "database.dump is geen leesbaar archief."

stap "Rollen (zonder wachtwoorden)"
docker compose exec -T postgres sh -c 'pg_dumpall -U "$POSTGRES_USER" --roles-only --no-role-passwords' > "$DOEL/rollen.sql"

KEYCLOAK=nee
if [ "$(psql_waarde "SELECT 1 FROM pg_database WHERE datname = 'keycloak'")" = "1" ]; then
    stap "Keycloak-database"
    docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d keycloak -Fc' > "$DOEL/keycloak.dump"
    docker compose exec -T postgres pg_restore --list < "$DOEL/keycloak.dump" > /dev/null \
        || fout "keycloak.dump is geen leesbaar archief."
    KEYCLOAK=ja
fi

# Volumes via de backend-image (die mount ze al); als root, zodat alles leesbaar is
volume_tar() {
    docker compose run --rm --no-deps -T --user root --entrypoint tar backend \
        -czf - -C "$1" . > "$2"
}
stap "Volume leveringen"
volume_tar /leveringen "$DOEL/leveringen.tar.gz"
stap "Volume uploads"
volume_tar /app/data-upload "$DOEL/uploads.tar.gz"

stap "Info en controlesommen"
{
    echo "datum=$(date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "versie=$(tr -d '\r\n' < VERSION 2>/dev/null || echo onbekend)"
    echo "project=$PROJECT"
    echo "database_eigenaar=$(docker compose exec -T postgres sh -c 'echo "$POSTGRES_USER"' | tr -d '\r')"
    echo "keycloak=$KEYCLOAK"
    echo "migratie=$(psql_waarde "SELECT max(versie) FROM schema_migraties" 2>/dev/null || echo onbekend)"
    echo "aantal_gebieden=$(psql_waarde "SELECT count(*) FROM gebieden")"
    echo "aantal_gebied_data=$(psql_waarde "SELECT count(*) FROM gebied_data")"
    echo "aantal_indicatoren=$(psql_waarde "SELECT count(*) FROM indicatoren")"
    echo "aantal_users=$(psql_waarde "SELECT count(*) FROM users")"
    echo "aantal_leveringen=$(psql_waarde "SELECT count(*) FROM laden.leveringen" 2>/dev/null || echo 0)"
} > "$DOEL/info.txt"
( cd "$DOEL" && sha256 ./*.dump ./*.sql ./*.tar.gz ./info.txt > SHA256SUMS )
chmod 600 "$DOEL"/* 2>/dev/null || true
klaar=ja

if [ "$BEWAAR" -gt 0 ]; then
    stap "Bewaartermijn: back-ups van $PROJECT ouder dan $BEWAAR dagen verwijderen"
    find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name "omnitwin-$PROJECT-*" -mtime +"$BEWAAR" \
        -print -exec rm -rf {} +
fi

echo "Back-up klaar: $DOEL"
du -sh "$DOEL" 2>/dev/null | cut -f1 | sed 's/^/Grootte: /'
