#!/bin/bash
# ============================================================
# D-OmniTwin — Database Initialisatie Script
# ============================================================
# Gebruik: bash init_data/scripts/init_database.sh
#
# Dit script richt de volledige database in:
#   1. PostgreSQL schema (tabellen, views, triggers)
#   2. Indicatoren seed (uit indicatoren_seed.json)
#   3. Kompas hiërarchie (uit kompas_hierarchie.csv)
#   4. Buurten + geometrie (uit buurten_fryslan.geojson)
#   5. Indicatorwaarden (uit indicatorwaarden_fryslan.csv)
#   6. Eerste admin gebruiker + API key aanmaken
#
# Vereisten:
#   - PostgreSQL draaien met omnitwin_db en omnitwin_user
#   - .env bestand aanwezig in de projectroot
#   - Python virtual environment geactiveerd: source .venv/bin/activate
#   - Geodata aanwezig: init_data/fryslan/buurten_fryslan.geojson
#   - Indicatorwaarden aanwezig: init_data/fryslan/indicatorwaarden_fryslan.csv
# ============================================================

set -e  # Stop bij eerste fout

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "============================================================"
echo "🌍 D-OmniTwin — Database Initialisatie"
echo "============================================================"
echo "   Project root: $PROJECT_ROOT"
echo ""

# Laad .env variabelen
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | sed -e 's/ *#.*//' | xargs 2>/dev/null)
    echo "✅ .env geladen"
else
    echo "❌ .env niet gevonden in projectroot!"
    echo "   Kopieer .env.example naar .env en vul je database-gegevens in."
    exit 1
fi

DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-omnitwin_db}"
DB_USER="${DATABASE_USER:-omnitwin_user}"

echo ""
echo "────────────────────────────────────────────────────────────"
echo "STAP 1/5: Schema laden"
echo "────────────────────────────────────────────────────────────"

if ! PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -f "$PROJECT_ROOT/db/schema/schema_latest.sql" 2>&1; then
    echo "❌ Schema laden mislukt."
    echo "   Controleer of de database bestaat:"
    echo ""
    echo "   sudo -u postgres psql -c \"CREATE USER $DB_USER WITH PASSWORD 'jouw-wachtwoord';\""
    echo "   sudo -u postgres psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\""
    echo "   sudo -u postgres psql -d $DB_NAME -c 'CREATE EXTENSION postgis;'"
    echo "   sudo -u postgres psql -d $DB_NAME -c 'CREATE EXTENSION vector;'"
    exit 1
fi

echo "✅ Schema geladen"

echo "Laden van AI/App configuratiedata..."
if ! PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -f "$PROJECT_ROOT/db/stuurdata/config_seed_fixed.sql" 2>&1; then
    echo "⚠️ Waarschuwing: Laden van configuratiedata (config_seed_fixed.sql) deels mislukt."
else
    echo "✅ Configuratiedata geladen"
fi


echo ""
echo "────────────────────────────────────────────────────────────"
echo "STAP 2-5/6: Data seeden (indicatoren, kompas, buurten, waarden)"
echo "────────────────────────────────────────────────────────────"

# Controleer of GeoJSON aanwezig is
if [ ! -f "$PROJECT_ROOT/init_data/fryslan/buurten_fryslan.geojson" ]; then
    echo "⚠️  buurten_fryslan.geojson niet gevonden."
    echo "   Download de geodata eerst:"
    echo ""
    echo "   python init_data/scripts/download_buurten_fryslan.py"
    echo ""
    echo "   Stap 4 (buurten) wordt overgeslagen."
fi

# Controleer of indicatorwaarden aanwezig zijn
if [ ! -f "$PROJECT_ROOT/init_data/fryslan/indicatorwaarden_fryslan.csv" ]; then
    echo "⚠️  indicatorwaarden_fryslan.csv niet gevonden."
    echo "   Download de CBS data eerst:"
    echo ""
    echo "   python init_data/scripts/download_indicatoren_fryslan.py"
    echo ""
    echo "   Stap 5 (waarden) wordt overgeslagen."
fi

python "$PROJECT_ROOT/init_data/scripts/seed_fryslan.py" --stap alle

echo ""
echo "────────────────────────────────────────────────────────────"
echo "STAP 6/6: Admin gebruiker aanmaken"
echo "────────────────────────────────────────────────────────────"

python "$PROJECT_ROOT/init_data/scripts/create_admin.py"

echo ""
echo "============================================================"
echo "✅ Database initialisatie voltooid!"
echo ""
echo "   🌐 Start de applicatie:  python run_dev.py"
echo "   🌐 Open in browser:      http://localhost:8000"
echo "   🔐 Admin Panel:          http://localhost:8000/admin"
echo "   📚 API documentatie:     http://localhost:8000/docs"
echo "============================================================"
echo ""
