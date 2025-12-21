from __future__ import annotations

import os
from typing import Optional

from sakhi.apps.api.core.db import q

DECAY_DAYS = float(os.getenv("THEME_DECAY_DAYS", "14.0"))


async def decay_themes(user_id: Optional[str] = None) -> None:
    """Apply exponential decay to theme salience based on recency."""

    await q(
        """
        UPDATE journal_themes jt
        SET metrics = jsonb_set(
            metrics,
            '{salience}',
            to_jsonb(
                GREATEST(
                    0.0,
                    COALESCE((metrics->>'salience')::numeric, 0)
                    * exp(
                        -GREATEST(
                            0,
                            EXTRACT(EPOCH FROM (now() - COALESCE((metrics->>'last_seen')::timestamptz, now()))) / 86400.0
                        ) / $1
                    )
                )
            )
        )
        WHERE ($2::uuid IS NULL OR jt.user_id = $2)
        """,
        DECAY_DAYS,
        user_id,
    )


async def recompute_significance(user_id: Optional[str] = None) -> None:
    """Refresh theme significance with light reinforcement based on engagement."""

    await q(
        """
        UPDATE journal_themes jt
        SET metrics = jsonb_set(
            metrics,
            '{significance}',
            to_jsonb(
                LEAST(
                    1.0,
                    COALESCE((metrics->>'significance')::numeric, 0) * 0.98
                    + 0.02 * ln(1 + COALESCE((metrics->>'mentions')::int, 0))
                    + 0.02 * COALESCE((metrics->>'emotion_avg')::numeric, 0)
                    + 0.02 * COALESCE((metrics->>'impact')::numeric, 0)
                )
            )
        )
        WHERE ($1::uuid IS NULL OR jt.user_id = $1)
        """,
        user_id,
    )


async def mark_surfaced(user_id: str, aspect_key: str) -> None:
    """Record when a theme or aspect was surfaced to manage fatigue."""

    await q(
        """
        INSERT INTO surfaced_aspects (user_id, aspect_key, last_surfaced_at)
        VALUES ($1, $2, now())
        ON CONFLICT (user_id, aspect_key)
        DO UPDATE SET last_surfaced_at = EXCLUDED.last_surfaced_at
        """,
        user_id,
        aspect_key,
    )


__all__ = ["decay_themes", "recompute_significance", "mark_surfaced"]
