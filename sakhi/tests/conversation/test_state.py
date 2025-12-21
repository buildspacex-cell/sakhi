import pytest

from sakhi.libs.conversation.state import ConversationState, ConversationStateStore


def test_conversation_state_stack_operations() -> None:
    state = ConversationState(conversation_id="conv-123", user_id="user-1")

    first = state.ensure_active("journaling", slots={"entry_id": "1"})
    assert first.name == "journaling"
    assert state.peek() is first

    second = state.ensure_active("planning", slots={"objective": "Focus"})
    assert second.name == "planning"
    assert state.peek() is second
    assert first.status == "paused"

    resumed = state.ensure_active("journaling")
    assert resumed is first
    assert resumed.status == "active"
    assert state.peek() is resumed


@pytest.mark.asyncio
async def test_state_store_graceful_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeConnection:
        async def fetchrow(self, *args, **kwargs):  # pragma: no cover - invoked via store
            raise RuntimeError("missing table")

        async def execute(self, *args, **kwargs):  # pragma: no cover - invoked via store
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

    monkeypatch.setattr("sakhi.libs.conversation.state.get_async_pool", _fake_get_pool)

    state = await ConversationStateStore.load("conv-test", user_id="user-99")
    assert state.conversation_id == "conv-test"
    assert state.user_id == "user-99"
    # Saving should be a no-op because the fake pool raises
    await ConversationStateStore.save(state)
