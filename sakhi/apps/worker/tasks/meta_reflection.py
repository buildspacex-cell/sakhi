from __future__ import annotations

import logging
import json
from statistics import mean
from typing import Any, Dict, List, Optional

from asyncpg import UndefinedColumnError, UndefinedTableError
from pydantic import BaseModel

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)


# -------------------------------
# Pydantic Model
# -------------------------------
class MetaReflectionItem(BaseModel):
    id: Optional[str]
    helpfulness: Optional[float]
    clarity: Optional[float]
    tone_feedback: Optional[str]


# -------------------------------
# Main Execution
# -------------------------------
async def run_meta_reflection(person_id: str) -> Dict[str, float] | None:
    """
    Evaluate recent reflections/insights and persist helpfulness + clarity scores.
    Uses JSONL (JSON Lines) format for robust parsing.
    """
    settings = get_settings()
    if not settings.enable_reflective_state_writes:
        LOGGER.info("Worker disabled by safety gate: ENABLE_REFLECTIVE_STATE_WRITES=false")
        return None

    db = await get_db()
    try:
        # ------------------------------------
        # 1. Fetch last 10 reflections
        # ------------------------------------
        reflections = await db.fetch(
            """
            SELECT id, content
            FROM reflections
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 10
            """,
            person_id,
        )

        if not reflections:
            LOGGER.info("[Meta-Reflection] No reflections found for %s", person_id)
            return None

        # Build text block
        text_block = "\n\n".join(
            f"{row['id']} :: {row.get('content') or ''}".strip()
            for row in reflections
            if row.get("content")
        )

        # ------------------------------------
        # 2. JSONL Prompt (VERY STABLE)
        # ------------------------------------
        prompt = f"""
You are Sakhi reviewing recent reflections of a user.

For EACH reflection, output exactly ONE LINE of JSON.
Each line must be a complete JSON object containing:

  - id            (string)
  - helpfulness   (0–1 float)
  - clarity       (0–1 float)
  - tone_feedback (short string)

IMPORTANT RULES:
- Output MUST be JSON Lines (JSONL).
- NO arrays. NO '[' or ']'.
- NO extra text or commentary.
- Do NOT prefix with "json:".
- Every line MUST be a valid JSON object.

Example:
{{"id":"12","helpfulness":0.8,"clarity":0.9,"tone_feedback":"warm"}}
{{"id":"13","helpfulness":0.9,"clarity":0.8,"tone_feedback":"direct"}}

Reflections:
{text_block}
""".strip()

        # ------------------------------------
        # 3. Call LLM (no schema!!)
        # ------------------------------------
        raw_payload = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            person_id=person_id,
        )

        if not isinstance(raw_payload, str):
            raw_payload = json.dumps(raw_payload, ensure_ascii=False)

        text = raw_payload.strip()

        # ------------------------------------
        # 4. Parse JSON lines robustly
        # ------------------------------------
        parsed_items: List[MetaReflectionItem] = []

        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                parsed_items.append(MetaReflectionItem(**obj))
            except Exception:
                # ignore malformed lines
                continue

        if not parsed_items:
            LOGGER.warning("[Meta-Reflection] No valid JSONL lines parsed for %s", person_id)
            return None

        # ------------------------------------
        # 5. Persist scores
        # ------------------------------------
        helpful_values: List[float] = []
        clarity_values: List[float] = []

        for entry in parsed_items:
            reflection_raw_id = entry.id
            try:
                reflection_id = int(reflection_raw_id)
            except (TypeError, ValueError):
                continue

            helpfulness = _coerce_score(entry.helpfulness)
            clarity = _coerce_score(entry.clarity)
            tone_feedback = (entry.tone_feedback or "").strip() or None

            if not reflection_id:
                continue

            persisted = await _upsert_meta_score(
                db=db,
                person_id=person_id,
                reflection_id=reflection_id,
                helpfulness=helpfulness,
                clarity=clarity,
                tone_feedback=tone_feedback,
            )

            # Insight confidence now intentionally skipped
            if helpfulness is not None:
                helpful_values.append(helpfulness)
            if clarity is not None:
                clarity_values.append(clarity)

        if not helpful_values and not clarity_values:
            LOGGER.warning("[Meta-Reflection] No numeric scores persisted for %s", person_id)
            return None

        # ------------------------------------
        # 6. Aggregate + return
        # ------------------------------------
        mean_helpfulness = mean(helpful_values) if helpful_values else 0.0
        mean_clarity = mean(clarity_values) if clarity_values else 0.0

        LOGGER.info(
            "[Meta-Reflection] Completed for %s — mean helpfulness=%.2f clarity=%.2f",
            person_id,
            mean_helpfulness,
            mean_clarity,
        )

        return {"mean_helpfulness": mean_helpfulness, "mean_clarity": mean_clarity}

    finally:
        await db.close()


# -------------------------------
# Utility functions
# -------------------------------
def _coerce_score(value: Any) -> float | None:
    try:
        if value is None:
            return None
        score = float(value)
        return min(max(score, 0.0), 1.0)
    except (TypeError, ValueError):
        return None


async def _upsert_meta_score(
    db: Any,
    person_id: str,
    reflection_id: int,
    helpfulness: float | None,
    clarity: float | None,
    tone_feedback: str | None,
) -> bool:
    """
    Save a single reflection scoring row.
    """
    try:
        await db.execute(
            """
            INSERT INTO meta_reflection_scores
                (person_id, helpfulness, clarity, tone_feedback)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id)
            DO UPDATE SET
                helpfulness = EXCLUDED.helpfulness,
                clarity = EXCLUDED.clarity,
                tone_feedback = EXCLUDED.tone_feedback,
                updated_at = now()
            """,
            person_id,
            helpfulness,
            clarity,
            tone_feedback,
        )
        return True

    except (UndefinedTableError, UndefinedColumnError) as exc:
        LOGGER.warning("[Meta-Reflection] Skipping score persistence due to schema mismatch: %s", exc)
        return False


async def _update_insight_confidence(db: Any, reflection_id: int, helpfulness: float | None) -> None:
    """
    Insight confidence now intentionally disabled.
    """
    LOGGER.warning("insight confidence update skipped — reflection_id removed")
    return None


__all__ = ["run_meta_reflection"]
