from __future__ import annotations

import json


async def handle_aspects(db, person_id: str, episode_id: str) -> None:
    count_24 = await db.fetchrow(
        "select count(*) c from journal_entries where user_id=$1 and created_at>now()-interval '24 hours'",
        person_id,
    )
    slack_hours = max(0.0, 4.0 - float(count_24["c"]) * 0.25)
    await _upsert_feat(
        db,
        person_id,
        "time",
        "time_slack",
        {"score": min(1.0, slack_hours / 4.0), "hours": slack_hours},
    )

    mood = await db.fetchrow(
        "select avg(mood_score) m from journal_entries where user_id=$1 and created_at>now()-interval '7 days'",
        person_id,
    )
    energy_score = 0.5 + 0.5 * float(mood["m"] or 0.0)
    await _upsert_feat(db, person_id, "energy", "energy_slack", {"score": max(0.0, min(1.0, energy_score))})

    await _upsert_feat(db, person_id, "finance", "money_feasibility", {"score": 0.5}, conf=0.3)

    pref = await db.fetchrow(
        "select 1 from preferences where person_id=$1 and confidence>=0.75 limit 1",
        person_id,
    )
    await _upsert_feat(
        db,
        person_id,
        "values",
        "values_alignment",
        {"score": 0.7 if pref else 0.5},
    )


async def _upsert_feat(db, pid: str, aspect: str, key: str, value: dict, conf: float = 0.7) -> None:
    await db.execute(
        """
        insert into aspect_features (person_id, aspect, feature_key, value)
        values ($1,$2,$3,$4)
        on conflict (person_id, aspect, feature_key)
        do update set value=excluded.value, updated_at=now()
        """,
        pid,
        aspect,
        f"{aspect}.{key}",
        json.dumps(value),
    )
