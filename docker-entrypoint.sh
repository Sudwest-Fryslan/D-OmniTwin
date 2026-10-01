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

init_db() {
    # Controleer of het schema al bestaat
    TABLE_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='gebieden';" 2>/dev/null || true)

    if [ "$TABLE_EXISTS" = "1" ]; then
        echo "✅ Bestaande database gevonden (tabel 'gebieden' aanwezig). Initialisatie overgeslagen."
        return
    fi

    echo "⚙️ Database is leeg. Initialiseren via schema_latest.sql..."
    # ON_ERROR_STOP: stop bij de eerste SQL-fout in plaats van een half schema
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/schema_latest.sql >/dev/null
    # Views voor pg_featureserv (vw_gebieden_features, gebruikt door de kaart) staan niet in schema_latest.sql
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/06_pg_featureserv_views.sql >/dev/null
    # SQL-functies die pg_featureserv publiceert onder /api/geo/functions (schema postgisftw)
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /app/init_data/schema/07_postgisftw_functions.sql >/dev/null
    # Migraties die (nog) niet in schema_latest.sql zitten; idempotent. Structureel: migratiebeheer (#54)
    for m in schema_v18_trigram.sql schema_v19_deduplicatie_uitzonderingen.sql schema_v21_zscore_referentie.sql; do
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "/app/migrations/$m" >/dev/null
    done
    echo "✅ Database schema succesvol aangemaakt."

    LOAD_SAMPLE="${LOAD_SAMPLE_DATA:-true}"
    if [ "$LOAD_SAMPLE" = "true" ] || [ "$LOAD_SAMPLE" = "1" ]; then
        echo "🌱 LOAD_SAMPLE_DATA is actief: Sample dataset (12 SWF buurten) inladen..."
        python /app/init_data/scripts/load_sample.py --stap alle
        echo "✅ Sample dataset succesvol ingeladen."
    else
        echo "⚙️ LOAD_SAMPLE_DATA niet actief: Alleen stuurdata inladen..."
        python /app/init_data/scripts/load_sample.py --stap stuurdata
        echo "✅ Stuurdata ingeladen."
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

echo "============================================================"
echo "🌍 D-OmniTwin — Container Startup"
echo "============================================================"

wait_for_db

if [ "$1" = "init" ]; then
    init_db
    echo "✅ Initialisatie klaar."
    exit 0
fi

echo "🚀 Start applicatie: $@"
exec "$@"
