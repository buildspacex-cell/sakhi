"""LLM judge for open loop extraction quality.

Given a conversation turn + extracted loops + ground truth, scores:
  precision  — are extracted items real decisions/commitments in the text?
  recall     — how many ground-truth items were actually extracted?
  resolution — was resolution detection correct?
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import asyncio
from sakhi.apps.api.core.llm import call_llm


_PRECISION_PROMPT = """\
You are evaluating whether an AI correctly identified open decisions or commitments in a conversation.

Conversation text:
{text}

Extracted items (type: {loop_type}):
{extracted}

For each extracted item, decide:
- "correct" if the item is a genuine open {loop_type} present in the text
- "wrong" if the item is NOT a real {loop_type}, is already resolved, is too vague, or was hallucinated

Return a JSON object:
{{
  "evaluations": [
    {{"item": "<item text>", "verdict": "correct" | "wrong", "reason": "<one sentence>"}}
  ]
}}

Return JSON only."""

_RECALL_PROMPT = """\
You are checking whether an AI missed any open decisions or commitments in a conversation.

Conversation text:
{text}

Ground truth {loop_type}s that should have been extracted:
{ground_truth}

Extracted {loop_type}s by the AI:
{extracted}

For each ground truth item, decide if the AI extracted it (exact match or semantically equivalent):
- "found" if extracted
- "missed" if not extracted

Return a JSON object:
{{
  "coverage": [
    {{"ground_truth_item": "<item>", "verdict": "found" | "missed", "reason": "<one sentence>"}}
  ]
}}

Return JSON only."""

_RESOLUTION_PROMPT = """\
You are evaluating whether an AI correctly detected which open loops were resolved in a follow-up message.

Follow-up message:
{text}

Open loops being tracked:
{open_loops}

AI said these were resolved: {ai_resolved}
Ground truth — these should be resolved: {gt_resolved}
Ground truth — these should NOT be resolved: {gt_not_resolved}

Evaluate:
1. False positives: items the AI marked resolved that shouldn't be
2. False negatives: items the AI missed resolving that should be

Return a JSON object:
{{
  "false_positives": ["<item id>"],
  "false_negatives": ["<item id>"],
  "correct_resolutions": ["<item id>"],
  "correct_non_resolutions": ["<item id>"]
}}

Return JSON only."""


def _parse_json(raw: str) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        return None


async def judge_precision(
    text: str,
    loop_type: str,
    extracted: list[str],
) -> dict[str, Any]:
    """Score whether extracted items are real. Returns precision metrics."""
    if not extracted:
        return {"precision": 1.0, "correct": 0, "wrong": 0, "evaluations": [], "note": "nothing_extracted"}

    extracted_block = "\n".join(f"- {item}" for item in extracted)
    raw = await call_llm(
        _PRECISION_PROMPT.format(text=text[:800], loop_type=loop_type, extracted=extracted_block),
        model="gpt-4o-mini",
    )
    parsed = _parse_json(raw)
    if not parsed:
        return {"precision": None, "error": "judge_parse_failed", "raw": raw}

    evals = parsed.get("evaluations") or []
    correct = sum(1 for e in evals if e.get("verdict") == "correct")
    wrong = sum(1 for e in evals if e.get("verdict") == "wrong")
    total = correct + wrong
    precision = correct / total if total > 0 else 1.0

    return {
        "precision": round(precision, 3),
        "correct": correct,
        "wrong": wrong,
        "evaluations": evals,
    }


async def judge_recall(
    text: str,
    loop_type: str,
    ground_truth: list[str],
    extracted: list[str],
) -> dict[str, Any]:
    """Score how many ground-truth items were found. Returns recall metrics."""
    if not ground_truth:
        return {"recall": 1.0, "found": 0, "missed": 0, "coverage": [], "note": "no_ground_truth"}

    gt_block = "\n".join(f"- {item}" for item in ground_truth)
    ext_block = "\n".join(f"- {item}" for item in extracted) if extracted else "(none extracted)"

    raw = await call_llm(
        _RECALL_PROMPT.format(text=text[:800], loop_type=loop_type, ground_truth=gt_block, extracted=ext_block),
        model="gpt-4o-mini",
    )
    parsed = _parse_json(raw)
    if not parsed:
        return {"recall": None, "error": "judge_parse_failed", "raw": raw}

    coverage = parsed.get("coverage") or []
    found = sum(1 for c in coverage if c.get("verdict") == "found")
    missed = sum(1 for c in coverage if c.get("verdict") == "missed")
    total = found + missed
    recall = found / total if total > 0 else 1.0

    return {
        "recall": round(recall, 3),
        "found": found,
        "missed": missed,
        "coverage": coverage,
    }


async def judge_resolution(
    resolution_text: str,
    open_loops: list[dict],
    ai_resolved_ids: list[str],
    gt_resolved_ids: list[str],
    gt_not_resolved_ids: list[str],
) -> dict[str, Any]:
    """Score resolution detection accuracy."""
    loops_block = "\n".join(f"- [{l['id']}] ({l['loop_type']}) {l['topic']}" for l in open_loops)
    raw = await call_llm(
        _RESOLUTION_PROMPT.format(
            text=resolution_text[:800],
            open_loops=loops_block,
            ai_resolved=json.dumps(ai_resolved_ids),
            gt_resolved=json.dumps(gt_resolved_ids),
            gt_not_resolved=json.dumps(gt_not_resolved_ids),
        ),
        model="gpt-4o-mini",
    )
    parsed = _parse_json(raw)
    if not parsed:
        return {"accuracy": None, "error": "judge_parse_failed", "raw": raw}

    fp = len(parsed.get("false_positives") or [])
    fn = len(parsed.get("false_negatives") or [])
    correct = len(parsed.get("correct_resolutions") or []) + len(parsed.get("correct_non_resolutions") or [])
    total = fp + fn + correct
    accuracy = correct / total if total > 0 else 1.0

    return {
        "accuracy": round(accuracy, 3),
        "false_positives": parsed.get("false_positives") or [],
        "false_negatives": parsed.get("false_negatives") or [],
        "correct_count": correct,
        "total": total,
    }
