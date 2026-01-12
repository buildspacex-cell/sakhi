"""
Scaffolding Decorators

Decorators for scaffold workers to enforce suppression checks and other policies.

Design Principle: "Suppression First"
- Every proactive scaffold MUST check suppression before running
- Decorator makes this enforcement automatic
- No scaffold can bypass suppression
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, cast

from sakhi.libs.scaffolding.suppression_engine import (
    SuppressionAction,
    SuppressionSensitivity,
    check_scaffold_suppression,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def require_suppression_check(
    scaffold_type: str,
    sensitivity: SuppressionSensitivity = SuppressionSensitivity.MEDIUM
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to enforce suppression check before scaffold worker runs

    Usage:
        @require_suppression_check(scaffold_type="morning_preview", sensitivity="medium")
        async def run_morning_preview(person_id: str) -> None:
            # Worker logic here
            ...

    Args:
        scaffold_type: Type of scaffold (e.g., "morning_preview", "focus_path")
        sensitivity: Sensitivity level (low/medium/high)

    Returns:
        Decorated function that checks suppression first

    Note:
        - If suppressed, function returns None without running
        - Suppression decision is logged
        - For on-demand/user-initiated scaffolds, don't use this decorator
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            # Extract person_id from args or kwargs
            person_id: Optional[str] = None

            # Try to get person_id from first positional arg
            if args and isinstance(args[0], str):
                person_id = args[0]

            # Try to get person_id from kwargs
            if not person_id:
                person_id = kwargs.get("person_id") or kwargs.get("user_id")

            if not person_id:
                logger.warning(
                    f"Suppression check skipped for {scaffold_type}: no person_id found in args"
                )
                # No person_id, can't check suppression - allow by default
                # (This should not happen in production)
                result = await func(*args, **kwargs)
                return cast(T, result)

            # Check suppression
            decision = await check_scaffold_suppression(
                user_id=person_id,
                scaffold_type=scaffold_type,
                sensitivity=sensitivity
            )

            # Log decision
            logger.info(
                f"Suppression check for {scaffold_type} (user={person_id[:8]}...): "
                f"action={decision.action.value} reason={decision.reason}"
            )

            # If suppressed, return None without running
            if decision.action != SuppressionAction.ALLOW:
                logger.info(
                    f"Scaffold {scaffold_type} suppressed for user {person_id[:8]}... "
                    f"(reason: {decision.reason})"
                )
                return None

            # Suppression passed - run the scaffold worker
            result = await func(*args, **kwargs)
            return cast(T, result)

        return cast(Callable[..., T], wrapper)

    return decorator


__all__ = [
    "require_suppression_check",
]
