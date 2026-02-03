#!/bin/bash
# Generate a new service module with boilerplate
# Usage: ./scripts/new-service.sh <service_name>
# Example: ./scripts/new-service.sh wellness_tracker

set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/new-service.sh <service_name>"
    echo "Example: ./scripts/new-service.sh wellness_tracker"
    exit 1
fi

SERVICE_NAME="$1"
SERVICE_DIR="sakhi/apps/api/services/${SERVICE_NAME}"
TEST_DIR="sakhi/tests/services"
TEST_FILE="${TEST_DIR}/test_${SERVICE_NAME}.py"
INTEGRATION_TEST_FILE="${TEST_DIR}/test_${SERVICE_NAME}_integration.py"

# Check if service already exists
if [ -d "$SERVICE_DIR" ]; then
    echo "Error: Service directory already exists: $SERVICE_DIR"
    exit 1
fi

echo "Creating service: $SERVICE_NAME"

# Create service directory
mkdir -p "$SERVICE_DIR"

# Create __init__.py
cat > "${SERVICE_DIR}/__init__.py" << EOF
"""
${SERVICE_NAME} Service

TODO: Add service description here.
"""

from .core import *
from .models import *
EOF

# Create models.py
cat > "${SERVICE_DIR}/models.py" << EOF
"""
Data models for ${SERVICE_NAME} service.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ${SERVICE_NAME_CLASS}Base(BaseModel):
    """Base model for ${SERVICE_NAME}."""
    person_id: str


class ${SERVICE_NAME_CLASS}Create(${SERVICE_NAME_CLASS}Base):
    """Model for creating ${SERVICE_NAME}."""
    pass


class ${SERVICE_NAME_CLASS}Response(${SERVICE_NAME_CLASS}Base):
    """Response model for ${SERVICE_NAME}."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
EOF

# Create core.py
cat > "${SERVICE_DIR}/core.py" << EOF
"""
Core business logic for ${SERVICE_NAME} service.
"""

import logging
from typing import Optional, List
from datetime import datetime

from sakhi.libs.db import get_db_pool
from .models import ${SERVICE_NAME_CLASS}Create, ${SERVICE_NAME_CLASS}Response

logger = logging.getLogger(__name__)

__all__ = [
    "get_${SERVICE_NAME}",
    "create_${SERVICE_NAME}",
    "update_${SERVICE_NAME}",
    "delete_${SERVICE_NAME}",
]


async def get_${SERVICE_NAME}(person_id: str) -> Optional[${SERVICE_NAME_CLASS}Response]:
    """
    Get ${SERVICE_NAME} data for a user.

    Args:
        person_id: User ID

    Returns:
        ${SERVICE_NAME_CLASS}Response or None if not found
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            \"\"\"
            SELECT * FROM ${SERVICE_NAME}
            WHERE person_id = \$1
            ORDER BY created_at DESC
            LIMIT 1
            \"\"\",
            person_id
        )

        if not row:
            return None

        return ${SERVICE_NAME_CLASS}Response(**dict(row))


async def create_${SERVICE_NAME}(data: ${SERVICE_NAME_CLASS}Create) -> ${SERVICE_NAME_CLASS}Response:
    """
    Create a new ${SERVICE_NAME} record.

    Args:
        data: Creation data

    Returns:
        Created ${SERVICE_NAME_CLASS}Response
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            \"\"\"
            INSERT INTO ${SERVICE_NAME} (person_id, created_at)
            VALUES (\$1, NOW())
            RETURNING *
            \"\"\",
            data.person_id
        )

        return ${SERVICE_NAME_CLASS}Response(**dict(row))


async def update_${SERVICE_NAME}(
    person_id: str,
    **updates
) -> Optional[${SERVICE_NAME_CLASS}Response]:
    """
    Update ${SERVICE_NAME} data.

    Args:
        person_id: User ID
        **updates: Fields to update

    Returns:
        Updated ${SERVICE_NAME_CLASS}Response or None
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # TODO: Implement update logic
        pass


async def delete_${SERVICE_NAME}(person_id: str, record_id: str) -> bool:
    """
    Delete a ${SERVICE_NAME} record.

    Args:
        person_id: User ID
        record_id: Record to delete

    Returns:
        True if deleted, False if not found
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            \"\"\"
            DELETE FROM ${SERVICE_NAME}
            WHERE person_id = \$1 AND id = \$2
            \"\"\",
            person_id, record_id
        )
        return result == "DELETE 1"
EOF

# Replace placeholders
SERVICE_NAME_CLASS=$(echo "$SERVICE_NAME" | sed 's/_\([a-z]\)/\U\1/g' | sed 's/^\([a-z]\)/\U\1/')

