from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Mapping
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch

WINDOW_MINUTES = 60
SLOT_MINUTES = 15
LOGGER = logging.getLogger(__name__)


def _parse_slots(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


async def _load_rhythm(person_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    try:
        state_row = await dbfetch(
            """
            SELECT body_energy, mind_focus, emotion_tone, fatigue_level, stress_level, next_peak, next_lull, chronotype
            FROM rhythm_state
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        state_row = None

    try:
        curve_row = await dbfetch(
            """
            SELECT slots, day_scope
            FROM rhythm_daily_curve
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
    except Exception:
        curve_row = None

    slots = _parse_slots((curve_row or {}).get("slots"))
    return state_row or {}, slots


def _window_average(slots: List[Dict[str, Any]], start_idx: int, length: int) -> float:
    sample = slots[start_idx : start_idx + length]
    if not sample:
        return 0.0
    energies = []
    for s in sample:
        try:
            energies.append(float(s.get("energy", 0)))
        except Exception:
            continue
    return sum(energies) / max(1, len(energies))


def _pick_windows(slots: List[Dict[str, Any]], count: int = 3, window_minutes: int = WINDOW_MINUTES) -> List[Dict[str, Any]]:
    if not slots:
        return []
    slots_per_window = max(1, window_minutes // SLOT_MINUTES)
    best: List[Tuple[float, int]] = []  # (avg_energy, start_index)
    for i in range(0, len(slots) - slots_per_window + 1):
        avg = _window_average(slots, i, slots_per_window)
        best.append((avg, i))
    best.sort(key=lambda tup: tup[0], reverse=True)

    selected: List[Dict[str, Any]] = []
    used_indices: set[int] = set()
    for avg, start_idx in best:
        if len(selected) >= count:
            break
        overlap = any(idx in used_indices for idx in range(start_idx, start_idx + slots_per_window))
        if overlap:
            continue
        start_time = slots[start_idx].get("time")
        end_slot = slots[min(len(slots) - 1, start_idx + slots_per_window - 1)]
        end_time = end_slot.get("time")
        selected.append(
            {
                "window": f"{start_time}-{end_time}",
                "energy": round(avg, 2),
                "idx": start_idx,
            }
        )
        used_indices.update(range(start_idx, start_idx + slots_per_window))
    return selected


def _find_lull(slots: List[Dict[str, Any]], window_minutes: int = WINDOW_MINUTES) -> Dict[str, Any] | None:
    if not slots:
        return None
    slots_per_window = max(1, window_minutes // SLOT_MINUTES)
    best = None
    for i in range(0, len(slots) - slots_per_window + 1):
        avg = _window_average(slots, i, slots_per_window)
        if best is None or avg < best[0]:
            best = (avg, i)
    if best is None:
        return None
    avg, start_idx = best
    start_time = slots[start_idx].get("time")
    end_slot = slots[min(len(slots) - 1, start_idx + slots_per_window - 1)]
    end_time = end_slot.get("time")
    return {"window": f"{start_time}-{end_time}", "energy": round(avg, 2), "idx": start_idx}


def _task_energy_hint(task: Mapping[str, Any]) -> float:
    energy = task.get("energy") or task.get("energy_hint")
    if isinstance(energy, str):
        lookup = {"low": 0.3, "medium": 0.6, "med": 0.6, "high": 0.8}
        return lookup.get(energy.lower(), 0.6)
    try:
        return float(energy)
    except Exception:
        return 0.6


def _assign_tasks_to_windows(tasks: List[Mapping[str, Any]], peaks: List[Dict[str, Any]], lull: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not tasks:
        return []
    assignments: List[Dict[str, Any]] = []
    sorted_peaks = sorted(peaks, key=lambda p: p.get("energy", 0.0), reverse=True) if peaks else []
    for idx, task in enumerate(tasks):
        label = task.get("label") or task.get("title") or "Task"
        energy_hint = _task_energy_hint(task)
        target_window = None
        if energy_hint >= 0.7 and sorted_peaks:
            target_window = sorted_peaks[idx % len(sorted_peaks)]
        elif energy_hint <= 0.4 and lull:
            target_window = lull
        elif sorted_peaks:
            target_window = sorted_peaks[(idx + 1) % len(sorted_peaks)]
        assignment = {
            "task_label": label,
            "window": target_window.get("window") if target_window else None,
            "energy_fit": energy_hint,
            "suggested_energy": target_window.get("energy") if target_window else None,
        }
        assignments.append(assignment)
    return assignments


async def compute_rhythm_planner_alignment(person_id: str, plan_graph: Dict[str, Any]) -> None:
    state, slots = await _load_rhythm(person_id)
    peaks = _pick_windows(slots, count=3)
    lull = _find_lull(slots)

    # Fallback if no curve slots present: derive a single window around next_peak/next_lull
    if not peaks and state.get("next_peak"):
        peaks = [{"window": f"{state['next_peak']} (approx)", "energy": state.get("body_energy", 0.6), "idx": 0}]
    if not lull and state.get("next_lull"):
        lull = {"window": f"{state['next_lull']} (approx)", "energy": state.get("body_energy", 0.4), "idx": 0}

    tasks = plan_graph.get("tasks") or []
    flow_assignments = _assign_tasks_to_windows(tasks, peaks, lull)

    recommendations = {
        "peaks": peaks,
        "lull": lull,
        "assignments": flow_assignments,
        "emotion_tone": state.get("emotion_tone"),
        "chronotype": state.get("chronotype"),
        "generated_at": datetime.utcnow().isoformat(),
    }

    LOGGER.info(
        "[RhythmFusion] person=%s peaks=%s lull=%s tasks=%s",
        person_id,
        len(peaks),
        1 if lull else 0,
        len(tasks),
    )

    # today horizon
    await dbexec(
        """
        INSERT INTO rhythm_planner_alignment (person_id, horizon, recommendations, generated_at)
        VALUES ($1, 'today', $2::jsonb, NOW())
        ON CONFLICT (person_id, horizon) DO UPDATE
        SET recommendations = EXCLUDED.recommendations,
            generated_at = NOW()
        """,
        person_id,
        json.dumps(recommendations, ensure_ascii=False),
    )

    # week horizon (reuse but mark scope)
    week_payload = dict(recommendations)
    week_payload["scope"] = "week"
    await dbexec(
        """
        INSERT INTO rhythm_planner_alignment (person_id, horizon, recommendations, generated_at)
        VALUES ($1, 'week', $2::jsonb, NOW())
        ON CONFLICT (person_id, horizon) DO UPDATE
        SET recommendations = EXCLUDED.recommendations,
            generated_at = NOW()
        """,
        person_id,
        json.dumps(week_payload, ensure_ascii=False),
    )


__all__ = ["compute_rhythm_planner_alignment"]
