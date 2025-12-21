from __future__ import annotations

import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec

logger = logging.getLogger(__name__)

# Configurable windows
LEARNING_WINDOW_DAYS = int(os.getenv("LEARNING_WINDOW_DAYS", "28") or "28")
DECAY_DAYS = int(os.getenv("DECAY_DAYS", "21") or "21")

ALLOWED_DIMENSIONS = {"body", "mind", "emotion", "energy", "work"}
INTENSITY_LEVELS = {"low": 0, "medium": 1, "high": 2}


def _normalize_signal(tag: Any) -> Tuple[str, str, str, str] | None:
    """Pull a normalized signal tuple from a context_tag entry."""
    if not isinstance(tag, dict):
        return None
    dim = str(tag.get("dimension") or "").strip().lower()
    key = str(tag.get("signal_key") or "").strip().lower()
    pol = str(tag.get("polarity") or "").strip().lower()
    intensity = str(tag.get("intensity") or "").strip().lower()
    if dim not in ALLOWED_DIMENSIONS:
        return None
    if not key or pol not in {"up", "down", "neutral"}:
        return None
    if intensity not in INTENSITY_LEVELS:
        intensity = "medium"
    return dim, key, pol, intensity


def _direction_from_polarities(polarities: List[str]) -> str:
    ups = polarities.count("up")
    downs = polarities.count("down")
    if ups and not downs:
        return "up"
    if downs and not ups:
        return "down"
    if not ups and not downs:
        return "stable"
    return "volatile"


def _volatility(polarities: List[str], intensities: List[str]) -> str:
    ups = "up" in polarities
    downs = "down" in polarities
    if ups and downs:
        return "high"
    spread = max(INTENSITY_LEVELS[i] for i in intensities) - min(INTENSITY_LEVELS[i] for i in intensities)
    if spread >= 2:
        return "high"
    if spread == 1:
        return "medium"
    return "low"


def _confidence(num_events: int, span_days: int, vol: str, now: datetime, last_ts: datetime | None) -> float:
    base = 0.15 + 0.05 * min(num_events, 10) + 0.02 * min(span_days, 30)
    if vol == "medium":
        base -= 0.1
    elif vol == "high":
        base -= 0.2
    base = max(0.0, min(1.0, base))

    if last_ts:
        gap_days = (now - last_ts).days
        if gap_days > DECAY_DAYS:
            decay_factor = max(0.0, 1 - ((gap_days - DECAY_DAYS) / DECAY_DAYS))
            base *= decay_factor
    return max(0.0, min(1.0, base))


def _decay_existing(state: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    updated = {}
    for dim, signals in state.items():
        if not isinstance(signals, dict):
            continue
        updated[dim] = {}
        for key, payload in signals.items():
            if not isinstance(payload, dict):
                continue
            last_ts_raw = payload.get("last_episode_at")
            try:
                last_ts = datetime.fromisoformat(last_ts_raw) if last_ts_raw else None
            except Exception:
                last_ts = None
            confidence = float(payload.get("confidence") or 0.0)
            if last_ts:
                gap_days = (now - last_ts).days
                if gap_days > DECAY_DAYS:
                    factor = max(0.0, 1 - ((gap_days - DECAY_DAYS) / DECAY_DAYS))
                    confidence = max(0.0, min(1.0, confidence * factor))
            payload = dict(payload)
            payload["confidence"] = confidence
            payload["last_updated_at"] = now.isoformat()
            updated[dim][key] = payload
    return updated


def update_longitudinal_state(
    current_state: Dict[str, Any], episodes: List[Dict[str, Any]], now: datetime
) -> Dict[str, Any]:
    """Pure function to derive longitudinal_state from episodic signals."""
    state = _decay_existing(current_state or {}, now)

    grouped: Dict[Tuple[str, str], List[Tuple[str, str, datetime]]] = defaultdict(list)
    for ep in episodes:
        tags = ep.get("context_tags") or []
        ts_raw = ep.get("created_at") or ep.get("episode_ts")
        try:
            ts = ts_raw if isinstance(ts_raw, datetime) else datetime.fromisoformat(ts_raw)
        except Exception:
            continue
        for tag in tags if isinstance(tags, list) else []:
            normalized = _normalize_signal(tag)
            if not normalized:
                continue
            dim, key, pol, intensity = normalized
            grouped[(dim, key)].append((pol, intensity, ts))

    for (dim, key), entries in grouped.items():
        polarities = [p for p, _, _ in entries]
        intensities = [i for _, i, _ in entries]
        timestamps = [t for _, _, t in entries]
        direction = _direction_from_polarities(polarities)
        vol = _volatility(polarities, intensities)
        span_days = max(1, (max(timestamps) - min(timestamps)).days + 1)
        last_ts = max(timestamps)
        conf = _confidence(len(entries), span_days, vol, now, last_ts)

        if dim not in state:
            state[dim] = {}
        state[dim][key] = {
            "direction": direction,
            "volatility": vol,
            "confidence": conf,
            "observed_over_days": span_days,
            "window": {
                "start": min(timestamps).date().isoformat(),
                "end": max(timestamps).date().isoformat(),
            },
            "last_episode_at": last_ts.isoformat(),
            "last_updated_at": now.isoformat(),
        }

    return state


async def run_weekly_learning(person_id: str | None = None) -> Dict[str, Any]:
    """
    Deterministic weekly learning worker.
    Reads episodic memory → updates personal_model.longitudinal_state.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=LEARNING_WINDOW_DAYS)

    if person_id:
        persons = [{"person_id": person_id}]
    else:
        persons = await q("SELECT person_id, longitudinal_state FROM personal_model")

    results: Dict[str, Any] = {"processed": 0, "updated": 0}

    for row in persons:
        pid = row.get("person_id") or row.get("id")
        if not pid:
            continue

        episodes = await q(
            """
            SELECT entry_id, created_at, context_tags
            FROM memory_episodic
            WHERE person_id = $1
              AND created_at >= $2
            ORDER BY created_at ASC
            """,
            pid,
            window_start,
        )

        current_state = row.get("longitudinal_state") if row else {}
        new_state = update_longitudinal_state(current_state or {}, episodes or [], now)

        await dbexec(
            """
            UPDATE personal_model
            SET longitudinal_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            pid,
            new_state,
        )
        results["processed"] += 1
        results["updated"] += 1

    return results


__all__ = ["run_weekly_learning", "update_longitudinal_state"]
