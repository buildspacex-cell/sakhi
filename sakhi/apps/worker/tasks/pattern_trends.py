from __future__ import annotations

import logging

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.patterns.detector import detect_patterns

LOGGER = logging.getLogger(__name__)


async def run_pattern_trends() -> None:
    persons = await q("SELECT id FROM persons")
    for row in persons:
        person_id = row.get("id")
        if not person_id:
            continue
        try:
            await detect_patterns(str(person_id))
        except Exception as exc:  # pragma: no cover
            LOGGER.error("[PatternTrends] Failed for %s: %s", person_id, exc)


__all__ = ["run_pattern_trends"]
