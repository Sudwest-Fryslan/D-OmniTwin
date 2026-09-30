#!/bin/bash
set -e

# ============================================================
# D-OmniTwin — Container Startup & Initialisatie
# ============================================================

DB_HOST="${DATABASE_HOST:-postgres}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-omnitwin_db}"
DB_USER="${DATABASE_USER:-omnitwin_user}"
DB_PASS="${DATABASE_PASSWORD:-}"

export PGPASSWORD="$DB_PASS"

echo "============================================================"
echo "🌍 D-OmniTwin — Container Startup"
echo "============================================================"
echo "   Database target: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

# 1. Wacht tot PostgreSQL bereikbaar is
echo "⏳ Wachten op PostgreSQL database verbinding..."
MAX_RETRIES=30
COUNT=0
until psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Kon na $MAX_RETRIES seconden geen verbinding maken met PostgreSQL ($DB_HOST:$DB_PORT)."
        exit 1
    fi
    sleep 1
done
echo "✅ PostgreSQL is gereed voor verbindingen."

# 2. Controleer of het schema al bestaat
TABLE_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='gebieden';" 2>/dev/null || true)

if [ "$TABLE_EXISTS" != "1" ]; then
    echo "⚙️ Database is leeg. Initialiseren via schema_latest.sql..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /app/init_data/schema/schema_latest.sql >/dev/null
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
    export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
    echo "👤 Admin gebruiker controleren/aanmaken ('$ADMIN_USER')..."
    python /app/init_data/scripts/create_admin.py || echo "⚠️ Admin initialisatie overgeslagen."

    # PostgREST schema cache herladen via NOTIFY
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "NOTIFY pgrst, 'reload schema';" >/dev/null 2>&1 || true
else
    echo "✅ Bestaande database gevonden (tabel 'gebieden' aanwezig). Initialisatie overgeslagen."
fi

echo "🚀 Start applicatie: $@"
exec "$@"
