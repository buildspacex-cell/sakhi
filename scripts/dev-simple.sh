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

# Export environment variables
set -a
source .env.local
set +a

# Ensure sakhi package is importable from any CWD
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Force inline workers
export SAKHI_DISABLE_QUEUE=1

echo -e "${YELLOW}Starting services...${NC}"
echo ""

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

# Wait for API to be ready
echo -n "     Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e " ${GREEN}ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Start web server
echo -e "${GREEN}[2/2] Starting Web server (port 3000)...${NC}"
cd "$PROJECT_ROOT/apps/web"
pnpm dev &
WEB_PID=$!

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
