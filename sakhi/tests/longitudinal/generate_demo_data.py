"""
Demo Data Generator for Longitudinal Simulation Visualization

Generates realistic pre-baked simulation data from persona specs
WITHOUT requiring a database or LLM. Deterministically derives:
- Daily dosha values from phase dosha_shift
- Friction states from computed drift
- Memory/pattern counts growing over time
- Journal entries from fallback templates
- Checkpoint assertion results

Output: JSON files in apps/web/public/simulation/

Usage:
    python -m sakhi.tests.longitudinal.generate_demo_data
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parents[4]))

from sakhi.tests.longitudinal.persona_spec import (
    PersonaSpec,
    ArcPhase,
    load_persona,
    list_available_personas,
)
from sakhi.tests.longitudinal.entry_generator import (
    _generate_fallback_entry,
    get_entry_timestamp,
)

# Friction state classification (mirrors vikriti.py logic)
DRIFT_THRESHOLDS = {"mild": 15, "moderate": 25, "significant": 40}


def _classify_severity(drift_pct: float) -> str:
    if drift_pct < DRIFT_THRESHOLDS["mild"]:
        return "minimal"
    elif drift_pct < DRIFT_THRESHOLDS["moderate"]:
        return "mild"
    elif drift_pct < DRIFT_THRESHOLDS["significant"]:
        return "moderate"
    return "significant"


def _compute_drift(baseline: Dict[str, float], current: Dict[str, float]) -> Dict[str, Any]:
    """Compute drift between baseline and current dosha state."""
    distances = {
        k: round(current.get(k, 0.33) - baseline.get(k, 0.33), 4)
        for k in ("vata", "pitta", "kapha")
    }
    euclidean = math.sqrt(sum(d ** 2 for d in distances.values()))
    drift_pct = round(min(100, euclidean * 87), 1)

    abs_d = {k: abs(v) for k, v in distances.items()}
    primary = max(abs_d, key=abs_d.get)
    direction = "elevated" if distances[primary] > 0 else "depleted"

    return {
        "drift_percentage": drift_pct,
        "primary_contributor": primary,
        "direction": direction,
        "raw_distances": distances,
        "severity": _classify_severity(drift_pct),
    }


def _classify_friction(drift: Dict[str, Any]) -> Dict[str, Any]:
    """Map drift to friction state."""
    drift_pct = drift["drift_percentage"]
    primary = drift["primary_contributor"]
    direction = drift["direction"]

    if drift_pct < DRIFT_THRESHOLDS["mild"]:
        return {
            "state": "balanced",
            "name": "Balanced Flow",
            "short": "Aligned, sustainable, flowing",
            "dosha": None,
            "drift_percentage": drift_pct,
            "severity": "minimal",
        }

    # If depleted, find what's elevated instead
    if direction != "elevated":
        raw = drift.get("raw_distances", {})
        elevated = {k: v for k, v in raw.items() if v > 0}
        if elevated:
            primary = max(elevated, key=elevated.get)

    dosha_to_friction = {"vata": "chaos", "pitta": "intensity", "kapha": "stagnation"}
    friction_key = dosha_to_friction.get(primary, "chaos")

    names = {
        "chaos": ("Chaos Friction", "Scattered, anxious, overwhelmed"),
        "intensity": ("Intensity Friction", "Driven, irritable, burning out"),
        "stagnation": ("Stagnation Friction", "Stuck, sluggish, unmotivated"),
    }
    name, short = names[friction_key]

    return {
        "state": friction_key,
        "name": name,
        "short": short,
        "dosha": primary,
        "drift_percentage": drift_pct,
        "severity": drift.get("severity", "mild"),
    }


def _infer_constitution_type(baseline: Dict[str, float]) -> str:
    v, p, k = baseline.get("vata", 0.33), baseline.get("pitta", 0.33), baseline.get("kapha", 0.34)
    if max(v, p, k) < 0.4:
        return "Balanced"
    elif p >= v and p >= k:
        return "Driven"
    elif v >= p and v >= k:
        return "Quick-moving"
    return "Steady"


def _smooth_transition(
    prev: Dict[str, float],
    target: Dict[str, float],
    progress: float,
    noise: float = 0.02,
) -> Dict[str, float]:
    """Smoothly transition between two dosha profiles with noise."""
    result = {}
    for k in ("vata", "pitta", "kapha"):
        base = prev.get(k, 0.33) + (target.get(k, 0.33) - prev.get(k, 0.33)) * progress
        jitter = random.uniform(-noise, noise)
        result[k] = max(0.05, base + jitter)

    # Normalize to sum to 1.0
    total = sum(result.values())
    result = {k: round(v / total, 4) for k, v in result.items()}
    adj = 1.0 - sum(result.values())
    result["kapha"] = round(result["kapha"] + adj, 4)

    return result


def generate_demo_data(persona: PersonaSpec) -> Dict[str, Any]:
    """
    Generate complete demo simulation data for a persona.

    Returns a dict matching the SimulationData TypeScript interface.
    """
    random.seed(hash(persona.id))  # Deterministic per persona

    total_days = persona.arc.total_days
    baseline = persona.dosha_baseline.model_dump()
    sim_start = datetime(2025, 9, 1, tzinfo=timezone.utc)

    # Generate day-by-day data
    entries: List[Dict[str, Any]] = []
    snapshots: List[Dict[str, Any]] = []

    # Track running state
    memory_count = 0
    pattern_count = 0
    prev_dosha = dict(baseline)
    confidence = 0.2

    for day in range(1, total_days + 1):
        phase = persona.arc.get_phase_at_day(day)
        if not phase:
            continue

        # Compute phase progress (0.0 to 1.0 within current phase)
        cumulative = 0
        phase_start_day = 1
        for p in persona.arc.phases:
            if p.name == phase.name:
                phase_start_day = cumulative + 1
                break
            cumulative += p.duration_days
        phase_progress = (day - phase_start_day) / max(phase.duration_days, 1)

        # Target dosha for this phase
        target_dosha = (
            phase.dosha_shift.model_dump() if phase.dosha_shift else baseline
        )

        # Use stronger smoothing factor so transitions are visible within a phase
        # Early in phase: fast transition (0.25); mid-phase: settled (0.1)
        smooth_factor = 0.25 if phase_progress < 0.3 else 0.12
        current_dosha = _smooth_transition(prev_dosha, target_dosha, smooth_factor, noise=0.012)
        prev_dosha = current_dosha

        # Confidence grows with entries
        confidence = min(0.92, 0.2 + memory_count * 0.012)

        # Compute drift and friction
        drift = _compute_drift(baseline, current_dosha)
        friction = _classify_friction(drift)

        # Generate entries for this day
        expected_entries = phase.entry_frequency
        num_entries = int(expected_entries)
        if random.random() < (expected_entries - num_entries):
            num_entries += 1
        if num_entries == 0 and random.random() < 0.3:
            num_entries = 1

        day_entries = []
        available_times = list(persona.entry_times)
        for _ in range(min(num_entries, len(available_times))):
            time_of_day = random.choice(available_times)
            available_times.remove(time_of_day)

            entry_text = _generate_fallback_entry(
                persona=persona,
                day=day,
                phase=phase.model_dump(),
                time_of_day=time_of_day,
            )

            ts = get_entry_timestamp(sim_start, day, time_of_day)
            day_entries.append({
                "day": day,
                "time_of_day": time_of_day,
                "content": entry_text,
                "timestamp": ts.isoformat(),
            })

            memory_count += 1

        entries.extend(day_entries)

        # Pattern count grows as memories accumulate (step function)
        if memory_count > 5 and day % 3 == 0:
            pattern_count += random.randint(0, 2)

        # Create daily snapshot
        snapshots.append({
            "day": day,
            "timestamp": (sim_start + timedelta(days=day - 1, hours=23)).isoformat(),
            "personal_model": {
                "operating_system": _infer_constitution_type(baseline),
                "dosha_baseline": baseline,
            },
            "memory_count": memory_count,
            "pattern_count": pattern_count,
            "friction_state": {
                "operating_system": _infer_constitution_type(baseline),
                "baseline": {"dosha_baseline": baseline},
                "current_state": {
                    "current_dosha": current_dosha,
                    "confidence": round(confidence, 2),
                    "episode_count": memory_count,
                },
                "drift": drift,
                "friction": friction,
            },
            "recent_memories": [
                {"content": e["content"], "created_at": e["timestamp"]}
                for e in day_entries[-3:]
            ],
        })

    # Generate checkpoint results
    checkpoint_results: Dict[str, List[Dict[str, Any]]] = {}
    for cp in persona.checkpoints:
        results = []
        # Find the snapshot closest to this checkpoint day
        cp_snapshot = None
        for s in snapshots:
            if s["day"] <= cp.day:
                cp_snapshot = s
            else:
                break

        for assert_type, config in cp.assertions.items():
            passed = _evaluate_checkpoint_assertion(
                assert_type, config, cp_snapshot, cp.day, total_days
            )
            results.append({
                "passed": passed,
                "type": assert_type,
                "message": _format_assertion_message(
                    assert_type, config, cp_snapshot, passed
                ),
            })

        checkpoint_results[str(cp.day)] = results

    # Build persona data for frontend
    persona_data = {
        "id": persona.id,
        "name": persona.name,
        "description": persona.description,
        "dosha_baseline": baseline,
        "rhythm": persona.rhythm.model_dump(),
        "traits": [t.model_dump() for t in persona.traits],
        "life_context": persona.life_context.model_dump(),
        "arc": {
            "name": persona.arc.name,
            "description": persona.arc.description,
            "phases": [p.model_dump() for p in persona.arc.phases],
        },
        "writing_style": persona.writing_style,
        "typical_entry_length": persona.typical_entry_length,
        "checkpoints": [
            {"day": cp.day, "name": cp.name, "assertions": cp.assertions}
            for cp in persona.checkpoints
        ],
    }

    return {
        "persona_id": persona.id,
        "persona": persona_data,
        "user_id": f"sim-{persona.id}-demo",
        "start_time": sim_start.isoformat(),
        "end_time": (sim_start + timedelta(days=total_days)).isoformat(),
        "total_days": total_days,
        "total_entries": len(entries),
        "all_checkpoints_passed": all(
            all(r["passed"] for r in results)
            for results in checkpoint_results.values()
        ),
        "snapshots": snapshots,
        "checkpoint_results": checkpoint_results,
        "entries": entries,
        "errors": [],
    }


def _evaluate_checkpoint_assertion(
    assert_type: str,
    config: Dict[str, Any],
    snapshot: Optional[Dict[str, Any]],
    day: int,
    total_days: int,
) -> bool:
    """Deterministically evaluate whether a checkpoint assertion passes."""
    if not snapshot:
        return False

    friction = snapshot.get("friction_state", {}).get("friction", {})
    drift = snapshot.get("friction_state", {}).get("drift", {})
    current_dosha = snapshot.get("friction_state", {}).get("current_state", {}).get("current_dosha", {})

    if assert_type == "friction_state":
        current_state = friction.get("state", "balanced")
        expected = config.get("expected")
        expected_in = config.get("expected_in", [])
        if expected:
            return current_state == expected
        if expected_in:
            return current_state in expected_in
        return True

    elif assert_type == "pattern_crystallized":
        # Patterns need enough time and entries
        count = snapshot.get("pattern_count", 0)
        return count >= config.get("min_occurrences", 3)

    elif assert_type == "theme_emerged":
        count = snapshot.get("memory_count", 0)
        return count >= config.get("min_occurrences", 3)

    elif assert_type == "rhythm_learned":
        # Rhythm is learned after enough data
        return snapshot.get("memory_count", 0) > 10

    elif assert_type == "dosha_drift":
        target_dosha = config.get("dosha", "vata")
        direction = config.get("direction", "elevated")
        min_pct = config.get("min_percentage", 15)

        raw = drift.get("raw_distances", {})
        dosha_drift = raw.get(target_dosha, 0) * 100
        direction_ok = (direction == "elevated" and dosha_drift > 0) or \
                       (direction == "depleted" and dosha_drift < 0)
        return direction_ok and abs(dosha_drift) >= min_pct

    elif assert_type == "dosha_state":
        primary = config.get("primary", "pitta")
        min_pct = config.get("min_percentage", 33)
        val = current_dosha.get(primary, 0) * 100
        return val >= min_pct

    elif assert_type == "rhythm_shift":
        return True  # Soft assertion

    return False


def _format_assertion_message(
    assert_type: str,
    config: Dict[str, Any],
    snapshot: Optional[Dict[str, Any]],
    passed: bool,
) -> str:
    """Format human-readable assertion result message."""
    if not snapshot:
        return f"{assert_type}: No data available"

    friction = snapshot.get("friction_state", {}).get("friction", {})
    drift = snapshot.get("friction_state", {}).get("drift", {})
    current_state = snapshot.get("friction_state", {}).get("current_state", {})
    confidence = current_state.get("confidence", 0)

    if assert_type == "friction_state":
        state = friction.get("state", "unknown")
        expected = config.get("expected") or config.get("expected_in", [])
        status = "PASS" if passed else "FAIL"
        return f"Friction state: {state} (confidence: {confidence:.2f}) [{status}]"

    elif assert_type == "pattern_crystallized":
        count = snapshot.get("pattern_count", 0)
        val = config.get("value", "?")
        return f"Pattern '{config.get('type', '?')}:{val}' — {count} occurrences {'(sufficient)' if passed else '(insufficient)'}"

    elif assert_type == "theme_emerged":
        keywords = config.get("keywords", [])
        count = snapshot.get("memory_count", 0)
        return f"Theme keywords {keywords} — {count} memories {'(sufficient)' if passed else '(insufficient)'}"

    elif assert_type == "rhythm_learned":
        slot = config.get("slot", "?")
        expected = config.get("expected", "?")
        return f"Rhythm slot '{slot}' = {expected} {'(learned)' if passed else '(not yet)'}"

    elif assert_type == "dosha_drift":
        dosha = config.get("dosha", "?")
        pct = drift.get("drift_percentage", 0)
        return f"Dosha {dosha} drift: {pct:.1f}% {'(sufficient)' if passed else '(insufficient)'}"

    elif assert_type == "dosha_state":
        primary = config.get("primary", "?")
        val = current_state.get("current_dosha", {}).get(primary, 0) * 100
        return f"Dosha {primary} at {val:.1f}% {'(sufficient)' if passed else '(insufficient)'}"

    return f"{assert_type}: {'PASS' if passed else 'FAIL'}"


def main():
    """Generate demo data for all personas."""
    # Navigate from sakhi/tests/longitudinal/ up to project root, then into apps/web
    project_root = Path(__file__).resolve().parents[3]  # sakhi/ -> Sakhi/
    output_dir = project_root / "apps" / "web" / "public" / "simulation"
    output_dir.mkdir(parents=True, exist_ok=True)

    personas = list_available_personas()
    print(f"Generating demo data for {len(personas)} personas...")
    print(f"Output directory: {output_dir}")

    for persona_id in personas:
        print(f"\n--- {persona_id} ---")
        persona = load_persona(persona_id)
        print(f"  Name: {persona.name}")
        print(f"  Arc: {persona.arc.name} ({persona.arc.total_days} days)")

        data = generate_demo_data(persona)

        out_path = output_dir / f"{persona_id}.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        size_kb = out_path.stat().st_size / 1024
        print(f"  Entries: {data['total_entries']}")
        print(f"  Snapshots: {len(data['snapshots'])}")
        print(f"  Checkpoints: {len(data['checkpoint_results'])}")
        print(f"  All passed: {data['all_checkpoints_passed']}")
        print(f"  File: {out_path} ({size_kb:.1f} KB)")

    print(f"\nDone! Files written to {output_dir}")


if __name__ == "__main__":
    main()
