"""
Email Digest Worker Task
-------------------------
RQ background job that generates an LLM-powered email digest.

Flow:
1. Select relevant emails from email_events
2. Fetch bodies transiently via Gmail API
3. Run LLM triage and commitment extraction
4. Store structured digest (bodies discarded)
"""

from __future__ import annotations

import asyncio
import logging

LOGGER = logging.getLogger(__name__)


async def _run_digest_generation(person_id: str, force: bool = False) -> dict:
    """Async implementation: generate email digest."""
    LOGGER.info("[DigestWorker] Starting digest generation for %s", person_id)

    try:
        from sakhi.apps.api.services.email.digest import generate_digest

        result = await generate_digest(person_id, force=force)

        status = result.get("status", "unknown") if isinstance(result, dict) else "done"
        LOGGER.info("[DigestWorker] Digest complete for %s: %s", person_id, status)

        return {
            "status": "complete",
            "digest_status": status,
        }

    except Exception as e:
        LOGGER.exception("[DigestWorker] Failed for %s: %s", person_id, e)
        return {"status": "error", "error": str(e)}


def run_digest_generation(person_id: str, force: bool = False) -> None:
    """RQ job entry point: generate email digest."""
    asyncio.run(_run_digest_generation(person_id, force=force))


__all__ = ["run_digest_generation", "_run_digest_generation"]
