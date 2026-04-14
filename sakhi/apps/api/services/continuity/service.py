from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sakhi.apps.api.services.governance.service import log_turn_event
from sakhi.apps.api.services.continuity.adapters import (
    canonicalize_anchor,
    get_continuity_policy,
    load_journal_entries_for_continuity,
    upsert_continuity_policy,
)
from sakhi.apps.api.services.continuity.compiler import (
    build_compiled_topics_index,
    compile_journal_continuity,
    parse_continuity_window,
    select_compiled_topic,
)

CONTINUITY_SCOPE = "continuity_arc_surface"


def _parse_source_ref(source_ref: str) -> dict[str, str]:
    raw = (source_ref or "").strip()
    if not raw or ":" not in raw:
        raise ValueError("source_ref must be in '<source>:<id>' format")
    source, item_id = raw.split(":", 1)
    source = source.strip()
    item_id = item_id.strip()
    if not source or not item_id:
        raise ValueError("source_ref must be in '<source>:<id>' format")
    return {"source": source, "id": item_id}


def _build_versions(compiled: dict[str, Any]) -> dict[str, Any]:
    return {
        "taxonomy_version": compiled.get("taxonomy_version"),
        "compiler_version": compiled.get("compiler_version"),
        "threshold_profile_version": compiled.get("threshold_profile_version"),
        "compiled_at": compiled.get("compiled_at"),
        "inputs_hash": compiled.get("inputs_hash"),
    }


def _topic_summary(topic: dict[str, Any]) -> dict[str, Any]:
    arc = topic.get("arc") or {}
    features = arc.get("features") or {}
    return {
        "anchor": topic.get("anchor"),
        "label": topic.get("label"),
        "confidence": float(topic.get("confidence") or 0.0),
        "selected_count": int(topic.get("selected_count") or 0),
        "span_days": float(arc.get("span_days") or 0.0),
        "start_ts": arc.get("start_ts"),
        "end_ts": arc.get("end_ts"),
        "direction": features.get("direction"),
        "surface": topic.get("surface") or {},
        "sub_threads": topic.get("sub_threads") or [],
    }


def _included_moments(topic: dict[str, Any]) -> list[dict[str, Any]]:
    event_refs = (topic.get("arc") or {}).get("event_refs") or []
    entry_tags = topic.get("entry_tags") or {}
    moments: list[dict[str, Any]] = []
    for ref in event_refs:
        key = f"{int(ref.get('day') or 0)}|{str(ref.get('ts') or '')}"
        tag = entry_tags.get(key) or {}
        moments.append(
            {
                "source_ref": ref.get("source_ref"),
                "source_type": ref.get("source_type"),
                "source_id": ref.get("source_id"),
                "ts": ref.get("ts"),
                "day": ref.get("day"),
                "short_snippet": ref.get("excerpt") or "",
                "confidence": float(tag.get("confidence") or 0.0),
                "facet": tag.get("facet") or ref.get("facet"),
                "facet_state": tag.get("facet_state") or ref.get("facet_state"),
                "decision_state": tag.get("decision_state") or ref.get("decision_state"),
                "stance": tag.get("stance") or ref.get("stance"),
            }
        )
    return moments


async def _compile_window_continuity(
    person_id: str,
    *,
    window: str,
    scope: str,
    max_gap_days: int = 21,
    min_len: int = 3,
) -> tuple[dict[str, Any], dict[str, Any], datetime, datetime]:
    policy = await get_continuity_policy(person_id, scope)
    if not policy.get("enabled"):
        raise PermissionError(f"Continuity surfacing is disabled for scope '{scope}'")

    now = datetime.now(UTC)
    from_ts = now - parse_continuity_window(window)
    journal_rows = await load_journal_entries_for_continuity(
        person_id,
        from_ts=from_ts,
        to_ts=now,
        exclusions=policy.get("exclusions") or [],
    )
    compiled = compile_journal_continuity(
        person_id=person_id,
        journal_rows=journal_rows,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )
    return compiled, policy, from_ts, now


