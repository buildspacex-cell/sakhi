from __future__ import annotations

from sakhi.apps.api.services.demo.simulation_continuity import (
    build_simulation_continuity_arc,
    classify_simulation_entry,
    compile_simulation_continuity,
)


def test_build_simulation_continuity_arc_returns_structured_arc():
    result = build_simulation_continuity_arc(
        persona_id="vidhya",
        anchor="Career",
        entries=[
            {
                "day": 2,
                "timestamp": "2026-01-02T08:00:00+00:00",
                "content": "I am thinking hard about my next career move.",
                "time_of_day": "morning",
                "facet": "promotion",
                "decision_state": "questioning",
                "stance": "toward",
            },
            {
                "day": 11,
                "timestamp": "2026-01-11T08:00:00+00:00",
                "content": "The promotion question is back in my mind.",
                "time_of_day": "morning",
                "facet": "promotion",
                "decision_state": "leaning_yes",
                "stance": "toward",
            },
            {
                "day": 24,
                "timestamp": "2026-01-24T08:00:00+00:00",
                "content": "I can see this as one long decision, not separate spikes.",
                "time_of_day": "morning",
                "facet": "identity",
                "decision_state": "resolved",
                "stance": "toward",
            },
        ],
    )

    assert result["persona_id"] == "vidhya"
    assert result["anchor"] == "career"
    assert result["arc"]["element_count"] == 3
    assert result["arc"]["phase_count"] == 3
    assert result["arc"]["event_refs"][0]["day"] == 2
    assert result["arc"]["event_refs"][0]["facet"] == "promotion"
    assert result["arc"]["event_refs"][0]["decision_state"] == "questioning"
    assert result["arc"]["features"]["direction"] == "rising"


def test_build_simulation_continuity_arc_enriches_phase_stats_with_dominant_tags():
    result = build_simulation_continuity_arc(
        persona_id="vidhya",
        anchor="Sakhi",
        entries=[
            {
                "day": 1,
                "timestamp": "2026-01-01T08:00:00+00:00",
                "content": "Ayurveda and ayurvedic wisdom should feel personal.",
                "time_of_day": "morning",
                "facet": "ayurveda_engine",
                "decision_state": "questioning",
                "stance": "toward",
                "confidence": 0.82,
                "matched_terms": ["ayurveda", "ayurvedic"],
            },
            {
                "day": 4,
                "timestamp": "2026-01-04T08:00:00+00:00",
                "content": "The ayurveda engine still feels central.",
                "time_of_day": "morning",
                "facet": "ayurveda_engine",
                "decision_state": "leaning_yes",
                "stance": "toward",
                "confidence": 0.86,
                "matched_terms": ["ayurveda"],
            },
            {
                "day": 9,
                "timestamp": "2026-01-09T08:00:00+00:00",
                "content": "The prototype and product shape need more clarity.",
                "time_of_day": "morning",
                "facet": "product_shape",
                "decision_state": "deferred",
                "stance": "unclear",
                "confidence": 0.8,
                "matched_terms": ["prototype", "clarity"],
            },
            {
                "day": 12,
                "timestamp": "2026-01-12T08:00:00+00:00",
                "content": "The product and MVP need to feel more coherent.",
                "time_of_day": "morning",
                "facet": "product_shape",
                "decision_state": "questioning",
                "stance": "toward",
                "confidence": 0.84,
                "matched_terms": ["product", "mvp"],
            },
            {
                "day": 18,
                "timestamp": "2026-01-18T08:00:00+00:00",
                "content": "Deterministic intelligence and continuity are the core now.",
                "time_of_day": "morning",
                "facet": "deterministic_core",
                "decision_state": "committed",
                "stance": "toward",
                "confidence": 0.9,
                "matched_terms": ["deterministic intelligence", "continuity"],
            },
            {
                "day": 24,
                "timestamp": "2026-01-24T08:00:00+00:00",
                "content": "Continuity still feels like the right core.",
                "time_of_day": "morning",
                "facet": "deterministic_core",
                "decision_state": "resolved",
                "stance": "toward",
                "confidence": 0.88,
                "matched_terms": ["continuity"],
            },
        ],
    )

    phases = result["arc"]["phases"]
    assert phases[0]["stats"]["dominant_facet"] == "ayurveda_engine"
    assert phases[0]["stats"]["dominant_tag"]["label"] == "ayurveda engine"
    assert phases[1]["stats"]["dominant_facet"] == "product_shape"
    assert phases[2]["stats"]["dominant_facet"] == "deterministic_core"
    assert phases[2]["stats"]["top_tags"][0]["label"] == "continuity"


