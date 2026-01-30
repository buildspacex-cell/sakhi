from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q
from sakhi.apps.logic.brain import brain_engine
from sakhi.apps.logic.journey import renderer as journey_renderer


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


async def _load_narrative(person_id: str) -> Dict[str, Any]:
    season = await q(
        """
        SELECT season, hints, updated_at
        FROM narrative_seasons
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    arc = await q(
        """
        SELECT arc_name, sentiment, tags, created_at
        FROM life_arcs
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    return {"season": season or {}, "arc": arc or {}}


async def _load_summaries(person_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    weekly = await q(
        """
        SELECT week_start, week_end, summary, highlights, top_themes, drift_score, created_at
        FROM memory_weekly_summaries
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    monthly = await q(
        """
        SELECT month_scope, summary, highlights, top_themes, chapter_hint, drift_score, compression, created_at
        FROM memory_monthly_recaps
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    return weekly or {}, monthly or {}


def _build_vision_insights(brain: Dict[str, Any], narrative: Dict[str, Any], monthly: Dict[str, Any]) -> List[str]:
    insights: List[str] = []
    life_chapter = _ensure_dict(brain.get("life_chapter"))
    chapter_name = life_chapter.get("chapter") or narrative.get("season", {}).get("season")
    identity = _ensure_dict(brain.get("identity_state"))
    purpose = identity.get("purpose")

    if chapter_name:
        insights.append(f"You appear to be in a '{chapter_name}' chapter; keep honoring its tone before pushing hard pivots.")
    if purpose:
        insights.append("Purpose themes stay present; small weekly moves toward them will reinforce direction.")
    drift = _to_float(monthly.get("drift_score"))
    if drift > 0.6:
        insights.append("Your monthly recap shows meaningful drift—consider pausing to rename what this phase means for you.")
    elif drift > 0.3:
        insights.append("There is some drift this month; a brief check-in on what's changing could help you realign.")

    return insights[:3]


def _build_pattern_insights(brain: Dict[str, Any], weekly: Dict[str, Any], journey_today: Dict[str, Any]) -> List[str]:
    insights: List[str] = []
    rhythm = _ensure_dict(brain.get("rhythm_state"))
    stress_trend = rhythm.get("stress_trend")
    energy_cycle = rhythm.get("energy_cycle") or []
    focus_sessions = _ensure_list(journey_today.get("focus_sessions"))
    environment = _ensure_dict(brain.get("environment_state"))
    environment["calendar_blocks"] = _ensure_list(environment.get("calendar_blocks"))
    environment["environment_tags"] = _ensure_list(environment.get("environment_tags"))
    calendar_blocks = environment["calendar_blocks"]
    total_meetings = sum(_to_float(b.get("total_minutes"), 0.0) for b in calendar_blocks)

    if stress_trend == "rising":
        insights.append("Stress has been rising—keep tasks small and close loops early in the day.")
    if energy_cycle:
        insights.append("Your energy pattern has a few peaks; schedule meaningful work into those windows.")
    if total_meetings > 240:
        insights.append("Meeting load looks heavy; avoid committing to deep work on the same days.")
    if focus_sessions:
        avg_completion = _to_float(sum(_to_float(s.get("completion_score"), 0.0) for s in focus_sessions) / max(len(focus_sessions), 1))
        if avg_completion < 0.5:
            insights.append("Recent focus sessions struggled; try lighter sessions and shorter wins to rebuild momentum.")

    weekly_themes = weekly.get("top_themes") if isinstance(weekly, dict) else None
    if weekly_themes:
        insights.append(f"This week's themes keep showing up: {', '.join(weekly_themes[:3])}. Reflect briefly on why.")

    return insights[:4]


def _build_value_alignment(brain: Dict[str, Any], habits: Dict[str, Any], weekly: Dict[str, Any]) -> List[str]:
    insights: List[str] = []
    identity = _ensure_dict(brain.get("identity_state"))
    values = identity.get("values") or []
    habits_top = _ensure_list(habits.get("top_habits"))
    if values and habits_top:
        top_value = values[0].get("value_name") if isinstance(values[0], dict) else None
        if top_value:
            insights.append(f"Your habit practice is reinforcing '{top_value}'; keep one tiny daily action to anchor it.")
    consistency = habits.get("consistency") or []
    if consistency:
        avg_streak = _to_float(sum(_to_float(c, 0.0) for c in consistency) / max(len(consistency), 1))
        if avg_streak < 2:
            insights.append("Habit consistency is soft; choose the smallest viable habit and protect it for 3 days.")
        else:
            insights.append("Consistency is forming—stack a small value-aligned task while the streak is warm.")
    if weekly.get("drift_score") and _to_float(weekly["drift_score"]) > 0.6:
        insights.append("You noted drift this week; check whether actions still match your core values.")
    return insights[:3]


def _build_actions(brain: Dict[str, Any], pattern_insights: List[str], behavior_profile: Dict[str, Any]) -> List[str]:
    actions: List[str] = []
    rhythm = _ensure_dict(brain.get("rhythm_state"))
    body_energy = _to_float(rhythm.get("body_energy"), 0.5)
    proactiveness = behavior_profile.get("proactiveness")
    planner_style = behavior_profile.get("planner_style")
    nudge_frequency = behavior_profile.get("nudge_frequency")

    if body_energy < 0.4:
        actions.append("Take one 10-minute restorative pause before new commitments today.")
    else:
        actions.append("Book a single 45-minute focus block in your next energy peak.")

    if planner_style == "light-touch":
        actions.append("Pick one goal and draft a tiny next step; skip detailed planning.")
    elif planner_style == "advisory":
        actions.append("Sketch a brief plan for your top priority and align it with your current energy.")

    if proactiveness == "passive" or nudge_frequency == "low":
        actions.append("Let’s keep suggestions minimal—if you want help, ask for one gentle idea.")
    else:
        actions.append("Would you like one supportive prompt to keep momentum?")

    # Keep to max 3
    return actions[:3]


def _confidence_score(patterns: List[str], values: List[str], actions: List[str]) -> float:
    # Lightweight confidence: more grounded signals -> higher confidence
    base = 0.5
    base += 0.1 * min(len(patterns), 2)
    base += 0.1 * min(len(values), 2)
    base += 0.1 * min(len(actions), 2)
    return round(min(0.95, base), 2)


async def generate_insights(person_id: str, mode: str = "today", behavior_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Build the Insight Bundle (VIVA).
    """

    brain = await brain_engine.get_brain_state(person_id, force_refresh=False)
    weekly, monthly = await _load_summaries(person_id)
    narrative = await _load_narrative(person_id)
    behavior = behavior_profile or {}

    # journey cache pull aligned to mode
    if mode == "monthly":
        journey_scope = await journey_renderer.get_month(person_id, force_refresh=False)
    elif mode == "weekly":
        journey_scope = await journey_renderer.get_week(person_id, force_refresh=False)
    else:
        journey_scope = await journey_renderer.get_today(person_id, force_refresh=False)

    vision = _build_vision_insights(brain, narrative, monthly)
    pattern = _build_pattern_insights(brain, weekly, journey_scope if isinstance(journey_scope, dict) else {})
    value = _build_value_alignment(brain, _ensure_dict(brain.get("habits_state")), weekly)
    actions = _build_actions(brain, pattern, behavior)

    confidence = _confidence_score(pattern, value, actions)

    summary_parts = []
    if vision:
        summary_parts.append(vision[0])
    if pattern:
        summary_parts.append(pattern[0])
    if value:
        summary_parts.append(value[0])
    if actions:
        summary_parts.append(actions[0])
    summary_text = " ".join(summary_parts[:4]) or "Insight bundle ready—no strong signals detected."

    return {
        "vision_insights": vision,
        "pattern_insights": pattern,
        "value_alignment": value,
        "action_recommendations": actions,
        "confidence": confidence,
        "summary": summary_text,
    }


async def summarize_insights(person_id: str, mode: str = "today", behavior_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    bundle = await generate_insights(person_id, mode=mode, behavior_profile=behavior_profile)
    text = bundle.get("summary") or ""
    return {"summary": text, "confidence": bundle.get("confidence", 0.5)}


__all__ = ["generate_insights", "summarize_insights"]
