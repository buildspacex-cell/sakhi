"""Lightweight scheduler bridge to enqueue reflection and presence jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Dict, List

import redis
from rq import Queue
from dotenv import load_dotenv
try:
    from supabase import create_client
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    create_client = None  # type: ignore[assignment]

from sakhi.apps.worker.jobs import (
    consolidate_person_models,
    deliver_insight_to_presence_queue,
    run_daily_reflection,
    run_weekly_summary,
)
from sakhi.apps.worker.jobs_presence import outreach
from sakhi.apps.worker.tasks.reflect_person_memory import (
    reflect_person_memory,
    reflect_person_memory_delta,
)
from sakhi.apps.worker.tasks.reflect_value_alignment import reflect_value_alignment
from sakhi.apps.worker.tasks.learn_rhythm_profile import learn_rhythm_profile
from sakhi.apps.worker.tasks.generate_clarity_actions import generate_clarity_actions
from sakhi.apps.worker.tasks.complete_task_enrichment import complete_task_enrichment
from sakhi.apps.worker.tasks.persona_updater import run_persona_updater
from sakhi.apps.worker.tasks.persona_mode_detector import run_persona_mode_detector
from sakhi.apps.worker.tasks.tone_continuity import run_tone_continuity
from sakhi.apps.worker.tasks.presence_reflection import run_presence_reflection
from sakhi.apps.worker.tasks.reflect_morning_presence import reflect_morning_presence
from sakhi.apps.worker.tasks.summarize_evening_state import summarize_evening_state
from sakhi.apps.worker.tasks.send_rhythm_nudge import send_rhythm_nudge
from sakhi.apps.worker.tasks.check_inactive_users import check_inactive_users
from sakhi.apps.worker.tasks.ingest_reflection_feedback import compute_feedback_scores
from sakhi.apps.worker.tasks.update_prompt_profile import update_prompt_profile
from sakhi.apps.worker.tasks.synthesize_meta_reflection import synthesize_meta_reflection
from sakhi.apps.worker.tasks.reinforcement_calibration import run_reinforcement_calibration
from sakhi.apps.worker.tasks.life_phase_mapper import run_life_phase_mapper
# ARCHIVED: meta_audit, meta_reflection - see _archive/weekly_v1/
from sakhi.apps.worker.tasks import rhythm_inference
from sakhi.apps.worker.tasks.rhythm_forecast import run_rhythm_forecast
# ARCHIVED: rhythm_adjustments, collective_patterns - see _archive/weekly_v1/
from sakhi.apps.worker.tasks.reflective_loop import run_reflective_loop
from sakhi.apps.worker.tasks.theme_inference import run_theme_inference
from sakhi.apps.worker.tasks.update_theme_rhythm_links import update_theme_rhythm_links
from sakhi.apps.worker.tasks.intent_evolution_decay import intent_evolution_decay
from sakhi.apps.worker.tasks.emotion_loop_refresh import emotion_loop_refresh
from sakhi.apps.worker.tasks.forecast import run_forecast
from sakhi.apps.worker.tasks.nudge_worker import run_nudge_check
from sakhi.apps.worker.tasks.learning_jobs import run_mark_missed
# ARCHIVED: alignment_refresh, narrative_arc_refresh, pattern_sense_refresh,
# inner_dialogue_refresh, identity_drift_refresh, inner_conflict, coherence,
# evening_closure_worker, morning_preview_worker, morning_ask_worker,
# morning_momentum_worker, micro_momentum_worker, micro_recovery_worker,
# focus_path_worker, mini_flow_worker, micro_journey_worker
# See: sakhi/apps/worker/tasks/_archive/daily_v1/
from sakhi.apps.worker.tasks.weekly_learning_worker import run_weekly_learning
from sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker import run_weekly_rhythm_rollup
# ARCHIVED: weekly_planner_pressure_worker, turn_personal_model_update - see _archive/weekly_v1/
from sakhi.apps.worker.tasks.weekly_signals_worker import run_weekly_signals_worker
from sakhi.apps.worker.rhythm_soul_deep import run_rhythm_soul_deep
from sakhi.apps.worker.tasks.goal_evolver import run_goal_evolver
# ARCHIVED: planner_auto_summary - see _archive/daily_v1/
from sakhi.apps.worker.tasks.pattern_crystallization_worker import (
    run_daily_crystallization,
    run_weekly_crystallization,
    run_monthly_crystallization,
)
from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental
from sakhi.apps.worker.identity_momentum_deep import run_identity_momentum_deep
# Per-turn workers moved to daily schedule (v2 optimization)
from sakhi.apps.worker.tasks.ayurvedic_pipeline import run_ayurvedic_pipeline
from sakhi.apps.worker.tasks.emotion_soul_rhythm_deep import run_emotion_soul_rhythm_deep
from sakhi.apps.worker.tasks.esr_worker import run_emotion_state_refresh
from sakhi.apps.worker.tasks.soul_refresh_worker import soul_refresh_worker
# ARCHIVED: esr_deep, decision_graph_deep, identity_timeline_deep - see _archive/weekly_v1/
# Legacy tasks removed - backed up in _legacy_backup/tasks/
# from sakhi.apps.worker.tasks.sync_analytics_cache import sync_analytics_cache
# from sakhi.apps.worker.tasks.update_system_tempo import update_system_tempo
from sakhi.apps.worker.tasks.memory_fanout import memory_event_fanout
from sakhi.apps.worker.tasks.task_weaver_refresh import task_weaver_refresh
# ARCHIVED: daily_reflection_worker - see _archive/daily_v1/
from sakhi.apps.worker.utils.db import db_find

load_dotenv(".env.worker")
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEMO_USER_ID = os.getenv("DEMO_USER_ID")
if not DEMO_USER_ID:
    raise RuntimeError("Set DEMO_USER_ID for scheduler.")

_redis = redis.from_url(REDIS_URL)
_queue = Queue(os.getenv("REFLECTION_QUEUE", "reflection"), connection=_redis)
_presence_queue = Queue(os.getenv("PRESENCE_QUEUE", "presence"), connection=_redis)
_rhythm_queue = Queue(os.getenv("RHYTHM_QUEUE", "rhythm"), connection=_redis)
_analytics_queue = Queue(os.getenv("ANALYTICS_QUEUE", "analytics"), connection=_redis)
_patterns_queue = Queue(os.getenv("PATTERNS_QUEUE", "patterns"), connection=_redis)
_learning_queue = Queue(os.getenv("LEARNING_QUEUE", "learning"), connection=_redis)
_SUPABASE_CLIENT: Any | None = None
_event_subscribers = {
    "memory.entry.observed": memory_event_fanout,
}

_WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}
_RUN_ALWAYS = -1
_RUN_DISABLED = -2


def _parse_weekday_config(env_var: str, default: tuple[int, ...]) -> set[int] | None:
    raw = os.getenv(env_var)
    if raw is None or raw.strip() == "":
        return set(default)
    normalized = raw.strip().lower()
    if normalized in {"*", "all", "any"}:
        return None
    if normalized in {"off", "none", "disable"}:
        return set()

    values: set[int] = set()
    for token in raw.split(","):
        slug = token.strip().lower()
        if slug == "":
            continue
        if slug in _WEEKDAY_ALIASES:
            values.add(_WEEKDAY_ALIASES[slug])
            continue
        try:
            idx = int(slug)
        except ValueError:
            continue
        if 0 <= idx <= 6:
            values.add(idx)
    return values


def _should_run_today(allowed_days: set[int] | None) -> bool:
    if allowed_days is None:
        return True
    if not allowed_days:
        return False
    return datetime.now(timezone.utc).weekday() in allowed_days


def _parse_time_config(env_var: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(env_var)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"*", "all", "any"}:
        return _RUN_ALWAYS
    if normalized in {"off", "none", "disable"}:
        return _RUN_DISABLED
    try:
        value = int(normalized)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _should_run_minute(target: int) -> bool:
    if target == _RUN_DISABLED:
        return False
    if target == _RUN_ALWAYS:
        return True
    return datetime.utcnow().minute == target


def _should_run_hour(target: int) -> bool:
    if target == _RUN_DISABLED:
        return False
    if target == _RUN_ALWAYS:
        return True
    return datetime.now(timezone.utc).hour == target


WEEKLY_SUMMARY_DAYS = _parse_weekday_config("WEEKLY_SUMMARY_WEEKDAYS", (0,))
META_AUDIT_DAYS = _parse_weekday_config("META_AUDIT_WEEKDAYS", (6,))
THEME_INFERENCE_DAYS = _parse_weekday_config("THEME_INFERENCE_WEEKDAYS", (6,))
META_REFLECTION_DAYS = _parse_weekday_config("META_REFLECTION_WEEKDAYS", (6,))
COLLECTIVE_LEARNING_DAYS = _parse_weekday_config("COLLECTIVE_PATTERNS_WEEKDAYS", (0,))
THEME_RHYTHM_LINK_DAYS = _parse_weekday_config("THEME_RHYTHM_LINKS_WEEKDAYS", (6,))
RHYTHM_SELF_ADJUST_DAYS = _parse_weekday_config("RHYTHM_SELF_ADJUSTMENT_WEEKDAYS", (1,))
RHYTHM_FORECAST_DAYS = _parse_weekday_config("RHYTHM_FORECAST_WEEKDAYS", (0,))
RHYTHM_SOUL_WEEKLY_DAYS = _parse_weekday_config("RHYTHM_SOUL_WEEKLY_DAYS", (0,))
LEARNING_WEEKLY_DAYS = _parse_weekday_config("LEARNING_WEEKLY_DAYS", (0,))
RHYTHM_ROLLUP_WEEKLY_DAYS = _parse_weekday_config("RHYTHM_ROLLUP_WEEKLY_DAYS", (0,))
# ARCHIVED: PLANNER_ROLLUP_WEEKLY_DAYS, PM_UPDATE_WEEKLY_DAYS - see _archive/weekly_v1/
WEEKLY_SIGNALS_DAYS = _parse_weekday_config("WEEKLY_SIGNALS_DAYS", (0,))
GOAL_EVOLVER_DAYS = _parse_weekday_config("GOAL_EVOLVER_DAYS", (0,))  # Weekly on Monday
CRYSTALLIZATION_WEEKLY_DAYS = _parse_weekday_config("CRYSTALLIZATION_WEEKLY_DAYS", (0,))  # Monday
CRYSTALLIZATION_MONTHLY_DAYS = _parse_weekday_config("CRYSTALLIZATION_MONTHLY_DAYS", ())  # First of month

RHYTHM_SOUL_DAILY_HOUR = _parse_time_config("RHYTHM_SOUL_DAILY_HOUR", 6, minimum=0, maximum=23)
RHYTHM_SOUL_WEEKLY_HOUR = _parse_time_config("RHYTHM_SOUL_WEEKLY_HOUR", 8, minimum=0, maximum=23)
# ARCHIVED: ESR_WEEKLY_*, IDENTITY_MOMENTUM_*, DECISION_GRAPH_*, IDENTITY_TIMELINE_* - see _archive/weekly_v1/
LEARNING_WEEKLY_HOUR = _parse_time_config("LEARNING_WEEKLY_HOUR", 6, minimum=0, maximum=23)
RHYTHM_ROLLUP_WEEKLY_HOUR = _parse_time_config("RHYTHM_ROLLUP_WEEKLY_HOUR", 5, minimum=0, maximum=23)
# ARCHIVED: PLANNER_ROLLUP_WEEKLY_HOUR, PM_UPDATE_WEEKLY_HOUR
WEEKLY_SIGNALS_HOUR = _parse_time_config("WEEKLY_SIGNALS_HOUR", 3, minimum=0, maximum=23)
TASK_WEAVER_HOUR = _parse_time_config("TASK_WEAVER_HOUR", 6, minimum=0, maximum=23)
GOAL_EVOLVER_HOUR = _parse_time_config("GOAL_EVOLVER_HOUR", 8, minimum=0, maximum=23)
PLANNER_SUMMARY_HOUR = _parse_time_config("PLANNER_SUMMARY_HOUR", 21, minimum=0, maximum=23)
CRYSTALLIZATION_DAILY_HOUR = _parse_time_config("CRYSTALLIZATION_DAILY_HOUR", 3, minimum=0, maximum=23)
CRYSTALLIZATION_WEEKLY_HOUR = _parse_time_config("CRYSTALLIZATION_WEEKLY_HOUR", 4, minimum=0, maximum=23)
CRYSTALLIZATION_MONTHLY_HOUR = _parse_time_config("CRYSTALLIZATION_MONTHLY_HOUR", 5, minimum=0, maximum=23)
THEME_UPRANK_HOUR = _parse_time_config("THEME_UPRANK_HOUR", 6, minimum=0, maximum=23)

# Per-turn workers moved to daily schedule (v2 optimization)
AYURVEDIC_PIPELINE_HOUR = _parse_time_config("AYURVEDIC_PIPELINE_HOUR", 6, minimum=0, maximum=23)
IDENTITY_MOMENTUM_HOUR = _parse_time_config("IDENTITY_MOMENTUM_HOUR", 6, minimum=0, maximum=23)
EMOTION_SOUL_RHYTHM_HOUR = _parse_time_config("EMOTION_SOUL_RHYTHM_HOUR", 4, minimum=0, maximum=23)
ESR_DAILY_HOUR = _parse_time_config("ESR_DAILY_HOUR", 4, minimum=0, maximum=23)
SOUL_REFRESH_HOUR = _parse_time_config("SOUL_REFRESH_HOUR", 6, minimum=0, maximum=23)

SYSTEM_TEMPO_MINUTE = _parse_time_config("SYSTEM_TEMPO_MINUTE", 0, minimum=0, maximum=59)
ANALYTICS_CACHE_HOUR = _parse_time_config("ANALYTICS_CACHE_HOUR", 2, minimum=0, maximum=23)
INTENT_DECAY_HOUR = _parse_time_config("INTENT_DECAY_HOUR", 7, minimum=0, maximum=23)
EMOTION_LOOP_HOUR = _parse_time_config("EMOTION_LOOP_HOUR", 4, minimum=0, maximum=23)
FORECAST_HOUR = _parse_time_config("FORECAST_HOUR", 7, minimum=0, maximum=23)
FORECAST_INTERVAL_HOURS = int(os.getenv("FORECAST_INTERVAL_HOURS", "3") or "3")
NUDGE_CHECK_MINUTE = _parse_time_config("NUDGE_CHECK_MINUTE", 0, minimum=0, maximum=59)
# ARCHIVED config: ALIGNMENT_REFRESH_HOUR, NARRATIVE_ARC_HOUR, PATTERN_SENSE_HOUR,
# INNER_DIALOGUE_HOUR, IDENTITY_DRIFT_HOUR, INNER_CONFLICT_HOUR, COHERENCE_STATE_HOUR,
# MORNING_ASK_MINUTE, MORNING_MOMENTUM_MINUTE, MICRO_MOMENTUM_MINUTE, MICRO_RECOVERY_*,
# FOCUS_PATH_*, MINI_FLOW_*, MICRO_JOURNEY_*


def _enqueue(queue: Queue, func: Any, *args: Any, **kwargs: Any) -> None:
    print(f"[scheduler] → enqueue {func.__name__} on {queue.name}")
    queue.enqueue(func, *args, **kwargs)


def _get_supabase_client() -> Any | None:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        if create_client is None:
            print("[scheduler] Supabase client unavailable – install supabase-py to enable insights queue polling.")
            _SUPABASE_CLIENT = False
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_API_KEY")
            if url and key:
                try:
                    _SUPABASE_CLIENT = create_client(url, key)
                except Exception as exc:  # pragma: no cover - optional client
                    print(f"[scheduler] Supabase client init failed: {exc}")
                    _SUPABASE_CLIENT = False
            else:
                _SUPABASE_CLIENT = False
    return _SUPABASE_CLIENT or None


def schedule_reflection_jobs() -> None:
    """
    Enqueue both immediate and scheduled reflections based on horizon.
    """

    user_id = DEMO_USER_ID
    _enqueue(_queue, run_daily_reflection, user_id)
    _enqueue(_queue, consolidate_person_models)
    _enqueue(_queue, reflect_person_memory, user_id)
    _enqueue(_queue, reflect_value_alignment, user_id)
    _enqueue(_queue, learn_rhythm_profile, user_id)
    _enqueue(_queue, generate_clarity_actions)
    _enqueue(_queue, complete_task_enrichment)
    _enqueue(_queue, run_persona_updater, user_id)
    _enqueue(_queue, run_persona_mode_detector, user_id)
    _enqueue(_queue, run_tone_continuity, user_id)
    _enqueue(_queue, run_reflective_loop, user_id)

    # ARCHIVED: run_weekly_summary, run_meta_audit - see _archive/weekly_v1/

    schedule_theme_inference_jobs()
    # ARCHIVED: schedule_meta_reflection_jobs, schedule_collective_learning, schedule_rhythm_self_adjustment
    schedule_theme_rhythm_links()
    schedule_tempo_updates()
    schedule_analytics_cache_job()
    check_and_enqueue_delta_jobs()


def schedule_presence_jobs() -> None:
    """Enqueue presence outreach previews for pilot users."""

    user_id = DEMO_USER_ID
    _enqueue(_presence_queue, outreach, user_id)
    _enqueue(_presence_queue, run_presence_reflection, user_id)


def schedule_presence_reflection() -> None:
    """
    Adds morning/evening reflection & rhythm nudges.
    """
    user_id = DEMO_USER_ID
    _enqueue(_queue, reflect_morning_presence, user_id)
    _enqueue(_queue, send_rhythm_nudge, user_id)
    _enqueue(_queue, summarize_evening_state, user_id)
    _enqueue(_queue, check_inactive_users)


def schedule_tone_jobs() -> None:
    """Schedule tone continuity updates."""
    user_id = DEMO_USER_ID
    _enqueue(_queue, run_tone_continuity, user_id)


def schedule_theme_inference_jobs() -> None:
    """Weekly theme consolidation (Sunday)."""
    if not _should_run_today(THEME_INFERENCE_DAYS):
        return
    user_id = DEMO_USER_ID
    _enqueue(_queue, run_theme_inference, user_id)


# ARCHIVED: schedule_meta_reflection_jobs, schedule_collective_learning - see _archive/weekly_v1/


def schedule_theme_rhythm_links() -> None:
    """Enqueue weekly theme–rhythm correlation updates (Sunday)."""

    if not _should_run_today(THEME_RHYTHM_LINK_DAYS):
        return
    _enqueue(_analytics_queue, update_theme_rhythm_links)


# ARCHIVED: schedule_rhythm_self_adjustment - see _archive/weekly_v1/


def schedule_tempo_updates() -> None:
    """Legacy - system tempo now computed from personal_model."""
    pass  # Removed: update_system_tempo used legacy body_metrics table


def schedule_analytics_cache_job() -> None:
    """Legacy - analytics now computed directly from personal_model."""
    pass  # Removed: sync_analytics_cache used legacy emotional_tones table


def schedule_learning_self_jobs() -> None:
    """Enqueue nightly self-learning updates for the default user."""
    user_id = DEMO_USER_ID
    _enqueue(_queue, compute_feedback_scores, user_id)
    _enqueue(_queue, update_prompt_profile, user_id)
    _enqueue(_queue, synthesize_meta_reflection, user_id)
    _enqueue(_queue, run_reinforcement_calibration, user_id)
    _enqueue(_queue, run_life_phase_mapper, user_id)

# ARCHIVED: schedule_daily_reflection_v2, schedule_evening_closure,
# schedule_morning_preview, schedule_morning_ask, schedule_morning_momentum,
# schedule_micro_momentum, schedule_micro_recovery, schedule_focus_path,
# schedule_mini_flow, schedule_micro_journey_daily
# See: sakhi/apps/worker/tasks/_archive/daily_v1/


def check_and_enqueue_delta_jobs(limit: int = 10) -> None:
    """
    Review short-horizon insights and enqueue deliveries once their delay matures.
    """

    pending = db_fetch_pending_insights(limit=limit)
    for row in pending:
        if not isinstance(row, dict):
            continue
        person_id = row.get("person_id")
        entry_text = row.get("entry_text") or ""
        if person_id and entry_text and "insight" not in row:
            try:
                result = asyncio.run(
                    reflect_person_memory_delta(person_id, entry_text)
                )
                row["insight"] = result.get("insight")
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[scheduler] delta reflection failed: {exc}")
                continue

        row.setdefault("delivered", False)
        _enqueue(_presence_queue, deliver_insight_to_presence_queue, row)
        mark_insight_delivered(row)


def db_fetch_pending_insights(*, limit: int = 10) -> List[Dict[str, Any]]:
    client = _get_supabase_client()
    if client is None:
        return []

    now_iso = datetime.utcnow().isoformat()
    try:
        response = (
            client.table("insights_queue")
            .select("*")
            .is_("delivered_at", None)
            .lte("deliver_after", now_iso)
            .limit(limit)
            .execute()
        )
        data = getattr(response, "data", None)
        if isinstance(data, list):
            return data
    except Exception as exc:  # pragma: no cover - optional service
        print(f"[scheduler] fetch pending insights failed: {exc}")
    return []


def mark_insight_delivered(row: Dict[str, Any]) -> None:
    client = _get_supabase_client()
    if client is None:
        return
    row_id = row.get("id")
    if not row_id:
        return
    now_iso = datetime.utcnow().isoformat()
    try:
        client.table("insights_queue").update(
            {"delivered_at": now_iso}
        ).eq("id", row_id).execute()
    except Exception as exc:  # pragma: no cover
        print(f"[scheduler] mark insight delivered failed: {exc}")


def nightly_learning_cycle() -> None:
    """Iterate across known persons and enqueue self-learning updates."""
    persons = db_find("persons") or []
    for person in persons:
        person_id = person.get("id") or person.get("person_id")
        if not person_id:
            continue
        _enqueue(_queue, compute_feedback_scores, person_id)
        _enqueue(_queue, update_prompt_profile, person_id)
        _enqueue(_queue, synthesize_meta_reflection, person_id)
        _enqueue(_queue, run_tone_continuity, person_id)


def schedule_rhythm_jobs() -> None:
    """Kick off background rhythm inference jobs."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    q = Queue("rhythm", connection=redis.from_url(redis_url))
    user_id = DEMO_USER_ID
    q.enqueue(rhythm_inference.run_rhythm_inference, user_id)


