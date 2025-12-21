from __future__ import annotations

import asyncio

from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.worker.tasks.update_relationship_arcs import update_relationship_arcs
from sakhi.apps.api.services.memory.graph_reinforcement import reinforce_recall_graph
from sakhi.apps.api.services.memory.consolidation import consolidate_memory


async def memory_event_fanout(event: dict) -> None:
    """
    Fan-out handler for memory.entry.observed events.
    """

    person_id = event.get("person_id")
    entry_id = event.get("entry_id")
    text = event.get("text") or ""
    layer = event.get("layer")

    if person_id and text:
        asyncio.create_task(update_relationship_arcs(person_id, text))
        asyncio.create_task(consolidate_memory(person_id))

    if person_id and entry_id:
        asyncio.create_task(reinforce_recall_graph(person_id, text, []))

    if layer == "journal" and entry_id and person_id:
        asyncio.create_task(
            ingest_journal_entry(
                {
                    "id": entry_id,
                    "user_id": person_id,
                    "content": text,
                }
            )
        )
