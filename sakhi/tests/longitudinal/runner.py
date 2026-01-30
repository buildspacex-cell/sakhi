"""
Longitudinal Test Runner with Checkpointing

Provides:
- CLI interface for running simulations
- Checkpointing and resume capability
- Parallel persona execution
- Result reporting and visualization

Usage:
    # Run single persona simulation
    python -m sakhi.tests.longitudinal.runner --persona anxious_achiever --days 60

    # Run with checkpoint resume
    python -m sakhi.tests.longitudinal.runner --persona anxious_achiever --resume

    # Run all personas
    python -m sakhi.tests.longitudinal.runner --all --days 30

    # List available personas
    python -m sakhi.tests.longitudinal.runner --list
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[4]))

from dotenv import load_dotenv
load_dotenv()

from sakhi.tests.longitudinal.persona_spec import (
    PersonaSpec,
    load_persona,
    list_available_personas,
)
from sakhi.tests.longitudinal.simulation_harness import (
    SimulationHarness,
    SimulationResult,
)

LOGGER = logging.getLogger(__name__)

# Default checkpoint directory
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


class CheckpointManager:
    """Manages simulation checkpoints for resume capability."""

    def __init__(self, checkpoint_dir: Path = CHECKPOINT_DIR):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_checkpoint_path(self, persona_id: str) -> Path:
        """Get checkpoint file path for a persona."""
        return self.checkpoint_dir / f"{persona_id}_checkpoint.json"

    def save_checkpoint(
        self,
        persona_id: str,
        user_id: str,
        day: int,
        data: Dict[str, Any],
    ) -> None:
        """Save simulation checkpoint."""
        checkpoint = {
            "persona_id": persona_id,
            "user_id": user_id,
            "day": day,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        with open(self.get_checkpoint_path(persona_id), "w") as f:
            json.dump(checkpoint, f, indent=2)

    def load_checkpoint(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Load existing checkpoint if available."""
        path = self.get_checkpoint_path(persona_id)
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None

    def clear_checkpoint(self, persona_id: str) -> None:
        """Clear checkpoint file."""
        path = self.get_checkpoint_path(persona_id)
        if path.exists():
            path.unlink()


