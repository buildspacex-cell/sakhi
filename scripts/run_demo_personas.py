#!/usr/bin/env python3
"""
Run Demo Personas Through Real Sakhi Pipeline

Creates real user accounts for Vidhya, Diya, and Big D, then processes
their journal entries through the REAL /v2/turn endpoint (same code path
as production). Records everything: conversation responses, brain state
evolution, drift, patterns, governance decisions.

Output: apps/web/public/simulation/{persona_id}.json

Usage:
    # Run a single persona
    python scripts/run_demo_personas.py --persona vidhya

    # Run all three
    python scripts/run_demo_personas.py --all

    # Limit days (useful for testing)
    python scripts/run_demo_personas.py --persona vidhya --days 5

    # Keep data in DB (don't clean up)
    python scripts/run_demo_personas.py --persona vidhya --no-cleanup

    # List available personas
    python scripts/run_demo_personas.py --list

    # Override multi-clock cadence
    python scripts/run_demo_personas.py --all --daily-interval 1 --weekly-interval 7 --monthly-interval 30 --forecast-runs-per-day 8

    # Print production vs simulation worker frequency map
    python scripts/run_demo_personas.py --list-worker-frequency
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sakhi.apps.worker.simulation_worker_registry import (
    as_import_tuples,
    interval_import_tuples,
    monthly_import_tuples,
    render_worker_frequency_table,
    resolve_forecast_runs_per_day,
    weekly_import_tuples,
)
from sakhi.apps.api.services.demo.simulation_continuity import enrich_simulation_payload

LOGGER = logging.getLogger(__name__)

# ── Fixed UUIDs (reproducible across runs) ──
PERSONA_UUIDS = {
    "vidhya": "a1b2c3d4-1111-4000-8000-000000000001",
    "diya":   "a1b2c3d4-2222-4000-8000-000000000002",
    "bigd":   "a1b2c3d4-3333-4000-8000-000000000003",
}

PERSONAS_DIR = PROJECT_ROOT / "docs" / "personas"
OUTPUT_DIR = PROJECT_ROOT / "apps" / "web" / "public" / "simulation"


# ── Persona Loading ──

def load_persona_def(persona_id: str) -> Dict[str, Any]:
    """Load persona definition from docs/personas/{id}.json."""
    path = PERSONAS_DIR / f"{persona_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")
    with open(path) as f:
        return json.load(f)


def list_personas() -> List[str]:
    """List available persona IDs."""
    return sorted(
        p.stem for p in PERSONAS_DIR.glob("*.json")
        if not p.name.startswith(".")
    )


# ── Database Helpers ──

async def _get_db():
    """Get database query/exec functions."""
    from sakhi.apps.api.core.db import q as db_query, exec as db_exec
    return db_query, db_exec


async def create_user(
    db_exec,
    user_id: str,
    persona: Dict[str, Any],
) -> None:
    """
    Create a real user account for a demo persona.

    Inserts into: persons, auth_users, profiles, personal_model.
    Same pattern as SimulationHarness.setup().
    """
    email = f"demo_{persona['id']}@sakhi.dev"
    baseline = persona["dosha_baseline"]

    # Infer constitution type
    v, p, k = baseline["vata"], baseline["pitta"], baseline["kapha"]
    if max(v, p, k) < 0.4:
        os_type = "Balanced"
    elif p >= v and p >= k:
        os_type = "Driven"
    elif v >= p and v >= k:
        os_type = "Quick-moving"
    else:
        os_type = "Steady"

    os_data = json.dumps({
        "type": os_type,
        "primary": max(baseline, key=baseline.get),
        "dosha_baseline": baseline,
        "source": "persona_definition",
    })

    rhythm = persona.get("rhythm", {})
    rhythm_data = json.dumps({
        "slots": {
            "morning": rhythm.get("morning", "medium"),
            "afternoon": rhythm.get("afternoon", "medium"),
            "evening": rhythm.get("evening", "medium"),
        },
    })

    # 1. persons
    await db_exec(
        "INSERT INTO persons (id, created_at) VALUES ($1, NOW()) ON CONFLICT (id) DO NOTHING",
        user_id,
    )
    # 1.5 users (intents table FK depends on this)
    await db_exec(
        """INSERT INTO users (id, email, full_name, created_at, updated_at)
           VALUES ($1, $2, $3, NOW(), NOW())
           ON CONFLICT (id) DO NOTHING""",
        user_id, email, persona["name"],
    )
    # 2. auth_users
    await db_exec(
        "INSERT INTO auth_users (id, email, created_at) VALUES ($1, $2, NOW()) ON CONFLICT (id) DO NOTHING",
        user_id, email,
    )
    # 3. profiles
    await db_exec(
        "INSERT INTO profiles (user_id, email, created_at, updated_at) VALUES ($1, $2, NOW(), NOW()) ON CONFLICT (user_id) DO NOTHING",
        user_id, email,
    )
    # 4. personal_model
    await db_exec(
        """INSERT INTO personal_model (person_id, operating_system, rhythm_state, updated_at)
           VALUES ($1, $2, $3, NOW()) ON CONFLICT (person_id) DO NOTHING""",
        user_id, os_data, rhythm_data,
    )

    LOGGER.info(f"Created user {user_id} ({persona['name']}, {os_type})")


async def cleanup_user(db_exec, user_id: str) -> None:
    """Delete all data for a demo user (reverse dependency order)."""
    tables = [
        # Conversation + turn data
        ("conversation_turns", "user_id"),
        ("conversation_sessions", "user_id"),
        ("dialog_state", "person_id"),
        ("reflection_traces", "person_id"),
        ("micro_goals", "person_id"),
        ("focus_paths", "person_id"),
        ("mini_flows", "person_id"),
        ("user_intents", "person_id"),
        ("user_preferences", "person_id"),
        ("behavior_symptom_log", "person_id"),
        ("behavior_log", "person_id"),
        ("symptom_log", "person_id"),
        ("personal_patterns", "person_id"),
        ("pattern_stats", "person_id"),
        # Worker output
        ("theme_states", "person_id"),
        ("pattern_occurrences", "person_id"),
        ("crystallized_patterns", "person_id"),
        ("memory_edges", "person_id"),
        ("memory_nodes", "person_id"),
        ("memory_episodic", "user_id"),
        ("memory_short_term", "user_id"),
        ("memory_context_cache", "person_id"),
        ("narrative_arc_cache", "person_id"),
        ("wellness_state_cache", "person_id"),
        ("body_state_history", "person_id"),
        # Ayurvedic pipeline
        ("elemental_signal_stm", "person_id"),
        ("elemental_weekly_aggregates", "person_id"),
        ("elemental_monthly_aggregates", "person_id"),
        ("energy_weekly_aggregates", "person_id"),
        ("energy_monthly_aggregates", "person_id"),
        ("health_data_sync", "person_id"),
        ("self_report_body", "person_id"),
        # Core tables
        ("journal_entries", "user_id"),
        ("personal_model", "person_id"),
        ("profiles", "user_id"),
        ("auth_users", "id"),
        ("users", "id"),
        ("persons", "id"),
    ]

    # Special case: journal_embeddings uses entry_id FK
    try:
        await db_exec(
            """DELETE FROM journal_embeddings
               WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)""",
            user_id,
        )
    except Exception:
        pass

    for table, col in tables:
        try:
            await db_exec(f"DELETE FROM {table} WHERE {col} = $1", user_id)
        except Exception as exc:
            LOGGER.debug(f"Cleanup {table}: {exc}")

    LOGGER.info(f"Cleaned up user {user_id}")


# ── Pipeline Runner ──

class DemoPersonaRunner:
    """
    Runs a demo persona through the real Sakhi pipeline.

    Adapted from SimulationHarness but uses pre-supplied journal entries
    instead of LLM-generated ones.
    """

    def __init__(
        self,
        persona: Dict[str, Any],
        user_id: str,
        db_query,
        db_exec,
        snapshot_interval: int = 1,
        daily_worker_interval: int = 1,
        weekly_worker_interval: int = 7,
        monthly_worker_interval: int = 30,
        forecast_interval_runs_per_day: Optional[int] = None,
        daily_worker_timeout: float = 30.0,
    ):
        self.persona = persona
        self.user_id = user_id
        self.db_query = db_query
        self.db_exec = db_exec
        self.snapshot_interval = snapshot_interval
        self.daily_worker_interval = max(1, daily_worker_interval)
        self.weekly_worker_interval = max(1, weekly_worker_interval)
        self.monthly_worker_interval = max(1, monthly_worker_interval)
        self.forecast_interval_runs_per_day = resolve_forecast_runs_per_day(
            forecast_interval_runs_per_day
        )
        self.daily_worker_timeout = daily_worker_timeout

        self._parity_client = None
        self._lifespan_cm = None
        self._tasks_before_turn: set = set()
        self._last_worker_results: Dict[str, Any] = {}

    async def init_pipeline(self) -> None:
        """Initialize the production pipeline client."""
        os.environ["SAKHI_DISABLE_QUEUE"] = "1"

        from httpx import AsyncClient, ASGITransport
        from sakhi.apps.api.main import app, lifespan

        self._lifespan_cm = lifespan(app)
        await self._lifespan_cm.__aenter__()

        transport = ASGITransport(app=app)
        self._parity_client = AsyncClient(
            transport=transport,
            base_url="http://test",
            timeout=120.0,
        )
        LOGGER.info("Pipeline client initialized (SAKHI_DISABLE_QUEUE=1)")

    async def close_pipeline(self) -> None:
        """Shut down the pipeline client."""
        if self._parity_client:
            await self._parity_client.aclose()
        if self._lifespan_cm:
            try:
                await self._lifespan_cm.__aexit__(None, None, None)
            except Exception:
                pass

    async def process_journal(
        self,
        content: str,
        timestamp: datetime,
        day: int,
    ) -> Dict[str, Any]:
        """
        Process a single journal entry through /v2/turn.

        Returns the full response including Sakhi's reply.
        """
        if not self._parity_client:
            raise RuntimeError("Pipeline not initialized. Call init_pipeline() first.")

        # Snapshot episodic IDs before turn (for precise backdating)
        existing_episodic: set = set()
        try:
            rows = await self.db_query(
                "SELECT id FROM memory_episodic WHERE user_id = $1",
                self.user_id,
            )
            existing_episodic = {str(r["id"]) for r in (rows or [])}
        except Exception:
            pass

        self._tasks_before_turn = self._snapshot_tasks()

        response = await self._parity_client.post(
            "/v2/turn",
            params={"user": self.user_id},
            json={"text": content, "ts": timestamp.isoformat()},
        )

        if response.status_code != 200:
            LOGGER.warning(f"[Day {day}] /v2/turn returned {response.status_code}: {response.text[:200]}")
            return {"error": response.text[:200], "status": response.status_code}

        data = response.json()
        entry_id = data.get("entry_id")
        reply = data.get("reply", "")

        LOGGER.info(f"[Day {day}] entry={entry_id}, reply_len={len(reply)}")

        # Drain background tasks (120s: post-reply involves multiple LLM calls)
        await self._drain_background_tasks(timeout=120.0)

        # Backdate to simulated timestamp
        if entry_id:
            await self._backdate(str(entry_id), timestamp, existing_episodic)

        return {
            "entry_id": str(entry_id) if entry_id else None,
            "reply": reply,
            "friction_state": data.get("friction_state"),
            "day": day,
            "timestamp": timestamp.isoformat(),
        }

    async def _run_worker_group(
        self,
        *,
        day: int,
        phase_name: str,
        worker_specs: List[tuple[str, str, str]],
        key_prefix: str,
    ) -> Dict[str, Any]:
        import importlib

        results: Dict[str, Any] = {}
        succeeded = 0

        for name, mod_path, fn_name in worker_specs:
            key = f"{key_prefix}{name}"
            try:
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, fn_name)
            except Exception as exc:
                results[key] = {"ok": False, "error": f"import: {exc}"}
                continue

            try:
                self._tasks_before_turn = self._snapshot_tasks()
                result = await asyncio.wait_for(
                    fn(self.user_id), timeout=self.daily_worker_timeout
                )
                await self._drain_background_tasks(timeout=10.0)
                payload = result if isinstance(result, dict) else {"raw": str(result)[:200]}
                results[key] = {"ok": True, **payload}
                succeeded += 1
                LOGGER.info(f"  {phase_name}.{name} OK (day {day}) payload={payload}")
            except asyncio.TimeoutError:
                results[key] = {"ok": False, "error": "timeout"}
                LOGGER.warning(f"  {phase_name}.{name} TIMEOUT (day {day})")
                await self._force_drain_all(timeout=5.0)
            except Exception as exc:
                results[key] = {"ok": False, "error": str(exc)[:200]}
                LOGGER.warning(f"  {phase_name}.{name} FAILED (day {day}): {exc}", exc_info=True)

        LOGGER.info(
            f"{phase_name.capitalize()} workers: {succeeded}/{len(worker_specs)} (day {day})"
        )
        return results

    async def run_daily_workers(self, day: int) -> Dict[str, Any]:
        return await self._run_worker_group(
            day=day,
            phase_name="daily",
            worker_specs=as_import_tuples(),
            key_prefix="",
        )

    async def run_weekly_workers(self, day: int) -> Dict[str, Any]:
        return await self._run_worker_group(
            day=day,
            phase_name="weekly",
            worker_specs=weekly_import_tuples(),
            key_prefix="weekly.",
        )

    async def run_monthly_workers(self, day: int) -> Dict[str, Any]:
        return await self._run_worker_group(
            day=day,
            phase_name="monthly",
            worker_specs=monthly_import_tuples(),
            key_prefix="monthly.",
        )

    async def run_interval_workers(self, day: int) -> Dict[str, Any]:
        if self.forecast_interval_runs_per_day <= 0:
            return {}
        results: Dict[str, Any] = {}
        for pass_index in range(1, self.forecast_interval_runs_per_day + 1):
            pass_results = await self._run_worker_group(
                day=day,
                phase_name=f"interval#{pass_index}",
                worker_specs=interval_import_tuples(),
                key_prefix=f"interval.{pass_index}.",
            )
            results.update(pass_results)
        return results

    async def capture_snapshot(self, day: int, reference_time: datetime | None = None) -> Dict[str, Any]:
        """Capture full state snapshot (same queries as SimulationHarness)."""
        model = await self.db_query(
            "SELECT * FROM personal_model WHERE person_id = $1",
            self.user_id, one=True,
        )

        memory_count = await self.db_query(
            "SELECT COUNT(*) as count FROM memory_episodic WHERE user_id = $1",
            self.user_id, one=True,
        )

        pattern_count = await self.db_query(
            "SELECT COUNT(*) as count FROM pattern_occurrences WHERE person_id = $1",
            self.user_id, one=True,
        )

        recent = await self.db_query(
            """SELECT id, text AS content, context_tags, created_at
               FROM memory_episodic WHERE user_id = $1
               ORDER BY created_at DESC LIMIT 5""",
            self.user_id,
        )

        # Friction state (pass simulation time so window queries hit backdated episodes)
        friction = {}
        try:
            from sakhi.apps.api.services.ayurveda.vikriti import get_full_friction_state
            friction = await get_full_friction_state(self.user_id, reference_time=reference_time)
        except Exception:
            pass

        # Provenance counts
        provenance = {}
        try:
            stm = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_short_term WHERE user_id = $1",
                self.user_id, one=True,
            )
            embed = await self.db_query(
                """SELECT COUNT(*) as count FROM journal_embeddings
                   WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)""",
                self.user_id, one=True,
            )
            nodes = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_nodes WHERE person_id = $1",
                self.user_id, one=True,
            )
            edges = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_edges WHERE person_id = $1",
                self.user_id, one=True,
            )
            provenance = {
                "stm_rows": stm["count"] if stm else 0,
                "embedding_rows": embed["count"] if embed else 0,
                "graph_nodes": nodes["count"] if nodes else 0,
                "graph_edges": edges["count"] if edges else 0,
            }
        except Exception:
            pass

        # Brain states
        brain_states = {}
        if model:
            for field in [
                "coherence_state", "alignment_state", "emotion_state",
                "soul_state", "rhythm_state", "identity_momentum_state",
                "forecast_state", "body_state", "operating_system",
            ]:
                raw = model.get(field)
                if raw and isinstance(raw, str):
                    try:
                        brain_states[field] = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        brain_states[field] = raw
                elif raw and not isinstance(raw, str):
                    brain_states[field] = _safe_json(raw)

        # Themes + patterns
        themes = []
        patterns = []
        try:
            t = await self.db_query(
                """SELECT theme, clarity_score, updated_at FROM theme_states
                   WHERE person_id = $1 ORDER BY clarity_score DESC LIMIT 20""",
                self.user_id,
            )
            themes = [dict(r) for r in t] if t else []
        except Exception:
            pass
        try:
            p = await self.db_query(
                """SELECT pattern_type, pattern_value, confidence, trajectory,
                          status, mention_count, distinct_days
                   FROM crystallized_patterns WHERE person_id = $1
                   AND status IN ('active', 'emerging')
                   ORDER BY confidence DESC LIMIT 30""",
                self.user_id,
            )
            patterns = [dict(r) for r in p] if p else []
        except Exception:
            pass

        return {
            "day": day,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "personal_model": _safe_json(dict(model) if model else {}),
            "memory_count": memory_count["count"] if memory_count else 0,
            "pattern_count": pattern_count["count"] if pattern_count else 0,
            "friction_state": _safe_json(friction),
            "recent_memories": [
                {"content": r.get("content", ""), "created_at": str(r.get("created_at", ""))}
                for r in (recent or [])
            ],
            "provenance": provenance,
            "brain_states": _safe_json(brain_states),
            "worker_results": self._last_worker_results,
            "themes": _safe_json(themes),
            "crystallized_patterns": _safe_json(patterns),
        }

    # ── Internal helpers (adapted from SimulationHarness) ──

    async def _backdate(
        self, entry_id: str, timestamp: datetime, existing_episodic: set,
    ) -> None:
        """Backdate all rows created by this turn to simulated timestamp."""
        await self.db_exec(
            "UPDATE journal_entries SET ts = $2, created_at = $2, updated_at = $2 WHERE id = $1",
            entry_id, timestamp,
        )
        try:
            await self.db_exec(
                """UPDATE conversation_turns SET created_at = $2
                   WHERE user_id = $1 AND created_at > NOW() - INTERVAL '30 seconds'""",
                self.user_id, timestamp,
            )
        except Exception:
            pass
        try:
            await self.db_exec(
                """UPDATE conversation_sessions
                   SET last_active_at = $2, created_at = LEAST(created_at, $2)
                   WHERE user_id = $1 AND last_active_at > NOW() - INTERVAL '30 seconds'""",
                self.user_id, timestamp,
            )
        except Exception:
            pass
        try:
            await self.db_exec(
                "UPDATE memory_short_term SET created_at = $2 WHERE entry_id = $1",
                entry_id, timestamp,
            )
        except Exception:
            pass
        try:
            all_rows = await self.db_query(
                "SELECT id FROM memory_episodic WHERE user_id = $1", self.user_id,
            )
            for r in (all_rows or []):
                if str(r["id"]) not in existing_episodic:
                    await self.db_exec(
                        "UPDATE memory_episodic SET created_at = $2 WHERE id = $1",
                        str(r["id"]), timestamp,
                    )
        except Exception:
            pass
        # Backdate pattern_occurrences (critical for crystallization distinct_days)
        try:
            await self.db_exec(
                "UPDATE pattern_occurrences SET detected_at = $2 WHERE entry_id = $1::uuid",
                entry_id, timestamp,
            )
        except Exception:
            pass

    def _snapshot_tasks(self) -> set:
        current = asyncio.current_task()
        return {t for t in asyncio.all_tasks() if t is not current and not t.done()}

    async def _drain_background_tasks(self, timeout: float = 30.0) -> None:
        """Wait for post-turn tasks until quiescent, then reset the DB pool on forced cancellation."""
        current = asyncio.current_task()
        baseline = self._tasks_before_turn
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        cancelled_tasks = False

        while True:
            new_tasks = {
                t for t in asyncio.all_tasks()
                if t is not current and not t.done() and t not in baseline
            }
            if not new_tasks:
                break

            remaining = deadline - loop.time()
            if remaining <= 0:
                for t in new_tasks:
                    t.cancel()
                await asyncio.gather(*new_tasks, return_exceptions=True)
                cancelled_tasks = True
                break

            done, pending = await asyncio.wait(new_tasks, timeout=remaining)

            for t in done:
                try:
                    t.result()
                except (asyncio.CancelledError, Exception):
                    pass

            if pending:
                for t in pending:
                    t.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                cancelled_tasks = True
                break

        if cancelled_tasks:
            await asyncio.sleep(0.5)
            await self._reset_db_pool()

    async def _force_drain_all(self, timeout: float = 10.0) -> None:
        """Cancel ALL pending tasks except current. Use after worker timeouts."""
        current = asyncio.current_task()
        pending = {
            t for t in asyncio.all_tasks()
            if t is not current and not t.done()
        }
        if not pending:
            return
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.sleep(0.5)
        # Reset DB pool to clear any corrupted connections from cancelled tasks
        await self._reset_db_pool()

    async def _reset_db_pool(self) -> None:
        """Force-terminate the DB pool to clear corrupted connections."""
        try:
            from sakhi.apps.api.core import db as db_mod
            if db_mod.POOL is not None:
                db_mod.POOL.terminate()  # synchronous, kills connections immediately
                db_mod.POOL = None
                db_mod._POOL_LOOP_ID = None
                LOGGER.debug("DB pool terminated and reset")
        except Exception as exc:
            LOGGER.debug(f"DB pool reset failed (non-fatal): {exc}")


def _safe_json(obj):
    """Convert to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    try:
        return dict(obj)
    except (TypeError, ValueError):
        return str(obj)


