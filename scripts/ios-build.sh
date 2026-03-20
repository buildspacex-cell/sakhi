#!/bin/bash
# =============================================================================
# Sakhi iOS Build — TestFlight
# =============================================================================
# Loads env vars, installs deps, then runs fastlane beta from apps/mobile/ios.
# EXPO_PUBLIC_* vars are passed through the shell to Metro at bundle time.
#
# Usage: ./scripts/ios-build.sh
#
# Requirements:
#   - Xcode + Xcode Command Line Tools
#   - fastlane (gem install fastlane)
#   - pnpm
#   - apps/mobile/.env.local with EXPO_PUBLIC_* vars set
#   - Apple Distribution cert + provisioning profile in your Keychain
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MOBILE_DIR="$PROJECT_ROOT/apps/mobile"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "============================================================"
echo "  SAKHI — iOS TestFlight Build"
echo "============================================================"
echo -e "${NC}"

# ── Preflight checks ─────────────────────────────────────────────────────────

ENV_FILE="$MOBILE_DIR/.env.local"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: apps/mobile/.env.local not found${NC}"
    exit 1
fi

if ! command -v fastlane &> /dev/null; then
    echo -e "${RED}Error: fastlane not found${NC}"
    echo "Install: gem install fastlane"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}Error: pnpm not found${NC}"
    echo "Install: corepack enable && corepack prepare pnpm@10.19.0 --activate"
    exit 1
fi

if ! command -v pod &> /dev/null; then
    echo -e "${RED}Error: CocoaPods not found${NC}"
    echo "Install: sudo gem install cocoapods"
    exit 1
fi

# ── Load env vars (passed through shell → xcodebuild → Metro at bundle time) ─

echo -e "${YELLOW}Loading env vars from apps/mobile/.env.local...${NC}"
set -a
source "$ENV_FILE"
set +a

required_vars=(
  EXPO_PUBLIC_BACKEND_URL
  EXPO_PUBLIC_SUPABASE_URL
  EXPO_PUBLIC_SUPABASE_ANON_KEY
  FASTLANE_USER
  FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name}" ]; then
    echo -e "${RED}Error: $var_name is not set in apps/mobile/.env.local${NC}"
    exit 1
  fi
done

for forbidden_var in EXPO_PUBLIC_OPENAI_API_KEY EXPO_PUBLIC_RELEASE_BYPASS_ENABLED EXPO_PUBLIC_RELEASE_BYPASS_PERSON_ID; do
  if [ -n "${!forbidden_var}" ]; then
    echo -e "${RED}Error: remove stale $forbidden_var from apps/mobile/.env.local before building${NC}"
    exit 1
  fi
done

if [ -z "$EXPO_PUBLIC_POSTHOG_KEY" ]; then
    echo -e "${YELLOW}Warning: EXPO_PUBLIC_POSTHOG_KEY is not set — analytics will be disabled in this build${NC}"
else
    echo -e "${GREEN}  PostHog analytics: enabled${NC}"
fi

# ── Step 1: Install JS deps ───────────────────────────────────────────────────

echo ""
echo -e "${GREEN}[1/3] Installing JS dependencies with pnpm...${NC}"
cd "$PROJECT_ROOT"
pnpm install --no-frozen-lockfile 2>&1

# ── Step 2: Install CocoaPods ─────────────────────────────────────────────────

echo ""
echo -e "${GREEN}[2/3] Installing CocoaPods...${NC}"
cd "$MOBILE_DIR/ios"
pod install 2>&1

# ── Step 3: Fastlane build + upload ──────────────────────────────────────────

echo ""
echo -e "${GREEN}[3/3] Building and uploading to TestFlight (fastlane beta)...${NC}"
cd "$MOBILE_DIR/ios"
fastlane beta 2>&1

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Build complete — check TestFlight for the new build${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${CYAN}PostHog Live Events:${NC} posthog.com → your project → Live Events"
echo "  Events will appear within ~30s of the first app session."
echo ""
