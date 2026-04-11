#!/usr/bin/env bash
#
# 马鞍 Ma'an - Start Script
#
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo -e "${CYAN}${BOLD}  马鞍 Ma'an${NC}"
echo ""

# Activate venv
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
else
    echo "Virtual environment not found. Run ./scripts/install.sh first."
    exit 1
fi

# Parse arguments
HOST="${MAAN_HOST:-0.0.0.0}"
PORT="${MAAN_PORT:-8080}"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift ;;
        --host) HOST="$2"; shift ;;
        *) ;;
    esac
    shift
done

echo -e "  Server: ${GREEN}http://$HOST:$PORT${NC}"
echo -e "  Press Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR/backend"

python app.py --host "$HOST" --port "$PORT"
