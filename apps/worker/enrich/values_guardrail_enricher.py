from __future__ import annotations

import json
import re

NO_MEETINGS = re.compile(r"no meetings after\s+(\d{1,2}):?(\d{2})?", re.I)


async def handle_values(db, person_id: str, episode_id: str) -> None:
    record = await db.fetchrow("select content from journal_entries where id=$1", episode_id)
    if not record:
        return
    text = record["content"] or ""
    match = NO_MEETINGS.search(text)
    if not match:
        return

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    value_json = json.dumps({"no_meetings_after": f"{hour:02d}:{minute:02d}"})

    await db.execute(
        """
        insert into preferences (person_id, scope, key, value, confidence)
        values ($1,'values','evening_boundary',$2,0.8)
        on conflict do nothing
        """,
        person_id,
        value_json,
    )
