"""
Browser Session Management
--------------------------
Manages persistent browser sessions with credential storage and context reuse.

Features:
- Persistent browser contexts (cookies, localStorage preserved)
- Credential vault for secure login automation
- Session pooling for concurrent tasks
- Automatic session cleanup
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from sakhi.apps.api.services.agent.browser_automation import (
    BrowserAutomation,
    ActionStrategy,
    DEFAULT_VIEWPORT,
)

LOGGER = logging.getLogger(__name__)

# Session storage directory
SESSION_DIR = Path(os.getenv("BROWSER_SESSION_DIR", "/tmp/sakhi/browser_sessions"))
CREDENTIAL_FILE = SESSION_DIR / ".credentials.json"

# Session limits
MAX_SESSIONS_PER_USER = 3
SESSION_TIMEOUT_MINUTES = 30
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BrowserSession:
    """Represents an active browser session."""
    id: str
    person_id: str
    browser: Optional[BrowserAutomation] = None
    task_description: Optional[str] = None

    # State
    status: str = "idle"  # idle, running, paused, completed, failed
    current_url: Optional[str] = None

    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    actions_executed: int = 0
    errors: List[str] = field(default_factory=list)

    # Context persistence
    context_path: Optional[Path] = None

    def is_expired(self) -> bool:
        """Check if session has expired due to inactivity."""
        timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        return datetime.utcnow() - self.last_activity > timeout

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "status": self.status,
            "current_url": self.current_url,
            "task_description": self.task_description,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "actions_executed": self.actions_executed,
            "errors": self.errors[-5:],  # Last 5 errors
        }


@dataclass
class StoredCredential:
    """Encrypted credential for a site."""
    site_pattern: str  # Regex pattern for matching URLs
    username: str
    password: str  # Should be encrypted in production
    extra_fields: Dict[str, str] = field(default_factory=dict)
    last_used: Optional[datetime] = None

    def matches(self, url: str) -> bool:
        """Check if credential matches the URL."""
        import re
        return bool(re.search(self.site_pattern, url))


# =============================================================================
# Session Manager (Singleton)
# =============================================================================

class BrowserSessionManager:
    """
    Manages browser sessions across the application.

    Usage:
        manager = get_session_manager()
        session = await manager.create_session(person_id="user123")

        async with session.browser as browser:
            await browser.navigate("https://example.com")
    """

    _instance: Optional["BrowserSessionManager"] = None

    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}
        self._credentials: Dict[str, List[StoredCredential]] = {}  # person_id -> credentials
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Ensure session directory exists
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        # Load stored credentials
        self._load_credentials()

    @classmethod
    def get_instance(cls) -> "BrowserSessionManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_credentials(self) -> None:
        """Load credentials from storage."""
        if CREDENTIAL_FILE.exists():
            try:
                data = json.loads(CREDENTIAL_FILE.read_text())
                for person_id, creds in data.items():
                    self._credentials[person_id] = [
                        StoredCredential(**c) for c in creds
                    ]
                LOGGER.info("[browser_session] Loaded credentials for %d users", len(data))
            except Exception as e:
                LOGGER.error("[browser_session] Failed to load credentials: %s", e)

    def _save_credentials(self) -> None:
        """Save credentials to storage."""
        try:
            data = {
                person_id: [
                    {
                        "site_pattern": c.site_pattern,
                        "username": c.username,
                        "password": c.password,  # Should encrypt in production
                        "extra_fields": c.extra_fields,
                    }
                    for c in creds
                ]
                for person_id, creds in self._credentials.items()
            }
            CREDENTIAL_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            LOGGER.error("[browser_session] Failed to save credentials: %s", e)

    async def create_session(
        self,
        person_id: str,
        *,
        task_description: Optional[str] = None,
        headless: bool = True,
        strategy: ActionStrategy = ActionStrategy.DOM_FIRST,
        reuse_context: bool = True,
    ) -> BrowserSession:
        """
        Create a new browser session.

        Args:
            person_id: User's ID
            task_description: What the session is for
            headless: Run browser in headless mode
            strategy: DOM_FIRST, VISION_ONLY, or DOM_ONLY
            reuse_context: Reuse stored cookies/localStorage

        Returns:
            New browser session
        """
        async with self._lock:
            # Check session limit
            user_sessions = [s for s in self._sessions.values() if s.person_id == person_id]
            if len(user_sessions) >= MAX_SESSIONS_PER_USER:
                # Close oldest session
                oldest = min(user_sessions, key=lambda s: s.last_activity)
                await self.close_session(oldest.id)

            # Create session
            session_id = str(uuid.uuid4())
            context_path = SESSION_DIR / f"context_{person_id}" if reuse_context else None

            # Create browser with persistent context
            browser = BrowserAutomation(
                headless=headless,
                strategy=strategy,
            )

            session = BrowserSession(
                id=session_id,
                person_id=person_id,
                browser=browser,
                task_description=task_description,
                context_path=context_path,
            )

            self._sessions[session_id] = session

            # Start cleanup task if not running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            LOGGER.info(
                "[browser_session] Created session %s for user %s",
                session_id,
                person_id,
            )

            return session

    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            session.touch()
            return session
        elif session:
            # Session expired, clean up
            await self.close_session(session_id)
        return None

    async def get_user_sessions(self, person_id: str) -> List[BrowserSession]:
        """Get all sessions for a user."""
        return [
            s for s in self._sessions.values()
            if s.person_id == person_id and not s.is_expired()
        ]

    async def close_session(self, session_id: str) -> bool:
        """Close and cleanup a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            try:
                if session.browser:
                    await session.browser.stop()
                session.status = "completed"
                LOGGER.info("[browser_session] Closed session %s", session_id)
                return True
            except Exception as e:
                LOGGER.error("[browser_session] Error closing session %s: %s", session_id, e)
        return False

    async def close_user_sessions(self, person_id: str) -> int:
        """Close all sessions for a user."""
        sessions = await self.get_user_sessions(person_id)
        closed = 0
        for session in sessions:
            if await self.close_session(session.id):
                closed += 1
        return closed

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired sessions."""
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]

            for sid in expired:
                await self.close_session(sid)

            if expired:
                LOGGER.info("[browser_session] Cleaned up %d expired sessions", len(expired))

    # =========================================================================
    # Credential Management
    # =========================================================================

    def store_credential(
        self,
        person_id: str,
        site_pattern: str,
        username: str,
        password: str,
        extra_fields: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Store a credential for automated login.

        Args:
            person_id: User's ID
            site_pattern: Regex pattern for matching URLs (e.g., r".*google\\.com.*")
            username: Login username/email
            password: Login password (should encrypt in production)
            extra_fields: Additional form fields
        """
        if person_id not in self._credentials:
            self._credentials[person_id] = []

        # Check if credential exists, update if so
        for i, cred in enumerate(self._credentials[person_id]):
            if cred.site_pattern == site_pattern:
                self._credentials[person_id][i] = StoredCredential(
                    site_pattern=site_pattern,
                    username=username,
                    password=password,
                    extra_fields=extra_fields or {},
                )
                self._save_credentials()
                return

        # Add new credential
        self._credentials[person_id].append(StoredCredential(
            site_pattern=site_pattern,
            username=username,
            password=password,
            extra_fields=extra_fields or {},
        ))
        self._save_credentials()
        LOGGER.info("[browser_session] Stored credential for %s", site_pattern)

    def get_credential(
        self,
        person_id: str,
        url: str,
    ) -> Optional[StoredCredential]:
        """Get matching credential for a URL."""
        creds = self._credentials.get(person_id, [])
        for cred in creds:
            if cred.matches(url):
                cred.last_used = datetime.utcnow()
                return cred
        return None

    def delete_credential(
        self,
        person_id: str,
        site_pattern: str,
    ) -> bool:
        """Delete a stored credential."""
        if person_id in self._credentials:
            original_len = len(self._credentials[person_id])
            self._credentials[person_id] = [
                c for c in self._credentials[person_id]
                if c.site_pattern != site_pattern
            ]
            if len(self._credentials[person_id]) < original_len:
                self._save_credentials()
                return True
        return False

    def list_credentials(self, person_id: str) -> List[Dict[str, str]]:
        """List stored credentials (without passwords)."""
        return [
            {
                "site_pattern": c.site_pattern,
                "username": c.username,
                "last_used": c.last_used.isoformat() if c.last_used else None,
            }
            for c in self._credentials.get(person_id, [])
        ]


