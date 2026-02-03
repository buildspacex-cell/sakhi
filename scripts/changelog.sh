#!/bin/bash
# Generate changelog entry from recent commits

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}       CHANGELOG GENERATOR             ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo ""

# Get date
TODAY=$(date +%Y-%m-%d)

# Get commits since last tag (or last 10 if no tags)
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -n "$LAST_TAG" ]; then
    echo -e "${GREEN}Commits since $LAST_TAG:${NC}"
    COMMITS=$(git log "$LAST_TAG"..HEAD --pretty=format:"- %s" --no-merges)
else
    echo -e "${GREEN}Last 10 commits:${NC}"
    COMMITS=$(git log -10 --pretty=format:"- %s" --no-merges)
fi

echo ""
echo "$COMMITS"
echo ""

# Categorize commits
echo -e "${YELLOW}Categorized entries for CHANGELOG.md:${NC}"
echo ""
echo "## [Unreleased] - $TODAY"
echo ""

# Added (feat:)
ADDED=$(echo "$COMMITS" | grep -i "^- feat:" | sed 's/^- feat: /- /' || true)
if [ -n "$ADDED" ]; then
    echo "### Added"
    echo "$ADDED"
    echo ""
fi

# Changed (refactor:, chore:, update:)
CHANGED=$(echo "$COMMITS" | grep -iE "^- (refactor|chore|update):" | sed 's/^- [a-z]*: /- /' || true)
if [ -n "$CHANGED" ]; then
    echo "### Changed"
    echo "$CHANGED"
    echo ""
fi

# Fixed (fix:)
FIXED=$(echo "$COMMITS" | grep -i "^- fix:" | sed 's/^- fix: /- /' || true)
if [ -n "$FIXED" ]; then
    echo "### Fixed"
    echo "$FIXED"
    echo ""
fi

# Docs (docs:)
DOCS=$(echo "$COMMITS" | grep -i "^- docs:" | sed 's/^- docs: /- /' || true)
if [ -n "$DOCS" ]; then
    echo "### Documentation"
    echo "$DOCS"
    echo ""
fi

# Other (uncategorized)
OTHER=$(echo "$COMMITS" | grep -ivE "^- (feat|fix|refactor|chore|update|docs):" || true)
if [ -n "$OTHER" ]; then
    echo "### Other"
    echo "$OTHER"
    echo ""
fi

echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "Copy the above to ${GREEN}CHANGELOG.md${NC}"
echo -e "Or use: ${YELLOW}make changelog >> CHANGELOG.md${NC}"
echo -e "${BLUE}=======================================${NC}"
