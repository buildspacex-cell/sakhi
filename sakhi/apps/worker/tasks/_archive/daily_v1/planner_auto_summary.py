from __future__ import annotations

import asyncio
import logging

from sakhi.apps.api.services.planning.auto_summarizer import generate_planner_summary

LOGGER = logging.getLogger(__name__)


async def run_planner_summary(person_id: str) -> None:
    await generate_planner_summary(person_id)


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m sakhi.apps.worker.tasks.planner_auto_summary <person_id>")
        return

    person_id = sys.argv[1]
    try:
        asyncio.run(run_planner_summary(person_id))
        LOGGER.info("Planner auto summary completed for %s", person_id)
    except Exception as exc:  # pragma: no cover - manual runner helper
        LOGGER.error("Planner auto summary failed for %s: %s", person_id, exc)


if __name__ == "__main__":
    main()


__all__ = ["run_planner_summary", "main"]
