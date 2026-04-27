#!/bin/bash
# =============================================================================
# Sakhi Development - Simple Mode (No Redis)
# =============================================================================
# Starts API + Web server with inline workers (SAKHI_DISABLE_QUEUE=1)
# Workers run synchronously during API calls - no Redis needed
#
# Usage: ./scripts/dev-simple.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "============================================================"
echo "  SAKHI - Simple Development Mode"
echo "============================================================"
echo -e "${NC}"
echo "  API:     http://localhost:8080"
echo "  Web:     http://localhost:3000"
echo "  Workers: Inline (no Redis)"
echo ""

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo -e "${RED}Error: .env.local not found${NC}"
    echo "Copy .env to .env.local and configure your settings"
    exit 1
fi

load_env_file() {
    local env_file="$1"
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ''|\#*)
                continue
                ;;
        esac
        export "$line"
    done < "$env_file"
}

# Export environment variables safely without shell-evaluating URL query params.
load_env_file ".env.local"

# Ensure sakhi package is importable from any CWD
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Force inline workers
export SAKHI_DISABLE_QUEUE=1

echo -e "${YELLOW}Starting services...${NC}"
echo ""

wait_for_http() {
    local service_name="$1"
    local url="$2"
    local attempts="$3"
    local pid="$4"

    echo -n "     Waiting for ${service_name}..."
    for ((i = 1; i <= attempts; i++)); do
        if curl -fsS "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}ready${NC}"
            return 0
        fi

        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
            echo -e " ${RED}failed${NC}"
            return 1
        fi

        echo -n "."
        sleep 1
    done

    echo -e " ${RED}timeout${NC}"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $(jobs -p) 2>/dev/null
    wait
    echo -e "${GREEN}Done${NC}"
}

trap cleanup EXIT INT TERM

# Start API server
echo -e "${GREEN}[1/2] Starting API server (port 8080)...${NC}"
cd "$PROJECT_ROOT/sakhi"
uvicorn apps.api.main:app --reload --port 8080 --host 0.0.0.0 &
API_PID=$!
echo -e "     API PID: $API_PID"

# Wait for API to be ready
wait_for_http "API" "http://localhost:8080/health" 30 "$API_PID"

# Start web server
echo -e "${GREEN}[2/2] Starting Web server (port 3000)...${NC}"
cd "$PROJECT_ROOT/apps/web"
pnpm dev &
WEB_PID=$!
echo -e "     Web PID: $WEB_PID"
wait_for_http "Web" "http://localhost:3000" 30 "$WEB_PID"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "  API Docs:  http://localhost:8080/docs"
echo "  Web App:   http://localhost:3000"
echo "  Lab:       http://localhost:3000/lab"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for processes
wait
