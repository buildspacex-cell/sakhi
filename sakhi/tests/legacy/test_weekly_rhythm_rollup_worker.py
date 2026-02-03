from datetime import datetime, timedelta, timezone

from sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker import compute_rollup


def _slot(time_label: str, energy: float):
    return {"time": time_label, "energy": energy}


def test_stable_input_produces_stable_rollup():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    slots = [_slot("08:00", 0.6)] * 10
    curves = [{"day_scope": now.date(), "slots": slots, "confidence": 0.8}]
    roll = compute_rollup(curves, [], now)
    energy = roll["energy"]
    assert energy["slope"] == "stable"
    assert energy["volatility"] == "low"
    assert abs(energy["avg_level"] - 0.6) < 0.05


def test_high_variance_sets_high_volatility():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    slots = [_slot("08:00", 0.2), _slot("09:00", 0.9)] * 5
    curves = [{"day_scope": now.date(), "slots": slots, "confidence": 0.8}]
    roll = compute_rollup(curves, [], now)
    assert roll["energy"]["volatility"] == "high"


def test_no_data_returns_unknowns():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    roll = compute_rollup([], [], now)
    assert roll["energy"]["slope"] == "unknown"
    assert roll["energy"]["peak_windows"] == ["unknown"]


def test_peak_and_dip_buckets_detected():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    curves = [
        {
            "day_scope": now.date(),
            "slots": [
                _slot("08:00", 0.9),  # morning peak
                _slot("18:00", 0.2),  # evening dip
            ],
            "confidence": 0.7,
        }
    ]
    roll = compute_rollup(curves, [], now)
    assert "morning" in roll["energy"]["peak_windows"]
    assert "evening" in roll["energy"]["dip_windows"]
