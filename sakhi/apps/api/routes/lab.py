from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from uuid import uuid4
import os
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from sakhi.apps.api.services.conversation.orchestrator import orchestrate_turn
from sakhi.apps.api.services.turn.async_triggers import enqueue_turn_jobs
from sakhi.apps.api.services.turn.context_loader import load_memory_context
from sakhi.apps.api.services.turn.reply_service import build_turn_reply
from sakhi.apps.worker.pipelines.turn_updates import runner as turn_runner
from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.services.memory.consolidation import consolidate_memory
from sakhi.apps.worker.tasks.turn_personal_model_update import run_turn_personal_model_update
from sakhi.libs.embeddings import embed_text
from sakhi.libs.retrieval.episodic_retrieval import retrieve_episodic_slices
from sakhi.apps.api.services.journaling.enrich import enrich_journal_entry
from sakhi.apps.api.services.memory_graph.graph import build_graph_from_enrichment
from sakhi.apps.api.services.memory_graph.persist import persist_enrichment, persist_memory_graph
from sakhi.apps.worker.narrative_deep import generate_deep_soul_narrative
from sakhi.apps.worker.identity_momentum_deep import run_identity_momentum_deep
from sakhi.apps.worker.decision_graph_deep import run_decision_graph_deep
from sakhi.apps.worker.rhythm_soul_deep import run_rhythm_soul_deep
from sakhi.apps.worker.tasks.esr_worker import run_emotion_state_refresh
from sakhi.apps.worker.tasks.emotion_soul_rhythm_deep import run_emotion_soul_rhythm_deep
from sakhi.apps.worker.tasks.weekly_learning_worker import run_weekly_learning
from sakhi.apps.worker.tasks.episodic_consolidation_v21 import extract_context_tags
from sakhi.apps.worker.tasks.soul_refresh_worker import soul_refresh_worker
from sakhi.apps.api.services.workers.context_refresh_worker import refresh_context
from sakhi.apps.api.services.reflection.narration_foundation import generate_foundation_narration
from sakhi.apps.api.services.reflection_inquiry.answerer import answer_reflection_inquiry
from sakhi.apps.api.services.personal_intelligence.assembler import assemble_personal_intelligence_snapshot
from sakhi.apps.api.services.personal_intelligence.renderer import render_personal_intelligence, render_personal_intelligence_narrative
from sakhi.apps.api.core.llm import call_llm

router = APIRouter(prefix="/lab", tags=["lab"])
logger = logging.getLogger(__name__)

# Simple in-memory store for lab runs (non-persistent, debug only)
_LAB_RESULTS: defaultdict[str, deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=200))
DEFAULT_REPLAY_WORKERS = ["memory", "episodic-v21", "personal-model", "ayurvedic_pipeline"]


class LiveTurnBody(BaseModel):
    user_id: str
    journal_text: Optional[str] = ""
    options: dict = {}
    session_id: Optional[str] = None
    workers: List[str] = []
    ts: Optional[str] = None
    mode: Optional[str] = None


class RunWorkersBody(BaseModel):
    user_id: str
    workers: List[str] = []
    session_id: Optional[str] = None
    entry_id: Optional[str] = None


class CleanupBody(BaseModel):
    user_id: str


class EpisodicRetrievalBody(BaseModel):
    user_id: str
    query_text: str
    k: int = 5
    days_back: int = 180


WORKER_JOB_MAP = {
    "memory": "turn_memory_update",
    "planner": "turn_planner_update",
    "planner-alignment": "turn_planner_update",
    # Rhythm: deterministic personal_model rhythm_state worker
    "rhythm": "rhythm_forecast",
    # Rhythm & Forecast label should run legacy turn_rhythm_update
    "rhythm-forecast": "turn_rhythm_update",
    "persona": "turn_persona_update",
    "persona-relationship": "turn_persona_update",
    "identity-soul": "turn_persona_update",
    "meta-reflection": "turn_insight_update",
    "insight": "turn_insight_update",
    "insight-engine": "turn_insight_update",
    "brain": "brain_refresh",
    "episodic-v21": "episodic_consolidation_v21",
    "esr": "esr",
    "neutral_signal_extraction": "neutral_signal_extraction",
    "ayurvedic_pipeline": "ayurvedic_pipeline",
}


