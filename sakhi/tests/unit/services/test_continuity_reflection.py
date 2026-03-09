from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.continuity import reflection


@pytest.mark.asyncio
async def test_create_deep_reflection_job_queues_background_work(monkeypatch: pytest.MonkeyPatch):
    queued: list[tuple[str, tuple[object, ...]]] = []
    created_tasks: list[object] = []
    mock_log = AsyncMock()

    async def fake_dbexec(sql: str, *args):
        queued.append((" ".join(sql.split()), args))

    def fake_create_task(coro):
        created_tasks.append(coro)
        coro.close()
        return object()

    monkeypatch.setattr(reflection, "dbexec", fake_dbexec)
    monkeypatch.setattr(reflection.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(reflection, "log_turn_event", mock_log)

    payload = await reflection.create_deep_reflection_job("person-1", "career", window="180d")

    assert payload["status"] == "queued"
    assert payload["topic_key"] == "career"
    assert payload["window"] == "180d"
    assert created_tasks
    assert queued
    mock_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_deep_reflection_status_returns_row(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        reflection,
        "dbfetch",
        AsyncMock(
            return_value={
                "id": "r-1",
                "person_id": "person-1",
                "topic_key": "career",
                "status": "running",
                "error": None,
                "created_at": reflection.datetime(2026, 3, 4, tzinfo=reflection.UTC),
                "updated_at": reflection.datetime(2026, 3, 4, tzinfo=reflection.UTC),
            }
        ),
    )

    payload = await reflection.get_deep_reflection_status("r-1", "person-1")

    assert payload["reflection_id"] == "r-1"
    assert payload["status"] == "running"
    assert payload["topic_key"] == "career"


@pytest.mark.asyncio
async def test_get_deep_reflection_result_returns_done_payload_and_logs(monkeypatch: pytest.MonkeyPatch):
    mock_log = AsyncMock()
    monkeypatch.setattr(
        reflection,
        "dbfetch",
        AsyncMock(
            return_value={
                "id": "r-1",
                "person_id": "person-1",
                "topic_key": "career",
                "status": "done",
                "result_json": json.dumps({"origin_story": "Started around autonomy."}),
                "error": None,
            }
        ),
    )
    monkeypatch.setattr(reflection, "log_turn_event", mock_log)

    payload = await reflection.get_deep_reflection_result("r-1", "person-1")

    assert payload["status"] == "done"
    assert payload["result"]["origin_story"] == "Started around autonomy."
    mock_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_deep_reflection_job_persists_compiled_result(monkeypatch: pytest.MonkeyPatch):
    writes: list[tuple[str, tuple[object, ...]]] = []

    async def fake_dbexec(sql: str, *args):
        writes.append((" ".join(sql.split()), args))

    monkeypatch.setattr(reflection, "dbexec", fake_dbexec)
    monkeypatch.setattr(
        reflection,
        "get_continuity_arc",
        AsyncMock(
            return_value={
                "anchor": "career",
                "label": "Career",
                "window": {
                    "from": "2025-01-01T00:00:00+00:00",
                    "to": "2025-04-01T00:00:00+00:00",
                },
                "versions": {"inputs_hash": "hash-1"},
                "surface": {"coherence_score": 0.74},
                "arc": {
                    "span_days": 90.0,
                    "element_count": 4,
                    "phase_count": 3,
                    "features": {"direction": "flat"},
                    "phases": [
                        {
                            "index": 0,
                            "start_ts": "2025-01-01T00:00:00+00:00",
                            "end_ts": "2025-01-31T00:00:00+00:00",
                            "element_count": 2,
                            "stats": {"dominant_tag": {"label": "autonomy"}},
                        }
                    ],
                },
                "included_moments": [
                    {
                        "source_ref": "journal:a",
                        "ts": "2025-01-10T00:00:00+00:00",
                        "short_snippet": "Thinking about autonomy",
                        "facet": "autonomy",
                    }
                ],
            }
        ),
    )

    await reflection._run_deep_reflection_job(
        reflection_id="r-1",
        person_id="person-1",
        topic_key="career",
        window="120d",
        mode="topic_reflection",
        user_query=None,
    )

    assert len(writes) == 2
    assert "SET status = 'running'" in writes[0][0]
    assert "SET status = 'done'" in writes[1][0]
    persisted_result = json.loads(str(writes[1][1][-1]))
    assert persisted_result["chat_response_source"] == "deterministic"
    assert isinstance(persisted_result.get("chat_response"), str)
    assert "Started around autonomy." in persisted_result["chat_response"]


@pytest.mark.asyncio
async def test_run_deep_reflection_job_persists_llm_chat_response(monkeypatch: pytest.MonkeyPatch):
    writes: list[tuple[str, tuple[object, ...]]] = []

    async def fake_dbexec(sql: str, *args):
        writes.append((" ".join(sql.split()), args))

    class _FakeRouter:
        async def chat(self, **kwargs):
            return SimpleNamespace(
                text="You've moved from validation loops into building with more clarity.",
                model="gpt-4o-mini",
                provider="openai",
                usage={"total_tokens": 123},
            )

    monkeypatch.setattr(reflection, "dbexec", fake_dbexec)
    monkeypatch.setattr(reflection, "get_router", lambda: _FakeRouter())
    monkeypatch.setattr(
        reflection,
        "_build_reflection_llm_packet",
        AsyncMock(return_value={"topic_key": "career", "arc_compact_global": {"current_stage": "build"}}),
    )
    monkeypatch.setattr(
        reflection,
        "get_continuity_arc",
        AsyncMock(
            return_value={
                "anchor": "career",
                "label": "Career",
                "window": {
                    "from": "2025-01-01T00:00:00+00:00",
                    "to": "2025-04-01T00:00:00+00:00",
                },
                "versions": {"inputs_hash": "hash-1"},
                "surface": {"coherence_score": 0.74},
                "arc": {"phases": []},
                "included_moments": [],
            }
        ),
    )

    await reflection._run_deep_reflection_job(
        reflection_id="r-llm",
        person_id="person-1",
        topic_key="career",
        window="120d",
        mode="topic_reflection",
        user_query=None,
    )

    persisted_result = json.loads(str(writes[1][1][-1]))
    assert persisted_result["chat_response_source"] == "llm"
    assert persisted_result["chat_response"].startswith("You've moved from validation loops")
    assert persisted_result["deterministic_chat_response"]
    assert persisted_result["llm_reflection"]["enabled"] is True
    assert persisted_result["llm_reflection"]["input_packet"]["topic_key"] == "career"


@pytest.mark.asyncio
async def test_load_recent_topic_episodes_scores_topic_overlap(monkeypatch: pytest.MonkeyPatch):
    async def fake_dbfetch(sql: str, *args, **kwargs):
        assert "memory_episodic" in sql
        return [
            {
                "id": "epi-1",
                "summary": "Sakhi continuity and deterministic core are now clearer.",
                "ts": reflection.datetime(2026, 3, 6, tzinfo=reflection.UTC),
            },
            {
                "id": "epi-2",
                "summary": "General health note with no topic overlap.",
                "ts": reflection.datetime(2026, 3, 5, tzinfo=reflection.UTC),
            },
        ]

    monkeypatch.setattr(reflection, "dbfetch", fake_dbfetch)

    episodes = await reflection._load_recent_topic_episodes(
        person_id="person-1",
        topic_keywords={"sakhi", "continuity", "deterministic"},
    )

    assert episodes
    assert episodes[0]["id"] == "epi-1"
    assert episodes[0]["topic_overlap"] >= 1


@pytest.mark.asyncio
async def test_load_latest_turn_context_filters_to_topic_user_turns(monkeypatch: pytest.MonkeyPatch):
    async def fake_dbfetch(sql: str, *args, **kwargs):
        if "FROM conversation_turns" in sql:
            return [
                {
                    "role": "assistant",
                    "text": "Generic advice text",
                    "created_at": reflection.datetime(2026, 3, 6, 10, 0, tzinfo=reflection.UTC),
                },
                {
                    "role": "user",
                    "text": "Career load question",
                    "created_at": reflection.datetime(2026, 3, 6, 9, 0, tzinfo=reflection.UTC),
                },
                {
                    "role": "user",
                    "text": "Sakhi continuity is getting clearer with deterministic core.",
                    "created_at": reflection.datetime(2026, 3, 6, 8, 0, tzinfo=reflection.UTC),
                },
            ]
        if "FROM personal_model" in sql:
            return {
                "emotion_state": {"mood": "steady"},
                "rhythm_state": {"energy_level": "medium"},
                "longitudinal_state": {},
                "identity_momentum_state": {"phase": "steady"},
            }
        return None

    monkeypatch.setattr(reflection, "dbfetch", fake_dbfetch)

    payload = await reflection._load_latest_turn_context(
        person_id="person-1",
        topic_keywords={"sakhi", "continuity", "deterministic"},
    )

    assert payload["latest_topic_user_message"].startswith("Sakhi continuity")
    assert len(payload["recent_topic_user_turns"]) == 1
    assert payload["recent_topic_user_turns"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_build_reflection_llm_packet_skips_turn_context_for_topic_reflection(monkeypatch: pytest.MonkeyPatch):
    """Topic reflection should NOT call _load_latest_turn_context."""
    turn_context_called = False
    original_load = reflection._load_latest_turn_context

    async def spy_load(*args, **kwargs):
        nonlocal turn_context_called
        turn_context_called = True
        return await original_load(*args, **kwargs)

    monkeypatch.setattr(reflection, "_load_recent_topic_episodes", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        reflection,
        "_build_delta_since_last_reflection",
        AsyncMock(return_value={"has_previous": False}),
    )
    monkeypatch.setattr(reflection, "_load_latest_turn_context", spy_load)

    packet = await reflection._build_reflection_llm_packet(
        person_id="person-1",
        topic_key="sakhi",
        arc_payload={"included_moments": []},
        deterministic={
            "topic_label": "Sakhi",
            "window": {"from": "2026-01-01T00:00:00+00:00", "to": "2026-03-01T00:00:00+00:00"},
            "surface": {"detail_allowed": False, "mirror_allowed": True},
            "recurring_tensions": [],
            "key_pivots": [],
            "open_questions": [],
            "phase_packets": [],
            "arc_summary": {},
        },
        mode="topic_reflection",
        user_query=None,
    )

    assert not turn_context_called, "_load_latest_turn_context should not be called for topic_reflection"

    assert packet["surface"]["detail_allowed"] is False
    assert packet["response_contract"]["voice"] == "friend, warm, direct"
    assert packet["response_contract"]["priority"] == "longitudinal_reflection"


@pytest.mark.asyncio
async def test_build_reflection_llm_packet_prefers_provided_query(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(reflection, "_load_recent_topic_episodes", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        reflection,
        "_build_delta_since_last_reflection",
        AsyncMock(return_value={"has_previous": False}),
    )
    monkeypatch.setattr(
        reflection,
        "_load_latest_turn_context",
        AsyncMock(
            return_value={
                "latest_topic_user_message": "Recovered topic message",
                "recent_topic_user_turns": [],
            }
        ),
    )

    packet = await reflection._build_reflection_llm_packet(
        person_id="person-1",
        topic_key="sakhi",
        arc_payload={"included_moments": []},
        deterministic={
            "topic_label": "Sakhi",
            "window": {"from": "2026-01-01T00:00:00+00:00", "to": "2026-03-01T00:00:00+00:00"},
            "surface": {"detail_allowed": True, "mirror_allowed": True},
            "recurring_tensions": [],
            "key_pivots": [],
            "open_questions": [],
            "phase_packets": [],
            "arc_summary": {},
        },
        mode="deep_answer",
        user_query="Should we run MVP pilots before pre-seed?",
    )

    assert packet["request_mode"] == "deep_answer"
    assert packet["current_query"]["source"] == "provided"
    assert packet["current_query"]["text"] == "Should we run MVP pilots before pre-seed?"
    assert packet["latest_turn_context"]["effective_user_query_source"] == "provided"
    assert packet["response_contract"]["length_words"] == "150-250"
    assert packet["response_contract"]["min_words"] == 150
    assert packet["response_contract"]["max_words"] == 250
    assert "required_sections" not in packet["response_contract"]


def test_build_deep_reflection_prompt_messages_uses_language_first_sections():
    packet = {
        "topic_key": "sakhi",
        "topic_label": "Sakhi",
        "request_mode": "deep_answer",
        "current_query": {"text": "Should continuity be our core offering?", "source": "provided"},
        "surface": {"detail_allowed": True, "mirror_allowed": True},
        "arc_compact_global": {
            "origin_story": "Started around ayurveda engine.",
            "current_stage": "Currently centered on deterministic core.",
            "key_pivots": ["Shifted from validation toward deterministic core."],
            "recurring_tensions": ["Recurring return to founder alignment."],
            "open_questions": ["Whether this thread stays centered."],
            "phase_compaction": [
                {"summary": "Started around ayurveda engine."},
                {"summary": "Shifted toward validation."},
                {"summary": "Centered on deterministic core."},
            ],
        },
        "evidence_anchors": [{"snippet": "We decided to focus on continuity."}],
        "recent_episode_compact": [{"summary": "Career and product narrative pressure."}],
        "latest_turn_context": {
            "latest_topic_user_message": "Should continuity be our core offering?",
            "state_hints": {"emotion_hint": "focused"},
        },
        "delta_since_last_reflection": {"has_previous": True, "current_stage_changed": False},
        "response_contract": {
            "voice": "friend, warm, direct",
            "length_words": "180-280",
            "max_questions": 1,
            "avoid": ["therapy-speak", "ayurvedic jargon"],
            "format": "single short paragraph",
            "detail_allowed": True,
            "mirror_allowed": True,
        },
    }

    messages = reflection._build_deep_reflection_prompt_messages(packet)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    user_prompt = messages[1]["content"]
    assert "History on this topic:" in user_prompt
    assert "What we know about this person on this topic:" in user_prompt
    assert "Current query now:" in user_prompt
    assert "Prioritize answering the current query directly." in user_prompt
    assert "Use history and person context as grounding, not as a detour." in user_prompt
    assert "Mode: deep_answer" in user_prompt
    assert "Current query source: provided" in user_prompt
    assert "Response contract:" in user_prompt
    assert "Should continuity be our core offering?" in user_prompt
    assert "PACKET:" not in user_prompt


@pytest.mark.asyncio
async def test_run_deep_reflection_job_falls_back_when_window_write_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    writes: list[str] = []

    async def fake_dbexec(sql: str, *args):
        normalized = " ".join(sql.split())
        writes.append(normalized)
        if "window_start = $2::timestamptz" in normalized:
            raise RuntimeError(
                'column "window_start" is of type date but expression is of type timestamp with time zone'
            )

    monkeypatch.setattr(reflection, "dbexec", fake_dbexec)
    monkeypatch.setattr(
        reflection,
        "get_continuity_arc",
        AsyncMock(
            return_value={
                "anchor": "career",
                "label": "Career",
                "window": {
                    "from": "2025-01-01T00:00:00+00:00",
                    "to": "2025-04-01T00:00:00+00:00",
                },
                "versions": {"inputs_hash": "hash-1"},
                "surface": {"coherence_score": 0.74},
                "arc": {"phases": []},
                "included_moments": [],
            }
        ),
    )

    await reflection._run_deep_reflection_job(
        reflection_id="r-2",
        person_id="person-1",
        topic_key="career",
        window="120d",
        mode="topic_reflection",
        user_query=None,
    )

    assert any("SET status = 'running'" in sql for sql in writes)
    assert any("window_start = $2::timestamptz" in sql for sql in writes)
    assert any(
        "SET status = 'done'" in sql and "window_start = $2::timestamptz" not in sql
        for sql in writes
    )
    assert not any("SET status = 'failed'" in sql for sql in writes)
