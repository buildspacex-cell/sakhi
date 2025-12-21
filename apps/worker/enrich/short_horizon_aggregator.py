from __future__ import annotations

import json


async def update_short_horizon(db, person_id: str) -> None:
    layers = await db.fetch(
        """
        select layer, count(*) n from journal_entries
        where user_id=$1 and created_at > now() - interval '7 days'
        group by layer
        """,
        person_id,
    )

    tags = await db.fetch(
        """
        select t, count(*) n from (
            select unnest(tags) as t from journal_entries
            where user_id=$1 and created_at > now() - interval '7 days' and array_length(tags,1) is not null
        ) s group by t order by n desc limit 12
        """,
        person_id,
    )

    mood = await db.fetchrow(
        "select avg(mood_score) m from journal_entries where user_id=$1 and created_at>now()-interval '7 days'",
        person_id,
    )

    await db.execute(
        """
        insert into short_horizon (person_id, recent_layers, recent_tags, recent_intents, avg_mood_7d, open_questions)
        values ($1,$2,$3,$4,$5,'[]')
        on conflict (person_id)
        do update set asof=now(), recent_layers=excluded.recent_layers,
                      recent_tags=excluded.recent_tags,
                      recent_intents=excluded.recent_intents,
                      avg_mood_7d=excluded.avg_mood_7d
        """,
        person_id,
        json.dumps([{"layer": layer["layer"], "n": layer["n"]} for layer in layers]),
        json.dumps([{"tag": tag["t"], "n": tag["n"]} for tag in tags]),
        json.dumps([]),
        float(mood["m"]) if mood and mood["m"] is not None else None,
    )
