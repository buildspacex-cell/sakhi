"""
Agent Error Classification System
---------------------------------
Based on OpenClaw's FailoverError pattern for intelligent retry logic.

This module provides:
- Explicit error classification with reason codes
- HTTP status mapping for API responses
- Helper functions for error detection and recovery decisions
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Dict, Any

LOGGER = logging.getLogger(__name__)


class ErrorReason(str, Enum):
    """Explicit classification of error types for retry logic."""
    AUTH = "auth"              # Authentication/authorization failed
    RATE_LIMIT = "rate_limit"  # API rate limited
    BILLING = "billing"        # Billing/quota exceeded
    TIMEOUT = "timeout"        # Request timed out
    CONTEXT_OVERFLOW = "context_overflow"  # Context window exceeded
    FORMAT = "format"          # Response format/parsing error
    NETWORK = "network"        # Network connectivity issue
    AGENT_OFFLINE = "agent_offline"  # Desktop agent not responding
    SESSION_LOCKED = "session_locked"  # Session is locked by another process
    RESOURCE_NOT_FOUND = "resource_not_found"  # Resource doesn't exist
    VALIDATION = "validation"  # Input validation failed
    UNKNOWN = "unknown"        # Unclassified error


class AgentError(Exception):
    """
    Base error class for agent operations with classification.

    Similar to OpenClaw's FailoverError, this provides:
    - Explicit reason classification
    - HTTP status mapping
    - Metadata for retry decisions
    """

    def __init__(
        self,
        message: str,
        reason: ErrorReason = ErrorReason.UNKNOWN,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[int] = None,
        retry_after_ms: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.reason = reason
        self.provider = provider
        self.model = model
        self.session_id = session_id
        self.agent_id = agent_id
        self.status = status or self._default_status()
        self.retry_after_ms = retry_after_ms
        self.original_error = original_error

    def _default_status(self) -> int:
        """Map reason to HTTP status code."""
        return {
            ErrorReason.AUTH: 401,
            ErrorReason.RATE_LIMIT: 429,
            ErrorReason.BILLING: 402,
            ErrorReason.TIMEOUT: 504,
            ErrorReason.CONTEXT_OVERFLOW: 413,
            ErrorReason.FORMAT: 422,
            ErrorReason.NETWORK: 503,
            ErrorReason.AGENT_OFFLINE: 503,
            ErrorReason.SESSION_LOCKED: 423,
            ErrorReason.RESOURCE_NOT_FOUND: 404,
            ErrorReason.VALIDATION: 400,
            ErrorReason.UNKNOWN: 500,
        }.get(self.reason, 500)

    def is_retryable(self) -> bool:
        """Check if this error can be retried."""
        return self.reason in {
            ErrorReason.RATE_LIMIT,
            ErrorReason.TIMEOUT,
            ErrorReason.NETWORK,
            ErrorReason.AGENT_OFFLINE,
            ErrorReason.CONTEXT_OVERFLOW,  # Can retry with compaction
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error for API responses."""
        return {
            "error": str(self),
            "reason": self.reason.value,
            "status": self.status,
            "retry_after_ms": self.retry_after_ms,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
        }


class VisionLoopError(AgentError):
    """Error during vision loop execution."""
    pass


class ActionError(AgentError):
    """Error executing an action."""
    pass


class ScreenAnalysisError(AgentError):
    """Error analyzing screen content."""
    pass


class SessionError(AgentError):
    """Error with session management."""
    pass


# =============================================================================
# Error Classification Helpers
# =============================================================================

