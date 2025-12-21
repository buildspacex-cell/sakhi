from __future__ import annotations

import datetime as dt
import os
import json
import uuid
from typing import Any, Dict, Sequence

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.services.memory.memory_short_term import merge_into_short_term
from sakhi.apps.api.services.memory.deep_context import write_deep_context_recall
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.worker.utils.llm import extract_entities, sentiment_score
from sakhi.libs.embeddings import embed_text


def _coerce_vector(candidate: Any) -> list[float]:
    if isinstance(candidate, (list, tuple)):
        items: Sequence[Any] = candidate  # type: ignore[assignment]
    else:
        return []

    if items and isinstance(items[0], (list, tuple)):
        items = items[0]  # type: ignore[assignment]

    try:
        return [float(value) for value in items]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return []


async def ingest_journal_entry(entry: Dict[str, Any]) -> None:
    """
    Convert a journal entry into an episodic memory node and kick off
    the short-term / long-term consolidation pipeline.
    """

    entry_id = entry.get("id")
    candidate_id = entry.get("user_id") or entry.get("person_id")
    person_id = await resolve_person_id(candidate_id) or candidate_id
    text = entry.get("content") or entry.get("cleaned") or ""

    if not (entry_id and person_id and text):
        return

    vector = _coerce_vector(await embed_text(text))
    if not vector:
        return

    sentiment = sentiment_score(text)
    entities = extract_entities(text)
    created_ts = entry.get("ts")
    if isinstance(created_ts, dt.datetime):
        created_ts = created_ts.isoformat()
    elif not isinstance(created_ts, str):
        created_ts = dt.datetime.utcnow().isoformat()

    record = {
        "entry_id": str(entry_id),
        "text": text,
        "sentiment": sentiment,
        "entities": entities,
        "facets": entry.get("facets") or entry.get("facets_v2") or {},
        "mood": entry.get("mood"),
        "tags": entry.get("tags") or [],
        "layer": entry.get("layer"),
        "created_ts": created_ts,
        "embedding": vector,
    }

    # Episodic rows are created only via explicit promotion, not during ingest.
    await merge_into_short_term(str(person_id), record, vector)

    # Build deep context recall (Build 41)
    try:
        await write_deep_context_recall(
            person_id=str(person_id),
            turn_id=str(entry_id),
            thread_id=str(entry.get("thread_id")) if entry.get("thread_id") else None,
            text=text,
            vector=vector,
            sentiment=sentiment,
            entities=entities if isinstance(entities, list) else [],
            tags=record.get("tags"),
            facets=record.get("facets"),
        )
    except Exception as exc:  # pragma: no cover - best effort
        LOGGER = None
        try:
            import logging  # local import to avoid top-level dep
            LOGGER = logging.getLogger(__name__)
        except Exception:
            pass
        if LOGGER:
            LOGGER.warning("[DeepRecall] write failed for %s: %s", person_id, exc)
