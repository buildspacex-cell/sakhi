"""Shim to expose reinforcement calibration task from the legacy apps namespace."""

from __future__ import annotations

try:
    from apps.worker.tasks.reinforcement_calibration import run_reinforcement_calibration  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError(
        "apps.worker.tasks.reinforcement_calibration module is required for run_reinforcement_calibration."
    ) from exc

__all__ = ["run_reinforcement_calibration"]