def schedule_rhythm_forecast_jobs() -> None:
    """Runs rhythm forecasts every Monday on the rhythm queue."""
    if not _should_run_today(RHYTHM_FORECAST_DAYS):
        return
    user_id = DEMO_USER_ID
    _enqueue(_rhythm_queue, run_rhythm_forecast, user_id)


def schedule_rhythm_soul_daily() -> None:
    """Daily deep rhythm–soul sync around RHYTHM_SOUL_DAILY_HOUR."""
    if not _should_run_hour(RHYTHM_SOUL_DAILY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_rhythm_soul_deep, user_id)


def schedule_rhythm_soul_weekly() -> None:
    """Weekly (default Monday) deep rhythm–soul sync at RHYTHM_SOUL_WEEKLY_HOUR."""
    if not _should_run_today(RHYTHM_SOUL_WEEKLY_DAYS):
        return
    if not _should_run_hour(RHYTHM_SOUL_WEEKLY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_rhythm_soul_deep, user_id)


# ARCHIVED: schedule_esr_weekly, schedule_identity_momentum_weekly,
# schedule_decision_graph_weekly, schedule_identity_timeline_weekly
# See: _archive/weekly_v1/


def schedule_weekly_learning() -> None:
    """Weekly longitudinal learning update (episodic -> longitudinal_state)."""
    if not _should_run_today(LEARNING_WEEKLY_DAYS):
        return
    if not _should_run_hour(LEARNING_WEEKLY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_learning_queue, run_weekly_learning, user_id)


