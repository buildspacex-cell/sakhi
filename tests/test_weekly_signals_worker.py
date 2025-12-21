from datetime import datetime, timedelta, timezone

from sakhi.apps.worker.tasks.weekly_signals_worker import (
    _aggregate_episodic,
    _confidence_from_inputs,
    _normalize_theme_weights,
    _direction_from_delta,
)


def test_aggregate_episodic_counts_and_themes():
    now = datetime.now(timezone.utc)
    rows = [
        {"created_at": now, "context_tags": [{"dimension": "work", "key": "focus"}, {"dimension": "energy", "key": "high"}]},
        {"created_at": now - timedelta(days=1), "context_tags": [{"dimension": "work", "key": "focus"}]},
    ]
    stats, themes = _aggregate_episodic(rows)
    assert stats["episode_count"] == 2
    assert stats["distinct_days"] >= 1
    assert themes["work:focus"] == 2


def test_theme_weights_normalize():
    counter_input = {"a": 3, "b": 1}
    weights = _normalize_theme_weights(counter_input)
    total = sum(item["weight"] for item in weights)
    assert total <= 1.0 + 1e-6


def test_confidence_respects_sparsity():
    conf_sparse = _confidence_from_inputs(None, None, {"episode_count": 1})
    conf_dense = _confidence_from_inputs(0.8, 0.7, {"episode_count": 10})
    assert conf_dense > conf_sparse
    assert 0.0 <= conf_sparse <= 1.0


def test_direction_from_delta():
    assert _direction_from_delta(0.1) == "up"
    assert _direction_from_delta(-0.2) == "down"
    assert _direction_from_delta(0.0) == "flat"
