from __future__ import annotations

import datetime
import os
from typing import Any, Dict, Iterable, List

import logging

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]

try:
    from supabase import create_client
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    create_client = None  # type: ignore[assignment]

from sakhi.apps.worker.utils.db import db_fetch, db_upsert

LOGGER = logging.getLogger(__name__)


def _get_supabase_client() -> Any | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_API_KEY")
    if not url or not key:
        return None
    if create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


async def learn_rhythm_profile(person_id: str) -> None:
    """
    Learns user rhythm from journaling & conversation timestamps.
    """
    if pd is None:
        LOGGER.warning("pandas not installed; skipping learn_rhythm_profile")
        return
    _get_supabase_client()  # touch configuration for future use

    entries_payload = db_fetch("journal_entries", {"user_id": person_id})
    entries: Iterable[Dict[str, Any]]
    if isinstance(entries_payload, list):
        entries = entries_payload
    elif isinstance(entries_payload, dict) and entries_payload.get("entries"):
        entries_value = entries_payload.get("entries")
        entries = entries_value if isinstance(entries_value, list) else [entries_payload]
    elif isinstance(entries_payload, dict) and entries_payload:
        entries = [entries_payload]
    else:
        return

    df = pd.DataFrame(list(entries))
    if df.empty:
        return

    ts_column = None
    for candidate in ("ts", "timestamp", "created_at"):
        if candidate in df.columns:
            ts_column = candidate
            break
    if ts_column is None:
        return

    df["ts"] = pd.to_datetime(df[ts_column])
    df = df.dropna(subset=["ts"])
    if df.empty:
        return

    df["hour"] = df["ts"].dt.hour
    if df["hour"].empty:
        return

    hour_counts = df["hour"].value_counts()
    best_hours: List[int] = list(map(int, hour_counts.head(3).index.tolist()))
    chrono = "morning" if best_hours and max(best_hours) < 12 else "evening"
    profile = {
        "person_id": person_id,
        "chrono_type": chrono,
        "optimal_reflection_hours": best_hours,
        "avg_response_time": float(df["hour"].mean()),
        "energy_pattern": {int(hour): int(count) for hour, count in hour_counts.items()},
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }

    db_upsert("user_rhythm_profile", profile)


__all__ = ["learn_rhythm_profile"]
