import pytest

from sakhi.apps.api.services.reflection.narration_foundation import build_narrative_notes, validate_narration


def test_validate_narration_blocks_directive():
    text = (
        "Most days felt busy and went by fast. "
        "Evenings had most of the activity. "
        "It should slow down soon. "
        "Feelings stayed even, without sharp swings. "
        "Routines stayed about the same."
    )
    result = validate_narration(text)
    assert result["passed"] is False
    assert "directive language detected" in result["fail_reasons"]


def test_validate_narration_allows_neutral():
    text = (
        "Most activity happened later in the day. "
        "Days felt busy and moved quickly. "
        "Feelings were steady, even when things were tense. "
        "Nothing swung wildly up or down. "
        "Routines stayed mostly the same."
    )
    result = validate_narration(text)
    assert result["passed"] is True


def test_build_notes_uses_states():
    states = {"rhythm_state": {"overall": {}}, "soul_state": {"identity_themes": []}}
    journals = [{"snippet": "A short journal", "created_at": None}]
    episodic = [{"summary": "A short episode", "ts": None}]
    suppression = {"suppressed_count": 1, "top_reason": "volatility"}
    notes = build_narrative_notes(states, journals, episodic, suppression, window_days=7)
    assert notes["timeframe"] == "last 7 days"
    assert "rhythm signals present with time-of-day slots" in notes["dominant_texture"]
    assert notes["evidence_anchors"]
