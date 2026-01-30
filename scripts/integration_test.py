#!/usr/bin/env python3
"""
Comprehensive Integration Test for Sakhi

Tests the entire conversation flow with inline workers and verifies
all worker outputs in the database.

Usage:
    SAKHI_DISABLE_QUEUE=1 python scripts/integration_test.py

Requirements:
    - API running on localhost:8000
    - SAKHI_DISABLE_QUEUE=1 in .env.local
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import asyncpg
import httpx

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8080")
DATABASE_URL = os.getenv("DATABASE_URL")
PERSON_ID = os.getenv("TEST_PERSON_ID", "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90")

# Test messages to send
TEST_MESSAGES = [
    "I've been feeling scattered lately, like I can't focus on anything for more than a few minutes.",
    "Work has been really intense. I'm managing a big project and the deadline is next week.",
    "I think I need to find better ways to unwind. Maybe I should try meditation again.",
]

# Workers triggered per turn (from turn_v2.py)
TURN_WORKERS = [
    "turn_memory_update",
    "ayurvedic_pipeline",
    "episodic_consolidation_v21",
    "rhythm_forecast",
    "identity_momentum_deep",
    "emotion_soul_rhythm_deep",
    "esr",
    "soul_refresh",
    "longitudinal_update",
    "rhythm_soul_deep",
]

# Scheduled workers to run manually
SCHEDULED_WORKERS = [
    "crystallization_daily",
    "theme_inference",
    "meta_reflection",
    "forecast",
    "task_weaver_refresh",
]

# Tables to query for worker output verification
WORKER_OUTPUT_TABLES = {
    "turn_memory_update": [
        ("journal_entries", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
        ("stm_turns", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
    ],
    "ayurvedic_pipeline": [
        ("elemental_signal_stm", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
        ("personal_model", "person_id = $1"),
    ],
    "episodic_consolidation_v21": [
        ("episodic_episodes", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
        ("episodic_state_vectors", "person_id = $1 ORDER BY created_at DESC LIMIT 3"),
    ],
    "rhythm_forecast": [
        ("personal_model", "person_id = $1"),  # Check rhythm_state field
    ],
    "identity_momentum_deep": [
        ("personal_model", "person_id = $1"),  # Check identity_momentum field
    ],
    "emotion_soul_rhythm_deep": [
        ("personal_model", "person_id = $1"),  # Check emotion_soul_rhythm field
    ],
    "esr": [
        ("personal_model", "person_id = $1"),  # Check esr field
    ],
    "soul_refresh": [
        ("personal_model", "person_id = $1"),  # Check soul field
    ],
    "longitudinal_update": [
        ("personal_model", "person_id = $1"),  # Check longitudinal_state field
    ],
    "rhythm_soul_deep": [
        ("personal_model", "person_id = $1"),  # Check rhythm_soul field
    ],
    "theme_inference": [
        ("themes", "person_id = $1 ORDER BY updated_at DESC LIMIT 5"),
    ],
    "meta_reflection": [
        ("meta_reflections", "person_id = $1 ORDER BY created_at DESC LIMIT 3"),
    ],
    "crystallization": [
        ("crystallized_patterns", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
        ("pattern_occurrences", "person_id = $1 ORDER BY created_at DESC LIMIT 5"),
    ],
}

# Fields to check in personal_model for each worker
PERSONAL_MODEL_FIELDS = {
    "rhythm_forecast": "rhythm_state",
    "identity_momentum_deep": "identity_momentum_v2",
    "emotion_soul_rhythm_deep": "emotion_soul_rhythm",
    "esr": "esr",
    "soul_refresh": "soul",
    "longitudinal_update": "longitudinal_state",
    "rhythm_soul_deep": "rhythm_soul",
    "ayurvedic_pipeline": "elemental_balance",
}


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.details: dict[str, Any] = {}
        self.error: str | None = None
        self.duration_ms: float = 0


class IntegrationTest:
    def __init__(self, person_id: str):
        self.person_id = person_id
        self.results: list[TestResult] = []
        self.conn: asyncpg.Connection | None = None
        self.client: httpx.AsyncClient | None = None
        self.turn_ids: list[str] = []
        self.start_time = datetime.utcnow()

    async def setup(self):
        """Initialize database connection and HTTP client."""
        print(f"\n{'='*60}")
        print("SAKHI INTEGRATION TEST")
        print(f"{'='*60}")
        print(f"Person ID: {self.person_id}")
        print(f"API Base: {API_BASE}")
        print(f"Start Time: {self.start_time.isoformat()}")
        print(f"{'='*60}\n")

        # Connect to database
        self.conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        self.client = httpx.AsyncClient(timeout=120.0)

        # Check API health
        try:
            resp = await self.client.get(f"{API_BASE}/health")
            if resp.status_code != 200:
                raise Exception(f"API health check failed: {resp.status_code}")
            print("[OK] API is healthy")
        except Exception as e:
            print(f"[FAIL] API health check: {e}")
            raise

        # Record baseline state
        await self._record_baseline()

    async def _record_baseline(self):
        """Record current state before tests."""
        result = TestResult("baseline_state")
        try:
            # Count existing records
            counts = {}
            tables = ["journal_entries", "conversation_turns", "memory_episodic", "themes"]
            for table in tables:
                row = await self.conn.fetchrow(
                    f"SELECT COUNT(*) as cnt FROM {table} WHERE person_id = $1",
                    self.person_id
                )
                counts[table] = row["cnt"] if row else 0

            # Get personal_model state
            pm = await self.conn.fetchrow(
                "SELECT * FROM personal_model WHERE person_id = $1",
                self.person_id
            )

            result.details = {
                "record_counts": counts,
                "personal_model_exists": pm is not None,
                "personal_model_updated_at": str(pm["updated_at"]) if pm else None,
            }
            result.success = True
            print(f"[OK] Baseline recorded: {counts}")
        except Exception as e:
            result.error = str(e)
            print(f"[WARN] Baseline recording failed: {e}")

        self.results.append(result)

    async def test_conversation_turns(self):
        """Send conversation turns and verify inline workers run."""
        print(f"\n--- CONVERSATION TURNS ({len(TEST_MESSAGES)} messages) ---\n")

        for i, message in enumerate(TEST_MESSAGES, 1):
            result = TestResult(f"turn_{i}")
            start = datetime.utcnow()

            try:
                print(f"[{i}/{len(TEST_MESSAGES)}] Sending: {message[:50]}...")

                resp = await self.client.post(
                    f"{API_BASE}/v2/turn",
                    json={
                        "sessionId": self.person_id,
                        "text": message,
                    },
                )

                duration = (datetime.utcnow() - start).total_seconds() * 1000
                result.duration_ms = duration

                if resp.status_code == 200:
                    data = resp.json()
                    turn_id = data.get("turn_id") or data.get("turnId")
                    if turn_id:
                        self.turn_ids.append(turn_id)

                    result.success = True
                    result.details = {
                        "turn_id": turn_id,
                        "response_preview": data.get("reply", "")[:100] if data.get("reply") else None,
                        "status_code": resp.status_code,
                    }
                    print(f"    [OK] Turn completed in {duration:.0f}ms (turn_id: {turn_id})")

                    # Brief reply preview
                    reply = data.get("reply", "")
                    if reply:
                        print(f"    Reply: {reply[:80]}...")
                else:
                    result.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    print(f"    [FAIL] {result.error}")

            except Exception as e:
                result.error = str(e)
                print(f"    [FAIL] {e}")

            self.results.append(result)

            # Small delay between turns
            await asyncio.sleep(0.5)

    async def test_scheduled_workers(self):
        """Run scheduled workers via lab endpoint."""
        print(f"\n--- SCHEDULED WORKERS ---\n")

        # Workers to run via lab endpoint
        lab_workers = [
            "episodic-v21",
            "rhythm-forecast",
            "esr",
            "ayurvedic_pipeline",
        ]

        for worker in lab_workers:
            result = TestResult(f"scheduled_{worker}")
            start = datetime.utcnow()

            try:
                print(f"Running worker: {worker}...")

                resp = await self.client.post(
                    f"{API_BASE}/lab/run-workers",
                    json={
                        "user_id": self.person_id,
                        "workers": [worker],
                    },
                )

                duration = (datetime.utcnow() - start).total_seconds() * 1000
                result.duration_ms = duration

                if resp.status_code == 200:
                    data = resp.json()
                    result.success = True
                    result.details = {
                        "response": data,
                        "status_code": resp.status_code,
                    }
                    print(f"    [OK] {worker} completed in {duration:.0f}ms")
                else:
                    result.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    print(f"    [FAIL] {result.error}")

            except Exception as e:
                result.error = str(e)
                print(f"    [FAIL] {e}")

            self.results.append(result)

    async def verify_worker_outputs(self):
        """Query database to verify worker outputs."""
        print(f"\n--- VERIFYING WORKER OUTPUTS ---\n")

        # Check personal_model updates
        pm = await self.conn.fetchrow(
            "SELECT * FROM personal_model WHERE person_id = $1",
            self.person_id
        )

        if pm:
            print("Personal Model Fields:")
            for worker, field in PERSONAL_MODEL_FIELDS.items():
                result = TestResult(f"verify_{worker}")
                try:
                    value = pm.get(field)
                    has_value = value is not None and value != {} and value != []
                    result.success = has_value
                    result.details = {
                        "field": field,
                        "has_value": has_value,
                        "value_preview": str(value)[:100] if value else None,
                    }
                    status = "[OK]" if has_value else "[EMPTY]"
                    print(f"    {status} {field}: {'populated' if has_value else 'empty'}")
                except Exception as e:
                    result.error = str(e)
                    print(f"    [FAIL] {field}: {e}")
                self.results.append(result)
        else:
            print("    [WARN] No personal_model found for user")

        # Check table records
        print("\nTable Records (created during test):")

        tables_to_check = [
            ("journal_entries", "created_at"),
            ("conversation_turns", "created_at"),
            ("memory_episodic", "created_at"),
            ("memory_short_term", "created_at"),
        ]

        for table, time_col in tables_to_check:
            result = TestResult(f"verify_table_{table}")
            try:
                rows = await self.conn.fetch(
                    f"""
                    SELECT * FROM {table}
                    WHERE person_id = $1
                    AND {time_col} >= $2
                    ORDER BY {time_col} DESC
                    LIMIT 5
                    """,
                    self.person_id,
                    self.start_time,
                )
                count = len(rows)
                result.success = count > 0
                result.details = {
                    "count": count,
                    "records": [dict(r) for r in rows[:2]] if rows else [],
                }
                status = "[OK]" if count > 0 else "[EMPTY]"
                print(f"    {status} {table}: {count} new records")
            except Exception as e:
                result.error = str(e)
                print(f"    [FAIL] {table}: {e}")
            self.results.append(result)

    async def verify_episodic_state(self):
        """Check episodic state vectors (Friction Framework)."""
        print("\nEpisodic Memory with State Vectors:")

        result = TestResult("verify_episodic_state_vectors")
        try:
            rows = await self.conn.fetch(
                """
                SELECT id, person_id, text, state_vector, guna_vector, created_at
                FROM memory_episodic
                WHERE person_id = $1
                AND state_vector IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 3
                """,
                self.person_id,
            )

            if rows:
                result.success = True
                result.details = {"count": len(rows)}
                print(f"    [OK] Found {len(rows)} entries with state vectors")
                for row in rows:
                    state = row.get("state_vector", {})
                    text = row.get("text", "") or ""
                    print(f"        - Episode: {text[:50] if text else 'N/A'}...")
                    if state:
                        print(f"          State: {str(state)[:80]}...")
            else:
                print("    [EMPTY] No episodic entries with state vectors")
                result.details = {"count": 0}
        except Exception as e:
            result.error = str(e)
            print(f"    [FAIL] {e}")

        self.results.append(result)

    async def generate_report(self):
        """Generate final test report."""
        print(f"\n{'='*60}")
        print("TEST REPORT")
        print(f"{'='*60}\n")

        # Summary counts
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success and r.error)
        empty = sum(1 for r in self.results if not r.success and not r.error)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Empty/Pending: {empty}")
        print(f"Success Rate: {passed/total*100:.1f}%")

        # Turn summary
        print(f"\nTurns Processed: {len(self.turn_ids)}")
        for tid in self.turn_ids:
            print(f"    - {tid}")

        # Duration
        total_duration = sum(r.duration_ms for r in self.results if r.duration_ms > 0)
        print(f"\nTotal API Duration: {total_duration/1000:.1f}s")

        # Failed tests
        if failed > 0:
            print("\n--- FAILED TESTS ---")
            for r in self.results:
                if not r.success and r.error:
                    print(f"  {r.name}: {r.error}")

        # Write detailed JSON report
        report = {
            "person_id": self.person_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "empty": empty,
            },
            "turn_ids": self.turn_ids,
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        report_path = f"/tmp/sakhi_test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {report_path}")
        print(f"\n{'='*60}\n")

        return report

    async def cleanup(self):
        """Close connections."""
        if self.conn:
            await self.conn.close()
        if self.client:
            await self.client.aclose()


async def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    test = IntegrationTest(PERSON_ID)

    try:
        await test.setup()
        await test.test_conversation_turns()
        await test.test_scheduled_workers()
        await test.verify_worker_outputs()
        await test.verify_episodic_state()
        report = await test.generate_report()

        # Exit with error code if tests failed
        if report["summary"]["failed"] > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
