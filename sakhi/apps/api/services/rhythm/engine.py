from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.core.event_logger import log_event
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)

MORNING_TEMPLATE = [
    0.55,
    0.6,
    0.65,
    0.75,
    0.8,
    0.92,
    0.95,
    0.9,
    0.8,
    0.7,
    0.65,
    0.6,
    0.58,
    0.55,
    0.55,
    0.58,
    0.62,
    0.68,
    0.7,
    0.65,
    0.6,
    0.55,
    0.5,
    0.48,
]

EVENING_TEMPLATE = [
    0.35,
    0.35,
    0.4,
    0.45,
    0.5,
    0.55,
    0.6,
    0.68,
    0.7,
    0.72,
    0.78,
    0.82,
    0.85,
    0.88,
    0.92,
    0.95,
    0.9,
    0.85,
    0.78,
    0.7,
    0.65,
    0.55,
    0.45,
    0.4,
]

INTERMEDIATE_TEMPLATE = [
    0.45,
    0.5,
    0.55,
    0.62,
    0.7,
    0.78,
    0.85,
    0.9,
    0.92,
    0.9,
    0.85,
    0.8,
    0.72,
    0.68,
    0.64,
    0.6,
    0.58,
    0.6,
    0.62,
    0.6,
    0.55,
    0.5,
    0.48,
    0.46,
]

TEMPLATES = {
    "morning": MORNING_TEMPLATE,
    "evening": EVENING_TEMPLATE,
    "intermediate": INTERMEDIATE_TEMPLATE,
}


async def run_rhythm_engine(person_id: str, text: str | None = None) -> Dict[str, Any]:
    """Compute rhythm state -> write tables -> emit planner alignment."""

    settings = get_settings()
    if not person_id:
        raise ValueError("person_id required")

    breath_rows = await q(
        """
        SELECT calm_score, avg_breath_rate, created_at
        FROM breath_sessions
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 24
        """,
        person_id,
    )
    journal_rows = await q(
        """
        SELECT created_at, COALESCE((facets_v2->>'sentiment')::float, 0.0) AS sentiment
        FROM journal_entries
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 40
        """,
        person_id,
    )

    chronotype = _infer_chronotype(journal_rows)
    fatigue = _compute_fatigue(breath_rows, journal_rows)
    stress = _compute_stress(breath_rows, journal_rows)
    emotion_tone = _detect_emotion_tone(journal_rows)

    slots = _build_daily_curve(chronotype["chronotype"], fatigue, stress)
    next_peak, next_lull = _find_inflection_points(slots)
    body_energy = round(sum(slot["energy"] for slot in slots) / len(slots), 3)
    mind_focus = round(max(0.05, min(1.0, body_energy - (stress * 0.25))), 3)

    await _upsert_chronotype(person_id, chronotype)
    await _store_daily_curve(person_id, slots)

    next_peak_str = next_peak.isoformat() if next_peak else None
    next_lull_str = next_lull.isoformat() if next_lull else None

    state_payload = {
        "body_energy": body_energy,
        "mind_focus": mind_focus,
        "emotion_tone": emotion_tone,
        "fatigue_level": fatigue,
        "stress_level": stress,
        "next_peak": next_peak_str,
        "next_lull": next_lull_str,
        "payload": {
            "recent_breath": [
                {
                    "calm_score": row.get("calm_score"),
                    "avg_breath_rate": row.get("avg_breath_rate"),
                    "created_at": row.get("created_at").isoformat()
                    if row.get("created_at")
                    else None,
                }
                for row in breath_rows[:5]
            ],
            "recent_sentiment": [
                {"sentiment": row.get("sentiment"), "created_at": row.get("created_at").isoformat()}
                for row in journal_rows[:5]
            ],
            "input_text": text or "",
        },
    }
    await _upsert_rhythm_state(person_id, state_payload)

    alignment = _build_planner_alignment(slots, stress, fatigue)
    if settings.enable_rhythm_workers:
        await _store_alignment(person_id, alignment)

    await _record_rhythm_event(person_id, state_payload, alignment)

    return {"state": state_payload, "chronotype": chronotype, "alignment": alignment}


