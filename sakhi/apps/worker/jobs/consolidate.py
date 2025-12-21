from __future__ import annotations

from sakhi.apps.api.core.db import q


async def consolidate_person(pid: str) -> None:
    episodes = await q(
        """
        SELECT id, tags
        FROM episodes
        WHERE person_id = $1 AND ts > now() - interval '7 days'
        """,
        pid,
    )

    tag_counts: dict[str, int] = {}
    for episode in episodes:
        for tag in episode.get("tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag, count in sorted(tag_counts.items(), key=lambda item: -item[1])[:3]:
        await q(
            """
            INSERT INTO themes (person_id, name, scope, signals)
            VALUES ($1, $2, NULL, $3)
            ON CONFLICT DO NOTHING
            """,
            pid,
            tag,
            {"count": count},
        )

    if tag_counts.get("morning_focus", 0) >= 3:
        await q(
            """
            INSERT INTO facts (person_id, scope, key, value, confidence)
            VALUES ($1, 'values', 'prefers_mornings', '{"statement":"prefers mornings"}', 0.8)
            ON CONFLICT DO NOTHING
            """,
            pid,
        )
