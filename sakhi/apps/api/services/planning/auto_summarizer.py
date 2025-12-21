from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.llm_router.context_builder import build_calibration_context
from sakhi.libs.json_utils import extract_json_block

LOGGER = logging.getLogger(__name__)


async def generate_planner_summary(person_id: str) -> Dict[str, Any] | None:
    """
    Generate a lightweight planning summary for the current day.
    Stores the output in planned_items and mirrors it into personal_model.goals_state.
    """

    db = await get_db()
    try:
        tasks: List[Dict[str, Any]] = await db.fetch(
            """
            SELECT id, title, status, due_at, priority
            FROM tasks
            WHERE user_id = $1
            ORDER BY COALESCE(due_at, NOW() + INTERVAL '30 days'), priority DESC
            LIMIT 25
            """,
            person_id,
        )

        task_lines = "\n".join(
            f"- {(row.get('title') or 'Untitled').strip()} "
            f"[{row.get('status') or 'unknown'}] due={row.get('due_at')}"
            for row in tasks
        )
        if not task_lines:
            task_lines = "No tasks found."

        context_blob = await build_calibration_context(person_id)

        prompt = f"""
Generate a PLANNING SUMMARY for today.

You MUST return JSON:
{{
  "today_focus": ["...", "..."],
  "blocking_items": ["..."],
  "urgent_items": ["..."],
  "recommendations": ["..."],
  "narrative": "..."
}}

Context:
{context_blob or 'None'}

User tasks:
{task_lines}
""".strip()

        messages = [
            {"role": "system", "content": "Be Sakhi — warm, clear, actionable."},
            {"role": "user", "content": prompt},
        ]

        llm_model = "gpt-4o-mini"
        response = await call_llm(messages=messages, person_id=person_id, model=llm_model)
        payload = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        payload = extract_json_block(payload)

        try:
            data: Dict[str, Any] = json.loads(payload)
        except Exception as exc:
            LOGGER.error("[Planner Summary] Failed to parse JSON for %s: %s", person_id, exc)
            return None

        await db.execute(
            """
            INSERT INTO planned_items (person_id, scope, label, payload, due_ts)
            VALUES ($1, 'daily_summary', 'today_plan', $2::jsonb, NOW())
            """,
            person_id,
            json.dumps(data, ensure_ascii=False),
        )

        await db.execute(
            """
            UPDATE personal_model
            SET goals_state = jsonb_set(
                COALESCE(goals_state, '{}'::jsonb),
                '{daily_summary}',
                $2::jsonb,
                true
            ),
            updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(data, ensure_ascii=False),
        )

        LOGGER.info("[Planner Summary] Updated planning snapshot for %s", person_id)
        return data
    finally:
        await db.close()


__all__ = ["generate_planner_summary"]