def _infer_chronotype(journal_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not journal_rows:
        return {"chronotype": "intermediate", "score": 0.5, "evidence": {}}

    buckets = Counter()
    for row in journal_rows:
        created_at = row.get("created_at")
        if isinstance(created_at, datetime):
            hour = created_at.hour
            if 5 <= hour < 11:
                buckets["morning"] += 1
            elif 11 <= hour < 18:
                buckets["intermediate"] += 1
            else:
                buckets["evening"] += 1

    chronotype, count = buckets.most_common(1)[0] if buckets else ("intermediate", 0)
    total = sum(buckets.values()) or 1
    score = round(count / total, 2)
    return {"chronotype": chronotype, "score": score, "evidence": buckets}


def _compute_fatigue(
    breath_rows: List[Dict[str, Any]], journal_rows: List[Dict[str, Any]]
) -> float:
    calm_scores = [float(row.get("calm_score") or 0.5) for row in breath_rows]
    calm_avg = sum(calm_scores) / len(calm_scores) if calm_scores else 0.5
    negative_sentiment_ratio = 0.0
    if journal_rows:
        negatives = sum(1 for row in journal_rows if float(row.get("sentiment") or 0.0) < -0.2)
        negative_sentiment_ratio = negatives / len(journal_rows)
    fatigue = max(0.0, min(1.0, (0.6 - calm_avg) + negative_sentiment_ratio * 0.6))
    return round(fatigue, 3)


def _compute_stress(
    breath_rows: List[Dict[str, Any]], journal_rows: List[Dict[str, Any]]
) -> float:
    volatility = 0.0
    if len(breath_rows) >= 2:
        diffs = [
            abs(float(a.get("calm_score") or 0.5) - float(b.get("calm_score") or 0.5))
            for a, b in zip(breath_rows[:-1], breath_rows[1:])
        ]
        volatility = sum(diffs) / len(diffs)
    emotional_spikes = sum(
        1 for row in journal_rows if abs(float(row.get("sentiment") or 0.0)) > 0.6
    )
    stress = min(1.0, 0.5 * volatility + 0.5 * (emotional_spikes / max(len(journal_rows), 1)))
    return round(stress, 3)


def _detect_emotion_tone(journal_rows: List[Dict[str, Any]]) -> str:
    if not journal_rows:
        return "neutral"
    avg = sum(float(row.get("sentiment") or 0.0) for row in journal_rows) / len(journal_rows)
    if avg > 0.25:
        return "uplifted"
    if avg < -0.25:
        return "heavy"
    return "neutral"


def _build_daily_curve(chronotype: str, fatigue: float, stress: float) -> List[Dict[str, Any]]:
    template = TEMPLATES.get(chronotype, INTERMEDIATE_TEMPLATE)
    slots: List[Dict[str, Any]] = []
    dampener = max(0.6, 1.0 - fatigue * 0.3 - stress * 0.2)
    for hour, base_energy in enumerate(template):
        adjusted = max(0.05, min(1.0, base_energy * dampener))
        for quarter in range(4):
            minute = quarter * 15
            label = f"{hour:02d}:{minute:02d}"
            slots.append({"time": label, "energy": round(adjusted, 3)})
    return slots


def _find_inflection_points(slots: List[Dict[str, Any]]) -> Tuple[datetime | None, datetime | None]:
    if not slots:
        return (None, None)
    now = datetime.now(timezone.utc)
    highest = max(slots, key=lambda slot: slot["energy"])
    lowest = min(slots, key=lambda slot: slot["energy"])
    peak = now.replace(hour=int(highest["time"][:2]), minute=int(highest["time"][3:]), second=0, microsecond=0)
    lull = now.replace(hour=int(lowest["time"][:2]), minute=int(lowest["time"][3:]), second=0, microsecond=0)
    if peak < now:
        peak += timedelta(days=1)
    if lull < now:
        lull += timedelta(days=1)
    return (peak, lull)


def _build_planner_alignment(slots: List[Dict[str, Any]], stress: float, fatigue: float) -> Dict[str, Any]:
    high_windows: List[Dict[str, Any]] = []
    window: List[str] = []
    for slot in slots:
        if slot["energy"] >= 0.75:
            window.append(slot["time"])
        else:
            if len(window) >= 3:
                high_windows.append({"start": window[0], "end": window[-1]})
            window = []
    if len(window) >= 3:
        high_windows.append({"start": window[0], "end": window[-1]})

    focus_windows = [
        {
            "window": f"{win['start']}-{win['end']}",
            "energy": "high",
            "fit": ["Deep Work", "Planning"],
        }
        for win in high_windows[:2]
    ]

    recovery_windows = [
        {
            "window": f"{slot['time']}-{(datetime.strptime(slot['time'], '%H:%M') + timedelta(minutes=30)).strftime('%H:%M')}",
            "energy": "low",
            "fit": ["Rest", "Light Review"],
        }
        for slot in slots[::16]
        if slot["energy"] < 0.4
    ][:2]

    return {
        "today": focus_windows + recovery_windows,
        "week": [
            {"day": "Mon-Thu", "focus": "Prioritize high-energy mornings"},
            {"day": "Fri", "focus": "Leave afternoons for review"},
        ],
        "stress": stress,
        "fatigue": fatigue,
    }


async def _upsert_chronotype(person_id: str, chronotype: Dict[str, Any]) -> None:
    await dbexec(
        """
        INSERT INTO rhythm_chronotype (person_id, chronotype, score, evidence, updated_at)
        VALUES ($1, $2, $3, $4::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE
        SET chronotype = EXCLUDED.chronotype,
            score = EXCLUDED.score,
            evidence = EXCLUDED.evidence,
            updated_at = NOW()
        """,
        person_id,
        chronotype["chronotype"],
        chronotype["score"],
        json.dumps(chronotype.get("evidence"), ensure_ascii=False),
    )


async def _store_daily_curve(person_id: str, slots: List[Dict[str, Any]]) -> None:
    await dbexec(
        """
        INSERT INTO rhythm_daily_curve (person_id, day_scope, slots, confidence, source, created_at)
        VALUES ($1, CURRENT_DATE, $2::jsonb, 0.7, 'worker', NOW())
        ON CONFLICT (person_id, day_scope) DO UPDATE
        SET slots = EXCLUDED.slots,
            confidence = EXCLUDED.confidence,
            source = EXCLUDED.source,
            created_at = NOW()
        """,
        person_id,
        json.dumps(slots, ensure_ascii=False),
    )


async def _upsert_rhythm_state(person_id: str, payload: Dict[str, Any]) -> None:
    await dbexec(
        """
        INSERT INTO rhythm_state (
            person_id,
            body_energy,
            mind_focus,
            emotion_tone,
            fatigue_level,
            stress_level,
            next_peak,
            next_lull,
            payload,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE SET
            body_energy = EXCLUDED.body_energy,
            mind_focus = EXCLUDED.mind_focus,
            emotion_tone = EXCLUDED.emotion_tone,
            fatigue_level = EXCLUDED.fatigue_level,
            stress_level = EXCLUDED.stress_level,
            next_peak = EXCLUDED.next_peak,
            next_lull = EXCLUDED.next_lull,
            payload = EXCLUDED.payload,
            updated_at = NOW()
        """,
        person_id,
        payload["body_energy"],
        payload["mind_focus"],
        payload["emotion_tone"],
        payload["fatigue_level"],
        payload["stress_level"],
        _parse_timestamp(payload.get("next_peak")),
        _parse_timestamp(payload.get("next_lull")),
        json.dumps(payload.get("payload") or {}, ensure_ascii=False),
    )


async def _store_alignment(person_id: str, alignment: Dict[str, Any]) -> None:
    today_rec = alignment.get("today") or []
    week_rec = alignment.get("week") or []
    await dbexec(
        """
        INSERT INTO rhythm_planner_alignment (person_id, horizon, recommendations, generated_at)
        VALUES ($1, 'today', $2::jsonb, NOW())
        ON CONFLICT (person_id, horizon) DO UPDATE
        SET recommendations = EXCLUDED.recommendations,
            generated_at = NOW()
        """,
        person_id,
        json.dumps(today_rec, ensure_ascii=False),
    )
    await dbexec(
        """
        INSERT INTO rhythm_planner_alignment (person_id, horizon, recommendations, generated_at)
        VALUES ($1, 'week', $2::jsonb, NOW())
        ON CONFLICT (person_id, horizon) DO UPDATE
        SET recommendations = EXCLUDED.recommendations,
            generated_at = NOW()
        """,
        person_id,
        json.dumps(week_rec, ensure_ascii=False),
    )


async def _record_rhythm_event(
    person_id: str, state: Dict[str, Any], alignment: Dict[str, Any]
) -> None:
    await dbexec(
        """
        INSERT INTO rhythm_events (person_id, event_ts, kind, payload, created_at)
        VALUES ($1, NOW(), 'inference', $2::jsonb, NOW())
        """,
        person_id,
        json.dumps({"state": state, "alignment": alignment}, ensure_ascii=False),
    )
    await log_event(
        person_id,
        "rhythm",
        "state_refresh",
        {
            "body_energy": state["body_energy"],
            "fatigue": state["fatigue_level"],
            "stress": state["stress_level"],
        },
    )


__all__ = ["run_rhythm_engine"]


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
