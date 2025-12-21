from __future__ import annotations

import asyncio
import logging

from sakhi.apps.api.services.persona.tuner import tune_persona

LOGGER = logging.getLogger(__name__)


async def run_persona_tuning(person_id: str) -> None:
    await tune_persona(person_id)


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m sakhi.apps.worker.tasks.persona_tuning <person_id>")
        return

    person_id = sys.argv[1]
    try:
        asyncio.run(run_persona_tuning(person_id))
        LOGGER.info("Persona tuning completed for %s", person_id)
    except Exception as exc:  # pragma: no cover - manual runner helper
        LOGGER.error("Persona tuning failed for %s: %s", person_id, exc)


if __name__ == "__main__":
    main()


__all__ = ["run_persona_tuning", "main"]
