# Reasoning Engine (Patch Z)
# ----------------------------------------------------------
# Provides unified reasoning over:
#  - Memory nodes
#  - Embeddings
#  - Observations (journal, intents, reflections)
#  - Memory graph (edges)
#  - LLM fusion layer
#
# Output: structured "reasoning bundle":
#  {
#     insights: [],
#     contradictions: [],
#     opportunities: [],
#     open_loops: []
#  }
# ----------------------------------------------------------

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.db import q as db_q
from sakhi.apps.api.services.memory.recall import build_recall_context
from sakhi.libs.embeddings import embed_text
from sakhi.libs.json_utils import extract_json_block
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)

# ------------------------------
# Embedding utilities
# ------------------------------

async def _embed_query(text: str) -> List[float]:
    if not text:
        return [0.0] * 1536
    try:
        return await embed_text(text)
    except Exception as exc:
        LOGGER.error("[ReasoningEngine] Embedding failed: %s", exc)
        return [0.0] * 1536


# ------------------------------
# Retrieval layer
# ------------------------------

async def fetch_similar_nodes(person_id: str, query_vec: List[float], limit: int = 20):
    rows = await dbfetch(
        """
        SELECT id, node_kind, label, data, embed_vec
        FROM memory_nodes
        WHERE person_id = $1
          AND embed_vec IS NOT NULL
        ORDER BY embed_vec <-> $2
        LIMIT $3
        """,
        person_id,
        query_vec,
        limit,
    )
    return rows or []


async def fetch_recent_observations(person_id: str, limit: int = 30):
    return await dbfetch(
        """
        SELECT id, lens, kind, payload, created_at
        FROM observations
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )


async def fetch_related_edges(person_id: str, node_ids: List[str]):
    if not node_ids:
        return []
    return await dbfetch(
        """
        SELECT id, from_node, to_node, relation, weight
        FROM memory_edges
        WHERE person_id = $1
          AND (from_node = ANY($2) OR to_node = ANY($2))
        """,
        person_id,
        node_ids,
    )


# ------------------------------
# Fusion (LLM reasoning)
# ------------------------------

async def _run_llm_fusion(
    person_id: str,
    query: str,
    retrieved_nodes: List[Dict[str, Any]],
    recent_obs: List[Dict[str, Any]],
    related_edges: List[Dict[str, Any]],
    memory_context: str | None = None,
) -> Dict[str, Any]:
    """
    LLM fusion step over:
      - query
      - similar nodes
      - recent observations
      - related memory graph edges
    """
    system_prompt = (
        "You are the reasoning engine for Sakhi.\n"
        "Given user memory nodes, observations, and graph relationships, "
        "extract structured reasoning.\n\n"
        "Return ONLY valid JSON with keys:\n"
        "  insights: list of strings\n"
        "  contradictions: list of strings\n"
        "  opportunities: list of strings\n"
        "  open_loops: list of strings\n"
    )

    payload = {
        "query": query,
        "retrieved_nodes": retrieved_nodes,
        "recent_observations": recent_obs,
        "related_edges": related_edges,
        "memory_context": memory_context,
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    resp = await call_llm(
        messages=messages,
        person_id=person_id,
        model="gpt-4o-mini",
    )

    raw = resp if isinstance(resp, str) else json.dumps(resp)
    block = extract_json_block(raw)

    try:
        return json.loads(block)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("[ReasoningEngine] LLM fusion JSON parse failed: %s", exc)
        return {
            "insights": [],
            "contradictions": [],
            "opportunities": [],
            "open_loops": [],
        }


# ------------------------------
# Public entrypoint
# ------------------------------

async def run_reasoning(person_id: str, query: str, memory_context: str | None = None) -> Dict[str, Any]:
    """
    Main external entrypoint for reasoning.
    """
    LOGGER.info("[ReasoningEngine] Running reasoning for %s: %s", person_id, query)

    if memory_context is None:
        memory_context = await build_recall_context(person_id, query)
        summary_row = await db_q(
            """
            SELECT summary
            FROM meta_reflections
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
        if summary_row:
            memory_context = (
                f"Reflection Summary:\n{summary_row[0]['summary']}\n\n{memory_context or ''}"
            )

    query_vec = await _embed_query(query)
    nodes = await fetch_similar_nodes(person_id, query_vec)
    recent_obs = await fetch_recent_observations(person_id)
    node_ids = [n.get("id") for n in nodes if n.get("id")]
    edges = await fetch_related_edges(person_id, node_ids)
    result = await _run_llm_fusion(
        person_id,
        query,
        nodes,
        recent_obs,
        edges,
        memory_context=memory_context,
    )

    reflection_signal = ""
    if memory_context and "Reflection Summary" in memory_context:
        try:
            reflection_signal = (
                memory_context.split("Reflection Summary:", 1)[1]
                .split("Relevant memory", 1)[0]
                .strip()
            )
        except Exception:
            reflection_signal = ""

    return {
        "insights": result.get("insights", []),
        "contradictions": result.get("contradictions", []),
        "opportunities": result.get("opportunities", []),
        "open_loops": result.get("open_loops", []),
        "reflection_signal": reflection_signal,
    }


__all__ = [
    "run_reasoning",
    "fetch_similar_nodes",
    "fetch_recent_observations",
    "fetch_related_edges",
]
