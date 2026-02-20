"""
Export Real Simulation Data for Demo (v2 — Full Brain)

Runs the longitudinal simulation harness with ALL production worker pipelines
against a live database, then exports results as JSON for the web demo page.

This produces genuinely processed data using the SAME code as production:
- Real LLM-generated journal entries
- Real memory ingestion (STM, embeddings, personal model)
- Real episodic consolidation (soul signals, patterns, memory graph)
- Real friction state computation (ayurvedic pipeline)
- Real brain state computation (emotion, soul, rhythm, coherence, alignment, etc.)
- Real conversation demo (personalized responses from the full brain)

Usage:
    # Run a single persona and export
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever

    # Run with limited days for quick testing
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever --days 10

    # Run all personas
    python -m sakhi.tests.longitudinal.export_real_simulation --all

    # Keep test data in DB for live demo (default: cleanup)
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever --no-cleanup

    # Control daily worker frequency (default: every 3 simulated days)
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever --daily-interval 5

    # Custom demo questions for conversation demo
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever --demo-questions "How am I doing?" "What should I prioritize?"

    # Production parity mode: route entries through /v2/turn (exact production code path)
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever --parity --days 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[4]))

from dotenv import load_dotenv
load_dotenv()

from sakhi.tests.longitudinal.persona_spec import (
    load_persona,
    list_available_personas,
)
from sakhi.tests.longitudinal.simulation_harness import (
    SimulationHarness,
    SimulationResult,
)

LOGGER = logging.getLogger(__name__)


def _init_llm_router() -> None:
    """
    Initialize the global LLM router for simulation runs.

    Replicates the router setup from FastAPI lifespan so that workers
    and conversation demo can call call_llm() outside the web server.
    """
    import os
    from sakhi.libs.llm_router import BaseProvider, LLMResponse, LLMRouter, Task
    from sakhi.apps.api.core.llm import set_router

    router = LLMRouter()

    # Stub fallback
    class _Stub(BaseProvider):
        def __init__(self):
            super().__init__(name="stub")

        async def chat(self, *, messages, model, tools=None, **kw) -> LLMResponse:
            last = messages[-1] if messages else {"role": "assistant", "content": ""}
            return LLMResponse(model=model, task=Task.CHAT, text=last.get("content", ""))

    router.register_provider("stub", _Stub())
    chat_providers: list[str] = []
    tool_providers: list[str] = []

    # OpenAI direct
    try:
        from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
        openai_prov = make_openai_provider_from_env()
        if openai_prov:
            router.register_provider("openai", openai_prov, daily_budget=None)
            chat_providers.append("openai")
            tool_providers.append("openai")
    except Exception as exc:
        LOGGER.warning("OpenAI provider init failed: %s", exc)

    chat_providers.append("stub")
    tool_providers.append("stub")
    router.set_policy(Task.CHAT, chat_providers)
    router.set_policy(Task.TOOL, tool_providers)

    set_router(router)
    LOGGER.info(
        "LLM router initialized for simulation (providers: %s)",
        list(router._providers.keys()),
    )


# Output directory for demo JSON files
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "apps" / "web" / "public" / "simulation"


async def run_and_export(
    persona_id: str,
    max_days: int | None = None,
    snapshot_interval: int = 1,  # Daily snapshots for rich demo data
    daily_worker_interval: int = 3,  # Run daily workers every N days
    cleanup: bool = True,
    output_dir: Path = OUTPUT_DIR,
    production_parity: bool = False,  # Route through /v2/turn
) -> Path:
    """
    Run a real simulation and export to JSON.

    Args:
        persona_id: Which persona to simulate
        max_days: Override total days (None = use persona's arc length)
        snapshot_interval: How often to capture state snapshots (days)
        daily_worker_interval: Run daily workers every N simulated days
        cleanup: Whether to delete test data from DB after export
        output_dir: Where to write the JSON file
        production_parity: If True, route entries through /v2/turn endpoint

    Returns:
        Path to the exported JSON file
    """
    from sakhi.apps.api.core.db import q as db_query, exec as db_exec

    persona = load_persona(persona_id)
    total_days = max_days or persona.arc.total_days

    mode_label = "PRODUCTION PARITY" if production_parity else "REAL WORKERS"
    LOGGER.info(f"Starting simulation [{mode_label}]: {persona.name} ({persona_id}), {total_days} days")

    harness = SimulationHarness(
        persona=persona,
        db_query=db_query,
        db_exec=db_exec,
        snapshot_interval=snapshot_interval,
        run_workers=True,
        daily_worker_interval=daily_worker_interval,
        production_parity=production_parity,
    )

    try:
        await harness.setup()
        LOGGER.info(f"Test user created: {harness.user_id}")

        result = await harness.run(max_days=max_days)

        # Export to JSON
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{persona_id}.json"

        export_data = result.to_dict(include_persona=True)
        export_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        export_data["real_pipeline"] = True  # Flag that this used real workers
        export_data["production_parity"] = production_parity  # True if routed through /v2/turn

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        size_kb = output_path.stat().st_size / 1024
        LOGGER.info(
            f"Exported: {output_path} ({size_kb:.0f} KB, "
            f"{result.total_entries} entries, "
            f"{len(result.snapshots)} snapshots)"
        )

        # Print summary
        print(f"\n{'='*60}")
        print(f"SIMULATION COMPLETE: {persona.name}")
        print(f"{'='*60}")
        print(f"  Days:       {result.total_days}")
        print(f"  Entries:    {result.total_entries}")
        print(f"  Snapshots:  {len(result.snapshots)}")
        print(f"  Checkpoints: {len(result.checkpoint_results)}")
        for day, assertions in result.checkpoint_results.items():
            passed = sum(1 for a in assertions if a.passed)
            total = len(assertions)
            status = "PASS" if passed == total else "FAIL"
            print(f"    Day {day}: {status} ({passed}/{total})")
        print(f"  All passed: {result.all_checkpoints_passed}")
        print(f"  Errors:     {len(result.errors)}")

        # Brain state summary from final snapshot
        if result.snapshots:
            final = result.snapshots[-1]
            brain = getattr(final, "_brain_states", {}) if hasattr(final, "_brain_states") else {}
            if not brain:
                # Check serialized form
                final_dict = export_data.get("snapshots", [{}])[-1] if export_data.get("snapshots") else {}
                brain = final_dict.get("brain_states", {})
            populated = [k for k, v in brain.items() if v and v != {}]
            print(f"  Brain states populated: {len(populated)}/{9} ({', '.join(populated) or 'none'})")

        # Conversation demo summary
        demo = getattr(result, "_conversation_demo", [])
        if demo:
            print(f"  Conversation demo: {len(demo)} Q&A pairs")
            for qa in demo:
                resp_preview = qa.get("response", "")[:80]
                print(f"    Q: {qa['question'][:60]}")
                print(f"    A: {resp_preview}...")

        print(f"  Output:     {output_path}")
        print(f"{'='*60}\n")

        return output_path

    finally:
        if cleanup:
            LOGGER.info("Cleaning up test data from database...")
            await harness.cleanup()
        else:
            LOGGER.info(f"Keeping test data in DB (user_id: {harness.user_id})")


async def main():
    parser = argparse.ArgumentParser(
        description="Run real longitudinal simulation and export for demo"
    )
    parser.add_argument(
        "--persona", "-p",
        help="Persona ID to simulate",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all available personas",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        help="Override simulation days (default: persona's arc length)",
    )
    parser.add_argument(
        "--snapshot-interval", "-s",
        type=int,
        default=1,
        help="Days between state snapshots (default: 1 for demo richness)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep test data in the database after export (for live demo)",
    )
    parser.add_argument(
        "--daily-interval",
        type=int,
        default=3,
        help="Run daily workers every N simulated days (default: 3)",
    )
    parser.add_argument(
        "--demo-questions",
        nargs="+",
        help="Custom demo questions for conversation demo",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available personas",
    )
    parser.add_argument(
        "--parity",
        action="store_true",
        help="Production parity mode: route entries through /v2/turn endpoint "
             "(same code path as production, not direct DB inserts)",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize LLM router so workers + conversation demo can call call_llm()
    # In parity mode, the FastAPI lifespan handles this instead.
    if not args.parity:
        _init_llm_router()

    if args.list:
        personas = list_available_personas()
        print("\nAvailable personas:")
        for pid in personas:
            try:
                p = load_persona(pid)
                print(f"  - {pid}: {p.name} ({p.arc.total_days} days)")
            except Exception as exc:
                print(f"  - {pid}: (error loading: {exc})")
        return

    if not args.persona and not args.all:
        parser.error("Must specify --persona or --all (or --list to see options)")

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    persona_ids = (
        list_available_personas() if args.all
        else [args.persona]
    )

    for pid in persona_ids:
        try:
            await run_and_export(
                persona_id=pid,
                max_days=args.days,
                snapshot_interval=args.snapshot_interval,
                daily_worker_interval=args.daily_interval,
                cleanup=not args.no_cleanup,
                output_dir=output_dir,
                production_parity=args.parity,
            )
        except Exception as exc:
            LOGGER.error(f"Failed to export {pid}: {exc}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
    # Force exit — background asyncio tasks (soul_extract_worker etc.)
    # can hold DB pool connections that prevent clean shutdown.
    import sys
    sys.exit(0)


__all__ = ["run_and_export"]
