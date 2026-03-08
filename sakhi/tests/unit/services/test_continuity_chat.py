from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.continuity import chat


@pytest.mark.asyncio
async def test_build_continuity_pack_returns_none_when_policy_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat, "get_continuity_policy", AsyncMock(return_value={"enabled": False, "exclusions": []}))

    result = await chat.build_continuity_pack("person-1", "How is this pattern changing?")

    assert result is None


@pytest.mark.asyncio
async def test_build_continuity_pack_builds_compact_arc_and_orders_evidence(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat, "get_continuity_policy", AsyncMock(return_value={"enabled": True, "exclusions": []}))
    monkeypatch.setattr(
        chat,
        "_load_acknowledged_assistant_signals",
        AsyncMock(
            return_value=[
                {
                    "ts": "2026-01-25T08:00:00+00:00",
                    "assistant_snippet": "Try picking one role story and repeating it.",
                    "user_ack": "Yes, that helps.",
                    "source_ref": "conversation_turns",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        chat,
        "classify_continuity_text",
        lambda text: {
            "primary_anchor": "career",
            "anchor_state": "CONFIDENT",
        },
    )
    monkeypatch.setattr(chat, "load_journal_entries_for_continuity", AsyncMock(return_value=[{"id": "a"}]))
    monkeypatch.setattr(
        chat,
        "compile_journal_continuity",
        lambda person_id, journal_rows: {
            "taxonomy_version": "2026.03.03",
            "compiler_version": "2026.03.03.1",
            "threshold_profile_version": "2026.03.03.1",
            "inputs_hash": "abc123",
        },
    )
    monkeypatch.setattr(
        chat,
        "select_compiled_topic",
        lambda compiled, anchor, debug=False: {
            "label": "Career",
            "confidence": 0.79,
            "surface": {"mirror_allowed": True, "detail_allowed": True},
            "arc": {
                "phase_count": 3,
                "phases": [
                    {
                        "start_ts": "2026-01-01T08:00:00+00:00",
                        "end_ts": "2026-01-10T08:00:00+00:00",
                        "element_count": 2,
                        "stats": {"dominant_tag": {"label": "promotion"}},
                    },
                    {
                        "start_ts": "2026-01-11T08:00:00+00:00",
                        "end_ts": "2026-01-20T08:00:00+00:00",
                        "element_count": 2,
                        "stats": {"dominant_tag": {"label": "boundary"}},
                    },
                    {
                        "start_ts": "2026-01-21T08:00:00+00:00",
                        "end_ts": "2026-01-30T08:00:00+00:00",
                        "element_count": 2,
                        "stats": {"dominant_tag": {"label": "leadership"}},
                    },
                ],
                "event_refs": [
                    {
                        "day": 1,
                        "ts": "2026-01-01T08:00:00+00:00",
                        "source_ref": "journal:a",
                        "excerpt": "I keep thinking about the promotion question.",
                    },
                    {
                        "day": 10,
                        "ts": "2026-01-10T08:00:00+00:00",
                        "source_ref": "journal:b",
                        "excerpt": "The role tension is back.",
                    },
                    {
                        "day": 20,
                        "ts": "2026-01-20T08:00:00+00:00",
                        "source_ref": "journal:c",
                        "excerpt": "Leadership now feels like the stronger thread.",
                    },
                ],
            },
            "entry_tags": {
                "1|2026-01-01T08:00:00+00:00": {"confidence": 0.7, "decision_state": "questioning", "stance": "unclear"},
                "10|2026-01-10T08:00:00+00:00": {"confidence": 0.8, "decision_state": "reversed", "stance": "away"},
                "20|2026-01-20T08:00:00+00:00": {"confidence": 0.9, "decision_state": "resolved", "stance": "toward"},
            },
        },
    )

    pack = await chat.build_continuity_pack(
        "person-1",
        "I keep returning to the promotion question.",
        evidence_limit=2,
    )

    assert pack is not None
    assert pack["topic_key"] == "career"
    assert pack["arc_compact"]["start_signal"] == "started around promotion"
    assert pack["arc_compact"]["current_signal"] == "currently centered on leadership"
    assert pack["history_compact"]["phase_count"] == 3
    assert len(pack["history_compact"]["phase_path"]) == 3
    assert len(pack["history_compact"]["anchor_points"]) == 3
    assert pack["history_compact"]["qualitative_mode"] == "detailed"
    assert "started around promotion" in pack["history_compact"]["qualitative_arc_summary"]
    assert len(pack["history_compact"]["decision_ledger"]) >= 2
    assert any(
        item.get("source") == "accepted_sakhi_suggestion"
        for item in pack["history_compact"]["decision_ledger"]
    )
    assert len(pack["evidence"]) == 2
    assert [item["source_ref"] for item in pack["evidence"]] == ["journal:a", "journal:c"]


@pytest.mark.asyncio
async def test_build_continuity_pack_uses_mirror_only_qualitative_summary_when_detail_blocked(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(chat, "get_continuity_policy", AsyncMock(return_value={"enabled": True, "exclusions": []}))
    monkeypatch.setattr(chat, "_load_acknowledged_assistant_signals", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        chat,
        "classify_continuity_text",
        lambda text: {
            "primary_anchor": "career",
            "anchor_state": "CONFIDENT",
        },
    )
    monkeypatch.setattr(chat, "load_journal_entries_for_continuity", AsyncMock(return_value=[{"id": "a"}]))
    monkeypatch.setattr(
        chat,
        "compile_journal_continuity",
        lambda person_id, journal_rows: {
            "taxonomy_version": "2026.03.03",
            "compiler_version": "2026.03.03.1",
            "threshold_profile_version": "2026.03.03.1",
            "inputs_hash": "abc123",
        },
    )
    monkeypatch.setattr(
        chat,
        "select_compiled_topic",
        lambda compiled, anchor, debug=False: {
            "label": "Career",
            "confidence": 0.79,
            "surface": {"mirror_allowed": True, "detail_allowed": False},
            "arc": {
                "phase_count": 2,
                "phases": [
                    {
                        "start_ts": "2026-01-01T08:00:00+00:00",
                        "end_ts": "2026-01-10T08:00:00+00:00",
                        "element_count": 2,
                        "stats": {"dominant_tag": {"label": "promotion"}},
                    },
                    {
                        "start_ts": "2026-01-11T08:00:00+00:00",
                        "end_ts": "2026-01-20T08:00:00+00:00",
                        "element_count": 2,
                        "stats": {"dominant_tag": {"label": "leadership"}},
                    },
                ],
                "event_refs": [
                    {
                        "day": 1,
                        "ts": "2026-01-01T08:00:00+00:00",
                        "source_ref": "journal:a",
                        "excerpt": "I keep thinking about the promotion question.",
                    },
                    {
                        "day": 20,
                        "ts": "2026-01-20T08:00:00+00:00",
                        "source_ref": "journal:c",
                        "excerpt": "Leadership now feels like the stronger thread.",
                    },
                ],
            },
            "entry_tags": {
                "1|2026-01-01T08:00:00+00:00": {"confidence": 0.7},
                "20|2026-01-20T08:00:00+00:00": {"confidence": 0.9},
            },
        },
    )

    pack = await chat.build_continuity_pack(
        "person-1",
        "How is this career thread evolving?",
        evidence_limit=2,
    )

    assert pack is not None
    assert pack["history_compact"]["qualitative_mode"] == "mirror_only"
    summary = pack["history_compact"]["qualitative_arc_summary"]
    assert "started around promotion" in summary
    assert "built from" not in summary


@pytest.mark.asyncio
async def test_load_acknowledged_assistant_signals_requires_topic_match_and_acceptance(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_dbfetch(sql: str, *args, **kwargs):
        assert "FROM conversation_turns" in sql
        return [
            {
                "role": "user",
                "text": "Yes, let's do that.",
                "created_at": chat.datetime(2026, 3, 6, 10, 2, tzinfo=chat.UTC),
            },
            {
                "role": "assistant",
                "text": "Pick one Sakhi story and repeat it consistently.",
                "created_at": chat.datetime(2026, 3, 6, 10, 1, tzinfo=chat.UTC),
            },
            {
                "role": "user",
                "text": "For Sakhi continuity, what should I prioritize?",
                "created_at": chat.datetime(2026, 3, 6, 10, 0, tzinfo=chat.UTC),
            },
            {
                "role": "assistant",
                "text": "Unrelated answer",
                "created_at": chat.datetime(2026, 3, 6, 9, 1, tzinfo=chat.UTC),
            },
            {
                "role": "user",
                "text": "How is weather?",
                "created_at": chat.datetime(2026, 3, 6, 9, 0, tzinfo=chat.UTC),
            },
        ]

    monkeypatch.setattr(chat, "dbfetch", fake_dbfetch)

    signals = await chat._load_acknowledged_assistant_signals(
        person_id="person-1",
        topic_keywords={"sakhi", "continuity"},
    )

    assert len(signals) == 1
    assert "Sakhi story" in signals[0]["assistant_snippet"]
