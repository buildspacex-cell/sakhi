"""Tests for kala.state.guna — guna state computation."""

from __future__ import annotations

from kala.state.guna import compute_guna_state


class TestComputeGunaStateDefaults:
    """Empty / missing text returns balanced defaults."""

    def test_empty_string(self) -> None:
        result = compute_guna_state("", {})
        assert result["sattva"] == 0.33
        assert result["rajas"] == 0.34
        assert result["tamas"] == 0.33
        assert result["confidence"] == 0.3

    def test_none_text(self) -> None:
        result = compute_guna_state(None, {})  # type: ignore[arg-type]
        assert result["confidence"] == 0.3

    def test_whitespace_only(self) -> None:
        result = compute_guna_state("   ", {})
        assert result["sattva"] == 0.33


class TestKeywordScoring:
    """Keyword presence drives guna scores."""

    def test_sattva_heavy_text(self) -> None:
        text = "Feeling peaceful and clear, balanced and centered with deep insight"
        result = compute_guna_state(text, {})
        assert result["sattva"] > result["rajas"]
        assert result["sattva"] > result["tamas"]

    def test_rajas_heavy_text(self) -> None:
        text = "Busy day, rushing to deadline, stressed and overwhelmed with meetings"
        result = compute_guna_state(text, {})
        assert result["rajas"] > result["sattva"]
        assert result["rajas"] > result["tamas"]

    def test_tamas_heavy_text(self) -> None:
        text = "Tired and sluggish, drained and unmotivated, need rest"
        result = compute_guna_state(text, {})
        assert result["tamas"] > result["sattva"]
        assert result["tamas"] > result["rajas"]

    def test_no_keywords_returns_balanced(self) -> None:
        text = "Went to the library to return a book"
        result = compute_guna_state(text, {})
        assert result["sattva"] == 0.33
        assert result["rajas"] == 0.34
        assert result["tamas"] == 0.33


class TestNormalization:
    """Scores always sum to 1.0."""

    def test_scores_sum_to_one(self) -> None:
        text = "Peaceful clarity but also busy rushing and tired sluggish"
        result = compute_guna_state(text, {})
        total = result["sattva"] + result["rajas"] + result["tamas"]
        assert abs(total - 1.0) < 0.01

    def test_balanced_sums_to_one(self) -> None:
        result = compute_guna_state("", {})
        total = result["sattva"] + result["rajas"] + result["tamas"]
        assert abs(total - 1.0) < 0.01


class TestEmotionalStateIntegration:
    """Emotional signals shift guna scores."""

    def test_positive_valence_high_stability_boosts_sattva(self) -> None:
        text = "A regular day"
        emotion = {"valence": 0.5, "activation": 0.5, "stability": 0.8}
        result = compute_guna_state(text, emotion)
        assert result["sattva"] > 0.33

    def test_high_activation_instability_boosts_rajas(self) -> None:
        text = "A regular day"
        emotion = {"valence": 0.0, "activation": 0.8, "stability": 0.3}
        result = compute_guna_state(text, emotion)
        assert result["rajas"] > 0.34

    def test_low_activation_negative_valence_boosts_tamas(self) -> None:
        text = "A regular day"
        emotion = {"valence": -0.5, "activation": 0.2, "stability": 0.5}
        result = compute_guna_state(text, emotion)
        assert result["tamas"] > 0.33


class TestConfidence:
    """Confidence scales with signal count."""

    def test_more_keywords_higher_confidence(self) -> None:
        text_few = "Feeling tired"
        text_many = "Tired heavy sluggish unmotivated foggy drained stuck"
        result_few = compute_guna_state(text_few, {})
        result_many = compute_guna_state(text_many, {})
        assert result_many["confidence"] >= result_few["confidence"]

    def test_confidence_capped(self) -> None:
        from kala.state.guna import RAJAS_KEYWORDS, SATTVA_KEYWORDS, TAMAS_KEYWORDS

        text = " ".join(SATTVA_KEYWORDS + RAJAS_KEYWORDS + TAMAS_KEYWORDS)
        result = compute_guna_state(text, {})
        assert result["confidence"] <= 0.85


class TestOutputShape:
    """Return value always has expected keys."""

    def test_has_computed_at(self) -> None:
        result = compute_guna_state("hello", {})
        assert "computed_at" in result

    def test_guna_keys(self) -> None:
        result = compute_guna_state("hello", {})
        assert "sattva" in result
        assert "rajas" in result
        assert "tamas" in result
        assert "confidence" in result
