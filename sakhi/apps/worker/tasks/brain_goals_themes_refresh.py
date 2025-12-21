from __future__ import annotations

import asyncio
import datetime as dt
import logging
import math
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import embed_normalized
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


def _norm(vec: List[float]) -> List[float]:
    mag = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / mag for x in vec]


def _cos_sim(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) + 1e-8)


def _cluster_entries(entries: List[Dict[str, Any]], threshold: float = 0.18) -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    for entry in entries:
        vec = entry.get("vector") or []
        if not vec:
            continue
        placed = False
        for cluster in clusters:
            sim = _cos_sim(cluster["centroid"], vec)
            if 1 - sim < threshold:
                cluster["items"].append(entry)
                # update centroid
                items = cluster["items"]
                centroid = [0.0 for _ in range(len(vec))]
                for itm in items:
                    v = itm.get("vector") or []
                    for i in range(len(v)):
                        centroid[i] += v[i]
                cluster["centroid"] = _norm([c / len(items) for c in centroid])
                placed = True
                break
        if not placed:
            clusters.append({"centroid": _norm(vec), "items": [entry]})
    return clusters


async def _prepare_entries(person_id: str) -> List[Dict[str, Any]]:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=90)
    rows = await q(
        """
        SELECT id, text, vector_vec, triage
        FROM memory_episodic
        WHERE person_id = $1 AND updated_at >= $2
        """,
        person_id,
        cutoff,
    )
    entries: List[Dict[str, Any]] = []
    for row in rows or []:
        text = row.get("text") or ""
        vec = row.get("vector_vec") or []
        if not vec and text:
            vec = await embed_normalized(text)
        entries.append(
            {
                "id": row.get("id"),
                "text": text,
                "vector": vec,
                "triage": row.get("triage") or {},
            }
        )
    return entries


def _title_for_cluster(cluster: Dict[str, Any]) -> str:
    first = (cluster["items"][0].get("text") or "goal").strip()
    return (first[:40] or "goal cluster").strip()


async def run_brain_goals_themes_refresh(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    try:
        entries = await _prepare_entries(person_id)
    except Exception as exc:
        logger.warning("goals_themes_refresh load failed person=%s err=%s", person_id, exc)
        return {"error": str(exc)}

    clusters = _cluster_entries(entries)
    summaries: List[Tuple[str, Dict[str, Any]]] = []
    for cluster in clusters:
        title = _title_for_cluster(cluster)
        items = cluster["items"]
        confidence = round(min(1.0, 0.5 + 0.05 * len(items)), 2)
        supporting_ids = [itm.get("id") for itm in items if itm.get("id")]
        identity_alignment = 0.6
        try:
            await dbexec(
                """
                INSERT INTO brain_goals_themes (
                    person_id,
                    cluster_title,
                    cluster_vector,
                    supporting_entry_ids,
                    confidence,
                    time_window,
                    emotional_tone,
                    value_mapping,
                    identity_alignment
                )
                VALUES ($1,$2,$3,$4,$5,'90d','{}'::jsonb,'{}'::jsonb,$6)
                ON CONFLICT (person_id, cluster_title) DO UPDATE
                SET cluster_vector = EXCLUDED.cluster_vector,
                    supporting_entry_ids = EXCLUDED.supporting_entry_ids,
                    confidence = EXCLUDED.confidence,
                    updated_at = now(),
                    identity_alignment = EXCLUDED.identity_alignment
                """,
                person_id,
                title,
                cluster["centroid"],
                supporting_ids,
                confidence,
                identity_alignment,
            )
        except Exception as exc:
            logger.warning("goals_themes_refresh upsert failed person=%s title=%s err=%s", person_id, title, exc)
        summaries.append(
            (
                title,
                {
                    "confidence": confidence,
                    "supporting_ids": supporting_ids,
                    "identity_alignment": identity_alignment,
                },
            )
        )

    # Update personal_model long_term
    try:
        pm = await q("SELECT long_term FROM personal_model WHERE person_id = $1", person_id, one=True)
        long_term = pm.get("long_term") if pm else {}
        life_themes = []
        active_goals_map = {}
        alignments = []
        for title, meta in summaries:
            life_themes.append({"title": title, "confidence": meta["confidence"], "updated_at": dt.datetime.utcnow().isoformat()})
            active_goals_map[title] = meta["supporting_ids"]
            alignments.append(meta["identity_alignment"])
        if long_term is None:
            long_term = {}
        long_term["life_themes"] = life_themes
        long_term["active_goals_map"] = active_goals_map
        if alignments:
            long_term["identity_alignment_score"] = sum(alignments) / len(alignments)
        await dbexec(
            """
            UPDATE personal_model
            SET long_term = $2::jsonb, updated_at = now()
            WHERE person_id = $1
            """,
            person_id,
            long_term,
        )
    except Exception as exc:
        logger.warning("goals_themes_refresh personal_model update failed person=%s err=%s", person_id, exc)

    return {"clusters": len(clusters)}


def enqueue_brain_goals_themes_refresh(person_id: str) -> None:
    try:
        asyncio.create_task(run_brain_goals_themes_refresh(person_id))
    except Exception:
        pass


__all__ = ["run_brain_goals_themes_refresh", "enqueue_brain_goals_themes_refresh", "_cluster_entries"]
