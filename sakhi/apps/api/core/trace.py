from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

EXPLAIN_DEFAULT = {
    "extract": "Parsed the message to find intent, time, and emotional tone.",
    "metrics": "Quantified novelty, emotional intensity, and coherence for salience/vividness.",
    "observe.write": "Saved the moment as an episode in long-term memory (hub).",
    "hcb.base": "Built base context: goals, preferences/values, timeline.",
    "hcb.fetch.time": "Fetched time slack and busy blocks.",
    "hcb.fetch.energy": "Fetched chronotype/energy signals for timing fit.",
    "hcb.fetch.finance": "Fetched liquidity/budgets to assess money feasibility.",
    "hcb.fetch.values": "Fetched value alignment and guardrails.",
    "anchors.score": "Merged features into the six clarity anchors (intent, commitment, resources, coherence, risk, rhythm).",
    "options": "Generated A/B/C plan candidates with guardrails applied.",
    "llm.prompt": "Constructed the LLM prompt with the context pack and options.",
}


class Trace:
    def __init__(self, person_id: str, flow: str) -> None:
        self.trace_id = str(uuid.uuid4())
        self.person_id = person_id
        self.flow = flow
        self._start = time.time()
        self.steps: List[Dict[str, Any]] = []

    def add(
        self,
        stage: str,
        label: str,
        data: Optional[Dict[str, Any]] = None,
        decision: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> None:
        self.steps.append(
            {
                "t": round(time.time() - self._start, 3),
                "stage": stage,
                "label": label,
                "data": data or {},
                "decision": decision,
                "explanation": explanation or EXPLAIN_DEFAULT.get(stage),
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "flow": self.flow,
            "steps": self.steps,
        }
