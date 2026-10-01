#!/bin/bash
set -e

# ============================================================
# D-OmniTwin — Container Startup & Initialisatie
#
#   docker-entrypoint.sh init         eenmalige database-initialisatie, daarna stoppen
#                                     (de db-init-service in docker-compose.yml)
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

# Migraties die (nog) niet in schema_latest.sql zitten. Idempotent, dus ze draaien
# bij elke init, ook op een bestaande database. Structureel: migratiebeheer (#54)
run_migrations() {
    for m in schema_v18_trigram.sql schema_v19_deduplicatie_uitzonderingen.sql schema_v20_llm_api_type.sql schema_v22_auth_hardening.sql; do
        PGOPTIONS="-c client_min_messages=warning" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q -f "/app/migrations/$m" >/dev/null
    done
}

init_db() {
    # Controleer of het schema al bestaat
    TABLE_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='gebieden';" 2>/dev/null || true)

    if [ "$TABLE_EXISTS" = "1" ]; then
        echo "✅ Bestaande database gevonden (tabel 'gebieden' aanwezig). Initialisatie overgeslagen."
        echo "⚙️ Migraties controleren..."
        run_migrations
        return
    fi

    echo "⚙️ Database is leeg. Initialiseren via schema_latest.sql..."
    # ON_ERROR_STOP: stop bij de eerste SQL-fout in plaats van een half schema
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/schema_latest.sql >/dev/null
    # Views voor pg_featureserv (vw_gebieden_features, gebruikt door de kaart) staan niet in schema_latest.sql
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/06_pg_featureserv_views.sql >/dev/null
    # SQL-functies die pg_featureserv publiceert onder /api/geo/functions (schema postgisftw)
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/07_postgisftw_functions.sql >/dev/null
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
    python /app/init_data/scripts/create_admin.py || echo "⚠️ Admin initialisatie overgeslagen."

    # PostgREST schema cache herladen via NOTIFY
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "NOTIFY pgrst, 'reload schema';" >/dev/null 2>&1 || true
}

# Rollen en schema api voor PostgREST en pg_featureserv (#57). Draait bij elke start, ook bij
# een bestaande database: zonder deze rollen kunnen PostgREST en pg_featureserv niet verbinden.
# Idempotent. De LOGIN-rollen authenticator (PostgREST) en featureserv (pg_featureserv) krijgen
# DATABASE_PASSWORD als wachtwoord: geen extra variabele in .env. Die containers kregen dat
# wachtwoord al; de rollen zelf hebben geen rechten op de tabellen.
setup_api_rollen() {
    echo "🔐 Rollen en schema api voor PostgREST en pg_featureserv bijwerken..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q -f /app/migrations/schema_v23_api_rollen.sql >/dev/null
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

echo "============================================================"
echo "🌍 D-OmniTwin — Container Startup"
echo "============================================================"

wait_for_db

if [ "$1" = "init" ]; then
    init_db
    setup_api_rollen
    generate_embeddings
    echo "✅ Initialisatie klaar."
    exit 0
fi

echo "🚀 Start applicatie: $@"
exec "$@"
