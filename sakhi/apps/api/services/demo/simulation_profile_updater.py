"""
Simulation Profile Updater
--------------------------
Append new journal entries to lab simulation profiles and process them through
the same production pipeline path used by demo persona generation.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from httpx import ASGITransport, AsyncClient

from sakhi.apps.api.core.db import exec as dbexec, q as dbquery
from sakhi.apps.worker.simulation_worker_registry import (
    as_import_tuples,
    interval_import_tuples,
    monthly_import_tuples,
    resolve_forecast_runs_per_day,
    weekly_import_tuples,
)

LOGGER = logging.getLogger(__name__)

TimeOfDay = Literal["morning", "afternoon", "evening"]

_FILE_LOCKS: dict[str, asyncio.Lock] = {}
_TIME_OF_DAY_HOUR: dict[TimeOfDay, int] = {
    "morning": 8,
    "afternoon": 14,
    "evening": 21,
}

DAILY_WORKER_SPECS = as_import_tuples()
WEEKLY_WORKER_SPECS = weekly_import_tuples()
MONTHLY_WORKER_SPECS = monthly_import_tuples()
INTERVAL_WORKER_SPECS = interval_import_tuples()


def _repo_root() -> Path:
    # .../sakhi/apps/api/services/demo/simulation_profile_updater.py -> repo root
    return Path(__file__).resolve().parents[5]


def _simulation_file(persona_id: str) -> Path:
    return _repo_root() / "apps" / "web" / "public" / "simulation" / f"{persona_id}.json"


def _parse_iso(ts: str | None) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_json(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    try:
        return dict(obj)
    except Exception:
        return str(obj)


def _entry_sort_key(entry: Dict[str, Any]) -> tuple[int, datetime]:
    day = _to_int(entry.get("day"))
    ts = _parse_iso(entry.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)
    return (day, ts)


def _next_day_and_timestamp(sim_data: Dict[str, Any], time_of_day: TimeOfDay) -> tuple[int, datetime]:
    entries = sim_data.get("entries") or []
    hour = _TIME_OF_DAY_HOUR[time_of_day]

    if entries:
        last_entry = max((e for e in entries if isinstance(e, dict)), key=_entry_sort_key)
        last_day = _to_int(last_entry.get("day"))
        day = max(last_day + 1, _to_int(sim_data.get("total_days")) + 1)
        last_ts = _parse_iso(last_entry.get("timestamp")) or _parse_iso(sim_data.get("end_time"))
        if not last_ts:
            last_ts = datetime.now(timezone.utc)
        target_date = (last_ts + timedelta(days=1)).date()
    else:
        day = max(1, _to_int(sim_data.get("total_days")) + 1)
        start_ts = _parse_iso(sim_data.get("start_time")) or (datetime.now(timezone.utc) - timedelta(days=30))
        target_date = (start_ts + timedelta(days=day - 1)).date()

    return (
        day,
        datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        ),
    )


async def _ensure_profile_user(user_id: str, persona: Dict[str, Any]) -> None:
    baseline = persona.get("dosha_baseline") or {}
    v = float(baseline.get("vata") or 0)
    p = float(baseline.get("pitta") or 0)
    k = float(baseline.get("kapha") or 0)

    if max(v, p, k) < 0.4:
        os_type = "Balanced"
    elif p >= v and p >= k:
        os_type = "Driven"
    elif v >= p and v >= k:
        os_type = "Quick-moving"
    else:
        os_type = "Steady"

    os_data = json.dumps(
        {
            "type": os_type,
            "primary": max({"vata": v, "pitta": p, "kapha": k}, key=lambda x: {"vata": v, "pitta": p, "kapha": k}[x]),
            "dosha_baseline": baseline,
            "source": "simulation_profile",
        }
    )
    rhythm = persona.get("rhythm") or {}
    rhythm_data = json.dumps(
        {
            "slots": {
                "morning": rhythm.get("morning", "medium"),
                "afternoon": rhythm.get("afternoon", "medium"),
                "evening": rhythm.get("evening", "medium"),
            }
        }
    )

    persona_id = str(persona.get("id") or "simulation_profile")
    email = f"demo_{persona_id}@sakhi.dev"

    await dbexec(
        "INSERT INTO persons (id, created_at) VALUES ($1, NOW()) ON CONFLICT (id) DO NOTHING",
        user_id,
    )
    await dbexec(
        """INSERT INTO users (id, email, full_name, created_at, updated_at)
           VALUES ($1, $2, $3, NOW(), NOW())
           ON CONFLICT (id) DO NOTHING""",
        user_id,
        email,
        str(persona.get("name") or "Simulation User"),
    )
    await dbexec(
        "INSERT INTO auth_users (id, email, created_at) VALUES ($1, $2, NOW()) ON CONFLICT (id) DO NOTHING",
        user_id,
        email,
    )
    await dbexec(
        "INSERT INTO profiles (user_id, email, created_at, updated_at) VALUES ($1, $2, NOW(), NOW()) ON CONFLICT (user_id) DO NOTHING",
        user_id,
        email,
    )
    await dbexec(
        """INSERT INTO personal_model (person_id, operating_system, rhythm_state, updated_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (person_id) DO NOTHING""",
        user_id,
        os_data,
        rhythm_data,
    )


def _snapshot_tasks() -> set[asyncio.Task[Any]]:
    current = asyncio.current_task()
    return {t for t in asyncio.all_tasks() if t is not current and not t.done()}


async def _drain_background_tasks(
    tasks_before: set[asyncio.Task[Any]],
    timeout: float = 30.0,
) -> None:
    current = asyncio.current_task()
    new_tasks = {
        t for t in asyncio.all_tasks() if t is not current and not t.done() and t not in tasks_before
    }
    if not new_tasks:
        return
    done, pending = await asyncio.wait(new_tasks, timeout=timeout)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.sleep(0.25)
    for task in done | pending:
        if task.done():
            try:
                task.result()
            except Exception:
                pass


async def _backdate_generated_rows(
    user_id: str,
    entry_id: str,
    timestamp: datetime,
    existing_episodic: set[str],
) -> None:
    await dbexec(
        "UPDATE journal_entries SET ts = $2, created_at = $2, updated_at = $2 WHERE id = $1",
        entry_id,
        timestamp,
    )
    try:
        await dbexec(
            """UPDATE conversation_turns
               SET created_at = $2
               WHERE user_id = $1 AND created_at > NOW() - INTERVAL '30 seconds'""",
            user_id,
            timestamp,
        )
    except Exception:
        pass
    try:
        await dbexec(
            """UPDATE conversation_sessions
               SET last_active_at = $2, created_at = LEAST(created_at, $2)
               WHERE user_id = $1 AND last_active_at > NOW() - INTERVAL '30 seconds'""",
            user_id,
            timestamp,
        )
    except Exception:
        pass
    try:
        await dbexec(
            "UPDATE memory_short_term SET created_at = $2 WHERE entry_id = $1",
            entry_id,
            timestamp,
        )
    except Exception:
        pass
    try:
        rows = await dbquery(
            "SELECT id FROM memory_episodic WHERE user_id = $1",
            user_id,
        )
        for row in rows or []:
            episodic_id = str(row["id"])
            if episodic_id not in existing_episodic:
                await dbexec(
                    "UPDATE memory_episodic SET created_at = $2 WHERE id = $1",
                    episodic_id,
                    timestamp,
                )
    except Exception:
        pass
    try:
        await dbexec(
            "UPDATE pattern_occurrences SET detected_at = $2 WHERE entry_id = $1::uuid",
            entry_id,
            timestamp,
        )
    except Exception:
        pass


async def _run_turn_for_journal(
    app: Any,
    user_id: str,
    content: str,
    timestamp: datetime,
    day: int,
) -> Dict[str, Any]:
    existing_episodic: set[str] = set()
    try:
        rows = await dbquery("SELECT id FROM memory_episodic WHERE user_id = $1", user_id)
        existing_episodic = {str(r["id"]) for r in (rows or [])}
    except Exception:
        pass

    tasks_before = _snapshot_tasks()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=120.0,
    ) as client:
        response = await client.post(
            "/v2/turn",
            params={"user": user_id, "debug": "1"},
            json={"text": content, "ts": timestamp.isoformat()},
        )
    if response.status_code != 200:
        raise RuntimeError(f"/v2/turn failed ({response.status_code}): {response.text[:300]}")

    payload = response.json()
    await _drain_background_tasks(tasks_before, timeout=120.0)

    entry_id = payload.get("entry_id")
    if entry_id:
        await _backdate_generated_rows(
            user_id=user_id,
            entry_id=str(entry_id),
            timestamp=timestamp,
            existing_episodic=existing_episodic,
        )

    LOGGER.info("[simulation] processed journal day=%s user=%s", day, user_id)
    return {
        "entry_id": str(entry_id) if entry_id else None,
        "reply": payload.get("reply", ""),
        "friction_state": payload.get("friction_state"),
        "debug_data": payload.get("debug_data"),
    }


async def _run_worker_group_for_user(
    *,
    user_id: str,
    day: int,
    phase_name: str,
    worker_specs: list[tuple[str, str, str]],
    key_prefix: str,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for name, module_path, function_name in worker_specs:
        key = f"{key_prefix}{name}"
        try:
            module = importlib.import_module(module_path)
            fn = getattr(module, function_name)
        except Exception as exc:
            results[key] = {"ok": False, "error": f"import: {exc}"}
            continue

        try:
            tasks_before = _snapshot_tasks()
            await asyncio.wait_for(fn(user_id), timeout=30.0)
            await _drain_background_tasks(tasks_before, timeout=10.0)
            results[key] = {"ok": True}
        except asyncio.TimeoutError:
            results[key] = {"ok": False, "error": "timeout"}
        except Exception as exc:
            results[key] = {"ok": False, "error": str(exc)[:200]}

    LOGGER.info(
        "[simulation] %s workers complete day=%s user=%s ok=%s/%s",
        phase_name,
        day,
        user_id,
        sum(1 for r in results.values() if r.get("ok")),
        len(worker_specs),
    )
    return results


async def _run_daily_workers_for_user(user_id: str, day: int) -> Dict[str, Any]:
    return await _run_worker_group_for_user(
        user_id=user_id,
        day=day,
        phase_name="daily",
        worker_specs=DAILY_WORKER_SPECS,
        key_prefix="",
    )


async def _run_weekly_workers_for_user(user_id: str, day: int) -> Dict[str, Any]:
    return await _run_worker_group_for_user(
        user_id=user_id,
        day=day,
        phase_name="weekly",
        worker_specs=WEEKLY_WORKER_SPECS,
        key_prefix="weekly.",
    )


async def _run_monthly_workers_for_user(user_id: str, day: int) -> Dict[str, Any]:
    return await _run_worker_group_for_user(
        user_id=user_id,
        day=day,
        phase_name="monthly",
        worker_specs=MONTHLY_WORKER_SPECS,
        key_prefix="monthly.",
    )


async def _run_interval_workers_for_user(
    user_id: str,
    day: int,
    runs_per_day: int,
) -> Dict[str, Any]:
    if runs_per_day <= 0:
        return {}
    results: Dict[str, Any] = {}
    for pass_index in range(1, runs_per_day + 1):
        pass_results = await _run_worker_group_for_user(
            user_id=user_id,
            day=day,
            phase_name=f"interval#{pass_index}",
            worker_specs=INTERVAL_WORKER_SPECS,
            key_prefix=f"interval.{pass_index}.",
        )
        results.update(pass_results)
    return results


async def _run_cadence_workers_for_user(user_id: str, day: int) -> Dict[str, Any]:
    results = await _run_daily_workers_for_user(user_id=user_id, day=day)
    if day % 7 == 0:
        results.update(await _run_weekly_workers_for_user(user_id=user_id, day=day))
    if day % 30 == 0:
        results.update(await _run_monthly_workers_for_user(user_id=user_id, day=day))
    raw_interval_runs = os.getenv("SIMULATION_UPDATER_FORECAST_RUNS_PER_DAY")
    interval_runs = 0
    if raw_interval_runs is not None:
        try:
            interval_runs = resolve_forecast_runs_per_day(int(raw_interval_runs))
        except ValueError:
            interval_runs = 0
    if interval_runs > 0:
        results.update(
            await _run_interval_workers_for_user(
                user_id=user_id,
                day=day,
                runs_per_day=interval_runs,
            )
        )
    return results


async def _capture_snapshot(
    user_id: str,
    day: int,
    reference_time: datetime | None = None,
    worker_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    model = await dbquery(
        "SELECT * FROM personal_model WHERE person_id = $1",
        user_id,
        one=True,
    )
    memory_count = await dbquery(
        "SELECT COUNT(*) as count FROM memory_episodic WHERE user_id = $1",
        user_id,
        one=True,
    )
    pattern_count = await dbquery(
        "SELECT COUNT(*) as count FROM pattern_occurrences WHERE person_id = $1",
        user_id,
        one=True,
    )
    recent = await dbquery(
        """SELECT id, text AS content, context_tags, created_at
           FROM memory_episodic
           WHERE user_id = $1
           ORDER BY created_at DESC
           LIMIT 5""",
        user_id,
    )

    friction: Dict[str, Any] = {}
    try:
        from sakhi.apps.api.services.ayurveda.vikriti import get_full_friction_state

        friction = await get_full_friction_state(user_id, reference_time=reference_time)
    except Exception:
        pass

    provenance: Dict[str, int] = {}
    try:
        stm = await dbquery(
            "SELECT COUNT(*) as count FROM memory_short_term WHERE user_id = $1",
            user_id,
            one=True,
        )
        embed = await dbquery(
            """SELECT COUNT(*) as count
               FROM journal_embeddings
               WHERE entry_id IN (SELECT id FROM journal_entries WHERE user_id = $1)""",
            user_id,
            one=True,
        )
        nodes = await dbquery(
            "SELECT COUNT(*) as count FROM memory_nodes WHERE person_id = $1",
            user_id,
            one=True,
        )
        edges = await dbquery(
            "SELECT COUNT(*) as count FROM memory_edges WHERE person_id = $1",
            user_id,
            one=True,
        )
        provenance = {
            "stm_rows": _to_int((stm or {}).get("count")),
            "embedding_rows": _to_int((embed or {}).get("count")),
            "graph_nodes": _to_int((nodes or {}).get("count")),
            "graph_edges": _to_int((edges or {}).get("count")),
        }
    except Exception:
        pass

    brain_states: Dict[str, Any] = {}
    if model:
        for field in [
            "coherence_state",
            "alignment_state",
            "emotion_state",
            "soul_state",
            "rhythm_state",
            "identity_momentum_state",
            "forecast_state",
            "body_state",
            "operating_system",
        ]:
            raw = model.get(field)
            if isinstance(raw, str):
                try:
                    brain_states[field] = json.loads(raw)
                except Exception:
                    brain_states[field] = raw
            elif raw is not None:
                brain_states[field] = _safe_json(raw)

    themes: list[Dict[str, Any]] = []
    patterns: list[Dict[str, Any]] = []
    try:
        t_rows = await dbquery(
            """SELECT theme, clarity_score, updated_at
               FROM theme_states
               WHERE person_id = $1
               ORDER BY clarity_score DESC
               LIMIT 20""",
            user_id,
        )
        themes = [dict(r) for r in (t_rows or [])]
    except Exception:
        pass
    try:
        p_rows = await dbquery(
            """SELECT pattern_type, pattern_value, confidence, trajectory,
                      status, mention_count, distinct_days
               FROM crystallized_patterns
               WHERE person_id = $1 AND status IN ('active', 'emerging')
               ORDER BY confidence DESC
               LIMIT 30""",
            user_id,
        )
        patterns = [dict(r) for r in (p_rows or [])]
    except Exception:
        pass

    return {
        "day": day,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "personal_model": _safe_json(dict(model) if model else {}),
        "memory_count": _to_int((memory_count or {}).get("count")),
        "pattern_count": _to_int((pattern_count or {}).get("count")),
        "friction_state": _safe_json(friction),
        "recent_memories": [
            {
                "content": row.get("content", ""),
                "created_at": str(row.get("created_at", "")),
            }
            for row in (recent or [])
        ],
        "provenance": provenance,
        "brain_states": _safe_json(brain_states),
        "worker_results": worker_results or {},
        "themes": _safe_json(themes),
        "crystallized_patterns": _safe_json(patterns),
    }


async def add_journal_to_simulation_profile(
    *,
    app: Any,
    persona_id: str,
    content: str,
    time_of_day: TimeOfDay = "evening",
) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("Journal content is required")

    path = _simulation_file(persona_id)
    if not path.exists():
        raise FileNotFoundError(f"Simulation profile not found: {persona_id}")

    lock = _FILE_LOCKS.setdefault(persona_id, asyncio.Lock())
    async with lock:
        with path.open("r", encoding="utf-8") as handle:
            sim_data = json.load(handle)

        user_id = str(sim_data.get("user_id") or "").strip()
        persona = sim_data.get("persona") or {}
        if not user_id:
            raise ValueError(f"Missing user_id in simulation profile: {persona_id}")
        if not isinstance(persona, dict):
            raise ValueError(f"Missing persona data in simulation profile: {persona_id}")

        await _ensure_profile_user(user_id=user_id, persona=persona)

        day, timestamp = _next_day_and_timestamp(sim_data, time_of_day)
        turn_result = await _run_turn_for_journal(
            app=app,
            user_id=user_id,
            content=text,
            timestamp=timestamp,
            day=day,
        )
        worker_results = await _run_cadence_workers_for_user(user_id=user_id, day=day)
        snapshot = await _capture_snapshot(
            user_id=user_id,
            day=day,
            reference_time=timestamp,
            worker_results=worker_results,
        )

        entry = {
            "day": day,
            "time_of_day": time_of_day,
            "content": text,
            "timestamp": timestamp.isoformat(),
            "reply": turn_result.get("reply", ""),
            "friction_state": turn_result.get("friction_state"),
        }

        entries = [e for e in (sim_data.get("entries") or []) if isinstance(e, dict)]
        entries.append(entry)
        entries.sort(key=_entry_sort_key)
        snapshots = [s for s in (sim_data.get("snapshots") or []) if isinstance(s, dict)]
        snapshots.append(snapshot)
        snapshots.sort(key=lambda s: _to_int(s.get("day")))

        sim_data["entries"] = entries
        sim_data["snapshots"] = snapshots
        sim_data["total_entries"] = len(entries)
        sim_data["total_days"] = max(_to_int(sim_data.get("total_days")), day)
        sim_data["end_time"] = timestamp.isoformat()
        sim_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        sim_data.setdefault("errors", [])
        sim_data["errors"] = [e for e in sim_data["errors"] if e]  # keep shape consistent
        try:
            # Best-effort enrichment; do not block add-journal flow if continuity imports fail.
            from sakhi.apps.api.services.demo.simulation_continuity import (
                enrich_simulation_payload,
            )

            enrich_simulation_payload(sim_data, persona_id=persona_id)
        except Exception as exc:
            LOGGER.warning(
                "Skipping simulation continuity enrichment for %s due to error: %s",
                persona_id,
                exc,
            )

        with path.open("w", encoding="utf-8") as handle:
            json.dump(sim_data, handle, indent=2, default=str, ensure_ascii=False)

        return {
            "persona_id": persona_id,
            "entry": entry,
            "snapshot_day": day,
            "total_days": sim_data["total_days"],
            "total_entries": sim_data["total_entries"],
            "updated_at": sim_data["generated_at"],
            "turn_debug": turn_result.get("debug_data") or {},
        }
