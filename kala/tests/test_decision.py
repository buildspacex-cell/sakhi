"""Tests for kala.decision — deterministic decision scoring."""

from __future__ import annotations

from kala.decision.scoring import compute_fast_decision_frame


class TestComputeFastDecisionFrame:
    def test_empty_inputs(self) -> None:
        result = compute_fast_decision_frame()
        assert result["active_nodes"]["values"] == []
        assert result["active_nodes"]["goals"] == []
        assert result["micro_links"] == []
        assert result["friction_points"] == []
        assert result["energy_path"] == []

    def test_basic_goals_and_values(self) -> None:
        result = compute_fast_decision_frame(
            goals=[{"title": "Improve health"}, {"title": "Learn yoga"}],
            soul_state={"core_values": ["health", "growth"]},
        )
        assert len(result["active_nodes"]["goals"]) == 2
        assert result["active_nodes"]["values"] == ["health", "growth"]

    def test_value_goal_alignment_support(self) -> None:
        result = compute_fast_decision_frame(
            goals=[{"title": "Improve health habits"}],
            soul_state={"core_values": ["health"]},
        )
        supports = [lk for lk in result["micro_links"] if lk["type"] == "supports"]
        assert len(supports) == 1
        assert supports[0]["from"] == "Improve health habits"
        assert supports[0]["to"] == "values"

    def test_friction_conflict_detection(self) -> None:
        result = compute_fast_decision_frame(
            goals=[{"title": "Morning exercise routine"}],
            soul_state={
                "core_values": [],
                "friction": ["morning"],
            },
        )
        conflicts = [lk for lk in result["micro_links"] if lk["type"] == "conflicts"]
        assert len(conflicts) == 1
        assert conflicts[0]["from"] == "Morning exercise routine"

    def test_friction_points_from_soul(self) -> None:
        result = compute_fast_decision_frame(
            soul_state={"friction": ["time pressure", "overwhelm"]},
        )
        assert result["friction_points"] == ["time pressure", "overwhelm"]

    def test_friction_from_conflicts_key(self) -> None:
        result = compute_fast_decision_frame(
            soul_state={"conflicts": ["schedule conflict"]},
        )
        assert result["friction_points"] == ["schedule conflict"]

    def test_energy_path_prioritization(self) -> None:
        result = compute_fast_decision_frame(
            goals=[
                {"title": "Learn meditation"},
                {"title": "Fix bugs"},
                {"title": "Practice mindfulness"},
            ],
            soul_state={
                "core_values": ["mindfulness", "meditation"],
                "friction": ["bugs"],
            },
        )
        # "Learn meditation" and "Practice mindfulness" match values
        # "Fix bugs" matches friction → penalized
        assert result["energy_path"][0] in ("Learn meditation", "Practice mindfulness")
        assert "Fix bugs" not in result["energy_path"][:2]

    def test_energy_path_limited_to_three(self) -> None:
        result = compute_fast_decision_frame(
            goals=[{"title": f"Goal {i}"} for i in range(10)],
        )
        assert len(result["energy_path"]) <= 3

    def test_intents_extraction(self) -> None:
        result = compute_fast_decision_frame(
            intents=[
                {"title": "Focus on work"},
                {"intent": "relax after lunch"},
            ],
        )
        assert result["active_nodes"]["intents"] == [
            "Focus on work",
            "relax after lunch",
        ]

    def test_tasks_extraction(self) -> None:
        result = compute_fast_decision_frame(
            tasks=[
                {"label": "Review PR"},
                {"title": "Write tests"},
            ],
        )
        assert result["active_nodes"]["tasks"] == ["Review PR", "Write tests"]

    def test_intents_capped_at_five(self) -> None:
        result = compute_fast_decision_frame(
            intents=[{"title": f"Intent {i}"} for i in range(10)],
        )
        assert len(result["active_nodes"]["intents"]) == 5

    def test_goals_capped_at_five(self) -> None:
        result = compute_fast_decision_frame(
            goals=[{"title": f"Goal {i}"} for i in range(10)],
        )
        assert len(result["active_nodes"]["goals"]) == 5

    def test_tasks_capped_at_five(self) -> None:
        result = compute_fast_decision_frame(
            tasks=[{"label": f"Task {i}"} for i in range(10)],
        )
        assert len(result["active_nodes"]["tasks"]) == 5

    def test_none_inputs(self) -> None:
        result = compute_fast_decision_frame(
            short_term=None,
            intents=None,
            goals=None,
            tasks=None,
            soul_state=None,
        )
        assert result["active_nodes"]["values"] == []
        assert result["energy_path"] == []

    def test_both_support_and_conflict(self) -> None:
        """A goal can both align with values and hit friction."""
        result = compute_fast_decision_frame(
            goals=[{"title": "Morning health routine"}],
            soul_state={
                "core_values": ["health"],
                "friction": ["morning"],
            },
        )
        supports = [lk for lk in result["micro_links"] if lk["type"] == "supports"]
        conflicts = [lk for lk in result["micro_links"] if lk["type"] == "conflicts"]
        assert len(supports) == 1
        assert len(conflicts) == 1
