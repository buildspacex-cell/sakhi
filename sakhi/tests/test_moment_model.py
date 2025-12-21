import datetime

from sakhi.apps.engine.moment_model.engine import compute_moment_model


def test_high_emotion_low_stability_ground():
    moment = compute_moment_model(
        emotion_state={"volatility": 0.7, "drift": 0.4, "mode": "volatile"},
        coherence_state={},
        alignment_state={},
        mind_state={"cognitive_load": 0.3},
        forecast_state={},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 10, 0, 0),
    )
    assert moment["recommended_companion_mode"] in {"ground", "hold"}
    assert moment["stability"] == "volatile"


def test_high_cognitive_load_clarify():
    moment = compute_moment_model(
        emotion_state={"volatility": 0.1, "drift": 0.05},
        coherence_state={},
        alignment_state={},
        mind_state={"cognitive_load": 0.8},
        forecast_state={"emotion_forecast": {"motivation_prob": 0.4}},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 10, 0, 0),
    )
    assert moment["cognitive_load"] == "overloaded"
    assert moment["recommended_companion_mode"] == "clarify"


def test_low_intensity_high_coherence_expand():
    moment = compute_moment_model(
        emotion_state={"volatility": 0.1, "drift": 0.05},
        coherence_state={"coherence_score": 0.9},
        alignment_state={},
        mind_state={"cognitive_load": 0.1},
        forecast_state={},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 9, 0, 0),
    )
    assert moment["emotional_intensity"] == "low"
    assert moment["recommended_companion_mode"] in {"expand", "reflect"}


def test_long_gap_hold():
    moment = compute_moment_model(
        emotion_state={},
        coherence_state={},
        alignment_state={},
        mind_state={},
        forecast_state={},
        continuity_state={},
        gap_hours=4.5,
        restart=True,
        now=datetime.datetime(2025, 1, 1, 12, 0, 0),
    )
    assert moment["continuity_state"] == "restarting"
    assert moment["recommended_companion_mode"] == "hold"


def test_fatigue_evening_pause():
    moment = compute_moment_model(
        emotion_state={"volatility": 0.2},
        coherence_state={},
        alignment_state={},
        mind_state={"cognitive_load": 0.2},
        forecast_state={"emotion_forecast": {"fatigue_prob": 0.8}},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 19, 0, 0),
    )
    assert "fatigue" in moment["risk_context"]
    assert moment["recommended_companion_mode"] == "pause"


def test_conflicting_signals_reflect():
    moment = compute_moment_model(
        emotion_state={"volatility": 0.7, "drift": 0.5, "mode": "volatile"},
        coherence_state={},
        alignment_state={},
        mind_state={"cognitive_load": 0.9},
        forecast_state={"emotion_forecast": {"fatigue_prob": 0.7}},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 16, 0, 0),
    )
    assert moment["recommended_companion_mode"] in {"reflect", "ground"}


def test_missing_signals_graceful():
    moment = compute_moment_model(
        emotion_state={},
        coherence_state={},
        alignment_state={},
        mind_state={},
        forecast_state={},
        continuity_state={},
        gap_hours=None,
        restart=False,
        now=datetime.datetime(2025, 1, 1, 6, 0, 0),
    )
    assert moment["emotional_intensity"] in {"low", "medium", "high"}
    assert moment["recommended_companion_mode"] in {"hold", "reflect", "ground", "clarify", "expand", "pause"}
