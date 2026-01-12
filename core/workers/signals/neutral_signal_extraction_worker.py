from __future__ import annotations

import datetime as dt
import json
from copy import deepcopy
from typing import Any, Dict, List
from uuid import UUID

from sakhi.apps.api.core.db import exec as dbexec, q as dbq

SOURCE_NAME = "neutral_signal_extractor_v1"

RULES = [
    {"type": "overactivation", "keywords": ["too much", "overloaded", "busy", "non-stop"], "confidence": 0.8},
    {"type": "recovery_gap", "keywords": ["tired", "exhausted", "drained", "no rest"], "confidence": 0.7},
    {"type": "dryness", "keywords": ["dry", "stiff", "tight"], "confidence": 0.6},
]


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_record(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _has_extractor_signal(record: Dict[str, Any]) -> bool:
    signals = record.get("signals") or []
    if not isinstance(signals, list):
        return False
    return any(isinstance(s, dict) and s.get("source") == SOURCE_NAME for s in signals)


async def run_neutral_signal_extraction_worker(person_id: UUID, ts: dt.datetime, mode: str = "manual") -> Dict[str, Any]:
    # TODO: tighten window for production; 1500-day span is for lab/backfill only.
    rows = await dbq(
        """
        SELECT id, record, created_at
        FROM memory_short_term
        WHERE (person_id::text = $1 OR user_id::text = $1)
          AND created_at >= NOW() - interval '1500 days'
        ORDER BY created_at DESC
        """,
        str(person_id),
    )
    scanned = 0
    added = 0
    for row in rows or []:
        scanned += 1
        record = _parse_record(row.get("record"))
        if _has_extractor_signal(record):
            continue
        text = (record.get("text") or "").lower()
        new_signals: List[Dict[str, Any]] = []
        for rule in RULES:
            if any(k in text for k in rule["keywords"]):
                new_signals.append(
                    {
                        "type": rule["type"],
                        "confidence": rule["confidence"],
                        "source": SOURCE_NAME,
                        "extracted_at": _now_iso(),
                    }
                )
        if not new_signals:
            continue
        new_record = deepcopy(record)
        existing = new_record.get("signals")
        if not isinstance(existing, list):
            existing = []
        new_record["signals"] = existing + new_signals
        await dbexec(
            """
            UPDATE memory_short_term
            SET record = $2::jsonb,
                updated_at = NOW()
            WHERE id = $1
            """,
            row.get("id"),
            json.dumps(new_record),
        )
        added += len(new_signals)

    status = "success" if added > 0 else "skipped"
    return {
        "worker_name": "neutral_signal_extraction",
        "status": status,
        "inputs": {"person_id": str(person_id), "ts": ts.isoformat(), "mode": mode, "stm_rows_scanned": scanned},
        "outputs": {"signals_added": added},
        "executed_at": _now_iso(),
    }
