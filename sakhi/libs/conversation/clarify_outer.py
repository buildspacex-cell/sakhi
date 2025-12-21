from typing import Any, Dict, Tuple

TIMELINE_HORIZONS = {"today", "tomorrow", "week", "weekend", "month", "quarter", "year", "long_term", "date"}


def _timeline_known(tl: Any) -> bool:
    if not isinstance(tl, dict):
        return False
    hor = str(tl.get("horizon") or "").lower()
    return (hor in TIMELINE_HORIZONS) or bool(tl.get("target_date"))


def next_question_with_step(cl: Dict) -> Tuple[str, str | None]:
    """
    Decide the next clarifying question for OUTER intents and identify the step.
    Returns (question, step_name) where step_name is one of
    [timeline, preferences, constraints, criteria, assets].
    """
    if not isinstance(cl, dict):
        return "", None

    # 1) TIMELINE FIRST
    tl = cl.get("timeline") or {}
    if not _timeline_known(tl):
        return ("When would you like this to happen — today, this weekend, or a specific date?", "timeline")

    # 2) PREFERENCES (activity-ish intents)
    intent_type = str(cl.get("intent_type") or "")
    domain = (cl.get("domain") or "").lower()
    ctx = cl.get("context", {}) if isinstance(cl.get("context"), dict) else {}
    location_known = bool(ctx.get("location") or cl.get("location"))

    if intent_type in {"activity", "task"} or domain in {"grooming", "errand", "outing", "meet"}:
        if not location_known:
            return ("Any preferred place or area for this?", "preferences")
        prefs = cl.get("tags") or []
        if isinstance(prefs, list) and not prefs:
            return ("Any preferences I should keep in mind (stylist, style, budget)?", "preferences")

    # 3) CONSTRAINTS / WINDOWS
    g = cl.get("g_mvs", {}) if isinstance(cl, dict) else {}
    if not g.get("constraints"):
        return ("Any time or budget constraints I should respect?", "constraints")

    # 4) CRITERIA / ASSETS
    if not g.get("criteria"):
        return ("What would count as progress here?", "criteria")
    if not g.get("assets_blockers"):
        return ("Anything that could help or get in the way?", "assets")

    # We have enough—hand off to planner
    return "", None


def next_question(cl: Dict) -> str:
    """
    Decide the next clarifying question for OUTER intents.
    """
    question, _ = next_question_with_step(cl)
    return question


def permission_prompt() -> str:
    # gentler, forward-moving; no “stay with it / leave it” wording
    return "Great — want me to sketch a quick plan and block a slot for you?"
