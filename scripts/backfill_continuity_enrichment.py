"""
Backfill continuity enrichment (labels, stance, loops) for existing journal entries.

Usage:
    python scripts/backfill_continuity_enrichment.py --person-id a1b2c3d4-1111-4000-8000-000000000001
    python scripts/backfill_continuity_enrichment.py --person-id all --limit 200
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure sakhi package is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(".env.local", override=True)
load_dotenv(".env", override=False)


async def run_backfill(person_id: str | None, limit: int, dry_run: bool) -> None:
    # Import continuity modules first — they load sakhi.libs.schemas through the
    # correct dependency order, resolving the schemas↔security circular import.
    from sakhi.apps.api.core.db import q
    from sakhi.apps.api.services.continuity.llm_enrichment import enrich_entry_continuity
    from sakhi.apps.api.services.continuity.stance import extract_and_store_stance
    from sakhi.apps.api.services.continuity.loops import run_loop_extraction

    # Configure the LLM router with OpenAI (same pattern as main.py).
    import sys
    _router_mod = sys.modules.get("sakhi.libs.llm_router.router")
    if _router_mod is None:
        from sakhi.libs.llm_router import router as _router_mod  # type: ignore[assignment]
    from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
    from sakhi.libs.llm_router.types import Task
    from sakhi.apps.api.core.llm import set_router

    llm_router = _router_mod.LLMRouter()
    openai_provider = make_openai_provider_from_env()
    if openai_provider:
        llm_router.register_provider("openai", openai_provider, daily_budget=None)
        llm_router.set_policy(Task.CHAT, ["openai"])
        llm_router.set_policy(Task.TOOL, ["openai"])
        print("LLM router: OpenAI configured.")
    else:
        raise RuntimeError("OPENAI_API_KEY not set — cannot run enrichment without LLM access.")
    set_router(llm_router)

    where_clause = "WHERE je.content IS NOT NULL AND je.content != ''"
    params: list = []
    if person_id and person_id != "all":
        where_clause += " AND je.person_id = $1"
        params.append(person_id)

    rows = await q(
        f"""
        SELECT je.id, je.person_id, je.content, je.created_at
        FROM journal_entries je
        LEFT JOIN continuity_labels cl ON cl.source_id = je.id::text AND cl.source_type = 'journal'
        {where_clause}
          AND cl.id IS NULL
        ORDER BY je.created_at ASC
        LIMIT {limit}
        """,
        *params,
    )

    if not rows:
        print("No unprocessed entries found.")
        return

    print(f"Found {len(rows)} entries to process.")
    decisions_total = 0
    commitments_total = 0
    stance_total = 0
    errors = 0

    for i, row in enumerate(rows):
        entry_id = str(row["id"])
        pid = str(row["person_id"])
        text = (row["content"] or "").strip()
        if not text:
            continue

        print(f"[{i+1}/{len(rows)}] entry={entry_id[:8]}... person={pid[:8]}... text={text[:60]!r}")

        if dry_run:
            continue

        enrichment_result: dict = {}
        try:
            enrichment_result = await enrich_entry_continuity(pid, entry_id, text, None)
            anchor = enrichment_result.get("inferred_anchor")
            print(f"  anchor={anchor}")
        except Exception as exc:
            print(f"  [ERROR] enrich_entry_continuity: {exc}")
            errors += 1
            anchor = None

        if anchor and anchor not in ("unknown", "", None):
            try:
                stance = await extract_and_store_stance(
                    person_id=pid,
                    topic_key=str(anchor),
                    text=text,
                    entry_id=entry_id,
                )
                if stance:
                    print(f"  stance={stance}")
                    stance_total += 1
            except Exception as exc:
                print(f"  [ERROR] extract_and_store_stance: {exc}")

        try:
            loop_result = await run_loop_extraction(
                person_id=pid,
                text=text,
                entry_id=entry_id,
                topic_key=str(anchor) if anchor and anchor not in ("unknown", "", None) else None,
                stance=enrichment_result.get("stance"),
            )
            d = loop_result.get("decisions_extracted", 0)
            c = loop_result.get("commitments_extracted", 0)
            r = len(loop_result.get("resolved", []))
            if d or c or r:
                print(f"  decisions={d} commitments={c} resolved={r}")
            decisions_total += d
            commitments_total += c
        except Exception as exc:
            print(f"  [ERROR] run_loop_extraction: {exc}")
            errors += 1

        # Small delay to avoid hammering the LLM
        await asyncio.sleep(0.3)

    print(f"\nDone. decisions={decisions_total} commitments={commitments_total} stances={stance_total} errors={errors}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill continuity enrichment for journal entries")
    parser.add_argument("--person-id", default="a1b2c3d4-1111-4000-8000-000000000001", help="Person UUID or 'all'")
    parser.add_argument("--limit", type=int, default=100, help="Max entries to process")
    parser.add_argument("--dry-run", action="store_true", help="Print entries but don't process")
    args = parser.parse_args()

    asyncio.run(run_backfill(args.person_id, args.limit, args.dry_run))


if __name__ == "__main__":
    main()