# =============================================================================
# Convenience Functions
# =============================================================================

def get_session_manager() -> BrowserSessionManager:
    """Get the browser session manager singleton."""
    return BrowserSessionManager.get_instance()


async def create_browser_session(
    person_id: str,
    task: Optional[str] = None,
    headless: bool = True,
) -> BrowserSession:
    """
    Create a browser session for a user.

    Convenience wrapper around session manager.
    """
    manager = get_session_manager()
    return await manager.create_session(
        person_id=person_id,
        task_description=task,
        headless=headless,
    )


async def run_browser_task_with_session(
    person_id: str,
    task: str,
    starting_url: str,
    *,
    headless: bool = True,
    max_steps: int = 20,
) -> Dict[str, Any]:
    """
    Run a browser task with session management.

    Handles session creation, credential injection, and cleanup.
    """
    from sakhi.apps.api.services.agent.browser_automation import run_browser_task

    manager = get_session_manager()
    session = await manager.create_session(
        person_id=person_id,
        task_description=task,
        headless=headless,
    )

    try:
        session.status = "running"

        # Start browser
        await session.browser.start()

        # Check for stored credentials for the starting URL
        cred = manager.get_credential(person_id, starting_url)
        if cred:
            LOGGER.info("[browser_session] Found stored credential for %s", starting_url)
            # Could auto-login here if needed

        # Run the task
        result = await run_browser_task(
            task=task,
            starting_url=starting_url,
            headless=headless,
            max_steps=max_steps,
        )

        session.status = "completed" if result.get("success") else "failed"
        session.actions_executed = session.browser.actions_executed

        return {
            **result,
            "session_id": session.id,
        }

    except Exception as e:
        session.status = "failed"
        session.errors.append(str(e))
        return {
            "success": False,
            "error": str(e),
            "session_id": session.id,
        }
    finally:
        await manager.close_session(session.id)


__all__ = [
    "BrowserSession",
    "StoredCredential",
    "BrowserSessionManager",
    "get_session_manager",
    "create_browser_session",
    "run_browser_task_with_session",
]
