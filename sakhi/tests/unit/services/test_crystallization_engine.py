import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from kala.pattern.trajectory import PatternCandidate
from sakhi.apps.api.services.crystallization import engine


@pytest.mark.asyncio
async def test_crystallize_pattern_parses_string_trajectory_data(monkeypatch: pytest.MonkeyPatch):
    candidate = PatternCandidate(
        pattern_type="theme",
        pattern_value="focus",
        mention_count=4,
        distinct_days=3,
        avg_confidence=0.8,
        first_seen=datetime.now(timezone.utc) - timedelta(days=5),
        last_seen=datetime.now(timezone.utc),
        evidence_ids=["11111111-1111-1111-1111-111111111111"],
        evidence_snippets=[{"id": "x1", "date": "2026-02-20", "snippet": "test snippet"}],
    )

    async def fake_dbfetch(query: str, *args, **kwargs):
        if "SELECT id, mention_count, confidence, last_seen, trajectory_data" in query:
            return {
                "id": "22222222-2222-2222-2222-222222222222",
                "mention_count": 2,
                "confidence": 0.5,
                "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                "trajectory_data": '{"2026-02-20T00:00:00+00:00":{"mentions":2}}',
            }
        raise AssertionError(f"Unexpected dbfetch query: {query[:80]}")

    captured: dict[str, str] = {}

    async def fake_dbexec(query: str, *args):
        captured["trajectory_data_json"] = args[8]

    log_mock = AsyncMock()

    monkeypatch.setattr(engine, "dbfetch", fake_dbfetch)
    monkeypatch.setattr(engine, "dbexec", fake_dbexec)
    monkeypatch.setattr(engine, "_log_crystallization", log_mock)

    pattern_id = await engine.crystallize_pattern(
        person_id="person-1",
        candidate=candidate,
        final_confidence=0.82,
    )

    assert pattern_id == "22222222-2222-2222-2222-222222222222"
    stored = json.loads(captured["trajectory_data_json"])
    assert "2026-02-20T00:00:00+00:00" in stored
    assert len(stored) == 2
    log_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_crystallize_pattern_handles_malformed_trajectory_data(monkeypatch: pytest.MonkeyPatch):
    candidate = PatternCandidate(
        pattern_type="theme",
        pattern_value="consistency",
        mention_count=3,
        distinct_days=2,
        avg_confidence=0.7,
        first_seen=datetime.now(timezone.utc) - timedelta(days=3),
        last_seen=datetime.now(timezone.utc),
        evidence_ids=["33333333-3333-3333-3333-333333333333"],
        evidence_snippets=[{"id": "x2", "date": "2026-02-22", "snippet": "another test snippet"}],
    )

    async def fake_dbfetch(query: str, *args, **kwargs):
        if "SELECT id, mention_count, confidence, last_seen, trajectory_data" in query:
            return {
                "id": "44444444-4444-4444-4444-444444444444",
                "mention_count": 1,
                "confidence": 0.4,
                "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                "trajectory_data": "not-json",
            }
        raise AssertionError(f"Unexpected dbfetch query: {query[:80]}")

    captured: dict[str, str] = {}

    async def fake_dbexec(query: str, *args):
        captured["trajectory_data_json"] = args[8]

    monkeypatch.setattr(engine, "dbfetch", fake_dbfetch)
    monkeypatch.setattr(engine, "dbexec", fake_dbexec)
    monkeypatch.setattr(engine, "_log_crystallization", AsyncMock())

    pattern_id = await engine.crystallize_pattern(
        person_id="person-2",
        candidate=candidate,
        final_confidence=0.75,
    )

    assert pattern_id == "44444444-4444-4444-4444-444444444444"
    stored = json.loads(captured["trajectory_data_json"])
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_crystallize_patterns_skips_decay_on_daily_runs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(engine, "aggregate_pattern_occurrences", AsyncMock(return_value={}))
    decay_mock = AsyncMock(return_value=4)
    monkeypatch.setattr(engine, "decay_stale_patterns", decay_mock)

    result = await engine.crystallize_patterns(
        person_id="person-daily",
        window_days=14,
        run_type="daily",
    )

    assert result.patterns_decayed == 0
    decay_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_crystallize_patterns_applies_decay_on_weekly_runs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(engine, "aggregate_pattern_occurrences", AsyncMock(return_value={}))
    decay_mock = AsyncMock(return_value=3)
    monkeypatch.setattr(engine, "decay_stale_patterns", decay_mock)

    result = await engine.crystallize_patterns(
        person_id="person-weekly",
        window_days=30,
        run_type="weekly",
    )

    assert result.patterns_decayed == 3
    decay_mock.assert_awaited_once_with("person-weekly")
