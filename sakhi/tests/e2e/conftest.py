"""
E2E Test Configuration

Specialized conftest for end-to-end tests that require:
- Real LLM calls (not mocked)
- Full app lifespan initialization
- Database connections
"""

import os
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager

# Ensure environment is loaded before importing app
from dotenv import load_dotenv
from pathlib import Path

env_local_path = Path(__file__).parents[3] / ".env.local"
if env_local_path.exists():
    load_dotenv(env_local_path, override=True)


@pytest_asyncio.fixture(scope="function")
async def api_client():
    """
    HTTP client for E2E tests with full lifespan initialization.

    This fixture properly triggers the app's lifespan context,
    which initializes the LLM router with real providers.
    """
    from httpx import AsyncClient, ASGITransport
    from sakhi.apps.api.main import app, lifespan

    # Manually run lifespan to initialize LLM router
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture(scope="function")
async def api_client_no_lifespan():
    """
    HTTP client without lifespan - for testing startup behavior.
    """
    from httpx import AsyncClient, ASGITransport
    from sakhi.apps.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
