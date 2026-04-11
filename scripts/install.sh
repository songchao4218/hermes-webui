#!/usr/bin/env bash
#
# 马鞍 Ma'an - Install Script
# Supports: Linux, macOS, WSL
#
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

echo ""
echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}  ║    马鞍 Ma'an Installer              ║${NC}"
echo -e "${CYAN}${BOLD}  ║    WebUI for Hermes Agent + Ollama   ║${NC}"
echo -e "${CYAN}${BOLD}  ╚══════════════════════════════════════╝${NC}"
echo ""

# ── Check prerequisites ──────────────────────────────────────────

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found: $(command -v "$1")"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

echo -e "${BOLD}Checking prerequisites...${NC}"
echo ""

# Python 3
PYTHON_CMD=""
if check_command python3; then
    PYTHON_CMD="python3"
elif check_command python; then
    if python --version 2>&1 | grep -q "Python 3"; then
        PYTHON_CMD="python"
        echo -e "  ${GREEN}✓${NC} python is Python 3"
    else
        echo -e "  ${RED}✗${NC} python is not Python 3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo -e "${RED}Python 3 is required. Install it first:${NC}"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi

# pip
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "  ${YELLOW}!${NC} pip not found, attempting to install..."
    $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || {
        echo -e "${RED}pip is required. Install it:${NC}"
        echo "  Ubuntu/Debian: sudo apt install python3-pip"
        exit 1
    }
fi
echo -e "  ${GREEN}✓${NC} pip available"

# Check for Hermes
echo ""
HERMES_HOME="$HOME/.hermes"
if [ -d "$HERMES_HOME" ]; then
    echo -e "  ${GREEN}✓${NC} Hermes found at $HERMES_HOME"
else
    echo -e "  ${YELLOW}!${NC} Hermes not found at $HERMES_HOME"
    echo -e "    Install Hermes first: ${CYAN}pipx install hermes-agent${NC}"
    echo -e "    Or: ${CYAN}pip install hermes-agent${NC}"
    echo ""
    read -p "  Continue without Hermes? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for Ollama
echo ""
OLLAMA_URL="http://localhost:11434"
if check_command ollama; then
    echo -e "  ${GREEN}✓${NC} Ollama installed locally"
else
    # Try to read Ollama URL from Hermes config
    if [ -f "$HERMES_HOME/config.yaml" ]; then
        DETECTED_URL=$(grep -E "ollama_base_url|base_url" "$HERMES_HOME/config.yaml" | head -1 | awk '{print $2}' | tr -d '"')
        if [ -n "$DETECTED_URL" ]; then
            OLLAMA_URL="$DETECTED_URL"
            echo -e "  ${GREEN}✓${NC} Ollama URL from Hermes config: $OLLAMA_URL"
        fi
    fi
    echo -e "  ${YELLOW}!${NC} Ollama not found locally (may be on another host)"
fi

# ── Install Python dependencies ──────────────────────────────────

echo ""
echo -e "${BOLD}Installing Python dependencies...${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create virtual environment
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv "$PROJECT_DIR/.venv"
fi

# Activate venv
source "$PROJECT_DIR/.venv/bin/activate"

# Install requirements
pip install -r "$PROJECT_DIR/backend/requirements.txt" --quiet

echo -e "  ${GREEN}✓${NC} Dependencies installed"

# ── Summary ──────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo -e "  Start WebUI:    ${CYAN}./scripts/start.sh${NC}"
echo -e "  Open browser:   ${CYAN}http://localhost:8080${NC}"
echo ""
echo -e "  Hermes home:    ${CYAN}$HERMES_HOME${NC}"
echo -e "  Ollama URL:     ${CYAN}$OLLAMA_URL${NC}"
echo ""
