"""Lightweight hooks to trigger reflection updates after task events."""

from __future__ import annotations

from .jobs import run_daily_reflection


def on_plan_created(user_id: str) -> None:
    """Trigger a daily reflection after a plan is created."""

    run_daily_reflection(user_id)


def on_task_completed(user_id: str) -> None:
    """Trigger a daily reflection after a task is completed."""

    run_daily_reflection(user_id)
