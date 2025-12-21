import pytest
from httpx import ASGITransport, AsyncClient

from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