def test_build_simulation_continuity_arc_requires_minimum_entries():
    try:
        build_simulation_continuity_arc(
            persona_id="diya",
            anchor="Recovery",
            entries=[
                {
                    "day": 3,
                    "timestamp": "2026-01-03T08:00:00+00:00",
                    "content": "Only one point.",
                },
                {
                    "day": 8,
                    "timestamp": "2026-01-08T08:00:00+00:00",
                    "content": "Only two points.",
                },
            ],
        )
    except LookupError as exc:
        assert "Select at least 3 entries" in str(exc)
    else:
        raise AssertionError("Expected a LookupError when fewer than 3 entries are selected")


def test_compile_simulation_continuity_derives_topics_from_entry_text():
    compiled = compile_simulation_continuity(
        persona_id="vidhya",
        entries=[
            {
                "day": 1,
                "timestamp": "2026-01-01T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Back-to-back meetings. My boss pushed the review again and I keep thinking about promotion.",
            },
            {
                "day": 5,
                "timestamp": "2026-01-05T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Heavy calendar today. Another work review, but I feel clearer about the role I want.",
            },
            {
                "day": 9,
                "timestamp": "2026-01-09T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "My boss brought up leadership again. I finally feel settled about this career move.",
            },
            {
                "day": 12,
                "timestamp": "2026-01-12T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Dad looked more confused today and the grief comes in waves.",
            },
            {
                "day": 17,
                "timestamp": "2026-01-17T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Mom is tired. The hospital call made the caregiving pressure feel heavier.",
            },
            {
                "day": 22,
                "timestamp": "2026-01-22T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "I need to care for them, but I also need a boundary so I do not drown in guilt.",
            },
        ],
    )

    assert compiled["version"] == 2
    assert compiled["taxonomy_version"] == "2026.03.03"
    assert compiled["compiler_version"] == "2026.03.18.1"
    assert compiled["threshold_profile_version"] == "2026.03.18.1"
    assert isinstance(compiled["inputs_hash"], str)
    anchors = [topic["anchor"] for topic in compiled["topics"]]
    assert "career" in anchors
    assert "caregiving" in anchors

    career_topic = next(topic for topic in compiled["topics"] if topic["anchor"] == "career")
    assert career_topic["selected_count"] == 3
    assert career_topic["primary_selected_count"] == 3
    assert career_topic["related_selected_count"] == 0
    assert career_topic["entry_days"] == [1, 5, 9]
    assert career_topic["arc"]["features"]["direction"] in {"rising", "flat"}
    career_key = "9|2026-01-09T08:00:00+00:00"
    assert career_topic["entry_tags"][career_key]["decision_state"] in {
        "resolved",
        "committed",
    }
    assert career_topic["entry_tags"][career_key]["anchor_state"] == "CONFIDENT"
    assert career_topic["arc"]["phases"][0]["stats"]["dominant_facet"] in {
        "promotion",
        "workload",
        "leadership",
    }
    assert "dominant_tag" in career_topic["arc"]["phases"][0]["stats"]
    assert career_topic["surface"]["mirror_allowed"] is True
    assert career_topic["surface"]["detail_allowed"] is True

    caregiving_topic = next(topic for topic in compiled["topics"] if topic["anchor"] == "caregiving")
    assert caregiving_topic["entry_days"] == [12, 17, 22]
    caregiving_key = "12|2026-01-12T08:00:00+00:00"
    assert caregiving_topic["entry_tags"][caregiving_key]["facet"] in {
        "grief",
        "caregiving",
    }


def test_compile_simulation_continuity_skips_sparse_topic_groups_without_failing():
    compiled = compile_simulation_continuity(
        persona_id="bigd",
        entries=[
            {
                "day": 1,
                "timestamp": "2026-01-01T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "The leadership question came up again today.",
            },
            {
                "day": 50,
                "timestamp": "2026-02-19T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Leadership is still on my mind.",
            },
            {
                "day": 100,
                "timestamp": "2026-04-10T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "I keep returning to leadership.",
            },
        ],
    )

    anchors = [topic["anchor"] for topic in compiled["topics"]]
    assert anchors == []


