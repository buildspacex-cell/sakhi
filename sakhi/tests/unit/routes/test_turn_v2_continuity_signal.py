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
        "min_moments": 8,
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
    assert deep_reflect["min_moments"] == 8


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
