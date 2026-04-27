from sakhi.apps.api.routes import turn_v2


def test_build_public_continuity_signal_returns_none_without_topic_key():
    assert turn_v2._build_public_continuity_signal({}) is None
    assert turn_v2._build_public_continuity_signal({"topic_key": "   "}) is None


def test_build_public_continuity_signal_includes_deep_reflect_ready():
    payload = turn_v2._build_public_continuity_signal(
        {
            "topic_key": "sakhi",
            "topic_label": "Sakhi",
            "surface": {"mirror_allowed": True, "detail_allowed": True},
            "history_compact": {"element_count": 10},
            "evidence": [{"source_ref": "journal:1"}],
        }
    )

    assert payload is not None
    assert payload["topic_key"] == "sakhi"
    assert payload["topic_label"] == "Sakhi"
    assert payload["deep_reflect"] == {
        "ready": True,
        "reason": "ready",
        "mirror_allowed": True,
        "detail_allowed": True,
        "selected_count": 10,
        "min_moments": 4,
    }


def test_build_public_continuity_signal_includes_deep_reflect_reason_when_depth_insufficient():
    payload = turn_v2._build_public_continuity_signal(
        {
            "topic_key": "career",
            "surface": {"mirror_allowed": True, "detail_allowed": True},
            "history_compact": {"element_count": 3},
            "evidence": [{"source_ref": "journal:1"}, {"source_ref": "journal:2"}],
        }
    )

    assert payload is not None
    deep_reflect = payload["deep_reflect"]
    assert deep_reflect["ready"] is False
    assert deep_reflect["reason"] == "insufficient_depth"
    assert deep_reflect["selected_count"] == 3
    assert deep_reflect["min_moments"] == 4


def test_build_public_continuity_signal_prefers_effective_topic_depth():
    payload = turn_v2._build_public_continuity_signal(
        {
            "topic_key": "sakhi",
            "surface": {"mirror_allowed": True, "detail_allowed": True},
            "history_compact": {
                "element_count": 9,
                "strict_element_count": 4,
                "attached_element_count": 5,
            },
            "evidence": [{"source_ref": "journal:1"}],
        }
    )

    assert payload is not None
    deep_reflect = payload["deep_reflect"]
    assert deep_reflect["ready"] is True
    assert deep_reflect["selected_count"] == 9


def test_build_public_continuity_signal_prioritizes_surface_blocks():
    payload = turn_v2._build_public_continuity_signal(
        {
            "topic_key": "family",
            "surface": {"mirror_allowed": False, "detail_allowed": False},
            "history_compact": {"element_count": 99},
        }
    )

    assert payload is not None
    deep_reflect = payload["deep_reflect"]
    assert deep_reflect["ready"] is False
    assert deep_reflect["reason"] == "mirror_blocked"
    assert deep_reflect["mirror_allowed"] is False
    assert deep_reflect["detail_allowed"] is False


def test_build_public_continuity_signal_passthroughs_cross_context_fields():
    payload = turn_v2._build_public_continuity_signal(
        {
            "topic_key": "sakhi",
            "topic_label": "Sakhi",
            "surface": {"mirror_allowed": True, "detail_allowed": True},
            "history_compact": {"element_count": 12},
            "whole_story": {
                "ready": True,
                "reason": "ready",
                "selected_topics": ["sakhi", "career"],
                "selected_count_total": 18,
                "correlation_score": 0.61,
            },
            "cross_context": {
                "ready": True,
                "reason": "ready",
                "correlated_topic_key": "career",
                "correlation_score": 0.61,
            },
            "candidate_topics": [
                {"topic_key": "sakhi", "score": 0.9},
                {"topic_key": "career", "score": 0.7},
            ],
            "life_dimensions": {
                "time_availability": {"level": 0.56, "direction": "pressured"},
            },
        }
    )

    assert payload is not None
    assert payload["whole_story"]["ready"] is True
    assert payload["cross_context"]["correlated_topic_key"] == "career"
    assert len(payload["candidate_topics"]) == 2
    assert payload["life_dimensions"]["time_availability"]["direction"] == "pressured"
