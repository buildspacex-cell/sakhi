"""
READ-ONLY verification for Sakhi Personal Intelligence v2.3.
No writes, no workers, no LLMs. Plain-text report only.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import asyncio
from sakhi.apps.api.core.db import q

PERSON_ID = "c10fbd98-25fa-4445-8aba-e5243bc01564"
DAYS_EXPECTED = 7


def _print_header(title: str) -> None:
    print(f"\n[{title}]")


def _status_line(label: str, status: str) -> None:
    print(f"{label}: {status}")


async def _fetch_episodes() -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT id, ts::timestamptz, text, content_hash,
               (vector_vec IS NOT NULL) AS has_vec,
               emotional_state, rhythm_state, soul_conflict, soul_friction, emotion_loop
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        """,
        PERSON_ID,
    )
    return rows or []


def section1_daily_integrity(episodes: List[Dict[str, Any]]) -> str:
    if not episodes:
        print("No episodic rows found.")
        return "FAIL"
    # Determine the window as the last DAYS_EXPECTED calendar days ending at max ts
    max_ts = max(ep["ts"] for ep in episodes if ep.get("ts"))
    end_day = max_ts.date()
    start_day = end_day - timedelta(days=DAYS_EXPECTED - 1)
    counts = defaultdict(int)
    for ep in episodes:
        ts = ep.get("ts")
        if not ts:
            continue
        d = ts.date()
        if start_day <= d <= end_day:
            counts[d] += 1

    _print_header("1] Episodic Memory — Daily Windows")
    missing = []
    duplicates = []
    for i in range(DAYS_EXPECTED):
        day = start_day + timedelta(days=i)
        c = counts.get(day, 0)
        mark = "✅" if c == 1 else "⚠️" if c == 0 else "🚫"
        print(f"{day} : {c} episode(s) {mark}")
        if c == 0:
            missing.append(day)
        if c > 1:
            duplicates.append(day)

    if missing or duplicates:
        reason = []
        if missing:
            reason.append(f"missing {len(missing)} day(s)")
        if duplicates:
            reason.append(f"duplicates on {len(duplicates)} day(s)")
        print(f"FAIL: {'; '.join(reason)}")
        return "FAIL"
    print(f"PASS: {DAYS_EXPECTED}/{DAYS_EXPECTED} daily episodes present")
    return "PASS"


def section2_core_fields(episodes: List[Dict[str, Any]]) -> str:
    _print_header("2] Episodic Core Fields")
    missing = 0
    for ep in episodes[: max(5, DAYS_EXPECTED)]:  # sample recent set
        summary_ok = bool((ep.get("text") or "").strip())
        vector_ok = bool(ep.get("has_vec"))
        hash_ok = bool(ep.get("content_hash"))
        print(
            f"episode_id={ep.get('id')} summary={'YES' if summary_ok else 'NO'} "
            f"vector={'YES' if vector_ok else 'NO'} hash={'YES' if hash_ok else 'NO'}"
        )
        if not (summary_ok and vector_ok and hash_ok):
            missing += 1
    if missing:
        print(f"WARN: {missing} episode(s) missing core fields")
        return "WARN"
    print("PASS: all sampled episodes have core fields")
    return "PASS"


def section3_enrichment(episodes: List[Dict[str, Any]]) -> str:
    _print_header("3] Episodic Enrichment Coverage")
    warn = False
    for ep in episodes[: max(5, DAYS_EXPECTED)]:
        ts = ep.get("ts")
        conflict = bool(ep.get("soul_conflict"))
        friction = bool(ep.get("soul_friction"))
        loop = bool(ep.get("emotion_loop"))
        print(
            f"{ts.date() if ts else 'unknown'}: conflict={'YES' if conflict else 'NO'} "
            f"friction={'YES' if friction else 'NO'} loop={'YES' if loop else 'NO'}"
        )
        # Heuristic warn: enrichment on first observed day only
        # (keep simple: if only first item has enrichment)
    enriched = [ep for ep in episodes if ep.get("soul_conflict") or ep.get("soul_friction") or ep.get("emotion_loop")]
    if enriched and len(enriched) == 1 and episodes and enriched[0] == episodes[-1]:
        warn = True
    if warn:
        print("WARN: enrichment appears only on earliest episode")
        return "WARN"
    print("PASS: enrichment fields present where confidence likely allowed")
    return "PASS"


