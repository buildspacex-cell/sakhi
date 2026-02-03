"""
Session Write Locking
---------------------
Database-based advisory locks for session write operations.

Based on OpenClaw's session-write-lock.ts pattern, adapted for PostgreSQL.

This prevents concurrent writes to the same session, which can cause:
- Race conditions in state updates
- Inconsistent action sequences
- Lost screenshot analyses

Usage:
    async with acquire_session_lock(session_id):
        # Session is exclusively locked
        await update_session_state(...)

Or manually:
    lock = await acquire_session_lock(session_id, timeout_ms=10000)
    try:
        await update_session_state(...)
    finally:
        await release_session_lock(lock)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, Optional, Set

from sakhi.apps.api.services.agent.errors import AgentError, ErrorReason
from sakhi.apps.api.services.agent.timeouts import Timeouts, clamp_timeout, ms_to_seconds

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Default timeout for lock acquisition
DEFAULT_LOCK_TIMEOUT_MS = 10_000  # 10 seconds

# Time after which a lock is considered stale (holder may have crashed)
STALE_LOCK_MS = 30 * 60 * 1000  # 30 minutes

# Use PostgreSQL advisory locks if available, fall back to in-memory
USE_DB_LOCKS = os.getenv("USE_DB_SESSION_LOCKS", "true").lower() == "true"


# =============================================================================
# Lock Data Structures
# =============================================================================

@dataclass
class SessionLock:
    """Represents an acquired session lock."""
    session_id: str
    lock_key: int  # PostgreSQL advisory lock key
    acquired_at: float  # Unix timestamp
    holder_id: str  # Identifier for the lock holder (process/request ID)
    is_db_lock: bool  # True if using DB advisory lock


# In-memory fallback locks
_memory_locks: Dict[str, SessionLock] = {}
_memory_lock = asyncio.Lock()

# Track locks held by this process
_held_locks: Set[str] = set()


# =============================================================================
# Lock Key Generation
# =============================================================================

def _session_to_lock_key(session_id: str) -> int:
    """
    Convert session ID to PostgreSQL advisory lock key.

    PostgreSQL advisory locks use bigint keys. We hash the session_id
    to get a consistent numeric key.
    """
    # Use first 8 bytes of MD5 hash as a signed 64-bit integer
    hash_bytes = hashlib.md5(session_id.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder='big', signed=True)


def _generate_holder_id() -> str:
    """Generate a unique identifier for this lock holder."""
    import uuid
    pid = os.getpid()
    unique = uuid.uuid4().hex[:8]
    return f"pid-{pid}-{unique}"


# =============================================================================
# Database Advisory Locks
# =============================================================================

async def _try_acquire_db_lock(lock_key: int, timeout_ms: int) -> bool:
    """
    Try to acquire a PostgreSQL advisory lock.

    Uses pg_try_advisory_lock which is non-blocking.
    Returns True if lock was acquired.
    """
    from sakhi.apps.api.core.db import q as dbfetch

    try:
        result = await dbfetch(
            "SELECT pg_try_advisory_lock($1) as acquired",
            lock_key,
            one=True,
        )
        return result.get("acquired", False) if result else False
    except Exception as e:
        LOGGER.warning("[session_lock] DB lock acquisition failed: %s", e)
        return False


async def _release_db_lock(lock_key: int) -> bool:
    """Release a PostgreSQL advisory lock."""
    from sakhi.apps.api.core.db import q as dbfetch

    try:
        result = await dbfetch(
            "SELECT pg_advisory_unlock($1) as released",
            lock_key,
            one=True,
        )
        return result.get("released", False) if result else False
    except Exception as e:
        LOGGER.warning("[session_lock] DB lock release failed: %s", e)
        return False


async def _check_db_lock_held(lock_key: int) -> bool:
    """Check if a PostgreSQL advisory lock is currently held."""
    from sakhi.apps.api.core.db import q as dbfetch

    try:
        # Check pg_locks for this advisory lock
        result = await dbfetch(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_locks
                WHERE locktype = 'advisory'
                AND classid = ($1 >> 32)::int
                AND objid = ($1 & 4294967295)::int
            ) as is_held
            """,
            lock_key,
            one=True,
        )
        return result.get("is_held", False) if result else False
    except Exception as e:
        LOGGER.warning("[session_lock] DB lock check failed: %s", e)
        return False


