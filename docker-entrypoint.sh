#!/bin/bash
set -e

# ============================================================
# D-OmniTwin — Container Startup & Initialisatie
#
#   docker-entrypoint.sh init         eenmalige database-initialisatie, daarna stoppen
#                                     (de db-init-service in docker-compose.yml)
#   docker-entrypoint.sh keycloak-db  database en rol voor Keycloak aanmaken, daarna stoppen
#                                     (de keycloak-db-init-service, profiel keycloak, #214)
#   docker-entrypoint.sh <commando>   wacht op de database en start <commando>
#                                     (standaard uvicorn, zie CMD in het Dockerfile)
#
# De applicatie initialiseert de database niet zelf: zo draait de init één keer,
# ook bij meerdere backend-replicas. Los draaien zonder compose: eerst
# `docker run <image> init`, daarna `docker run <image>`.
# ============================================================

DB_HOST="${DATABASE_HOST:-postgres}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-omnitwin_db}"
DB_USER="${DATABASE_USER:-omnitwin_user}"
DB_PASS="${DATABASE_PASSWORD:-}"

export PGPASSWORD="$DB_PASS"

wait_for_db() {
    echo "   Database target: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    echo "⏳ Wachten op PostgreSQL database verbinding..."
    local max_retries=30 count=0
    until psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; do
        count=$((count + 1))
        if [ $count -ge $max_retries ]; then
            echo "❌ Kon na $max_retries seconden geen verbinding maken met PostgreSQL ($DB_HOST:$DB_PORT)."
            exit 1
        fi
        sleep 1
    done
    echo "✅ PostgreSQL is gereed voor verbindingen."
}

# Schemamigraties (#54): db/migraties/V<versie>__<naam>.sql. De runner past toe wat nog niet
# in de tabel schema_migraties staat, op volgorde, en registreert het. Bij een bestaande
# database zonder die tabel draaien alle migraties één keer opnieuw (ze zijn idempotent).
# Baseline: wat in db/migraties/baseline/ staat, zit al in db/schema/schema_latest.sql.
run_migrations() {
    PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGDATABASE="$DB_NAME" PGUSER="$DB_USER" python -m omnitwin.migraties
}