async def run_replay_for_user(user_id: str, worker_keys: List[str], *, session_id: str | None = None) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT id, content, ts
        FROM journal_entries
        WHERE person_id = $1 OR user_id = $1
        ORDER BY ts ASC
        """,
        user_id,
    )
    journals = rows or []
    logger.info(
        "[lab] replaying journals via live turn",
        extra={"user_id": user_id, "journal_count": len(journals)},
    )
    if not worker_keys:
        worker_keys = DEFAULT_REPLAY_WORKERS

    all_results: List[Dict[str, Any]] = []
    for journal in journals:
        journal_id = journal.get("id")
        journal_ts = journal.get("ts")
        payload = {
            "text": journal.get("content") or "",
            "entry_id": str(journal_id) if journal_id else None,
            "ts": (journal_ts.isoformat() if isinstance(journal_ts, dt.datetime) else dt.datetime.utcnow().isoformat()),
            "thread_id": user_id,
        }
        for key in worker_keys:
            res = await _run_worker_sync(key, turn_id=str(uuid4()), person_id=user_id, payload=payload)
            res["journal_id"] = str(journal_id) if journal_id else None
            res["journal_ts"] = payload["ts"]
            all_results.append(res)
    if session_id:
        _store_results(session_id, all_results)
    return all_results


async def _run_worker_sync(worker_key: str, *, turn_id: str, person_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if worker_key == "consolidation":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await consolidate_memory(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"merged": result.get("merged"), "candidates": result.get("candidates")},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover - debug fallback
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "memory-graph-builder":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            entry_id = payload.get("entry_id")
            text = payload.get("text") or ""
            ts_raw = payload.get("ts")
            ts = None
            if isinstance(ts_raw, str):
                try:
                    ts = dt.datetime.fromisoformat(ts_raw)
                except Exception:
                    ts = None
            if not isinstance(ts, dt.datetime):
                ts = dt.datetime.utcnow()

            # If no text passed, fetch the latest journal for this person (optionally match entry_id).
            if not text:
                if entry_id:
                    row = await q(
                        "SELECT content FROM journal_entries WHERE id = $1 AND user_id = $2",
                        entry_id,
                        person_id,
                        one=True,
                    )
                    text = (row or {}).get("content") or ""
                else:
                    row = await q(
                        """
                        SELECT id, content, created_at
                        FROM journal_entries
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        person_id,
                        one=True,
                    )
                    entry_id = (row or {}).get("id") or entry_id
                    text = (row or {}).get("content") or ""

            if not text:
                return {
                    "worker": worker_key,
                    "status": "skipped",
                    "error": "No text/journal available to build graph",
                    "started_at": started_at,
                    "finished_at": dt.datetime.utcnow().isoformat(),
                }

            enrichment = await enrich_journal_entry(text, person_id=person_id)
            graph = build_graph_from_enrichment(enrichment)
            await persist_enrichment(entry_id, enrichment)
            await persist_memory_graph(person_id, graph)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {
                    "nodes": len(graph.get("nodes") or []),
                    "edges": len(graph.get("edges") or []),
                },
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover - defensive
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "personal-model":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_turn_personal_model_update(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": result},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover - debug fallback
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "narrative-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await generate_deep_soul_narrative(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"soul_narrative": bool(result)},
                "signals": {"episodic_used": len(result.get("episodic", [])) if isinstance(result, dict) else None},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover - debug fallback
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "identity-momentum-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_identity_momentum_deep(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "decision-graph-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_decision_graph_deep(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "rhythm-soul-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_rhythm_soul_deep(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }
    if worker_key == "longitudinal-update":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_weekly_learning(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }
    if worker_key == "emotion-soul-rhythm-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_emotion_soul_rhythm_deep(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }
    if worker_key == "esr":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_emotion_state_refresh(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "esr-deep":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            result = await run_emotion_state_refresh(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"updated": bool(result)},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "soul-refresh":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            await soul_refresh_worker(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"refreshed": True},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    if worker_key == "context-refresh":
        started_at_dt = dt.datetime.utcnow()
        started_at = started_at_dt.isoformat()
        try:
            await refresh_context(person_id)
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "ok",
                "writes": {"cache_refreshed": True},
                "finished_at": finished_at,
                "started_at": started_at,
            }
        except Exception as exc:  # pragma: no cover
            finished_at = dt.datetime.utcnow().isoformat()
            return {
                "worker": worker_key,
                "status": "error",
                "error": str(exc),
                "finished_at": finished_at,
                "started_at": started_at,
            }

    job_type = WORKER_JOB_MAP.get(worker_key)
    started_at_dt = dt.datetime.utcnow()
    started_at = started_at_dt.isoformat()
    if not job_type:
        return {
            "worker": worker_key,
            "status": "skipped",
            "notes": "No synchronous mapping for this worker in lab mode.",
            "finished_at": started_at,
        }
    try:
        await turn_runner._process(job_type, turn_id, person_id, payload)  # type: ignore[attr-defined]
        finished_at_dt = dt.datetime.utcnow()
        snapshot = await load_memory_context(person_id)

        def _from_snapshot(key: str) -> Dict[str, Any]:
            if key in {"memory", "memory-spine"}:
                return {
                    "writes": {
                        "short_term_entries": len(snapshot.get("entries") or []),
                        "tasks_count": len(snapshot.get("tasks") or []),
                        "cache_hit": snapshot.get("cache_hit"),
                    },
                    "signals": {"memory_context": snapshot.get("memory_context")},
                    "evidence": [],
                }
            if key in {"rhythm", "rhythm-forecast"}:
                return {
                    "writes": {},
                    "signals": snapshot.get("rhythm") or {},
                    "evidence": [],
                }
            if key in {"planner", "planner-alignment"}:
                return {
                    "writes": {"tasks_count": len(snapshot.get("tasks") or [])},
                    "signals": {},
                    "evidence": [],
                }
            if key in {"persona", "persona-relationship", "identity-soul"}:
                persona = snapshot.get("persona") or {}
                return {
                    "writes": {"persona_keys": list(persona.keys())},
                    "signals": persona,
                    "evidence": [],
                }
            if key in {"insight", "insight-engine", "meta-reflection"}:
                return {
                    "writes": {},
                    "signals": {"insight_snapshot": snapshot.get("persona") or {}},
                    "evidence": [],
                }
            return {"writes": {}, "signals": {}, "evidence": []}

        post = _from_snapshot(worker_key)
        return {
            "worker": worker_key,
            "status": "completed",
            "notes": f"Lab shim: ran {job_type} (worker does not emit structured payload).",
            "inputs_used": ["turn_payload"],
            "writes": post["writes"],
            "signals": post["signals"],
            "evidence": post["evidence"],
            "confidence": None,
            "job_type": job_type,
            "finished_at": finished_at_dt.isoformat(),
            "started_at": started_at,
            "duration_ms": int((finished_at_dt - started_at_dt).total_seconds() * 1000),
        }
    except Exception as exc:
        return {
            "worker": worker_key,
            "status": "error",
            "notes": f"Sync run failed: {exc}",
            "finished_at": dt.datetime.utcnow().isoformat(),
            "started_at": started_at,
        }


def _store_results(session_id: str, results: List[Dict[str, Any]]) -> None:
    if not session_id:
        return
    bucket = _LAB_RESULTS[session_id]
    for res in results:
        bucket.appendleft(res)


@router.post("/live-turn")
async def lab_live_turn(body: LiveTurnBody):
    if not body.user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    if body.mode != "replay_existing" and not (body.journal_text or "").strip():
        raise HTTPException(status_code=400, detail="journal_text required for live-turn")

    lab_inline_memory = os.getenv("LAB_INLINE_MEMORY", "0") == "1"
    # Force full writes in lab mode so workers have complete inputs (disable minimal/capture-only shortcuts).
    os.environ["SAKHI_TURN_MINIMAL_WRITE"] = "0"
    os.environ["SAKHI_UNIFIED_INGEST"] = "1"

    lab_session_id = body.session_id or f"lab-{uuid4()}"
    turn_id = str(uuid4())  # use real UUIDs for downstream jobs/storage
    worker_keys = body.workers or []
    sync_workers = bool((body.options or {}).get("sync_workers"))
    # Lab should never enqueue to background worker queues.
    enqueue_workers = False
    # In lab, when specific workers are selected for live turn, default to running them synchronously
    # so their logs/results show up inline unless explicitly opted out.
    if worker_keys and not (body.options or {}).get("sync_workers") and not (body.options or {}).get("enqueue_workers"):
        sync_workers = True
    if lab_inline_memory:
        sync_workers = True
        enqueue_workers = False
        if "memory" not in worker_keys:
            worker_keys = ["memory"] + worker_keys

    if body.mode == "replay_existing":
        replay_results = await run_replay_for_user(body.user_id, worker_keys, session_id=lab_session_id)
        return {
            "turn_id": None,
            "session_id": lab_session_id,
            "entry_id": None,
            "immediate_response": {},
            "llm_debug": {},
            "job_ids": [],
            "sync_results": replay_results,
            "debug": {
                "source": "lab/live-turn",
                "mode": "replay_existing",
                "workers": worker_keys,
            },
        }

    # Run the core turn (conversation + ingest)
    turn_context = await orchestrate_turn(
        person_id=body.user_id,
        text=body.journal_text or "",
        clarity_hint=None,
        capture_only=False,
        ts=body.ts,
    )
    entry_id = turn_context.get("entry_id")
    entry_id_str = str(entry_id) if entry_id else None
    context_snapshot = await load_memory_context(body.user_id)
    reply_package = await build_turn_reply(
        person_id=body.user_id,
        user_text=body.journal_text or "",
        context_snapshot=context_snapshot,
        return_debug=True,
    )
    reply = reply_package.get("reply") or reply_package or {}

    entry_ts: dt.datetime | None = None
    if entry_id:
        row_ts = await q("SELECT ts FROM journal_entries WHERE id = $1", entry_id, one=True)
        entry_ts = row_ts.get("ts") if row_ts else None
    if isinstance(entry_ts, str):
        try:
            entry_ts = dt.datetime.fromisoformat(entry_ts)
        except Exception:
            entry_ts = None
    if not isinstance(entry_ts, dt.datetime):
        # Fall back to the provided ts or the orchestrated turn timestamp (UTC now inside orchestrate_turn).
        if isinstance(body.ts, str):
            try:
                entry_ts = dt.datetime.fromisoformat(body.ts.replace("Z", "+00:00"))
            except Exception:
                entry_ts = None
        elif isinstance(body.ts, dt.datetime):
            entry_ts = body.ts
        else:
            entry_ts = dt.datetime.utcnow()
    entry_ts_iso = entry_ts.isoformat()

    # Optionally enqueue async jobs (if desired later)
    job_ids: List[str] = []
    if enqueue_workers:
        # This path is intentionally disabled in lab mode.
        enqueue_workers = False

    # Run selected workers synchronously for lab inspection
    sync_results: List[Dict[str, Any]] = []
    if sync_workers and worker_keys:
        for key in worker_keys:
            sync_results.append(
                await _run_worker_sync(
                    key,
                    turn_id=turn_id,
                    person_id=body.user_id,
                    payload={
                        "text": body.journal_text,
                        "entry_id": entry_id_str,
                        "ts": entry_ts_iso,
                        "thread_id": body.user_id,
                    },
                )
            )
        _store_results(lab_session_id, sync_results)

    return {
        "turn_id": turn_id,
        "session_id": lab_session_id,
        "entry_id": str(entry_id) if entry_id else None,
        "immediate_response": reply,
        "llm_debug": reply_package.get("debug") or {},
        "job_ids": job_ids,
        "sync_results": sync_results,
        "debug": {
            "source": "lab/live-turn",
            "sync_workers": sync_workers,
            "workers": worker_keys,
        },
    }


@router.post("/run-workers")
async def lab_run_workers(body: RunWorkersBody):
    if not body.user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    if not body.workers:
        raise HTTPException(status_code=400, detail="workers required")
    # Pick an entry_id to run against (latest by default, or supplied)
    entry_id = body.entry_id
    journal_row = None
    if not entry_id:
        journal_row = await q(
            """
            SELECT id, content, ts
            FROM journal_entries
            WHERE person_id = $1 OR user_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            body.user_id,
            one=True,
        )
        entry_id = journal_row.get("id") if journal_row else None
    if not entry_id:
        raise HTTPException(status_code=400, detail="No journal entry found for this user; please run a live turn first.")

    if journal_row is None:
        journal_row = await q(
            "SELECT id, content, ts FROM journal_entries WHERE id = $1",
            entry_id,
            one=True,
        )

    text_for_payload = (journal_row or {}).get("content") or ""
    ts_for_payload = (journal_row or {}).get("ts") or dt.datetime.utcnow()
    entry_id_str = str(entry_id) if entry_id else None
    turn_id = str(uuid4())
    payload = {
        "text": text_for_payload,
        "entry_id": entry_id_str,
        "ts": ts_for_payload.isoformat(),
        "thread_id": body.user_id,
    }
    results: List[Dict[str, Any]] = []
    for key in body.workers:
        results.append(await _run_worker_sync(key, turn_id=turn_id, person_id=body.user_id, payload=payload))
    _store_results(body.session_id or turn_id, results)
    return {"results": results, "session_id": body.session_id or turn_id}


@router.post("/episodic-retrieval")
async def lab_episodic_retrieval(body: EpisodicRetrievalBody):
    if not body.user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    if not (body.query_text or "").strip():
        raise HTTPException(status_code=400, detail="query_text required")
    try:
        query_vec = await embed_text(body.query_text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[lab_episodic_retrieval] embed failed user_id=%s err=%s", body.user_id, exc)
        raise HTTPException(status_code=500, detail="failed to embed query_text") from exc

    results = await retrieve_episodic_slices(
        user_id=body.user_id,
        query_vector=query_vec if isinstance(query_vec, list) else [],
        k=body.k or 5,
        days_back=body.days_back or 180,
    )
    logger.info(
        "[lab_episodic_retrieval] user_id=%s query_len=%s returned=%s",
        body.user_id,
        len(body.query_text or ""),
        len(results),
    )
    return {"query": body.query_text, "results": results}


@router.post("/cleanup")
async def lab_cleanup(body: CleanupBody) -> Dict[str, Any]:
    if not body.user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    person = body.user_id

    async def _count(sql: str, val: str) -> int:
        row = await q(sql, val, one=True)
        try:
            return int((row or {}).get("count") or 0)
        except Exception:
            return 0

    journal_count = await _count("SELECT COUNT(*) FROM journal_entries WHERE user_id = $1", person)
    emb_count = await _count(
        "SELECT COUNT(*) FROM journal_embeddings WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)",
        person,
    )
    stm_count = await _count("SELECT COUNT(*) FROM memory_short_term WHERE user_id = $1", person)
    epi_count = await _count("SELECT COUNT(*) FROM memory_episodic WHERE user_id = $1", person)
    cache_count = await _count("SELECT COUNT(*) FROM memory_context_cache WHERE person_id::text = $1", person)
    arc_count = await _count("SELECT COUNT(*) FROM narrative_arc_cache WHERE person_id::text = $1", person)

    await dbexec(
        "DELETE FROM journal_embeddings WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)",
        person,
    )
    await dbexec("DELETE FROM journal_entries WHERE user_id = $1", person)
    await dbexec("DELETE FROM memory_short_term WHERE user_id = $1", person)
    await dbexec("DELETE FROM memory_episodic WHERE user_id = $1", person)
    await dbexec("DELETE FROM memory_context_cache WHERE person_id::text = $1", person)
    await dbexec("DELETE FROM narrative_arc_cache WHERE person_id::text = $1", person)

    return {
        "status": "ok",
        "person_id": person,
        "deleted": {
            "journal_entries": journal_count,
            "journal_embeddings": emb_count,
            "memory_short_term": stm_count,
            "memory_episodic": epi_count,
            "memory_context_cache": cache_count,
            "narrative_arc_cache": arc_count,
        },
        "note": "Cleanup is destructive. Re-run ingest/workers to repopulate.",
    }


@router.get("/worker-results")
async def lab_worker_results(session_id: Optional[str] = Query(default=None), user_id: Optional[str] = Query(default=None)):
    bucket = _LAB_RESULTS.get(session_id or "", deque())
    return {
        "results": list(bucket),
        "session_id": session_id,
        "user_id": user_id,
        "note": "In-memory lab results",
    }


class ContextTagBackfillBody(BaseModel):
    person_id: str
    limit: int = 1000


@router.post("/backfill-context-tags")
async def backfill_context_tags(body: ContextTagBackfillBody):
    """Lab helper: recompute deterministic context_tags for episodic rows for a user."""
    try:
        rows = await q(
            """
            SELECT id, text, context_tags
            FROM memory_episodic
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            body.person_id,
            body.limit,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to fetch episodic rows: {exc}")

    updated = 0
    processed = 0
    for row in rows or []:
        processed += 1
        text_val = row.get("text") or ""
        new_tags = extract_context_tags(text_val)
        if new_tags is None:
            new_tags = []
        try:
            old_tags = row.get("context_tags") or []
        except Exception:
            old_tags = []
        # Only update if different
        if json.dumps(old_tags, sort_keys=True) == json.dumps(new_tags, sort_keys=True):
            continue
        try:
            await dbexec(
                "UPDATE memory_episodic SET context_tags = $2::jsonb WHERE id = $1",
                row.get("id"),
                json.dumps(new_tags),
            )
            updated += 1
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to update context_tags", extra={"episode_id": row.get("id"), "error": str(exc)})
            continue

    return {
        "person_id": body.person_id,
        "processed": processed,
        "updated": updated,
        "note": "context_tags recomputed deterministically from episode text",
    }


@router.get("/memory-details")
async def lab_memory_details(
    person_id: str = Query(...),
    entry_id: Optional[str] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
):
    """Lab-only helper to inspect what memory worker wrote. Returns flags instead of raw vectors."""

    # STM: fixed limit 14 per request
    stm_limit = 14
    stm = []
    try:
        stm = await q(
            """
            SELECT id,
                   COALESCE(entry_id::text, record->>'entry_id', '') AS entry_id,
                   person_id,
                   text,
                   tags,
                   created_at,
                   (vector_vec IS NOT NULL) AS has_vec
            FROM memory_short_term
            WHERE (person_id::text = $1 OR user_id::text = $1)
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            stm_limit,
        )
    except Exception:
        try:
            stm = await q(
                """
                SELECT id, user_id as person_id,
                       record,
                       COALESCE(entry_id::text, record->>'entry_id', '') as entry_id,
                       record->>'text' as text,
                       record->'tags' as tags,
                       created_at,
                       (vector_vec IS NOT NULL) AS has_vec
                FROM memory_short_term
                WHERE (person_id::text = $1 OR user_id::text = $1)
                ORDER BY created_at DESC
                LIMIT $2
                """,
                person_id,
                stm_limit,
            )
        except Exception:
            stm = []

    try:
        episodic = await q(
            """
            SELECT id,
                   person_id,
                   ts,
                   text,
                   soul,
                   soul_shadow,
                   soul_light,
                   soul_conflict,
                   soul_friction,
                   emotion_loop,
                   rhythm_state,
                   emotional_state,
                   created_at,
                   updated_at,
                   (vector_vec IS NOT NULL) AS has_vec
            FROM memory_episodic
            WHERE (person_id::text = $1 OR user_id::text = $1)
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        episodic = []

    try:
        recalls = await q(
            """
            SELECT recall_id, entry_id, event_label, weight, created_at
            FROM context_recalls
            WHERE person_id = $1
              AND ($2::uuid IS NULL OR entry_id = $2)
            ORDER BY created_at DESC
            LIMIT $3
            """,
            person_id,
            entry_id,
            limit,
        )
    except Exception:
        recalls = []

    try:
        embedding = await q(
            """
            SELECT entry_id, created_at
                   , (embedding_vec IS NOT NULL) AS has_vec
            FROM journal_embeddings
            WHERE ($1::uuid IS NULL OR entry_id = $1)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            entry_id,
            one=True,
        )
    except Exception:
        embedding = None

    try:
        cache_row = await q(
            """
            SELECT window_kind,
                   entries,
                   jsonb_array_length(entries) AS entries_len,
                   rhythm_state,
                   persona_snapshot,
                   task_window,
                   updated_at,
                   cache_hit,
                   (merged_context_vector IS NOT NULL) AS has_vec
            FROM memory_context_cache
            WHERE person_id = $1
              AND window_kind = 'default'
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
    except Exception:
        cache_row = None

    try:
        entry_row = None
        if entry_id:
            entry_row = await q(
                "SELECT id, content, layer, created_at, updated_at FROM journal_entries WHERE id = $1",
                entry_id,
                one=True,
            )
    except Exception:
        entry_row = None

    try:
        narrative_row = await q(
            "SELECT soul_narrative, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        narrative_row = None

    try:
        soul_row = await q(
            "SELECT soul_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        soul_row = None

    try:
        identity_momentum_row = await q(
            "SELECT identity_momentum_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        identity_momentum_row = None

    try:
        identity_row = await q(
            "SELECT identity_momentum_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        identity_row = None

    try:
        rhythm_row = await q(
            "SELECT rhythm_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        rhythm_row = None

    try:
        rhythm_soul_row = await q(
            "SELECT rhythm_soul_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        rhythm_soul_row = None

    try:
        longitudinal_row = await q(
            "SELECT longitudinal_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        longitudinal_row = None

    try:
        decision_graph_row = await q(
            "SELECT internal_decision_graph, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        decision_graph_row = None

    try:
        emotion_soul_rhythm_row = await q(
            "SELECT emotion_soul_rhythm_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        emotion_soul_rhythm_row = None
    try:
        esr_row = await q(
            "SELECT emotion_state, updated_at FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
    except Exception:
        esr_row = None

    try:
        # Debug: Check total count including expired
        debug_count = await q(
            """
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE expires_at >= NOW()) as active
            FROM elemental_signal_stm
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        if debug_count:
            logger.info(f"[lab] elemental_stm debug: total={debug_count.get('total', 0)}, active={debug_count.get('active', 0)}")

        elemental_stm = await q(
            """
            SELECT id,
                   person_id,
                   source_signal_id,
                   source_type,
                   dimension,
                   earth,
                   water,
                   fire,
                   air,
                   ether,
                   magnitude,
                   confidence,
                   created_at,
                   expires_at
            FROM elemental_signal_stm
            WHERE person_id = $1
              AND expires_at >= NOW()
            ORDER BY created_at DESC
            LIMIT 30
            """,
            person_id,
        )
    except Exception as e:
        logger.warning(f"[lab] elemental_stm query error: {e}")
        elemental_stm = []

    try:
        elemental_weekly = await q(
            """
            SELECT person_id,
                   week_start,
                   dimension,
                   earth_avg,
                   water_avg,
                   fire_avg,
                   air_avg,
                   ether_avg,
                   volatility,
                   signal_count,
                   created_at
            FROM elemental_summary_weekly
            WHERE person_id = $1
            ORDER BY week_start DESC, dimension
            LIMIT 30
            """,
            person_id,
        )
    except Exception:
        elemental_weekly = []

    try:
        elemental_monthly = await q(
            """
            SELECT person_id,
                   month_start,
                   dimension,
                   earth_avg,
                   water_avg,
                   fire_avg,
                   air_avg,
                   ether_avg,
                   volatility,
                   week_count,
                   created_at
            FROM elemental_summary_monthly
            WHERE person_id = $1
            ORDER BY month_start DESC, dimension
            LIMIT 30
            """,
            person_id,
        )
    except Exception:
        elemental_monthly = []

    try:
        personal_model_elemental = await q(
            """
            SELECT baseline, volatility, recovery_rate, coupling, confidence, updated_at
            FROM personal_model_elemental
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        personal_model_elemental = None

    try:
        energy_weekly = await q(
            """
            SELECT person_id,
                   week_start,
                   activation_load,
                   grounding,
                   circulation,
                   recovery_efficiency,
                   confidence,
                   created_at
            FROM energy_summary_weekly
            WHERE person_id = $1
            ORDER BY week_start DESC
            LIMIT 12
            """,
            person_id,
        )
    except Exception:
        energy_weekly = []

    try:
        energy_monthly = await q(
            """
            SELECT person_id,
                   month_start,
                   activation_load,
                   grounding,
                   circulation,
                   recovery_efficiency,
                   confidence,
                   created_at
            FROM energy_summary_monthly
            WHERE person_id = $1
            ORDER BY month_start DESC
            LIMIT 12
            """,
            person_id,
        )
    except Exception:
        energy_monthly = []

    try:
        personal_model_energy = await q(
            """
            SELECT baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at
            FROM personal_model_energy
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        personal_model_energy = None

    try:
        goals_themes = await q(
            """
            SELECT cluster_title, supporting_entry_ids, confidence, identity_alignment, updated_at
            FROM brain_goals_themes
            WHERE person_id = $1
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        goals_themes = []

    logger.info(
        "[lab] memory-details payload",
        extra={
            "person_id": person_id,
            "elemental_stm": len(elemental_stm or []),
            "elemental_weekly": len(elemental_weekly or []),
            "elemental_monthly": len(elemental_monthly or []),
            "energy_weekly": len(energy_weekly or []),
            "energy_monthly": len(energy_monthly or []),
            "personal_model_elemental": bool(personal_model_elemental),
            "personal_model_energy": bool(personal_model_energy),
        },
    )

    return {
        "person_id": person_id,
        "entry_id": entry_id,
        "short_term": stm or [],
        "episodic": episodic or [],
        "recalls": recalls or [],
        "embedding": embedding or {},
        "context_cache": cache_row or {},
        "entry": entry_row or {},
        "soul": soul_row or {},
        "identity_momentum_v2": identity_momentum_row or {},
        "narrative": narrative_row or {},
        "identity_momentum": identity_row or {},
        "rhythm": rhythm_row or {},
        "rhythm_soul": rhythm_soul_row or {},
        "longitudinal": longitudinal_row or {},
        "emotion_soul_rhythm": emotion_soul_rhythm_row or {},
        "decision_graph": decision_graph_row or {},
        "esr": esr_row or {},
        "goals_themes": goals_themes or [],
        "elemental_stm": elemental_stm or [],
        "elemental_weekly": elemental_weekly or [],
        "elemental_monthly": elemental_monthly or [],
        "personal_model_elemental": personal_model_elemental or {},
        "energy_weekly": energy_weekly or [],
        "energy_monthly": energy_monthly or [],
        "personal_model_energy": personal_model_energy or {},
    }


@router.get("/planner-details")
async def lab_planner_details(
    person_id: str = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Lab-only helper to inspect planner-related artifacts."""
    try:
        tasks = await q(
            """
            SELECT id, label, due_ts, status, horizon, priority, created_at
            FROM planned_items
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        tasks = []

    try:
        cache_row = await q(
            """
            SELECT task_window, updated_at
            FROM memory_context_cache
            WHERE person_id = $1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
    except Exception:
        cache_row = None

    return {
        "person_id": person_id,
        "tasks": tasks or [],
        "task_window": (cache_row or {}).get("task_window") if cache_row else None,
        "cache_updated_at": (cache_row or {}).get("updated_at") if cache_row else None,
    }


@router.get("/rhythm-details")
async def lab_rhythm_details(
    person_id: str = Query(...),
    days: int = Query(default=7, ge=1, le=30),
):
    """Lab-only helper to inspect rhythm artifacts."""
    try:
        rhythm_state = await q(
            """
            SELECT rs.*, rc.chronotype, rc.score, rc.evidence
            FROM rhythm_state rs
            LEFT JOIN rhythm_chronotype rc ON rc.person_id = rs.person_id
            WHERE rs.person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        rhythm_state = None

    try:
        curves = await q(
            """
            SELECT day_scope, slots, confidence, created_at
            FROM rhythm_daily_curve
            WHERE person_id = $1
            ORDER BY day_scope DESC
            LIMIT $2
            """,
            person_id,
            days,
        )
    except Exception:
        curves = []

    try:
        alignment = await q(
            """
            SELECT horizon, recommendations, generated_at
            FROM rhythm_planner_alignment
            WHERE person_id = $1
            """,
            person_id,
        )
    except Exception:
        alignment = []

    return {
        "person_id": person_id,
        "state": rhythm_state or {},
        "daily_curves": curves or [],
        "planner_alignment": alignment or [],
    }


@router.get("/persona-details")
async def lab_persona_details(
    person_id: str = Query(...),
):
    """Lab-only helper to inspect persona/identity artifacts."""
    try:
        pm = await q(
            """
            SELECT persona, soul_state, identity_state, updated_at
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        pm = None

    try:
        cache_row = await q(
            """
            SELECT persona_snapshot, updated_at
            FROM memory_context_cache
            WHERE person_id = $1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
    except Exception:
        cache_row = None

    return {
        "person_id": person_id,
        "personal_model": pm or {},
        "persona_snapshot": (cache_row or {}).get("persona_snapshot") if cache_row else None,
        "cache_updated_at": (cache_row or {}).get("updated_at") if cache_row else None,
    }


@router.get("/meta-reflection-details")
async def lab_meta_reflection_details(
    person_id: str = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Lab-only helper to inspect meta-reflection artifacts."""
    try:
        scores = await q(
            """
            SELECT helpfulness, clarity, updated_at
            FROM meta_reflection_scores
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        scores = None

    try:
        queue_items = await q(
            """
            SELECT insight, priority, created_at
            FROM insights_queue
            WHERE person_id = $1
              AND insight->>'kind' = 'meta_reflection'
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        queue_items = []

    try:
        continuity = await q(
            """
            SELECT reflection_pending, last_interaction_ts
            FROM session_continuity
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        continuity = None

    try:
        metas = await q(
            """
            SELECT id, period, summary, insights, created_at
            FROM meta_reflections
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        metas = []

    return {
        "person_id": person_id,
        "scores": scores or {},
        "queue": queue_items or [],
        "continuity": continuity or {},
        "meta_reflections": metas or [],
    }


@router.get("/memory-spine-details")
async def lab_memory_spine_details(
    person_id: str = Query(...),
    limit: int = Query(default=3, ge=1, le=20),
):
    """Lab-only helper to inspect memory spine artifacts (weekly/monthly summaries)."""
    try:
        weekly = await q(
            """
            SELECT week_start, week_end, summary, highlights, top_themes, drift_score, semantic_notes, created_at
            FROM memory_weekly_summaries
            WHERE person_id = $1
            ORDER BY week_start DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        weekly = []

    try:
        signals = await q(
            """
            SELECT week_start, week_end, episodic_stats, theme_stats, contrast_stats, delta_stats, confidence, weekly_salience, weekly_contrast, dimension_states, weekly_body_notes, created_at
            FROM memory_weekly_signals
            WHERE person_id = $1
            ORDER BY week_start DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        signals = []

    try:
        pm = await q(
            """
            SELECT long_term, updated_at
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        pm = None

    return {
        "person_id": person_id,
        "weekly_summaries": weekly or [],
        "weekly_signals": signals or [],
        "personal_model_long_term": pm.get("long_term") if pm else {},
        "personal_model_updated_at": pm.get("updated_at") if pm else None,
    }


@router.get("/micro-flows-details")
async def lab_micro_flows_details(
    person_id: str = Query(...),
    limit: int = Query(default=5, ge=1, le=50),
):
    """Lab-only helper to inspect daily/micro flow artifacts."""
    try:
        flows = await q(
            """
            SELECT person_id, flow_date, warmup_step, focus_block_step, closure_step, optional_reward, source, rhythm_slot, created_at
            FROM mini_flow_cache
            WHERE person_id = $1
            ORDER BY flow_date DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        flows = []

    try:
        pm = await q(
            """
            SELECT mini_flow_state, mini_flow_rhythm_slot, updated_at
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        pm = None

    return {
        "person_id": person_id,
        "mini_flows": flows or [],
        "personal_model": pm or {},
    }


@router.get("/presence-details")
async def lab_presence_details(
    person_id: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Lab-only helper to inspect presence / follow-up artifacts."""
    try:
        presence_rows = await q(
            """
            SELECT date, summary, mood_today, open_actions, created_at, updated_at
            FROM presence_state
            WHERE person_id = $1
            ORDER BY date DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        presence_rows = []

    try:
        insights = await q(
            """
            SELECT id, kind, message, ts
            FROM insights
            WHERE person_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        insights = []

    try:
        queue_items = await q(
            """
            SELECT insight, priority, created_at
            FROM insights_queue
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        queue_items = []

    return {
        "person_id": person_id,
        "presence_state": presence_rows or [],
        "insights": insights or [],
        "insights_queue": queue_items or [],
    }


@router.get("/task-weaver-details")
async def lab_task_weaver_details(
    person_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Lab-only helper to inspect task weaver artifacts (task energy/priority)."""
    try:
        tasks = await q(
            """
            SELECT id, title, auto_priority, energy_cost, inferred_time_horizon, emotional_fit, status, created_at, updated_at
            FROM tasks
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        tasks = []

    return {
        "person_id": person_id,
        "tasks": tasks or [],
    }


@router.get("/memory-graph-details")
async def lab_memory_graph_details(
    person_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Lab-only helper to inspect memory graph artifacts (nodes/edges)."""
    try:
        nodes = await q(
            """
            SELECT id, node_kind, label, data, created_at
            FROM memory_nodes
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        nodes = []

    try:
        edges = await q(
            """
            SELECT from_node, to_node, relation, weight, created_at
            FROM memory_edges
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        edges = []

    return {
        "person_id": person_id,
        "nodes": nodes or [],
        "edges": edges or [],
    }


@router.get("/consolidation-details")
async def lab_consolidation_details(
    person_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Lab-only helper to inspect consolidation artifacts (recent nodes/edges)."""
    try:
        nodes = await q(
            """
            SELECT id, node_kind, label, data, created_at
            FROM memory_nodes
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        nodes = []

    try:
        edges = await q(
            """
            SELECT from_node, to_node, relation, weight, created_at
            FROM memory_edges
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        edges = []

    return {
        "person_id": person_id,
        "nodes": nodes or [],
        "edges": edges or [],
    }


@router.get("/analytics-calibration-details")
async def lab_analytics_calibration_details(
    person_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Lab-only helper to inspect analytics/calibration artifacts."""
    try:
        analytics = await q(
            """
            SELECT person_id, key, payload, computed_at
            FROM analytics_cache
            WHERE person_id = $1
            ORDER BY computed_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        analytics = []

    try:
        events = await q(
            """
            SELECT ts, kind, payload
            FROM system_events
            WHERE payload->>'person_id' = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        events = []

    return {
        "person_id": person_id,
        "analytics_cache": analytics or [],
        "system_events": events or [],
    }


@router.get("/maintenance-tempo-details")
async def lab_maintenance_tempo_details(
    person_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Lab-only helper to inspect maintenance/tempo artifacts (system events)."""
    try:
        events = await q(
            """
            SELECT ts, kind, payload
            FROM system_events
            WHERE payload->>'person_id' = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        events = []

    return {
        "person_id": person_id,
        "system_events": events or [],
    }


@router.get("/insights-details")
async def lab_insights_details(
    person_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Lab-only helper to inspect insights and queue artifacts."""
    try:
        insights = await q(
            """
            SELECT id, kind, message, ts
            FROM insights
            WHERE person_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        insights = []

    try:
        queue_items = await q(
            """
            SELECT insight, priority, created_at
            FROM insights_queue
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    except Exception:
        queue_items = []

    return {
        "person_id": person_id,
        "insights": insights or [],
        "insights_queue": queue_items or [],
    }


@router.get("/reflection/narration")
async def lab_render_narration(
    person_id: str = Query(...),
    # TODO (prod): tighten max window back to 180 once demo data is newer
    window_days: int = Query(1500, ge=1, le=1500),
    debug: int = Query(1, ge=0, le=1),
):
    """
    Lab-only human narration (Foundation Mode). Read-only, no advice, no writes.
    """
    result = await generate_foundation_narration(person_id=person_id, window_days=window_days, include_debug=bool(debug))
    return result


@router.get("/personal-intelligence")
async def lab_personal_intelligence_snapshot(
    person_id: str = Query(...),
    anchor_days: int = Query(1500, ge=1, le=1500),
):
    """
    Lab-only Personal Intelligence Snapshot (deterministic recognitions only).
    Now using narrative paragraphs instead of bullets.
    """
    anchor_end = dt.datetime.now(dt.timezone.utc)
    anchor_start = anchor_end - dt.timedelta(days=anchor_days)
    snapshot = await assemble_personal_intelligence_snapshot(
        person_id=person_id,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
    )
    # Use narrative renderer for descriptive paragraphs
    narratives = render_personal_intelligence_narrative(snapshot)
    return {
        "recognitions": narratives,
        "raw_recognitions": snapshot.get("recognitions", []),
        "debug": {
            "states_used": snapshot.get("states_used", []),
            "anchor_window": f"last {anchor_days} days",
        },
        "timeframe": {
            "mode": "rolling",
            "anchor_days": anchor_days,
            "context": "deterministic",
        },
    }


class ReflectionInquiryRequest(BaseModel):
    person_id: str
    reflection_id: str
    question_text: str
    window_days: int = 1500


class AyurvedicReflectionRequest(BaseModel):
    person_id: str
    anchor_days: int = 1500


@router.post("/reflection/inquiry")
async def lab_reflection_inquiry(request: ReflectionInquiryRequest):
    """
    Lab-only Reflection Inquiry endpoint.
    """
    result = await answer_reflection_inquiry(
        person_id=request.person_id,
        reflection_id=request.reflection_id,
        question_text=request.question_text,
        window_days=request.window_days,
    )
    return result


def _element_descriptors() -> dict[str, str]:
    return {
        "earth": "steadiness / heaviness",
        "water": "soothing / fluidity",
        "fire": "heat / intensity",
        "air": "movement / restlessness",
        "ether": "spaciousness / lightness",
    }


def _dominant_elements(row: dict) -> list[str]:
    elements = ["earth", "water", "fire", "air", "ether"]
    vals = [(el, float(row.get(f"{el}_avg", 0.0))) for el in elements]
    max_val = max(v for _, v in vals) if vals else 0.0
    if max_val <= 0:
        return []
    return [el for el, v in vals if abs(v - max_val) < 1e-6 or v == max_val]


@router.post("/ayurvedic-reflection")
async def lab_ayurvedic_reflection(request: AyurvedicReflectionRequest):
    """
    Lab-only Ayurvedic Reflection (interpretive, no writes).
    """
    person_id = request.person_id
    anchor_end = dt.datetime.now(dt.timezone.utc)
    anchor_start = anchor_end - dt.timedelta(days=request.anchor_days)

    # Fetch elemental summaries
    weekly = await q(
        """
        SELECT *
        FROM elemental_summary_weekly
        WHERE person_id = $1
          AND week_start >= $2::date
        ORDER BY week_start DESC
        """,
        person_id,
        anchor_start.date(),
    )
    monthly = await q(
        """
        SELECT *
        FROM elemental_summary_monthly
        WHERE person_id = $1
          AND month_start >= $2::date
        ORDER BY month_start DESC
        """,
        person_id,
        anchor_start.date().replace(day=1),
    )
    personal_elemental = await q(
        """
        SELECT baseline, volatility, recovery_rate, coupling, confidence, updated_at
        FROM personal_model_elemental
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    # Fetch energy summaries
    energy_weekly = await q(
        """
        SELECT *
        FROM energy_summary_weekly
        WHERE person_id = $1
          AND week_start >= $2::date
        ORDER BY week_start DESC
        """,
        person_id,
        anchor_start.date(),
    )
    energy_monthly = await q(
        """
        SELECT *
        FROM energy_summary_monthly
        WHERE person_id = $1
          AND month_start >= $2::date
        ORDER BY month_start DESC
        """,
        person_id,
        anchor_start.date().replace(day=1),
    )
    personal_energy = await q(
        """
        SELECT baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at
        FROM personal_model_energy
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    # Build context summary
    descriptors = _element_descriptors()
    latest_week_by_dim = {}
    for dim in ("body", "mind", "emotion"):
        for row in weekly or []:
            if row.get("dimension") == dim and dim not in latest_week_by_dim:
                latest_week_by_dim[dim] = row
                break

    elemental_patterns = {}
    for dim, row in latest_week_by_dim.items():
        dominant_raw = _dominant_elements(row)
        dominant = [descriptors.get(el, el) for el in dominant_raw]
        elemental_patterns[dim] = {
            "dominant": dominant,
            "volatility": float(row.get("volatility", 0.0)),
        }

    latest_energy = energy_weekly[0] if energy_weekly else None
    energy_patterns = {}
    if latest_energy:
        energy_patterns = {
            "activation_load": float(latest_energy.get("activation_load", 0.0)),
            "grounding": float(latest_energy.get("grounding", 0.0)),
            "circulation": float(latest_energy.get("circulation", 0.0)),
            "recovery_efficiency": float(latest_energy.get("recovery_efficiency", 0.0)),
            "confidence": float(latest_energy.get("confidence", 0.0)),
        }

    ctx = {
        "elemental_patterns": elemental_patterns,
        "energy_patterns": energy_patterns,
        "time_window_days": request.anchor_days,
        "confidence": float((personal_elemental or {}).get("confidence") or (personal_energy or {}).get("confidence") or 0.0),
    }

    system_msg = (
        "You are generating an internal reflection for a personal intelligence system.\n"
        "Your role is to describe observable patterns in body, mind, and energy using everyday conversational language.\n"
        "Rules:\n"
        "- Do NOT give advice or suggestions.\n"
        "- Do NOT use Sanskrit or technical Ayurvedic terms.\n"
        "- Do NOT diagnose or label conditions.\n"
        "- Do NOT claim certainty.\n"
        "- Do NOT reference internal tables or metrics.\n"
        "- Speak gently, reflectively, and tentatively.\n"
        "This is an interpretive lens, not a source of truth."
    )

    data_block = f"Context (summarized):\n{json.dumps(ctx, ensure_ascii=False, indent=2)}"

    user_msg = (
        "Write a short internal reflection (2–4 paragraphs) describing what these patterns suggest about how the person's body, mind, "
        "and energy have been moving together over time.\n"
        "Use calm, conversational language.\n"
        "Focus on tendencies and rhythms, not causes or fixes.\n"
        "Acknowledge uncertainty where appropriate."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "system", "content": data_block},
        {"role": "user", "content": user_msg},
    ]

    reflection_text = await call_llm(messages=messages, person_id=person_id)

    return {
        "reflection": reflection_text,
        "context": ctx,
        "timeframe": {"anchor_days": request.anchor_days},
    }


# ============================================================================
# Scaffolding Layer Tests (MVP: Demo User)
# ============================================================================

class SuppressionTestRequest(BaseModel):
    """Request to test suppression logic"""
    scaffold_type: str
    sensitivity: Optional[str] = "medium"  # low/medium/high


@router.post("/scaffolding/test-suppression")
async def test_suppression(request: SuppressionTestRequest):
    """
    Test suppression logic with demo user

    MVP: Uses demo user from environment variable (DEMO_USER_ID)
    Future: Support persona snapshots

    Returns: SuppressionDecision with action, reason, and user state
    """
    from sakhi.libs.scaffolding.suppression_engine import (
        check_scaffold_suppression,
        SuppressionSensitivity,
    )

    # Get demo user ID from environment
    demo_user_id = os.getenv("DEMO_USER_ID", "c10fbd98-25fa-4445-8aba-e5243bc01564")

    # Map sensitivity string to enum
    sensitivity_map = {
        "low": SuppressionSensitivity.LOW,
        "medium": SuppressionSensitivity.MEDIUM,
        "high": SuppressionSensitivity.HIGH,
    }
    sensitivity = sensitivity_map.get(request.sensitivity or "medium", SuppressionSensitivity.MEDIUM)

    # Check suppression
    decision = await check_scaffold_suppression(
        user_id=demo_user_id,
        scaffold_type=request.scaffold_type,
        sensitivity=sensitivity
    )

    return {
        "decision": decision.action.value,
        "reason": decision.reason,
        "sensitivity": decision.sensitivity.value,
        "user_state": decision.user_state,
        "tested_at": decision.checked_at.isoformat(),
        "demo_user_id": demo_user_id,
    }
