"""
Time-Aware Simulation Harness

Orchestrates longitudinal simulations:
1. Creates test user for simulation
2. Runs day-by-day entry generation
3. Processes entries through workers
4. Captures state snapshots at checkpoints
5. Runs assertions at checkpoints

The harness simulates the passage of time while running workers
synchronously (not via queue) to maintain deterministic behavior.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sakhi.apps.worker.simulation_worker_registry import (
    as_import_tuples,
    interval_import_tuples,
    monthly_import_tuples,
    resolve_forecast_runs_per_day,
    weekly_import_tuples,
)

from .persona_spec import PersonaSpec, Checkpoint
from .entry_generator import generate_day_entries, get_entry_timestamp
from .assertions import AssertionResult, run_checkpoint_assertions

LOGGER = logging.getLogger(__name__)


def _serialize_snapshot(s: "StateSnapshot") -> Dict[str, Any]:
    """Serialize a StateSnapshot to a JSON-safe dict."""
    friction = s.friction_state or {}
    # Extract dosha values from friction state or personal model
    current_dosha = {}
    if isinstance(friction, dict):
        cs = friction.get("current_state") or {}
        if isinstance(cs, dict) and "current_dosha" in cs:
            current_dosha = cs["current_dosha"]
    pm = s.personal_model or {}
    os_data = pm.get("operating_system") or {}
    if isinstance(os_data, str):
        os_data = {}
    baseline = os_data.get("dosha_baseline") or {}

    result = {
        "day": s.day,
        "timestamp": s.timestamp.isoformat() if isinstance(s.timestamp, datetime) else str(s.timestamp),
        "personal_model": _safe_json(pm),
        "memory_count": s.memory_count,
        "pattern_count": s.pattern_count,
        "friction_state": _safe_json(friction),
        "recent_memories": [
            {"content": m.get("content", ""), "created_at": str(m.get("created_at", ""))}
            for m in (s.recent_memories or [])
        ],
    }
    # Include provenance if captured from real pipeline
    prov = getattr(s, "_provenance", None)
    if prov:
        result["provenance"] = prov
    # Include structured brain states (coherence, alignment, emotion, etc.)
    brain_states = getattr(s, "_brain_states", None)
    if brain_states:
        result["brain_states"] = _safe_json(brain_states)
    # Include worker execution results for this snapshot
    worker_results = getattr(s, "_worker_results", None)
    if worker_results:
        result["worker_results"] = worker_results
    # Include theme_states and crystallized_patterns from separate tables
    themes = getattr(s, "_themes", None)
    if themes:
        result["themes"] = _safe_json(themes)
    patterns = getattr(s, "_crystallized_patterns", None)
    if patterns:
        result["crystallized_patterns"] = _safe_json(patterns)
    return result


def _safe_json(obj: Any) -> Any:
    """Convert an object to a JSON-serializable form."""
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
    # Handle asyncpg Record objects and similar
    try:
        return dict(obj)
    except (TypeError, ValueError):
        return str(obj)


@dataclass
class StateSnapshot:
    """Snapshot of Sakhi's understanding at a point in time."""
    day: int
    timestamp: datetime
    personal_model: Dict[str, Any]
    memory_count: int
    pattern_count: int
    friction_state: Dict[str, Any]
    recent_memories: List[Dict[str, Any]]
    checkpoint_results: Optional[List[AssertionResult]] = None


@dataclass
class SimulationResult:
    """Complete result of a longitudinal simulation."""
    persona_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_days: int = 0
    total_entries: int = 0
    snapshots: List[StateSnapshot] = field(default_factory=list)
    checkpoint_results: Dict[int, List[AssertionResult]] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def all_checkpoints_passed(self) -> bool:
        """Check if all checkpoint assertions passed."""
        for day, results in self.checkpoint_results.items():
            if any(not r.passed for r in results):
                return False
        return True

    def to_dict(self, include_persona: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Args:
            include_persona: If True, include full persona spec for demo export.
        """
        result = {
            "persona_id": self.persona_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_days": self.total_days,
            "total_entries": self.total_entries,
            "all_checkpoints_passed": self.all_checkpoints_passed,
            "snapshots": [
                _serialize_snapshot(s) for s in self.snapshots
            ],
            "checkpoint_results": {
                str(day): [
                    {
                        "passed": r.passed,
                        "type": r.assertion_type,
                        "message": r.message,
                    }
                    for r in results
                ]
                for day, results in self.checkpoint_results.items()
            },
            "entries": [
                {
                    "day": e["day"],
                    "time_of_day": e["time_of_day"],
                    "content": e["content"],
                    "timestamp": e["timestamp"],
                }
                for e in self._raw_entries
            ] if hasattr(self, "_raw_entries") else [],
            "errors": self.errors,
        }
        if include_persona and hasattr(self, "_persona_dict"):
            result["persona"] = self._persona_dict
        # Include conversation demo Q&A pairs
        if hasattr(self, "_conversation_demo"):
            result["conversation_demo"] = self._conversation_demo
        return result

    def save(self, path: Path, include_persona: bool = False) -> None:
        """Save simulation result to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(include_persona=include_persona), f, indent=2, default=str)


