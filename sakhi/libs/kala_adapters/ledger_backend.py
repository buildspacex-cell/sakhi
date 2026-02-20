"""SakhiLedgerBackend — kala LedgerBackend backed by governance_events table."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from kala.ledger.core import Event, LedgerBackend


class SakhiLedgerBackend(LedgerBackend):
    """Persist kala governance events to PostgreSQL via governance_events table."""

    async def append(self, event: Event) -> None:  # noqa: D401
        from sakhi.apps.api.core.db import get_db

        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO governance_events (id, ts, person_id, event_type, action, actor, data, reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                """,
                event.id,
                event.timestamp,
                event.entity_id,
                event.event_type,
                event.action,
                event.actor,
                json.dumps(event.data, ensure_ascii=False, default=str),
                event.reason,
            )
        finally:
            await db.close()

    async def query(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        action: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        from sakhi.apps.api.core.db import get_db

        clauses: list[str] = []
        args: list[Any] = []
        idx = 1

        if entity_id is not None:
            clauses.append(f"person_id = ${idx}")
            args.append(entity_id)
            idx += 1
        if event_type is not None:
            clauses.append(f"event_type = ${idx}")
            args.append(event_type)
            idx += 1
        if action is not None:
            clauses.append(f"action = ${idx}")
            args.append(action)
            idx += 1
        if after is not None:
            clauses.append(f"ts > ${idx}")
            args.append(after)
            idx += 1
        if before is not None:
            clauses.append(f"ts < ${idx}")
            args.append(before)
            idx += 1

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM governance_events{where} ORDER BY ts DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        db = await get_db()
        try:
            rows = await db.fetch(sql, *args)
        finally:
            await db.close()

        events: list[Event] = []
        for row in rows:
            data_raw = row.get("data") or "{}"
            data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
            ts = row["ts"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            events.append(
                Event(
                    id=row["id"],
                    timestamp=ts,
                    entity_id=str(row["person_id"]),
                    event_type=row["event_type"],
                    action=row["action"],
                    actor=row.get("actor", "system"),
                    data=data,
                    reason=row.get("reason", ""),
                )
            )
        return events