# psql met de gegevens uit .env; -X: geen psqlrc
db_psql() {
    psql -X -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

# Eén waarde opvragen (leeg bij een fout)
db_waarde() {
    db_psql -tAc "$1" 2>/dev/null || true
}

# Init-status (#201). Een eerste initialisatie bestaat uit veel stappen (schema, migraties,
# stuurdata, use cases, beheerder, rollen). Pas als die allemaal gelukt zijn, krijgt de tabel
# installatie_status een rij (markeer_voltooid). Zo is een half mislukte init te herkennen.
#   voltooid      rij in installatie_status
#   leeg          geen eigen tabellen in public (alleen die van extensies zoals PostGIS)
#   oud-compleet  van vóór 0.2.1, zonder installatie_status, maar met gebieden en een beheerder
#   half          wel tabellen, geen markering en geen beheerder: eerdere init niet afgemaakt
db_toestand() {
    if [ "$(db_waarde "SELECT to_regclass('public.installatie_status') IS NOT NULL")" = "t" ] \
        && [ "$(db_waarde "SELECT count(*) > 0 FROM public.installatie_status")" = "t" ]; then
        echo voltooid; return
    fi
    local tabellen
    tabellen=$(db_waarde "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                          AND d.objid = c.oid AND d.deptype = 'e')")
    if [ "$tabellen" = "0" ]; then
        echo leeg; return
    fi
    if [ "$(db_waarde "SELECT to_regclass('public.gebieden') IS NOT NULL AND to_regclass('public.users') IS NOT NULL")" = "t" ] \
        && [ "$(db_waarde "SELECT EXISTS (SELECT 1 FROM public.users WHERE is_admin)")" = "t" ]; then
        echo oud-compleet; return
    fi
    echo half
}

markeer_voltooid() {
    local versie
    versie=$(tr -d '\r\n' < /app/VERSION 2>/dev/null || echo onbekend)  # VERSION kan CRLF hebben (Windows)
    db_psql -v ON_ERROR_STOP=1 -q -v versie="$versie" -v hoe="$1" >/dev/null <<'SQL'
SET client_min_messages = warning;
CREATE TABLE IF NOT EXISTS public.installatie_status (
    id          boolean     PRIMARY KEY DEFAULT true CHECK (id),  -- hooguit één rij
    voltooid_op timestamptz NOT NULL DEFAULT now(),
    versie      text        NOT NULL,
    hoe         text        NOT NULL
);
COMMENT ON TABLE public.installatie_status IS
    'Eerste initialisatie voltooid (docker-entrypoint.sh, #201). Zonder rij weigert db-init een database met tabellen.';
INSERT INTO public.installatie_status (versie, hoe) VALUES (:'versie', :'hoe') ON CONFLICT (id) DO NOTHING;
SQL
}

fout_half_geinitialiseerd() {
    cat >&2 <<'EOF'
❌ De database is half geïnitialiseerd: er staan tabellen in, maar een eerdere eerste
   initialisatie is niet afgemaakt (geen rij in installatie_status en geen beheerder).
   db-init stopt, zodat de stack niet start met een onvolledige database.

   Oorzaak: zie de log van de eerste mislukte run (docker compose logs db-init).
   Herstel bij een nieuwe installatie (wist de database en de andere volumes van dit project):
     docker compose down -v
     docker compose up -d --build
   Alleen de database wissen: docker compose down, docker volume rm <project>_pgdata
   (docker volume ls toont de naam), en weer docker compose up -d.

   Bestaande installatie met data die je wilt houden, en ontbreekt alleen de beheerder?
   Maak die aan en start opnieuw:
     docker compose run --rm db-init python /app/init_data/scripts/create_admin.py
EOF
    exit 1
}

init_db() {
    case "$(db_toestand)" in
        voltooid)
            echo "✅ Bestaande database gevonden (installatie voltooid). Initialisatie overgeslagen."
            echo "⚙️ Migraties controleren..."
            run_migrations
            return
            ;;
        oud-compleet)
            echo "✅ Bestaande database van vóór 0.2.1 gevonden (gebieden en beheerder aanwezig). Initialisatie overgeslagen."
            INIT_HOE="bestaande installatie herkend"
            echo "⚙️ Migraties controleren..."
            run_migrations
            return
            ;;
        half)
            fout_half_geinitialiseerd
            ;;
    esac

    INIT_HOE="nieuwe installatie"
    echo "⚙️ Database is leeg. Initialiseren via schema_latest.sql..."
    # ON_ERROR_STOP en één transactie per bestand: bij een fout blijft er van dat bestand niets staan
    db_psql -q -v ON_ERROR_STOP=1 --single-transaction -f /app/db/schema/schema_latest.sql >/dev/null
    # Views voor pg_featureserv (vw_gebieden_features, gebruikt door de kaart) staan niet in schema_latest.sql
    db_psql -q -v ON_ERROR_STOP=1 --single-transaction -f /app/db/schema/06_pg_featureserv_views.sql >/dev/null
    # SQL-functies die pg_featureserv publiceert onder /api/geo/functions (schema postgisftw)
    db_psql -q -v ON_ERROR_STOP=1 --single-transaction -f /app/db/schema/07_postgisftw_functions.sql >/dev/null
    run_migrations
    echo "✅ Database schema succesvol aangemaakt."

    # Altijd: het product zonder data (stuurdata, indicatordefinities, Kompas)
    python /app/init_data/scripts/load_sample.py --stap definities
    echo "✅ Stuurdata en definities ingeladen."

    # Data komt uit de use cases (usecases/<naam>/): gebieden, waarden en inrichting per use case
    LOAD_SAMPLE="${LOAD_SAMPLE_DATA:-true}"
    if [ "$LOAD_SAMPLE" = "true" ] || [ "$LOAD_SAMPLE" = "1" ]; then
        echo "🌱 LOAD_SAMPLE_DATA is actief: alle use cases inladen..."
        python /app/init_data/scripts/laad_usecase.py --alle
        # CBS Kerncijfers 2019-nu (alle jaargangen, voor trends) voor de gebieden die nu in de
        # database staan; gedownload bij CBS met cache in $DATA_CACHE (volume bron-cache). Heel Fryslân: seed_fryslan.py
        python /app/init_data/scripts/laad_cbs.py
        echo "✅ Use cases ingeladen."
    else
        echo "⚙️ LOAD_SAMPLE_DATA niet actief: geen data, alleen het product."
    fi

    # Admin gebruiker initialiseren
    export ADMIN_USER="${ADMIN_USER:-admin}"
    # Geen standaardwachtwoord: zonder (ingevuld) ADMIN_PASSWORD eenmalig een willekeurig wachtwoord genereren
    case "${ADMIN_PASSWORD:-}" in
        ""|"<"*">")
            export ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(16))')"
            echo "⚠️ ADMIN_PASSWORD niet ingesteld. Gegenereerd wachtwoord voor '$ADMIN_USER' (eenmalig getoond):"
            echo "   $ADMIN_PASSWORD"
            ;;
        *)
            export ADMIN_PASSWORD
            ;;
    esac
    echo "👤 Admin gebruiker controleren/aanmaken ('$ADMIN_USER')..."
    # Mislukt dit, dan stopt de init (set -e): zonder beheerder is de installatie niet af
    python /app/init_data/scripts/create_admin.py

    # PostgREST schema cache herladen via NOTIFY
    db_psql -c "NOTIFY pgrst, 'reload schema';" >/dev/null 2>&1 || true
}

