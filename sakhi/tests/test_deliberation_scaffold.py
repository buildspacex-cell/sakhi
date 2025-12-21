from sakhi.apps.engine.deliberation_scaffold.engine import compute_deliberation_scaffold


def _base(moment_mode="clarify", evidence_conf=0.6, anchors=1, tension=True):
    moment = {"recommended_companion_mode": moment_mode, "stability": "stable", "emotional_intensity": "medium"}
    evidence = {"confidence": evidence_conf, "anchors": [{}] * anchors}
    conflict = {"present": tension, "conflict_score": 0.7} if tension else {}
    alignment = {"tension_score": 0.7} if tension else {}
    identity = {"drift_score": 0.0}
    forecast = {}
    continuity = {"last_text_turns": ["a", "b", "c", "d"]}
    return moment, evidence, conflict, alignment, identity, forecast, continuity


def test_builds_when_tension_and_confidence():
    moment, evidence, conflict, alignment, identity, forecast, continuity = _base()
    scaffold = compute_deliberation_scaffold(
        moment_model=moment,
        evidence_pack=evidence,
        conflict_state=conflict,
        alignment_state=alignment,
        identity_state=identity,
        forecast_state=forecast,
        continuity_state=continuity,
    )
    assert scaffold is not None
    assert scaffold["explicitly_not_deciding"] is True
    assert len(scaffold["options"]) >= 2


def test_suppresses_on_low_confidence():
    moment, evidence, conflict, alignment, identity, forecast, continuity = _base()
    evidence["confidence"] = 0.1
    scaffold = compute_deliberation_scaffold(
        moment_model=moment,
        evidence_pack=evidence,
        conflict_state=conflict,
        alignment_state=alignment,
        identity_state=identity,
        forecast_state=forecast,
        continuity_state=continuity,
    )
    assert scaffold is None


def test_suppresses_without_anchors():
    moment, evidence, conflict, alignment, identity, forecast, continuity = _base()
    evidence["anchors"] = []
    scaffold = compute_deliberation_scaffold(
        moment_model=moment,
        evidence_pack=evidence,
        conflict_state=conflict,
        alignment_state=alignment,
        identity_state=identity,
        forecast_state=forecast,
        continuity_state=continuity,
    )
    assert scaffold is None


def test_suppresses_non_decision_mode():
    moment, evidence, conflict, alignment, identity, forecast, continuity = _base(moment_mode="hold")
    scaffold = compute_deliberation_scaffold(
        moment_model=moment,
        evidence_pack=evidence,
        conflict_state=conflict,
        alignment_state=alignment,
        identity_state=identity,
        forecast_state=forecast,
        continuity_state=continuity,
    )
    assert scaffold is None


def test_options_are_neutral():
    moment, evidence, conflict, alignment, identity, forecast, continuity = _base()
    scaffold = compute_deliberation_scaffold(
        moment_model=moment,
        evidence_pack=evidence,
        conflict_state=conflict,
        alignment_state=alignment,
        identity_state=identity,
        forecast_state=forecast,
        continuity_state=continuity,
    )
    assert scaffold is not None
    for opt in scaffold["options"]:
        assert "choose" not in opt.lower()