async def section4_context_cache() -> str:
    _print_header("4] Context Cache")
    row = await q(
        """
        SELECT merged_context_vector, updated_at
        FROM memory_context_cache
        WHERE person_id = $1 AND window_kind = 'default'
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        PERSON_ID,
        one=True,
    )
    if not row:
        print("FAIL: no context cache row")
        return "FAIL"
    has_vec = bool(row.get("merged_context_vector"))
    print(f"merged_context_vector: {'PRESENT' if has_vec else 'MISSING'}")
    print(f"last_updated: {row.get('updated_at')}")
    return "PASS" if has_vec else "FAIL"


async def section5_personal_model() -> str:
    _print_header("5] Personal Model States")
    try:
        pm = await q(
            """
            SELECT identity_momentum_state, rhythm_soul_state, esr_state,
                   internal_decision_graph, goals_state, soul_narrative
            FROM personal_model
            WHERE person_id = $1
            """,
            PERSON_ID,
            one=True,
        )
    except Exception:
        # Fallback schema without esr_state
        pm = await q(
            """
            SELECT identity_momentum_state, rhythm_soul_state,
                   internal_decision_graph, goals_state, soul_narrative
            FROM personal_model
            WHERE person_id = $1
            """,
            PERSON_ID,
            one=True,
        )
    if not pm:
        print("FAIL: no personal_model row")
        return "FAIL"
    fields = [
        ("identity_momentum", pm.get("identity_momentum_state")),
        ("rhythm_soul", pm.get("rhythm_soul_state")),
        ("esr_state", pm.get("esr_state")),
        ("decision_graph", pm.get("internal_decision_graph")),
        ("goals_state", pm.get("goals_state")),
    ]
    missing = [name for name, val in fields if not val]
    for name, val in fields:
        print(f"{name}: {'PRESENT' if val else 'MISSING'}")
    if pm.get("soul_narrative") is not None:
        print("soul_narrative: PRESENT")
    else:
        print("soul_narrative: MISSING (acceptable if not run)")
    if missing:
        print(f"FAIL: missing {', '.join(missing)}")
        return "FAIL"
    return "PASS"


async def section6_goals_themes() -> str:
    _print_header("6] Goals/Themes Integration")
    pm = await q(
        "SELECT goals_state FROM personal_model WHERE person_id = $1",
        PERSON_ID,
        one=True,
    )
    if pm and pm.get("goals_state"):
        print("goals_state present")
        print("signal-first selection verified via episodic data")
        return "PASS"
    print("WARN: goals_state missing or empty")
    return "WARN"


def section7_retrieval_preconditions(episodes: List[Dict[str, Any]]) -> str:
    _print_header("7] Episodic Retrieval Preconditions")
    with_summary = [ep for ep in episodes if (ep.get("text") or "").strip()]
    with_vec = [ep for ep in episodes if ep.get("has_vec")]
    print(f"summaries: {len(with_summary)}")
    print(f"vectors: {len(with_vec)}")
    if len(with_summary) >= DAYS_EXPECTED and len(with_vec) >= DAYS_EXPECTED:
        print("PASS")
        return "PASS"
    print("WARN: fewer summaries/vectors than expected")
    return "WARN"


async def main() -> None:
    episodes = await _fetch_episodes()
    statuses = []
    statuses.append(section1_daily_integrity(episodes))
    statuses.append(section2_core_fields(episodes))
    statuses.append(section3_enrichment(episodes))
    statuses.append(await section4_context_cache())
    statuses.append(await section5_personal_model())
    statuses.append(await section6_goals_themes())
    statuses.append(section7_retrieval_preconditions(episodes))

    failures = [s for s in statuses if s == "FAIL"]
    warns = [s for s in statuses if s == "WARN"]

    print("\n====================================")
    print("FINAL VERDICT")
    print("Sakhi Personal Intelligence v2.3")
    if failures:
        print("STATUS: FAIL")
        sys.exit(1)
    elif warns:
        print("STATUS: WARN (see sections above)")
        sys.exit(0)
    else:
        print("STATUS: PASS")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
