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
    "visual": 0.9,          # Visual memories are highly relevant
    "visual_insight": 0.75,  # Insights from visual patterns
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

    # Visual memories - learned from images/documents
    try:
        visual_memories = await q(
            """
            SELECT vm.id, vm.memory_type, vm.subject, vm.learned_facts,
                   vm.source_description, vm.confidence, vm.embedding,
                   vm.first_seen_at, vm.times_seen,
                   m.description as media_description,
                   m.extracted_text
            FROM vision_memory vm
            LEFT JOIN media_attachments m ON m.id = vm.media_id
            WHERE vm.person_id = $1 AND vm.confidence >= 0.3
            ORDER BY vm.confidence DESC, vm.times_seen DESC
            LIMIT 50
            """,
            person_id,
        )

        for row in visual_memories or []:
            # Build text from visual memory
            facts = row.get("learned_facts") or []
            fact_texts = [f.get("fact", "") for f in facts if isinstance(f, dict)]
            text_parts = [
                f"[{row.get('memory_type', 'visual')}] {row.get('subject', '')}",
                row.get("source_description") or "",
                row.get("media_description") or "",
            ]
            text_parts.extend(fact_texts[:3])  # Top 3 facts
            full_text = " | ".join(filter(None, text_parts))

            sources.append(
                {
                    "type": "visual",
                    "id": row["id"],
                    "text": full_text[:500],
                    "vec": _parse_vec(row.get("embedding")),
                    "ts": row.get("first_seen_at"),
                    "confidence": row.get("confidence", 0.5),
                    "times_seen": row.get("times_seen", 1),
                    "media_description": row.get("media_description"),
                    "extracted_text": row.get("extracted_text"),
                }
            )
    except Exception as ve:
        LOGGER.debug("[Recall] Visual memory fetch failed (table may not exist): %s", ve)

    # Visual insights - patterns learned from images
    try:
        visual_insights = await q(
            """
            SELECT id, insight_type, insight, confidence, patterns,
                   first_observed_at, times_confirmed
            FROM visual_insights
            WHERE person_id = $1 AND confidence >= 0.4
            ORDER BY confidence DESC
            LIMIT 20
            """,
            person_id,
        )

        for row in visual_insights or []:
            patterns = row.get("patterns") or {}
            pattern_text = ""
            if patterns.get("recurring_objects"):
                pattern_text = f"Often sees: {', '.join(patterns['recurring_objects'][:5])}"

            sources.append(
                {
                    "type": "visual_insight",
                    "id": row["id"],
                    "text": f"[{row.get('insight_type', 'visual')}] {row.get('insight', '')} {pattern_text}",
                    "vec": [],
                    "ts": row.get("first_observed_at"),
                    "confidence": row.get("confidence", 0.5),
                }
            )
    except Exception as vie:
        LOGGER.debug("[Recall] Visual insights fetch failed (table may not exist): %s", vie)

    # Journal entries with media attachments
    try:
        journal_media = await q(
            """
            SELECT je.id, je.content, je.ts,
                   m.description as media_description,
                   m.extracted_text,
                   m.analysis,
                   jem.caption
            FROM journal_entries je
            JOIN journal_entry_media jem ON jem.entry_id = je.id
            JOIN media_attachments m ON m.id = jem.media_id
            WHERE je.user_id = $1
            ORDER BY je.ts DESC
            LIMIT 30
            """,
            person_id,
        )

        for row in journal_media or []:
            # Combine journal text with media context
            media_context = " | ".join(filter(None, [
                row.get("media_description"),
                row.get("caption"),
                (row.get("extracted_text") or "")[:200],
            ]))
            full_text = f"{row.get('content', '')[:200]} [Media: {media_context}]"

            sources.append(
                {
                    "type": "journal",  # Keep as journal but with media enrichment
                    "id": row["id"],
                    "text": full_text[:600],
                    "vec": [],  # Will use journal's embedding
                    "ts": row.get("ts"),
                    "has_media": True,
                    "media_description": row.get("media_description"),
                }
            )
    except Exception as jme:
        LOGGER.debug("[Recall] Journal media fetch failed (table may not exist): %s", jme)

    return sources