find "$SERVICE_DIR" -name "*.py" -exec sed -i '' "s/\${SERVICE_NAME}/${SERVICE_NAME}/g" {} \;
find "$SERVICE_DIR" -name "*.py" -exec sed -i '' "s/\${SERVICE_NAME_CLASS}/${SERVICE_NAME_CLASS}/g" {} \;

echo "Created: $SERVICE_DIR/"
echo "  - __init__.py"
echo "  - models.py"
echo "  - core.py"

# Create test directory
mkdir -p "$TEST_DIR"

# Create unit test file
cat > "$TEST_FILE" << EOF
"""
Unit tests for ${SERVICE_NAME} service.
"""

import pytest
from unittest.mock import AsyncMock, patch

from sakhi.apps.api.services.${SERVICE_NAME}.core import (
    get_${SERVICE_NAME},
    create_${SERVICE_NAME},
)
from sakhi.apps.api.services.${SERVICE_NAME}.models import (
    ${SERVICE_NAME_CLASS}Create,
)


@pytest.fixture
def test_person_id():
    return "565bdb63-124b-4692-a039-846fddceff90"


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool."""
    with patch("sakhi.apps.api.services.${SERVICE_NAME}.core.get_db_pool") as mock:
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        mock.return_value = pool
        yield conn


@pytest.mark.asyncio
async def test_get_${SERVICE_NAME}_not_found(mock_db_pool, test_person_id):
    """Test get returns None when not found."""
    mock_db_pool.fetchrow.return_value = None

    result = await get_${SERVICE_NAME}(test_person_id)

    assert result is None
    mock_db_pool.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_create_${SERVICE_NAME}(mock_db_pool, test_person_id):
    """Test create ${SERVICE_NAME}."""
    from datetime import datetime
    import uuid

    mock_db_pool.fetchrow.return_value = {
        "id": str(uuid.uuid4()),
        "person_id": test_person_id,
        "created_at": datetime.now(),
        "updated_at": None,
    }

    data = ${SERVICE_NAME_CLASS}Create(person_id=test_person_id)
    result = await create_${SERVICE_NAME}(data)

    assert result is not None
    assert result.person_id == test_person_id
    mock_db_pool.fetchrow.assert_called_once()
EOF

# Create integration test file
cat > "$INTEGRATION_TEST_FILE" << EOF
"""
Integration tests for ${SERVICE_NAME} service.

These tests require a running database with test data.
Run with: pytest ${INTEGRATION_TEST_FILE} -v --tb=short
"""

import pytest
from sakhi.tests.fixtures import get_test_person_id, ensure_test_user

from sakhi.apps.api.services.${SERVICE_NAME}.core import (
    get_${SERVICE_NAME},
    create_${SERVICE_NAME},
    delete_${SERVICE_NAME},
)
from sakhi.apps.api.services.${SERVICE_NAME}.models import ${SERVICE_NAME_CLASS}Create


@pytest.fixture
async def test_person_id():
    """Get or create test user."""
    return await ensure_test_user()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_${SERVICE_NAME}_full_lifecycle(test_person_id):
    """
    Integration test: Create -> Get -> Delete lifecycle.

    This test verifies the full flow of ${SERVICE_NAME} operations
    against a real database.
    """
    # Create
    data = ${SERVICE_NAME_CLASS}Create(person_id=test_person_id)
    created = await create_${SERVICE_NAME}(data)

    assert created is not None
    assert created.person_id == test_person_id
    record_id = created.id

    # Get
    retrieved = await get_${SERVICE_NAME}(test_person_id)
    assert retrieved is not None
    assert retrieved.id == record_id

    # Delete
    deleted = await delete_${SERVICE_NAME}(test_person_id, record_id)
    assert deleted is True

    # Verify deleted
    # (Uncomment if your get returns None after delete)
    # after_delete = await get_${SERVICE_NAME}(test_person_id)
    # assert after_delete is None
EOF

echo "Created: $TEST_FILE"
echo "Created: $INTEGRATION_TEST_FILE"

# Print next steps
echo ""
echo "Next steps:"
echo "1. Create database table (if needed):"
echo "   sakhi/infra/scripts/migrations/NNNN_${SERVICE_NAME}.sql"
echo ""
echo "2. Run unit tests:"
echo "   pytest ${TEST_FILE} -v"
echo ""
echo "3. Run integration tests (requires DB):"
echo "   pytest ${INTEGRATION_TEST_FILE} -v -m integration"
echo ""
echo "4. Update docs:"
echo "   - CLAUDE.md (key services table)"
echo "   - docs/ARCHITECTURE.md (services section)"
echo "   - docs/BUILD_PLAN.md (if completing a planned feature)"
