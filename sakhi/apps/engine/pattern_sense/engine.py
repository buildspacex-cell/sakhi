from __future__ import annotations

import datetime as dt
import math
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _corr(xs: List[float], ys: List[float]) -> float:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)) or 1.0
    return num / den


def _group_by_weekday(sentiments: List[Tuple[dt.datetime, float]]) -> Dict[str, float]:
    buckets: Dict[int, List[float]] = {}
    for ts, val in sentiments:
        buckets.setdefault(ts.weekday(), []).append(val)
    return {str(k): _avg(v) for k, v in buckets.items()}


def _group_by_hour(sentiments: List[Tuple[dt.datetime, float]]) -> Dict[str, float]:
    buckets: Dict[int, List[float]] = {}
    for ts, val in sentiments:
        buckets.setdefault(ts.hour, []).append(val)
    return {str(k): _avg(v) for k, v in buckets.items()}


async def compute_patterns(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    # episodic sentiments and tags
    epi_rows = await q(
        """
        SELECT updated_at, triage, context_tags
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 200
        """,
        person_id,
    )
    sentiments: List[Tuple[dt.datetime, float]] = []
    wellness_tags: List[Dict[str, Any]] = []
    for row in epi_rows or []:
        ts_raw = row.get("updated_at") or row.get("time_scope") or dt.datetime.utcnow().isoformat()
        ts = dt.datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")) if isinstance(ts_raw, str) else dt.datetime.utcnow()
        triage = row.get("triage") or {}
        mood = (triage.get("slots") or {}).get("mood_affect") if isinstance(triage, dict) else {}
        sentiments.append((ts, float((mood or {}).get("score") or 0)))
        for tag in row.get("context_tags") or []:
            if isinstance(tag, dict) and "wellness_tags" in tag:
                wellness_tags.append(tag["wellness_tags"])

    # intents
    intents = await q(
        "SELECT intent_name, strength, emotional_alignment FROM intent_evolution WHERE person_id = $1",
        person_id,
    ) or []

    # tasks completions
    tasks = await q(
        """
        SELECT status, energy_cost
        FROM tasks
        WHERE user_id = $1
        """,
        person_id,
    ) or []

    # rhythm state (latest)
    rhythm_row = await q(
        "SELECT rhythm_state FROM personal_os_brain WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    rhythm_state = rhythm_row.get("rhythm_state") or {}

    # journal frequency not stored; infer from episodic count over 7d
    now = dt.datetime.utcnow()
    freq_7d = len([ts for ts, _ in sentiments if (now - ts).days <= 7])

    emotional_patterns = {
        "weekday": _group_by_weekday(sentiments),
        "hour": _group_by_hour(sentiments),
        "volatility_windows": 0.0,
        "negative_runs": 0,
    }
    if sentiments:
        values = [v for _, v in sentiments]
        mean = _avg(values)
        emotional_patterns["volatility_windows"] = math.sqrt(_avg([(v - mean) ** 2 for v in values]))
        # negative drift sequences
        run = 0
        max_run = 0
        for val in values:
            if val < 0:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        emotional_patterns["negative_runs"] = max_run

    # intent couplings
    intent_couplings = []
    sentiment_series = [v for _, v in sentiments]
    for intent in intents:
        strength = float(intent.get("strength") or 0)
        emo_align = float(intent.get("emotional_alignment") or 0)
        corr_sent = _corr([strength] * len(sentiment_series), sentiment_series) if sentiment_series else 0.0
        intent_couplings.append(
            {
                "intent": intent.get("intent_name"),
                "intent_strength": strength,
                "emotional_alignment": emo_align,
                "intent_sentiment_corr": corr_sent,
            }
        )

    # task effects (simple proxy: completed vs sentiment mean)
    completed = [t for t in tasks if (t.get("status") or "").lower() == "done"]
    task_effects = {"completed_count": len(completed), "energy_avg": _avg([t.get("energy_cost") or 0 for t in completed])}

    # wellness correlations
    body_vals = [w.get("body", 0) for w in wellness_tags]
    mind_vals = [w.get("mind", 0) for w in wellness_tags]
    emotion_vals = [w.get("emotion", 0.0) for w in wellness_tags]
    wellness_corr = {
        "body_emotion_corr": _corr(body_vals, emotion_vals) if len(body_vals) == len(emotion_vals) and body_vals else 0.0,
        "mind_emotion_corr": _corr(mind_vals, emotion_vals) if len(mind_vals) == len(emotion_vals) and mind_vals else 0.0,
    }

    rhythm_signatures = rhythm_state
    seasonality = {"entries_last_7d": freq_7d}

    return {
        "emotional_patterns": emotional_patterns,
        "intent_couplings": intent_couplings,
        "task_effects": task_effects,
        "wellness_correlations": wellness_corr,
        "rhythm_signatures": rhythm_signatures,
        "seasonality": seasonality,
    }


__all__ = ["compute_patterns"]
