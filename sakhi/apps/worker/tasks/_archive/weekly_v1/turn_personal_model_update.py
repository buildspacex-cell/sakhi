from __future__ import annotations

import logging
import os
from collections import defaultdict
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q

logger = logging.getLogger(__name__)

# Config
PM_UPDATE_WINDOW_DAYS = int(os.getenv("PM_UPDATE_WINDOW_DAYS", "7") or "7")
DIRECTION_EPS = 0.05
ALLOWED_DIMENSIONS = {"body", "mind", "emotion", "energy", "work"}


@dataclass
class SignalSnapshot:
    level: Optional[float] = None
    volatility: Optional[float] = None
    confidence: Optional[float] = None
    count: int = 0
    direction_hint: Optional[str] = None  # e.g., slope from rollup


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _vol_to_numeric(vol: Any) -> Optional[float]:
    mapping = {"low": 0.2, "medium": 0.5, "high": 0.8}
    if isinstance(vol, str):
        return mapping.get(vol.lower())
    try:
        return float(vol)
    except Exception:
        return None


def _avg(lst: List[float]) -> Optional[float]:
    return sum(lst) / len(lst) if lst else None


def _select_rollup(rows: List[Dict[str, Any]], window_start: datetime, window_end: datetime) -> Optional[Dict[str, Any]]:
    """Pick the rollup whose week_start falls inside [window_start, window_end)."""
    candidate = None
    for row in rows:
        ws = row.get("week_start")
        if not ws:
            continue
        ws_dt = ws if isinstance(ws, datetime) else datetime.fromisoformat(str(ws))
        if window_start.replace(tzinfo=None) <= ws_dt < window_end.replace(tzinfo=None):
            candidate = row
    return candidate


def _compute_direction(current: Optional[float], previous: Optional[float], hint: Optional[str]) -> Tuple[str, float]:
    if current is None and previous is None:
        return "flat", 0.0
    if current is None:
        return "flat", 0.0
    if previous is None:
        if hint in {"up", "down"}:
            return hint, _clamp(abs(current), 0.0, 1.0)
        return "flat", _clamp(abs(current), 0.0, 1.0)
    delta = current - previous
    if delta > DIRECTION_EPS:
        return "up", _clamp(abs(delta), 0.0, 1.0)
    if delta < -DIRECTION_EPS:
        return "down", _clamp(abs(delta), 0.0, 1.0)
    return "flat", _clamp(abs(delta), 0.0, 1.0)


def _compute_confidence(
    snapshot: SignalSnapshot,
    prev_conf: float,
    prev_direction: str,
    direction: str,
    has_prev_window: bool,
) -> float:
    conf = 0.1
    if snapshot.confidence is not None:
        conf += 0.4 * _clamp(snapshot.confidence)
    if snapshot.count >= 3:
        conf += 0.1
    if snapshot.count >= 6:
        conf += 0.05
    if direction and prev_direction and direction == prev_direction and has_prev_window:
        conf += 0.1
    if direction == "flat":
        conf -= 0.05
    if snapshot.count == 0 and snapshot.level is None:
        conf = max(0.05, conf - 0.2)
    # Blend with previous confidence to make moves reversible and decaying
    conf = (conf + prev_conf * 0.4) / 1.4
    return _clamp(conf)


def _compute_lifecycle(conf: float, prev_conf: float, direction: str, prev_direction: str) -> str:
    if conf < 0.4:
        return "emerging"
    if prev_direction and direction and direction != prev_direction and conf <= prev_conf:
        return "decaying"
    if conf >= 0.6 and direction == prev_direction and direction in {"up", "down", "flat"}:
        return "stabilizing"
    if conf < prev_conf:
        return "decaying"
    return "stabilizing" if conf >= 0.6 else "emerging"


def _build_snapshot_from_rollup(rollup: Dict[str, Any], dimension: str) -> SignalSnapshot:
    data = rollup.get("rollup") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {}
    node = data.get(dimension) or {}
    return SignalSnapshot(
        level=_clamp(float(node.get("avg_level")), 0.0, 1.0) if node.get("avg_level") is not None else None,
        volatility=_vol_to_numeric(node.get("volatility")),
        confidence=_clamp(float(node.get("confidence") or rollup.get("confidence") or 0.0), 0.0, 1.0),
        count=0,
        direction_hint=node.get("slope"),
    )


