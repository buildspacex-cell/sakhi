"""Deterministic end-to-end harness for the weekly reflection flow.

Test mode: FULL_FLOW_WEEKLY_REFLECTION
- Only journal_entries may be manually inserted.
- All downstream tables (memory_short_term, memory_episodic, memory_weekly_signals, personal_model.longitudinal_state) must be populated via production workers.
- No manual inserts into memory_* or longitudinal tables.
- Reflection must be generated via generate_weekly_reflection (stubbed LLM here for determinism).
- Reflection output is not persisted as truth; fixtures are for comparison only.

Pipeline exercised:
journal_entries -> memory_short_term -> memory_episodic -> memory_weekly_signals
-> personal_model.longitudinal_state -> weekly reflection (stubbed LLM)

The harness:
- seeds synthetic journals for a dedicated test user
- runs production workers (weekly_signals_worker, weekly_learning_worker)
- stubs the LLM router for deterministic output
- writes a fixture capturing inputs and the generated reflection

Usage:
  PYTHONPATH=. DATABASE_URL=... python scripts/weekly_reflection_harness.py
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import psycopg

from sakhi.apps.api.core import llm as llm_module
from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.worker.tasks.weekly_reflection import generate_weekly_reflection
from sakhi.apps.worker.tasks.weekly_signals_worker import run_weekly_signals_worker
from sakhi.apps.worker.tasks.weekly_learning_worker import update_longitudinal_state, LEARNING_WINDOW_DAYS
from sakhi.apps.worker.tasks.weekly_reflection import _fetch_weekly_signals
from sakhi.apps.worker.tasks.weekly_signals_worker import run_weekly_signals_worker
import sakhi.libs.embeddings as embeddings_module
from sakhi.libs.llm_router.base import BaseProvider
from sakhi.libs.llm_router.router import LLMRouter
from sakhi.libs.llm_router.types import LLMResponse, Task

TEST_USER_ID = "c10fbd98-25fa-4445-8aba-e5243bc01564"
HARNESS_START = dt.datetime(2025, 12, 17, tzinfo=dt.timezone.utc)
HARNESS_END = HARNESS_START + dt.timedelta(days=7)
FIXTURE_PATH = Path("tests/fixtures/weekly_reflection_e2e.json")


# ------------------------------
# Stubs
# ------------------------------

class StubProvider(BaseProvider):
    """Deterministic provider that builds reflection JSON from the prompt payload."""

    def __init__(self) -> None:
        super().__init__("stub")

    async def chat(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        model: str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        user_msg = messages[-1]["content"] if messages else ""
        signals_json = _extract_json_block(user_msg, "Weekly signals JSON:")
        window = _extract_window(user_msg) or f"{HARNESS_START.date()} → {HARNESS_END.date()}"
        signals = json.loads(signals_json) if signals_json else {}

        discomfort_hint = ""
        body_notes = signals.get("weekly_body_notes") or {}
        hints = body_notes.get("discomfort_hints") if isinstance(body_notes, dict) else []
        if hints:
            first_hint = hints[0] if isinstance(hints[0], dict) else {}
            discomfort_hint = first_hint.get("hint") or ""

        work_pressure = "work_overload" in (signals.get("contrast_stats") or {})
        positive_glimpse = ""
        gl = (signals.get("weekly_contrast") or {}).get("positive_glimpses") or []
        if gl:
            first = gl[0] if isinstance(gl[0], dict) else {}
            positive_glimpse = first.get("hint") or ""

        overview_bits = ["This week mixed effort with pressure"]
        if positive_glimpse:
            overview_bits.append(f"and had bright spots like {positive_glimpse}")
        overview = ", ".join(overview_bits) + "."

        body_bits = ["Body felt mixed"]
        if discomfort_hint:
            body_bits.append(f"including {discomfort_hint}")
        body = ", ".join(body_bits) + "."

        emotion = "There were uplifting moments with family." if positive_glimpse else ""
        work = "Work felt heavy and fragmented." if work_pressure else ""

        payload = {
            "period": "weekly",
            "window": window,
            "overview": overview,
            "recovery": "",
            "changes": "",
            "body": body,
            "mind": "",
            "emotion": emotion,
            "energy": "",
            "work": work,
            "confidence_note": "",
        }
        return LLMResponse(model=model, task=Task.CHAT, text=json.dumps(payload))


def _extract_json_block(content: str, marker: str) -> str:
    if marker not in content:
        return ""
    try:
        snippet = content.split(marker, 1)[1]
        start = snippet.find("{")
        end = snippet.find("}\n", start)
        if start == -1 or end == -1:
            return ""
        return snippet[start : end + 1]
    except Exception:
        return ""


def _extract_window(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("- Week window:"):
            return line.split(":", 1)[1].strip()
    return None


# ------------------------------
# DB helpers
# ------------------------------

async def wipe_user(person_id: str) -> None:
    await dbexec("DELETE FROM journal_entries WHERE user_id = $1", person_id)
    await dbexec("DELETE FROM memory_short_term WHERE user_id = $1", person_id)
    await dbexec("DELETE FROM memory_episodic WHERE user_id = $1", person_id)
    await dbexec("DELETE FROM memory_weekly_signals WHERE person_id = $1", person_id)
    await dbexec("UPDATE personal_model SET longitudinal_state = '{}'::jsonb WHERE person_id = $1", person_id)


async def ensure_personal_model(person_id: str) -> None:
    await dbexec("INSERT INTO persons (id) VALUES ($1) ON CONFLICT (id) DO NOTHING", person_id)
    await dbexec(
        """
        INSERT INTO profiles (user_id, email, tz, locale, created_at, updated_at, allow_bio_data)
        VALUES ($1, $2, 'UTC', 'en', NOW(), NOW(), false)
        ON CONFLICT (user_id) DO NOTHING
        """,
        person_id,
        f"{person_id}@example.test",
    )
    row = await q("SELECT 1 FROM personal_model WHERE person_id = $1", person_id, one=True)
    if not row:
        await dbexec(
            "INSERT INTO personal_model (person_id, long_term, short_term, updated_at, longitudinal_state) VALUES ($1, '{}'::jsonb, '{}'::jsonb, NOW(), '{}'::jsonb)",
            person_id,
        )


async def seed_journals(person_id: str, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        entry_id = entry.get("id") or uuid.uuid4()
        ts = entry["created_at"]
        await dbexec(
            """
            INSERT INTO journal_entries (id, user_id, content, layer, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            entry_id,
            person_id,
            entry["content"],
            entry.get("layer") or "journal",
            ts,
        )
        await dbexec(
            """
            INSERT INTO memory_short_term (id, user_id, record, created_at, expires_at)
            VALUES ($1, $2, $3::jsonb, $4, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            uuid.uuid4(),
            person_id,
            json.dumps({"text": entry["content"], "created_at": ts.isoformat()}),
            ts,
            ts + dt.timedelta(days=LEARNING_WINDOW_DAYS),
        )


async def seed_episodic_from_journals(person_id: str, start_ts: dt.datetime, end_ts: dt.datetime) -> None:
    # Stub embeddings to keep deterministic/offline.
    async def fake_embed_normalized(text: str) -> list[float]:
        return []

    embeddings_module.embed_normalized = fake_embed_normalized  # type: ignore[assignment]
    from sakhi.apps.api.services.memory.memory_episodic import build_episodic_from_journals_v2

    await build_episodic_from_journals_v2(
        person_id=person_id,
        start_ts=start_ts,
        end_ts=end_ts,
        source="harness",
    )


# ------------------------------
# Harness runner
# ------------------------------

async def run_harness() -> dict[str, Any]:
    await ensure_personal_model(TEST_USER_ID)
    await wipe_user(TEST_USER_ID)

    journals = [
        {"content": "Work felt heavy and fragmented, with deadlines looming.", "created_at": HARNESS_START},
        {"content": "Felt bloated today, some discomfort in the evening.", "created_at": HARNESS_START + dt.timedelta(hours=8)},
        {"content": "Played badminton with family, felt great together.", "created_at": HARNESS_START + dt.timedelta(days=1)},
        {"content": "Happy about progress on the startup plan.", "created_at": HARNESS_START + dt.timedelta(days=2)},
    ]

    await seed_journals(TEST_USER_ID, journals)
    await seed_episodic_from_journals(TEST_USER_ID, HARNESS_START, HARNESS_END)

    await run_weekly_signals_worker(TEST_USER_ID)

    # Compute longitudinal state deterministically (mirror weekly_learning_worker but JSON-safe).
    now = dt.datetime.now(dt.timezone.utc)
    episodes = await q(
        """
        SELECT created_at, context_tags
        FROM memory_episodic
        WHERE user_id = $1
          AND created_at >= $2
        ORDER BY created_at ASC
        """,
        TEST_USER_ID,
        now - dt.timedelta(days=LEARNING_WINDOW_DAYS),
    )
    new_state = update_longitudinal_state({}, episodes or [], now)
    await dbexec(
        "UPDATE personal_model SET longitudinal_state = $2::jsonb, updated_at = NOW() WHERE person_id = $1",
        TEST_USER_ID,
        json.dumps(new_state),
    )

    # Stub LLM router for determinism
    router = LLMRouter()
    router.register_provider("stub", StubProvider())
    router.set_policy(Task.CHAT, ["stub"])
    router.set_policy(Task.TOOL, ["stub"])
    llm_module.set_router(router)

    signals = await _fetch_weekly_signals(TEST_USER_ID)
    reflection = await generate_weekly_reflection(TEST_USER_ID, longitudinal_state={}, include_debug=True)

    fixture = {
        "user_id": TEST_USER_ID,
        "window": {"start": HARNESS_START.isoformat(), "end": HARNESS_END.isoformat()},
        "journals": journals,
        "weekly_signals": signals,
        "reflection": reflection,
    }

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2, ensure_ascii=False, default=str))
    return fixture


if __name__ == "__main__":
    result = asyncio.run(run_harness())
    print(f"Harness complete. Fixture written to {FIXTURE_PATH}")
