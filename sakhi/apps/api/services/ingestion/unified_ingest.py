from __future__ import annotations

import datetime as dt
import asyncio
import uuid
import hashlib
import json
from typing import Any, Dict, Optional, List

from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion
from sakhi.apps.api.services.mind_engine import compute as compute_mind
from sakhi.apps.api.services.workers.context_refresh_worker import refresh_context
from sakhi.apps.api.services.soul_engine import compute as compute_soul
from sakhi.apps.api.services.identity_graph_engine import build as build_identity_graph
from sakhi.apps.worker.tasks import soul_worker
from sakhi.apps.worker.tasks import soul_extract_worker, soul_refresh_worker
from sakhi.apps.services import micro_goals_service
from sakhi.apps.engine.hands import weaver
from sakhi.apps.intent_engine import evolution as intent_evolution
from sakhi.apps.engine.emotion_loop import engine as emotion_loop_engine
from sakhi.apps.services.narrative import narrative_templates
SOUL_KEYWORDS = (
    "purpose",
    "identity",
    "meaning",
    "i am",
    "i want to become",
    "i care about",
    "matters to me",
)
from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.services.memory.personal_model import update_personal_model
from sakhi.libs.embeddings import embed_normalized
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.services.memory.stm_config import compute_expires_at
from sakhi.apps.api.services.memory.memory_short_term import cleanup_expired_short_term
from datetime import datetime, timezone

# simple in-process latching to avoid duplicate ingestion on same entry_id
_processed_fast: set[str] = set()
_processed_heavy: set[str] = set()


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_soul_relevant(text: str) -> bool:
    lower = (text or "").lower()
    return any(key in lower for key in SOUL_KEYWORDS)


BODY_KEYWORDS = ["tired", "exhausted", "fatigue", "sleepy", "headache", "body", "pain"]
MIND_KEYWORDS = ["focused", "overwhelmed", "confused", "distracted", "mental"]
ENERGY_KEYWORDS = ["energized", "motivated", "drained", "low energy", "flat"]

async def _existing_vector(person_id: str, content_hash: str) -> Optional[List[float]]:
    if not content_hash:
        return None
    for sql in (
        "SELECT embedding_vec AS vec FROM journal_embeddings WHERE content_hash = $1 AND entry_id IN (SELECT id FROM journal_entries WHERE user_id = $2) LIMIT 1",
        "SELECT vector_vec AS vec FROM memory_short_term WHERE content_hash = $1 AND user_id = $2 LIMIT 1",
        "SELECT vector_vec AS vec FROM memory_episodic WHERE content_hash = $1 AND user_id = $2 LIMIT 1",
    ):
        row = await q(sql, content_hash, person_id, one=True)
        if row and row.get("vec"):
            return row["vec"]
    return None