class SimulationHarness:
    """
    Orchestrates longitudinal testing simulations.

    Manages:
    - Test user creation/cleanup
    - Day-by-day entry generation and processing
    - Worker execution (synchronous)
    - State snapshots and checkpoint verification
    """

    def __init__(
        self,
        persona: PersonaSpec,
        db_query,
        db_exec,
        simulation_start: Optional[datetime] = None,
        snapshot_interval: int = 7,  # Snapshot every N days
        run_workers: bool = True,
        daily_worker_interval: int = 1,  # Run daily workers every simulated day
        weekly_worker_interval: int = 7,  # Run weekly workers every N simulated days
        monthly_worker_interval: int = 30,  # Run monthly workers every N simulated days
        forecast_interval_runs_per_day: Optional[int] = None,  # Extra intraday forecast passes
        production_parity: bool = False,  # Route through /v2/turn endpoint
    ):
        """
        Initialize simulation harness.

        Args:
            persona: The persona to simulate
            db_query: Database query function
            db_exec: Database exec function
            simulation_start: Start date (default: 90 days ago)
            snapshot_interval: Days between state snapshots
            run_workers: Whether to run workers after entries
            daily_worker_interval: Run daily workers every N simulated days.
                Use 1 for production-like daily cadence.
            weekly_worker_interval: Run weekly workers every N simulated days.
            monthly_worker_interval: Run monthly workers every N simulated days.
            forecast_interval_runs_per_day: Number of extra intraday forecast
                passes per simulated day (None = derive from FORECAST_INTERVAL_HOURS).
            production_parity: If True, route entries through the real /v2/turn
                endpoint (same code path as production) instead of direct DB
                inserts + manual worker calls.
        """
        self.persona = persona
        self.db_query = db_query
        self.db_exec = db_exec
        self.simulation_start = simulation_start or (
            datetime.now(timezone.utc) - timedelta(days=90)
        )
        self.snapshot_interval = snapshot_interval
        self.run_workers = run_workers
        self.daily_worker_interval = max(1, daily_worker_interval)
        self.weekly_worker_interval = max(1, weekly_worker_interval)
        self.monthly_worker_interval = max(1, monthly_worker_interval)
        self.forecast_interval_runs_per_day = resolve_forecast_runs_per_day(
            forecast_interval_runs_per_day
        )
        self.production_parity = production_parity

        self.user_id: Optional[str] = None
        self.result: Optional[SimulationResult] = None
        self._created_entries: List[str] = []
        self._raw_entries: List[Dict[str, Any]] = []
        self._last_entry_content: str = ""
        self._last_entry_ts: datetime = datetime.now(timezone.utc)
        self._parity_client: Optional[Any] = None  # httpx.AsyncClient for parity mode
        self._total_days: int = 0

    async def setup(self) -> str:
        """
        Create test user for simulation.

        Returns:
            User ID of created test user
        """
        self.user_id = str(uuid.uuid4())
        short_id = self.user_id[:8]
        test_email = f"sim_{self.persona.id}_{short_id}@test.sakhi.dev"

        # 1) Create persons row (journal_entries + personal_model FK reference persons.id)
        await self.db_exec(
            """
            INSERT INTO persons (id, created_at)
            VALUES ($1, NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            self.user_id,
        )

        # 2) Create auth_users row (profiles FK references auth_users.id)
        await self.db_exec(
            """
            INSERT INTO auth_users (id, email, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            self.user_id,
            test_email,
        )

        # 3) Create user profile
        await self.db_exec(
            """
            INSERT INTO profiles (user_id, email, created_at, updated_at)
            VALUES ($1, $2, NOW(), NOW())
            ON CONFLICT (user_id) DO NOTHING
            """,
            self.user_id,
            test_email,
        )

        # Create personal model with baseline dosha
        baseline = self.persona.dosha_baseline.model_dump()
        os_data = json.dumps({
            "type": self._infer_constitution_type(baseline),
            "dosha_baseline": baseline,
        })
        rhythm_data = json.dumps({
            "slots": {
                "morning": self.persona.rhythm.morning.value,
                "afternoon": self.persona.rhythm.afternoon.value,
                "evening": self.persona.rhythm.evening.value,
            },
        })
        await self.db_exec(
            """
            INSERT INTO personal_model (
                person_id,
                operating_system,
                rhythm_state,
                updated_at
            )
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (person_id) DO NOTHING
            """,
            self.user_id,
            os_data,
            rhythm_data,
        )

        LOGGER.info(
            f"[Simulation] Created test user {self.user_id} for persona {self.persona.id}"
        )
        return self.user_id

    def _infer_constitution_type(self, baseline: Dict[str, float]) -> str:
        """Infer constitution type name from dosha baseline."""
        v, p, k = baseline.get("vata", 0.33), baseline.get("pitta", 0.33), baseline.get("kapha", 0.34)

        if max(v, p, k) < 0.4:
            return "Balanced"
        elif p >= v and p >= k:
            return "Driven"  # Pitta-dominant
        elif v >= p and v >= k:
            return "Quick-moving"  # Vata-dominant
        else:
            return "Steady"  # Kapha-dominant

    async def _init_parity_client(self) -> None:
        """Initialize httpx AsyncClient + ASGITransport for production parity mode.

        Uses the same pattern as e2e tests: routes through the real FastAPI app
        with full lifespan initialization (LLM router, queues, etc.).

        Sets SAKHI_DISABLE_QUEUE=1 so all per-turn workers run inline
        (deterministic, no Redis dependency).
        """
        import os
        os.environ["SAKHI_DISABLE_QUEUE"] = "1"

        from httpx import AsyncClient, ASGITransport
        from sakhi.apps.api.main import app, lifespan

        # Enter lifespan context (initializes LLM router, etc.)
        self._lifespan_cm = lifespan(app)
        await self._lifespan_cm.__aenter__()

        transport = ASGITransport(app=app)
        self._parity_client = AsyncClient(
            transport=transport,
            base_url="http://test",
            timeout=120.0,  # Workers can be slow under LLM load
        )
        LOGGER.info("[Simulation] Production parity client initialized (SAKHI_DISABLE_QUEUE=1)")

    async def _close_parity_client(self) -> None:
        """Shut down the parity client and lifespan."""
        if self._parity_client:
            await self._parity_client.aclose()
            self._parity_client = None
        if hasattr(self, "_lifespan_cm") and self._lifespan_cm:
            try:
                await self._lifespan_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._lifespan_cm = None

    async def cleanup(self) -> None:
        """Clean up test data after simulation."""
        # Close parity client if it was initialized
        await self._close_parity_client()

        if not self.user_id:
            return

        # Delete in reverse dependency order — includes all tables real workers write to
        # and tables that /v2/turn production flow writes to (sessions, dialog, etc.)
        tables = [
            # Production /v2/turn writes (parity mode)
            "conversation_turns",
            "conversation_sessions",
            "dialog_state",
            "reflection_traces",
            "micro_goals",
            "focus_paths",
            "mini_flows",
            "user_intents",
            "user_preferences",
            "behavior_symptom_log",
            "pattern_stats",
            # Worker output tables
            "theme_states",
            "pattern_occurrences",
            "crystallized_patterns",
            "memory_edges",
            "memory_nodes",
            "memory_episodic",
            "memory_short_term",
            "memory_context_cache",
            "journal_embeddings",
            "narrative_arc_cache",
            "wellness_state_cache",
            # Ayurvedic pipeline tables (elemental/energy workers)
            "elemental_signal_stm",
            "elemental_weekly_aggregates",
            "elemental_monthly_aggregates",
            "energy_weekly_aggregates",
            "energy_monthly_aggregates",
            "journal_entries",
            "personal_model",
            "profiles",
            "auth_users",
            "persons",
        ]

        for table in tables:
            try:
                # Most tables use person_id; some use user_id or id
                user_id_tables = {
                    "memory_episodic", "journal_entries", "memory_short_term",
                    "profiles",
                }
                id_tables = {"auth_users", "persons"}
                # journal_embeddings uses entry_id, not person_id — skip FK cleanup
                if table == "journal_embeddings":
                    # Delete via subquery on journal_entries
                    await self.db_exec(
                        """
                        DELETE FROM journal_embeddings
                        WHERE entry_id IN (
                            SELECT id FROM journal_entries WHERE user_id = $1
                        )
                        """,
                        self.user_id,
                    )
                    continue
                col = "id" if table in id_tables else "user_id" if table in user_id_tables else "person_id"
                await self.db_exec(
                    f"DELETE FROM {table} WHERE {col} = $1",
                    self.user_id,
                )
            except Exception as exc:
                LOGGER.warning(f"Cleanup of {table} failed: {exc}")

        LOGGER.info(f"[Simulation] Cleaned up test user {self.user_id}")

    async def run(self, max_days: Optional[int] = None) -> SimulationResult:
        """
        Run the full simulation.

        Args:
            max_days: Optional limit on simulation days

        Returns:
            SimulationResult with all data
        """
        if not self.user_id:
            await self.setup()

        # Initialize production parity client if enabled
        if self.production_parity:
            await self._init_parity_client()

        total_days = max_days or self.persona.arc.total_days
        self._total_days = total_days
        self.result = SimulationResult(
            persona_id=self.persona.id,
            user_id=self.user_id,
            start_time=datetime.now(timezone.utc),
            total_days=total_days,
        )

        # Attach raw entries list and persona to result for export
        self.result._raw_entries = self._raw_entries
        self.result._persona_dict = self.persona.to_dict() if hasattr(self.persona, "to_dict") else {}

        LOGGER.info(
            f"[Simulation] Starting {total_days}-day simulation for persona {self.persona.id}"
        )

        for day in range(1, total_days + 1):
            try:
                await self._run_day(day)

                # Check for checkpoint
                checkpoint = self.persona.get_checkpoint_at_day(day)
                if checkpoint:
                    await self._run_checkpoint(checkpoint)

                # Periodic snapshots
                if day % self.snapshot_interval == 0:
                    snapshot = await self._capture_snapshot(day)
                    self.result.snapshots.append(snapshot)

            except Exception as exc:
                LOGGER.error(f"[Simulation] Day {day} failed: {exc}")
                self.result.errors.append({
                    "day": day,
                    "error": str(exc),
                    "type": type(exc).__name__,
                })

        # Let background tasks (soul_extract, context_refresh) drain before daily workers
        await asyncio.sleep(2)

        # Flush any cadence groups that did not run on the final simulated day.
        if self.run_workers:
            final_worker_results: Dict[str, Any] = {}
            if total_days % self.daily_worker_interval != 0:
                final_worker_results.update(await self._run_daily_workers(total_days))
            if total_days % self.weekly_worker_interval != 0:
                final_worker_results.update(await self._run_weekly_workers(total_days))
            if total_days % self.monthly_worker_interval != 0:
                final_worker_results.update(await self._run_monthly_workers(total_days))
            if final_worker_results:
                self._last_worker_results = final_worker_results

        # Final snapshot
        final_snapshot = await self._capture_snapshot(total_days, include_checkpoint=True)
        self.result.snapshots.append(final_snapshot)

        # Run conversation demo — ask questions with the fully-built brain
        if self.run_workers:
            LOGGER.info("[Simulation] Running conversation demo with full brain...")
            self.result._conversation_demo = await self._run_conversation_demo()  # type: ignore[attr-defined]

        self.result.end_time = datetime.now(timezone.utc)

        LOGGER.info(
            f"[Simulation] Completed: {self.result.total_entries} entries, "
            f"{len(self.result.checkpoint_results)} checkpoints, "
            f"all passed: {self.result.all_checkpoints_passed}"
        )

        return self.result

    async def _run_day(self, day: int) -> None:
        """Process a single simulation day."""
        # Generate entries for this day
        entries = await generate_day_entries(
            persona=self.persona,
            day=day,
        )

        for time_of_day, entry_text in entries:
            timestamp = get_entry_timestamp(self.simulation_start, day, time_of_day)
            self._last_entry_content = entry_text
            self._last_entry_ts = timestamp

            if self.production_parity:
                # Route through real /v2/turn endpoint — full production code path
                entry_id = await self._process_entry_parity(day, time_of_day, entry_text, timestamp)
            else:
                # Legacy path: direct DB insert + manual worker calls
                entry_id = await self._create_entry(day, time_of_day, entry_text)
                if self.run_workers:
                    await self._process_entry(entry_id)

            if entry_id:
                self._created_entries.append(entry_id)
            self._raw_entries.append({
                "day": day,
                "time_of_day": time_of_day,
                "content": entry_text,
                "timestamp": timestamp.isoformat(),
            })
            self.result.total_entries += 1

        # Run production worker cadence across daily + weekly + monthly + intraday.
        if self.run_workers:
            should_run_daily = day % self.daily_worker_interval == 0
            should_run_weekly = day % self.weekly_worker_interval == 0
            should_run_monthly = day % self.monthly_worker_interval == 0
            should_run_interval = self.forecast_interval_runs_per_day > 0

            if should_run_daily or should_run_weekly or should_run_monthly or should_run_interval:
                # Drain any lingering background tasks from the last parity turn
                # before running cadence workers. Without this, undrained tasks can
                # hold DB pool connections and starve worker execution.
                if self.production_parity:
                    self._tasks_before_turn = self._snapshot_tasks()
                    await self._drain_background_tasks(timeout=15.0)

                worker_results: Dict[str, Any] = {}
                if should_run_daily:
                    worker_results.update(await self._run_daily_workers(day))
                if should_run_weekly:
                    worker_results.update(await self._run_weekly_workers(day))
                if should_run_monthly:
                    worker_results.update(await self._run_monthly_workers(day))
                if should_run_interval:
                    worker_results.update(await self._run_interval_workers(day))

                # Drain any background tasks spawned by cadence workers.
                if self.production_parity:
                    self._tasks_before_turn = self._snapshot_tasks()
                    await self._drain_background_tasks(timeout=15.0)

                # Store for provenance in next snapshot
                self._last_worker_results = worker_results

        if day % 10 == 0:
            LOGGER.info(
                f"[Simulation] Day {day}/{self.persona.arc.total_days}: "
                f"{len(entries)} entries"
            )

    async def _create_entry(
        self,
        day: int,
        time_of_day: str,
        content: str,
    ) -> str:
        """Create a journal entry in the database (legacy path)."""
        entry_id = str(uuid.uuid4())
        timestamp = get_entry_timestamp(self.simulation_start, day, time_of_day)

        await self.db_exec(
            """
            INSERT INTO journal_entries (
                id, user_id, content, layer, ts, created_at, updated_at, processing_state
            )
            VALUES ($1, $2, $3, 'reflection', $4, $4, $4, 'pending')
            """,
            entry_id,
            self.user_id,
            content,
            timestamp,
        )

        return entry_id

    async def _process_entry(self, entry_id: str) -> None:
        """
        Process an entry through the REAL worker pipeline.

        Runs all 5 per-turn workers synchronously (same as production):
        1. turn_memory_update  → ingest_heavy (STM, embeddings, personal model)
        2. episodic_consolidation_v21 → soul/emotion/rhythm extraction, patterns, memory graph
        3. preference_learning → extract preferences + feedback + behavior→symptom patterns
        4. journal_enrich → LLM enrichment of journal entry
        5. intent_extraction → extract user intents
        """
        self._tasks_before_turn = self._snapshot_tasks()
        try:
            from sakhi.apps.worker.pipelines.turn_updates.runner import (
                process_turn_job_async,
            )

            content = getattr(self, "_last_entry_content", "")
            ts = getattr(self, "_last_entry_ts", datetime.now(timezone.utc))

            payload = {
                "text": content,
                "ts": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "entry_id": entry_id,
                "thread_id": self.user_id,
                "user_id": self.user_id,
                "mode": "today",
            }

            # 1) Memory update: STM, embeddings, personal model, identity graph
            await process_turn_job_async(
                job_type="turn_memory_update",
                turn_id=entry_id,
                person_id=self.user_id,
                payload=payload,
            )

            # 2) Episodic consolidation: summarize day, extract signals, patterns, memory graph
            await process_turn_job_async(
                job_type="episodic_consolidation_v21",
                turn_id=f"{entry_id}_episodic",
                person_id=self.user_id,
                payload=payload,
            )

            # 3) Preference learning: "I like X" + feedback + behavior→symptom patterns
            await process_turn_job_async(
                job_type="preference_learning",
                turn_id=f"{entry_id}_pref",
                person_id=self.user_id,
                payload=payload,
            )

            # 4) Journal enrichment: LLM extracts meaning, annotations
            await process_turn_job_async(
                job_type="journal_enrich",
                turn_id=f"{entry_id}_enrich",
                person_id=self.user_id,
                payload=payload,
            )

            # 5) Intent extraction: LLM extracts intents ("I want to...", "I plan to...")
            await process_turn_job_async(
                job_type="intent_extraction",
                turn_id=f"{entry_id}_intent",
                person_id=self.user_id,
                payload=payload,
            )

            # Mark entry as processed
            await self.db_exec(
                """
                UPDATE journal_entries
                SET processing_state = 'processed'
                WHERE id = $1
                """,
                entry_id,
            )

            # Drain fire-and-forget background tasks (soul_extract_worker,
            # soul_refresh_worker, context_refresh_worker) spawned by
            # ingest_heavy via asyncio.create_task(). Without this, these
            # tasks hold DB pool connections indefinitely, eventually
            # exhausting the pool and deadlocking the simulation.
            await self._drain_background_tasks()

        except Exception as exc:
            LOGGER.warning(
                f"[Simulation] Worker processing failed for {entry_id}: {exc}",
                exc_info=True,
            )
            # Continue simulation even if individual entry fails

    async def _process_entry_parity(
        self,
        day: int,
        time_of_day: str,
        content: str,
        timestamp: datetime,
    ) -> Optional[str]:
        """
        Process an entry through the REAL /v2/turn endpoint.

        This is production parity mode: the entry goes through the exact same
        code path as a real user message — orchestrate_turn, triage, deterministic
        context loading, generate_reply, post-reply processing (sessions, memory,
        workers). SAKHI_DISABLE_QUEUE=1 ensures workers run inline.

        After the turn completes, we backdate the journal entry timestamp to the
        simulated date (since TurnIn doesn't accept a timestamp field).

        Returns:
            The entry_id created by orchestrate_turn, or None on failure.
        """
        if not self._parity_client:
            LOGGER.error("[Simulation] Parity client not initialized")
            return None

        # Snapshot existing episodic IDs before turn (for precise backdating)
        existing_episodic_ids: set = set()
        try:
            rows = await self.db_query(
                "SELECT id FROM memory_episodic WHERE user_id = $1",
                self.user_id,
            )
            existing_episodic_ids = {str(r["id"]) for r in (rows or [])}
        except Exception:
            pass

        self._tasks_before_turn = self._snapshot_tasks()

        try:
            response = await self._parity_client.post(
                "/v2/turn",
                params={"user": self.user_id},
                json={"text": content},
            )

            if response.status_code != 200:
                LOGGER.warning(
                    f"[Simulation][Parity] /v2/turn returned {response.status_code} "
                    f"(day {day}, {time_of_day}): {response.text[:200]}"
                )
                return None

            data = response.json()
            entry_id = data.get("entry_id")
            reply = data.get("reply", "")

            LOGGER.info(
                f"[Simulation][Parity] day {day} {time_of_day}: "
                f"entry={entry_id}, reply_len={len(reply)}"
            )

            # Drain background tasks spawned by post-reply processing
            # (asyncio.create_task in turn_v2.py: _run_post_reply_processing,
            # plus ingest_heavy's soul_extract_worker, etc.)
            await self._drain_background_tasks()

            # Backdate all rows created by this turn to the simulated timestamp.
            # /v2/turn uses datetime.utcnow(), but simulation needs entries
            # spread across a 60+ day arc. Without backdating, the deterministic
            # context loader sees zero time gaps between turns (it reads
            # conversation_turns.created_at for gap logic).
            if entry_id:
                await self._backdate_turn_rows(
                    entry_id=str(entry_id),
                    timestamp=timestamp,
                    existing_episodic_ids=existing_episodic_ids,
                )

            return str(entry_id) if entry_id else None

        except Exception as exc:
            LOGGER.warning(
                f"[Simulation][Parity] Failed day {day} {time_of_day}: {exc}",
                exc_info=True,
            )
            return None

    async def _backdate_turn_rows(
        self,
        entry_id: str,
        timestamp: datetime,
        existing_episodic_ids: set,
    ) -> None:
        """Backdate all DB rows created by a parity turn to the simulated timestamp.

        Covers: journal_entries, conversation_turns, conversation_sessions,
        memory_short_term, and memory_episodic.
        """
        # journal_entries
        await self.db_exec(
            """
            UPDATE journal_entries
            SET ts = $2, created_at = $2, updated_at = $2
            WHERE id = $1
            """,
            entry_id,
            timestamp,
        )

        # conversation_turns — critical for deterministic_context_loader gap logic
        try:
            await self.db_exec(
                """
                UPDATE conversation_turns
                SET created_at = $2
                WHERE user_id = $1
                  AND created_at > NOW() - INTERVAL '30 seconds'
                  AND created_at <= NOW()
                """,
                self.user_id,
                timestamp,
            )
        except Exception:
            pass

        # conversation_sessions.last_active_at — used for session continuity
        try:
            await self.db_exec(
                """
                UPDATE conversation_sessions
                SET last_active_at = $2, created_at = LEAST(created_at, $2)
                WHERE user_id = $1
                  AND last_active_at > NOW() - INTERVAL '30 seconds'
                """,
                self.user_id,
                timestamp,
            )
        except Exception:
            pass

        # memory_short_term
        try:
            await self.db_exec(
                """
                UPDATE memory_short_term
                SET created_at = $2
                WHERE entry_id = $1
                """,
                entry_id,
                timestamp,
            )
        except Exception:
            pass

        # memory_episodic — precise ID diff (no time heuristic)
        try:
            all_rows = await self.db_query(
                "SELECT id FROM memory_episodic WHERE user_id = $1",
                self.user_id,
            )
            new_ids = [
                str(r["id"]) for r in (all_rows or [])
                if str(r["id"]) not in existing_episodic_ids
            ]
            for eid in new_ids:
                await self.db_exec(
                    "UPDATE memory_episodic SET created_at = $2 WHERE id = $1",
                    eid,
                    timestamp,
                )
        except Exception:
            pass

    def _snapshot_tasks(self) -> set:
        """Capture the current set of asyncio tasks (for diffing after a turn)."""
        current = asyncio.current_task()
        return {t for t in asyncio.all_tasks() if t is not current and not t.done()}

    async def _drain_background_tasks(self, timeout: float = 30.0) -> None:
        """Await background tasks spawned since the last snapshot.

        Only drains tasks that were NOT present before the turn started,
        avoiding accidental cancellation of unrelated long-running tasks
        (e.g. lifespan, ASGI server internals).

        If no snapshot was taken (legacy path), falls back to draining all
        non-current pending tasks.
        """
        current = asyncio.current_task()
        baseline = getattr(self, "_tasks_before_turn", None)

        if baseline is not None:
            # Only drain tasks that are new since the snapshot
            new_tasks = {
                t for t in asyncio.all_tasks()
                if t is not current and not t.done() and t not in baseline
            }
        else:
            # Fallback: drain all pending (legacy path without snapshot)
            new_tasks = {
                t for t in asyncio.all_tasks()
                if t is not current and not t.done()
            }

        if new_tasks:
            done, still_pending = await asyncio.wait(
                new_tasks, timeout=timeout
            )
            for t in still_pending:
                t.cancel()
            # Suppress CancelledError from cancelled tasks
            for t in done | still_pending:
                if t.done():
                    try:
                        t.result()
                    except (asyncio.CancelledError, Exception):
                        pass

    # Canonical production-aligned worker lists shared across simulation
    # harnesses and the profile updater.
    DAILY_WORKER_SPECS = as_import_tuples()
    WEEKLY_WORKER_SPECS = weekly_import_tuples()
    MONTHLY_WORKER_SPECS = monthly_import_tuples()
    INTERVAL_WORKER_SPECS = interval_import_tuples()

    async def _run_worker_group(
        self,
        *,
        day: int,
        phase_name: str,
        worker_specs: List[tuple[str, str, str]],
        key_prefix: str,
    ) -> Dict[str, Any]:
        """Run one cadence worker group with lazy imports and per-worker isolation."""
        import importlib

        workers = []
        for name, mod_path, fn_name in worker_specs:
            try:
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, fn_name)
                workers.append((name, fn))
            except Exception as exc:
                LOGGER.warning(
                    f"[Simulation] Could not import {phase_name}.{name} "
                    f"({mod_path}.{fn_name}): {exc}"
                )
                workers.append((name, None))

        LOGGER.info(
            f"[Simulation] Running {len(workers)} {phase_name} workers (day {day})"
        )
        results: Dict[str, Any] = {}
        succeeded = 0
        worker_timeout = 60.0
        for name, fn in workers:
            key = f"{key_prefix}{name}"
            if fn is None:
                results[key] = {"ok": False, "error": "import failed"}
                continue
            try:
                result = await asyncio.wait_for(fn(self.user_id), timeout=worker_timeout)
                results[key] = {"ok": True, "result": str(result)[:200] if result else None}
                succeeded += 1
                LOGGER.info(f"[Simulation]   {phase_name}.{name} OK (day {day})")
            except asyncio.TimeoutError:
                results[key] = {"ok": False, "error": f"timeout ({worker_timeout}s)"}
                LOGGER.warning(
                    f"[Simulation]   {phase_name}.{name} TIMEOUT (day {day}): "
                    f"exceeded {worker_timeout}s"
                )
            except Exception as exc:
                results[key] = {"ok": False, "error": str(exc)}
                LOGGER.warning(f"[Simulation]   {phase_name}.{name} FAILED (day {day}): {exc}")

        LOGGER.info(
            f"[Simulation] {phase_name} workers done: "
            f"{succeeded}/{len(workers)} succeeded (day {day})"
        )
        return results

    async def _run_daily_workers(self, day: int) -> Dict[str, Any]:
        """
        Run production daily workers for this simulated day.
        """
        return await self._run_worker_group(
            day=day,
            phase_name="daily",
            worker_specs=self.DAILY_WORKER_SPECS,
            key_prefix="",
        )

    async def _run_weekly_workers(self, day: int) -> Dict[str, Any]:
        """Run production weekly workers on simulation cadence."""
        return await self._run_worker_group(
            day=day,
            phase_name="weekly",
            worker_specs=self.WEEKLY_WORKER_SPECS,
            key_prefix="weekly.",
        )

    async def _run_monthly_workers(self, day: int) -> Dict[str, Any]:
        """Run production monthly workers on simulation cadence."""
        return await self._run_worker_group(
            day=day,
            phase_name="monthly",
            worker_specs=self.MONTHLY_WORKER_SPECS,
            key_prefix="monthly.",
        )

    async def _run_interval_workers(self, day: int) -> Dict[str, Any]:
        """Run extra intraday workers (forecast refresh intervals)."""
        if self.forecast_interval_runs_per_day <= 0:
            return {}
        results: Dict[str, Any] = {}
        for pass_index in range(1, self.forecast_interval_runs_per_day + 1):
            phase = f"interval#{pass_index}"
            pass_results = await self._run_worker_group(
                day=day,
                phase_name=phase,
                worker_specs=self.INTERVAL_WORKER_SPECS,
                key_prefix=f"interval.{pass_index}.",
            )
            results.update(pass_results)
        return results

    async def _run_conversation_demo(
        self, questions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ask demo questions through the real conversation engine.

        In production_parity mode, routes through /v2/turn (full endpoint).
        Otherwise, calls generate_reply directly.

        After the simulation builds a rich brain, this shows how Sakhi's
        responses are personalized based on the accumulated brain state.
        """
        demo_questions = questions or [
            "I'm feeling stuck today, any suggestions?",
            "Should I push through or take a break?",
            "What should I focus on this week?",
        ]

        results: List[Dict[str, Any]] = []
        for question in demo_questions:
            try:
                if self.production_parity and self._parity_client:
                    # Snapshot before each demo turn so drain is scoped
                    self._tasks_before_turn = self._snapshot_tasks()
                    # Route through real /v2/turn endpoint
                    resp = await self._parity_client.post(
                        "/v2/turn",
                        params={"user": self.user_id, "debug": "1"},
                        json={"text": question},
                    )
                    await self._drain_background_tasks()
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({
                            "question": question,
                            "response": data.get("reply", ""),
                            "debug": {
                                "context_used": list(
                                    (data.get("debug_data") or {}).get("active_modules", [])
                                ),
                                "tone": (data.get("toneBlueprint") or {}),
                            },
                        })
                    else:
                        results.append({
                            "question": question,
                            "response": f"[HTTP {resp.status_code}]",
                            "error": resp.text[:200],
                        })
                else:
                    # Direct call to conversation engine
                    from sakhi.apps.api.services.conversation_v2.conversation_engine import (
                        generate_reply,
                    )
                    response = await generate_reply(
                        person_id=self.user_id,
                        user_text=question,
                        return_debug=True,
                    )
                    results.append({
                        "question": question,
                        "response": response.get("reply", ""),
                        "debug": {
                            "context_used": list(
                                response.get("debug", {}).get("context_keys", [])
                            ),
                            "tone": response.get("debug", {}).get("tone", {}),
                        },
                    })

                reply_text = results[-1].get("response", "")
                LOGGER.info(
                    f"[Simulation] Conversation demo: '{question[:40]}...' -> "
                    f"{len(reply_text)} chars"
                )
            except Exception as exc:
                results.append({
                    "question": question,
                    "response": f"[Error: {exc}]",
                    "error": str(exc),
                })
                LOGGER.warning(
                    f"[Simulation] Conversation demo failed: '{question[:40]}...': {exc}"
                )

        return results

    async def _run_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Run assertions for a checkpoint."""
        LOGGER.info(f"[Simulation] Running checkpoint: {checkpoint.name} (day {checkpoint.day})")

        results = await run_checkpoint_assertions(
            self.db_query,
            self.user_id,
            checkpoint.assertions,
        )

        self.result.checkpoint_results[checkpoint.day] = results

        # Log results
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        LOGGER.info(
            f"[Simulation] Checkpoint '{checkpoint.name}': {passed}/{total} passed"
        )
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            LOGGER.info(f"  [{status}] {r.assertion_type}: {r.message}")

    async def _capture_snapshot(
        self,
        day: int,
        include_checkpoint: bool = False,
    ) -> StateSnapshot:
        """Capture current state snapshot."""
        # Get personal model
        model = await self.db_query(
            """
            SELECT * FROM personal_model WHERE person_id = $1
            """,
            self.user_id,
            one=True,
        )

        # Get memory count
        memory_count = await self.db_query(
            """
            SELECT COUNT(*) as count FROM memory_episodic WHERE user_id = $1
            """,
            self.user_id,
            one=True,
        )

        # Get pattern count
        pattern_count = await self.db_query(
            """
            SELECT COUNT(*) as count FROM pattern_occurrences WHERE person_id = $1
            """,
            self.user_id,
            one=True,
        )

        # Get recent memories (episodic table uses 'text' column, not 'content')
        recent = await self.db_query(
            """
            SELECT id, text AS content, context_tags, created_at
            FROM memory_episodic
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 5
            """,
            self.user_id,
        )

        # Get friction state
        try:
            from sakhi.apps.api.services.ayurveda.vikriti import get_full_friction_state
            friction = await get_full_friction_state(self.user_id)
        except Exception:
            friction = {}

        # Provenance: real DB row counts proving pipeline ran
        provenance = {}
        try:
            stm_count = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_short_term WHERE user_id = $1",
                self.user_id, one=True,
            )
            embed_count = await self.db_query(
                """SELECT COUNT(*) as count FROM journal_embeddings
                   WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)""",
                self.user_id, one=True,
            )
            node_count = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_nodes WHERE person_id = $1",
                self.user_id, one=True,
            )
            edge_count = await self.db_query(
                "SELECT COUNT(*) as count FROM memory_edges WHERE person_id = $1",
                self.user_id, one=True,
            )
            provenance = {
                "stm_rows": stm_count["count"] if stm_count else 0,
                "embedding_rows": embed_count["count"] if embed_count else 0,
                "graph_nodes": node_count["count"] if node_count else 0,
                "graph_edges": edge_count["count"] if edge_count else 0,
            }
        except Exception:
            pass

        snapshot = StateSnapshot(
            day=day,
            timestamp=datetime.now(timezone.utc),
            personal_model=dict(model) if model else {},
            memory_count=memory_count["count"] if memory_count else 0,
            pattern_count=pattern_count["count"] if pattern_count else 0,
            friction_state=friction,
            recent_memories=[dict(r) for r in recent] if recent else [],
        )
        # Capture crystallized patterns + theme states from separate tables
        theme_data: List[Dict[str, Any]] = []
        pattern_data: List[Dict[str, Any]] = []
        try:
            themes_raw = await self.db_query(
                """SELECT theme, clarity_score, updated_at
                   FROM theme_states WHERE person_id = $1
                   ORDER BY clarity_score DESC LIMIT 20""",
                self.user_id,
            )
            theme_data = [dict(r) for r in themes_raw] if themes_raw else []
        except Exception:
            pass
        try:
            patterns_raw = await self.db_query(
                """SELECT pattern_type, pattern_value, confidence, trajectory,
                          status, mention_count, distinct_days
                   FROM crystallized_patterns WHERE person_id = $1
                   AND status IN ('active', 'emerging')
                   ORDER BY confidence DESC LIMIT 30""",
                self.user_id,
            )
            pattern_data = [dict(r) for r in patterns_raw] if patterns_raw else []
        except Exception:
            pass

        # Attach provenance as extra data (not in dataclass, added dynamically)
        snapshot._provenance = provenance  # type: ignore[attr-defined]
        snapshot._themes = theme_data  # type: ignore[attr-defined]
        snapshot._crystallized_patterns = pattern_data  # type: ignore[attr-defined]

        # Extract structured brain states from personal_model for frontend
        brain_states: Dict[str, Any] = {}
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
        snapshot._brain_states = brain_states  # type: ignore[attr-defined]

        # Attach last worker results if available
        snapshot._worker_results = getattr(self, "_last_worker_results", {})  # type: ignore[attr-defined]
        self._last_worker_results: Dict[str, Any] = {}  # Reset after capture

        return snapshot


async def run_simulation(
    persona_id: str,
    db_query,
    db_exec,
    max_days: Optional[int] = None,
    cleanup_after: bool = True,
) -> SimulationResult:
    """
    Convenience function to run a full simulation.

    Args:
        persona_id: ID of persona to simulate
        db_query: Database query function
        db_exec: Database exec function
        max_days: Optional day limit
        cleanup_after: Whether to clean up test data

    Returns:
        SimulationResult
    """
    from .persona_spec import load_persona

    persona = load_persona(persona_id)
    harness = SimulationHarness(
        persona=persona,
        db_query=db_query,
        db_exec=db_exec,
    )

    try:
        await harness.setup()
        result = await harness.run(max_days=max_days)
        return result
    finally:
        if cleanup_after:
            await harness.cleanup()


__all__ = [
    "SimulationHarness",
    "SimulationResult",
    "StateSnapshot",
    "run_simulation",
]
