from __future__ import annotations

from datetime import datetime


def deadline_urgency(due_at, now: datetime) -> int:
    if not due_at:
        return 0
    delta_hours = (due_at - now).total_seconds() / 3600.0
    if delta_hours <= 0:
        return 3
    if delta_hours < 24:
        return 2
    if delta_hours < 72:
        return 1
    return 0


def value_over_effort(task: dict) -> float:
    value = task.get("value_score") or 0
    effort = task.get("estimated_min") or 30
    return value / max(effort, 1)




def context_fit(task: dict, ctx: dict) -> int:
    if ctx.get("mood") == "low":
        short = (task.get("estimated_min") or 25) <= 30
        return 1 if short else 0
    return 1 if ctx.get("time_of_day") == ctx.get("preferred_time") else 0


def rank_frontier(frontier: list, ctx: dict, prefs: dict):
    def score(task: dict) -> float:
        return (
            (prefs.get("w1", 2)) * (task.get("priority") or 0)
            + (prefs.get("w2", 3)) * value_over_effort(task)
            + (prefs.get("w3", 3)) * deadline_urgency(task.get("due_at"), ctx["now"])
            + (prefs.get("w4", 1)) * context_fit(task, ctx)
            + (prefs.get("w5", 1)) * (1 if task.get("project_id") == ctx.get("last_project_id") else 0)
        )

    return sorted(frontier, key=score, reverse=True)
