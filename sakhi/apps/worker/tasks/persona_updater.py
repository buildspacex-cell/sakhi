"""Shim module to import persona updater task from legacy apps namespace."""

from __future__ import annotations

try:
    from apps.worker.tasks.persona_updater import run_persona_updater  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - defensive shim
    raise ImportError(
        "apps.worker.tasks.persona_updater module is required for run_persona_updater."
    ) from exc

__all__ = ["run_persona_updater"]

