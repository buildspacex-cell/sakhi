from __future__ import annotations

from sakhi.apps.api.services.demo.simulation_continuity import classify_simulation_entry


def test_continuity_taxonomy_benchmark_corpus():
    corpus = [
        {
            "name": "career_review",
            "content": "Back-to-back meetings. My boss pushed the review again and I keep thinking about promotion.",
            "expected_anchor": "career",
            "expected_facet": "promotion",
            "forbidden_anchors": {"caregiving", "family"},
        },
        {
            "name": "caregiving_grief",
            "content": "Dad looked more confused today and the grief comes in waves after the hospital call.",
            "expected_anchor": "caregiving",
            "expected_facet": "grief",
            "forbidden_anchors": {"career"},
        },
        {
            "name": "sakhi_deterministic_core",
            "content": "Ravi and I think deterministic intelligence, continuity, and the knowledge graph are the real core.",
            "expected_anchor": "sakhi",
            "expected_facet": "deterministic_core",
            "forbidden_anchors": {"career"},
        },
        {
            "name": "low_signal_fallback",
            "content": "Long day. I am thinking and trying to make sense of it.",
            "expected_anchor": "unknown",
            "expected_facet": "unknown",
        },
        {
            "name": "career_broad_anchor_unknown_facet",
            "content": "I keep circling the same work life question and thinking about my next job path.",
            "expected_anchor": "career",
            "expected_facet": "unknown",
            "expected_anchor_state": "CONFIDENT",
            "expected_facet_state": "UNKNOWN",
            "forbidden_anchors": {"caregiving", "family"},
        },
    ]

    for row in corpus:
        result = classify_simulation_entry({"content": row["content"]})
        assert result["taxonomy_version"] == "2026.03.03"
        assert result["compiler_version"] == "2026.03.03.1"
        assert result["threshold_profile_version"] == "2026.03.03.1"
        assert result["primary_anchor"] == row["expected_anchor"], row["name"]
        assert result["facet"] == row["expected_facet"], row["name"]
        if row.get("expected_anchor_state"):
            assert result["anchor_state"] == row["expected_anchor_state"], row["name"]
        if row.get("expected_facet_state"):
            assert result["facet_state"] == row["expected_facet_state"], row["name"]

        forbidden_anchors = row.get("forbidden_anchors") or set()
        for forbidden in forbidden_anchors:
            assert forbidden not in set(result["anchor_candidates"]), row["name"]
