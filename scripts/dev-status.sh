#!/bin/bash
# Development Status Dashboard
# Shows current state of all Sakhi services, tests, and git status
# Usage: ./scripts/dev-status.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    SAKHI DEV STATUS                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Git Status
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}📦 GIT STATUS${NC}"
echo "─────────────────────────────────────────────────────────────────"

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo -e "Branch: ${GREEN}$BRANCH${NC}"

# Count changes
STAGED=$(git diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
UNSTAGED=$(git diff --numstat 2>/dev/null | wc -l | tr -d ' ')
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

if [ "$STAGED" -gt 0 ]; then
    echo -e "Staged:    ${GREEN}$STAGED files${NC}"
fi
if [ "$UNSTAGED" -gt 0 ]; then
    echo -e "Unstaged:  ${YELLOW}$UNSTAGED files${NC}"
fi
if [ "$UNTRACKED" -gt 0 ]; then
    echo -e "Untracked: ${RED}$UNTRACKED files${NC}"
fi
if [ "$STAGED" -eq 0 ] && [ "$UNSTAGED" -eq 0 ] && [ "$UNTRACKED" -eq 0 ]; then
    echo -e "${GREEN}Working tree clean${NC}"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Services Status
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}🔌 SERVICES${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Check API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "API (8000):     ${GREEN}● Running${NC}"
else
    echo -e "API (8000):     ${RED}○ Stopped${NC}"
fi

# Check Next.js
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "Web (3000):     ${GREEN}● Running${NC}"
else
    echo -e "Web (3000):     ${RED}○ Stopped${NC}"
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "Redis:          ${GREEN}● Running${NC}"
else
    echo -e "Redis:          ${RED}○ Stopped${NC}"
fi

# Check PostgreSQL
if pg_isready -q 2>/dev/null; then
    echo -e "PostgreSQL:     ${GREEN}● Running${NC}"
else
    echo -e "PostgreSQL:     ${RED}○ Stopped${NC}"
fi

# Check worker processes
WORKER_COUNT=$(pgrep -f "sakhi.apps.worker" 2>/dev/null | wc -l | tr -d ' ')
if [ "$WORKER_COUNT" -gt 0 ]; then
    echo -e "Workers:        ${GREEN}● Running ($WORKER_COUNT)${NC}"
else
    echo -e "Workers:        ${RED}○ Stopped${NC}"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Quick Health Checks
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}🧪 QUICK CHECKS${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Python imports check
if python -c "from sakhi.apps.api.main import app" 2>/dev/null; then
    echo -e "Python imports: ${GREEN}✓ OK${NC}"
else
    echo -e "Python imports: ${RED}✗ FAILED${NC}"
fi

# TypeScript check (quick - just syntax)
if [ -d "apps/web" ]; then
    TS_ERRORS=$(cd apps/web && pnpm tsc --noEmit 2>&1 | grep -c "error TS" || echo "0")
    if [ "$TS_ERRORS" -eq 0 ]; then
        echo -e "TypeScript:     ${GREEN}✓ OK${NC}"
    else
        echo -e "TypeScript:     ${RED}✗ $TS_ERRORS errors${NC}"
    fi
fi

# Check for uncommitted migrations
MIGRATION_COUNT=$(ls -1 sakhi/infra/scripts/migrations/*.sql 2>/dev/null | wc -l | tr -d ' ')
echo -e "Migrations:     ${BLUE}$MIGRATION_COUNT files${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Test Summary
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}📊 TEST COUNTS${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Count test files
UNIT_TESTS=$(find sakhi/tests -name "test_*.py" -not -path "*/_archive/*" -not -path "*/legacy/*" 2>/dev/null | wc -l | tr -d ' ')
INTEGRATION_TESTS=$(find sakhi/tests -name "*_integration*.py" 2>/dev/null | wc -l | tr -d ' ')
LEGACY_TESTS=$(find sakhi/tests/legacy -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')

echo -e "Unit tests:        ${BLUE}$UNIT_TESTS files${NC}"
echo -e "Integration tests: ${BLUE}$INTEGRATION_TESTS files${NC}"
echo -e "Legacy tests:      ${BLUE}$LEGACY_TESTS files${NC} (archived)"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# File Counts
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}📁 CODEBASE STATS${NC}"
echo "─────────────────────────────────────────────────────────────────"

PY_FILES=$(find sakhi -name "*.py" -not -path "*/__pycache__/*" 2>/dev/null | wc -l | tr -d ' ')
TS_FILES=$(find apps/web -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l | tr -d ' ')
ROUTES=$(ls -1 sakhi/apps/api/routes/*.py 2>/dev/null | wc -l | tr -d ' ')
SERVICES=$(find sakhi/apps/api/services -type d -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')

echo -e "Python files:   ${BLUE}$PY_FILES${NC}"
echo -e "TypeScript:     ${BLUE}$TS_FILES${NC}"
echo -e "API routes:     ${BLUE}$ROUTES${NC}"
echo -e "Services:       ${BLUE}$SERVICES${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}⚙️  ENVIRONMENT${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Check key env vars (without exposing values)
check_env() {
    if [ -n "${!1}" ]; then
        echo -e "$1: ${GREEN}✓ Set${NC}"
    else
        echo -e "$1: ${RED}✗ Not set${NC}"
    fi
}

check_env "DATABASE_URL"
check_env "REDIS_URL"
check_env "OPENAI_API_KEY"
check_env "SUPABASE_URL"

# Check dev flags
if [ "${SAKHI_DISABLE_QUEUE:-0}" = "1" ]; then
    echo -e "Queue mode: ${YELLOW}Inline (dev)${NC}"
else
    echo -e "Queue mode: ${GREEN}Async (Redis)${NC}"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Quick Commands Reference
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}🚀 QUICK COMMANDS${NC}"
echo "─────────────────────────────────────────────────────────────────"
echo "  make dev          # Start API server"
echo "  make worker       # Start background workers"
echo "  make test         # Run all tests"
echo "  make quick-test   # Run smoke tests only"
echo "  make lint         # Run linter"
echo "  make format       # Format code"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