def _merge_episodic(tags: List[Dict[str, Any]], snapshot: SignalSnapshot, target_dim: str) -> SignalSnapshot:
    """Use explicit context_tags (dimension, polarity, intensity) without inference."""
    polarity_map = {"up": 1, "down": -1, "neutral": 0}
    polarity_scores = []
    for tag in tags or []:
        if not isinstance(tag, dict):
            continue
        dim = str(tag.get("dimension") or "").lower()
        if dim != target_dim:
            continue
        pol = str(tag.get("polarity") or "").lower()
        intensity = str(tag.get("intensity") or "medium").lower()
        if dim not in ALLOWED_DIMENSIONS:
            continue
        if pol not in polarity_map:
            continue
        weight = 1.0 if intensity == "medium" else 1.2 if intensity == "high" else 0.8
        polarity_scores.append(polarity_map[pol] * weight)
    merged = SignalSnapshot(**snapshot.__dict__)
    merged.count += len(polarity_scores)
    if polarity_scores:
        adj = _clamp(sum(polarity_scores) / (len(polarity_scores) * 2) + 0.5, 0.0, 1.0)
        if merged.level is None:
            merged.level = adj
        else:
            merged.level = _clamp((merged.level + adj) / 2, 0.0, 1.0)
    return merged


def _work_from_planner(pressure: Dict[str, Any]) -> SignalSnapshot:
    if not pressure:
        return SignalSnapshot()
    p = pressure.get("pressure") or {}
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except Exception:
            p = {}
    # Deterministic load score from numeric fields only.
    load_components = []
    for key in ("carryover_rate", "fragmentation_score", "urgency_ratio"):
        val = p.get(key)
        try:
            load_components.append(float(val))
        except Exception:
            continue
    if p.get("overload_flag"):
        load_components.append(1.0)
    level = _clamp(_avg(load_components) if load_components else 0.0, 0.0, 1.0)
    return SignalSnapshot(
        level=level if load_components else None,
        volatility=0.5 if load_components else None,
        confidence=_clamp(float(pressure.get("confidence") or 0.0), 0.0, 1.0),
        count=p.get("open_count", 0) if isinstance(p.get("open_count"), int) else 0,
        direction_hint="up" if p.get("overload_flag") else None,
    )


def _combine_snapshots(
    current: Dict[str, SignalSnapshot],
    previous: Dict[str, SignalSnapshot],
    existing_state: Dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> Dict[str, Any]:
    if isinstance(existing_state, str):
        try:
            existing_state = json.loads(existing_state)
        except Exception:
            existing_state = {}
    updated: Dict[str, Any] = {}
    for dim in ALLOWED_DIMENSIONS:
        cur = current.get(dim, SignalSnapshot())
        prev = previous.get(dim, SignalSnapshot())

        prev_state = ((existing_state or {}).get(dim) or {}).get(dim) or {}
        # Fallback to last stored direction/confidence if available
        prev_conf = float(((existing_state or {}).get(dim) or {}).get("confidence") or 0.0)
        prev_direction = str(((existing_state or {}).get(dim) or {}).get("direction") or "")
        direction, magnitude = _compute_direction(cur.level, prev.level, cur.direction_hint)
        vol_values = [v for v in (cur.volatility, prev.volatility) if v is not None]
        volatility = _avg(vol_values) if vol_values else 0.0
        conf = _compute_confidence(cur, prev_conf, prev_direction, direction, has_prev_window=prev.level is not None)
        lifecycle = _compute_lifecycle(conf, prev_conf, direction, prev_direction)

        updated[dim] = {
            "direction": direction,
            "magnitude": _clamp(magnitude),
            "volatility": _clamp(volatility if volatility is not None else 0.0),
            "confidence": conf,
            "window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
            },
            "lifecycle": lifecycle,
            "last_updated_at": now.isoformat(),
        }
    return updated


async def _load_person_rows(person_id: Optional[str]) -> List[Dict[str, Any]]:
    if person_id:
        row = await q("SELECT person_id, longitudinal_state FROM personal_model WHERE person_id = $1", person_id, one=True)
        return [row] if row else []
    return await q("SELECT person_id, longitudinal_state FROM personal_model")


