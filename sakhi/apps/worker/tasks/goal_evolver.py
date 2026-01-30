"""Goal evolution worker: reviews active goals against recent context and suggests revisions."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.llm_parsing import extract_json_from_llm_response

LOGGER = logging.getLogger(__name__)


async def run_goal_evolver(person_id: str) -> Dict[str, Any]:
    """
    Review active goals and compare with recent reflections, rhythm, and life phase.
    Suggest revisions for goals that need reframing.
    """
    # Fetch active goals
    goals = await dbfetch(
        """
        SELECT id, title, description, type, status, priority, evolution_score, created_at
        FROM goals
        WHERE person_id = $1 AND status = 'active'
        ORDER BY priority DESC, created_at DESC
        LIMIT 20
        """,
        person_id,
    )

    if not goals:
        LOGGER.info("[GoalEvolver] No active goals for person=%s", person_id)
        return {"status": "no_goals", "revisions": []}

    # Fetch recent episodes for context
    episodes = await dbfetch(
        """
        SELECT summary, themes, created_at
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        person_id,
    )

    # Fetch current rhythm state
    rhythm = await dbfetch(
        """
        SELECT body_energy, mind_focus, stress_level, fatigue_level
        FROM rhythm_state
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    # Fetch operating system for context
    personal_model = await dbfetch(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    # Build prompt
    goals_text = json.dumps([dict(g) for g in goals], default=str, indent=2)
    episodes_text = json.dumps([dict(e) for e in (episodes or [])], default=str, indent=2)
    rhythm_text = json.dumps(dict(rhythm) if rhythm else {}, default=str)
    os_text = json.dumps((personal_model or {}).get("operating_system") or {}, default=str)

    prompt = f"""You are Sakhi's Goal Evolution Engine.
Review active goals and compare with recent episodes, rhythm state, and operating system.

ACTIVE GOALS:
{goals_text}

RECENT EPISODES (reflections/conversations):
{episodes_text}

CURRENT RHYTHM STATE:
{rhythm_text}

OPERATING SYSTEM (user's baseline):
{os_text}

Analyze and identify:
1. Goals that are aligned and progressing well (no change needed)
2. Goals that need reframing based on recent context
3. Goals that should be merged or split
4. Evolution score (0.0-1.0) for each goal based on alignment

Output a JSON object with this structure:
```json
{{
  "revisions": [
    {{
      "goal_id": "<uuid>",
      "action": "keep" | "revise" | "merge" | "archive",
      "revised_title": "<new title if revise>",
      "revised_description": "<new description if revise>",
      "reason": "<brief explanation>",
      "evolution_score": 0.82
    }}
  ],
  "summary": "<1-2 sentence summary of goal evolution status>"
}}
```

Only include goals that need attention (action != "keep" or significant evolution_score change)."""

    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        person_id=person_id,
    )

    payload = response if isinstance(response, str) else json.dumps(response)
    parsed = extract_json_from_llm_response(payload)

    if not parsed:
        LOGGER.warning("[GoalEvolver] Failed to parse LLM response for person=%s", person_id)
        return {"status": "parse_error", "revisions": []}

    revisions = parsed.get("revisions") or []
    applied_count = 0

    for revision in revisions:
        goal_id = revision.get("goal_id")
        action = revision.get("action", "keep")

        if not goal_id or action == "keep":
            continue

        # Find matching goal
        matching_goal = next((g for g in goals if str(g.get("id")) == str(goal_id)), None)
        if not matching_goal:
            LOGGER.debug("[GoalEvolver] Goal not found: %s", goal_id)
            continue

        # Log to goal_history
        await dbexec(
            """
            INSERT INTO goal_history (goal_id, person_id, previous_title, revised_title, reason)
            VALUES ($1, $2, $3, $4, $5)
            """,
            goal_id,
            person_id,
            matching_goal.get("title"),
            revision.get("revised_title") or matching_goal.get("title"),
            revision.get("reason"),
        )

        if action == "revise":
            await dbexec(
                """
                UPDATE goals
                SET title = COALESCE($2, title),
                    description = COALESCE($3, description),
                    evolution_score = COALESCE($4, evolution_score),
                    last_revised = NOW()
                WHERE id = $1
                """,
                goal_id,
                revision.get("revised_title"),
                revision.get("revised_description"),
                revision.get("evolution_score"),
            )
            applied_count += 1
        elif action == "archive":
            await dbexec(
                """
                UPDATE goals
                SET status = 'archived', last_revised = NOW()
                WHERE id = $1
                """,
                goal_id,
            )
            applied_count += 1

    LOGGER.info(
        "[GoalEvolver] person=%s goals=%s revisions=%s applied=%s",
        person_id,
        len(goals),
        len(revisions),
        applied_count,
    )

    return {
        "status": "success",
        "goals_reviewed": len(goals),
        "revisions": revisions,
        "applied": applied_count,
        "summary": parsed.get("summary"),
    }


__all__ = ["run_goal_evolver"]