def classify_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> AgentError:
    """
    Classify an arbitrary exception into an AgentError.

    Uses pattern matching on error messages similar to OpenClaw's approach.

    Args:
        error: The original exception
        context: Optional context (session_id, agent_id, etc.)

    Returns:
        Classified AgentError
    """
    context = context or {}
    message = str(error).lower()

    # Rate limiting patterns
    if any(pattern in message for pattern in [
        "rate limit", "ratelimit", "429", "too many requests",
        "quota exceeded", "throttl",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.RATE_LIMIT,
            retry_after_ms=60000,  # Default 1 minute
            original_error=error,
            **context,
        )

    # Authentication patterns
    if any(pattern in message for pattern in [
        "unauthorized", "authentication", "invalid api key",
        "401", "forbidden", "403", "access denied",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.AUTH,
            original_error=error,
            **context,
        )

    # Billing patterns
    if any(pattern in message for pattern in [
        "billing", "payment", "insufficient", "402",
        "credit", "exceeded your", "quota",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.BILLING,
            original_error=error,
            **context,
        )

    # Timeout patterns
    if any(pattern in message for pattern in [
        "timeout", "timed out", "deadline exceeded",
        "504", "request took too long",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.TIMEOUT,
            retry_after_ms=5000,  # Retry quickly
            original_error=error,
            **context,
        )

    # Context overflow patterns
    if any(pattern in message for pattern in [
        "context length", "too many tokens", "token limit",
        "context window", "maximum context", "413",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.CONTEXT_OVERFLOW,
            original_error=error,
            **context,
        )

    # Network patterns
    if any(pattern in message for pattern in [
        "connection", "network", "dns", "unreachable",
        "econnrefused", "enotfound", "503",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.NETWORK,
            retry_after_ms=5000,
            original_error=error,
            **context,
        )

    # Format/parsing patterns
    if any(pattern in message for pattern in [
        "json", "parse", "invalid format", "422",
        "unexpected token", "decode",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.FORMAT,
            original_error=error,
            **context,
        )

    # Agent offline patterns
    if any(pattern in message for pattern in [
        "agent not responding", "no screenshot", "desktop agent",
        "agent offline",
    ]):
        return AgentError(
            str(error),
            reason=ErrorReason.AGENT_OFFLINE,
            retry_after_ms=10000,
            original_error=error,
            **context,
        )

    # Default to unknown
    return AgentError(
        str(error),
        reason=ErrorReason.UNKNOWN,
        original_error=error,
        **context,
    )


def is_context_overflow_error(error: Exception) -> bool:
    """Check if an error is due to context window overflow."""
    if isinstance(error, AgentError):
        return error.reason == ErrorReason.CONTEXT_OVERFLOW

    message = str(error).lower()
    return any(pattern in message for pattern in [
        "context length", "too many tokens", "token limit",
        "context window", "maximum context",
    ])


def is_retryable_error(error: Exception) -> bool:
    """Check if an error can be retried."""
    if isinstance(error, AgentError):
        return error.is_retryable()

    # Classify and check
    classified = classify_error(error)
    return classified.is_retryable()


def get_retry_delay_ms(error: Exception, attempt: int = 1) -> int:
    """
    Calculate retry delay with exponential backoff.

    Uses OpenClaw's pattern: base * 2^(attempt-1), capped at max.

    Args:
        error: The error that occurred
        attempt: Current attempt number (1-based)

    Returns:
        Delay in milliseconds before retry
    """
    MIN_DELAY_MS = 1000   # 1 second
    MAX_DELAY_MS = 60000  # 1 minute

    # Get base delay from error if available
    if isinstance(error, AgentError) and error.retry_after_ms:
        base_delay = error.retry_after_ms
    else:
        base_delay = 5000  # 5 seconds default

    # Exponential backoff: base * 2^(attempt-1)
    delay = base_delay * (2 ** (attempt - 1))

    # Clamp to bounds
    return max(MIN_DELAY_MS, min(MAX_DELAY_MS, delay))


# =============================================================================
# Cooldown Tracking (OpenClaw pattern)
# =============================================================================

_error_counts: Dict[str, int] = {}  # agent_id -> error count
_cooldown_until: Dict[str, float] = {}  # agent_id -> timestamp


def track_error(agent_id: str) -> int:
    """
    Track an error for an agent, return current count.

    Used for implementing OpenClaw-style exponential cooldowns.
    """
    _error_counts[agent_id] = _error_counts.get(agent_id, 0) + 1
    return _error_counts[agent_id]


def clear_errors(agent_id: str) -> None:
    """Clear error count for an agent (on successful operation)."""
    _error_counts.pop(agent_id, None)
    _cooldown_until.pop(agent_id, None)


def get_error_count(agent_id: str) -> int:
    """Get current error count for an agent."""
    return _error_counts.get(agent_id, 0)


def set_cooldown(agent_id: str, until_timestamp: float) -> None:
    """Set cooldown until timestamp for an agent."""
    _cooldown_until[agent_id] = until_timestamp
    LOGGER.info(
        "[errors] Set cooldown for agent %s until %s",
        agent_id,
        until_timestamp,
    )


def is_in_cooldown(agent_id: str) -> bool:
    """Check if an agent is in cooldown period."""
    import time
    until = _cooldown_until.get(agent_id, 0)
    return time.time() < until


def calculate_cooldown_ms(error_count: int) -> int:
    """
    Calculate cooldown duration based on error count.

    Uses OpenClaw's pattern: 5^(n-1) minutes, capped at 1 hour.

    Args:
        error_count: Number of consecutive errors

    Returns:
        Cooldown duration in milliseconds
    """
    MAX_COOLDOWN_MS = 60 * 60 * 1000  # 1 hour

    # 5^(n-1) minutes
    minutes = 5 ** min(error_count - 1, 3)  # Cap exponent at 3
    ms = minutes * 60 * 1000

    return min(ms, MAX_COOLDOWN_MS)


__all__ = [
    "ErrorReason",
    "AgentError",
    "VisionLoopError",
    "ActionError",
    "ScreenAnalysisError",
    "SessionError",
    "classify_error",
    "is_context_overflow_error",
    "is_retryable_error",
    "get_retry_delay_ms",
    "track_error",
    "clear_errors",
    "get_error_count",
    "set_cooldown",
    "is_in_cooldown",
    "calculate_cooldown_ms",
]
