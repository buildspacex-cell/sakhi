"""Tests for kala.signals.context_tags — deterministic tag extraction."""

from __future__ import annotations

from kala.signals.context_tags import extract_context_tags


class TestEmptyInput:
    """Edge cases for invalid / empty input."""

    def test_empty_string(self) -> None:
        assert extract_context_tags("") == []

    def test_none_input(self) -> None:
        assert extract_context_tags(None) == []  # type: ignore[arg-type]

    def test_whitespace_only(self) -> None:
        assert extract_context_tags("   ") == []

    def test_non_string(self) -> None:
        assert extract_context_tags(123) == []  # type: ignore[arg-type]


class TestBodyDimension:
    """Body-related tags."""

    def test_sleep_tag(self) -> None:
        tags = extract_context_tags("I didn't get enough sleep last night")
        dims = [t["dimension"] for t in tags]
        assert "body" in dims

    def test_fatigue_tag(self) -> None:
        tags = extract_context_tags("Deep fatigue today")
        body_tags = [t for t in tags if t["dimension"] == "body"]
        assert any(t["signal_key"] == "energy_rest" for t in body_tags)

    def test_discomfort_tag(self) -> None:
        tags = extract_context_tags("My back pain is flaring up")
        body_tags = [t for t in tags if t["dimension"] == "body"]
        assert any(t["signal_key"] == "discomfort" for t in body_tags)


class TestEmotionDimension:
    """Emotion-related tags."""

    def test_stress_tag(self) -> None:
        tags = extract_context_tags("Extreme stress from work")
        emotion_tags = [t for t in tags if t["dimension"] == "emotion"]
        assert any(t["signal_key"] == "stress" for t in emotion_tags)

    def test_calm_tag(self) -> None:
        tags = extract_context_tags("Feeling calm and grounded")
        emotion_tags = [t for t in tags if t["dimension"] == "emotion"]
        assert any(t["signal_key"] == "calm" for t in emotion_tags)


class TestEnergyDimension:
    """Energy-related tags."""

    def test_activation_up(self) -> None:
        tags = extract_context_tags("Very productive and energized today")
        energy_tags = [t for t in tags if t["dimension"] == "energy"]
        assert any(t["polarity"] == "up" for t in energy_tags)

    def test_activation_down(self) -> None:
        tags = extract_context_tags("Feeling sluggish and drained")
        energy_tags = [t for t in tags if t["dimension"] == "energy"]
        assert any(t["polarity"] == "down" for t in energy_tags)


class TestWorkDimension:
    """Work-related tags."""

    def test_load_up(self) -> None:
        tags = extract_context_tags("Back to back meetings all day")
        work_tags = [t for t in tags if t["dimension"] == "work"]
        assert any(t["signal_key"] == "load" for t in work_tags)

    def test_recovery_down(self) -> None:
        tags = extract_context_tags("Took a long break and went for a walk")
        work_tags = [t for t in tags if t["dimension"] == "work"]
        assert any(t["signal_key"] == "recovery" for t in work_tags)


class TestMindDimension:
    """Mind-related tags."""

    def test_clarity_up(self) -> None:
        tags = extract_context_tags("Have a clear plan and feel organized")
        mind_tags = [t for t in tags if t["dimension"] == "mind"]
        assert any(t["signal_key"] == "clarity" and t["polarity"] == "up" for t in mind_tags)

    def test_clarity_down(self) -> None:
        tags = extract_context_tags("My thoughts are scattered and distracted")
        mind_tags = [t for t in tags if t["dimension"] == "mind"]
        assert any(t["signal_key"] == "clarity" and t["polarity"] == "down" for t in mind_tags)


class TestMaxTags:
    """At most 5 tags are returned."""

    def test_max_five_tags(self) -> None:
        # Text with keywords from all dimensions
        text = (
            "Tired from poor sleep with back pain, "
            "extreme stress but also calm, "
            "energized yet sluggish, "
            "meetings and deadlines but took a break, "
            "clear plan but scattered thoughts"
        )
        tags = extract_context_tags(text)
        assert len(tags) <= 5


class TestTagStructure:
    """Each tag has the expected keys."""

    def test_tag_keys(self) -> None:
        tags = extract_context_tags("Feeling anxious and stressed")
        for tag in tags:
            assert "dimension" in tag
            assert "signal_key" in tag
            assert "polarity" in tag
            assert "intensity" in tag
