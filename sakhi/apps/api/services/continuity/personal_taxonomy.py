"""Personal taxonomy — per-user anchor discovery.

Stores and retrieves topic anchors discovered via LLM enrichment for topics
that fall outside the hardcoded lexical taxonomy. Grows over time as the user
discusses new topics, building a personal vocabulary the classifier can reuse.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)

_ANCHOR_RE = re.compile(r"[^a-z0-9_]")


def canonicalise_anchor(anchor: str) -> str:
    """Normalise a raw anchor string to snake_case key."""
    cleaned = (anchor or "").strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = _ANCHOR_RE.sub("", cleaned)
    return cleaned[:64]  # hard cap


async def load_personal_taxonomy(person_id: str) -> dict[str, str]:
    """Return {anchor_key: label} for all personal taxonomy entries for this person."""
    try:
        rows = await dbfetch(
            """
            SELECT anchor, label
            FROM continuity_personal_taxonomy
            WHERE person_id = $1
            ORDER BY entry_count DESC
            """,
            person_id,
        )
        return {str(row["anchor"]): str(row["label"]) for row in rows}
    except Exception as exc:
        LOGGER.warning("[PersonalTaxonomy] load failed person=%s: %s", person_id, exc)
        return {}


async def upsert_personal_taxonomy(
    person_id: str,
    anchor: str,
    label: str,
) -> dict[str, Any]:
    """Insert or increment entry_count for a personal taxonomy anchor."""
    canonical = canonicalise_anchor(anchor)
    if not canonical:
        return {}
    safe_label = (label or canonical.replace("_", " ").title())[:128]
    try:
        await dbexec(
            """
            INSERT INTO continuity_personal_taxonomy
                (person_id, anchor, label, entry_count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (person_id, anchor)
            DO UPDATE SET
                entry_count = continuity_personal_taxonomy.entry_count + 1,
                label       = EXCLUDED.label,
                updated_at  = now()
            """,
            person_id,
            canonical,
            safe_label,
        )
        return {"anchor": canonical, "label": safe_label}
    except Exception as exc:
        LOGGER.warning(
            "[PersonalTaxonomy] upsert failed person=%s anchor=%s: %s",
            person_id, canonical, exc,
        )
        return {}


async def update_continuity_label_anchor(
    person_id: str,
    entry_id: str,
    anchor: str,
    decision_state: str | None = None,
    epistemic_state: str | None = None,
    affective_scalar: float | None = None,
) -> None:
    """Upsert a continuity_labels row with LLM-inferred anchor.

    Creates the row if it doesn't exist yet (entry may arrive before the first
    compile pass runs) so the inferred anchor is not silently discarded.
    """
    canonical = canonicalise_anchor(anchor)
    if not canonical:
        return
    try:
        await dbexec(
            """
            INSERT INTO continuity_labels
                (person_id, source_type, source_id, anchor, inferred_by,
                 facets, entities, scalar, metadata,
                 decision_state, epistemic_state, affective_scalar)
            VALUES ($1, 'journal', $2, $3, 'llm',
                    '[]'::jsonb, '[]'::jsonb, NULL, '{}'::jsonb,
                    $4, $5, $6)
            ON CONFLICT (person_id, source_type, source_id)
            DO UPDATE SET
                anchor           = EXCLUDED.anchor,
                inferred_by      = 'llm',
                decision_state   = COALESCE(EXCLUDED.decision_state, continuity_labels.decision_state),
                epistemic_state  = COALESCE(EXCLUDED.epistemic_state, continuity_labels.epistemic_state),
                affective_scalar = COALESCE(EXCLUDED.affective_scalar, continuity_labels.affective_scalar),
                updated_at       = now()
            """,
            person_id,
            entry_id,
            canonical,
            decision_state,
            epistemic_state,
            affective_scalar,
        )
    except Exception as exc:
        LOGGER.warning(
            "[PersonalTaxonomy] label upsert failed person=%s entry=%s: %s",
            person_id, entry_id, exc,
        )


async def upsert_continuity_label_enrichment(
    person_id: str,
    entry_id: str,
    *,
    decision_state: str | None = None,
    epistemic_state: str | None = None,
    affective_scalar: float | None = None,
) -> None:
    """Upsert enrichment columns (decision/epistemic/affective) without changing anchor.

    Creates the row with anchor='unknown' if it doesn't exist yet, so enrichment
    data is never discarded before the compile pass runs.
    """
    try:
        await dbexec(
            """
            INSERT INTO continuity_labels
                (person_id, source_type, source_id, anchor, inferred_by,
                 facets, entities, scalar, metadata,
                 decision_state, epistemic_state, affective_scalar)
            VALUES ($1, 'journal', $2, 'unknown', 'lexical',
                    '[]'::jsonb, '[]'::jsonb, NULL, '{}'::jsonb,
                    $3, $4, $5)
            ON CONFLICT (person_id, source_type, source_id)
            DO UPDATE SET
                decision_state   = COALESCE(EXCLUDED.decision_state, continuity_labels.decision_state),
                epistemic_state  = COALESCE(EXCLUDED.epistemic_state, continuity_labels.epistemic_state),
                affective_scalar = COALESCE(EXCLUDED.affective_scalar, continuity_labels.affective_scalar),
                updated_at       = now()
            """,
            person_id,
            entry_id,
            decision_state,
            epistemic_state,
            affective_scalar,
        )
    except Exception as exc:
        LOGGER.warning(
            "[PersonalTaxonomy] enrichment upsert failed person=%s entry=%s: %s",
            person_id, entry_id, exc,
        )
