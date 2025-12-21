from __future__ import annotations

import logging
import os
from collections import Counter, defaultdict
import json
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q

logger = logging.getLogger(__name__)

WINDOW_DAYS = int(os.getenv("WEEKLY_SIGNALS_WINDOW_DAYS", "7") or "7")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalize_theme_weights(counter: Counter) -> List[Dict[str, Any]]:
    total = sum(counter.values()) or 1
    return [{"key": key, "weight": round(count / total, 3)} for key, count in counter.most_common(8)]


def _direction_from_delta(delta: float, eps: float = 0.05) -> str:
    if delta > eps:
        return "up"
    if delta < -eps:
        return "down"
    return "flat"


def _aggregate_episodic(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Counter]:
    days = set()
    theme_counter: Counter = Counter()
    for row in rows:
        ts = row.get("created_at")
        if ts:
            try:
                ts_dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
                days.add(ts_dt.date())
            except Exception:
                pass
        tags = row.get("context_tags") or []
        for tag in tags:
            if not isinstance(tag, dict):
                continue
            key = str(tag.get("key") or tag.get("theme") or tag.get("signal_key") or "").strip().lower()
            dim = str(tag.get("dimension") or "").strip().lower()
            if key:
                theme_counter[(dim, key)] += 1
    episodic_stats = {
        "episode_count": len(rows),
        "salient_count": 0,  # we do not compute salience without LLM; keep 0 for now
        "distinct_days": len(days),
    }
    # Flatten dim/key into single key for simplicity while staying non-narrative.
    flattened = Counter()
    for (dim, key), count in theme_counter.items():
        label = key if not dim else f"{dim}:{key}"
        flattened[label] += count
    return episodic_stats, flattened


def _contrast_from_rollups(rhythm_rollup: Dict[str, Any], planner_pressure: Dict[str, Any]) -> Dict[str, Any]:
    contrast: Dict[str, Any] = {}
    if rhythm_rollup:
        roll = rhythm_rollup.get("rollup") or {}
        if isinstance(roll, str):
            try:
                roll = json.loads(roll)
            except Exception:
                roll = {}
        levels = {}
        if isinstance(roll, dict):
            for dim, node in roll.items():
                try:
                    levels[dim] = float(node.get("avg_level") or 0.0)
                except Exception:
                    continue
        if levels:
            sorted_levels = sorted(levels.items(), key=lambda kv: kv[1])
            contrast["lowest_energy_dimension"] = sorted_levels[0][0]
            contrast["highest_energy_dimension"] = sorted_levels[-1][0]
    if planner_pressure:
        pressure = planner_pressure.get("pressure") or {}
        if isinstance(pressure, str):
            try:
                pressure = json.loads(pressure)
            except Exception:
                pressure = {}
        try:
            frag = float(pressure.get("fragmentation_score") or 0.0)
            contrast["work_fragmentation"] = frag
        except Exception:
            pass
        if pressure.get("overload_flag") is True:
            contrast["work_overload"] = True
    return contrast


def _deltas_from_longitudinal(state: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except Exception:
            state = {}
    deltas: Dict[str, Any] = {}
    for dim in ("body", "mind", "emotion", "energy", "work"):
        node = state.get(dim) or {}
        direction = str(node.get("direction") or "").lower()
        if direction in {"up", "down", "flat"}:
            deltas[dim] = direction
    return deltas


def _confidence_from_inputs(
    rhythm_conf: Optional[float],
    planner_conf: Optional[float],
    episodic_stats: Dict[str, Any],
) -> float:
    parts = []
    if rhythm_conf is not None:
        parts.append(_clamp(rhythm_conf))
    if planner_conf is not None:
        parts.append(_clamp(planner_conf))
    count = episodic_stats.get("episode_count", 0)
    if count:
        parts.append(_clamp(min(1.0, 0.1 + 0.02 * min(count, 20))))
    if not parts:
        return 0.1
    conf = sum(parts) / len(parts)
    if count < 3:
        conf *= 0.6
    return _clamp(conf)


async def run_weekly_signals_worker(person_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Weekly signals aggregation (language-free). Upserts memory_weekly_signals.
    """
    now = datetime.now(timezone.utc)
    window_end = now.date()
    window_start = (now - timedelta(days=WINDOW_DAYS)).date()

    persons = [person_id] if person_id else [row["person_id"] for row in await q("SELECT person_id FROM personal_model")]
    results = {"processed": 0, "updated": 0}

    for pid in persons:
        if not pid:
            continue
        # Episodic slice
        episodic_rows = await q(
            """
            SELECT created_at, context_tags
            FROM memory_episodic
            WHERE user_id = $1
              AND created_at >= $2
              AND created_at < $3
            """,
            pid,
            window_start,
            window_end,
        )
        episodic_stats, theme_counter = _aggregate_episodic(episodic_rows or [])
        theme_stats = _normalize_theme_weights(theme_counter)

        # Rhythm rollup (current week)
        rhythm_rollup = await q(
            """
            SELECT week_start, week_end, rollup, confidence
            FROM rhythm_weekly_rollups
            WHERE person_id = $1 AND week_start = $2
            """,
            pid,
            window_start,
            one=True,
        ) or {}

        # Planner pressure (current week)
        planner_pressure = await q(
            """
            SELECT week_start, week_end, pressure, confidence
            FROM planner_weekly_pressure
            WHERE person_id = $1 AND week_start = $2
            """,
            pid,
            window_start,
            one=True,
        ) or {}

        # Longitudinal deltas
        pm = await q(
            "SELECT longitudinal_state FROM personal_model WHERE person_id = $1",
            pid,
            one=True,
        ) or {}
        delta_stats = _deltas_from_longitudinal(pm.get("longitudinal_state") or {})

        contrast_stats = _contrast_from_rollups(rhythm_rollup, planner_pressure)
        confidence = _confidence_from_inputs(
            rhythm_rollup.get("confidence"),
            planner_pressure.get("confidence"),
            episodic_stats,
        )
        episodic_json = json.dumps(episodic_stats)
        theme_json = json.dumps(theme_stats)
        contrast_json = json.dumps(contrast_stats)
        delta_json = json.dumps(delta_stats)

        await dbexec(
            """
            INSERT INTO memory_weekly_signals (person_id, week_start, week_end, episodic_stats, theme_stats, contrast_stats, delta_stats, confidence)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8)
            ON CONFLICT (person_id, week_start)
            DO UPDATE SET
                week_end = EXCLUDED.week_end,
                episodic_stats = EXCLUDED.episodic_stats,
                theme_stats = EXCLUDED.theme_stats,
                contrast_stats = EXCLUDED.contrast_stats,
                delta_stats = EXCLUDED.delta_stats,
                confidence = EXCLUDED.confidence,
                created_at = NOW()
            """,
            pid,
            window_start,
            window_end,
            episodic_json,
            theme_json,
            contrast_json,
            delta_json,
            confidence,
        )
        results["processed"] += 1
        results["updated"] += 1

    logger.info(
        "weekly_signals_worker complete window=%s→%s updated=%s",
        window_start,
        window_end,
        results["updated"],
    )
    return results


__all__ = ["run_weekly_signals_worker"]
