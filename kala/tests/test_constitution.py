"""
Unit tests for kala constitution computation.

Tests pure functions for quiz-to-dosha mapping and constitution naming.
"""

from kala.state.constitution import (
    CONSTITUTION_NAMES,
    DOSHA_FROM_NAME,
    compute_dosha_from_quiz,
    determine_constitution_type,
)

# =============================================================================
# compute_dosha_from_quiz tests
# =============================================================================


class TestComputeDoshaFromQuiz:
    """Tests for quiz response → dosha score computation."""

    def test_pure_vata(self):
        """All vata responses should produce vata-dominant scores."""
        responses = {
            "body_type": "light_thin",
            "energy_pattern": "variable_bursts",
            "stress_response": "anxious_scattered",
            "sleep_pattern": "light_variable",
            "work_style": "creative_multitask",
        }
        scores = compute_dosha_from_quiz(responses)
        assert scores["vata"] > scores["pitta"]
        assert scores["vata"] > scores["kapha"]
        assert scores["vata"] == 1.0

    def test_pure_pitta(self):
        """All pitta responses should produce pitta-dominant scores."""
        responses = {
            "body_type": "medium_muscular",
            "energy_pattern": "focused_sustained",
            "stress_response": "irritable_intense",
            "sleep_pattern": "moderate_efficient",
            "work_style": "goal_driven",
        }
        scores = compute_dosha_from_quiz(responses)
        assert scores["pitta"] > scores["vata"]
        assert scores["pitta"] > scores["kapha"]

    def test_pure_kapha(self):
        """All kapha responses should produce kapha-dominant scores."""
        responses = {
            "body_type": "solid_heavy",
            "energy_pattern": "steady_slow",
            "stress_response": "withdrawn_sluggish",
            "sleep_pattern": "deep_heavy",
            "work_style": "methodical_consistent",
        }
        scores = compute_dosha_from_quiz(responses)
        assert scores["kapha"] > scores["vata"]
        assert scores["kapha"] > scores["pitta"]

    def test_mixed_constitution(self):
        """Mixed responses should produce mixed scores."""
        responses = {
            "body_type": "light_thin",           # vata
            "energy_pattern": "focused_sustained",  # pitta
            "stress_response": "anxious_scattered",  # vata
            "sleep_pattern": "moderate_efficient",   # pitta
            "work_style": "creative_multitask",      # vata
        }
        scores = compute_dosha_from_quiz(responses)
        assert scores["vata"] > scores["pitta"]
        assert scores["pitta"] > scores["kapha"]

    def test_empty_responses(self):
        """Empty dict should return balanced defaults."""
        scores = compute_dosha_from_quiz({})
        assert scores == {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    def test_scores_sum_to_one(self):
        """All dosha scores should sum to 1.0."""
        responses = {
            "body_type": "light_thin",
            "energy_pattern": "focused_sustained",
            "stress_response": "withdrawn_sluggish",
        }
        scores = compute_dosha_from_quiz(responses)
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.01

    def test_case_insensitive(self):
        """Quiz responses should be case-insensitive."""
        responses = {"body_type": "Light_Thin"}
        scores = compute_dosha_from_quiz(responses)
        assert scores["vata"] > 0

    def test_unknown_response_ignored(self):
        """Unknown response values should be ignored (no crash)."""
        responses = {"body_type": "unknown_type"}
        scores = compute_dosha_from_quiz(responses)
        # Should fall back to balanced
        assert scores == {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}


# =============================================================================
# determine_constitution_type tests
# =============================================================================


class TestDetermineConstitutionType:
    """Tests for constitution type naming."""

    def test_vata_dominant(self):
        primary, name = determine_constitution_type({"vata": 0.60, "pitta": 0.25, "kapha": 0.15})
        assert primary == "vata"
        assert name == "Adaptive"

    def test_pitta_dominant(self):
        primary, name = determine_constitution_type({"vata": 0.20, "pitta": 0.55, "kapha": 0.25})
        assert primary == "pitta"
        assert name == "Performance"

    def test_kapha_dominant(self):
        primary, name = determine_constitution_type({"vata": 0.15, "pitta": 0.25, "kapha": 0.60})
        assert primary == "kapha"
        assert name == "Conservation"

    def test_combined_when_close(self):
        """When top two doshas are within 10%, use combined name."""
        primary, name = determine_constitution_type({"vata": 0.40, "pitta": 0.35, "kapha": 0.25})
        assert primary == "vata"
        assert name == "Adaptive-Performance"

    def test_balanced_gives_combined(self):
        """Perfectly balanced doshas produce combined name."""
        primary, name = determine_constitution_type({"vata": 0.34, "pitta": 0.33, "kapha": 0.33})
        assert "-" in name  # Combined name expected


# =============================================================================
# Constants tests
# =============================================================================


class TestConstants:
    """Tests for CONSTITUTION_NAMES and DOSHA_FROM_NAME."""

    def test_all_doshas_have_names(self):
        assert set(CONSTITUTION_NAMES.keys()) == {"vata", "pitta", "kapha"}

    def test_reverse_mapping_complete(self):
        for name, dosha in DOSHA_FROM_NAME.items():
            assert dosha in CONSTITUTION_NAMES
            assert CONSTITUTION_NAMES[dosha].lower() == name

    def test_names_are_nonempty(self):
        for dosha, name in CONSTITUTION_NAMES.items():
            assert len(name) > 0, f"Empty name for {dosha}"
