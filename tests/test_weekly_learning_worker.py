from datetime import datetime, timedelta, timezone

from sakhi.apps.worker.tasks.weekly_learning_worker import (
    update_longitudinal_state,
    DECAY_DAYS,
)


def test_consistent_polarity_confidence_increases():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    episodes = [
        {"created_at": now - timedelta(days=1), "context_tags": [{"dimension": "emotion", "signal_key": "anxiety", "polarity": "up", "intensity": "medium"}]},
        {"created_at": now - timedelta(days=2), "context_tags": [{"dimension": "emotion", "signal_key": "anxiety", "polarity": "up", "intensity": "high"}]},
    ]
    state = update_longitudinal_state({}, episodes, now)
    payload = state["emotion"]["anxiety"]
    assert payload["direction"] == "up"
    assert payload["confidence"] > 0.15
    assert payload["volatility"] in {"low", "medium"}


def test_mixed_polarity_sets_volatile():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    episodes = [
        {"created_at": now - timedelta(days=1), "context_tags": [{"dimension": "energy", "signal_key": "fatigue", "polarity": "up", "intensity": "medium"}]},
        {"created_at": now - timedelta(days=2), "context_tags": [{"dimension": "energy", "signal_key": "fatigue", "polarity": "down", "intensity": "medium"}]},
    ]
    state = update_longitudinal_state({}, episodes, now)
    payload = state["energy"]["fatigue"]
    assert payload["direction"] == "volatile"
    assert payload["volatility"] == "high"


def test_inactivity_decays_confidence():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    old_ts = (now - timedelta(days=DECAY_DAYS + 5)).isoformat()
    current = {
        "mind": {
            "overload": {
                "direction": "up",
                "volatility": "medium",
                "confidence": 0.8,
                "observed_over_days": 3,
                "window": {"start": "2024-12-01", "end": "2024-12-03"},
                "last_episode_at": old_ts,
                "last_updated_at": old_ts,
            }
        }
    }
    state = update_longitudinal_state(current, [], now)
    payload = state["mind"]["overload"]
    assert payload["confidence"] < 0.8


def test_invalid_dimensions_ignored():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    episodes = [
        {"created_at": now, "context_tags": [{"dimension": "soul", "signal_key": "identity", "polarity": "up", "intensity": "high"}]}
    ]
    state = update_longitudinal_state({}, episodes, now)
    assert state == {}
