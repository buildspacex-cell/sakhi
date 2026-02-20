"""Tests for kala.state.dosha — dosha state computation."""

from __future__ import annotations

from kala.state.dosha import (
    KAPHA_KEYWORDS,
    PITTA_KEYWORDS,
    VATA_KEYWORDS,
    compute_dosha_state,
)


class TestComputeDoshaStateDefaults:
    """Empty / missing text returns balanced defaults."""

    def test_empty_string(self) -> None:
        result = compute_dosha_state("", {}, {})
        assert result["dosha"] == {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}
        assert result["confidence"] == 0.3

    def test_none_text(self) -> None:
        result = compute_dosha_state(None, {}, {})  # type: ignore[arg-type]
        assert result["confidence"] == 0.3

    def test_whitespace_only(self) -> None:
        result = compute_dosha_state("   ", {}, {})
        assert result["dosha"]["vata"] == 0.33


class TestKeywordScoring:
    """Keyword presence drives dosha scores."""

    def test_vata_heavy_text(self) -> None:
        text = "I feel scattered and anxious, my mind is racing with creative ideas"
        result = compute_dosha_state(text, {}, {})
        dosha = result["dosha"]
        assert dosha["vata"] > dosha["pitta"]
        assert dosha["vata"] > dosha["kapha"]

    def test_pitta_heavy_text(self) -> None:
        text = "Intense focus on deadline, feeling driven and accomplished"
        result = compute_dosha_state(text, {}, {})
        dosha = result["dosha"]
        assert dosha["pitta"] > dosha["vata"]
        assert dosha["pitta"] > dosha["kapha"]

    def test_kapha_heavy_text(self) -> None:
        text = "Feeling steady and calm, grounded in routine, a bit sluggish"
        result = compute_dosha_state(text, {}, {})
        dosha = result["dosha"]
        assert dosha["kapha"] > dosha["vata"]
        assert dosha["kapha"] > dosha["pitta"]

    def test_no_keywords_returns_balanced(self) -> None:
        text = "Had a meeting about the quarterly report"
        result = compute_dosha_state(text, {}, {})
        dosha = result["dosha"]
        # No keywords matched → balanced fallback
        assert dosha == {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}


class TestNormalization:
    """Scores always sum to 1.0."""

    def test_scores_sum_to_one(self) -> None:
        text = "Scattered anxious racing creative intense focused driven"
        result = compute_dosha_state(text, {}, {})
        total = sum(result["dosha"].values())
        assert abs(total - 1.0) < 0.01

    def test_balanced_sums_to_one(self) -> None:
        result = compute_dosha_state("", {}, {})
        total = sum(result["dosha"].values())
        assert abs(total - 1.0) < 0.01


class TestEmotionalStateIntegration:
    """Emotional signals shift dosha scores."""

    def test_high_activation_negative_valence_boosts_pitta(self) -> None:
        text = "A busy day"
        emotion = {"activation": 0.8, "stability": 0.5, "valence": -0.5}
        result = compute_dosha_state(text, emotion, {})
        # With pitta boost from emotional state
        assert result["dosha"]["pitta"] > 0

    def test_low_stability_boosts_vata(self) -> None:
        text = "A busy day"
        emotion = {"activation": 0.5, "stability": 0.2, "valence": 0.0}
        result = compute_dosha_state(text, emotion, {})
        assert result["dosha"]["vata"] > 0

    def test_low_activation_boosts_kapha(self) -> None:
        text = "A busy day"
        emotion = {"activation": 0.2, "stability": 0.5, "valence": 0.0}
        result = compute_dosha_state(text, emotion, {})
        assert result["dosha"]["kapha"] > 0


class TestRhythmStateIntegration:
    """Rhythm signals shift dosha scores."""

    def test_low_energy_boosts_kapha(self) -> None:
        text = "A normal day"
        rhythm = {"energy_level": 0.2, "structure": 0.5}
        result = compute_dosha_state(text, {}, rhythm)
        assert result["dosha"]["kapha"] > 0

    def test_high_energy_low_structure_boosts_vata(self) -> None:
        text = "A normal day"
        rhythm = {"energy_level": 0.8, "structure": 0.2}
        result = compute_dosha_state(text, {}, rhythm)
        assert result["dosha"]["vata"] > 0


class TestBodyDoshaBlending:
    """Body data blends 60/40 with journal-derived scores."""

    def test_body_dosha_shifts_scores(self) -> None:
        text = "Feeling scattered and anxious"  # Vata-heavy text
        body = {"vata": 0.1, "pitta": 0.8, "kapha": 0.1}  # Pitta body
        result_without = compute_dosha_state(text, {}, {})
        result_with = compute_dosha_state(text, {}, {}, body_dosha=body)
        # Body pitta should pull pitta score up
        assert result_with["dosha"]["pitta"] > result_without["dosha"]["pitta"]

    def test_body_dosha_boosts_confidence(self) -> None:
        text = "Feeling scattered"
        result_without = compute_dosha_state(text, {}, {})
        result_with = compute_dosha_state(text, {}, {}, body_dosha={"vata": 0.5, "pitta": 0.3, "kapha": 0.2})
        assert result_with["confidence"] > result_without["confidence"]

    def test_body_dosha_still_sums_to_one(self) -> None:
        text = "Intense creative day with lots of rest"
        body = {"vata": 0.4, "pitta": 0.4, "kapha": 0.2}
        result = compute_dosha_state(text, {}, {}, body_dosha=body)
        total = sum(result["dosha"].values())
        assert abs(total - 1.0) < 0.01


class TestConfidence:
    """Confidence scales with signal count."""

    def test_more_keywords_higher_confidence(self) -> None:
        text_few = "Feeling anxious"
        text_many = "Scattered anxious racing creative restless insomnia mind racing"
        result_few = compute_dosha_state(text_few, {}, {})
        result_many = compute_dosha_state(text_many, {}, {})
        assert result_many["confidence"] >= result_few["confidence"]

    def test_confidence_capped(self) -> None:
        text = " ".join(VATA_KEYWORDS + PITTA_KEYWORDS + KAPHA_KEYWORDS)
        result = compute_dosha_state(text, {}, {})
        assert result["confidence"] <= 0.95


class TestOutputShape:
    """Return value always has expected keys."""

    def test_has_computed_at(self) -> None:
        result = compute_dosha_state("hello", {}, {})
        assert "computed_at" in result

    def test_dosha_keys(self) -> None:
        result = compute_dosha_state("hello", {}, {})
        assert set(result["dosha"].keys()) == {"vata", "pitta", "kapha"}
