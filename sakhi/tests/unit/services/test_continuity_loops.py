"""Unit tests for the open loops ledger."""
from __future__ import annotations

import pytest

from sakhi.apps.api.services.continuity.loops import _parse_llm_list


# =============================================================================
# _parse_llm_list (pure, no DB)
# =============================================================================


def test_parse_llm_list_valid_array():
    raw = '["whether to take the new role", "which co-founder to go with"]'
    result = _parse_llm_list(raw)
    assert result == ["whether to take the new role", "which co-founder to go with"]


def test_parse_llm_list_empty_array():
    assert _parse_llm_list("[]") == []


def test_parse_llm_list_empty_string():
    assert _parse_llm_list("") == []


def test_parse_llm_list_strips_markdown_fences():
    raw = '```json\n["send the proposal to Sarah"]\n```'
    result = _parse_llm_list(raw)
    assert result == ["send the proposal to Sarah"]


def test_parse_llm_list_caps_whitespace_in_items():
    raw = '["  reach out to James  ", "  decide on pricing  "]'
    result = _parse_llm_list(raw)
    assert result == ["reach out to James", "decide on pricing"]


def test_parse_llm_list_invalid_json_returns_empty():
    assert _parse_llm_list("not json at all") == []


def test_parse_llm_list_filters_empty_items():
    raw = '["valid item", "", "  ", "another item"]'
    result = _parse_llm_list(raw)
    assert result == ["valid item", "another item"]


# =============================================================================
# get_open_loops (mocked DB)
# =============================================================================


@pytest.mark.asyncio
async def test_get_open_loops_splits_by_type(monkeypatch):
    import datetime as dt

    fake_rows = [
        {"id": "aaa", "loop_type": "open_decision", "topic": "whether to take the role",
         "topic_key": "career", "stance": "quality", "status": "open",
         "first_raised_at": dt.datetime(2026, 4, 20), "last_updated_at": dt.datetime(2026, 4, 22),
         "resolved_at": None},
        {"id": "bbb", "loop_type": "conversation_commitment", "topic": "reach out to James by Friday",
         "topic_key": None, "stance": None, "status": "open",
         "first_raised_at": dt.datetime(2026, 4, 21), "last_updated_at": dt.datetime(2026, 4, 21),
         "resolved_at": None},
    ]

    async def _fake_fetch(*args, **kwargs):
        return fake_rows

    monkeypatch.setattr("sakhi.apps.api.services.continuity.loops.dbfetch", _fake_fetch)

    from sakhi.apps.api.services.continuity.loops import get_open_loops

    result = await get_open_loops("person-1")
    assert len(result["decisions"]) == 1
    assert len(result["commitments"]) == 1
    assert result["decisions"][0]["topic"] == "whether to take the role"
    assert result["commitments"][0]["topic"] == "reach out to James by Friday"


@pytest.mark.asyncio
async def test_get_open_loops_handles_db_error(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("DB down")

    monkeypatch.setattr("sakhi.apps.api.services.continuity.loops.dbfetch", _fail)

    from sakhi.apps.api.services.continuity.loops import get_open_loops

    result = await get_open_loops("person-1")
    assert result == {"decisions": [], "commitments": []}


# =============================================================================
# open_loops in conversation prompt
# =============================================================================


def test_open_loops_appear_in_prompt_when_stale_loops_present():
    from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt

    metadata = {
        "continuity_pack": {
            "topic_key": "career",
            "open_loops": {
                "decisions": [{"id": "aaa", "topic": "whether to take the new role", "topic_key": "career"}],
                "commitments": [{"id": "bbb", "topic": "reach out to James by Friday", "topic_key": None}],
            },
        }
    }
    ctx = {"conversation": {"last_emotion": "neutral", "energy_level": 0.5}}
    tone = {"style": "direct", "pace": "balanced", "mirroring": {}}
    result = build_prompt("I'm feeling scattered", ctx, tone, metadata=metadata)
    assert "OPEN LOOPS" in result
    assert "whether to take the new role" in result
    assert "reach out to James by Friday" in result


def test_open_loops_absent_when_none():
    from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt

    metadata = {"continuity_pack": {"topic_key": "career", "open_loops": None}}
    ctx = {"conversation": {"last_emotion": "neutral", "energy_level": 0.5}}
    tone = {"style": "direct", "pace": "balanced", "mirroring": {}}
    result = build_prompt("How am I doing?", ctx, tone, metadata=metadata)
    assert "OPEN LOOPS" not in result


def test_open_loops_in_public_continuity_signal():
    from sakhi.apps.api.routes.turn_v2 import _build_public_continuity_signal

    pack = {
        "topic_key": "career",
        "surface": {"mirror_allowed": True, "detail_allowed": True},
        "history_compact": {"element_count": 8},
        "open_loops": {
            "decisions": [{"id": "aaa", "topic": "whether to take the new role"}],
            "commitments": [],
        },
    }
    signal = _build_public_continuity_signal(pack)
    assert signal is not None
    assert signal["open_loops"]["decisions"][0]["topic"] == "whether to take the new role"
