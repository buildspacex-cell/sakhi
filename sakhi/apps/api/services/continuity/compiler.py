from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sakhi.apps.api.services.continuity.inference import (
    ClassificationState,
    classify_entry_for_continuity,
    compile_entries_for_continuity,
)


def parse_continuity_window(window: str) -> timedelta:
    token = (window or "90d").strip().lower()
    if token.endswith("d") and token[:-1].isdigit():
        days = int(token[:-1])
        if days <= 0 or days > 3650:
            raise ValueError("window days must be between 1 and 3650")
        return timedelta(days=days)
    raise ValueError("window must be in '<days>d' format, e.g. 90d")


def classify_continuity_text(text: str) -> dict[str, Any]:
    return classify_entry_for_continuity({"content": text})


def compile_journal_continuity(
    *,
    person_id: str,
    journal_rows: list[dict[str, Any]],
    max_gap_days: int = 21,
    min_len: int = 3,
) -> dict[str, Any]:
    normalized_entries = _normalize_journal_entries(journal_rows)
    compiled = compile_entries_for_continuity(
        person_id=person_id,
        entries=normalized_entries,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )
    compiled["inputs_hash"] = _compute_journal_inputs_hash(
        person_id=person_id,
        journal_rows=journal_rows,
        max_gap_days=max_gap_days,
        min_len=min_len,
        taxonomy_version=str(compiled.get("taxonomy_version") or ""),
        compiler_version=str(compiled.get("compiler_version") or ""),
        threshold_profile_version=str(compiled.get("threshold_profile_version") or ""),
    )
    return compiled


def select_compiled_topic(
    compiled: dict[str, Any],
    *,
    anchor: str,
    debug: bool = False,
) -> dict[str, Any]:
    target = _normalize_anchor(anchor)
    for topic in compiled.get("topics") or []:
        if _normalize_anchor(topic.get("anchor")) == target:
            selected = copy.deepcopy(topic)
            if not debug:
                _strip_topic_debug(selected)
            return selected
    raise LookupError("No continuity arc found for the requested anchor and window")


def build_compiled_topics_index(
    compiled: dict[str, Any],
    *,
    debug: bool = False,
) -> list[dict[str, Any]]:
    topics: list[dict[str, Any]] = []
    for topic in compiled.get("topics") or []:
        topic_copy = copy.deepcopy(topic)
        if not debug:
            _strip_topic_debug(topic_copy)
        topics.append(topic_copy)
    return topics


def _normalize_journal_entries(journal_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = sorted(
        [
            row
            for row in journal_rows
            if isinstance(row, dict) and _coerce_dt(row.get("ts")) is not None
        ],
        key=lambda row: (
            _coerce_dt(row.get("ts")),
            str(row.get("id") or ""),
        ),
    )
    if not normalized_rows:
        return []

    start_day = _coerce_dt(normalized_rows[0].get("ts")).date()
    entries: list[dict[str, Any]] = []
    for row in normalized_rows:
        ts = _coerce_dt(row.get("ts"))
        if ts is None:
            continue
        content = str(row.get("content") or row.get("cleaned") or row.get("title") or "").strip()
        if not content:
            continue
        day = _relative_day(ts.date(), start_day)
        source_id = str(row.get("id") or "").strip()
        entry: dict[str, Any] = {
            "day": day,
            "timestamp": ts.isoformat(),
            "time_of_day": _time_of_day_label(ts),
            "content": content,
            "source_type": "journal",
            "source_id": source_id,
            "source_ref": f"journal:{source_id}",
        }
        # Preserve LLM-inferred hints so _classify_entry can honour them.
        for hint_key in (
            "hint_anchor",
            "hint_decision_state",
            "hint_affective_scalar",
            "hint_epistemic_state",
        ):
            val = row.get(hint_key)
            if val is not None:
                entry[hint_key] = val
        entries.append(entry)
    return entries


def _compute_journal_inputs_hash(
    *,
    person_id: str,
    journal_rows: list[dict[str, Any]],
    max_gap_days: int,
    min_len: int,
    taxonomy_version: str,
    compiler_version: str,
    threshold_profile_version: str,
) -> str:
    canonical_rows = sorted(
        [
            {
                "id": str(row.get("id") or ""),
                "ts": _coerce_dt(row.get("ts")).isoformat() if _coerce_dt(row.get("ts")) else "",
                "updated_at": _coerce_dt(row.get("updated_at")).isoformat()
                if _coerce_dt(row.get("updated_at"))
                else "",
            }
            for row in journal_rows
            if isinstance(row, dict)
        ],
        key=lambda row: (row["ts"], row["id"]),
    )
    payload = {
        "person_id": person_id,
        "rows": canonical_rows,
        "max_gap_days": max_gap_days,
        "min_len": min_len,
        "taxonomy_version": taxonomy_version,
        "compiler_version": compiler_version,
        "threshold_profile_version": threshold_profile_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _strip_topic_debug(topic: dict[str, Any]) -> None:
    entry_tags = topic.get("entry_tags")
    if isinstance(entry_tags, dict):
        for item in entry_tags.values():
            if isinstance(item, dict):
                item.pop("trace", None)


def _coerce_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return None


def _relative_day(current_day: date, start_day: date) -> int:
    return (current_day - start_day).days + 1


def _time_of_day_label(ts: datetime) -> str:
    hour = ts.astimezone(UTC).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _normalize_anchor(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


__all__ = [
    "ClassificationState",
    "build_compiled_topics_index",
    "classify_continuity_text",
    "compile_journal_continuity",
    "parse_continuity_window",
    "select_compiled_topic",
]
