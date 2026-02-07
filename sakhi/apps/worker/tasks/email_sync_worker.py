"""
Email Sync Worker Task
----------------------
RQ background job that orchestrates email sync and signal extraction.

Flow:
1. Sync email metadata from provider (Gmail)
2. Extract signals (subscriptions, avoidance, boundary, cognitive load)
3. Store results for frontend display
"""

from __future__ import annotations

import asyncio
import logging

from sakhi.apps.api.services.email.integration import extract_all_signals
from sakhi.apps.api.services.email.models import SyncStatus
from sakhi.apps.api.services.email.sync import start_email_sync, update_sync_status

LOGGER = logging.getLogger(__name__)


async def _run_email_sync(person_id: str) -> dict:
    """Async implementation: sync emails then extract signals."""
    LOGGER.info("[EmailSyncWorker] Starting email sync for %s", person_id)

    try:
        # Phase 1: Sync emails from provider
        progress = await start_email_sync(person_id)

        if progress.status in (
            SyncStatus.ERROR,
            SyncStatus.REVOKED,
            SyncStatus.NOT_CONNECTED,
        ):
            LOGGER.warning(
                "[EmailSyncWorker] Sync failed for %s: status=%s error=%s",
                person_id,
                progress.status,
                progress.error,
            )
            return {
                "status": "error",
                "sync_status": progress.status.value
                if hasattr(progress.status, "value")
                else str(progress.status),
                "error": progress.error,
            }

        LOGGER.info(
            "[EmailSyncWorker] Sync complete for %s: %d messages",
            person_id,
            progress.messages_synced,
        )

        # Phase 2: Extract signals from synced events
        signals = await extract_all_signals(person_id, force_refresh=True)

        LOGGER.info(
            "[EmailSyncWorker] Signals extracted for %s: %s",
            person_id,
            signals.get("status") if isinstance(signals, dict) else "done",
        )

        return {
            "status": "complete",
            "messages_synced": progress.messages_synced,
            "signals_status": signals.get("status")
            if isinstance(signals, dict)
            else "extracted",
        }

    except Exception as e:
        LOGGER.exception("[EmailSyncWorker] Failed for %s: %s", person_id, e)
        try:
            await update_sync_status(person_id, SyncStatus.ERROR, str(e))
        except Exception:
            pass
        return {"status": "error", "error": str(e)}


def run_email_sync(person_id: str) -> None:
    """RQ job entry point: sync emails and extract signals."""
    asyncio.run(_run_email_sync(person_id))


__all__ = ["run_email_sync", "_run_email_sync"]
