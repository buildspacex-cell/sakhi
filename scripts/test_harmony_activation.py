"""
Lightweight runner for harmony activation/triage tests.

Usage:
    poetry run python scripts/test_harmony_activation.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sakhi.apps.logic.harmony.orchestrator import triage_text, decide_activation


async def main() -> None:
    behavior = {"conversation_depth": "reflective", "planner_style": "structured"}
    triage = triage_text("Why do I feel tired and what should I plan next?", behavior)
    activation = decide_activation(triage, behavior)
    print("Triage:", triage)
    print("Activation:", activation)

    behavior2 = {"conversation_depth": "surface", "planner_style": "light-touch"}
    triage2 = triage_text("Let's plan something", behavior2)
    activation2 = decide_activation(triage2, behavior2)
    print("Triage2:", triage2)
    print("Activation2:", activation2)


if __name__ == "__main__":
    asyncio.run(main())
