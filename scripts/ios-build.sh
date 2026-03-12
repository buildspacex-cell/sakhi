#!/bin/bash
# =============================================================================
# Sakhi iOS Build — TestFlight
# =============================================================================
# Runs expo prebuild (bakes env vars) then fastlane beta (build + upload).
#
# Usage: ./scripts/ios-build.sh
#
# Requirements:
#   - Xcode + Xcode Command Line Tools
#   - fastlane (gem install fastlane)
#   - apps/mobile/.env.local with EXPO_PUBLIC_* vars set
#   - apps/mobile/ios/fastlane/keys/AuthKey_BWGN9F87AQ.p8 present
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

AUTH_KEY="$MOBILE_DIR/ios/fastlane/keys/AuthKey_BWGN9F87AQ.p8"
if [ ! -f "$AUTH_KEY" ]; then
    echo -e "${RED}Error: App Store Connect API key not found at:${NC}"
    echo "  $AUTH_KEY"
    exit 1
fi

if ! command -v fastlane &> /dev/null; then
    echo -e "${RED}Error: fastlane not found${NC}"
    echo "Install: gem install fastlane"
    exit 1
fi

if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npx not found${NC}"
    exit 1
fi

# ── Load env vars so they're available during prebuild ───────────────────────

echo -e "${YELLOW}Loading env vars from apps/mobile/.env.local...${NC}"
set -a
source "$ENV_FILE"
set +a

# Confirm PostHog key is set
if [ -z "$EXPO_PUBLIC_POSTHOG_KEY" ]; then
    echo -e "${YELLOW}Warning: EXPO_PUBLIC_POSTHOG_KEY is not set — analytics will be disabled in this build${NC}"
else
    echo -e "${GREEN}  PostHog analytics: enabled${NC}"
fi

# ── Step 1: Install JS deps ───────────────────────────────────────────────────

echo ""
echo -e "${GREEN}[1/4] Installing JS dependencies...${NC}"
cd "$PROJECT_ROOT"
if command -v pnpm &> /dev/null; then
    pnpm install --frozen-lockfile 2>&1
else
    npm install 2>&1
fi

# ── Step 2: Expo prebuild ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}[2/4] Running expo prebuild (bakes env vars into native)...${NC}"
cd "$MOBILE_DIR"
npx expo prebuild --platform ios --clean 2>&1

# ── Step 3: Install CocoaPods ─────────────────────────────────────────────────

echo ""
echo -e "${GREEN}[3/4] Installing CocoaPods...${NC}"
cd "$MOBILE_DIR/ios"
pod install 2>&1

# ── Step 4: Fastlane build + upload ──────────────────────────────────────────

echo ""
echo -e "${GREEN}[4/4] Building and uploading to TestFlight (fastlane beta)...${NC}"
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