async def recall_advanced(
    person_id: str,
    query: str,
    *,
    k: int = 8,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    use_hybrid: bool = True,
) -> List[Dict[str, Any]]:
    """
    Advanced memory recall with hybrid search (vector + BM25 keyword).

    Hybrid search borrowed from OpenClaw:
    - vector_weight (0.7): Semantic similarity dominates
    - keyword_weight (0.3): Exact keyword matches get boost

    This ensures "Manali cabin" finds the exact mention, not just similar concepts.
    """
    from sakhi.apps.api.services.memory.bm25 import bm25_search_all, merge_hybrid_scores

    # 1. Get query embedding for vector search
    query_vec = await _get_embedding(query)

    # 2. Fetch all memory sources
    sources = await _fetch_sources(person_id)

    # 3. Get BM25 keyword scores if hybrid enabled
    keyword_scores: Dict[str, Dict[str, float]] = {}
    if use_hybrid and keyword_weight > 0:
        try:
            keyword_scores = await bm25_search_all(person_id, query, limit=k * 3)
            LOGGER.debug(
                "[Recall] BM25 found matches: journals=%d, reflections=%d, nodes=%d, facts=%d",
                len(keyword_scores.get("journal", {})),
                len(keyword_scores.get("reflection", {})),
                len(keyword_scores.get("node", {})),
                len(keyword_scores.get("fact", {})),
            )
        except Exception as e:
            LOGGER.warning("[Recall] BM25 search failed, falling back to vector-only: %s", e)
            keyword_scores = {}

    # 4. Score each source with hybrid scoring
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for src in sources:
        surface_weight = SURFACE_WEIGHTS.get(src["type"], 1.0)
        recency = _recency_weight(src.get("ts"))
        chunks = _chunk_text(src.get("text") or "")
        stored_vec = src.get("vec") or []

        # Get BM25 score for this source
        src_type = src["type"]
        src_id = str(src["id"])

        # Map source type to BM25 result key
        bm25_type_map = {
            "journal": "journal",
            "reflection": "reflection",
            "node": "node",
            "fact": "fact",
            "theme": "fact",  # themes search with facts
            "visual": "journal",  # visual memories don't have BM25 yet
            "visual_insight": "node",
        }
        bm25_key = bm25_type_map.get(src_type, src_type)
        bm25_score = keyword_scores.get(bm25_key, {}).get(src_id, 0.0)

        for chunk in chunks:
            # Hard rule: never embed stored rows at read-time.
            # If a source row does not already have a stored vector, skip it.
            if not stored_vec:
                continue

            vec = stored_vec
            vector_sim = _sim(query_vec, vec)

            # Hybrid score: combine vector and keyword
            if use_hybrid and bm25_score > 0:
                hybrid_sim = merge_hybrid_scores(
                    vector_sim, bm25_score, vector_weight, keyword_weight
                )
            else:
                hybrid_sim = vector_sim

            # Final score includes surface weight and recency
            final_score = hybrid_sim * surface_weight * recency

            scored.append(
                (
                    final_score,
                    {
                        "type": src_type,
                        "id": src_id,
                        "text": chunk,
                        "vec": vec,
                        "raw_similarity": vector_sim,
                        "keyword_score": bm25_score,
                        "hybrid_similarity": hybrid_sim,
                        "recency_weight": recency,
                        "surface_weight": surface_weight,
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


async def recall_with_keyword_boost(
    person_id: str,
    query: str,
    *,
    k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Recall optimized for exact keyword matches.

    Uses higher keyword weight (0.5) for queries that likely need exact matches,
    like names, places, restaurants, specific items.
    """
    return await recall_advanced(
        person_id,
        query,
        k=k,
        vector_weight=0.5,
        keyword_weight=0.5,
        use_hybrid=True,
    )


async def recall_semantic_only(
    person_id: str,
    query: str,
    *,
    k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Recall using only vector similarity (no BM25).

    Useful for conceptual queries like "times I felt happy" where
    exact keywords matter less than semantic meaning.
    """
    return await recall_advanced(
        person_id,
        query,
        k=k,
        use_hybrid=False,
    )


__all__ = [
    "recall_advanced",
    "recall_with_keyword_boost",
    "recall_semantic_only",
    "build_recall_context",
    "memory_recall",
    "unified_recall",
]
