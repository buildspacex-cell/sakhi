"""Shim module that exposes the reflective loop task from the legacy apps namespace."""

from __future__ import annotations

try:
    from apps.worker.tasks.reflective_loop import run_reflective_loop  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - defensive shim
    raise ImportError(
        "apps.worker.tasks.reflective_loop module is required for run_reflective_loop."
    ) from exc

__all__ = ["run_reflective_loop"]

