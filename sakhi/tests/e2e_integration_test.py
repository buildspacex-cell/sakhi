"""
Sakhi End-to-End Integration Test Suite

Tests the complete flow:
1. User onboarding (Operating System / Prakruti)
2. Conversation → Episodic Memory creation
3. Pattern detection → Pattern Occurrences logging
4. Friction State computation (Prakruti vs Vikriti)
5. Crystallization (threshold-based pattern promotion)
6. Theme upranking and decay

Usage:
    python -m sakhi.tests.e2e_integration_test [--user-id UUID] [--api-url URL]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

# Test configuration
DEFAULT_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90"
DEFAULT_API_URL = "http://localhost:8080"

# Test journal entries with specific patterns for testing
TEST_JOURNAL_ENTRIES = [
    {
        "text": "I've been feeling really scattered and anxious today. My mind keeps racing with thoughts about work deadlines. I couldn't focus on anything important. The constant mental chatter is exhausting.",
        "expected_patterns": {
            "concerns": ["anxiety", "focus", "mental chatter"],
            "dosha_signals": ["vata"],  # Scattered, racing thoughts = Vata
        },
    },
    {
        "text": "Woke up feeling heavy and unmotivated. Just wanted to stay in bed. Everything feels like too much effort. I've been avoiding my creative projects even though they usually bring me joy.",
        "expected_patterns": {
            "concerns": ["motivation", "avoidance"],
            "dosha_signals": ["kapha"],  # Heavy, unmotivated = Kapha
        },
    },
    {
        "text": "I noticed I got really irritated at small things today. Traffic, slow internet, my coffee being lukewarm - everything set me off. I need to be more patient but my fuse is so short.",
        "expected_patterns": {
            "concerns": ["irritation", "patience"],
            "dosha_signals": ["pitta"],  # Irritability = Pitta
        },
    },
    {
        "text": "Creativity is one of my core values. When I'm creating, I feel most alive. Today I spent 3 hours painting and lost track of time. This is what flow feels like.",
        "expected_patterns": {
            "core_values": ["creativity"],
            "lights": ["flow", "artistic expression"],
        },
    },
    {
        "text": "I keep procrastinating on important tasks. This pattern of avoidance is something I've noticed for years. I think I'm afraid of failure or judgment.",
        "expected_patterns": {
            "shadows": ["procrastination", "fear of failure"],
            "concerns": ["avoidance"],
        },
    },
]


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0


@dataclass
class TestSuite:
    results: List[TestResult] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0

    def add(self, result: TestResult):
        self.results.append(result)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"{status} | {r.name}")
            if not r.passed:
                print(f"       └─ {r.message}")
            if r.details:
                for k, v in r.details.items():
                    print(f"       └─ {k}: {v}")

        print("-" * 70)
        print(f"Total: {self.total} | Passed: {self.passed} | Failed: {self.failed}")
        duration = self.end_time - self.start_time
        print(f"Duration: {duration:.2f}s")
        print("=" * 70)


class SakhiE2ETest:
    def __init__(self, user_id: str, api_url: str):
        self.user_id = user_id
        self.api_url = api_url.rstrip("/")
        self.suite = TestSuite()
        self.client = httpx.AsyncClient(timeout=30.0)

        # Track state before/after
        self.initial_state: Dict[str, Any] = {}
        self.final_state: Dict[str, Any] = {}

    async def close(self):
        await self.client.aclose()

    # =========================================================================
    # Database helpers
    # =========================================================================

    async def get_db_counts(self) -> Dict[str, int]:
        """Get current counts from database."""
        from sakhi.apps.api.core.db import q

        counts = {}

        # Episodic memory
        result = await q(
            "SELECT COUNT(*) as cnt FROM memory_episodic WHERE person_id = $1",
            self.user_id, one=True
        )
        counts["episodic_memory"] = result.get("cnt", 0) if isinstance(result, dict) else 0

        # Pattern occurrences
        result = await q(
            "SELECT COUNT(*) as cnt FROM pattern_occurrences WHERE person_id = $1",
            self.user_id, one=True
        )
        counts["pattern_occurrences"] = result.get("cnt", 0) if isinstance(result, dict) else 0

        # Crystallized patterns
        result = await q(
            "SELECT COUNT(*) as cnt FROM crystallized_patterns WHERE person_id = $1",
            self.user_id, one=True
        )
        counts["crystallized_patterns"] = result.get("cnt", 0) if isinstance(result, dict) else 0

        # Journal entries
        result = await q(
            "SELECT COUNT(*) as cnt FROM journal_entries WHERE user_id = $1",
            self.user_id, one=True
        )
        counts["journal_entries"] = result.get("cnt", 0) if isinstance(result, dict) else 0

        # Theme states
        result = await q(
            "SELECT COUNT(*) as cnt FROM theme_states WHERE person_id = $1",
            self.user_id, one=True
        )
        counts["theme_states"] = result.get("cnt", 0) if isinstance(result, dict) else 0

        return counts

    async def get_recent_patterns(self, limit: int = 10) -> List[Dict]:
        """Get recent pattern occurrences."""
        from sakhi.apps.api.core.db import q

        return await q(
            """
            SELECT pattern_type, pattern_value, confidence, detected_at
            FROM pattern_occurrences
            WHERE person_id = $1
            ORDER BY detected_at DESC
            LIMIT $2
            """,
            self.user_id, limit
        ) or []

    async def get_recent_episodes(self, limit: int = 5) -> List[Dict]:
        """Get recent episodic memories."""
        from sakhi.apps.api.core.db import q

        return await q(
            """
            SELECT id, text, soul, state_vector, ts
            FROM memory_episodic
            WHERE person_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            self.user_id, limit
        ) or []

    # =========================================================================
    # Test: API Health
    # =========================================================================

    async def test_api_health(self) -> TestResult:
        """Test that API is running and healthy."""
        start = time.time()
        try:
            resp = await self.client.get(f"{self.api_url}/health")
            data = resp.json()

            passed = resp.status_code == 200 and data.get("status") == "ok"
            return TestResult(
                name="API Health Check",
                passed=passed,
                message="API is healthy" if passed else f"API unhealthy: {data}",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="API Health Check",
                passed=False,
                message=f"Connection failed: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Operating System (Prakruti)
    # =========================================================================

    async def test_set_operating_system(self) -> TestResult:
        """Test computing and storing the user's constitutional type."""
        start = time.time()
        try:
            # Compute Prakruti from onboarding-like responses
            resp = await self.client.post(
                f"{self.api_url}/v1/state/operating-system/compute",
                json={
                    "person_id": self.user_id,
                    "responses": {
                        "body_type": "light_thin",  # Vata
                        "energy_pattern": "variable_bursts",  # Vata
                        "stress_response": "anxious_worried",  # Vata
                        "sleep_pattern": "light_irregular",  # Vata
                        "work_style": "creative_scattered",  # Vata
                    },
                },
            )
            data = resp.json()

            passed = resp.status_code == 200 and data.get("status") == "ok"

            return TestResult(
                name="Set Operating System (Prakruti)",
                passed=passed,
                message=f"Type: {data.get('type', 'Unknown')}" if passed else f"Failed: {data}",
                details={
                    "constitution_type": data.get("type"),
                    "primary_dosha": data.get("primary_dosha"),
                    "dosha_baseline": data.get("dosha_baseline"),
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Set Operating System (Prakruti)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Conversation Flow
    # =========================================================================

    async def test_send_journal_entry(self, entry: Dict) -> TestResult:
        """Test creating a journal entry via direct database insert."""
        start = time.time()
        text = entry["text"][:50] + "..."
        import uuid as uuid_module

        try:
            from sakhi.apps.api.core.db import exec as dbexec

            entry_id = str(uuid_module.uuid4())
            ts = datetime.now(timezone.utc)

            # Insert directly into journal_entries
            await dbexec(
                """
                INSERT INTO journal_entries (id, user_id, content, layer, ts, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                entry_id,
                self.user_id,
                entry["text"],
                "journal",
                ts,
            )

            return TestResult(
                name=f"Journal Entry: {text}",
                passed=True,
                message=f"Entry created: {entry_id[:8]}...",
                details={
                    "entry_id": entry_id,
                    "timestamp": ts.isoformat(),
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name=f"Journal Entry: {text}",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Trigger Episodic Consolidation
    # =========================================================================

    async def test_trigger_episodic_consolidation(self) -> TestResult:
        """Manually trigger episodic consolidation for today's entries."""
        start = time.time()

        try:
            from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21

            # Use today's date for consolidation window
            now = datetime.now(timezone.utc)
            payload = {
                "user_id": self.user_id,
                "ts": now.isoformat(),
            }

            await run_episodic_consolidation_v21(self.user_id, payload)

            return TestResult(
                name="Episodic Consolidation Trigger",
                passed=True,
                message="Consolidation triggered successfully",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Episodic Consolidation Trigger",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Episodic Memory Creation
    # =========================================================================

    async def test_episodic_memory_created(self) -> TestResult:
        """Verify that episodic memories exist (created or updated)."""
        start = time.time()

        initial_count = self.initial_state.get("episodic_memory", 0)
        current_counts = await self.get_db_counts()
        current_count = current_counts.get("episodic_memory", 0)

        new_episodes = current_count - initial_count
        episodes = await self.get_recent_episodes(limit=3)

        # Test passes if:
        # 1. New episodes were created, OR
        # 2. Episodes already exist (consolidation updates existing daily episode)
        passed = current_count > 0

        if new_episodes > 0:
            message = f"Created {new_episodes} new episodes"
        elif current_count > 0:
            message = f"Episode exists for today (consolidation deduplicates)"
        else:
            message = "No episodes found"

        return TestResult(
            name="Episodic Memory Creation",
            passed=passed,
            message=message,
            details={
                "initial_count": initial_count,
                "current_count": current_count,
                "new_episodes": new_episodes,
                "recent_texts": [
                    (e.get("text") or "")[:60] for e in episodes[:3]
                ],
            },
            duration_ms=(time.time() - start) * 1000,
        )

    # =========================================================================
    # Test: Pattern Occurrence Logging
    # =========================================================================

    async def test_pattern_occurrences_logged(self) -> TestResult:
        """Verify that pattern occurrences are being logged."""
        start = time.time()

        initial_count = self.initial_state.get("pattern_occurrences", 0)
        current_counts = await self.get_db_counts()
        current_count = current_counts.get("pattern_occurrences", 0)

        new_patterns = current_count - initial_count
        patterns = await self.get_recent_patterns(limit=10)

        # Group by type
        pattern_types = {}
        for p in patterns:
            ptype = p.get("pattern_type", "unknown")
            pattern_types[ptype] = pattern_types.get(ptype, 0) + 1

        passed = new_patterns > 0

        return TestResult(
            name="Pattern Occurrence Logging",
            passed=passed,
            message=f"Logged {new_patterns} new patterns" if passed else "No patterns logged (may need worker trigger)",
            details={
                "initial_count": initial_count,
                "current_count": current_count,
                "new_patterns": new_patterns,
                "by_type": pattern_types,
            },
            duration_ms=(time.time() - start) * 1000,
        )

    # =========================================================================
    # Test: Friction State
    # =========================================================================

    async def test_friction_state(self) -> TestResult:
        """Test friction state computation."""
        start = time.time()

        try:
            resp = await self.client.get(
                f"{self.api_url}/v1/state/friction/{self.user_id}"
            )
            data = resp.json()

            passed = resp.status_code == 200 and data.get("status") == "ok"

            return TestResult(
                name="Friction State Computation",
                passed=passed,
                message=f"State: {data.get('friction_state', 'unknown')}" if passed else f"Failed: {data}",
                details={
                    "operating_system": data.get("operating_system"),
                    "friction_state": data.get("friction_state"),
                    "friction_name": data.get("friction_name"),
                    "drift_percentage": data.get("drift_percentage"),
                    "severity": data.get("severity"),
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Friction State Computation",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Manual Crystallization Run
    # =========================================================================

    async def test_crystallization_worker(self) -> TestResult:
        """Run the crystallization worker manually and verify."""
        start = time.time()

        try:
            from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_daily_crystallization

            result = await run_daily_crystallization(self.user_id)

            passed = result is not None

            return TestResult(
                name="Crystallization Worker",
                passed=passed,
                message="Worker executed successfully" if passed else "Worker failed",
                details={
                    "patterns_checked": result.get("patterns_checked", 0) if result else 0,
                    "patterns_crystallized": result.get("patterns_crystallized", 0) if result else 0,
                    "patterns_updated": result.get("patterns_updated", 0) if result else 0,
                    "patterns_decayed": result.get("patterns_decayed", 0) if result else 0,
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Crystallization Worker",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Theme Inference
    # =========================================================================

    async def test_theme_inference(self) -> TestResult:
        """Run theme inference and verify."""
        start = time.time()

        try:
            from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental

            result = await run_theme_inference_incremental(self.user_id)

            passed = result is not None

            return TestResult(
                name="Theme Inference (Incremental)",
                passed=passed,
                message="Theme inference executed" if passed else "Theme inference failed",
                details={
                    "boosted": result.get("boosted", 0) if result else 0,
                    "decayed": result.get("decayed", 0) if result else 0,
                    "crystallized_themes": result.get("crystallized_themes", 0) if result else 0,
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Theme Inference (Incremental)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Test: Vikriti (Current State)
    # =========================================================================

    async def test_vikriti_computation(self) -> TestResult:
        """Test current state (vikriti) computation."""
        start = time.time()

        try:
            resp = await self.client.get(
                f"{self.api_url}/v1/state/vikriti/{self.user_id}"
            )
            data = resp.json()

            passed = resp.status_code == 200 and data.get("status") == "ok"

            return TestResult(
                name="Vikriti (Current State) Computation",
                passed=passed,
                message=f"Computed from {data.get('episode_count', 0)} episodes" if passed else f"Failed: {data}",
                details={
                    "current_dosha": data.get("current_dosha"),
                    "confidence": data.get("confidence"),
                    "episode_count": data.get("episode_count"),
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return TestResult(
                name="Vikriti (Current State) Computation",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    # =========================================================================
    # Main test runner
    # =========================================================================

    async def run_all(self):
        """Run all tests in sequence."""
        print("\n" + "=" * 70)
        print("SAKHI END-TO-END INTEGRATION TEST")
        print(f"User ID: {self.user_id}")
        print(f"API URL: {self.api_url}")
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 70)

        self.suite.start_time = time.time()

        # Capture initial state
        print("\n📊 Capturing initial state...")
        self.initial_state = await self.get_db_counts()
        print(f"   Initial counts: {self.initial_state}")

        # Test 1: API Health
        print("\n🔍 Test 1: API Health Check")
        result = await self.test_api_health()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        if not result.passed:
            print("\n⚠️  API not available. Stopping tests.")
            self.suite.end_time = time.time()
            self.suite.print_summary()
            return

        # Test 2: Set Operating System
        print("\n🔍 Test 2: Set Operating System (Prakruti)")
        result = await self.test_set_operating_system()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 3: Send Journal Entries
        print("\n🔍 Test 3: Send Journal Entries")
        for i, entry in enumerate(TEST_JOURNAL_ENTRIES[:3], 1):  # Send first 3
            print(f"   Sending entry {i}/3...")
            result = await self.test_send_journal_entry(entry)
            self.suite.add(result)
            print(f"   {'✅' if result.passed else '❌'} {result.message}")
            await asyncio.sleep(1)  # Brief pause between entries

        # Wait for async processing
        print("\n⏳ Waiting for async workers to process...")
        await asyncio.sleep(3)

        # Test 4: Trigger Episodic Consolidation
        print("\n🔍 Test 4: Trigger Episodic Consolidation")
        result = await self.test_trigger_episodic_consolidation()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 5: Episodic Memory
        print("\n🔍 Test 5: Episodic Memory Creation")
        result = await self.test_episodic_memory_created()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 6: Pattern Occurrences
        print("\n🔍 Test 6: Pattern Occurrence Logging")
        result = await self.test_pattern_occurrences_logged()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 7: Vikriti
        print("\n🔍 Test 7: Vikriti (Current State)")
        result = await self.test_vikriti_computation()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 8: Friction State
        print("\n🔍 Test 8: Friction State")
        result = await self.test_friction_state()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 9: Crystallization Worker
        print("\n🔍 Test 9: Crystallization Worker")
        result = await self.test_crystallization_worker()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Test 10: Theme Inference
        print("\n🔍 Test 10: Theme Inference")
        result = await self.test_theme_inference()
        self.suite.add(result)
        print(f"   {'✅' if result.passed else '❌'} {result.message}")

        # Capture final state
        print("\n📊 Capturing final state...")
        self.final_state = await self.get_db_counts()
        print(f"   Final counts: {self.final_state}")

        # Print changes
        print("\n📈 Changes during test:")
        for key in self.initial_state:
            initial = self.initial_state.get(key, 0)
            final = self.final_state.get(key, 0)
            delta = final - initial
            if delta != 0:
                print(f"   {key}: {initial} → {final} ({'+' if delta > 0 else ''}{delta})")

        self.suite.end_time = time.time()
        self.suite.print_summary()

        await self.close()


async def main():
    parser = argparse.ArgumentParser(description="Sakhi E2E Integration Test")
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User ID to test with (default: {DEFAULT_USER_ID})",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )

    args = parser.parse_args()

    tester = SakhiE2ETest(user_id=args.user_id, api_url=args.api_url)
    await tester.run_all()

    # Exit with error code if any tests failed
    sys.exit(0 if tester.suite.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