def test_classify_simulation_entry_returns_unknown_for_low_signal():
    result = classify_simulation_entry({"content": "Long day. I am thinking and trying to make sense of it."})

    assert result["primary_anchor"] == "unknown"
    assert result["facet"] == "unknown"
    assert result["anchor_state"] == "UNKNOWN"
    assert result["facet_state"] == "UNKNOWN"
    assert result["trace"]["anchor"]["fallback_reason"] in {"no_anchor_signal", "anchor_below_threshold"}


def test_classify_simulation_entry_keeps_broad_anchor_but_unknown_facet_when_facet_is_weak():
    result = classify_simulation_entry(
        {
            "content": "I keep circling the same work life question and thinking about my next job path.",
        }
    )

    assert result["primary_anchor"] == "career"
    assert result["anchor_state"] == "CONFIDENT"
    assert result["facet"] == "unknown"
    assert result["facet_state"] in {"UNKNOWN", "UNCERTAIN"}


def test_compile_simulation_continuity_is_stable_for_same_inputs():
    entries = [
        {
            "day": 1,
            "timestamp": "2026-01-01T08:00:00+00:00",
            "time_of_day": "morning",
            "content": "Ravi and I think deterministic intelligence and continuity are the core.",
        },
        {
            "day": 5,
            "timestamp": "2026-01-05T08:00:00+00:00",
            "time_of_day": "morning",
            "content": "The knowledge graph still feels more honest than a reactive companion.",
        },
        {
            "day": 9,
            "timestamp": "2026-01-09T08:00:00+00:00",
            "time_of_day": "morning",
            "content": "We keep returning to deterministic continuity as the real product core.",
        },
    ]

    first = compile_simulation_continuity(persona_id="vidhya", entries=entries)
    second = compile_simulation_continuity(persona_id="vidhya", entries=entries)

    assert first["inputs_hash"] == second["inputs_hash"]
    assert first["topics"] == second["topics"]


def test_compile_simulation_continuity_blocks_surfacing_for_low_signal_fallback():
    compiled = compile_simulation_continuity(
        persona_id="vidhya",
        entries=[
            {
                "day": 1,
                "timestamp": "2026-01-01T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Long day. I am trying to make sense of it.",
            },
            {
                "day": 5,
                "timestamp": "2026-01-05T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Still sitting with the same blurry feeling.",
            },
            {
                "day": 9,
                "timestamp": "2026-01-09T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Nothing clear yet. Just holding it.",
            },
        ],
    )

    assert compiled["topics"][0]["anchor"] == "life"
    assert compiled["topics"][0]["surface"]["mirror_allowed"] is False
    assert compiled["topics"][0]["surface"]["detail_allowed"] is False


def test_compile_simulation_continuity_projects_shared_moments_into_related_topics():
    compiled = compile_simulation_continuity(
        persona_id="vidhya",
        entries=[
            {
                "day": 1,
                "timestamp": "2026-01-01T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Mom needed me again, and that family pressure cut into Sakhi founder time.",
            },
            {
                "day": 5,
                "timestamp": "2026-01-05T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Dad and family demands keep cutting into Sakhi founder time.",
            },
            {
                "day": 9,
                "timestamp": "2026-01-09T08:00:00+00:00",
                "time_of_day": "morning",
                "content": "Mom and family pressure are shaping Sakhi founder work this week.",
            },
        ],
    )

    anchors = {topic["anchor"] for topic in compiled["topics"]}
    assert "family" in anchors
    assert "sakhi" in anchors

    sakhi_topic = next(topic for topic in compiled["topics"] if topic["anchor"] == "sakhi")
    family_topic = next(topic for topic in compiled["topics"] if topic["anchor"] == "family")

    assert sakhi_topic["primary_selected_count"] == 3
    assert sakhi_topic["related_selected_count"] == 0
    assert family_topic["primary_selected_count"] == 0
    assert family_topic["related_selected_count"] == 3

    first_key = "1|2026-01-01T08:00:00+00:00"
    assert sakhi_topic["entry_tags"][first_key]["membership_role"] == "primary"
    assert family_topic["entry_tags"][first_key]["membership_role"] == "related"
    assert family_topic["entry_tags"][first_key]["source_anchor"] == "sakhi"
    assert any(
        item["anchor"] == "family"
        for item in sakhi_topic["entry_tags"][first_key]["related_anchors"]
    )
