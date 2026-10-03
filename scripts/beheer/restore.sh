#!/bin/sh
# Herstel van een back-up van scripts/beheer/backup.sh (https://github.com/TLaan/D-OmniTwin/issues/257).
#
#   sh scripts/beheer/restore.sh backups/omnitwin-<project>-<stempel>
#   sh scripts/beheer/restore.sh <map> --overschrijf     # ook als er al data staat (die gaat weg)
#   sh scripts/beheer/restore.sh <map> --niet-starten    # na herstel de stack niet starten
#
# Bedoeld voor een lege installatie: dezelfde of een nieuwere versie van D-OmniTwin, een
# eigen .env (een ander DATABASE_PASSWORD mag, DATABASE_USER moet gelijk zijn aan die in
# de back-up). Volgorde:
#   1. controlesommen (SHA256SUMS) controleren;
#   2. postgres starten; weigeren als de database al data heeft (tenzij --overschrijf);
#   3. alle andere services stoppen;
#   4. rollen aanmaken (zonder wachtwoorden; db-init en keycloak-db-init zetten die);
#   5. database (en zo nodig keycloak) opnieuw aanmaken en terugzetten met pg_restore;
#   6. de volumes leveringen en uploads leegmaken en terugzetten;
#   7. docker compose up -d: db-init ziet een bestaande database, laat de data staan,
#      past openstaande migraties toe en zet de rollen en wachtwoorden opnieuw.
# Uitleg: docs/9-beheer/beheerhandleiding.md.
set -eu

MSYS_NO_PATHCONV=1
export MSYS_NO_PATHCONV

fout() { echo "FOUT: $*" >&2; exit 1; }
stap() { echo "== $*"; }

BRON=""
OVERSCHRIJF=nee
STARTEN=ja
for arg in "$@"; do
    case "$arg" in
        --overschrijf) OVERSCHRIJF=ja ;;
        --niet-starten) STARTEN=nee ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        -*) fout "onbekende optie $arg" ;;
        *) BRON="$arg" ;;
    esac
done
[ -n "$BRON" ] || fout "geef de map van de back-up op (zie --help)."
[ -d "$BRON" ] || fout "map $BRON bestaat niet."
BRON="$(cd "$BRON" && pwd)"

cd "$(dirname "$0")/../.."
[ -f docker-compose.yml ] || fout "docker-compose.yml niet gevonden."
[ -f .env ] || fout ".env niet gevonden; maak eerst een .env voor deze installatie."

sha256c() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum -c --quiet "$@"; else shasum -a 256 -c --quiet "$@"; fi
}

stap "Controlesommen"
[ -f "$BRON/SHA256SUMS" ] || fout "SHA256SUMS ontbreekt in $BRON."
for f in database.dump rollen.sql leveringen.tar.gz uploads.tar.gz info.txt; do
    [ -f "$BRON/$f" ] || fout "$f ontbreekt in $BRON."
done
( cd "$BRON" && sha256c SHA256SUMS ) || fout "controlesom klopt niet; de back-up is beschadigd."
echo "ok"

info() { sed -n "s/^$1=//p" "$BRON/info.txt" | tr -d '\r'; }
echo "Back-up van $(info datum), versie $(info versie), project $(info project)"

stap "Postgres starten"
docker compose up -d --wait postgres

pg() { docker compose exec -T postgres "$@"; }
psql_waarde() {
    pg sh -c 'psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$2" -c "$1"' sh "$1" "${2:-postgres}" | tr -d '\r'
}

EIGENAAR="$(pg sh -c 'echo "$POSTGRES_USER"' | tr -d '\r')"
DBNAAM="$(pg sh -c 'echo "$POSTGRES_DB"' | tr -d '\r')"
if [ "$(info database_eigenaar)" != "$EIGENAAR" ]; then
    fout "DATABASE_USER in .env ($EIGENAAR) wijkt af van de back-up ($(info database_eigenaar)). Zet hem gelijk en begin opnieuw met een lege installatie (docker compose down -v)."
fi

stap "Is de installatie leeg?"
HEEFT_DATA="$(psql_waarde "SELECT (to_regclass('public.gebieden') IS NOT NULL OR to_regclass('public.installatie_status') IS NOT NULL)::int" "$DBNAAM")"
if [ "$HEEFT_DATA" = "1" ] && [ "$OVERSCHRIJF" != ja ]; then
    fout "database $DBNAAM heeft al tabellen. Herstel in een lege installatie (docker compose down -v), of gebruik --overschrijf (de huidige data gaat dan weg)."
fi
if [ "$HEEFT_DATA" = "1" ]; then echo "niet leeg; wordt overschreven (--overschrijf)"; else echo "leeg"; fi

stap "Overige services stoppen"
# Geen verbindingen meer met de database tijdens het terugzetten
docker compose stop >/dev/null 2>&1 || true
docker compose up -d --wait postgres

stap "Rollen"
# Bestaande rollen (de eigenaar) geven een melding 'already exists'; dat is verwacht
pg sh -c 'psql -X -q -U "$POSTGRES_USER" -d postgres' < "$BRON/rollen.sql" 2>&1 \
    | grep -v 'already exists' || true

herstel_db() {  # $1 = databasenaam, $2 = eigenaar, $3 = dumpbestand
    pg sh -c 'dropdb -U "$POSTGRES_USER" --if-exists --force "$1" && createdb -U "$POSTGRES_USER" -T template0 -O "$2" "$1"' sh "$1" "$2"
    pg sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error' sh "$1" < "$3"
}

stap "Database $DBNAAM terugzetten"
# Verbinden met de database postgres; de doeldatabase wordt opnieuw aangemaakt (template0),
# zodat de extensies (PostGIS e.d.) uit de dump komen en niet botsen met die van de image
herstel_db "$DBNAAM" "$EIGENAAR" "$BRON/database.dump"

if [ -f "$BRON/keycloak.dump" ]; then
    stap "Database keycloak terugzetten"
    herstel_db keycloak keycloak "$BRON/keycloak.dump"
fi

volume_terug() {  # $1 = pad in de backend-container, $2 = tar.gz
    docker compose run --rm --no-deps -T --user root --entrypoint sh backend \
        -c 'find "$1" -mindepth 1 -delete && tar -xzf - -C "$1"' sh "$1" < "$2"
}
stap "Volume leveringen terugzetten"
volume_terug /leveringen "$BRON/leveringen.tar.gz"
stap "Volume uploads terugzetten"
volume_terug /app/data-upload "$BRON/uploads.tar.gz"

stap "Controle"
for t in gebieden gebied_data indicatoren users; do
    nu="$(psql_waarde "SELECT count(*) FROM $t" "$DBNAAM")"
    was="$(info "aantal_$t")"
    printf '%-12s back-up %-8s hersteld %s\n' "$t" "$was" "$nu"
    [ "$nu" = "$was" ] || fout "aantal in $t wijkt af."
done

if [ "$STARTEN" = ja ]; then
    stap "Stack starten (db-init past openstaande migraties toe en zet de rollen)"
    docker compose up -d
    echo "Controleer met: docker compose ps -a   en   curl http://localhost:<OMNITWIN_HTTP_PORT>/health"
else
    echo "Niet gestart (--niet-starten). Start met: docker compose up -d"
fi
echo "Herstel klaar."
