from __future__ import annotations

import logging
import os
from collections import Counter, defaultdict
import json
import re
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q

logger = logging.getLogger(__name__)

WINDOW_DAYS = int(os.getenv("WEEKLY_SIGNALS_WINDOW_DAYS", "7") or "7")
TARGET_WEEK_START_ENV = os.getenv("WEEKLY_SIGNALS_TARGET_WEEK_START")


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


def _analyze_journals(journal_rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    weekly_salience = {"present": False, "items": []}
    weekly_contrast = {"positive_glimpses": [], "count": 0}
    weekly_body_notes = {"discomfort_hints": [], "count": 0}
    dimension_states: Dict[str, str] = {dim: "flat" for dim in ("body", "mind", "emotion", "energy", "work")}

    # Anchor eligibility (for weekly reflections) is scoped to these journal rows:
    # - Anchors must come from journal_entries.content that triggered:
    #   * body discomfort detection
    #   * work overload / overextension salience
    #   * emotional salience (guilt, pride, happiness)
    # - Only rows contributing to weekly_salience, weekly_contrast, or weekly_body_notes are candidates.
    # - Do NOT fetch anchors from memory_episodic; journals are the source of truth here.
    anchor_candidates: Dict[str, List[Dict[str, Any]]] = {
        "body_discomfort": [],
        "work_overload": [],
        "positive_emotion": [],
        "negative_emotion": [],
    }

    def _append_anchor(key: str, row: Dict[str, Any]) -> None:
        entry = {
            "content": row.get("content") or "",
            "created_at": None,
        }
        ts = row.get("created_at")
        if hasattr(ts, "isoformat"):
            entry["created_at"] = ts.isoformat()
        elif isinstance(ts, str):
            entry["created_at"] = ts
        anchor_candidates.setdefault(key, []).append(entry)

    def build_moment_hint(text: str, signal_type: str) -> str:
        """Deterministic, time-neutral moment hint (8-20 words, no advice/causes)."""
        base_map = {
            "body_discomfort": "a moment when your body felt off",
            "work_overload": "a time when work felt heavy",
            "positive_emotion": "a time that felt uplifting",
            "negative_emotion": "a moment when emotions felt heavier",
        }
        base = base_map.get(signal_type, "a moment in the week")
        cleaned = re.sub(r"[^A-Za-z0-9\\s]", " ", text or "").strip()
        words = [w.lower() for w in cleaned.split() if w.strip()]
        tail = words[:12]  # limit tail to keep under 20 words overall
        combined = (base.split() + tail)[:20]
        if len(combined) < 8:
            combined += ["in", "the", "week"]
        return " ".join(combined[:20]).strip()

    def _snippet_hint(raw_text: str, keyword: str, max_words: int = 5) -> str:
        words = raw_text.split()
        lower_words = [w.lower() for w in words]
        idx = None
        for i, w in enumerate(lower_words):
            if keyword and keyword in w:
                idx = i
                break
        if idx is None:
            return " ".join(words[:max_words]) if words else ""
        start = max(idx - 1, 0)
        end = min(len(words), start + max_words)
        return " ".join(words[start:end])

    work_pressure_hits = 0
    overextension_hits = 0
    positive_emotion_seen = False
    negative_emotion_seen = False
    discomfort_seen = False
    positive_body_seen = False
    exhaustion_seen = False
    energizing_seen = False

    work_pressure_terms = [
        "work overload",
        "overloaded",
        "too much work",
        "pressure",
        "stressed about work",
        "blocked",
        "blockage",
        "frustrated",
        "frustration",
        "stuck at work",
        "deadline pressure",
        "workload",
        "pushing beyond reason",
        "pushed beyond reason",
    ]
    overextension_terms = [
        "pushing through",
        "pushed through",
        "pushing myself",
        "kept going",
        "exhausted",
        "exhaustion",
        "tired but still",
        "pushed through work",
        "push through work",
        "pushing beyond reason",
    ]
    guilt_terms = ["guilt", "guilty"]
    rest_terms = ["rest", "resting", "break", "nap"]
    positive_body_terms = [
        "felt great",
        "felt strong",
        "amazing workout",
        "good workout",
        "great workout",
        "run",
        "walk",
        "yoga",
        "pilates",
        "exercise",
        "energized",
        "badminton",
        "family badminton",
        "play",
        "played with family",
        "walked with",
    ]
    positive_emotion_terms = ["happy", "joy", "joyful", "excited", "grateful", "proud", "calm", "relieved", "family time", "time with family", "with family", "family"]
    negative_emotion_terms = [
        "sad",
        "angry",
        "anxious",
        "upset",
        "frustrated",
        "stressed",
        "lonely",
        "guilty",
        "guilt",
    ]
    discomfort_terms = ["pain", "sore", "sick", "headache", "fatigue", "tired", "aching", "nausea", "hurting", "bloat", "bloated", "bloating"]
    exhaustion_terms = ["exhausted", "exhaustion", "burned out", "burnt out", "worn out", "drained"]
    energizing_terms = ["energized", "recharged", "rested", "good sleep", "slept well", "refreshing", "walk", "run", "workout", "exercise"]

    for row in journal_rows or []:
        raw_text = row.get("content") or ""
        text = raw_text.lower()
        if not text.strip():
            continue

        has_work_pressure = any(term in text for term in work_pressure_terms)
        work_pressure_hits += 1 if has_work_pressure else 0

        has_overextension = any(term in text for term in overextension_terms)
        if any(gt in text for gt in guilt_terms) and any(rt in text for rt in rest_terms):
            has_overextension = True
        overextension_hits += 1 if has_overextension else 0

        has_positive_body = any(term in text for term in positive_body_terms)
        has_positive_emotion = any(term in text for term in positive_emotion_terms)
        has_negative_emotion = any(term in text for term in negative_emotion_terms)
        has_discomfort = any(term in text for term in discomfort_terms)
        has_exhaustion = any(term in text for term in exhaustion_terms)
        has_energizing = any(term in text for term in energizing_terms)

        if has_work_pressure or has_overextension:
            _append_anchor("work_overload", row)

        if has_positive_body:
            matched = next((term for term in positive_body_terms if term in text), "")
            hint = _snippet_hint(raw_text, matched)
            weekly_contrast["positive_glimpses"].append({"type": "positive_body", "hint": hint})
            weekly_contrast["count"] += 1
            positive_body_seen = True
        if has_positive_emotion:
            matched = next((term for term in positive_emotion_terms if term in text), "")
            hint = _snippet_hint(raw_text, matched)
            weekly_contrast["positive_glimpses"].append({"type": "positive_emotion", "hint": hint})
            weekly_contrast["count"] += 1
            positive_emotion_seen = True
            _append_anchor("positive_emotion", row)
        if has_negative_emotion:
            negative_emotion_seen = True
            _append_anchor("negative_emotion", row)
        if has_discomfort:
            matched = next((term for term in discomfort_terms if term in text), "")
            hint = _snippet_hint(raw_text, matched, max_words=3) if matched else " ".join(raw_text.split()[:3])
            weekly_body_notes["discomfort_hints"].append({"type": "physical_discomfort", "hint": hint})
            discomfort_seen = True
            _append_anchor("body_discomfort", row)
        if has_exhaustion:
            exhaustion_seen = True
        if has_energizing:
            energizing_seen = True

    salience_items = []
    if work_pressure_hits >= 2:
        salience_items.append({"key": "work_pressure", "weight": 0.6})
    if overextension_hits >= 2:
        salience_items.append({"key": "overextension", "weight": 0.4})
    if salience_items:
        weekly_salience["present"] = True
        weekly_salience["items"] = salience_items

    if discomfort_seen or positive_body_seen:
        dimension_states["body"] = "mixed"
    if weekly_salience["present"] and any(item.get("key") == "work_pressure" for item in salience_items):
        dimension_states["work"] = "salient"
    if positive_emotion_seen and negative_emotion_seen:
        dimension_states["emotion"] = "mixed"
    if exhaustion_seen and energizing_seen:
        dimension_states["energy"] = "mixed"

    if weekly_body_notes["discomfort_hints"]:
        weekly_body_notes["count"] = len(weekly_body_notes["discomfort_hints"])

    # Select up to one anchor per signal type from candidates (journal-based only).
    moment_anchors: List[Dict[str, Any]] = []
    for key in ("body_discomfort", "work_overload", "positive_emotion", "negative_emotion"):
        candidates = anchor_candidates.get(key) or []
        if not candidates:
            continue
        chosen = candidates[0]  # deterministic: first contributing row
        hint = build_moment_hint(chosen.get("content") or "", key)
        moment_anchors.append(
            {
                "type": key,
                "hint": hint,
            }
        )
    if moment_anchors:
        weekly_contrast["moment_anchors"] = moment_anchors

    # Per-dimension anchors (journal only, no ids/dates, max 1)
    for anchor in moment_anchors:
        if anchor["type"] == "body_discomfort":
            weekly_body_notes.setdefault("anchors", [])
            if not weekly_body_notes["anchors"]:
                weekly_body_notes["anchors"].append({"source": "journal", "moment_hint": anchor["hint"]})
        if anchor["type"] == "work_overload":
            weekly_salience.setdefault("anchors", [])
            if not weekly_salience["anchors"]:
                weekly_salience["anchors"].append({"source": "journal", "moment_hint": anchor["hint"]})

    # Surface anchor candidates alongside signals (journal-based only).
    weekly_contrast["_anchor_candidates"] = anchor_candidates

    return weekly_salience, weekly_contrast, dimension_states, weekly_body_notes


def _resolve_week_bounds() -> tuple[date, date]:
    if TARGET_WEEK_START_ENV:
        try:
            forced_start = date.fromisoformat(TARGET_WEEK_START_ENV)
            return forced_start, forced_start + timedelta(days=WINDOW_DAYS)
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    window_end = now.date()
    window_start = (now - timedelta(days=WINDOW_DAYS)).date()
    return window_start, window_end


async def run_weekly_signals_worker(person_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Weekly signals aggregation (language-free). Upserts memory_weekly_signals.
    """
    window_start, window_end = _resolve_week_bounds()

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
        journal_rows = await q(
            """
            SELECT content
            FROM journal_entries
            WHERE user_id = $1
              AND created_at >= $2
              AND created_at < $3
            """,
            pid,
            window_start,
            window_end,
        )
        weekly_salience, weekly_contrast, dimension_states, weekly_body_notes = _analyze_journals(journal_rows or [])

        episodic_json = json.dumps(episodic_stats)
        theme_json = json.dumps(theme_stats)
        contrast_json = json.dumps(contrast_stats)
        delta_json = json.dumps(delta_stats)
        weekly_salience_json = json.dumps(weekly_salience)
        weekly_contrast_json = json.dumps(weekly_contrast)
        dimension_states_json = json.dumps(dimension_states)
        weekly_body_notes_json = json.dumps(weekly_body_notes)

        await dbexec(
            """
            INSERT INTO memory_weekly_signals (person_id, week_start, week_end, episodic_stats, theme_stats, contrast_stats, delta_stats, confidence, weekly_salience, weekly_contrast, dimension_states, weekly_body_notes)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb)
            ON CONFLICT (person_id, week_start)
            DO UPDATE SET
                week_end = EXCLUDED.week_end,
                episodic_stats = EXCLUDED.episodic_stats,
                theme_stats = EXCLUDED.theme_stats,
                contrast_stats = EXCLUDED.contrast_stats,
                delta_stats = EXCLUDED.delta_stats,
                confidence = EXCLUDED.confidence,
                weekly_salience = EXCLUDED.weekly_salience,
                weekly_contrast = EXCLUDED.weekly_contrast,
                dimension_states = EXCLUDED.dimension_states,
                weekly_body_notes = EXCLUDED.weekly_body_notes,
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
            weekly_salience_json,
            weekly_contrast_json,
            dimension_states_json,
            weekly_body_notes_json,
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
