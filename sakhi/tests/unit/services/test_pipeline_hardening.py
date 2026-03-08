import datetime as dt
from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.recommendations import context_builder
from sakhi.apps.engine.continuity import engine as continuity_engine
from sakhi.apps.worker.tasks import weekly_rhythm_rollup_worker


@pytest.mark.asyncio
async def test_load_continuity_falls_back_when_continuity_column_missing(monkeypatch: pytest.MonkeyPatch):
    async def fake_resolve_person_id(person_id: str) -> str:
        return person_id

    async def fake_q(sql: str, *args, one: bool = False):
        if "SELECT continuity_state" in sql:
            raise Exception('column "continuity_state" does not exist')
        return {
            "last_emotion": "anxious",
            "last_interaction_ts": dt.datetime(2026, 2, 1, 9, 30, tzinfo=dt.timezone.utc),
            "engagement_level": 0.8,
            "reflection_pending": True,
        }

    monkeypatch.setattr(continuity_engine, "resolve_person_id", fake_resolve_person_id)
    monkeypatch.setattr(continuity_engine, "q", fake_q)

    state = await continuity_engine.load_continuity("person-1")

    assert state["threads"]["current"] == "general"
    assert state["threads"]["confidence"] == pytest.approx(0.8)
    assert state["last_emotion_snapshots"][0]["emotion"] == "anxious"
    assert state["last_nudges"][0]["pending_reflection"] is True


@pytest.mark.asyncio
async def test_get_historical_effectiveness_filters_null_and_invalid_items(monkeypatch: pytest.MonkeyPatch):
    async def fake_dbfetch(sql: str, person_id: str):
        return [
            {
                "recommendation_type": "food",
                "recommendation_domain": None,
                "recommendation_content": '{"name": null}',
                "rating": 1.0,
                "was_followed": False,
            },
            {
                "recommendation_type": "food",
                "recommendation_domain": "coffee",
                "recommendation_content": '{"name": "Late coffee"}',
                "rating": 1.0,
                "was_followed": False,
            },
            {
                "recommendation_type": "practice",
                "recommendation_domain": "breathwork",
                "recommendation_content": "not-json",
                "rating": 4.0,
                "was_followed": True,
            },
            {
                "recommendation_type": "practice",
                "recommendation_domain": "breathwork",
                "recommendation_content": '{"name": "Breathwork"}',
                "rating": 5.0,
                "was_followed": True,
            },
        ]

    monkeypatch.setattr(context_builder, "dbfetch", fake_dbfetch)

    result = await context_builder.get_historical_effectiveness("person-1")

    assert result.effective_practices == ["breathwork", "Breathwork"]
    assert result.effective_foods == []
    assert result.ineffective_or_avoided == ["Late coffee"]
    assert all(isinstance(item, str) and item.strip() for item in result.ineffective_or_avoided)


@pytest.mark.asyncio
async def test_weekly_rollup_skips_when_rhythm_daily_curve_table_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "ENABLE_WEEKLY_RHYTHM_ROLLUP", True)

    async def fake_q(sql: str, *args, one: bool = False):
        if "to_regclass" in sql:
            table_name = args[0]
            if table_name == "public.rhythm_daily_curve":
                return {"relation_name": None}
            return {"relation_name": table_name}
        raise AssertionError(f"Unexpected query during skip path: {sql}")

    mock_dbexec = AsyncMock()
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "q", fake_q)
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "dbexec", mock_dbexec)

    result = await weekly_rhythm_rollup_worker.run_weekly_rhythm_rollup(person_id="person-1")

    assert result == {"processed": 0, "updated": 0, "skipped": "rhythm_daily_curve_missing"}
    mock_dbexec.assert_not_called()


@pytest.mark.asyncio
async def test_weekly_rollup_continues_when_rhythm_events_table_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "ENABLE_WEEKLY_RHYTHM_ROLLUP", True)

    async def fake_q(sql: str, *args, one: bool = False):
        if "to_regclass" in sql:
            table_name = args[0]
            if table_name in {"public.rhythm_daily_curve", "public.rhythm_weekly_rollups"}:
                return {"relation_name": table_name}
            if table_name == "public.rhythm_events":
                return {"relation_name": None}
        if "FROM rhythm_daily_curve" in sql:
            return []
        if "FROM rhythm_events" in sql:
            raise AssertionError("rhythm_events should not be queried when table is missing")
        raise AssertionError(f"Unexpected query: {sql}")

    mock_dbexec = AsyncMock()
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "q", fake_q)
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "dbexec", mock_dbexec)

    result = await weekly_rhythm_rollup_worker.run_weekly_rhythm_rollup(person_id="person-1")

    assert result == {"processed": 1, "updated": 1}
    assert mock_dbexec.await_count == 1


@pytest.mark.asyncio
async def test_weekly_rollup_skips_when_disabled_by_policy(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "ENABLE_WEEKLY_RHYTHM_ROLLUP", False)
    mock_q = AsyncMock()
    mock_dbexec = AsyncMock()
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "q", mock_q)
    monkeypatch.setattr(weekly_rhythm_rollup_worker, "dbexec", mock_dbexec)

    result = await weekly_rhythm_rollup_worker.run_weekly_rhythm_rollup(person_id="person-1")

    assert result == {"processed": 0, "updated": 0, "skipped": "disabled_by_policy"}
    mock_q.assert_not_called()
    mock_dbexec.assert_not_called()
