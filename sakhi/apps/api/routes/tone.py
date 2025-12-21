"""Compatibility shim to expose legacy tone routes via the sakhi namespace."""

from __future__ import annotations

try:
    from apps.api.routes.tone import router  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - defensive shim
    raise ImportError("apps.api.routes.tone module is required for tone routes.") from exc

__all__ = ["router"]