def schedule_rhythm_rollup_weekly() -> None:
    """Weekly rhythm rollup (deterministic capacity patterns)."""
    if not _should_run_today(RHYTHM_ROLLUP_WEEKLY_DAYS):
        return
    if not _should_run_hour(RHYTHM_ROLLUP_WEEKLY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_weekly_rhythm_rollup, user_id)


# ARCHIVED: schedule_planner_pressure_weekly, schedule_turn_personal_model_update_weekly
# See: _archive/weekly_v1/


def schedule_weekly_signals() -> None:
    """Weekly signals aggregation (language-free)."""
    if not _should_run_today(WEEKLY_SIGNALS_DAYS):
        return
    if not _should_run_hour(WEEKLY_SIGNALS_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_weekly_signals_worker, user_id)
def schedule_task_weaver_daily() -> None:
    """Daily task weaver refresh to keep auto-priorities current."""
    if not _should_run_hour(TASK_WEAVER_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, task_weaver_refresh, user_id)


def schedule_goal_evolver_weekly() -> None:
    """Weekly goal evolution - reviews goals against reflections and rhythm."""
    if not _should_run_today(GOAL_EVOLVER_DAYS):
        return
    if not _should_run_hour(GOAL_EVOLVER_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_learning_queue, run_goal_evolver, user_id)