async def get_continuity_topics(
    person_id: str,
    *,
    window: str = "120d",
    scope: str = CONTINUITY_SCOPE,
    debug: bool = False,
) -> dict[str, Any]:
    compiled, policy, from_ts, now = await _compile_window_continuity(
        person_id,
        window=window,
        scope=scope,
        max_gap_days=21,
        min_len=3,
    )
    topics = build_compiled_topics_index(compiled, debug=debug)
    response = {
        "person_id": person_id,
        "window": {
            "from": from_ts.isoformat(),
            "to": now.isoformat(),
        },
        "consent": {
            "scope": scope,
            "allowed": True,
        },
        "policy": {
            "enabled": True,
            "exclusions": policy.get("exclusions") or [],
        },
        "versions": _build_versions(compiled),
        "topics": [_topic_summary(topic) for topic in topics],
    }
    if debug:
        response["topic_details"] = topics
    return response


async def get_continuity_arc(
    person_id: str,
    anchor: str,
    *,
    window: str = "90d",
    max_gap_days: int = 21,
    min_len: int = 3,
    scope: str = CONTINUITY_SCOPE,
    debug: bool = False,
    log_access: bool = True,
) -> dict[str, Any]:
    if max_gap_days <= 0:
        raise ValueError("max_gap_days must be positive")
    if min_len <= 0:
        raise ValueError("min_len must be positive")

    compiled, policy, from_ts, now = await _compile_window_continuity(
        person_id,
        window=window,
        scope=scope,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )
    normalized_anchor = canonicalize_anchor(anchor)
    topic = select_compiled_topic(compiled, anchor=normalized_anchor, debug=debug)
    if int(topic.get("selected_count") or 0) < min_len:
        raise LookupError("Not enough continuity items for the requested anchor and window")

    if log_access:
        await log_turn_event(
            person_id=person_id,
            action=CONTINUITY_SCOPE,
            event_type="observed",
            actor="system",
            data={
                "anchor": normalized_anchor,
                "window": window,
                "event_count": topic.get("selected_count"),
                "inputs_hash": compiled.get("inputs_hash"),
            },
            reason="continuity arc surfaced",
        )

    response = {
        "person_id": person_id,
        "anchor": normalized_anchor,
        "label": topic.get("label"),
        "window": {
            "from": from_ts.isoformat(),
            "to": now.isoformat(),
        },
        "consent": {
            "scope": scope,
            "allowed": True,
        },
        "policy": {
            "enabled": True,
            "exclusions": policy.get("exclusions") or [],
        },
        "versions": _build_versions(compiled),
        "topic_confidence": float(topic.get("confidence") or 0.0),
        "surface": topic.get("surface") or {},
        "arc": topic.get("arc") or {},
        "included_moments": _included_moments(topic),
        "audit": {
            "event_type": "observed",
            "action": CONTINUITY_SCOPE,
        },
    }
    if debug:
        response["entry_tags"] = topic.get("entry_tags") or {}
    return response


async def enable_continuity_policy(
    person_id: str,
    *,
    scope: str = CONTINUITY_SCOPE,
) -> dict[str, Any]:
    current = await get_continuity_policy(person_id, scope)
    updated = await upsert_continuity_policy(
        person_id,
        scope=scope,
        enabled=True,
        exclusions=current.get("exclusions") or [],
    )
    await log_turn_event(
        person_id=person_id,
        action="continuity_enable",
        event_type="observed",
        actor="system",
        data={"scope": scope},
        reason="continuity policy enabled",
    )
    return updated


async def exclude_continuity_ref(
    person_id: str,
    source_ref: str,
    *,
    scope: str = CONTINUITY_SCOPE,
) -> dict[str, Any]:
    current = await get_continuity_policy(person_id, scope)
    parsed = _parse_source_ref(source_ref)
    exclusions = [
        item
        for item in (current.get("exclusions") or [])
        if not (
            str(item.get("source") or "") == parsed["source"]
            and str(item.get("id") or "") == parsed["id"]
        )
    ]
    exclusions.append(parsed)
    updated = await upsert_continuity_policy(
        person_id,
        scope=scope,
        enabled=bool(current.get("enabled")),
        exclusions=exclusions,
    )
    await log_turn_event(
        person_id=person_id,
        action="continuity_exclude_ref",
        event_type="observed",
        actor="system",
        data={"scope": scope, "source_ref": source_ref},
        reason="continuity source excluded",
    )
    return updated


__all__ = [
    "CONTINUITY_SCOPE",
    "enable_continuity_policy",
    "exclude_continuity_ref",
    "get_continuity_arc",
    "get_continuity_topics",
]
