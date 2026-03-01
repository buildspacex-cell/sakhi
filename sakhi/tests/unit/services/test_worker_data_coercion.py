import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from sakhi.apps.engine.forecast import engine as forecast_engine
from sakhi.apps.worker.tasks import body_refresh
from sakhi.apps.worker.tasks import emotion_loop_refresh as emotion_loop_refresh_worker
from sakhi.apps.worker.tasks import forecast as forecast_worker
from sakhi.core.rhythm.rhythm_soul_engine import compute_deep_rhythm_soul


@pytest.mark.asyncio
async def test_body_refresh_limits_pattern_detection_runtime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BODY_REFRESH_PATTERN_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr(
        body_refresh,
        "update_body_state_from_health_data",
        AsyncMock(
            return_value={
                "summary": {"overall_score": 0.7, "primary_need": "rest"},
                "dosha_body": {"dominant_imbalance": "vata"},
            }
        ),
    )

    async def slow_detect_patterns(person_id: str, lookback_days: int = 14):
        await asyncio.sleep(2)
        return [{"name": "late_sleep"}]

    monkeypatch.setattr(
        "sakhi.apps.api.services.ayurveda.pattern_learning.detect_patterns",
        slow_detect_patterns,
    )

    result = await body_refresh.run_body_refresh("person-1")

    assert result["success"] is True
    assert result["patterns_detected"] == 0


@pytest.mark.asyncio
async def test_compute_forecast_handles_json_string_states(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql: str, *args, one: bool = False):
        if "SELECT identity_state, conflict_state, coherence_state, pattern_sense, forecast_state" in sql:
            return {
                "identity_state": '{"drift_score": -0.1}',
                "conflict_state": "{}",
                "coherence_state": '{"fragmentation_index": 0.2}',
                "pattern_sense": "{}",
                "forecast_state": "{}",
            }
        if "SELECT emotion_loop FROM memory_episodic" in sql:
            return [{"emotion_loop": '{"trend": 0.3}'}]
        if "SELECT intent_name, strength, trend FROM intent_evolution" in sql:
            return [{"intent_name": "focus", "strength": 0.8, "trend": "up"}]
        if "SELECT status, auto_priority, energy_cost, updated_at FROM tasks" in sql:
            return [{"status": "done"}]
        raise AssertionError(f"Unexpected query: {sql[:80]}")

    monkeypatch.setattr(forecast_engine, "resolve_person_id", AsyncMock(return_value="person-1"))
    monkeypatch.setattr(forecast_engine, "q", fake_q)

    result = await forecast_engine.compute_forecast("person-1")

    assert "clarity_forecast" in result
    assert 0.0 <= result["clarity_forecast"]["clarity_score"] <= 1.0
    assert "summary_text" in result


@pytest.mark.asyncio
async def test_emotion_loop_refresh_coerces_long_term_json_string(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        emotion_loop_refresh_worker,
        "resolve_person_id",
        AsyncMock(return_value="person-2"),
    )
    monkeypatch.setattr(
        emotion_loop_refresh_worker.emotion_loop_engine,
        "compute_emotion_loop_for_person",
        AsyncMock(return_value={"trend": "stable", "confidence": 0.7}),
    )
    monkeypatch.setattr(
        emotion_loop_refresh_worker,
        "q",
        AsyncMock(return_value={"long_term": '{"existing": true}'}),
    )
    dbexec_mock = AsyncMock()
    monkeypatch.setattr(emotion_loop_refresh_worker, "dbexec", dbexec_mock)

    await emotion_loop_refresh_worker.emotion_loop_refresh("person-2")

    assert dbexec_mock.await_count == 1
    args = dbexec_mock.await_args.args
    assert isinstance(args[2], str)
    payload = json.loads(args[2])
    assert payload["existing"] is True
    assert "emotion_state" in payload


@pytest.mark.asyncio
async def test_run_forecast_serializes_jsonb_payload(monkeypatch: pytest.MonkeyPatch):
    forecast_state = {"summary_text": "stable day expected", "emotion_forecast": {"calm": 0.6}}
    monkeypatch.setattr(forecast_worker, "resolve_person_id", AsyncMock(return_value="person-3"))
    monkeypatch.setattr(forecast_worker, "compute_forecast", AsyncMock(return_value=forecast_state))
    dbexec_mock = AsyncMock()
    monkeypatch.setattr(forecast_worker, "dbexec", dbexec_mock)

    await forecast_worker.run_forecast("person-3")

    assert dbexec_mock.await_count == 2
    first_args = dbexec_mock.await_args_list[0].args
    second_args = dbexec_mock.await_args_list[1].args
    assert json.loads(first_args[2]) == forecast_state
    assert json.loads(second_args[2]) == forecast_state


def test_compute_deep_rhythm_soul_coerces_slot_metric_strings():
    result = compute_deep_rhythm_soul(
        person_id="person-3",
        episodic=[],
        rhythm_state={
            "overall": '{"energy_level": 0.4, "load_level": 0.2, "recovery_level": 0.4, "strain_level": 0.2}',
            "slots": {
                "morning": '{"energy_level": 0.3, "load_level": 0.6, "strain_level": 0.5, "recovery_level": 0.2}'
            },
            "window_days": 7,
        },
        soul_state={"core_values": ["stability"]},
    )

    assert "alignment_level" in result
    assert isinstance(result.get("tension_zones"), list)