# ARCHIVED: schedule_planner_summary_daily - see _archive/daily_v1/


def schedule_crystallization_daily() -> None:
    """Daily pattern crystallization - frequency and recurrence focus."""
    if not _should_run_hour(CRYSTALLIZATION_DAILY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_patterns_queue, run_daily_crystallization, user_id)


def schedule_crystallization_weekly() -> None:
    """Weekly pattern crystallization - trajectory and consistency focus."""
    if not _should_run_today(CRYSTALLIZATION_WEEKLY_DAYS):
        return
    if not _should_run_hour(CRYSTALLIZATION_WEEKLY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_patterns_queue, run_weekly_crystallization, user_id)


def schedule_crystallization_monthly() -> None:
    """Monthly pattern crystallization - identity and traits focus."""
    # Run on first day of month
    if datetime.now(timezone.utc).day != 1:
        return
    if not _should_run_hour(CRYSTALLIZATION_MONTHLY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_patterns_queue, run_monthly_crystallization, user_id)


def schedule_theme_uprank_daily() -> None:
    """Daily theme upranking based on crystallized patterns."""
    if not _should_run_hour(THEME_UPRANK_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_theme_inference_incremental, user_id)


def schedule_intent_decay_daily() -> None:
    """Daily decay for intent evolution."""
    if not _should_run_hour(INTENT_DECAY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, intent_evolution_decay, user_id)