def _get_entry_timestamp(
    start: datetime,
    day: int,
    time_of_day: str,
    occurrence_index: int = 0,
) -> datetime:
    """Compute simulated timestamp for a journal entry."""
    base = start + timedelta(days=day - 1)
    hours = {"morning": 8, "afternoon": 14, "evening": 21}
    minute = max(0, occurrence_index) * 5
    return base.replace(
        hour=hours.get(time_of_day, 21),
        minute=minute,
        second=0,
        microsecond=0,
    )


# ── Main Orchestrator ──

async def run_persona(
    persona_id: str,
    max_days: Optional[int] = None,
    cleanup: bool = True,
    daily_worker_interval: int = 1,
    weekly_worker_interval: int = 7,
    monthly_worker_interval: int = 30,
    forecast_interval_runs_per_day: Optional[int] = None,
    daily_worker_timeout: float = 30.0,
    snapshot_timeout: float = 90.0,
    final_snapshot_timeout: float = 30.0,
) -> Path:
    """
    Run a single persona through the real pipeline.

    Returns path to exported JSON.
    """
    persona = load_persona_def(persona_id)
    daily_worker_interval = max(1, daily_worker_interval)
    weekly_worker_interval = max(1, weekly_worker_interval)
    monthly_worker_interval = max(1, monthly_worker_interval)
    user_id = PERSONA_UUIDS[persona_id]
    journals = persona.get("journals", [])

    if not journals:
        LOGGER.warning(f"No journals for {persona_id}. Creating user + export with empty entries.")

    # Determine total days
    total_days = max_days or (max(j["day"] for j in journals) if journals else 0)

    db_query, db_exec = await _get_db()

    # Clean up any existing data for this user
    await cleanup_user(db_exec, user_id)

    # Create user
    await create_user(db_exec, user_id, persona)

    runner = DemoPersonaRunner(
        persona=persona,
        user_id=user_id,
        db_query=db_query,
        db_exec=db_exec,
        daily_worker_interval=daily_worker_interval,
        weekly_worker_interval=weekly_worker_interval,
        monthly_worker_interval=monthly_worker_interval,
        forecast_interval_runs_per_day=forecast_interval_runs_per_day,
        daily_worker_timeout=daily_worker_timeout,
    )

    # Simulation start: 90 days ago (or however many days of journals)
    sim_start = datetime.now(timezone.utc) - timedelta(days=max(total_days + 5, 30))

    snapshots = []
    entries = []
    errors = []

    try:
        await runner.init_pipeline()

        # Group journals by day
        journals_by_day: Dict[int, List[Dict]] = {}
        for j in journals:
            journals_by_day.setdefault(j["day"], []).append(j)

        # Process day by day
        for day in range(1, total_days + 1):
            day_journals = journals_by_day.get(day, [])
            day_reference_ts = _get_entry_timestamp(sim_start, day, "evening")

            for occurrence_index, j in enumerate(day_journals):
                timestamp = _get_entry_timestamp(
                    sim_start,
                    day,
                    j.get("time_of_day", "evening"),
                    occurrence_index=occurrence_index,
                )
                try:
                    result = await runner.process_journal(
                        content=j["content"],
                        timestamp=timestamp,
                        day=day,
                    )
                    entries.append({
                        "day": day,
                        "time_of_day": j.get("time_of_day", "evening"),
                        "content": j["content"],
                        "timestamp": timestamp.isoformat(),
                        "reply": result.get("reply", ""),
                        "friction_state": result.get("friction_state"),
                    })
                except Exception as exc:
                    LOGGER.error(f"[Day {day}] Journal processing failed: {exc}")
                    errors.append({"day": day, "error": str(exc)})

            # Run production cadence across daily + weekly + monthly + interval.
            should_run_daily = day % daily_worker_interval == 0
            should_run_weekly = day % weekly_worker_interval == 0
            should_run_monthly = day % monthly_worker_interval == 0
            should_run_interval = runner.forecast_interval_runs_per_day > 0

            if should_run_daily or should_run_weekly or should_run_monthly or should_run_interval:
                await runner._force_drain_all(timeout=5.0)
                worker_results: Dict[str, Any] = {}
                if should_run_daily:
                    worker_results.update(await runner.run_daily_workers(day))
                if should_run_weekly:
                    worker_results.update(await runner.run_weekly_workers(day))
                if should_run_monthly:
                    worker_results.update(await runner.run_monthly_workers(day))
                if should_run_interval:
                    worker_results.update(await runner.run_interval_workers(day))
                runner._last_worker_results = worker_results
                await runner._force_drain_all(timeout=5.0)

            # Capture snapshot (pass simulated timestamp for drift computation).
            if day % runner.snapshot_interval == 0:
                try:
                    snapshot = await asyncio.wait_for(
                        runner.capture_snapshot(day, reference_time=day_reference_ts),
                        timeout=snapshot_timeout,
                    )
                    snapshots.append(snapshot)
                except asyncio.TimeoutError:
                    LOGGER.warning(f"[Day {day}] Snapshot timed out")

            if day % 5 == 0:
                LOGGER.info(f"[{persona['name']}] Day {day}/{total_days}")

        # Final daily workers + snapshot
        if journals:
            final_ts = _get_entry_timestamp(sim_start, total_days, "evening")
            await asyncio.sleep(2)
            await runner._force_drain_all(timeout=5.0)
            final_worker_results: Dict[str, Any] = {}
            if total_days % daily_worker_interval != 0:
                final_worker_results.update(await runner.run_daily_workers(total_days))
            if total_days % weekly_worker_interval != 0:
                final_worker_results.update(await runner.run_weekly_workers(total_days))
            if total_days % monthly_worker_interval != 0:
                final_worker_results.update(await runner.run_monthly_workers(total_days))
            if final_worker_results:
                runner._last_worker_results = final_worker_results
                await runner._force_drain_all(timeout=5.0)
            try:
                final = await asyncio.wait_for(
                    runner.capture_snapshot(total_days, reference_time=final_ts),
                    timeout=final_snapshot_timeout,
                )
                snapshots.append(final)
            except asyncio.TimeoutError:
                LOGGER.warning("Final snapshot timed out")

        # Run conversation demo
        conversation_demo = []
        demo_questions = [
            "I'm feeling stuck today, any suggestions?",
            "Should I push through or take a break?",
            "What should I focus on this week?",
        ]
        demo_env_overrides = {
            # Keep the post-simulation demo focused on the synthesized brain state,
            # not a growing 30-day chat transcript.
            "SAKHI_CONVERSATION_COMPRESS_THRESHOLD": "9999",
            "SAKHI_CONVERSATION_RECENT_LIMIT": "4",
        }
        demo_env_previous = {key: os.environ.get(key) for key in demo_env_overrides}
        try:
            await runner._force_drain_all(timeout=5.0)
            os.environ.update(demo_env_overrides)

            for q in demo_questions:
                try:
                    runner._tasks_before_turn = runner._snapshot_tasks()
                    resp = await runner._parity_client.post(
                        "/v2/turn",
                        params={"user": user_id, "debug": "1"},
                        json={"text": q},
                    )
                    await runner._drain_background_tasks(timeout=120.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        conversation_demo.append({
                            "question": q,
                            "response": data.get("reply", ""),
                        })
                    else:
                        conversation_demo.append({"question": q, "error": resp.text[:200]})
                except Exception as exc:
                    conversation_demo.append({"question": q, "error": str(exc)})
        finally:
            for key, value in demo_env_previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        # Run governance scenario (if defined)
        governance_result = None
        scenario = persona.get("governance_scenario")
        if scenario:
            try:
                # Seed governance constraints, objectives, and ledger events
                from sakhi.apps.api.services.demo.governance_seeder import seed_governance_demo_data
                await seed_governance_demo_data(person_id=user_id)
                LOGGER.info("Seeded governance data for %s", user_id)

                from sakhi.apps.api.services.governance.service import evaluate_turn
                governance_result = await evaluate_turn(
                    person_id=user_id,
                    action_context={
                        **scenario,
                        "entity_id": user_id,             # needed for contradiction detection
                        "action": scenario.get("proposed_action", ""),  # gate.py reads "action"
                    },
                )
                governance_result = _safe_json(governance_result)
                LOGGER.info(f"Governance result: {governance_result}")
            except Exception as exc:
                LOGGER.warning(f"Governance evaluation failed: {exc}")
                governance_result = {"error": str(exc)}

    finally:
        await runner.close_pipeline()

        if cleanup:
            await cleanup_user(db_exec, user_id)
        else:
            LOGGER.info(f"Keeping data in DB (user_id: {user_id})")

    # ── Export ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{persona_id}.json"

    export_data = {
        "persona_id": persona_id,
        "user_id": user_id,
        "persona": persona,
        "total_days": total_days,
        "total_entries": len(entries),
        "entries": entries,
        "snapshots": snapshots,
        "conversation_demo": conversation_demo,
        "governance_result": governance_result,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_pipeline": True,
        "production_parity": True,
    }
    enrich_simulation_payload(export_data, persona_id=persona_id)

    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"\n{'='*60}")
    print(f"COMPLETE: {persona['name']}")
    print(f"{'='*60}")
    print(f"  Days:       {total_days}")
    print(f"  Entries:    {len(entries)}")
    print(f"  Snapshots:  {len(snapshots)}")
    print(f"  Errors:     {len(errors)}")
    print(f"  Governance: {governance_result.get('decision', 'N/A') if isinstance(governance_result, dict) else 'N/A'}")
    print(f"  Output:     {output_path} ({size_kb:.0f} KB)")
    print(f"{'='*60}\n")

    return output_path


