import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from sakhi.apps.api.main import app


@pytest.fixture(autouse=True)
def override_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENCRYPTION_KEY", "tests-secret-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sakhi")
    monkeypatch.setenv("SAKHI_POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/sakhi")
    monkeypatch.setenv("SAKHI_ENVIRONMENT", "test")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_post_journal_v2_flow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeConnection:
        async def fetchrow(self, query, *args):
            text = str(query)
            if "INSERT INTO public.journal_entries" in text:
                return {"id": "00000000-0000-0000-0000-000000000123"}
            return None

        async def execute(self, *args, **kwargs):
            return "OK"

    class _AcquireCtx:
        def __init__(self, conn: _FakeConnection) -> None:
            self._conn = conn

        async def __aenter__(self) -> _FakeConnection:
            return self._conn

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    class _FakePool:
        def __init__(self) -> None:
            self._conn = _FakeConnection()

        async def acquire(self) -> _AcquireCtx:
            return _AcquireCtx(self._conn)

    monkeypatch.setattr("sakhi.apps.api.main.get_async_pool", AsyncMock(return_value=_FakePool()))
    monkeypatch.setattr("sakhi.apps.api.main.enqueue_embedding_and_salience", AsyncMock())
    monkeypatch.setattr("sakhi.apps.api.main.capture_salient_memory", AsyncMock())
    monkeypatch.setattr(
        "sakhi.apps.api.main.classify_outer_inner",
        AsyncMock(return_value={
            "track": "outer",
            "timeline": {"horizon": "none"},
            "g_mvs": {
                "target_horizon": False,
                "current_position": False,
                "constraints": False,
                "criteria": False,
                "assets_blockers": False,
            },
            "intent_type": "activity",
        }),
    )

    form = {"raw": "Need a haircut", "mood": "neutral"}
    response = client.post(
        "/journal/v2",
        data=form,
        headers={"X-API-Key": "test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert "id" in body
    assert "follow_up" in body

    retrieval_response = client.post("/retrieval", json={"query": "Testing"})
    assert retrieval_response.status_code == 200
    data = retrieval_response.json()
    assert data["query"] == "Testing"
    assert isinstance(data["results"], list)