def schedule_emotion_loop_daily() -> None:
    """Daily refresh for emotion loop state."""
    if not _should_run_hour(EMOTION_LOOP_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, emotion_loop_refresh, user_id)


# ARCHIVED: schedule_alignment_refresh_daily, schedule_narrative_arc_daily,
# schedule_pattern_sense_daily, schedule_inner_dialogue_daily,
# schedule_identity_drift_daily, schedule_inner_conflict_daily,
# schedule_coherence_state_daily - see _archive/daily_v1/


def schedule_forecast_jobs() -> None:
    """Forecast refresh daily and interval-based."""
    user_id = DEMO_USER_ID
    if _should_run_hour(FORECAST_HOUR):
        _enqueue(_analytics_queue, run_forecast, user_id)
        _enqueue(_analytics_queue, run_nudge_check, user_id)
        _enqueue(_learning_queue, run_mark_missed)
    # interval-based (every N hours) best-effort
    try:
        if FORECAST_INTERVAL_HOURS > 0 and (datetime.utcnow().hour % FORECAST_INTERVAL_HOURS) == 0:
            _enqueue(_analytics_queue, run_forecast, user_id)
            _enqueue(_analytics_queue, run_nudge_check, user_id)
    except Exception:
        pass


def schedule_nudge_checks() -> None:
    """Hourly nudge check using forecast cache and tone state."""
    if not _should_run_minute(NUDGE_CHECK_MINUTE):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_nudge_check, user_id)


