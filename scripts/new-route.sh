#!/bin/bash
# Generate a new FastAPI route with boilerplate
# Usage: ./scripts/new-route.sh <route_name>
# Example: ./scripts/new-route.sh wellness

set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/new-route.sh <route_name>"
    echo "Example: ./scripts/new-route.sh wellness"
    exit 1
fi

ROUTE_NAME="$1"
ROUTE_FILE="sakhi/apps/api/routes/${ROUTE_NAME}.py"
TEST_FILE="sakhi/tests/api/test_${ROUTE_NAME}.py"

# Check if route already exists
if [ -f "$ROUTE_FILE" ]; then
    echo "Error: Route file already exists: $ROUTE_FILE"
    exit 1
fi

echo "Creating route: $ROUTE_NAME"

# Create route file
cat > "$ROUTE_FILE" << 'EOF'
"""
${ROUTE_NAME_TITLE} API Routes

Endpoints for ${ROUTE_NAME} functionality.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import logging

from sakhi.libs.db import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/${ROUTE_NAME}", tags=["${ROUTE_NAME}"])


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class ${ROUTE_NAME_CLASS}Response(BaseModel):
    """Response model for ${ROUTE_NAME} endpoint."""
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None


class ${ROUTE_NAME_CLASS}Request(BaseModel):
    """Request model for ${ROUTE_NAME} endpoint."""
    person_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/")
async def get_${ROUTE_NAME}(
    person_id: str = Query(..., description="User ID")
) -> ${ROUTE_NAME_CLASS}Response:
    """
    Get ${ROUTE_NAME} data for a user.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # TODO: Implement database query
            pass

        return ${ROUTE_NAME_CLASS}Response(
            success=True,
            data={"person_id": person_id},
            message="${ROUTE_NAME_TITLE} retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_${ROUTE_NAME}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_${ROUTE_NAME}(
    request: ${ROUTE_NAME_CLASS}Request
) -> ${ROUTE_NAME_CLASS}Response:
    """
    Create or update ${ROUTE_NAME} data.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # TODO: Implement database insert/update
            pass

        return ${ROUTE_NAME_CLASS}Response(
            success=True,
            message="${ROUTE_NAME_TITLE} created successfully"
        )
    except Exception as e:
        logger.error(f"Error in create_${ROUTE_NAME}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
EOF

# Replace placeholders
ROUTE_NAME_TITLE=$(echo "$ROUTE_NAME" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)$i=toupper(substr($i,1,1))tolower(substr($i,2))}1')
ROUTE_NAME_CLASS=$(echo "$ROUTE_NAME" | sed 's/_\([a-z]\)/\U\1/g' | sed 's/^\([a-z]\)/\U\1/')

sed -i '' "s/\${ROUTE_NAME}/${ROUTE_NAME}/g" "$ROUTE_FILE"
sed -i '' "s/\${ROUTE_NAME_TITLE}/${ROUTE_NAME_TITLE}/g" "$ROUTE_FILE"
sed -i '' "s/\${ROUTE_NAME_CLASS}/${ROUTE_NAME_CLASS}/g" "$ROUTE_FILE"

echo "Created: $ROUTE_FILE"

# Create test file
mkdir -p "$(dirname "$TEST_FILE")"
cat > "$TEST_FILE" << EOF
"""
Tests for ${ROUTE_NAME} routes.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sakhi.apps.api.main import app


@pytest.fixture
def test_person_id():
    return "565bdb63-124b-4692-a039-846fddceff90"  # Demo user (Vidhya)


@pytest.mark.asyncio
async def test_get_${ROUTE_NAME}(test_person_id):
    """Test GET /${ROUTE_NAME} endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/${ROUTE_NAME}",
            params={"person_id": test_person_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_create_${ROUTE_NAME}(test_person_id):
    """Test POST /${ROUTE_NAME} endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/${ROUTE_NAME}",
            json={"person_id": test_person_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
EOF

echo "Created: $TEST_FILE"

# Reminder to register route
echo ""
echo "Next steps:"
echo "1. Register the route in sakhi/apps/api/main.py:"
echo "   from sakhi.apps.api.routes.${ROUTE_NAME} import router as ${ROUTE_NAME}_router"
echo "   app.include_router(${ROUTE_NAME}_router)"
echo ""
echo "2. Run tests:"
echo "   pytest ${TEST_FILE} -v"
echo ""
echo "3. Update docs:"
echo "   - docs/ARCHITECTURE.md (API routes section)"
echo "   - docs/BUILD_PLAN.md (if completing a planned feature)"
