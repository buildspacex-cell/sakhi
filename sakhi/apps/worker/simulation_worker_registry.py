"""Shared simulation worker registry aligned to production scheduler cadence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class SimulationWorkerSpec:
    """Worker definition used by simulation pipelines."""

    name: str
    module_path: str
    function_name: str
    production_frequency: str
    production_source: str
    parity_note: str = ""


SIMULATION_DAILY_WORKER_SPECS: tuple[SimulationWorkerSpec, ...] = (
    SimulationWorkerSpec(
        name="daily_reflection",
        module_path="sakhi.apps.worker.tasks.daily_reflection_worker",
        function_name="run_daily_reflection",
        production_frequency="daily (scheduler reflection cycle)",
        production_source="schedule_reflection_jobs",
    ),
    SimulationWorkerSpec(
        name="ayurvedic_pipeline",
        module_path="sakhi.apps.worker.tasks.ayurvedic_pipeline",
        function_name="run_ayurvedic_pipeline",
        production_frequency="daily at AYURVEDIC_PIPELINE_HOUR",
        production_source="schedule_ayurvedic_pipeline_daily",
    ),
    SimulationWorkerSpec(
        name="esr",
        module_path="sakhi.apps.worker.tasks.esr_worker",
        function_name="run_emotion_state_refresh",
        production_frequency="daily at ESR_DAILY_HOUR",
        production_source="schedule_esr_daily",
    ),
    SimulationWorkerSpec(
        name="soul_refresh",
        module_path="sakhi.apps.worker.tasks.soul_refresh_worker",
        function_name="soul_refresh_worker",
        production_frequency="daily at SOUL_REFRESH_HOUR",
        production_source="schedule_soul_refresh_daily",
    ),
    SimulationWorkerSpec(
        name="identity_momentum",
        module_path="sakhi.apps.worker.identity_momentum_deep",
        function_name="run_identity_momentum_deep",
        production_frequency="daily at IDENTITY_MOMENTUM_HOUR",
        production_source="schedule_identity_momentum_daily",
    ),
    SimulationWorkerSpec(
        name="emotion_soul_rhythm",
        module_path="sakhi.apps.worker.tasks.emotion_soul_rhythm_deep",
        function_name="run_emotion_soul_rhythm_deep",
        production_frequency="daily at EMOTION_SOUL_RHYTHM_HOUR",
        production_source="schedule_emotion_soul_rhythm_daily",
    ),
    SimulationWorkerSpec(
        name="rhythm_soul",
        module_path="sakhi.apps.worker.rhythm_soul_deep",
        function_name="run_rhythm_soul_deep",
        production_frequency=(
            "daily at RHYTHM_SOUL_DAILY_HOUR + weekly at RHYTHM_SOUL_WEEKLY_HOUR"
        ),
        production_source="schedule_rhythm_soul_daily + schedule_rhythm_soul_weekly",
        parity_note="Simulation runs the daily pass only.",
    ),
    SimulationWorkerSpec(
        name="alignment_refresh",
        module_path="sakhi.apps.worker.tasks.alignment_refresh",
        function_name="run_alignment_refresh",
        production_frequency="daily at ALIGNMENT_REFRESH_HOUR",
        production_source="schedule_alignment_refresh_daily",
    ),
    SimulationWorkerSpec(
        name="coherence_refresh",
        module_path="sakhi.apps.worker.tasks.coherence_refresh",
        function_name="run_coherence_refresh",
        production_frequency="daily at COHERENCE_REFRESH_HOUR",
        production_source="schedule_coherence_refresh_daily",
    ),
    SimulationWorkerSpec(
        name="crystallization",
        module_path="sakhi.apps.worker.tasks.pattern_crystallization_worker",
        function_name="run_daily_crystallization",
        production_frequency=(
            "daily at CRYSTALLIZATION_DAILY_HOUR "
            "(plus weekly/monthly via separate workers)"
        ),
        production_source="schedule_crystallization_daily",
        parity_note="Simulation runs daily crystallization only.",
    ),
    SimulationWorkerSpec(
        name="theme_uprank",
        module_path="sakhi.apps.worker.tasks.theme_inference",
        function_name="run_theme_inference_incremental",
        production_frequency="daily at THEME_UPRANK_HOUR",
        production_source="schedule_theme_uprank_daily",
    ),
    SimulationWorkerSpec(
        name="intent_decay",
        module_path="sakhi.apps.worker.tasks.intent_evolution_decay",
        function_name="intent_evolution_decay",
        production_frequency="daily at INTENT_DECAY_HOUR",
        production_source="schedule_intent_decay_daily",
    ),
    SimulationWorkerSpec(
        name="emotion_loop",
        module_path="sakhi.apps.worker.tasks.emotion_loop_refresh",
        function_name="emotion_loop_refresh",
        production_frequency="daily at EMOTION_LOOP_HOUR",
        production_source="schedule_emotion_loop_daily",
    ),
    SimulationWorkerSpec(
        name="task_weaver",
        module_path="sakhi.apps.worker.tasks.task_weaver_refresh",
        function_name="task_weaver_refresh",
        production_frequency="daily at TASK_WEAVER_HOUR",
        production_source="schedule_task_weaver_daily",
    ),
    SimulationWorkerSpec(
        name="forecast",
        module_path="sakhi.apps.worker.tasks.forecast",
        function_name="run_forecast",
        production_frequency="daily at FORECAST_HOUR + every FORECAST_INTERVAL_HOURS",
        production_source="schedule_forecast_jobs",
        parity_note="Simulation runs one forecast pass when daily workers run.",
    ),
)


SIMULATION_WEEKLY_WORKER_SPECS: tuple[SimulationWorkerSpec, ...] = (
    SimulationWorkerSpec(
        name="theme_full",
        module_path="sakhi.apps.worker.tasks.theme_inference",
        function_name="run_theme_inference",
        production_frequency="weekly on THEME_INFERENCE_DAYS",
        production_source="schedule_theme_inference_jobs",
    ),
    SimulationWorkerSpec(
        name="rhythm_soul_weekly",
        module_path="sakhi.apps.worker.rhythm_soul_deep",
        function_name="run_rhythm_soul_deep",
        production_frequency="weekly on RHYTHM_SOUL_WEEKLY_DAYS at RHYTHM_SOUL_WEEKLY_HOUR",
        production_source="schedule_rhythm_soul_weekly",
    ),
    SimulationWorkerSpec(
        name="weekly_learning",
        module_path="sakhi.apps.worker.tasks.weekly_learning_worker",
        function_name="run_weekly_learning",
        production_frequency="weekly on LEARNING_WEEKLY_DAYS at LEARNING_WEEKLY_HOUR",
        production_source="schedule_weekly_learning",
    ),
    SimulationWorkerSpec(
        name="weekly_rhythm_rollup",
        module_path="sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker",
        function_name="run_weekly_rhythm_rollup",
        production_frequency="weekly on RHYTHM_ROLLUP_WEEKLY_DAYS at RHYTHM_ROLLUP_WEEKLY_HOUR",
        production_source="schedule_rhythm_rollup_weekly",
    ),
    SimulationWorkerSpec(
        name="weekly_signals",
        module_path="sakhi.apps.worker.tasks.weekly_signals_worker",
        function_name="run_weekly_signals_worker",
        production_frequency="weekly on WEEKLY_SIGNALS_DAYS at WEEKLY_SIGNALS_HOUR",
        production_source="schedule_weekly_signals",
    ),
    SimulationWorkerSpec(
        name="goal_evolver",
        module_path="sakhi.apps.worker.tasks.goal_evolver",
        function_name="run_goal_evolver",
        production_frequency="weekly on GOAL_EVOLVER_DAYS at GOAL_EVOLVER_HOUR",
        production_source="schedule_goal_evolver_weekly",
    ),
    SimulationWorkerSpec(
        name="crystallization_weekly",
        module_path="sakhi.apps.worker.tasks.pattern_crystallization_worker",
        function_name="run_weekly_crystallization",
        production_frequency="weekly on CRYSTALLIZATION_WEEKLY_DAYS at CRYSTALLIZATION_WEEKLY_HOUR",
        production_source="schedule_crystallization_weekly",
    ),
)


SIMULATION_MONTHLY_WORKER_SPECS: tuple[SimulationWorkerSpec, ...] = (
    SimulationWorkerSpec(
        name="crystallization_monthly",
        module_path="sakhi.apps.worker.tasks.pattern_crystallization_worker",
        function_name="run_monthly_crystallization",
        production_frequency="monthly on day 1 at CRYSTALLIZATION_MONTHLY_HOUR",
        production_source="schedule_crystallization_monthly",
    ),
)


SIMULATION_INTERVAL_WORKER_SPECS: tuple[SimulationWorkerSpec, ...] = (
    SimulationWorkerSpec(
        name="forecast_interval",
        module_path="sakhi.apps.worker.tasks.forecast",
        function_name="run_forecast",
        production_frequency="every FORECAST_INTERVAL_HOURS",
        production_source="schedule_forecast_jobs",
        parity_note="Runs extra intraday forecast passes for simulation parity.",
    ),
)


def as_import_tuples() -> List[Tuple[str, str, str]]:
    """Return worker specs in (name, module, function) form."""
    return [
        (spec.name, spec.module_path, spec.function_name)
        for spec in SIMULATION_DAILY_WORKER_SPECS
    ]


def weekly_import_tuples() -> List[Tuple[str, str, str]]:
    """Return weekly worker specs in (name, module, function) form."""
    return [
        (spec.name, spec.module_path, spec.function_name)
        for spec in SIMULATION_WEEKLY_WORKER_SPECS
    ]


def monthly_import_tuples() -> List[Tuple[str, str, str]]:
    """Return monthly worker specs in (name, module, function) form."""
    return [
        (spec.name, spec.module_path, spec.function_name)
        for spec in SIMULATION_MONTHLY_WORKER_SPECS
    ]


def interval_import_tuples() -> List[Tuple[str, str, str]]:
    """Return interval worker specs in (name, module, function) form."""
    return [
        (spec.name, spec.module_path, spec.function_name)
        for spec in SIMULATION_INTERVAL_WORKER_SPECS
    ]


def resolve_forecast_runs_per_day(explicit_runs: int | None = None) -> int:
    """Resolve intraday forecast runs from explicit value or FORECAST_INTERVAL_HOURS."""
    if explicit_runs is not None:
        return max(0, explicit_runs)
    raw = os.getenv("FORECAST_INTERVAL_HOURS", "3")
    try:
        hours = int(raw)
    except ValueError:
        hours = 3
    if hours <= 0:
        return 0
    # Keep default parity behavior (3h -> 8 passes/day) but cap runaway values.
    return max(1, min(8, 24 // hours))


def build_worker_frequency_rows(
    daily_worker_interval: int,
    weekly_worker_interval: int = 7,
    monthly_worker_interval: int = 30,
    forecast_interval_runs_per_day: int | None = None,
) -> List[dict[str, str]]:
    """Return production-vs-simulation frequency rows for reporting."""
    daily_interval = max(1, int(daily_worker_interval))
    weekly_interval = max(1, int(weekly_worker_interval))
    monthly_interval = max(1, int(monthly_worker_interval))
    forecast_runs = resolve_forecast_runs_per_day(forecast_interval_runs_per_day)
    rows: List[dict[str, str]] = []
    for spec in SIMULATION_DAILY_WORKER_SPECS:
        rows.append(
            {
                "worker": spec.name,
                "production_frequency": spec.production_frequency,
                "simulation_frequency": (
                    "every simulated day"
                    if daily_interval == 1
                    else f"every {daily_interval} simulated days"
                ),
                "phase": "daily",
                "production_source": spec.production_source,
                "parity_note": spec.parity_note,
            }
        )
    for spec in SIMULATION_WEEKLY_WORKER_SPECS:
        rows.append(
            {
                "worker": spec.name,
                "production_frequency": spec.production_frequency,
                "simulation_frequency": (
                    "every 7 simulated days"
                    if weekly_interval == 7
                    else f"every {weekly_interval} simulated days"
                ),
                "phase": "weekly",
                "production_source": spec.production_source,
                "parity_note": spec.parity_note,
            }
        )
    for spec in SIMULATION_MONTHLY_WORKER_SPECS:
        rows.append(
            {
                "worker": spec.name,
                "production_frequency": spec.production_frequency,
                "simulation_frequency": (
                    "every 30 simulated days"
                    if monthly_interval == 30
                    else f"every {monthly_interval} simulated days"
                ),
                "phase": "monthly",
                "production_source": spec.production_source,
                "parity_note": spec.parity_note,
            }
        )
    for spec in SIMULATION_INTERVAL_WORKER_SPECS:
        rows.append(
            {
                "worker": spec.name,
                "production_frequency": spec.production_frequency,
                "simulation_frequency": (
                    "disabled"
                    if forecast_runs <= 0
                    else f"{forecast_runs} intraday runs per simulated day"
                ),
                "phase": "interval",
                "production_source": spec.production_source,
                "parity_note": spec.parity_note,
            }
        )
    return rows


def render_worker_frequency_table(
    daily_worker_interval: int,
    weekly_worker_interval: int = 7,
    monthly_worker_interval: int = 30,
    forecast_interval_runs_per_day: int | None = None,
) -> str:
    """Render a compact markdown table for CLI output."""
    rows = build_worker_frequency_rows(
        daily_worker_interval=daily_worker_interval,
        weekly_worker_interval=weekly_worker_interval,
        monthly_worker_interval=monthly_worker_interval,
        forecast_interval_runs_per_day=forecast_interval_runs_per_day,
    )
    lines = [
        (
            "Simulation worker frequency "
            f"(daily={max(1, int(daily_worker_interval))}, "
            f"weekly={max(1, int(weekly_worker_interval))}, "
            f"monthly={max(1, int(monthly_worker_interval))}, "
            f"interval_runs={resolve_forecast_runs_per_day(forecast_interval_runs_per_day)})"
        ),
        "",
        "| Phase | Worker | Production Frequency | Simulation Frequency |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['phase']} | {row['worker']} | {row['production_frequency']} | {row['simulation_frequency']} |"
        )
    return "\n".join(lines)


__all__ = [
    "SimulationWorkerSpec",
    "SIMULATION_DAILY_WORKER_SPECS",
    "SIMULATION_WEEKLY_WORKER_SPECS",
    "SIMULATION_MONTHLY_WORKER_SPECS",
    "SIMULATION_INTERVAL_WORKER_SPECS",
    "as_import_tuples",
    "weekly_import_tuples",
    "monthly_import_tuples",
    "interval_import_tuples",
    "resolve_forecast_runs_per_day",
    "build_worker_frequency_rows",
    "render_worker_frequency_table",
]