# =============================================================================
# Per-Turn Workers Moved to Daily Schedule (v2 Optimization)
# These were previously running on every conversation turn but are now scheduled
# daily to reduce turn processing overhead. Context is maintained via:
# - conversation_history + memory_recall + memory_graph + personal_model
# =============================================================================


def schedule_ayurvedic_pipeline_daily() -> None:
    """Daily Ayurvedic pipeline - dosha/elemental state computation."""
    if not _should_run_hour(AYURVEDIC_PIPELINE_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_ayurvedic_pipeline, user_id)


def schedule_identity_momentum_daily() -> None:
    """Daily identity momentum - tracks identity evolution patterns."""
    if not _should_run_hour(IDENTITY_MOMENTUM_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_identity_momentum_deep, user_id)


def schedule_emotion_soul_rhythm_daily() -> None:
    """Daily emotion-soul-rhythm integration."""
    if not _should_run_hour(EMOTION_SOUL_RHYTHM_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_emotion_soul_rhythm_deep, user_id)


def schedule_esr_daily() -> None:
    """Daily ESR (Emotion State Refresh)."""
    if not _should_run_hour(ESR_DAILY_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, run_emotion_state_refresh, user_id)


def schedule_soul_refresh_daily() -> None:
    """Daily soul/prakriti state refresh."""
    if not _should_run_hour(SOUL_REFRESH_HOUR):
        return
    user_id = DEMO_USER_ID
    _enqueue(_analytics_queue, soul_refresh_worker, user_id)