# =============================================================================
# In-Memory Fallback Locks
# =============================================================================

async def _try_acquire_memory_lock(
    session_id: str,
    holder_id: str,
    stale_ms: int = STALE_LOCK_MS,
) -> Optional[SessionLock]:
    """
    Try to acquire an in-memory lock.

    Detects and releases stale locks (holder may have crashed).
    """
    async with _memory_lock:
        existing = _memory_locks.get(session_id)

        if existing:
            # Check if lock is stale
            age_ms = (time.time() - existing.acquired_at) * 1000
            if age_ms > stale_ms:
                LOGGER.warning(
                    "[session_lock] Releasing stale lock for session %s (age: %.1fs)",
                    session_id,
                    age_ms / 1000,
                )
                del _memory_locks[session_id]
            else:
                # Lock is held and not stale
                return None

        # Acquire the lock
        lock = SessionLock(
            session_id=session_id,
            lock_key=_session_to_lock_key(session_id),
            acquired_at=time.time(),
            holder_id=holder_id,
            is_db_lock=False,
        )
        _memory_locks[session_id] = lock
        return lock


async def _release_memory_lock(session_id: str, holder_id: str) -> bool:
    """Release an in-memory lock."""
    async with _memory_lock:
        existing = _memory_locks.get(session_id)
        if existing and existing.holder_id == holder_id:
            del _memory_locks[session_id]
            return True
        return False


# =============================================================================
# Public API
# =============================================================================

async def acquire_session_lock(
    session_id: str,
    timeout_ms: Optional[int] = None,
    stale_ms: Optional[int] = None,
) -> SessionLock:
    """
    Acquire an exclusive lock for a session.

    Implements exponential backoff while waiting for the lock.

    Args:
        session_id: Session to lock
        timeout_ms: Max time to wait for lock (default 10s)
        stale_ms: Time after which a lock is considered stale (default 30min)

    Returns:
        SessionLock object (must be released when done)

    Raises:
        AgentError with reason=SESSION_LOCKED if timeout exceeded
    """
    timeout = clamp_timeout(
        timeout_ms,
        default_ms=DEFAULT_LOCK_TIMEOUT_MS,
        min_ms=Timeouts.LOCK_MIN,
        max_ms=Timeouts.LOCK_MAX,
    )
    stale = stale_ms or STALE_LOCK_MS

    lock_key = _session_to_lock_key(session_id)
    holder_id = _generate_holder_id()

    deadline = time.time() + ms_to_seconds(timeout)
    attempt = 0
    backoff_ms = 100  # Start with 100ms backoff

    LOGGER.debug(
        "[session_lock] Acquiring lock for session %s (timeout=%dms)",
        session_id,
        timeout,
    )

    while time.time() < deadline:
        attempt += 1

        # Try database lock first if enabled
        if USE_DB_LOCKS:
            if await _try_acquire_db_lock(lock_key, timeout):
                lock = SessionLock(
                    session_id=session_id,
                    lock_key=lock_key,
                    acquired_at=time.time(),
                    holder_id=holder_id,
                    is_db_lock=True,
                )
                _held_locks.add(session_id)
                LOGGER.debug(
                    "[session_lock] Acquired DB lock for session %s (attempt %d)",
                    session_id,
                    attempt,
                )
                return lock

        # Fall back to memory lock
        lock = await _try_acquire_memory_lock(session_id, holder_id, stale)
        if lock:
            _held_locks.add(session_id)
            LOGGER.debug(
                "[session_lock] Acquired memory lock for session %s (attempt %d)",
                session_id,
                attempt,
            )
            return lock

        # Exponential backoff with jitter
        import random
        jitter = random.uniform(0.8, 1.2)
        sleep_ms = min(backoff_ms * jitter, 1000)  # Cap at 1 second

        if attempt % 5 == 0:
            LOGGER.debug(
                "[session_lock] Waiting for lock on session %s (attempt %d)",
                session_id,
                attempt,
            )

        await asyncio.sleep(ms_to_seconds(int(sleep_ms)))
        backoff_ms = min(backoff_ms * 2, 1000)  # Double up to 1 second

    LOGGER.warning(
        "[session_lock] Timeout acquiring lock for session %s after %d attempts",
        session_id,
        attempt,
    )

    raise AgentError(
        f"Could not acquire lock for session {session_id} within {timeout}ms",
        reason=ErrorReason.SESSION_LOCKED,
        session_id=session_id,
    )