# De eigen organisatie van deze instantie (#231, ADR 0007): naam, gemeentecode(s), logo's,
# contact. Bij elke start, ook bij een bestaande database, maar alleen als de tabel
# organisatie nog leeg is: een eigen inrichting wordt nooit overschreven.
seed_organisatie() {
    db_psql -v ON_ERROR_STOP=1 -q -f /app/db/stuurdata/organisatie.sql >/dev/null
    echo "✅ Organisatie: $(db_waarde "SELECT naam FROM public.organisatie")"
}

# Rollen en schema api voor PostgREST en pg_featureserv (#57). Draait bij elke start, ook bij
# een bestaande database: zonder deze rollen kunnen PostgREST en pg_featureserv niet verbinden.
# Idempotent. De LOGIN-rollen authenticator (PostgREST) en featureserv (pg_featureserv) krijgen
# DATABASE_PASSWORD als wachtwoord: geen extra variabele in .env. Die containers kregen dat
# wachtwoord al; de rollen zelf hebben geen rechten op de tabellen.
setup_api_rollen() {
    echo "🔐 Rollen en schema api voor PostgREST en pg_featureserv bijwerken..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q -f /app/db/migraties/R__api_rollen.sql >/dev/null
    # Wachtwoord via een psql-variabele (:'pw' quote het correct), niet in de SQL-bestanden
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q -v pw="$DB_PASS" >/dev/null <<'SQL'
ALTER ROLE authenticator PASSWORD :'pw';
ALTER ROLE featureserv PASSWORD :'pw';
SQL
    echo "✅ Rollen authenticator, web_anon en featureserv zijn bijgewerkt."
}

# Embeddings voor AI-zoeken en de chat (#139). Draait ook bij een bestaande database:
# het script vectoriseert alleen indicatoren zonder embedding en laadt het model alleen
# als er iets te doen is. Geen model of geen netwerk: waarschuwing, init gaat door.
generate_embeddings() {
    echo "🧠 Embeddings voor AI-zoeken genereren..."
    python /app/scripts/ai/genereer_embeddings.py || echo "⚠️ Embeddings niet gegenereerd: AI-zoeken en de chat vinden geen indicatoren. Later opnieuw: docker compose run --rm db-init (of python scripts/ai/genereer_embeddings.py)."
}

# Database en rol voor Keycloak (#214, compose-profiel keycloak). Zelfde PostgreSQL-server,
# eigen database `keycloak` met eigen rol `keycloak` (eigenaar); andere rollen kunnen er niet
# bij. Idempotent: zet het wachtwoord bij elke start opnieuw op KEYCLOAK_DB_PASSWORD.
setup_keycloak_db() {
    local kc_pass="${KEYCLOAK_DB_PASSWORD:-}"
    if [ -z "$kc_pass" ]; then
        echo "❌ KEYCLOAK_DB_PASSWORD is leeg. Zet het in .env (openssl rand -hex 24) en start opnieuw." >&2
        exit 1
    fi
    echo "🔐 Database en rol voor Keycloak bijwerken..."
    db_psql -v ON_ERROR_STOP=1 -q -v pw="$kc_pass" >/dev/null <<'SQL'
SET client_min_messages = warning;
SELECT 'CREATE ROLE keycloak LOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'keycloak')
\gexec
ALTER ROLE keycloak WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'pw';
SELECT 'CREATE DATABASE keycloak OWNER keycloak' WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'keycloak')
\gexec
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;
SQL
    echo "✅ Database keycloak en rol keycloak zijn bijgewerkt."
}

echo "============================================================"
echo "🌍 D-OmniTwin — Container Startup"
echo "============================================================"

wait_for_db

if [ "$1" = "init" ]; then
    INIT_HOE=""
    init_db
    seed_organisatie
    setup_api_rollen
    # Pas hier is de eerste initialisatie geslaagd; embeddings zijn optioneel (zie hierboven)
    if [ -n "$INIT_HOE" ]; then
        markeer_voltooid "$INIT_HOE"
        echo "✅ Installatie gemarkeerd als voltooid ($INIT_HOE)."
    fi
    generate_embeddings
    echo "✅ Initialisatie klaar."
    exit 0
fi

if [ "$1" = "keycloak-db" ]; then
    setup_keycloak_db
    exit 0
fi

echo "🚀 Start applicatie: $@"
exec "$@"
