from __future__ import annotations

import os
import logging
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec

LOGGER = logging.getLogger(__name__)

RHYTHM_ROLLUP_WINDOW_DAYS = int(os.getenv("RHYTHM_ROLLUP_WINDOW_DAYS", "7") or "7")
TIME_BUCKETS = {
    "early_morning": (5, 8),
    "morning": (8, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 24),
}
CHANNELS = {"body", "mind", "emotion", "energy"}


def _bucket_for_time(label: str) -> str | None:
    try:
        hour = int(label.split(":")[0])
    except Exception:
        return None
    for name, (start, end) in TIME_BUCKETS.items():
        if start <= hour < end:
            return name
    return None


def _slope(values: List[float]) -> str:
    if len(values) < 2:
        return "unknown"
    first = mean(values[: max(1, len(values) // 3)])
    last = mean(values[-max(1, len(values) // 3) :])
    delta = last - first
    if delta > 0.05:
        return "up"
    if delta < -0.05:
        return "down"
    return "stable"


def _volatility(values: List[float]) -> str:
    if len(values) < 2:
        return "unknown"
    std = pstdev(values)
    if std >= 0.15:
        return "high"
    if std >= 0.08:
        return "medium"
    return "low"


def _peak_dip(bucket_means: Dict[str, float]) -> Tuple[List[str], List[str]]:
    if not bucket_means:
        return [], []
    values = list(bucket_means.values())
    max_v, min_v = max(values), min(values)
    if max_v == min_v:
        return [], []
    peaks = [b for b, v in bucket_means.items() if v >= max_v - 0.02]
    dips = [b for b, v in bucket_means.items() if v <= min_v + 0.02]
    return peaks, dips


def _recovery_latency(slope_value: str, vol: str) -> str:
    if slope_value == "up" and vol in {"low", "medium"}:
        return "short"
    if slope_value == "stable":
        return "medium"
    if slope_value == "down" or vol == "high":
        return "long"
    return "unknown"


def _confidence(num_samples: int, bucket_coverage: int, avg_conf: float) -> float:
    base = 0.1 + 0.02 * min(num_samples, 50) + 0.05 * min(bucket_coverage, len(TIME_BUCKETS))
    base += 0.2 * min(max(avg_conf, 0.0), 1.0)
    return max(0.0, min(1.0, base))


def _extract_event_values(events: List[Dict[str, Any]], channel: str) -> List[float]:
    values: List[float] = []
    for ev in events:
        payload = ev.get("payload") or {}
        state = payload.get("state") or payload
        if not isinstance(state, dict):
            continue
        if channel in {"body", "energy"} and isinstance(state.get("body_energy"), (int, float)):
            values.append(float(state["body_energy"]))
        elif channel == "mind" and isinstance(state.get("mind_focus"), (int, float)):
            values.append(float(state["mind_focus"]))
        elif channel == "emotion":
            if isinstance(state.get("stress_level"), (int, float)):
                # Higher stress → lower capacity
                values.append(max(0.0, min(1.0, 1.0 - float(state["stress_level"]))))
    return values


def compute_rollup(curves: List[Dict[str, Any]], events: List[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    if not curves and not events:
        return {ch: _unknown_payload() for ch in CHANNELS}

    # Aggregate slots into channel series and bucket means (slots are capacity estimates).
    slot_values: List[float] = []
    bucket_acc: Dict[str, List[float]] = defaultdict(list)
    avg_conf = 0.0
    for curve in curves:
        slots = curve.get("slots") or []
        avg_conf += float(curve.get("confidence") or 0.0)
        for slot in slots:
            try:
                energy = float(slot.get("energy"))
            except Exception:
                continue
            label = slot.get("time") or ""
            bucket = _bucket_for_time(label)
            slot_values.append(energy)
            if bucket:
                bucket_acc[bucket].append(energy)
    avg_conf = avg_conf / max(1, len(curves))
    bucket_means = {b: mean(vs) for b, vs in bucket_acc.items() if vs}

    rollup: Dict[str, Any] = {}
    for channel in CHANNELS:
        channel_values = list(slot_values)
        channel_values.extend(_extract_event_values(events, channel))

        if not channel_values:
            rollup[channel] = _unknown_payload()
            continue

        avg_level = sum(channel_values) / len(channel_values)
        slope_val = _slope(channel_values)
        vol = _volatility(channel_values)
        peaks, dips = _peak_dip(bucket_means)
        recovery = _recovery_latency(slope_val, vol)
        conf = _confidence(len(channel_values), len(bucket_means), avg_conf)

        rollup[channel] = {
            "avg_level": round(avg_level, 3),
            "slope": slope_val,
            "volatility": vol,
            "peak_windows": peaks or ["unknown"],
            "dip_windows": dips or ["unknown"],
            "recovery_latency": recovery,
            "confidence": round(conf, 3),
        }
    return rollup


def _unknown_payload() -> Dict[str, Any]:
    return {
        "avg_level": None,
        "slope": "unknown",
        "volatility": "unknown",
        "peak_windows": ["unknown"],
        "dip_windows": ["unknown"],
        "recovery_latency": "unknown",
        "confidence": 0.0,
    }


async def run_weekly_rhythm_rollup(person_id: str | None = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=RHYTHM_ROLLUP_WINDOW_DAYS)).date()
    week_start = window_start
    week_end = now.date()

    if person_id:
        persons = [{"person_id": person_id}]
    else:
        persons = await q("SELECT DISTINCT person_id FROM rhythm_daily_curve")

    results = {"processed": 0, "updated": 0}

    for row in persons:
        pid = row.get("person_id") or row.get("id")
        if not pid:
            continue

        curves = await q(
            """
            SELECT day_scope, slots, confidence
            FROM rhythm_daily_curve
            WHERE person_id = $1 AND day_scope >= $2
            ORDER BY day_scope ASC
            """,
            pid,
            window_start,
        )
        events = await q(
            """
            SELECT event_ts, payload
            FROM rhythm_events
            WHERE person_id = $1 AND event_ts >= $2
            ORDER BY event_ts ASC
            """,
            pid,
            datetime.combine(window_start, datetime.min.time(), tzinfo=timezone.utc),
        )

        rollup = compute_rollup(curves or [], events or [], now)
        rollup_json = json.dumps(rollup)
        await dbexec(
            """
            INSERT INTO rhythm_weekly_rollups (person_id, week_start, week_end, rollup, confidence, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, NOW())
            ON CONFLICT (person_id, week_start) DO UPDATE
            SET rollup = EXCLUDED.rollup,
                confidence = EXCLUDED.confidence,
                week_end = EXCLUDED.week_end,
                created_at = NOW()
            """,
            pid,
            week_start,
            week_end,
            rollup_json,
            _overall_confidence(rollup),
        )
        results["processed"] += 1
        results["updated"] += 1

    return results


def _overall_confidence(rollup: Dict[str, Any]) -> float:
    confidences = [payload.get("confidence") or 0.0 for payload in rollup.values() if isinstance(payload, dict)]
    return round(sum(confidences) / max(1, len(confidences)), 3)


__all__ = ["run_weekly_rhythm_rollup", "compute_rollup"]
