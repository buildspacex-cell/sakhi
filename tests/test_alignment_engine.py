from sakhi.core.soul.alignment_engine import compute_alignment


def test_alignment_engine_scores():
    soul_state = {"core_values": ["growth"], "friction": ["burnout"], "conflicts": ["time"], "aversions": ["burnout"]}
    goals_state = {"active_goals": [{"title": "Growth plan"}, {"title": "Workout"}]}
    out = compute_alignment(None, soul_state, goals_state)
    assert 0 <= out["alignment_score"] <= 1
    assert isinstance(out["conflict_zones"], list)
    assert isinstance(out["action_suggestions"], list)
