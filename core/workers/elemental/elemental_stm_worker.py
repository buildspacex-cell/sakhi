from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List
from uuid import UUID
import logging
import uuid

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.elemental_projection_engine import project_to_elements
from core.workers.signals.neutral_signal_extraction_worker import _parse_record

logger = logging.getLogger(__name__)


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


# TODO: Reduce window_days for production; 1500-day span is for lab/backfill only.
async def _fetch_stm_signals(person_id: UUID, window_days: int = 1500) -> List[Dict[str, Any]]:
    rows = await dbq(
        """
        SELECT
          id,
          record,
          COALESCE(record->>'source_type', 'journal') AS source_type,
          created_at
        FROM memory_short_term
        WHERE (person_id::text = $1 OR user_id::text = $1)
          AND created_at >= NOW() - ($2::int || ' days')::interval
        ORDER BY created_at DESC
        """,
        str(person_id),
        window_days,
    )
    return rows or []


async def _insert_elemental_row(
    person_id: UUID,
    source_signal_id: str,
    source_type: str,
    dimension: str,
    distribution: Dict[str, float],
    magnitude: float,
    confidence: float,
    expires_at: dt.datetime,
    created_at: dt.datetime,
) -> None:
    await dbexec(
        """
        INSERT INTO elemental_signal_stm (
          person_id, source_signal_id, source_type, dimension,
          earth, water, fire, air, ether, magnitude, confidence, created_at, expires_at
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11, $12, $13)
        ON CONFLICT (person_id, source_signal_id, dimension) DO NOTHING
        """,
        str(person_id),
        source_signal_id,
        source_type,
        dimension,
        distribution.get("earth", 0.0),
        distribution.get("water", 0.0),
        distribution.get("fire", 0.0),
        distribution.get("air", 0.0),
        distribution.get("ether", 0.0),
        magnitude,
        confidence,
        created_at,
        expires_at,
    )


def _signal_uuid(row_id: Any, idx: int) -> UUID:
    try:
        base = UUID(str(row_id))
    except Exception:
        base = uuid.uuid4()
    return uuid.uuid5(base, f"signal-{idx}")


async def run_elemental_stm_worker(person_id: UUID, ts: dt.datetime, mode: str = "manual") -> Dict[str, Any]:
    stm_rows = await _fetch_stm_signals(person_id)
    written = 0
    skipped = 0
    signals_seen = 0
    for row in stm_rows:
        record = _parse_record(row.get("record"))
        signal_list = record.get("signals") if isinstance(record, dict) else None
        if not isinstance(signal_list, list):
            continue
        for idx, sig in enumerate(signal_list):
            if not isinstance(sig, dict) or not sig.get("type"):
                continue
            signals_seen += 1
            try:
                projection = project_to_elements(
                    {
                        "id": row.get("id"),
                        "type": sig.get("type"),
                        "confidence": float(sig.get("confidence") or 1.0),
                        "ts": row.get("created_at") or ts,
                        "source_type": "signal",
                    }
                )
            except Exception:
                skipped += 1
                continue
            source_signal_id = _signal_uuid(row.get("id"), idx)
            for dimension, vec in (projection.get("vector") or {}).items():
                await _insert_elemental_row(
                    person_id=person_id,
                    source_signal_id=source_signal_id,
                    source_type="signal",
                    dimension=dimension,
                    distribution=vec.get("distribution") or {},
                    magnitude=float(vec.get("magnitude") or 0.0),
                    confidence=float(projection.get("confidence") or 0.0),
                    expires_at=projection.get("expires_at") or _now(),
                    created_at=row.get("created_at") or _now(),
                )
                written += 1

    status = "success" if written > 0 else "skipped"
    logger.info(
        "elemental_stm_worker_done",
        extra={
            "person_id": str(person_id),
            "mode": mode,
            "signals_seen": signals_seen,
            "written_rows": written,
            "skipped_signals": skipped,
        },
    )
    return {
        "worker_name": "elemental_stm",
        "status": status,
        "inputs": {"person_id": str(person_id), "ts": ts.isoformat(), "mode": mode, "signals_seen": signals_seen},
        "outputs": {"written_rows": written, "skipped_signals": skipped},
        "executed_at": _now().isoformat(),
    }
