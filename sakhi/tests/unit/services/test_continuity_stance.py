"""Unit tests for continuity stance extraction and shift detection."""
from __future__ import annotations

import pytest

from sakhi.apps.api.services.continuity.stance import (
    VALID_STANCES,
    detect_stance_shift,
)


# =============================================================================
# VALID_STANCES contract
# =============================================================================


def test_valid_stances_contains_expected_targets():
    expected = {"quality", "speed", "stability", "relationships", "autonomy", "learning", "impact", "simplicity"}
    assert expected == VALID_STANCES


# =============================================================================
# detect_stance_shift (pure logic — uses mocked DB)
# =============================================================================


def _make_rows(stances: list[str]) -> list[dict]:
    """Build fake DB rows ordered newest-first."""
    import datetime as dt

    base = dt.datetime(2026, 4, 25, 12, 0, 0)
    rows = []
    for i, stance in enumerate(stances):
        rows.append({
            "stance": stance,
            "confidence": 0.6,
            "detected_at": base - dt.timedelta(hours=i),
        })
    return rows


@pytest.mark.asyncio
async def test_detect_shift_returns_none_when_insufficient_data(monkeypatch):
    async def _fake_fetch(*args, **kwargs):
        return _make_rows(["quality"])  # only 1 row

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fake_fetch,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is None


@pytest.mark.asyncio
async def test_detect_shift_returns_none_when_no_shift(monkeypatch):
    async def _fake_fetch(*args, **kwargs):
        return _make_rows(["quality", "quality", "quality", "quality", "quality"])

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fake_fetch,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is None


@pytest.mark.asyncio
async def test_detect_shift_returns_shift_when_recent_diverges(monkeypatch):
    # Recent 2: speed, speed — Prior: quality, quality, quality
    async def _fake_fetch(*args, **kwargs):
        return _make_rows(["speed", "speed", "quality", "quality", "quality"])

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fake_fetch,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is not None
    assert result["from"] == "quality"
    assert result["to"] == "speed"
    assert "confidence" in result
    assert "detected_at" in result


@pytest.mark.asyncio
async def test_detect_shift_returns_none_when_recent_disagrees(monkeypatch):
    # Recent 2 are different from each other — not a confirmed shift
    async def _fake_fetch(*args, **kwargs):
        return _make_rows(["speed", "impact", "quality", "quality", "quality"])

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fake_fetch,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is None


@pytest.mark.asyncio
async def test_detect_shift_returns_none_when_prior_mixed(monkeypatch):
    # Prior window has no clear dominant stance
    async def _fake_fetch(*args, **kwargs):
        return _make_rows(["speed", "speed", "quality", "impact", "learning", "stability"])

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fake_fetch,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is None


@pytest.mark.asyncio
async def test_detect_shift_handles_db_error_gracefully(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("DB is down")

    monkeypatch.setattr(
        "sakhi.apps.api.services.continuity.stance.dbfetch",
        _fail,
    )
    result = await detect_stance_shift("person-1", "career")
    assert result is None


# =============================================================================
# what_changed in conversation reasoner prompt
# =============================================================================


def test_what_changed_appears_in_prompt_when_shift_detected():
    from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt

    metadata = {
        "continuity_pack": {
            "topic_key": "career",
            "topic_label": "Career",
            "what_changed": {"from": "quality", "to": "speed", "confidence": 0.7, "detected_at": "2026-04-25"},
        }
    }
    ctx = {"conversation": {"last_emotion": "neutral", "energy_level": 0.5}}
    tone = {"style": "direct", "pace": "balanced", "mirroring": {}}
    result = build_prompt("How am I doing?", ctx, tone, metadata=metadata)
    assert "WHAT CHANGED" in result
    assert "quality" in result
    assert "speed" in result


def test_what_changed_absent_when_no_shift():
    from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt

    metadata = {
        "continuity_pack": {
            "topic_key": "career",
            "topic_label": "Career",
            "what_changed": None,
        }
    }
    ctx = {"conversation": {"last_emotion": "neutral", "energy_level": 0.5}}
    tone = {"style": "direct", "pace": "balanced", "mirroring": {}}
    result = build_prompt("How am I doing?", ctx, tone, metadata=metadata)
    assert "WHAT CHANGED" not in result


def test_what_changed_absent_when_low_confidence():
    from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt

    metadata = {
        "continuity_pack": {
            "topic_key": "career",
            "what_changed": {"from": "quality", "to": "speed", "confidence": 0.2},
        }
    }
    ctx = {"conversation": {"last_emotion": "neutral", "energy_level": 0.5}}
    tone = {"style": "direct", "pace": "balanced", "mirroring": {}}
    result = build_prompt("How am I doing?", ctx, tone, metadata=metadata)
    assert "WHAT CHANGED" not in result


def test_what_changed_in_public_continuity_signal():
    from sakhi.apps.api.routes.turn_v2 import _build_public_continuity_signal

    pack = {
        "topic_key": "career",
        "topic_label": "Career",
        "surface": {"mirror_allowed": True, "detail_allowed": True},
        "history_compact": {"element_count": 8},
        "what_changed": {"from": "quality", "to": "speed", "confidence": 0.7, "detected_at": "2026-04-25"},
    }
    signal = _build_public_continuity_signal(pack)
    assert signal is not None
    assert signal["what_changed"]["from"] == "quality"
    assert signal["what_changed"]["to"] == "speed"
