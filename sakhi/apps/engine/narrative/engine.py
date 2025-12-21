from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


async def _fetch_intents(person_id: str) -> List[Dict[str, Any]]:
    return await q(
        """
        SELECT intent_name, strength, emotional_alignment, trend
        FROM intent_evolution
        WHERE person_id = $1
        """,
        person_id,
    ) or []


async def _fetch_tasks(person_id: str, intent_name: str) -> List[Dict[str, Any]]:
    return await q(
        """
        SELECT id, title, status, energy_cost, anchor_goal_id, auto_priority
        FROM tasks
        WHERE user_id = $1 AND lower(title) LIKE '%' || $2 || '%'
        """,
        person_id,
        intent_name.lower(),
    ) or []


async def _fetch_maps(person_id: str) -> Dict[str, Any]:
    pm_row = await q("SELECT long_term FROM personal_model WHERE person_id = $1", person_id, one=True) or {}
    long_term = (pm_row.get("long_term") or {}) if pm_row else {}
    alignment_row = await q("SELECT alignment_map FROM daily_alignment_cache WHERE person_id = $1", person_id, one=True) or {}
    coherence = long_term.get("coherence_report") or {}
    return {
        "alignment": alignment_row.get("alignment_map") or {},
        "coherence": coherence,
        "emotion_state": long_term.get("emotion_state") or {},
    }


def _task_progress(tasks: List[Dict[str, Any]]) -> float:
    if not tasks:
        return 0.0
    total = len(tasks)
    done = len([t for t in tasks if (t.get("status") or "").lower() == "done"])
    return done / total if total else 0.0


def _momentum(intent_strength: float, task_progress: float, emotional_alignment: float, drift: float) -> float:
    val = (intent_strength * 0.4) + (task_progress * 0.3) + (emotional_alignment * 0.2) + (drift * 0.1)
    return max(0.0, min(1.0, val))


def _stage(momentum: float) -> str:
    if momentum < 0.2:
        return "Initiation"
    if momentum < 0.4:
        return "Plateau"
    if momentum < 0.6:
        return "Rising Action"
    if momentum < 0.8:
        return "Climax"
    return "Recovery"


async def compute_narrative_arcs(person_id: str) -> List[Dict[str, Any]]:
    person_id = await resolve_person_id(person_id) or person_id
    intents = await _fetch_intents(person_id)
    maps = await _fetch_maps(person_id)
    alignment_map = maps.get("alignment") or {}
    coherence = maps.get("coherence") or {}
    emotion_state = maps.get("emotion_state") or {}
    drift = float(emotion_state.get("drift") or 0)

    arcs: List[Dict[str, Any]] = []
    for intent in intents:
        name = intent.get("intent_name") or ""
        strength = float(intent.get("strength") or 0)
        if strength <= 0.3:
            continue
        emotional_alignment = float(intent.get("emotional_alignment") or 0)
        tasks = await _fetch_tasks(person_id, name)
        progress = _task_progress(tasks)
        momentum_val = _momentum(strength, progress, emotional_alignment, drift)
        stage_val = _stage(momentum_val)

        warns: List[str] = []
        encour: List[str] = []
        if drift < -0.2:
            warns.append("Negative emotional drift")
        if progress < 0.2 and strength > 0.6:
            warns.append("Momentum loss risk")
        if coherence.get("issues"):
            warns.extend(coherence.get("issues"))

        if momentum_val < 0.5:
            encour.append("Micro-step improvements")
        if emotional_alignment < 0:
            encour.append("Try emotionally lighter version")
        if progress < 0.2:
            encour.append("Start with smallest action available")

        # Avoid actions influence
        if alignment_map.get("avoid_actions"):
            warns.append("Some tasks are marked avoid today")

        arcs.append(
            {
                "intent": name,
                "stage": stage_val,
                "momentum": round(momentum_val, 3),
                "emotional_backing": emotional_alignment,
                "task_progress": round(progress, 3),
                "warnings": warns,
                "encouragements": encour,
                "last_update": dt.datetime.utcnow().isoformat(),
            }
        )

    return arcs


__all__ = ["compute_narrative_arcs"]
