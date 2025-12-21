import pytest

from sakhi.libs.memory.store import fetch_recent_memories


@pytest.mark.asyncio
async def test_fetch_recent_memories_graceful_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeConnection:
        async def fetch(self, *args, **kwargs):  # pragma: no cover - executed by fetch_recent
            raise RuntimeError("missing table")

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

    async def _fake_get_pool():  # pragma: no cover - patched in test
        return _FakePool()

    monkeypatch.setattr("sakhi.libs.memory.store.get_async_pool", _fake_get_pool)

    results = await fetch_recent_memories("user-abc", limit=5)
    assert results == []
