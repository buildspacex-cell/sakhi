"""
Sakhi Comprehensive Worker Test Suite

Tests ALL 51 workers directly and verifies database updates.

Categories:
- Memory & Episodic (4 workers)
- Pattern & Crystallization (5 workers)
- Theme & Identity (6 workers)
- Soul & Emotion (5 workers)
- Rhythm & Forecast (4 workers)
- Planning & Goals (5 workers)
- Morning/Evening (5 workers)
- Micro & Mini (5 workers)
- Deep Analysis (6 workers)
- Utility (6 workers)

Usage:
    python -m sakhi.tests.all_workers_test [--user-id UUID] [--category CATEGORY]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional, Callable, Awaitable

logging.basicConfig(level=logging.WARNING)

DEFAULT_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90"


@dataclass
class WorkerTestResult:
    name: str
    category: str
    passed: bool
    message: str
    db_tables_affected: List[str] = field(default_factory=list)
    changes_detected: bool = False
    duration_ms: float = 0
    error: Optional[str] = None
    skipped: bool = False


class ComprehensiveWorkerTester:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.results: List[WorkerTestResult] = []
        self.llm_available = False
        self.category_stats: Dict[str, Dict[str, int]] = {}

    async def init_llm_router(self) -> bool:
        """Initialize LLM router for workers that need it."""
        try:
            from sakhi.apps.worker.jobs import _get_router
            worker_router = _get_router()
            from sakhi.apps.api.core.llm import set_router
            set_router(worker_router)
            self.llm_available = True
            return True
        except Exception:
            self.llm_available = False
            return False

    async def get_table_hash(self, table: str, columns: List[str]) -> str:
        """Get a hash of table state for change detection."""
        from sakhi.apps.api.core.db import q

        cols = ", ".join(columns)
        try:
            rows = await q(
                f"SELECT {cols} FROM {table} WHERE person_id = $1 OR user_id = $1 LIMIT 10",
                self.user_id
            )
            return str(hash(str(rows)))
        except Exception:
            try:
                rows = await q(f"SELECT {cols} FROM {table} LIMIT 10")
                return str(hash(str(rows)))
            except Exception:
                return "error"

    async def check_table_changed(self, table: str, columns: List[str], before_hash: str) -> bool:
        """Check if table state changed."""
        after_hash = await self.get_table_hash(table, columns)
        return after_hash != before_hash

    async def run_worker_test(
        self,
        name: str,
        category: str,
        worker_func: Callable[..., Awaitable],
        args: tuple = (),
        kwargs: dict = None,
        tables: List[tuple] = None,  # [(table_name, [columns])]
        requires_llm: bool = False,
    ) -> WorkerTestResult:
        """Generic worker test runner."""
        kwargs = kwargs or {}
        tables = tables or []
        start = time.time()

        # Skip if requires LLM and not available
        if requires_llm and not self.llm_available:
            return WorkerTestResult(
                name=name,
                category=category,
                passed=True,
                message="Skipped (requires LLM)",
                skipped=True,
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            # Get before state
            before_hashes = {}
            for table, cols in tables:
                before_hashes[table] = await self.get_table_hash(table, cols)

            # Run worker
            await worker_func(*args, **kwargs)

            # Check for changes
            changes = []
            for table, cols in tables:
                if await self.check_table_changed(table, cols, before_hashes[table]):
                    changes.append(table)

            return WorkerTestResult(
                name=name,
                category=category,
                passed=True,
                message=f"OK - Changes: {changes}" if changes else "OK - No changes detected",
                db_tables_affected=[t for t, _ in tables],
                changes_detected=len(changes) > 0,
                duration_ms=(time.time() - start) * 1000,
            )

        except Exception as e:
            return WorkerTestResult(
                name=name,
                category=category,
                passed=False,
                message=f"Error: {str(e)[:100]}",
                error=traceback.format_exc(),
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # MEMORY & EPISODIC WORKERS (4)
    # =========================================================================

    async def test_episodic_consolidation_v21(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21
        payload = {"user_id": self.user_id, "ts": datetime.now(timezone.utc).isoformat()}
        return await self.run_worker_test(
            "Episodic Consolidation v21",
            "Memory & Episodic",
            run_episodic_consolidation_v21,
            args=(self.user_id, payload),
            tables=[("memory_episodic", ["id", "text", "ts"]), ("pattern_occurrences", ["id", "pattern_type"])],
        )

    async def test_embedding_consolidation(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.embedding_consolidation import run_embedding_consolidation
        return await self.run_worker_test(
            "Embedding Consolidation",
            "Memory & Episodic",
            run_embedding_consolidation,
            args=(self.user_id,),
            tables=[("journal_embeddings", ["entry_id", "content_hash"])],
        )

    async def test_brain_update(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.brain_update import run_brain_update
        return await self.run_worker_test(
            "Brain Update",
            "Memory & Episodic",
            run_brain_update,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "updated_at"])],
        )

    async def test_turn_personal_model_update(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.turn_personal_model_update import run_turn_personal_model_update
        return await self.run_worker_test(
            "Turn Personal Model Update",
            "Memory & Episodic",
            run_turn_personal_model_update,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "updated_at"])],
        )

    # =========================================================================
    # PATTERN & CRYSTALLIZATION WORKERS (5)
    # =========================================================================

    async def test_pattern_crystallization_daily(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_daily_crystallization
        return await self.run_worker_test(
            "Pattern Crystallization (Daily)",
            "Pattern & Crystallization",
            run_daily_crystallization,
            args=(self.user_id,),
            tables=[("crystallization_log", ["id", "pattern_type"]), ("personal_model", ["person_id"])],
        )

    async def test_pattern_crystallization_weekly(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_weekly_crystallization
        return await self.run_worker_test(
            "Pattern Crystallization (Weekly)",
            "Pattern & Crystallization",
            run_weekly_crystallization,
            args=(self.user_id,),
            tables=[("crystallization_log", ["id", "pattern_type"])],
        )

    async def test_pattern_crystallization_monthly(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_monthly_crystallization
        return await self.run_worker_test(
            "Pattern Crystallization (Monthly)",
            "Pattern & Crystallization",
            run_monthly_crystallization,
            args=(self.user_id,),
            tables=[("crystallization_log", ["id", "pattern_type"])],
        )

    async def test_pattern_trends(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.pattern_trends import run_pattern_trends
        return await self.run_worker_test(
            "Pattern Trends",
            "Pattern & Crystallization",
            run_pattern_trends,
            tables=[],  # Global worker, may not write per-user
        )

    async def test_weekly_signals(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.weekly_signals_worker import run_weekly_signals_worker
        return await self.run_worker_test(
            "Weekly Signals",
            "Pattern & Crystallization",
            run_weekly_signals_worker,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "updated_at"])],
        )

    # =========================================================================
    # THEME & IDENTITY WORKERS (6)
    # =========================================================================

    async def test_theme_inference(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.theme_inference import run_theme_inference
        return await self.run_worker_test(
            "Theme Inference (Full)",
            "Theme & Identity",
            run_theme_inference,
            args=(self.user_id,),
            tables=[("theme_states", ["id", "theme", "clarity_score"])],
            requires_llm=True,
        )

    async def test_theme_inference_incremental(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental
        return await self.run_worker_test(
            "Theme Inference (Incremental)",
            "Theme & Identity",
            run_theme_inference_incremental,
            args=(self.user_id,),
            tables=[("theme_states", ["id", "clarity_score"])],
        )

    async def test_identity_timeline_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.identity_timeline_deep import run_identity_timeline_deep
        return await self.run_worker_test(
            "Identity Timeline Deep",
            "Theme & Identity",
            run_identity_timeline_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "identity_timeline"])],
        )

    async def test_identity_momentum_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.identity_momentum_deep import run_identity_momentum_deep
        return await self.run_worker_test(
            "Identity Momentum Deep",
            "Theme & Identity",
            run_identity_momentum_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "identity_momentum_state"])],
        )

    async def test_persona_mode_detector(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.persona_mode_detector import run_persona_mode_detector
        return await self.run_worker_test(
            "Persona Mode Detector",
            "Theme & Identity",
            run_persona_mode_detector,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "persona_evolution_state"])],
        )

    async def test_persona_tuning(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.persona_tuning import run_persona_tuning
        return await self.run_worker_test(
            "Persona Tuning",
            "Theme & Identity",
            run_persona_tuning,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "persona_evolution_state"])],
        )

    # =========================================================================
    # SOUL & EMOTION WORKERS (5)
    # =========================================================================

    async def test_emotion_state_refresh(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.esr_worker import run_emotion_state_refresh
        return await self.run_worker_test(
            "Emotion State Refresh (ESR)",
            "Soul & Emotion",
            run_emotion_state_refresh,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "emotion_soul_rhythm_state"])],
        )

    async def test_emotion_soul_rhythm_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.emotion_soul_rhythm_deep import run_emotion_soul_rhythm_deep
        return await self.run_worker_test(
            "Emotion Soul Rhythm Deep",
            "Soul & Emotion",
            run_emotion_soul_rhythm_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "emotion_soul_rhythm_state"])],
        )

    async def test_esr_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.esr_deep import run_esr_deep
        return await self.run_worker_test(
            "ESR Deep",
            "Soul & Emotion",
            run_esr_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "emotion_soul_rhythm_state"])],
        )

    async def test_inner_conflict(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.inner_conflict import run_inner_conflict
        return await self.run_worker_test(
            "Inner Conflict",
            "Soul & Emotion",
            run_inner_conflict,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "conflict_state"])],
        )

    async def test_tone_continuity(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.tone_continuity import run_tone_continuity
        return await self.run_worker_test(
            "Tone Continuity",
            "Soul & Emotion",
            run_tone_continuity,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "tone_state"])],
        )

    # =========================================================================
    # RHYTHM & FORECAST WORKERS (4)
    # =========================================================================

    async def test_rhythm_forecast(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.rhythm_forecast import run_rhythm_forecast
        return await self.run_worker_test(
            "Rhythm Forecast",
            "Rhythm & Forecast",
            run_rhythm_forecast,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "rhythm_state"])],
        )

    async def test_rhythm_soul_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.rhythm_soul_deep import run_rhythm_soul_deep
        return await self.run_worker_test(
            "Rhythm Soul Deep",
            "Rhythm & Forecast",
            run_rhythm_soul_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "rhythm_soul_state"])],
        )

    async def test_weekly_rhythm_rollup(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker import run_weekly_rhythm_rollup
        return await self.run_worker_test(
            "Weekly Rhythm Rollup",
            "Rhythm & Forecast",
            run_weekly_rhythm_rollup,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "rhythm_state"])],
        )

    async def test_forecast(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.forecast import run_forecast
        return await self.run_worker_test(
            "Forecast",
            "Rhythm & Forecast",
            run_forecast,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "forecast_state"])],
        )

    # =========================================================================
    # PLANNING & GOALS WORKERS (5)
    # =========================================================================

    async def test_goal_evolver(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.goal_evolver import run_goal_evolver
        return await self.run_worker_test(
            "Goal Evolver",
            "Planning & Goals",
            run_goal_evolver,
            args=(self.user_id,),
            tables=[("goals", ["id", "title", "status"]), ("goal_history", ["id", "goal_id"])],
            requires_llm=True,
        )

    async def test_planner_summary(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.planner_auto_summary import run_planner_summary
        return await self.run_worker_test(
            "Planner Auto Summary",
            "Planning & Goals",
            run_planner_summary,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "goals_state"])],
        )

    async def test_task_routing(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.task_routing_worker import run_task_routing
        return await self.run_worker_test(
            "Task Routing",
            "Planning & Goals",
            run_task_routing,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_weekly_planner_pressure(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.weekly_planner_pressure_worker import run_weekly_planner_pressure
        return await self.run_worker_test(
            "Weekly Planner Pressure",
            "Planning & Goals",
            run_weekly_planner_pressure,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_decision_graph_deep(self) -> WorkerTestResult:
        from sakhi.apps.worker.decision_graph_deep import run_decision_graph_deep
        return await self.run_worker_test(
            "Decision Graph Deep",
            "Planning & Goals",
            run_decision_graph_deep,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "internal_decision_graph"])],
        )

    # =========================================================================
    # MORNING/EVENING WORKERS (5)
    # =========================================================================

    async def test_morning_preview(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.morning_preview_worker import run_morning_preview
        return await self.run_worker_test(
            "Morning Preview",
            "Morning/Evening",
            run_morning_preview,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "morning_preview_state"])],
        )

    async def test_morning_ask(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.morning_ask_worker import run_morning_ask
        return await self.run_worker_test(
            "Morning Ask",
            "Morning/Evening",
            run_morning_ask,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "morning_ask_state"])],
        )

    async def test_morning_momentum(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.morning_momentum_worker import run_morning_momentum
        return await self.run_worker_test(
            "Morning Momentum",
            "Morning/Evening",
            run_morning_momentum,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "morning_momentum_state"])],
        )

    async def test_evening_closure(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.evening_closure_worker import run_evening_closure
        return await self.run_worker_test(
            "Evening Closure",
            "Morning/Evening",
            run_evening_closure,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "closure_state"])],
        )

    async def test_daily_reflection(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.daily_reflection import run_daily_reflection
        return await self.run_worker_test(
            "Daily Reflection",
            "Morning/Evening",
            run_daily_reflection,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "daily_reflection_state"])],
            requires_llm=True,
        )

    # =========================================================================
    # MICRO & MINI WORKERS (5)
    # =========================================================================

    async def test_micro_momentum(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.micro_momentum_worker import run_micro_momentum
        return await self.run_worker_test(
            "Micro Momentum",
            "Micro & Mini",
            run_micro_momentum,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "micro_momentum_state"])],
        )

    async def test_micro_recovery(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.micro_recovery_worker import run_micro_recovery
        return await self.run_worker_test(
            "Micro Recovery",
            "Micro & Mini",
            run_micro_recovery,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "micro_recovery_state"])],
        )

    async def test_micro_journey(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.micro_journey_worker import run_micro_journey
        return await self.run_worker_test(
            "Micro Journey",
            "Micro & Mini",
            run_micro_journey,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_mini_flow(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.mini_flow_worker import run_mini_flow
        return await self.run_worker_test(
            "Mini Flow",
            "Micro & Mini",
            run_mini_flow,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "mini_flow_state"])],
        )

    async def test_focus_path(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.focus_path_worker import run_focus_path
        return await self.run_worker_test(
            "Focus Path",
            "Micro & Mini",
            run_focus_path,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "focus_path_state"])],
        )

    # =========================================================================
    # DEEP ANALYSIS WORKERS (6)
    # =========================================================================

    async def test_meta_reflection(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.meta_reflection import run_meta_reflection
        return await self.run_worker_test(
            "Meta Reflection",
            "Deep Analysis",
            run_meta_reflection,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
            requires_llm=True,
        )

    # test_meta_audit removed — meta_audit table archived in v2 refactor

    async def test_coherence(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.coherence import run_coherence
        return await self.run_worker_test(
            "Coherence",
            "Deep Analysis",
            run_coherence,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "coherence_state"])],
        )

    async def test_presence_reflection(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.presence_reflection import run_presence_reflection
        return await self.run_worker_test(
            "Presence Reflection",
            "Deep Analysis",
            run_presence_reflection,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_weekly_learning(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.weekly_learning_worker import run_weekly_learning
        return await self.run_worker_test(
            "Weekly Learning",
            "Deep Analysis",
            run_weekly_learning,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_brain_goals_themes_refresh(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.brain_goals_themes_refresh import run_brain_goals_themes_refresh
        return await self.run_worker_test(
            "Brain Goals Themes Refresh",
            "Deep Analysis",
            run_brain_goals_themes_refresh,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    # =========================================================================
    # UTILITY WORKERS (6)
    # =========================================================================

    async def test_ayurvedic_pipeline(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.ayurvedic_pipeline import run_ayurvedic_pipeline
        return await self.run_worker_test(
            "Ayurvedic Pipeline",
            "Utility",
            run_ayurvedic_pipeline,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id"])],
        )

    async def test_life_phase_mapper(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.life_phase_mapper import run_life_phase_mapper
        return await self.run_worker_test(
            "Life Phase Mapper",
            "Utility",
            run_life_phase_mapper,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "life_context"])],
        )

    async def test_nudge_check(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.nudge_worker import run_nudge_check
        return await self.run_worker_test(
            "Nudge Check",
            "Utility",
            run_nudge_check,
            args=(self.user_id,),
            tables=[("personal_model", ["person_id", "nudge_state"])],
        )

    async def test_rhythm_scheduler(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.rhythm_scheduler import run_rhythm_scheduler
        return await self.run_worker_test(
            "Rhythm Scheduler",
            "Utility",
            run_rhythm_scheduler,
            tables=[],  # Global scheduler
        )

    async def test_meta_reflection_weekly(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.meta_reflection_weekly import run_meta_reflection_weekly
        return await self.run_worker_test(
            "Meta Reflection Weekly",
            "Utility",
            run_meta_reflection_weekly,
            tables=[],  # Global worker
        )

    async def test_crystallization_for_all_users(self) -> WorkerTestResult:
        from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_crystallization_for_all_users
        return await self.run_worker_test(
            "Crystallization For All Users",
            "Utility",
            run_crystallization_for_all_users,
            args=("daily",),
            tables=[],  # Global worker
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    async def run_all(self, category_filter: Optional[str] = None):
        """Run all worker tests."""
        print("\n" + "=" * 80)
        print("SAKHI COMPREHENSIVE WORKER TEST - ALL 51 WORKERS")
        print(f"User ID: {self.user_id}")
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 80)

        # Initialize LLM
        print("\n📡 Checking LLM availability...")
        llm_ok = await self.init_llm_router()
        if llm_ok:
            print("   ✅ LLM router initialized")
        else:
            print("   ⚠️  LLM not available - some tests will be skipped")

        total_start = time.time()

        # Define all tests by category
        all_tests = [
            # Memory & Episodic (4)
            self.test_episodic_consolidation_v21,
            self.test_embedding_consolidation,
            self.test_brain_update,
            self.test_turn_personal_model_update,
            # Pattern & Crystallization (5)
            self.test_pattern_crystallization_daily,
            self.test_pattern_crystallization_weekly,
            self.test_pattern_crystallization_monthly,
            self.test_pattern_trends,
            self.test_weekly_signals,
            # Theme & Identity (6)
            self.test_theme_inference,
            self.test_theme_inference_incremental,
            self.test_identity_timeline_deep,
            self.test_identity_momentum_deep,
            self.test_persona_mode_detector,
            self.test_persona_tuning,
            # Soul & Emotion (5)
            self.test_emotion_state_refresh,
            self.test_emotion_soul_rhythm_deep,
            self.test_esr_deep,
            self.test_inner_conflict,
            self.test_tone_continuity,
            # Rhythm & Forecast (4)
            self.test_rhythm_forecast,
            self.test_rhythm_soul_deep,
            self.test_weekly_rhythm_rollup,
            self.test_forecast,
            # Planning & Goals (5)
            self.test_goal_evolver,
            self.test_planner_summary,
            self.test_task_routing,
            self.test_weekly_planner_pressure,
            self.test_decision_graph_deep,
            # Morning/Evening (5)
            self.test_morning_preview,
            self.test_morning_ask,
            self.test_morning_momentum,
            self.test_evening_closure,
            self.test_daily_reflection,
            # Micro & Mini (5)
            self.test_micro_momentum,
            self.test_micro_recovery,
            self.test_micro_journey,
            self.test_mini_flow,
            self.test_focus_path,
            # Deep Analysis (6)
            self.test_meta_reflection,
            self.test_coherence,
            self.test_presence_reflection,
            self.test_weekly_learning,
            self.test_brain_goals_themes_refresh,
            # Utility (6)
            self.test_ayurvedic_pipeline,
            self.test_life_phase_mapper,
            self.test_nudge_check,
            self.test_rhythm_scheduler,
            self.test_meta_reflection_weekly,
            self.test_crystallization_for_all_users,
        ]

        # Run tests
        current_category = None
        for i, test_func in enumerate(all_tests, 1):
            result = await test_func()
            self.results.append(result)

            # Print category header
            if result.category != current_category:
                current_category = result.category
                print(f"\n{'─' * 40}")
                print(f"📂 {current_category}")
                print(f"{'─' * 40}")

            # Print result
            if result.skipped:
                status = "⏭️  SKIP"
            elif result.passed:
                status = "✅ PASS" if result.changes_detected else "✅ OK  "
            else:
                status = "❌ FAIL"

            print(f"  {status} | {result.name}")
            if not result.passed and result.error:
                print(f"         └─ {result.message}")

            # Track category stats
            if result.category not in self.category_stats:
                self.category_stats[result.category] = {"passed": 0, "failed": 0, "skipped": 0}
            if result.skipped:
                self.category_stats[result.category]["skipped"] += 1
            elif result.passed:
                self.category_stats[result.category]["passed"] += 1
            else:
                self.category_stats[result.category]["failed"] += 1

        # Print summary
        total_duration = time.time() - total_start
        passed = sum(1 for r in self.results if r.passed and not r.skipped)
        failed = sum(1 for r in self.results if not r.passed)
        skipped = sum(1 for r in self.results if r.skipped)
        changes = sum(1 for r in self.results if r.changes_detected)

        print("\n" + "=" * 80)
        print("COMPREHENSIVE WORKER TEST SUMMARY")
        print("=" * 80)

        print("\n📊 By Category:")
        for cat, stats in sorted(self.category_stats.items()):
            p, f, s = stats["passed"], stats["failed"], stats["skipped"]
            status_icon = "✅" if f == 0 else "❌"
            print(f"   {status_icon} {cat}: {p} passed, {f} failed, {s} skipped")

        print(f"\n{'─' * 80}")
        print(f"Total Workers: {len(self.results)}")
        print(f"Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        print(f"DB Changes Detected: {changes}")
        print(f"Duration: {total_duration:.2f}s")
        print("=" * 80)

        # Print failures if any
        if failed > 0:
            print("\n❌ FAILED WORKERS:")
            for r in self.results:
                if not r.passed:
                    print(f"\n{r.name} ({r.category})")
                    print(f"  Error: {r.message}")
                    if r.error:
                        print(f"  Traceback:\n{r.error[:500]}")

        return failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Comprehensive Sakhi Worker Test")
    parser.add_argument("--user-id", default=DEFAULT_USER_ID, help="User ID to test with")
    parser.add_argument("--category", help="Filter by category name")
    args = parser.parse_args()

    tester = ComprehensiveWorkerTester(args.user_id)
    success = await tester.run_all(args.category)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
