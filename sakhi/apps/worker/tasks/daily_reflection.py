from __future__ import annotations

import asyncio
import logging
from typing import Any

from sakhi.apps.api.services.reflection.daily_generator import generate_daily_reflection

LOGGER = logging.getLogger(__name__)


async def run_daily_reflection(person_id: str) -> Any:
    """Async helper to trigger the daily reflection generator."""

    return await generate_daily_reflection(person_id)


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m sakhi.apps.worker.tasks.daily_reflection <person_id>")
        return

    person_id = sys.argv[1]
    try:
        result = asyncio.run(run_daily_reflection(person_id))
        LOGGER.info("Daily reflection completed for %s: %s", person_id, bool(result))
    except Exception as exc:  # pragma: no cover - manual runner utility
        LOGGER.error("Daily reflection failed for %s: %s", person_id, exc)


if __name__ == "__main__":
    main()


__all__ = ["run_daily_reflection", "main"]
