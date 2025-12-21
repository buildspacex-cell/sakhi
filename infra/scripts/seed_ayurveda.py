"""Seed minimal Ayurvedic graph data for local experimentation."""

from __future__ import annotations

import asyncio
from typing import Sequence, Tuple

from sakhi.libs.schemas.db import get_async_pool

NODE_PAYLOADS: Sequence[Tuple[str, str, dict]] = [
    ("dosha", "vata", {"qualities": ["light", "dry"]}),
    ("dosha", "pitta", {"qualities": ["hot", "sharp"]}),
    ("dosha", "kapha", {"qualities": ["heavy", "cool"]}),
    ("food", "warm soups", {"pacifies": ["vata"], "season": "winter"}),
    ("food", "spicy curries", {"aggravates": ["pitta"], "season": "summer"}),
    ("habit", "late-night screen time", {"aggravates": ["vata"], "phase": "evening"}),
    ("habit", "midday intense workouts", {"aggravates": ["pitta"], "phase": "midday"}),
    ("habit", "slow heavy breakfast", {"aggravates": ["kapha"], "phase": "morning"}),
]


async def main() -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            for kind, name, payload in NODE_PAYLOADS:
                await connection.execute(
                    """
                    INSERT INTO ay_nodes (kind, name, attrs)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (kind, name) DO NOTHING
                    """,
                    kind,
                    name,
                    payload,
                )


if __name__ == "__main__":
    asyncio.run(main())
