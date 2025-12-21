from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Tuple
import numpy as np

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.memory.graph_reinforcement import reinforce_recall_graph
from sakhi.libs.embeddings import embed_text

LOGGER = logging.getLogger(__name__)

SURFACE_WEIGHTS = {
    "journal": 1.0,
    "reflection": 0.85,
    "theme": 0.6,
    "fact": 0.65,
    "node": 0.55,
}
RECENCY_HALFLIFE_DAYS = 45


async def _get_embedding(text: str) -> List[float]:
    try:
        return await embed_text(text)
    except Exception as exc:
        LOGGER.error("[Recall] Embedding failed: %s", exc)
        return [0.0] * 1536


def _parse_vec(raw: Any) -> List[float]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str) and raw.startswith("[") and raw.endswith("]"):
        body = raw[1:-1].strip()
        if not body:
            return []
        try:
            return [float(piece) for piece in body.split(",")]
        except ValueError:
            return []
    return []


def _sim(a: List[float], b: List[float]) -> float:
    try:
        va = np.array(a, dtype=float)
        vb = np.array(b, dtype=float)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)
    except Exception:
        return 0.0


def _recency_weight(ts: Any) -> float:
    import datetime

    if not ts:
        return 1.0
    if isinstance(ts, str):
        try:
            ts = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return 1.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    age_days = (now - ts).days
    return float(0.5 ** (age_days / RECENCY_HALFLIFE_DAYS))


def _chunk_text(text: str, max_len: int = 280) -> List[str]:
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        chunks.append(text[start:end])
        start = end
    return chunks


def _diversity_filter(scored_items: List[Tuple[float, Dict[str, Any]]], top_k: int) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    vecs: List[List[float]] = []

    for score, item in scored_items:
        if len(selected) >= top_k:
            break
        vec = item.get("vec")
        if not vec:
            continue
        diverse = True
        for prev in vecs:
            if _sim(prev, vec) > 0.92:
                diverse = False
                break
        if diverse:
            selected.append({"score": score, **item})
            vecs.append(vec)
    if len(selected) < top_k:
        for score, item in scored_items:
            if len(selected) >= top_k:
                break
            candidate = {"score": score, **item}
            if candidate not in selected:
                selected.append(candidate)
    return selected[:top_k]


async def _fetch_sources(person_id: str) -> List[Dict[str, Any]]:
    journals = await q(
        """
        SELECT je.id, je.content, je.ts,
               emb.embedding_vec AS vec
        FROM journal_entries je
        JOIN journal_embeddings emb ON je.id = emb.entry_id
        WHERE je.user_id = $1
        ORDER BY je.ts DESC
        LIMIT 100
        """,
        person_id,
    )

    reflections = await q(
        """
        SELECT id, content, theme, created_at
        FROM reflections
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 100
        """,
        person_id,
    )

    themes = await q(
        """
        SELECT id, name, description
        FROM themes
        WHERE person_id = $1
        """,
        person_id,
    )

    facts = await q(
        """
        SELECT id, key, value
        FROM facts
        WHERE person_id = $1
        LIMIT 100
        """,
        person_id,
    )

    nodes = await q(
        """
        SELECT id, node_kind, label, data
        FROM memory_nodes
        WHERE person_id = $1
        """,
        person_id,
    )

    sources: List[Dict[str, Any]] = []

    for row in journals:
        sources.append(
            {
                "type": "journal",
                "id": row["id"],
                "text": row.get("content") or "",
                "vec": _parse_vec(row.get("vec")),
                "ts": row.get("ts"),
            }
        )

    for row in reflections:
        sources.append(
            {
                "type": "reflection",
                "id": row["id"],
                "text": f"{row.get('content') or ''} [{row.get('theme') or 'general'}]",
                "vec": [],
                "ts": row.get("created_at"),
            }
        )

    for row in themes:
        sources.append(
            {
                "type": "theme",
                "id": row["id"],
                "text": f"{row.get('name') or ''} — {row.get('description') or ''}",
                "vec": [],
                "ts": None,
            }
        )

    for row in facts:
        sources.append(
            {
                "type": "fact",
                "id": row["id"],
                "text": f"{row.get('key')}: {row.get('value')}",
                "vec": [],
                "ts": None,
            }
        )

    for row in nodes:
        sources.append(
            {
                "type": "node",
                "id": row["id"],
                "text": f"{row.get('node_kind')}: {row.get('label')}",
                "vec": [],
                "ts": None,
            }
        )

    return sources


async def recall_advanced(person_id: str, query: str, *, k: int = 8) -> List[Dict[str, Any]]:
    query_vec = await _get_embedding(query)
    sources = await _fetch_sources(person_id)
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for src in sources:
        weight = SURFACE_WEIGHTS.get(src["type"], 1.0)
        recency = _recency_weight(src.get("ts"))
        chunks = _chunk_text(src.get("text") or "")
        stored_vec = src.get("vec") or []
        for chunk in chunks:
            # Hard rule: never embed stored rows at read-time.
            # If a source row does not already have a stored vector, skip it.
            if not stored_vec:
                continue
            vec = stored_vec
            sim = _sim(query_vec, vec)
            final_score = sim * weight * recency
            scored.append(
                (
                    final_score,
                    {
                        "type": src["type"],
                        "id": src["id"],
                        "text": chunk,
                        "vec": vec,
                        "raw_similarity": sim,
                        "recency_weight": recency,
                        "surface_weight": weight,
                    },
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    top = _diversity_filter(scored, top_k=k)

    if top:
        try:
            asyncio.create_task(reinforce_recall_graph(person_id, query, top))
        except RuntimeError:
            await reinforce_recall_graph(person_id, query, top)

    return top


async def build_recall_context(person_id: str, text: str) -> str:
    top_items = await recall_advanced(person_id, text, k=5)
    if not top_items:
        return "Relevant memory: none."

    bullets = [f"- [{item['type']}] {item['text']} (s={item['score']:.2f})" for item in top_items]
    long_context = "Relevant memory:\n" + "\n".join(bullets)

    if len(long_context) < 800:
        return long_context

    from sakhi.apps.api.core.llm import call_llm

    response = await call_llm(
        messages=[
            {"role": "system", "content": "Summarize the recall data into concise memory hints."},
            {"role": "user", "content": long_context},
        ],
        model="gpt-4o-mini",
        person_id=person_id,
    )

    if isinstance(response, dict):
        summary = response.get("reply") or response.get("text") or ""
    else:
        summary = str(response)
    return summary[:1000]


async def memory_recall(person_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Compatibility helper for Patch DD: returns top-N recall items.
    """

    items = await recall_advanced(person_id, query, k=limit)
    return [
        {
            "id": item.get("id"),
            "type": item.get("type"),
            "text": item.get("text"),
            "score": item.get("score"),
        }
        for item in items
    ]


async def unified_recall(person_id: str, query: str, *, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Highest-level recall entry:
      1. Advanced recall
      2. Falls back to hybrid journal recall (legacy) if empty
    """

    top = await recall_advanced(person_id, query, k=limit)
    if top:
        return top
    try:
        from sakhi.libs.retrieval.recall import recall as low_recall

        embedding = await _get_embedding(query)
        rows = await low_recall(person_id, query, k=limit, embedding=embedding)
        return rows
    except Exception as exc:
        LOGGER.warning("[Recall] unified fallback failed: %s", exc)
        return []


__all__ = ["recall_advanced", "build_recall_context", "memory_recall", "unified_recall"]
