"""
Timeout Configuration and Utilities
------------------------------------
Based on OpenClaw's defensive timeout patterns.

All timeouts are clamped to reasonable min/max bounds to prevent:
- Timeouts too short (< 500ms) causing premature failures
- Timeouts too long (> 10 minutes) hanging indefinitely

Usage:
    from sakhi.apps.api.services.agent.timeouts import clamp_timeout, Timeouts

    # Clamp user-provided timeout
    timeout_ms = clamp_timeout(user_timeout, min_ms=1000, max_ms=30000)

    # Use predefined constants
    timeout_ms = Timeouts.ACTION_EXECUTION
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TypeVar, Callable, Awaitable
from functools import wraps

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Timeout Constants (in milliseconds)
# =============================================================================

class Timeouts:
    """
    Predefined timeout values for different operations.

    All values are in milliseconds.
    Based on OpenClaw's timeout configurations.
    """

    # Minimum timeout for any operation (prevent instant failures)
    GLOBAL_MIN_MS = 500

    # Maximum timeout for any operation (prevent indefinite hangs)
    GLOBAL_MAX_MS = 600_000  # 10 minutes

    # Action execution
    ACTION_EXECUTION = 8_000  # 8 seconds default
    ACTION_MIN = 500
    ACTION_MAX = 60_000  # 1 minute max for any single action

    # Screen analysis (LLM call with image)
    SCREEN_ANALYSIS = 30_000  # 30 seconds
    SCREEN_ANALYSIS_MIN = 5_000
    SCREEN_ANALYSIS_MAX = 120_000  # 2 minutes

    # Action decision (LLM call)
    ACTION_DECISION = 15_000  # 15 seconds
    ACTION_DECISION_MIN = 2_000
    ACTION_DECISION_MAX = 60_000

    # Screenshot capture
    SCREENSHOT_CAPTURE = 5_000  # 5 seconds
    SCREENSHOT_CAPTURE_MIN = 1_000
    SCREENSHOT_CAPTURE_MAX = 30_000

    # Screenshot wait (polling for agent response)
    SCREENSHOT_WAIT = 60_000  # 60 seconds
    SCREENSHOT_WAIT_MIN = 10_000
    SCREENSHOT_WAIT_MAX = 300_000  # 5 minutes

    # Heartbeat interval
    HEARTBEAT_INTERVAL = 30_000  # 30 seconds
    HEARTBEAT_MIN = 5_000
    HEARTBEAT_MAX = 120_000

    # Lock acquisition
    LOCK_ACQUISITION = 10_000  # 10 seconds
    LOCK_MIN = 1_000
    LOCK_MAX = 60_000

    # Stale lock detection
    STALE_LOCK = 1_800_000  # 30 minutes

    # Approval wait
    APPROVAL_WAIT = 300_000  # 5 minutes
    APPROVAL_WAIT_MIN = 30_000
    APPROVAL_WAIT_MAX = 900_000  # 15 minutes

    # Session timeout (entire session)
    SESSION_TIMEOUT = 1_800_000  # 30 minutes
    SESSION_MIN = 60_000
    SESSION_MAX = 3_600_000  # 1 hour

    # API request
    API_REQUEST = 30_000  # 30 seconds
    API_REQUEST_MIN = 5_000
    API_REQUEST_MAX = 120_000


# =============================================================================
# Timeout Utilities
# =============================================================================

def clamp_timeout(
    timeout_ms: Optional[int],
    default_ms: int,
    min_ms: int = Timeouts.GLOBAL_MIN_MS,
    max_ms: int = Timeouts.GLOBAL_MAX_MS,
) -> int:
    """
    Clamp a timeout value to safe bounds.

    Follows OpenClaw's pattern: Math.max(min, Math.min(max, value))

    Args:
        timeout_ms: User-provided timeout (can be None)
        default_ms: Default value if None
        min_ms: Minimum allowed timeout
        max_ms: Maximum allowed timeout

    Returns:
        Clamped timeout value in milliseconds
    """
    if timeout_ms is None:
        timeout_ms = default_ms

    # Use global bounds as fallback
    actual_min = max(Timeouts.GLOBAL_MIN_MS, min_ms)
    actual_max = min(Timeouts.GLOBAL_MAX_MS, max_ms)

    return max(actual_min, min(actual_max, timeout_ms))


def ms_to_seconds(ms: int) -> float:
    """Convert milliseconds to seconds."""
    return ms / 1000.0


def seconds_to_ms(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return int(seconds * 1000)


# =============================================================================
# Async Timeout Decorator
# =============================================================================

T = TypeVar("T")


async def with_timeout(
    coro: Awaitable[T],
    timeout_ms: int,
    operation_name: str = "operation",
    *,
    min_ms: Optional[int] = None,
    max_ms: Optional[int] = None,
    on_timeout: Optional[Callable[[], T]] = None,
) -> T:
    """
    Execute a coroutine with a clamped timeout.

    Args:
        coro: The coroutine to execute
        timeout_ms: Timeout in milliseconds
        operation_name: Name for logging
        min_ms: Override minimum timeout
        max_ms: Override maximum timeout
        on_timeout: Optional callback to return value on timeout (instead of raising)

    Returns:
        Result of the coroutine

    Raises:
        asyncio.TimeoutError: If timeout exceeded and no on_timeout provided
    """
    from sakhi.apps.api.services.agent.errors import AgentError, ErrorReason

    # Clamp timeout
    clamped_ms = clamp_timeout(
        timeout_ms,
        default_ms=Timeouts.ACTION_EXECUTION,
        min_ms=min_ms or Timeouts.GLOBAL_MIN_MS,
        max_ms=max_ms or Timeouts.GLOBAL_MAX_MS,
    )

    timeout_seconds = ms_to_seconds(clamped_ms)

    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        LOGGER.warning(
            "[timeout] %s timed out after %dms",
            operation_name,
            clamped_ms,
        )
        if on_timeout:
            return on_timeout()
        raise AgentError(
            f"{operation_name} timed out after {clamped_ms}ms",
            reason=ErrorReason.TIMEOUT,
        )


def timeout_decorator(
    timeout_ms: int,
    operation_name: Optional[str] = None,
    min_ms: Optional[int] = None,
    max_ms: Optional[int] = None,
):
    """
    Decorator to apply timeout to async functions.

    Usage:
        @timeout_decorator(Timeouts.SCREEN_ANALYSIS, "screen analysis")
        async def analyze_screen(...):
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            name = operation_name or func.__name__
            return await with_timeout(
                func(*args, **kwargs),
                timeout_ms=timeout_ms,
                operation_name=name,
                min_ms=min_ms,
                max_ms=max_ms,
            )
        return wrapper
    return decorator


