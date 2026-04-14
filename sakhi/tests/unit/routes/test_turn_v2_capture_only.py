from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sakhi.apps.api.routes import turn_v2
from sakhi.apps.api.services.conversation import orchestrator


def test_build_capture_only_worker_payload_uses_first_intent_when_available():
    payload = turn_v2._build_capture_only_worker_payload(
        text="Need to put this somewhere safe.",
        ts_iso="2026-04-10T10:00:00Z",
        entry_id="entry-123",
        emotion={"emotion": "overwhelmed"},
        intents=[{"intent_type": "offload"}],
        topics=["workload", "stress"],
        plans=[],
        triage={"slots": {"mood_affect": {"label": "overwhelmed"}}},
        layer="offload",
    )

    assert payload["entry_id"] == "entry-123"
    assert payload["layer"] == "offload"
    assert payload["facets"]["intent"] == {"intent_type": "offload"}
    assert payload["facets"]["topics"] == ["workload", "stress"]


@pytest.mark.asyncio
async def test_orchestrate_turn_capture_only_passes_source_and_client_id():
    observe = AsyncMock(return_value={"id": "client-offload-1"})

    def _drain_task(coro):
        coro.close()
        return MagicMock()

    with patch(
        "sakhi.apps.api.services.conversation.orchestrator.observe_entry",
        observe,
    ), patch(
        "sakhi.apps.api.services.conversation.orchestrator.generate_journal_embedding",
        AsyncMock(return_value=[]),
    ), patch(
        "sakhi.apps.api.services.conversation.orchestrator.asyncio.create_task",
        side_effect=_drain_task,
    ) as create_task:
        result = await orchestrator.orchestrate_turn(
            person_id="person-123",
            text="I need to offload this without a reply.",
            capture_only=True,
            skip_llm=True,
            source="offload",
            client_id="client-offload-1",
        )

    observe.assert_awaited_once()
    kwargs = observe.await_args.kwargs
    assert kwargs["source"] == "offload"
    assert kwargs["entry_id"] == "client-offload-1"
    assert result["entry_id"] == "client-offload-1"
    create_task.assert_called_once()
