import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")

from sakhi.apps.api.routes import soul_analytics  # noqa: E402


@pytest.mark.asyncio
async def test_soul_state_endpoint(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return {
            "soul_state": {
                "core_values": ["growth"],
                "longing": ["balance"],
                "aversions": ["burnout"],
                "identity_themes": ["learning"],
                "commitments": ["practice"],
                "confidence": 0.7,
                "updated_at": "now",
            },
            "soul_shadow": ["doubt"],
            "soul_light": ["optimism"],
            "soul_conflicts": ["rest vs action"],
            "soul_friction": ["balance vs overwork"],
        }

    monkeypatch.setattr(soul_analytics, "q", fake_q)
    app = FastAPI()
    app.include_router(soul_analytics.router)
    client = TestClient(app)
    resp = client.get("/soul/state/p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["core_values"] == ["growth"]
    assert body["shadow"] == ["doubt"]


@pytest.mark.asyncio
async def test_soul_timeline(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {
                "soul_shadow": ["doubt"],
                "soul_light": ["hope"],
                "soul_conflict": ["rest vs action"],
                "soul_friction": ["balance vs overwork"],
                "updated_at": None,
            }
        ]

    monkeypatch.setattr(soul_analytics, "q", fake_q)
    app = FastAPI()
    app.include_router(soul_analytics.router)
    client = TestClient(app)
    resp = client.get("/soul/timeline/p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["shadow"] == ["doubt"]


@pytest.mark.asyncio
async def test_soul_summary(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {
                "soul_shadow": ["doubt"],
                "soul_light": ["hope"],
                "soul_conflict": ["rest vs action"],
                "soul_friction": ["balance vs overwork"],
                "updated_at": None,
            },
            {
                "soul_shadow": ["avoidance"],
                "soul_light": ["optimism"],
                "soul_conflict": ["rest vs action"],
                "soul_friction": ["balance vs overwork"],
                "updated_at": None,
            },
        ]

    monkeypatch.setattr(soul_analytics, "q", fake_q)
    app = FastAPI()
    app.include_router(soul_analytics.router)
    client = TestClient(app)
    resp = client.get("/soul/summary/p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["top_shadow"][0] in ["doubt", "avoidance"]
    assert body["dominant_friction"] == "balance vs overwork"