# =============================================================================
# Polling with Timeout
# =============================================================================

async def poll_until(
    condition: Callable[[], Awaitable[bool]],
    timeout_ms: int,
    poll_interval_ms: int = 2000,
    operation_name: str = "poll",
) -> bool:
    """
    Poll a condition until it returns True or timeout.

    Args:
        condition: Async function that returns True when done
        timeout_ms: Total timeout in milliseconds
        poll_interval_ms: Interval between polls
        operation_name: Name for logging

    Returns:
        True if condition was met, False if timed out
    """
    clamped_timeout = clamp_timeout(timeout_ms, default_ms=60000)
    clamped_interval = clamp_timeout(poll_interval_ms, default_ms=2000, min_ms=100, max_ms=30000)

    elapsed_ms = 0
    attempt = 0

    while elapsed_ms < clamped_timeout:
        attempt += 1
        try:
            if await condition():
                LOGGER.debug(
                    "[timeout] %s completed after %d attempts (%.1fs)",
                    operation_name,
                    attempt,
                    elapsed_ms / 1000,
                )
                return True
        except Exception as e:
            LOGGER.warning(
                "[timeout] %s condition check failed: %s",
                operation_name,
                e,
            )

        await asyncio.sleep(ms_to_seconds(clamped_interval))
        elapsed_ms += clamped_interval

        # Log progress periodically
        if attempt % 5 == 0:
            LOGGER.debug(
                "[timeout] %s still polling... (attempt %d, %.1fs elapsed)",
                operation_name,
                attempt,
                elapsed_ms / 1000,
            )

    LOGGER.warning(
        "[timeout] %s timed out after %d attempts (%.1fs)",
        operation_name,
        attempt,
        elapsed_ms / 1000,
    )
    return False


__all__ = [
    "Timeouts",
    "clamp_timeout",
    "ms_to_seconds",
    "seconds_to_ms",
    "with_timeout",
    "timeout_decorator",
    "poll_until",
]
