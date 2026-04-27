#!/bin/bash
# =============================================================================
# Sakhi Development - Full Stack Mode (Production-like)
# =============================================================================
# Starts Redis + API + Worker + Web server
# Workers run asynchronously via Redis queues - matches production behavior
#
# Usage: ./scripts/dev-full.sh
#
# Requirements:
#   - Redis installed (brew install redis)
#   - Python environment with dependencies
#   - Node.js with pnpm
#
# For mobile development, run separately: cd apps/mobile && pnpm start
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
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "============================================================"
echo "  SAKHI - Full Stack Development Mode"
echo "============================================================"
echo -e "${NC}"
echo "  Redis:   localhost:6379"
echo "  API:     http://localhost:8080"
echo "  Worker:  Background job processor"
echo "  Web:     http://localhost:3000"
echo ""

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo -e "${RED}Error: .env.local not found${NC}"
    echo "Copy .env to .env.local and configure your settings"
    exit 1
fi

# Check if redis-server is installed
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}Error: redis-server not found${NC}"
    echo "Install Redis: brew install redis"
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

# Fix macOS fork() safety issue that crashes RQ workers
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Force queue mode (not inline)
export SAKHI_DISABLE_QUEUE=0

echo -e "${YELLOW}Starting services...${NC}"
echo ""

# Create log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Track PIDs
API_PID=""
WORKER_PID=""
WEB_PID=""

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
            echo "     ${service_name} exited before becoming ready. See log: $5"
            return 1
        fi

        echo -n "."
        sleep 1
    done

    echo -e " ${RED}timeout${NC}"
    echo "     ${service_name} did not become ready in time. See log: $5"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"

    # Send SIGTERM first for graceful shutdown
    if [ -n "$WEB_PID" ] && kill -0 $WEB_PID 2>/dev/null; then
        echo "  Stopping Web server..."
        kill -TERM $WEB_PID 2>/dev/null
    fi

    if [ -n "$WORKER_PID" ] && kill -0 $WORKER_PID 2>/dev/null; then
        echo "  Stopping Worker (graceful)..."
        kill -TERM $WORKER_PID 2>/dev/null
    fi

    if [ -n "$API_PID" ] && kill -0 $API_PID 2>/dev/null; then
        echo "  Stopping API server..."
        kill -TERM $API_PID 2>/dev/null
    fi

    # Give processes time to shut down gracefully
    echo "  Waiting for processes to exit..."
    sleep 2

    # Force kill any remaining processes
    for pid in $WEB_PID $WORKER_PID $API_PID; do
        if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
            echo "  Force killing PID $pid..."
            kill -9 $pid 2>/dev/null
        fi
    done

    # Kill any remaining background jobs
    jobs -p 2>/dev/null | xargs -r kill -9 2>/dev/null

    # Stop Redis if we started it
    if [ "$REDIS_STARTED" = "true" ]; then
        echo "  Stopping Redis..."
        redis-cli shutdown 2>/dev/null || true
    fi

    wait 2>/dev/null
    echo -e "${GREEN}Done${NC}"
}

trap cleanup EXIT INT TERM

# Check if Redis is already running
REDIS_STARTED="false"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}[1/4] Redis already running${NC}"
else
    echo -e "${GREEN}[1/4] Starting Redis server...${NC}"
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
    REDIS_STARTED="true"
    sleep 1

    if redis-cli ping > /dev/null 2>&1; then
        echo -e "     ${GREEN}Redis ready${NC}"
    else
        echo -e "     ${RED}Redis failed to start${NC}"
        exit 1
    fi
fi

# Start API server
echo -e "${GREEN}[2/4] Starting API server (port 8080)...${NC}"
cd "$PROJECT_ROOT/sakhi"
uvicorn apps.api.main:app --reload --port 8080 --host 0.0.0.0 > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!
echo -e "     API PID: $API_PID"

# Wait for API to be ready
wait_for_http "API" "http://localhost:8080/health" 30 "$API_PID" "$LOG_DIR/api.log"

# Start worker process
echo -e "${GREEN}[3/4] Starting Worker process...${NC}"
cd "$PROJECT_ROOT/sakhi"
python -m apps.worker.main > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!
echo -e "     Worker PID: $WORKER_PID"

# Start web server
echo -e "${GREEN}[4/4] Starting Web server (port 3000)...${NC}"
cd "$PROJECT_ROOT/apps/web"
pnpm dev > "$LOG_DIR/web.log" 2>&1 &
WEB_PID=$!
echo -e "     Web PID: $WEB_PID"
wait_for_http "Web" "http://localhost:3000" 30 "$WEB_PID" "$LOG_DIR/web.log"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "  Redis:     localhost:6379"
echo "  API Docs:  http://localhost:8080/docs"
echo "  Web App:   http://localhost:3000"
echo "  Lab:       http://localhost:3000/lab"
echo ""
echo "  Logs:      $LOG_DIR/"
echo ""
echo -e "${CYAN}Queue Status:${NC}"
echo "  redis-cli LLEN turn_updates    # Check pending jobs"
echo "  redis-cli KEYS 'rq:job:*'      # List all jobs"
echo ""
echo -e "${CYAN}Mobile Development:${NC}"
echo "  Run separately: cd apps/mobile && pnpm start"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for processes
wait
