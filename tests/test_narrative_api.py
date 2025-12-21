import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_narrative_api_smoke(monkeypatch):
    async def fake_q(query, *args, **kwargs):
        return {"soul_narrative": {"identity_arc": "test"}}

    monkeypatch.setattr("sakhi.apps.api.routes.narrative.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/soul/narrative/demo")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_alignment_api_smoke(monkeypatch):
    async def fake_q(query, *args, **kwargs):
        return {"alignment_state": {"alignment_score": 0.5}}

    monkeypatch.setattr("sakhi.apps.api.routes.narrative.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/soul/alignment/demo")
    assert resp.status_code == 200