if __name__ == "__main__":  # pragma: no cover
    import sys

    args = sys.argv[1:]
    if args and args[0] == "rhythm":
        schedule_rhythm_jobs()
    else:
        # TODO: before production, replace this manual orchestration with real cron scheduling
        # and remove any force-runs added for testing.
        schedule_reflection_jobs()
        schedule_presence_jobs()
        schedule_presence_reflection()
        schedule_tone_jobs()
        schedule_rhythm_jobs()
        schedule_rhythm_forecast_jobs()
        schedule_rhythm_soul_daily()
        schedule_rhythm_soul_weekly()
        # ARCHIVED: schedule_esr_weekly, schedule_identity_momentum_weekly,
        # schedule_decision_graph_weekly, schedule_identity_timeline_weekly,
        # schedule_turn_personal_model_update_weekly, schedule_planner_pressure_weekly
        schedule_weekly_learning()
        schedule_rhythm_rollup_weekly()
        schedule_weekly_signals()
        schedule_task_weaver_daily()
        schedule_intent_decay_daily()
        schedule_emotion_loop_daily()
        # ARCHIVED: alignment_refresh, narrative_arc, pattern_sense,
        # inner_dialogue, identity_drift, inner_conflict, coherence_state
        schedule_forecast_jobs()
        schedule_nudge_checks()
        schedule_goal_evolver_weekly()
        # ARCHIVED: planner_summary_daily
        schedule_crystallization_daily()
        schedule_crystallization_weekly()
        schedule_crystallization_monthly()
        schedule_theme_uprank_daily()
        # Per-turn workers moved to daily schedule (v2 optimization)
        schedule_ayurvedic_pipeline_daily()
        schedule_identity_momentum_daily()
        schedule_emotion_soul_rhythm_daily()
        schedule_esr_daily()
        schedule_soul_refresh_daily()
