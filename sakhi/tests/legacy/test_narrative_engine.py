from sakhi.core.soul.narrative_engine import compute_fast_narrative


def test_compute_fast_narrative_deterministic():
    st = [{"triage": {"emotion": "calm"}}, {"triage": {"emotion": "joy"}}]
    soul_state = {"identity_themes": ["growth"], "core_values": ["learning"], "friction": ["overwork"], "shadow": ["doubt"], "light": ["optimism"]}
    out = compute_fast_narrative(st, soul_state)
    assert "dominant_theme" in out
    assert out["emotional_trend"] in {"calm", "joy", "neutral"}
    assert 0 <= out["value_alignment"] <= 1
    assert 0 <= out["shadow_pressure"] <= 1
