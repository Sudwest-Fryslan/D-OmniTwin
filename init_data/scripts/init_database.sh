#!/bin/bash
# ============================================================
# D-OmniTwin — database inrichten zonder Docker
# ============================================================
# Gebruik: bash init_data/scripts/init_database.sh
#
# Eén initialisatieroute (#69): dit script doet precies wat de Docker-service
# db-init doet, door docker-entrypoint.sh init aan te roepen met de repo als
# projectmap. Dus dezelfde stappen: schema, migraties, stuurdata, use cases
# (als LOAD_SAMPLE_DATA=true), beheerder, organisatie, rollen voor PostgREST en
# pg_featureserv, embeddings. Een bestaande database wordt alleen gemigreerd.
#
# Configuratie: alleen .env in de projectroot (DATABASE_HOST, DATABASE_PORT,
# DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD). Zonder DATABASE_HOST: localhost.
#
# Vereisten:
#   - PostgreSQL met de extensies PostGIS en pgvector; database en eigenaar uit .env
#   - psql op het PATH
#   - Python-omgeving met requirements.txt (bijv. source .venv/bin/activate)
#
# Volledige Fryslân-data daarna (optioneel):
#   python init_data/scripts/seed_fryslan.py --stap alle
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "❌ .env niet gevonden in $PROJECT_ROOT"
    echo "   Kopieer .env.example naar .env en vul de DATABASE_*-gegevens in."
    exit 1
fi

# .env inlezen als KEY=waarde (geen shell-syntax: waarden worden niet uitgevoerd);
# wat al in de omgeving staat, gaat voor.
while IFS= read -r regel || [ -n "$regel" ]; do
    regel="${regel%$'\r'}"
    case "$regel" in
        [A-Za-z_]*=*)
            naam="${regel%%=*}"
            case "$naam" in *[!A-Za-z0-9_]*) continue ;; esac
            [ -z "${!naam+x}" ] && export "$naam=${regel#*=}"
            ;;
    esac
done < "$PROJECT_ROOT/.env"

export DATABASE_HOST="${DATABASE_HOST:-localhost}"
export APP_DIR="$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

cd "$PROJECT_ROOT"
exec bash "$PROJECT_ROOT/docker-entrypoint.sh" init