async def run_turn_personal_model_update(person_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic weekly personal model updater.
    Reads episodic + rhythm rollups + planner pressure → writes only longitudinal_state.
    No prose, no identity, no LLM.
    """
    now = datetime.now(timezone.utc)
    window_end = now
    window_start = now - timedelta(days=PM_UPDATE_WINDOW_DAYS)
    prev_window_end = window_start
    prev_window_start = window_start - timedelta(days=PM_UPDATE_WINDOW_DAYS)

    persons = await _load_person_rows(person_id)
    results = {"processed": 0, "updated": 0}

    for row in persons:
        pid = row.get("person_id") or row.get("id")
        if not pid:
            continue

        # Rhythm rollups (current + previous)
        rhythm_rows = await q(
            """
            SELECT week_start, week_end, rollup, confidence
            FROM rhythm_weekly_rollups
            WHERE person_id = $1
              AND week_start >= $2
            ORDER BY week_start ASC
            """,
            pid,
            prev_window_start.date(),
        )
        current_rhythm = _select_rollup(rhythm_rows, window_start, window_end)
        previous_rhythm = _select_rollup(rhythm_rows, prev_window_start, prev_window_end)

        # Planner pressure (current + previous)
        planner_rows = await q(
            """
            SELECT week_start, week_end, pressure, confidence
            FROM planner_weekly_pressure
            WHERE person_id = $1
              AND week_start >= $2
            ORDER BY week_start ASC
            """,
            pid,
            prev_window_start.date(),
        )
        current_planner = _select_rollup(planner_rows, window_start, window_end)
        previous_planner = _select_rollup(planner_rows, prev_window_start, prev_window_end)

        # Episodic tags
        episodic_current = await q(
            """
            SELECT context_tags
            FROM memory_episodic
            WHERE user_id = $1
              AND created_at >= $2 AND created_at < $3
            """,
            pid,
            window_start,
            window_end,
        )
        episodic_previous = await q(
            """
            SELECT context_tags
            FROM memory_episodic
            WHERE user_id = $1
              AND created_at >= $2 AND created_at < $3
            """,
            pid,
            prev_window_start,
            prev_window_end,
        )

        current_snapshots: Dict[str, SignalSnapshot] = defaultdict(SignalSnapshot)
        previous_snapshots: Dict[str, SignalSnapshot] = defaultdict(SignalSnapshot)

        # Rhythm-driven dimensions
        if current_rhythm:
            for dim in ("body", "mind", "emotion", "energy"):
                current_snapshots[dim] = _build_snapshot_from_rollup(current_rhythm, dim)
        if previous_rhythm:
            for dim in ("body", "mind", "emotion", "energy"):
                previous_snapshots[dim] = _build_snapshot_from_rollup(previous_rhythm, dim)

        # Episodic overlays (mind/emotion primarily, but allow all allowed dims)
        for row_tags in episodic_current or []:
            tags = row_tags.get("context_tags") if isinstance(row_tags, dict) else row_tags
            for dim in ALLOWED_DIMENSIONS:
                current_snapshots[dim] = _merge_episodic(tags, current_snapshots.get(dim, SignalSnapshot()), dim)
        for row_tags in episodic_previous or []:
            tags = row_tags.get("context_tags") if isinstance(row_tags, dict) else row_tags
            for dim in ALLOWED_DIMENSIONS:
                previous_snapshots[dim] = _merge_episodic(tags, previous_snapshots.get(dim, SignalSnapshot()), dim)

        # Work from planner pressure
        if current_planner:
            current_snapshots["work"] = _work_from_planner(current_planner)
        if previous_planner:
            previous_snapshots["work"] = _work_from_planner(previous_planner)

        existing_state = row.get("longitudinal_state") or {}
        new_state = _combine_snapshots(
            current=current_snapshots,
            previous=previous_snapshots,
            existing_state=existing_state,
            window_start=window_start,
            window_end=window_end,
            now=now,
        )
        new_state_json = json.dumps(new_state)

        await dbexec(
            """
            UPDATE personal_model
            SET longitudinal_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            pid,
            new_state_json,
        )
        results["processed"] += 1
        results["updated"] += 1

    if persons:
        logger.info(
            "turn_personal_model_update complete window=%s→%s updated=%s",
            window_start.date(),
            window_end.date(),
            results["updated"],
        )
    return results


__all__ = ["run_turn_personal_model_update"]
