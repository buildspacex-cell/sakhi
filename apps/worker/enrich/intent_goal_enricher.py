from __future__ import annotations

import re

GOAL_RE = re.compile(r"\b(i (want|plan|aim|need) to)\s+(?P<title>[^.!?\n]{3,120})", re.I)


async def handle_intents_goals(db, person_id: str, episode_id: str) -> None:
    record = await db.fetchrow("select content from journal_entries where id=$1", episode_id)
    if not record:
        return
    text = record["content"] or ""
    match = GOAL_RE.search(text)
    if not match:
        return
    title = match.group("title").strip()
    await db.execute(
        """
        insert into goals (person_id, title, horizon, status, progress)
        values ($1,$2,'month','proposed',0)
        on conflict do nothing
        """,
        person_id,
        title,
    )
