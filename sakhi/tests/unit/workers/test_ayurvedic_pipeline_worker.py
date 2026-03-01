from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from sakhi.apps.worker.tasks import ayurvedic_pipeline


@pytest.mark.asyncio
async def test_run_ayurvedic_pipeline_uses_fallback_when_legacy_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        ayurvedic_pipeline,
        "_anchor_dates_from_stm",
        AsyncMock(
            return_value={
                "week_start": date(2026, 2, 23),
                "month_start": date(2026, 2, 1),
                "anchor_date": date(2026, 2, 26),
            }
        ),
    )
    legacy_mock = AsyncMock(return_value={"mode": "fallback_required", "reason": "No module named 'core'"})
    monkeypatch.setattr(ayurvedic_pipeline, "_run_legacy_pipeline", legacy_mock)
    fallback_mock = AsyncMock(
        return_value={
            "mode": "fallback",
            "executed": ["body_refresh", "friction_refresh"],
        }
    )
    monkeypatch.setattr(ayurvedic_pipeline, "_run_fallback_pipeline", fallback_mock)

    result = await ayurvedic_pipeline.run_ayurvedic_pipeline("11111111-1111-1111-1111-111111111111")

    assert result["mode"] == "fallback"
    assert "body_refresh" in result["executed"]
    legacy_mock.assert_not_awaited()
    fallback_mock.assert_awaited_once()
    kwargs = fallback_mock.await_args.kwargs
    assert kwargs["reason"] == "legacy workers disabled (using native pipeline)"


@pytest.mark.asyncio
async def test_run_ayurvedic_pipeline_returns_legacy_when_available(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SAKHI_ENABLE_LEGACY_AYURVEDIC", "1")
    monkeypatch.setattr(
        ayurvedic_pipeline,
        "_anchor_dates_from_stm",
        AsyncMock(
            return_value={
                "week_start": date(2026, 2, 23),
                "month_start": date(2026, 2, 1),
                "anchor_date": date(2026, 2, 26),
            }
        ),
    )
    monkeypatch.setattr(
        ayurvedic_pipeline,
        "_run_legacy_pipeline",
        AsyncMock(
            return_value={
                "mode": "legacy",
                "executed": ["elemental_stm", "energy_weekly"],
                "steps": [],
            }
        ),
    )
    fallback_mock = AsyncMock(return_value={"mode": "fallback", "executed": ["body_refresh"]})
    monkeypatch.setattr(ayurvedic_pipeline, "_run_fallback_pipeline", fallback_mock)

    result = await ayurvedic_pipeline.run_ayurvedic_pipeline("22222222-2222-2222-2222-222222222222")

    assert result["mode"] == "legacy"
    assert result["executed"] == ["elemental_stm", "energy_weekly"]
    fallback_mock.assert_not_awaited()
