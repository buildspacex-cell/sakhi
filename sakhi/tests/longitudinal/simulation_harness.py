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
        """
        self.persona = persona
        self.db_query = db_query
        self.db_exec = db_exec
        self.simulation_start = simulation_start or (
            datetime.now(timezone.utc) - timedelta(days=90)
        )
        self.snapshot_interval = snapshot_interval
        self.run_workers = run_workers

        self.user_id: Optional[str] = None
        self.result: Optional[SimulationResult] = None
        self._created_entries: List[str] = []
        self._raw_entries: List[Dict[str, Any]] = []
        self._last_entry_content: str = ""
        self._last_entry_ts: datetime = datetime.now(timezone.utc)

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

    async def cleanup(self) -> None:
        """Clean up test data after simulation."""
        if not self.user_id:
            return

        # Delete in reverse dependency order — includes all tables real workers write to
        tables = [
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

        total_days = max_days or self.persona.arc.total_days
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

        # Final snapshot
        final_snapshot = await self._capture_snapshot(total_days, include_checkpoint=True)
        self.result.snapshots.append(final_snapshot)

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
            entry_id = await self._create_entry(day, time_of_day, entry_text)
            self._created_entries.append(entry_id)
            self._raw_entries.append({
                "day": day,
                "time_of_day": time_of_day,
                "content": entry_text,
                "timestamp": self._last_entry_ts.isoformat(),
            })
            self.result.total_entries += 1

            if self.run_workers:
                await self._process_entry(entry_id)

        # Run daily-scheduled workers (ayurvedic pipeline, etc.) every 7 days
        # These are normally triggered by scheduler.py in production but the
        # simulation harness must invoke them explicitly.
        if self.run_workers and day % 7 == 0:
            await self._run_daily_workers(day)

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
        """Create a journal entry in the database."""
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

        # Store for payload construction in _process_entry
        self._last_entry_content = content
        self._last_entry_ts = timestamp

        return entry_id

    async def _process_entry(self, entry_id: str) -> None:
        """
        Process an entry through the REAL worker pipeline.

        Runs both per-turn workers synchronously:
        1. turn_memory_update  → ingest_heavy (STM, embeddings, personal model)
        2. episodic_consolidation_v21 → soul/emotion/rhythm extraction, patterns, memory graph
        """
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

            # Mark entry as processed
            await self.db_exec(
                """
                UPDATE journal_entries
                SET processing_state = 'processed'
                WHERE id = $1
                """,
                entry_id,
            )

        except Exception as exc:
            LOGGER.warning(
                f"[Simulation] Worker processing failed for {entry_id}: {exc}",
                exc_info=True,
            )
            # Continue simulation even if individual entry fails

    async def _run_daily_workers(self, day: int) -> None:
        """
        Run daily-scheduled workers that are normally triggered by scheduler.py.

        In production these run once per day via Celery beat. The simulation
        must call them explicitly so that dosha/elemental/energy state evolves.
        """
        try:
            from sakhi.apps.worker.tasks.ayurvedic_pipeline import run_ayurvedic_pipeline

            LOGGER.info(f"[Simulation] Running daily workers (day {day})")
            await run_ayurvedic_pipeline(self.user_id)
            LOGGER.info(f"[Simulation] Daily workers completed (day {day})")
        except Exception as exc:
            LOGGER.warning(
                f"[Simulation] Daily workers failed on day {day}: {exc}",
                exc_info=True,
            )
            # Non-fatal — simulation continues without dosha evolution

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
        # Attach provenance as extra data (not in dataclass, added dynamically)
        snapshot._provenance = provenance  # type: ignore[attr-defined]
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
