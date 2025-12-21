"""Compatibility shim to expose legacy presence routes via the sakhi namespace."""

from __future__ import annotations

try:
    from apps.api.routes.presence import router  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - defensive shim
    raise ImportError("apps.api.routes.presence module is required for presence routes.") from exc

__all__ = ["router"]

