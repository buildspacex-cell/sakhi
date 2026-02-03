from sakhi.apps.engine.reflection_trace.engine import build_reflection_trace


def test_reflection_trace_confidence_blend_with_all_inputs():
    payload = build_reflection_trace(
        person_id="u1",
        turn_id="t1",
        session_id="s1",
        moment_model={"confidence": 0.8, "stability": "stable", "recommended_companion_mode": "clarify"},
        evidence_pack={"confidence": 0.6, "anchors": ["a1"]},
        deliberation_scaffold={"confidence": 0.5, "summary": "test"},
    )
    assert 0.0 <= payload["confidence"] <= 1.0
    # 0.8*0.4 + 0.6*0.4 + 0.5*0.2 = 0.66
    assert abs(payload["confidence"] - 0.66) < 1e-6
    assert payload["trace"]["deliberation_present"] is True
    assert payload["low_confidence"] is False
    assert payload["recommend_caution"] is False


def test_reflection_trace_missing_inputs_records_missing_and_flags_low_confidence():
    payload = build_reflection_trace(
        person_id="u2",
        turn_id="t2",
        session_id=None,
        moment_model={},
        evidence_pack={},
        deliberation_scaffold=None,
    )
    assert "moment_model" in payload["trace"]["missing"]
    assert "evidence_pack" in payload["trace"]["missing"]
    assert "deliberation_scaffold" in payload["trace"]["missing"]
    assert payload["confidence"] >= 0.0
    # with zeroed inputs confidence should be low
    assert payload["low_confidence"] is True
    assert payload["recommend_caution"] is True

