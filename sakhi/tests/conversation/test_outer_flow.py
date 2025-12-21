from sakhi.libs.conversation.outer_flow import (
    ensure_flow,
    merge_classification,
    prepare_next_question,
    apply_answer,
    is_active,
    build_classifier_context,
)


def test_outer_flow_progression() -> None:
    metadata: dict[str, object] = {}
    flow = ensure_flow(metadata)
    features = {
        "intent_type": "activity",
        "timeline": {"horizon": "none"},
        "g_mvs": {
            "target_horizon": False,
            "current_position": False,
            "constraints": False,
            "criteria": False,
            "assets_blockers": False,
        },
    }
    merge_classification(flow, features)

    question, step = prepare_next_question(flow)
    assert "When would you like this" in question
    assert step == "timeline"
    assert is_active(flow)

    apply_answer(flow, "this weekend")
    question2, step2 = prepare_next_question(flow)
    assert step2 == "preferences"
    assert "preferences" in question2.lower()

    apply_answer(flow, "downtown barber, morning slot")
    question3, step3 = prepare_next_question(flow)
    assert step3 == "constraints"
    assert "constraints" in question3.lower()


def test_outer_flow_exit_phrase_closes_flow() -> None:
    metadata: dict[str, object] = {}
    flow = ensure_flow(metadata)
    merge_classification(
        flow,
        {
            "timeline": {},
            "g_mvs": {
                "target_horizon": False,
                "current_position": False,
                "constraints": False,
                "criteria": False,
                "assets_blockers": False,
            },
        },
    )
    prepare_next_question(flow)
    apply_answer(flow, "that's all for now")
    question, step = prepare_next_question(flow)
    assert question == ""
    assert step is None
    assert not is_active(flow)


def test_permission_affirmation_closes_flow() -> None:
    metadata: dict[str, object] = {}
    flow = ensure_flow(metadata)
    flow["awaiting_step"] = "permission"
    apply_answer(flow, "yes please")
    assert flow["closed"]
    assert flow["ready_for_plan"]


def test_build_classifier_context_captures_history() -> None:
    flow = ensure_flow({})
    merge_classification(
        flow,
        {
            "intent_type": "activity",
            "timeline": {"horizon": "none"},
            "g_mvs": {
                "target_horizon": False,
                "current_position": False,
                "constraints": False,
                "criteria": False,
                "assets_blockers": False,
            },
        },
    )
    question, _ = prepare_next_question(flow)
    assert "When would" in question
    apply_answer(flow, "weekend")
    context = build_classifier_context(flow, base_prompt="Continue outer flow.")
    assert "Assistant:" in context
    assert "User: weekend" in context
