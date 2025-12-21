from __future__ import annotations

import asyncio
import logging

from sakhi.apps.api.services.embeddings.consolidate import consolidate_embeddings_for_user

LOGGER = logging.getLogger(__name__)


async def run_embedding_consolidation(person_id: str) -> None:
    await consolidate_embeddings_for_user(person_id)


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m sakhi.apps.worker.tasks.embedding_consolidation <person_id>")
        return

    person_id = sys.argv[1]
    try:
        asyncio.run(run_embedding_consolidation(person_id))
        LOGGER.info("Embedding consolidation completed for %s", person_id)
    except Exception as exc:  # pragma: no cover - manual helper
        LOGGER.error("Embedding consolidation failed for %s: %s", person_id, exc)


if __name__ == "__main__":
    main()


__all__ = ["run_embedding_consolidation", "main"]