async def release_session_lock(lock: SessionLock) -> bool:
    """
    Release a session lock.

    Args:
        lock: The lock to release (from acquire_session_lock)

    Returns:
        True if lock was released successfully
    """
    released = False

    try:
        if lock.is_db_lock:
            released = await _release_db_lock(lock.lock_key)
        else:
            released = await _release_memory_lock(lock.session_id, lock.holder_id)

        if released:
            _held_locks.discard(lock.session_id)
            LOGGER.debug(
                "[session_lock] Released lock for session %s",
                lock.session_id,
            )
        else:
            LOGGER.warning(
                "[session_lock] Failed to release lock for session %s",
                lock.session_id,
            )
    except Exception as e:
        LOGGER.error("[session_lock] Error releasing lock: %s", e)

    return released


@asynccontextmanager
async def session_write_lock(
    session_id: str,
    timeout_ms: Optional[int] = None,
):
    """
    Context manager for session write locking.

    Usage:
        async with session_write_lock(session_id):
            await update_session(...)

    Args:
        session_id: Session to lock
        timeout_ms: Max time to wait for lock

    Raises:
        AgentError if lock cannot be acquired
    """
    lock = await acquire_session_lock(session_id, timeout_ms)
    try:
        yield lock
    finally:
        await release_session_lock(lock)


def is_session_locked(session_id: str) -> bool:
    """Check if a session is currently locked by this process."""
    return session_id in _held_locks


async def release_all_locks() -> int:
    """
    Release all locks held by this process.

    Call this on process shutdown to clean up.

    Returns:
        Number of locks released
    """
    released = 0

    for session_id in list(_held_locks):
        lock_key = _session_to_lock_key(session_id)

        # Try to release DB lock
        if USE_DB_LOCKS:
            try:
                await _release_db_lock(lock_key)
            except Exception:
                pass

        # Release memory lock
        async with _memory_lock:
            if session_id in _memory_locks:
                del _memory_locks[session_id]

        _held_locks.discard(session_id)
        released += 1

    if released > 0:
        LOGGER.info("[session_lock] Released %d locks on shutdown", released)

    return released


async def get_lock_diagnostics() -> Dict:
    """Get diagnostic information about current locks."""
    async with _memory_lock:
        memory_lock_count = len(_memory_locks)
        oldest_lock_age_ms = 0

        if _memory_locks:
            oldest = min(lock.acquired_at for lock in _memory_locks.values())
            oldest_lock_age_ms = int((time.time() - oldest) * 1000)

    return {
        "held_by_process": len(_held_locks),
        "memory_locks": memory_lock_count,
        "oldest_lock_age_ms": oldest_lock_age_ms,
        "use_db_locks": USE_DB_LOCKS,
    }


__all__ = [
    "SessionLock",
    "acquire_session_lock",
    "release_session_lock",
    "session_write_lock",
    "is_session_locked",
    "release_all_locks",
    "get_lock_diagnostics",
]
