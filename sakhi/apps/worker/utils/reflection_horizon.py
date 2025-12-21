from __future__ import annotations

import datetime
import logging
import os
from typing import Any, Dict

try:
    from supabase import create_client as _supabase_create_client
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _supabase_create_client = None

LOGGER = logging.getLogger(__name__)
_SUPABASE_CLIENT: Any | None = None


def _get_supabase_client() -> Any | None:
    """Lazily instantiate Supabase client if settings are present."""
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        if _supabase_create_client is None:
            LOGGER.debug("Supabase not installed; skipping rhythm adjustments.")
            _SUPABASE_CLIENT = False
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_API_KEY")
            if url and key:
                try:
                    _SUPABASE_CLIENT = _supabase_create_client(url, key)
                except Exception as exc:  # pragma: no cover - external failure
                    LOGGER.warning("Supabase client creation failed: %s", exc)
                    _SUPABASE_CLIENT = False
            else:
                _SUPABASE_CLIENT = False
    return _SUPABASE_CLIENT or None


def infer_reflection_horizon(person_id: str, text: str) -> Dict[str, int | str]:
    """
    Return delay minutes and urgency tag based on temporal cues in the text.
    """
    normalized = (text or "").lower()

    if any(keyword in normalized for keyword in ("today", "tonight", "now")):
        base_delay = 60
        urgency = "immediate"
    elif any(keyword in normalized for keyword in ("tomorrow", "this week")):
        base_delay = 12 * 60
        urgency = "near_term"
    elif any(keyword in normalized for keyword in ("next month", "later")):
        base_delay = 3 * 24 * 60
        urgency = "deferred"
    else:
        base_delay = 24 * 60
        urgency = "default"

    adjusted = adjust_by_rhythm(person_id, base_delay)
    return {"delay": int(adjusted), "urgency": urgency}


def adjust_by_rhythm(person_id: str, base_delay: int) -> float:
    client = _get_supabase_client()
    if client is None:
        return float(base_delay)

    try:
        response = (
            client.table("user_rhythm_profile")
            .select("*")
            .eq("person_id", person_id)
            .execute()
        )
    except Exception as exc:  # pragma: no cover - external service failure
        LOGGER.warning("Supabase horizon lookup failed: %s", exc)
        return float(base_delay)

    data = getattr(response, "data", None)
    if not data:
        return float(base_delay)

    record = data[0] or {}
    hours = record.get("optimal_reflection_hours") or [9, 20]
    now_hour = datetime.datetime.utcnow().hour
    if isinstance(hours, list) and now_hour in hours:
        return base_delay / 2
    return base_delay * 1.5
