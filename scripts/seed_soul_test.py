from __future__ import annotations

import asyncio

from sakhi.apps.worker.tasks.soul_reasoner import run_soul_reasoner


async def main() -> None:
    await run_soul_reasoner("YOUR_PERSON_UUID_HERE")


if __name__ == "__main__":
    asyncio.run(main())
