#!/bin/bash
# run_flask_integration.sh
#
# Equivalente a run_integration_test.sh pero usando el servidor Flask
# (gvsoc_flask_server.py) en lugar del servidor TCP (gvsoc_tcp_server.py).
#
# El servidor Flask acepta N conexiones concurrentes (threaded=True),
# lo que permite ejecutar batches paralelos de SHARC sin bloqueo.
#
# Uso:
#   bash SHARCBRIDGE/scripts/run_flask_integration.sh
#
# Variables de entorno:
#   FLASK_PORT  Puerto Flask (default: 5000)
#   GVSOC_HOST  Host GVSoC visto desde Docker (default: 127.0.0.1)

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARCBRIDGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SHARCBRIDGE_DIR/.." && pwd)"

FLASK_PORT="${FLASK_PORT:-5000}"
GVSOC_HOST="${GVSOC_HOST:-127.0.0.1}"
FLASK_SERVER="$SCRIPT_DIR/gvsoc_flask_server.py"
VENV_ACTIVATE="$REPO_DIR/venv/bin/activate"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

FLASK_PID=""
FLASK_STARTED_HERE=false

# ── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup() {
    local exit_code=$?
    echo -e "\n${YELLOW}[Flask] Cleaning up...${NC}"

    if [ "$FLASK_STARTED_HERE" = true ] && [ -n "$FLASK_PID" ]; then
        echo -e "${YELLOW}[Flask] Shutting down Flask server (PID $FLASK_PID)...${NC}"
        # Try graceful shutdown first
        curl -sf -X POST "http://localhost:${FLASK_PORT}/shutdown" \
             -o /dev/null 2>/dev/null || true
        sleep 0.5

        # Force kill if still running
        if kill -0 "$FLASK_PID" 2>/dev/null; then
            kill "$FLASK_PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}[Flask] Server stopped${NC}"
    fi

    exit $exit_code
}
trap cleanup EXIT INT TERM

# ── 1. Install dependencies ──────────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Installing Python dependencies...${NC}"
# shellcheck source=/dev/null
source "$VENV_ACTIVATE"
pip install flask requests -q
echo -e "${GREEN}✓ flask and requests installed${NC}"

# ── 2. Check if Flask is already running ────────────────────────────────────
echo -e "${YELLOW}[2/6] Checking for existing Flask server on port ${FLASK_PORT}...${NC}"
if curl -sf "http://localhost:${FLASK_PORT}/health" -o /dev/null 2>/dev/null; then
    echo -e "${GREEN}✓ Flask server already running — reusing it${NC}"
else
    echo -e "${YELLOW}   Starting Flask server...${NC}"
    python3 "$FLASK_SERVER" \
        --host 0.0.0.0 \
        --port "$FLASK_PORT" \
        --skip-validation \
        &
    FLASK_PID=$!
    FLASK_STARTED_HERE=true
    echo -e "${GREEN}   Flask PID: $FLASK_PID${NC}"

    # ── 3. Wait for Flask to be ready ─────────────────────────────────────
    echo -e "${YELLOW}[3/6] Waiting for Flask server to be ready...${NC}"
    MAX_WAIT=15
    WAITED=0
    until curl -sf "http://localhost:${FLASK_PORT}/health" -o /dev/null 2>/dev/null; do
        sleep 1
        WAITED=$((WAITED + 1))
        echo -n "."
        if [ $WAITED -ge $MAX_WAIT ]; then
            echo -e "\n${RED}ERROR: Flask server did not start within ${MAX_WAIT}s${NC}"
            exit 1
        fi
    done
    echo -e "\n${GREEN}✓ Flask server ready at http://localhost:${FLASK_PORT}${NC}"
fi

# ── 4. Run the integration using HTTP transport ──────────────────────────────
echo -e "${YELLOW}[4/6] Running SHARC integration with HTTP transport...${NC}"
export GVSOC_TRANSPORT=http
export GVSOC_HOST="$GVSOC_HOST"
export GVSOC_PORT="$FLASK_PORT"

# Delegate to the same integration script, which handles Docker + FIFOs + wrapper
bash "$SCRIPT_DIR/run_integration_test.sh"
INTEGRATION_EXIT=$?

# ── 5. Report ────────────────────────────────────────────────────────────────
if [ $INTEGRATION_EXIT -eq 0 ]; then
    echo -e "${GREEN}[5/6] Integration test PASSED (Flask transport)${NC}"
else
    echo -e "${RED}[5/6] Integration test FAILED (exit code: $INTEGRATION_EXIT)${NC}"
fi

# cleanup() will shut down Flask via the trap
exit $INTEGRATION_EXIT
