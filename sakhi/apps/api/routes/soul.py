from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/soul", tags=["Soul"])


@router.get("/{person_id}/summary")
async def soul_summary(person_id: str) -> Dict[str, Any]:
    values = await q(
        """
        SELECT value_name, description, confidence, anchors, evidence, created_at
        FROM soul_values
        WHERE person_id = $1
        ORDER BY confidence DESC
        """,
        person_id,
    )

    identities = await q(
        """
        SELECT label, narrative, coherence, supporting_memories, created_at
        FROM identity_signatures
        WHERE person_id = $1
        ORDER BY created_at DESC
        """,
        person_id,
    )

    purpose = await q(
        """
        SELECT theme, description, anchors, momentum, created_at
        FROM purpose_themes
        WHERE person_id = $1
        ORDER BY created_at DESC
        """,
        person_id,
    )

    arcs = await q(
        """
        SELECT arc_name, start_scope, end_scope, summary, sentiment, tags, narrative
        FROM life_arcs
        WHERE person_id = $1
        ORDER BY start_scope
        """,
        person_id,
    )

    conflicts = await q(
        """
        SELECT conflict_type, description, impact, tension_between, resolution_hint, created_at
        FROM conflict_records
        WHERE person_id = $1
        ORDER BY created_at DESC
        """,
        person_id,
    )

    evolution_row = await q(
        """
        SELECT current_mode, drift_score, evolution_path, updated_at
        FROM persona_evolution
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    return {
        "values": [dict(row) for row in values],
        "identity_signatures": [dict(row) for row in identities],
        "purpose_themes": [dict(row) for row in purpose],
        "life_arcs": [dict(row) for row in arcs],
        "conflicts": [dict(row) for row in conflicts],
        "persona_evolution": dict(evolution_row) if evolution_row else None,
    }


__all__ = ["router"]
