from __future__ import annotations

import asyncio
from typing import Any

from sakhi.apps.engine.daily_reflection.engine import generate_daily_reflection, persist_daily_reflection


async def run_daily_reflection(person_id: str) -> Any:
    summary = await generate_daily_reflection(person_id)
    await persist_daily_reflection(person_id, summary)
    return summary


def main() -> None:  # pragma: no cover - manual execution helper
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m sakhi.apps.worker.tasks.daily_reflection_worker <person_id>")
        return
    person_id = sys.argv[1]
    result = asyncio.run(run_daily_reflection(person_id))
    print(result)


__all__ = ["run_daily_reflection", "main"]
