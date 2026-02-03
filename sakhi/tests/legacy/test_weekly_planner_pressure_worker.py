from datetime import datetime, timedelta, timezone

from sakhi.apps.worker.tasks.weekly_planner_pressure_worker import _compute_pressure


def _item(status, due_delta=None, priority=1, horizon="week", created_delta=None, updated_delta=None):
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    due_ts = now + timedelta(days=due_delta) if due_delta is not None else None
    created_at = now + timedelta(days=created_delta) if created_delta is not None else now
    updated_at = now + timedelta(days=updated_delta) if updated_delta is not None else now
    return {
        "status": status,
        "due_ts": due_ts,
        "priority": priority,
        "horizon": horizon,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def test_counts_and_ratios():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    window_start = (now - timedelta(days=7)).date()
    window_end = now.date()
    items = [
        _item("open", due_delta=-1, priority=3, horizon="today"),
        _item("in_progress", due_delta=2, priority=2, horizon="week"),
        _item("completed", due_delta=1, priority=1, horizon="week", updated_delta=-1),
    ]
    pressure, _ = _compute_pressure(items, now, window_start, window_end)
    assert pressure["open_count"] == 2  # completed excluded from open
    assert pressure["overdue_count"] == 1
    assert pressure["due_this_week"] >= 2
    assert pressure["urgency_ratio"] > 0  # one high-priority open


def test_fragmentation_deterministic():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    window_start = (now - timedelta(days=7)).date()
    window_end = now.date()
    items = [
        _item("open", due_delta=1, priority=1, horizon="week"),
        _item("open", due_delta=2, priority=4, horizon="month"),
        _item("open", due_delta=3, priority=2, horizon="today"),
    ]
    pressure, _ = _compute_pressure(items, now, window_start, window_end)
    score1 = pressure["fragmentation_score"]
    pressure_again, _ = _compute_pressure(items, now, window_start, window_end)
    assert score1 == pressure_again["fragmentation_score"]


def test_overload_flag_logic():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    window_start = (now - timedelta(days=7)).date()
    window_end = now.date()
    items = [
        _item("overdue", due_delta=-3, priority=4, horizon="week"),
        _item("overdue", due_delta=-2, priority=3, horizon="week"),
        _item("overdue", due_delta=-1, priority=3, horizon="week"),
        _item("open", due_delta=1, priority=4, horizon="today"),
    ]
    pressure, _ = _compute_pressure(items, now, window_start, window_end)
    assert pressure["overload_flag"] is True


def test_no_task_text_used():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    window_start = (now - timedelta(days=7)).date()
    window_end = now.date()
    items = [{"status": "open", "label": "should be ignored"}]
    pressure, _ = _compute_pressure(items, now, window_start, window_end)
    assert "label" not in pressure
