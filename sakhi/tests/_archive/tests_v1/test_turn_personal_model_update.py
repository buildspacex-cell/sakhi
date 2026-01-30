from datetime import datetime, timedelta, timezone

from sakhi.apps.worker.tasks.turn_personal_model_update import (
    SignalSnapshot,
    _combine_snapshots,
    _compute_confidence,
    _compute_direction,
    _compute_lifecycle,
)


def test_direction_and_confidence_upwards():
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    window_end = now
    current = {"energy": SignalSnapshot(level=0.7, volatility=0.2, confidence=0.6, count=5)}
    previous = {"energy": SignalSnapshot(level=0.4, volatility=0.3, confidence=0.5, count=4)}
    existing = {"energy": {"confidence": 0.3, "direction": "up"}}

    state = _combine_snapshots(current, previous, existing, window_start, window_end, now)
    energy = state["energy"]
    assert energy["direction"] == "up"
    assert energy["magnitude"] > 0.0
    assert energy["confidence"] > 0.3
    assert energy["lifecycle"] in {"emerging", "stabilizing"}


def test_confidence_decays_without_evidence():
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    window_end = now
    current = {"mind": SignalSnapshot()}  # no evidence
    previous = {"mind": SignalSnapshot()}  # no evidence
    existing = {"mind": {"confidence": 0.8, "direction": "up"}}

    state = _combine_snapshots(current, previous, existing, window_start, window_end, now)
    mind = state["mind"]
    assert mind["confidence"] < 0.8  # decay applied
    assert mind["direction"] == "flat"


def test_direction_reversal_triggers_decaying_lifecycle():
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    window_end = now
    current = {"emotion": SignalSnapshot(level=0.2, volatility=0.5, confidence=0.6, count=4)}
    previous = {"emotion": SignalSnapshot(level=0.7, volatility=0.3, confidence=0.6, count=4)}
    existing = {"emotion": {"confidence": 0.6, "direction": "up"}}

    state = _combine_snapshots(current, previous, existing, window_start, window_end, now)
    emotion = state["emotion"]
    assert emotion["direction"] == "down"
    assert emotion["lifecycle"] in {"decaying", "emerging"}


def test_confidence_helper_behaviour():
    snap = SignalSnapshot(level=0.6, volatility=0.3, confidence=0.5, count=5)
    conf = _compute_confidence(snap, prev_conf=0.2, prev_direction="up", direction="up", has_prev_window=True)
    assert 0.2 < conf <= 1.0

    conf_decay = _compute_confidence(SignalSnapshot(), prev_conf=0.6, prev_direction="up", direction="flat", has_prev_window=False)
    assert conf_decay < 0.6


def test_direction_helper_thresholds():
    direction, magnitude = _compute_direction(0.5, 0.4, None)
    assert direction == "up"
    assert magnitude > 0

    direction_flat, _ = _compute_direction(0.41, 0.4, None)
    assert direction_flat == "flat"
