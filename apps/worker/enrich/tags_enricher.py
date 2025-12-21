from __future__ import annotations

LEX = {
    "gym": ["gym", "workout", "exercise"],
    "focus": ["focus", "deep work", "study"],
    "finance": ["budget", "emi", "₹", "inr", "pay", "buy", "down payment"],
    "sleep": ["sleep", "insomnia", "nap", "rest"],
}


async def handle_tags(db, person_id: str, episode_id: str) -> None:
    record = await db.fetchrow("select content, tags from journal_entries where id=$1", episode_id)
    if not record:
        return
    text = (record["content"] or "").lower()
    tags = set(record["tags"] or [])

    for tag, keywords in LEX.items():
        if any(keyword in text for keyword in keywords):
            tags.add(tag)

    await db.execute(
        """
        INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
        VALUES ($1, 'context', jsonb_build_object('tags', to_jsonb($2::text[])), 'structural', 'tags_enricher')
        """,
        episode_id,
        list(tags),
    )