class TestRunner:
    """
    Main test runner for longitudinal simulations.

    Supports:
    - Single persona or all-persona runs
    - Checkpointing for long simulations
    - Result aggregation and reporting
    """

    def __init__(
        self,
        db_query,
        db_exec,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        self.db_query = db_query
        self.db_exec = db_exec
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.results: Dict[str, SimulationResult] = {}

    async def run_persona(
        self,
        persona_id: str,
        max_days: Optional[int] = None,
        resume: bool = False,
        cleanup: bool = False,
    ) -> SimulationResult:
        """
        Run simulation for a single persona.

        Args:
            persona_id: Persona ID to simulate
            max_days: Maximum simulation days
            resume: Whether to resume from checkpoint
            cleanup: Whether to clean up test data after

        Returns:
            SimulationResult
        """
        persona = load_persona(persona_id)
        total_days = max_days or persona.arc.total_days

        LOGGER.info(f"Running simulation for persona: {persona.name} ({persona_id})")
        LOGGER.info(f"Total days: {total_days}")

        # Check for checkpoint
        start_day = 1
        user_id = None
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint(persona_id)
            if checkpoint:
                start_day = checkpoint["day"] + 1
                user_id = checkpoint.get("user_id")
                LOGGER.info(f"Resuming from day {start_day} (user: {user_id})")

        # Create harness
        harness = SimulationHarness(
            persona=persona,
            db_query=self.db_query,
            db_exec=self.db_exec,
        )

        if user_id:
            harness.user_id = user_id
        else:
            await harness.setup()

        # Run simulation with checkpointing
        try:
            result = await self._run_with_checkpoints(
                harness=harness,
                persona_id=persona_id,
                start_day=start_day,
                total_days=total_days,
            )
            self.results[persona_id] = result

            # Clear checkpoint on successful completion
            self.checkpoint_manager.clear_checkpoint(persona_id)

            return result

        finally:
            if cleanup:
                await harness.cleanup()

    async def _run_with_checkpoints(
        self,
        harness: SimulationHarness,
        persona_id: str,
        start_day: int,
        total_days: int,
        checkpoint_interval: int = 7,
    ) -> SimulationResult:
        """Run simulation with periodic checkpointing."""
        harness.result = SimulationResult(
            persona_id=persona_id,
            user_id=harness.user_id,
            start_time=datetime.now(timezone.utc),
            total_days=total_days,
        )

        for day in range(start_day, total_days + 1):
            await harness._run_day(day)

            # Check for checkpoint assertions
            checkpoint = harness.persona.get_checkpoint_at_day(day)
            if checkpoint:
                await harness._run_checkpoint(checkpoint)

            # Periodic snapshots and checkpoint saves
            if day % checkpoint_interval == 0:
                snapshot = await harness._capture_snapshot(day)
                harness.result.snapshots.append(snapshot)

                # Save checkpoint
                self.checkpoint_manager.save_checkpoint(
                    persona_id=persona_id,
                    user_id=harness.user_id,
                    day=day,
                    data={
                        "total_entries": harness.result.total_entries,
                        "checkpoint_results": {
                            str(k): [r.message for r in v]
                            for k, v in harness.result.checkpoint_results.items()
                        },
                    },
                )

                LOGGER.info(f"[Checkpoint] Day {day}/{total_days} saved")

        harness.result.end_time = datetime.now(timezone.utc)
        return harness.result

    async def run_all(
        self,
        max_days: Optional[int] = None,
        parallel: bool = False,
        cleanup: bool = True,
    ) -> Dict[str, SimulationResult]:
        """
        Run simulations for all available personas.

        Args:
            max_days: Maximum days per persona
            parallel: Whether to run personas in parallel
            cleanup: Whether to clean up after each

        Returns:
            Dict of persona_id -> SimulationResult
        """
        persona_ids = list_available_personas()
        LOGGER.info(f"Running simulations for {len(persona_ids)} personas")

        if parallel:
            tasks = [
                self.run_persona(pid, max_days=max_days, cleanup=cleanup)
                for pid in persona_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for pid, result in zip(persona_ids, results):
                if isinstance(result, Exception):
                    LOGGER.error(f"Persona {pid} failed: {result}")
                else:
                    self.results[pid] = result
        else:
            for persona_id in persona_ids:
                try:
                    await self.run_persona(
                        persona_id,
                        max_days=max_days,
                        cleanup=cleanup,
                    )
                except Exception as exc:
                    LOGGER.error(f"Persona {persona_id} failed: {exc}")

        return self.results

    def print_report(self) -> None:
        """Print summary report of all simulation results."""
        print("\n" + "=" * 60)
        print("LONGITUDINAL SIMULATION REPORT")
        print("=" * 60)

        for persona_id, result in self.results.items():
            print(f"\n--- {persona_id} ---")
            print(f"  User ID: {result.user_id}")
            print(f"  Days: {result.total_days}")
            print(f"  Entries: {result.total_entries}")
            print(f"  Checkpoints: {len(result.checkpoint_results)}")

            # Checkpoint details
            for day, assertions in result.checkpoint_results.items():
                passed = sum(1 for a in assertions if a.passed)
                total = len(assertions)
                status = "PASS" if passed == total else "FAIL"
                print(f"    Day {day}: {status} ({passed}/{total})")

            print(f"  All Passed: {result.all_checkpoints_passed}")
            print(f"  Errors: {len(result.errors)}")

        print("\n" + "=" * 60)

        # Overall summary
        total_personas = len(self.results)
        passed_personas = sum(
            1 for r in self.results.values() if r.all_checkpoints_passed
        )
        print(f"OVERALL: {passed_personas}/{total_personas} personas passed all checkpoints")
        print("=" * 60 + "\n")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run longitudinal simulations for Sakhi"
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
        help="Maximum simulation days",
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from checkpoint",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available personas",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test data after simulation",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run personas in parallel (with --all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # List personas
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

    # Need either --persona or --all
    if not args.persona and not args.all:
        parser.error("Must specify --persona or --all")

    # Get database functions
    from sakhi.apps.api.core.db import q as db_query, exec as db_exec

    # Create runner
    runner = TestRunner(
        db_query=db_query,
        db_exec=db_exec,
    )

    try:
        if args.all:
            await runner.run_all(
                max_days=args.days,
                parallel=args.parallel,
                cleanup=args.cleanup,
            )
        else:
            await runner.run_persona(
                persona_id=args.persona,
                max_days=args.days,
                resume=args.resume,
                cleanup=args.cleanup,
            )

        runner.print_report()

        # Exit with error if any failed
        if not all(r.all_checkpoints_passed for r in runner.results.values()):
            sys.exit(1)

    except Exception as exc:
        LOGGER.error(f"Simulation failed: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())


__all__ = [
    "TestRunner",
    "CheckpointManager",
    "main",
]
