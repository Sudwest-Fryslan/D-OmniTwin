#!/bin/bash
# ============================================================
#  D-OmniTwin — DEMO Start Script
#  Worktree: D-OmniTwin-DEMO (altijd op 'main')
#  Gebruik:  bash start_demo.sh [--port 8001]
# ============================================================

set -e

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_DIR="$(dirname "$DEMO_DIR")/D-OmniTwin"
VENV_PYTHON="$DEV_DIR/.venv/bin/python"
PORT="${2:-8000}"

# -- Kleurcodes
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo ""
echo -e "${CYAN}🎯 D-OmniTwin DEMO Server${RESET}"
echo -e "${CYAN}   Branch: main (stabiele versie)${RESET}"
echo -e "${CYAN}   Map:    $DEMO_DIR${RESET}"
echo ""

# -- 1. Controleer of .venv beschikbaar is
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Python venv niet gevonden op: $VENV_PYTHON${RESET}"
    echo -e "   Zorg dat de dev-omgeving op D-OmniTwin/ correct is geïnstalleerd."
    exit 1
fi
echo -e "${GREEN}✅ Python venv gevonden${RESET}"

# -- 2. Kopieer .env indien die ontbreekt
if [ ! -f "$DEMO_DIR/.env" ]; then
    if [ -f "$DEV_DIR/.env" ]; then
        cp "$DEV_DIR/.env" "$DEMO_DIR/.env"
        echo -e "${GREEN}✅ .env gekopieerd vanuit D-OmniTwin/${RESET}"
    else
        echo -e "${RED}❌ Geen .env gevonden in D-OmniTwin/ — demo kan niet starten.${RESET}"
        echo -e "   Maak eerst een .env aan in de dev-map."
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env aanwezig${RESET}"
fi

# -- 3. Controleer of poort al in gebruik is
if lsof -i ":$PORT" > /dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}⚠️  Poort $PORT is al in gebruik.${RESET}"
    echo -e "   Waarschijnlijk draait de dev-server nog in D-OmniTwin/."
    echo -e "   Stop die eerst (Ctrl+C) of gebruik een andere poort:"
    echo -e "   ${CYAN}bash start_demo.sh --port 8001${RESET}"
    echo ""
    exit 1
fi

# -- 4. Controleer git branch (extra veiligheid)
CURRENT_BRANCH=$(git -C "$DEMO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "onbekend")
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}⚠️  Waarschuwing: DEMO-map staat op branch '$CURRENT_BRANCH' (verwacht: main)${RESET}"
    echo -e "   Herstel met: git -C $DEMO_DIR checkout main"
    echo ""
fi

# -- 5. Start de demo server
echo ""
echo -e "${GREEN}🚀 DEMO server starten op http://localhost:$PORT${RESET}"
echo -e "   Gebruik ${YELLOW}Ctrl+C${RESET} om te stoppen."
echo ""

cd "$DEMO_DIR"
"$VENV_PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
