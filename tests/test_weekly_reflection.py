import datetime as dt
import json

import pytest

from sakhi.apps.worker.tasks.weekly_reflection import generate_weekly_reflection


@pytest.mark.asyncio
async def test_weekly_reflection_ephemeral_and_filtered(monkeypatch):
    week_row = {
        "week_start": dt.date(2025, 1, 1),
        "week_end": dt.date(2025, 1, 7),
        "episodic_stats": {"episode_count": 5, "distinct_days": 4},
        "theme_stats": [{"key": "recovery", "weight": 0.4}, {"key": "workload", "weight": 0.3}],
        "contrast_stats": {"highest_energy_dimension": "body", "lowest_energy_dimension": "work"},
        "delta_stats": {"energy": "down", "work_pressure": "up"},
        "confidence": 0.7,
    }

    async def fake_q(sql, *args, **kwargs):
        return week_row

    monkeypatch.setattr("sakhi.apps.worker.tasks.weekly_reflection.q", fake_q)

    longitudinal_state = {
        "mind": {
            "direction": "up",
            "volatility": "low",
            "confidence": 0.72,
            "window": {"start": "2025-01-01", "end": "2025-01-07"},
            "last_updated_at": dt.datetime.utcnow().isoformat(),
        },
        "emotion": {
            "direction": "flat",
            "volatility": "medium",
            "confidence": 0.3,  # Should be dropped (below threshold)
            "window": {"start": "2025-01-01", "end": "2025-01-07"},
        },
    }

    result = await generate_weekly_reflection("u1", longitudinal_state)

    assert result["period"] == "weekly"
    assert "→" in result["window"]

    reflection = result["reflection"]
    assert "overview" in reflection and reflection["overview"]
    assert "mind" in reflection  # high confidence kept
    assert "emotion" not in reflection  # low confidence removed

    # No identity or advice language
    full_text = " ".join(reflection.values()).lower()
    assert "you are" not in full_text
    assert "should" not in full_text

    # Output is ephemeral (no persistence side effects possible here)
    assert isinstance(result["confidence_note"], str) and result["confidence_note"]


@pytest.mark.asyncio
async def test_weekly_reflection_llm_guard(monkeypatch):
    week_row = {
        "week_start": dt.date(2025, 2, 1),
        "week_end": dt.date(2025, 2, 7),
        "episodic_stats": {"episode_count": 2, "distinct_days": 2},
        "theme_stats": [],
        "contrast_stats": {},
        "delta_stats": {},
        "confidence": 0.8,
    }

    async def fake_q(sql, *args, **kwargs):
        return week_row

    async def bad_llm(prompt: str, system: str | None = None, person_id: str | None = None):
        # Return a JSON payload that would be rejected for identity/advice language
        return json.dumps(
            {
                "period": "weekly",
                "window": "2025-02-01 → 2025-02-07",
                "reflection": {"overview": "You should know you are great."},
                "confidence_note": "ok",
            }
        )

    monkeypatch.setattr("sakhi.apps.worker.tasks.weekly_reflection.q", fake_q)
    monkeypatch.setattr("sakhi.apps.worker.tasks.weekly_reflection.llm_router.text", bad_llm)

    result = await generate_weekly_reflection("u1", {})

    # Should fall back to deterministic renderer and strip forbidden language
    reflection = result["reflection"]
    text = " ".join(reflection.values()).lower()
    assert "you should" not in text
    assert "you are" not in text
