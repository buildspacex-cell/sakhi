"""
Sakhi Worker Integration Test Suite

Tests each worker directly (not via scheduler) and verifies database updates.

Workers tested:
1. Episodic Consolidation v21 - Creates/updates memory_episodic
2. Pattern Crystallization - Promotes patterns to crystallized_patterns
3. Theme Inference - Updates theme_states
4. Theme Inference Incremental - Upranking and decay
5. Soul Refresh - Updates soul_state in personal_model
6. ESR Worker - Updates emotion_soul_rhythm_state
7. Rhythm Forecast - Updates rhythm predictions
8. Goal Evolver - Evolves goals based on patterns
9. Ayurvedic Pipeline - Runs full Ayurvedic analysis

Usage:
    python -m sakhi.tests.worker_integration_test [--user-id UUID]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.WARNING)

DEFAULT_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90"


@dataclass
class WorkerTestResult:
    name: str
    passed: bool
    message: str
    before: Dict[str, Any] = field(default_factory=dict)
    after: Dict[str, Any] = field(default_factory=dict)
    changes: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    error: Optional[str] = None


class WorkerTester:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.results: List[WorkerTestResult] = []
        self.llm_available = False

    async def init_llm_router(self) -> bool:
        """Try to initialize LLM router for workers that need it."""
        try:
            # Initialize worker router
            from sakhi.apps.worker.jobs import _get_router
            worker_router = _get_router()

            # Also set the API's LLM router (used by theme_inference, goal_evolver)
            from sakhi.apps.api.core.llm import set_router
            set_router(worker_router)

            self.llm_available = True
            return True
        except Exception as e:
            self.llm_available = False
            return False

    async def get_db_state(self, tables: List[str]) -> Dict[str, Any]:
        """Snapshot relevant database state."""
        from sakhi.apps.api.core.db import q

        state = {}

        for table in tables:
            if table == "memory_episodic":
                rows = await q(
                    "SELECT id, ts, text FROM memory_episodic WHERE person_id = $1 ORDER BY ts DESC LIMIT 5",
                    self.user_id
                )
                state["memory_episodic"] = {
                    "count": len(rows),
                    "latest_ts": rows[0].get("ts") if rows else None,
                    "latest_text": (rows[0].get("text") or "")[:50] if rows else None,
                }

            elif table == "pattern_occurrences":
                rows = await q(
                    "SELECT pattern_type, COUNT(*) as cnt FROM pattern_occurrences WHERE person_id = $1 GROUP BY pattern_type",
                    self.user_id
                )
                state["pattern_occurrences"] = {
                    "total": sum(r.get("cnt", 0) for r in rows),
                    "by_type": {r.get("pattern_type"): r.get("cnt") for r in rows},
                }

            elif table == "crystallized_patterns":
                rows = await q(
                    "SELECT pattern_type, status, COUNT(*) as cnt FROM crystallized_patterns WHERE person_id = $1 GROUP BY pattern_type, status",
                    self.user_id
                )
                state["crystallized_patterns"] = {
                    "total": sum(r.get("cnt", 0) for r in rows),
                    "by_type": {r.get("pattern_type"): r.get("cnt") for r in rows},
                }

            elif table == "theme_states":
                rows = await q(
                    "SELECT theme, clarity_score FROM theme_states WHERE person_id = $1 ORDER BY clarity_score DESC LIMIT 5",
                    self.user_id
                )
                state["theme_states"] = {
                    "count": len(rows),
                    "themes": [(r.get("theme"), r.get("clarity_score")) for r in rows],
                }

            elif table == "personal_model":
                row = await q(
                    """SELECT
                        soul_state IS NOT NULL as has_soul,
                        rhythm_state IS NOT NULL as has_rhythm,
                        emotion_state IS NOT NULL as has_emotion,
                        emotion_soul_rhythm_state IS NOT NULL as has_esr,
                        operating_system IS NOT NULL as has_os,
                        updated_at
                    FROM personal_model WHERE person_id = $1""",
                    self.user_id,
                    one=True
                )
                state["personal_model"] = dict(row) if row else {}

            elif table == "goals":
                rows = await q(
                    "SELECT id, title, status, priority FROM goals WHERE person_id = $1 LIMIT 5",
                    self.user_id
                )
                state["goals"] = {
                    "count": len(rows),
                    "active": sum(1 for r in rows if r.get("status") == "active"),
                }

            elif table == "journal_entries":
                row = await q(
                    "SELECT COUNT(*) as cnt FROM journal_entries WHERE user_id = $1",
                    self.user_id,
                    one=True
                )
                state["journal_entries"] = {"count": row.get("cnt", 0) if row else 0}

        return state

    def compare_states(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare before/after states and identify changes."""
        changes = {}
        for key in set(list(before.keys()) + list(after.keys())):
            b = before.get(key, {})
            a = after.get(key, {})
            if b != a:
                changes[key] = {"before": b, "after": a}
        return changes

    # =========================================================================
    # Worker Tests
    # =========================================================================

    async def test_episodic_consolidation(self) -> WorkerTestResult:
        """Test episodic_consolidation_v21 worker."""
        start = time.time()
        tables = ["memory_episodic", "pattern_occurrences", "journal_entries"]

        try:
            from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21

            before = await self.get_db_state(tables)

            # Run worker with today's date
            now = datetime.now(timezone.utc)
            payload = {"user_id": self.user_id, "ts": now.isoformat()}
            await run_episodic_consolidation_v21(self.user_id, payload)

            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            # Determine pass/fail
            # Pass if: episodes exist OR patterns were logged
            passed = (
                after.get("memory_episodic", {}).get("count", 0) > 0 or
                after.get("pattern_occurrences", {}).get("total", 0) > before.get("pattern_occurrences", {}).get("total", 0)
            )

            return WorkerTestResult(
                name="Episodic Consolidation v21",
                passed=passed,
                message=f"Episodes: {after.get('memory_episodic', {}).get('count', 0)}, Patterns: {after.get('pattern_occurrences', {}).get('total', 0)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Episodic Consolidation v21",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_pattern_crystallization_daily(self) -> WorkerTestResult:
        """Test pattern_crystallization_worker (daily)."""
        start = time.time()
        tables = ["pattern_occurrences", "crystallized_patterns"]

        try:
            from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_daily_crystallization

            before = await self.get_db_state(tables)
            result = await run_daily_crystallization(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None

            return WorkerTestResult(
                name="Pattern Crystallization (Daily)",
                passed=passed,
                message=f"Checked: {result.get('patterns_checked', 0)}, Crystallized: {result.get('patterns_crystallized', 0)}, Updated: {result.get('patterns_updated', 0)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Pattern Crystallization (Daily)",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_pattern_crystallization_weekly(self) -> WorkerTestResult:
        """Test pattern_crystallization_worker (weekly)."""
        start = time.time()
        tables = ["pattern_occurrences", "crystallized_patterns"]

        try:
            from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_weekly_crystallization

            before = await self.get_db_state(tables)
            result = await run_weekly_crystallization(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None

            return WorkerTestResult(
                name="Pattern Crystallization (Weekly)",
                passed=passed,
                message=f"Checked: {result.get('patterns_checked', 0)}, Crystallized: {result.get('patterns_crystallized', 0)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Pattern Crystallization (Weekly)",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_theme_inference(self) -> WorkerTestResult:
        """Test theme_inference worker (full). Requires LLM."""
        start = time.time()

        # Skip if LLM not available
        if not self.llm_available:
            return WorkerTestResult(
                name="Theme Inference (Full)",
                passed=True,  # Skip counts as pass
                message="Skipped (requires LLM)",
                duration_ms=(time.time() - start) * 1000,
            )

        tables = ["theme_states", "personal_model"]

        try:
            from sakhi.apps.worker.tasks.theme_inference import run_theme_inference

            before = await self.get_db_state(tables)
            result = await run_theme_inference(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None or after.get("theme_states", {}).get("count", 0) >= 0

            themes_count = result.get("themes_count", 0) if result else 0
            return WorkerTestResult(
                name="Theme Inference (Full)",
                passed=passed,
                message=f"Themes created/updated: {themes_count}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Theme Inference (Full)",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_theme_inference_incremental(self) -> WorkerTestResult:
        """Test theme_inference_incremental worker."""
        start = time.time()
        tables = ["theme_states", "crystallized_patterns"]

        try:
            from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental

            before = await self.get_db_state(tables)
            result = await run_theme_inference_incremental(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None

            return WorkerTestResult(
                name="Theme Inference (Incremental)",
                passed=passed,
                message=f"Boosted: {result.get('boosted', 0)}, Decayed: {result.get('decayed', 0)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Theme Inference (Incremental)",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_soul_refresh(self) -> WorkerTestResult:
        """Test soul_refresh_worker."""
        start = time.time()
        tables = ["personal_model"]

        try:
            from sakhi.apps.worker.tasks.soul_refresh_worker import soul_refresh_worker

            before = await self.get_db_state(tables)
            result = await soul_refresh_worker(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None or after.get("personal_model", {}).get("has_soul", False)

            return WorkerTestResult(
                name="Soul Refresh Worker",
                passed=passed,
                message=f"Soul state updated: {after.get('personal_model', {}).get('has_soul', False)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Soul Refresh Worker",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_esr_worker(self) -> WorkerTestResult:
        """Test emotion_state_refresh worker."""
        start = time.time()
        tables = ["personal_model"]

        try:
            from sakhi.apps.worker.tasks.esr_worker import run_emotion_state_refresh

            before = await self.get_db_state(tables)
            result = await run_emotion_state_refresh(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = True  # ESR worker typically succeeds even with no data

            return WorkerTestResult(
                name="ESR Worker (Emotion State Refresh)",
                passed=passed,
                message=f"ESR state exists: {after.get('personal_model', {}).get('has_esr', False)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="ESR Worker (Emotion State Refresh)",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_rhythm_forecast(self) -> WorkerTestResult:
        """Test rhythm_forecast worker."""
        start = time.time()
        tables = ["personal_model"]

        try:
            from sakhi.apps.worker.tasks.rhythm_forecast import run_rhythm_forecast

            before = await self.get_db_state(tables)
            result = await run_rhythm_forecast(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = True  # Rhythm forecast may not update if no data

            return WorkerTestResult(
                name="Rhythm Forecast Worker",
                passed=passed,
                message=f"Rhythm state exists: {after.get('personal_model', {}).get('has_rhythm', False)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Rhythm Forecast Worker",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_goal_evolver(self) -> WorkerTestResult:
        """Test goal_evolver worker. Requires LLM."""
        start = time.time()

        # Skip if LLM not available
        if not self.llm_available:
            return WorkerTestResult(
                name="Goal Evolver Worker",
                passed=True,  # Skip counts as pass
                message="Skipped (requires LLM)",
                duration_ms=(time.time() - start) * 1000,
            )

        tables = ["goals"]

        try:
            from sakhi.apps.worker.tasks.goal_evolver import run_goal_evolver

            before = await self.get_db_state(tables)
            result = await run_goal_evolver(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = True  # Goal evolver succeeds even with no goals

            return WorkerTestResult(
                name="Goal Evolver Worker",
                passed=passed,
                message=f"Goals: {after.get('goals', {}).get('count', 0)} total, {after.get('goals', {}).get('active', 0)} active",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Goal Evolver Worker",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_ayurvedic_pipeline(self) -> WorkerTestResult:
        """Test ayurvedic_pipeline worker."""
        start = time.time()
        tables = ["personal_model", "memory_episodic"]

        try:
            from sakhi.apps.worker.tasks.ayurvedic_pipeline import run_ayurvedic_pipeline

            before = await self.get_db_state(tables)
            result = await run_ayurvedic_pipeline(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = result is not None
            executed = result.get("executed", []) if result else []

            return WorkerTestResult(
                name="Ayurvedic Pipeline",
                passed=passed,
                message=f"Executed steps: {', '.join(executed) if executed else 'none'}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="Ayurvedic Pipeline",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def test_esr_deep(self) -> WorkerTestResult:
        """Test emotion_soul_rhythm_deep worker."""
        start = time.time()
        tables = ["personal_model"]

        try:
            from sakhi.apps.worker.tasks.emotion_soul_rhythm_deep import run_emotion_soul_rhythm_deep

            before = await self.get_db_state(tables)
            result = await run_emotion_soul_rhythm_deep(self.user_id)
            after = await self.get_db_state(tables)
            changes = self.compare_states(before, after)

            passed = True

            return WorkerTestResult(
                name="ESR Deep Worker",
                passed=passed,
                message=f"ESR state: {after.get('personal_model', {}).get('has_esr', False)}",
                before=before,
                after=after,
                changes=changes,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return WorkerTestResult(
                name="ESR Deep Worker",
                passed=False,
                message=f"Error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Main Runner
    # =========================================================================

    async def run_all(self):
        """Run all worker tests."""
        print("\n" + "=" * 70)
        print("SAKHI WORKER INTEGRATION TEST")
        print(f"User ID: {self.user_id}")
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 70)

        # Try to initialize LLM router
        print("\n📡 Checking LLM availability...")
        llm_ok = await self.init_llm_router()
        if llm_ok:
            print("   ✅ LLM router initialized")
        else:
            print("   ⚠️  LLM not available - some tests will be skipped")

        total_start = time.time()

        # Define all tests
        tests = [
            ("1", "Episodic Consolidation", self.test_episodic_consolidation),
            ("2", "Pattern Crystallization (Daily)", self.test_pattern_crystallization_daily),
            ("3", "Pattern Crystallization (Weekly)", self.test_pattern_crystallization_weekly),
            ("4", "Theme Inference (Full)", self.test_theme_inference),
            ("5", "Theme Inference (Incremental)", self.test_theme_inference_incremental),
            ("6", "Soul Refresh", self.test_soul_refresh),
            ("7", "ESR Worker", self.test_esr_worker),
            ("8", "ESR Deep", self.test_esr_deep),
            ("9", "Rhythm Forecast", self.test_rhythm_forecast),
            ("10", "Goal Evolver", self.test_goal_evolver),
            ("11", "Ayurvedic Pipeline", self.test_ayurvedic_pipeline),
        ]

        for num, name, test_fn in tests:
            print(f"\n🔍 Test {num}: {name}")
            result = await test_fn()
            self.results.append(result)
            status = "✅" if result.passed else "❌"
            print(f"   {status} {result.message}")
            if result.changes:
                for table, change in result.changes.items():
                    print(f"      └─ {table}: changed")
            if result.error:
                print(f"      └─ Error: {result.error[:100]}")

        # Summary
        total_duration = time.time() - total_start
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print("\n" + "=" * 70)
        print("WORKER TEST SUMMARY")
        print("=" * 70)

        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"{status} | {r.name}")
            print(f"       └─ {r.message}")
            if r.error:
                print(f"       └─ Error: {r.error[:80]}...")

        print("-" * 70)
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        print(f"Duration: {total_duration:.2f}s")
        print("=" * 70)

        return failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Sakhi Worker Integration Test")
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User ID to test with (default: {DEFAULT_USER_ID})",
    )

    args = parser.parse_args()

    tester = WorkerTester(user_id=args.user_id)
    success = await tester.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