async def ingest_fast(
    *,
    person_id: str,
    text: str,
    layer: str,
    ts: dt.datetime,
    session_id: Optional[str] = None,
    entry_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    FAST ingestion layer
    """

    if entry_id and entry_id in _processed_fast:
        return {"skipped": True, "reason": "duplicate_fast_ingest"}

    person_id = await resolve_person_id(person_id) or person_id

    normalized = _normalize_text(text)
    content_hash = _hash_text(normalized)
    vec = await _existing_vector(person_id, content_hash)
    if not vec:
        vec = await embed_normalized(normalized)
        try:
            await dbexec(
                """
                INSERT INTO journal_embeddings (entry_id, model, embedding_vec, content_hash, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (entry_id) DO UPDATE SET content_hash = EXCLUDED.content_hash, embedding_vec = EXCLUDED.embedding_vec
                """,
                entry_id or session_id or str(uuid.uuid4()),
                "text-embedding-3-small",
                vec,
                content_hash,
            )
        except Exception:
            pass

    return {
        "embedding": vec,
        "content_hash": content_hash,
        "normalized_text": normalized,
        "entry_id": entry_id,
        "session_id": session_id,
        "layer": layer,
    }


async def ingest_heavy(
    *,
    person_id: str,
    entry_id: Optional[str],
    text: Optional[str] = None,
    ts: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    """
    HEAVY ingestion layer: normalize + dedup + canonical memory writes
    """

    if entry_id and entry_id in _processed_heavy:
        return {"skipped": True, "reason": "duplicate_heavy_ingest"}

    entry_id = entry_id or str(uuid.uuid4())

    # Best-effort eviction before inserting new STM rows.
    try:
        await cleanup_expired_short_term()
    except Exception:
        pass

    person_id = await resolve_person_id(person_id) or person_id
    if text is None:
        row = await q(
            "SELECT content, layer FROM journal_entries WHERE id = $1",
            entry_id,
            one=True,
        )
        if not row:
            return {"error": "entry not found"}
        text = row["content"]
        layer = row.get("layer") or "journal"
    else:
        layer = "journal"

    ts = ts or dt.datetime.utcnow()
    triage = extract(text, ts)
    expires_at = compute_expires_at(ts)
    normalized = _normalize_text(text)
    content_hash = _hash_text(normalized)
    lower_intent = ""
    if isinstance(triage, dict):
        lower_intent = (triage.get("intent") or triage.get("intent_type") or "").lower()
    mood = (triage.get("slots") or {}).get("mood_affect") if isinstance(triage, dict) else {}
    sentiment = float((mood or {}).get("score") or 0)
    body_score = sum(1 for k in BODY_KEYWORDS if k in normalized)
    mind_score = sum(1 for k in MIND_KEYWORDS if k in normalized)
    energy_score = sum(1 for k in ENERGY_KEYWORDS if k in normalized) + (1 if sentiment > 0.2 else -1 if sentiment < -0.2 else 0)
    wellness_tags = {
        "body": body_score,
        "mind": mind_score,
        "emotion": sentiment,
        "energy": energy_score,
    }
    try:
        await intent_evolution.evolve(person_id, lower_intent, sentiment)
    except Exception:
        pass
    try:
        emotion_loop_state = await emotion_loop_engine.compute_emotion_loop_for_person(person_id)
    except Exception:
        emotion_loop_state = {}
    try:
        await intent_evolution.evolve(person_id, lower_intent, sentiment)
    except Exception:
        pass

    vec = await _existing_vector(person_id, content_hash)
    if not vec:
        vec = await embed_normalized(normalized)
        try:
            await dbexec(
                """
                INSERT INTO journal_embeddings (entry_id, model, embedding_vec, content_hash, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (entry_id) DO UPDATE SET content_hash = EXCLUDED.content_hash, embedding_vec = EXCLUDED.embedding_vec
                """,
                entry_id or str(uuid.uuid4()),
                "text-embedding-3-small",
                vec,
                content_hash,
            )
        except Exception:
            pass

    existing_st = await q(
        "SELECT 1 FROM memory_short_term WHERE user_id = $1 AND entry_id = $2 LIMIT 1",
        person_id,
        entry_id,
        one=True,
    )
    if not existing_st:
        await dbexec(
            """
            INSERT INTO memory_short_term (id, user_id, entry_id, text, layer, expires_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """,
            str(uuid.uuid4()),
            person_id,
            entry_id,
            text or "",
            layer,
            expires_at,
        )

    # Episodic rows are now created only via explicit promotion, not ingest-time dual writes.

    # compute lightweight emotion/mind/soul summaries
    emotion_summary = await compute_emotion(person_id)
    mind_summary = await compute_mind(person_id)
    soul_summary = await compute_soul(person_id)
    identity_graph = await build_identity_graph(person_id)

    layer_overrides_payload = {
        "emotion": emotion_summary,
        "mind": mind_summary,
    }
    if soul_summary and soul_summary.get("signal_count", 0) >= 2:
        layer_overrides_payload["soul"] = {
            k: v for k, v in soul_summary.items() if k != "signal_count"
        }
    # identity graph lives outside layers; patched into long_term below

    personal_model_update = await update_personal_model(
        person_id,
        {
            "text": normalized,
            "layer": layer,
            "entry_id": entry_id,
            "content_hash": content_hash,
        },
        vector=vec,
        layer_overrides=layer_overrides_payload,
    )

    try:
        await dbexec(
            """
            INSERT INTO memory_context_cache (person_id)
            VALUES ($1)
            ON CONFLICT (person_id) DO NOTHING
            """,
            person_id,
        )
    except Exception:
        pass

    # Patch identity_graph into personal_model
    if personal_model_update and identity_graph:
        long_term = personal_model_update.get("long_term") or {}
        long_term["identity_graph"] = identity_graph
        await dbexec(
            """
            UPDATE personal_model
            SET long_term = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(long_term, ensure_ascii=False),
        )

    try:
        asyncio.create_task(refresh_context(person_id))
    except Exception:
        pass

    if lower_intent in {"plan_intent", "task_intent", "action_intent"}:
        try:
            await micro_goals_service.create_micro_goals(person_id, text or "")
        except Exception:
            pass

    if _is_soul_relevant(normalized):
        try:
            soul_worker.enqueue(person_id)
        except Exception:
            pass

    if lower_intent in {"task_intent", "action_intent"}:
        try:
            await weaver.assign(person_id, text or "", triage=triage, emotion_state=emotion_summary)
        except Exception:
            pass

    # Arc detection and cache update (deterministic, non-LLM)
    try:
        # fetch recent episodic entries for simple clustering
        recent_ep = await q(
            """
            SELECT id, text, time_scope, context_tags, triage, updated_at
            FROM memory_episodic
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT 200
            """,
            person_id,
        )
        themes: Dict[str, List[Dict[str, Any]]] = {}
        words = [w for w in normalized.split() if len(w) > 4]
        now_ts = dt.datetime.utcnow()
        for w in words:
            themes[w] = []
        for row in recent_ep or []:
            row_text = row.get("text") or ""
            tokens = [t for t in row_text.split() if len(t) > 4]
            for token in tokens:
                if token in themes:
                    themes[token].append(row)

        arc_stages = []
        for theme, items in themes.items():
            if len(items) >= 3:
                times = sorted(
                    [
                        dt.datetime.fromisoformat((itm.get("updated_at") or itm.get("time_scope") or now_ts).replace("Z", "+00:00"))
                        if isinstance(itm.get("updated_at") or itm.get("time_scope"), str)
                        else now_ts
                        for itm in items
                    ]
                )
                span_hours = (times[0] - times[-1]).total_seconds() / 3600 if len(times) > 1 else 0
                if span_hours >= 48:
                    # decide stage
                    stage = "building"
                    if len(items) == 1:
                        stage = "beginning"
                    elif len(items) <= 4:
                        stage = "building"
                    sentiment = 0
                    tri = triage if isinstance(triage, dict) else {}
                    mood = (tri.get("slots") or {}).get("mood_affect") if tri else {}
                    sentiment = (mood or {}).get("score") or 0
                    if sentiment < 0:
                        stage = "tension"
                    if sentiment > 0.4 and len(items) >= 3:
                        stage = "breakthrough"
                    arc_stages.append({"name": theme, "stage": stage, "mentions": len(items)})
    except Exception:
        arc_stages = []

    if arc_stages:
        life_arcs = [{"title": a["name"], "stage": a["stage"], "confidence": min(1.0, 0.5 + 0.05 * a["mentions"])} for a in arc_stages]
        arc_states = {a["name"]: a["stage"] for a in arc_stages}
        arc_progress = {a["name"]: a["mentions"] for a in arc_stages}
        arc_breakthroughs = [a["name"] for a in arc_stages if a["stage"] == "breakthrough"]
        await dbexec(
            """
            INSERT INTO narrative_arc_cache (person_id, life_arcs, active_arcs, arc_states, arc_progress, arc_breakthroughs, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET life_arcs = EXCLUDED.life_arcs,
                active_arcs = EXCLUDED.active_arcs,
                arc_states = EXCLUDED.arc_states,
                arc_progress = EXCLUDED.arc_progress,
                arc_breakthroughs = EXCLUDED.arc_breakthroughs,
                updated_at = NOW()
            """,
            person_id,
            life_arcs,
            life_arcs,
            arc_states,
            arc_progress,
            arc_breakthroughs,
        )
        # attach arcs to personal_model
        try:
            pm_row = await q("SELECT long_term FROM personal_model WHERE person_id = $1", person_id, one=True)
            long_term = (pm_row.get("long_term") or {}) if pm_row else {}
            long_term["life_arcs"] = life_arcs
            long_term["active_arcs"] = life_arcs
            long_term["arc_states"] = arc_states
            long_term["arc_progress"] = arc_progress
            long_term["arc_breakthroughs"] = arc_breakthroughs
            await dbexec(
                """
                UPDATE personal_model
                SET long_term = $2::jsonb, updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                long_term,
            )
        except Exception:
            pass
    # wellness rollup (last 20 episodic wellness tags)
    try:
        wellness_rows = await q(
            """
            SELECT context_tags FROM memory_episodic
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            person_id,
        )
        body_vals = []
        mind_vals = []
        emotion_vals = []
        energy_vals = []
        for row in wellness_rows or []:
            for tag in row.get("context_tags") or []:
                if isinstance(tag, dict) and "wellness_tags" in tag:
                    wt = tag["wellness_tags"]
                    body_vals.append(wt.get("body", 0))
                    mind_vals.append(wt.get("mind", 0))
                    emotion_vals.append(wt.get("emotion", 0.0))
                    energy_vals.append(wt.get("energy", 0))
        def _avg(values):
            return sum(values) / len(values) if values else 0.0
        wellness_state = {
            "body": {"score": _avg(body_vals)},
            "mind": {"score": _avg(mind_vals)},
            "emotion": {"score": _avg(emotion_vals)},
            "energy": {"score": _avg(energy_vals)},
            "updated_at": dt.datetime.utcnow().isoformat(),
        }
        await dbexec(
            """
            INSERT INTO wellness_state_cache (person_id, body, mind, emotion, energy, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET body = EXCLUDED.body,
                mind = EXCLUDED.mind,
                emotion = EXCLUDED.emotion,
                energy = EXCLUDED.energy,
                updated_at = NOW()
            """,
            person_id,
            wellness_state["body"],
            wellness_state["mind"],
            wellness_state["emotion"],
            wellness_state["energy"],
        )
        # sync to personal_model
        try:
            pm_row = await q("SELECT long_term FROM personal_model WHERE person_id = $1", person_id, one=True)
            long_term = (pm_row.get("long_term") or {}) if pm_row else {}
            long_term["wellness_state"] = wellness_state
            await dbexec(
                """
                UPDATE personal_model
                SET long_term = $2::jsonb, updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                long_term,
            )
        except Exception:
            pass
    except Exception:
        pass
    except Exception:
        pass

    if entry_id:
        _processed_fast.add(entry_id)
        _processed_heavy.add(entry_id)

    # enqueue soul extraction/refresh asynchronously
    try:
        if entry_id:
            asyncio.create_task(soul_extract_worker.soul_extract_worker(entry_id, person_id))
        asyncio.create_task(soul_refresh_worker.soul_refresh_worker(person_id))
    except Exception:
        pass

    return {
        "entry_id": entry_id,
        "embedding": len(vec),
        "personal_model": personal_model_update,
        "content_hash": content_hash,
    }
