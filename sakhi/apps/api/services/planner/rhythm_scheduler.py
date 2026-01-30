"""Rhythm-aligned task scheduler: matches tasks to optimal energy windows."""

from __future__ import annotations

import json
import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch

LOGGER = logging.getLogger(__name__)

# Energy thresholds for task scheduling
HIGH_ENERGY_THRESHOLD = 0.7
LOW_ENERGY_THRESHOLD = 0.4
BLOCK_CAPACITY_THRESHOLD = 0.3  # Don't schedule demanding tasks below this


async def schedule_tasks_by_rhythm(
    person_id: str,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Schedule tasks for a day by matching energy requirements to rhythm windows.

    Returns:
        Dict with scheduled tasks, energy forecast, and capacity assessment
    """
    if target_date is None:
        target_date = datetime.utcnow().date()

    # Load rhythm state and curve
    rhythm_state = await _load_rhythm_state(person_id)
    rhythm_curve = await _load_rhythm_curve(person_id, target_date)

    # Load active tasks (from goals table with type='task')
    tasks = await dbfetch(
        """
        SELECT id, title, description, priority, evolution_score
        FROM goals
        WHERE person_id = $1
          AND type = 'task'
          AND status = 'active'
        ORDER BY priority DESC
        LIMIT 20
        """,
        person_id,
    )

    # Load intents that are tasks
    pending_intents = await dbfetch(
        """
        SELECT id, title, priority, context_snapshot
        FROM intents
        WHERE user_id = $1
          AND intent_type = 'task'
          AND status IN ('draft', 'pending')
        ORDER BY priority DESC
        LIMIT 10
        """,
        person_id,
    )

    # Combine tasks and pending intents
    all_tasks = _normalize_tasks(tasks, pending_intents)

    if not all_tasks:
        return {
            "date": str(target_date),
            "scheduled": [],
            "rhythm_state": rhythm_state,
            "message": "No tasks to schedule",
        }

    # Find peak and lull windows
    peaks = _find_peak_windows(rhythm_curve, count=3)
    lulls = _find_lull_windows(rhythm_curve, count=2)

    # Calculate current capacity
    capacity = _calculate_capacity(rhythm_state)

    # Assign tasks to windows
    scheduled = _assign_to_windows(all_tasks, peaks, lulls, capacity)

    # Build capacity message
    if capacity >= HIGH_ENERGY_THRESHOLD:
        capacity_msg = "High capacity - good for stretch goals and demanding tasks"
    elif capacity >= LOW_ENERGY_THRESHOLD:
        capacity_msg = "Moderate capacity - focus on priority tasks"
    else:
        capacity_msg = "Low capacity - consider lighter tasks or rest"

    LOGGER.info(
        "[RhythmScheduler] person=%s date=%s tasks=%s capacity=%.2f peaks=%s",
        person_id,
        target_date,
        len(all_tasks),
        capacity,
        len(peaks),
    )

    return {
        "date": str(target_date),
        "capacity": round(capacity, 2),
        "capacity_message": capacity_msg,
        "scheduled": scheduled,
        "peaks": peaks,
        "lulls": lulls,
        "rhythm_state": rhythm_state,
    }


async def get_next_optimal_window(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Find the next optimal window for high-energy tasks.
    Useful for "when should I do X" queries.
    """
    rhythm_state = await _load_rhythm_state(person_id)
    rhythm_curve = await _load_rhythm_curve(person_id)

    if not rhythm_curve:
        # Fallback to next_peak from rhythm_state
        next_peak = rhythm_state.get("next_peak")
        if next_peak:
            return {
                "window": str(next_peak),
                "energy": rhythm_state.get("body_energy", 0.6),
                "source": "rhythm_state",
            }
        return None

    # Find current slot index based on time
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute

    peaks = _find_peak_windows(rhythm_curve, count=1, after_time=(current_hour, current_minute))

    if peaks:
        return peaks[0]

    return None


async def _load_rhythm_state(person_id: str) -> Dict[str, Any]:
    """Load current rhythm state."""
    state = await dbfetch(
        """
        SELECT body_energy, mind_focus, emotion_tone, fatigue_level,
               stress_level, next_peak, next_lull, chronotype
        FROM rhythm_state
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    return dict(state) if state else {}


async def _load_rhythm_curve(
    person_id: str,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Load rhythm curve slots for a specific day."""
    curve = await dbfetch(
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

    if not curve:
        return []

    slots = curve.get("slots")
    if isinstance(slots, str):
        try:
            slots = json.loads(slots)
        except json.JSONDecodeError:
            return []

    return slots if isinstance(slots, list) else []


def _normalize_tasks(
    goals: List[Any],
    intents: List[Any],
) -> List[Dict[str, Any]]:
    """Normalize tasks from goals and intents into common format."""
    tasks = []

    for g in (goals or []):
        tasks.append({
            "id": str(g.get("id")),
            "title": g.get("title"),
            "source": "goal",
            "priority": g.get("priority", 3),
            "energy_hint": _infer_energy_from_priority(g.get("priority", 3)),
        })

    for i in (intents or []):
        context = i.get("context_snapshot") or {}
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except json.JSONDecodeError:
                context = {}

        tasks.append({
            "id": str(i.get("id")),
            "title": i.get("title"),
            "source": "intent",
            "priority": i.get("priority", 3),
            "energy_hint": context.get("energy_hint") or _infer_energy_from_priority(i.get("priority", 3)),
        })

    # Sort by priority
    tasks.sort(key=lambda t: t.get("priority", 3), reverse=True)
    return tasks


def _infer_energy_from_priority(priority: int) -> str:
    """Map priority to energy requirement."""
    if priority >= 4:
        return "high"
    elif priority >= 2:
        return "medium"
    return "low"


def _energy_to_float(energy_hint: str) -> float:
    """Convert energy hint to float."""
    mapping = {"high": 0.8, "medium": 0.5, "low": 0.3}
    return mapping.get(energy_hint, 0.5)


def _find_peak_windows(
    slots: List[Dict[str, Any]],
    count: int = 3,
    after_time: Optional[Tuple[int, int]] = None,
) -> List[Dict[str, Any]]:
    """Find highest energy windows."""
    if not slots:
        return []

    # Filter to slots after current time if specified
    filtered_slots = slots
    if after_time:
        current_hour, current_minute = after_time
        filtered_slots = []
        for s in slots:
            slot_time = s.get("time", "")
            if ":" in slot_time:
                try:
                    h, m = map(int, slot_time.split(":"))
                    if h > current_hour or (h == current_hour and m >= current_minute):
                        filtered_slots.append(s)
                except ValueError:
                    pass
        if not filtered_slots:
            filtered_slots = slots  # Fallback to all slots

    # Sort by energy descending
    sorted_slots = sorted(
        filtered_slots,
        key=lambda s: float(s.get("energy", 0)),
        reverse=True,
    )

    peaks = []
    used_times = set()

    for slot in sorted_slots:
        if len(peaks) >= count:
            break

        time = slot.get("time")
        if time in used_times:
            continue

        # Avoid overlapping windows (60-min gap)
        try:
            h, m = map(int, time.split(":"))
            slot_minutes = h * 60 + m

            overlap = any(
                abs(slot_minutes - (int(t.split(":")[0]) * 60 + int(t.split(":")[1]))) < 60
                for t in used_times
            )
            if overlap:
                continue
        except (ValueError, AttributeError):
            pass

        peaks.append({
            "time": time,
            "energy": round(float(slot.get("energy", 0)), 2),
            "label": slot.get("label", "Peak"),
        })
        used_times.add(time)

    return peaks


def _find_lull_windows(slots: List[Dict[str, Any]], count: int = 2) -> List[Dict[str, Any]]:
    """Find lowest energy windows (good for rest/light tasks)."""
    if not slots:
        return []

    sorted_slots = sorted(
        slots,
        key=lambda s: float(s.get("energy", 0)),
    )

    lulls = []
    used_times = set()

    for slot in sorted_slots:
        if len(lulls) >= count:
            break

        time = slot.get("time")
        if time in used_times:
            continue

        lulls.append({
            "time": time,
            "energy": round(float(slot.get("energy", 0)), 2),
            "label": slot.get("label", "Rest window"),
        })
        used_times.add(time)

    return lulls


def _calculate_capacity(rhythm_state: Dict[str, Any]) -> float:
    """Calculate overall capacity from rhythm state."""
    if not rhythm_state:
        return 0.5  # Default neutral

    body_energy = float(rhythm_state.get("body_energy") or 0.5)
    mind_focus = float(rhythm_state.get("mind_focus") or 0.5)
    fatigue = float(rhythm_state.get("fatigue_level") or 0.3)
    stress = float(rhythm_state.get("stress_level") or 0.3)

    # Weighted capacity: positive factors - negative factors
    capacity = (body_energy * 0.4 + mind_focus * 0.3) - (fatigue * 0.2 + stress * 0.1)

    return max(0.0, min(1.0, capacity))


def _assign_to_windows(
    tasks: List[Dict[str, Any]],
    peaks: List[Dict[str, Any]],
    lulls: List[Dict[str, Any]],
    capacity: float,
) -> List[Dict[str, Any]]:
    """Assign tasks to optimal windows based on energy requirements."""
    scheduled = []
    peak_idx = 0
    lull_idx = 0

    for task in tasks:
        energy_needed = _energy_to_float(task.get("energy_hint", "medium"))

        # Skip high-energy tasks if capacity is too low
        if energy_needed >= HIGH_ENERGY_THRESHOLD and capacity < BLOCK_CAPACITY_THRESHOLD:
            scheduled.append({
                **task,
                "window": None,
                "status": "blocked",
                "reason": "Low capacity - consider rescheduling",
            })
            continue

        # High-energy tasks → peaks
        if energy_needed >= HIGH_ENERGY_THRESHOLD and peaks and peak_idx < len(peaks):
            window = peaks[peak_idx]
            peak_idx += 1
            scheduled.append({
                **task,
                "window": window.get("time"),
                "window_energy": window.get("energy"),
                "status": "scheduled",
                "fit_score": _calculate_fit_score(energy_needed, window.get("energy", 0.5)),
            })

        # Low-energy tasks → lulls (or anytime)
        elif energy_needed <= 0.4 and lulls and lull_idx < len(lulls):
            window = lulls[lull_idx]
            lull_idx += 1
            scheduled.append({
                **task,
                "window": window.get("time"),
                "window_energy": window.get("energy"),
                "status": "scheduled",
                "fit_score": 0.8,  # Good fit for low-energy in lull
            })

        # Medium-energy tasks → remaining peaks or flexible
        elif peaks and peak_idx < len(peaks):
            window = peaks[peak_idx]
            peak_idx += 1
            scheduled.append({
                **task,
                "window": window.get("time"),
                "window_energy": window.get("energy"),
                "status": "scheduled",
                "fit_score": _calculate_fit_score(energy_needed, window.get("energy", 0.5)),
            })

        else:
            # No optimal window, mark as flexible
            scheduled.append({
                **task,
                "window": None,
                "status": "flexible",
                "reason": "Schedule when convenient",
            })

    return scheduled


def _calculate_fit_score(energy_needed: float, window_energy: float) -> float:
    """Calculate how well a task fits a window (0-1)."""
    diff = abs(energy_needed - window_energy)
    return round(max(0, 1 - diff), 2)


__all__ = [
    "schedule_tasks_by_rhythm",
    "get_next_optimal_window",
]