async def main():
    parser = argparse.ArgumentParser(description="Run demo personas through real Sakhi pipeline")
    parser.add_argument("--persona", "-p", help="Persona ID (vidhya, diya, bigd)")
    parser.add_argument("--all", "-a", action="store_true", help="Run all personas")
    parser.add_argument("--days", "-d", type=int, help="Override max simulation days")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep data in DB")
    parser.add_argument("--daily-interval", type=int, default=1, help="Run daily workers every N days")
    parser.add_argument("--weekly-interval", type=int, default=7, help="Run weekly workers every N days")
    parser.add_argument("--monthly-interval", type=int, default=30, help="Run monthly workers every N days")
    parser.add_argument("--forecast-runs-per-day", type=int, help="Extra intraday forecast runs per day")
    parser.add_argument("--worker-timeout", type=float, default=30.0, help="Timeout per daily worker execution (seconds)")
    parser.add_argument("--snapshot-timeout", type=float, default=90.0, help="Timeout for periodic snapshot capture (seconds)")
    parser.add_argument("--final-snapshot-timeout", type=float, default=30.0, help="Timeout for final snapshot capture (seconds)")
    parser.add_argument("--list", "-l", action="store_true", help="List available personas")
    parser.add_argument("--list-worker-frequency", action="store_true", help="Print production vs simulation frequency for simulation workers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.list:
        print("\nAvailable personas:")
        for pid in list_personas():
            p = load_persona_def(pid)
            journals = p.get("journals", [])
            print(f"  - {pid}: {p['name']} ({len(journals)} journals)")
        return

    if args.list_worker_frequency:
        print(
            render_worker_frequency_table(
                daily_worker_interval=args.daily_interval,
                weekly_worker_interval=args.weekly_interval,
                monthly_worker_interval=args.monthly_interval,
                forecast_interval_runs_per_day=args.forecast_runs_per_day,
            )
        )
        return

    if not args.persona and not args.all:
        parser.error("Must specify --persona or --all (or --list / --list-worker-frequency)")

    persona_ids = list_personas() if args.all else [args.persona]

    for pid in persona_ids:
        if pid not in PERSONA_UUIDS:
            print(f"Warning: No UUID assigned for '{pid}', skipping")
            continue
        try:
            await run_persona(
                persona_id=pid,
                max_days=args.days,
                cleanup=not args.no_cleanup,
                daily_worker_interval=args.daily_interval,
                weekly_worker_interval=args.weekly_interval,
                monthly_worker_interval=args.monthly_interval,
                forecast_interval_runs_per_day=args.forecast_runs_per_day,
                daily_worker_timeout=args.worker_timeout,
                snapshot_timeout=args.snapshot_timeout,
                final_snapshot_timeout=args.final_snapshot_timeout,
            )
        except Exception as exc:
            LOGGER.error(f"Failed {pid}: {exc}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
