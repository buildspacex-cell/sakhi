"""
Mission Repository - Database operations for long-running missions
"""

from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID
import json

from sakhi.libs.schemas.db import get_async_pool as get_pool
from .models import (
    Mission, MissionCreate, MissionPhase, WeeklyPlan,
    ScheduledAction, MissionCheckpoint, MissionData,
    MissionSummary, TodayAction, MissionStatus, ActionStatus
)


class MissionRepository:
    """Database operations for missions"""

    # ========================================================================
    # MISSIONS CRUD
    # ========================================================================

    @staticmethod
    async def create_mission(
        person_id: UUID,
        data: MissionCreate,
        plan_document: Optional[str] = None,
        conversation_id: Optional[UUID] = None
    ) -> Mission:
        """Create a new mission"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO long_running_missions (
                person_id, title, description, category,
                success_criteria, plan_document, target_end_date,
                conversation_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """,
            person_id,
            data.title,
            data.description,
            data.category.value if data.category else None,
            json.dumps(data.success_criteria) if data.success_criteria else None,
            plan_document,
            data.target_end_date,
            conversation_id
        )
        return Mission(**dict(row))

    @staticmethod
    async def get_mission(mission_id: UUID) -> Optional[Mission]:
        """Get a mission by ID"""
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM long_running_missions WHERE id = $1",
            mission_id
        )
        return Mission(**dict(row)) if row else None

    @staticmethod
    async def get_active_missions(person_id: UUID) -> List[MissionSummary]:
        """Get all active missions for a person with summary info"""
        pool = await get_pool()
        rows = await pool.fetch(
            "SELECT * FROM get_active_missions($1)",
            person_id
        )
        return [MissionSummary(**dict(row)) for row in rows]

    @staticmethod
    async def update_mission(
        mission_id: UUID,
        **updates
    ) -> Optional[Mission]:
        """Update mission fields"""
        if not updates:
            return await MissionRepository.get_mission(mission_id)

        # Build SET clause
        set_parts = []
        values = []
        for i, (key, value) in enumerate(updates.items(), start=1):
            set_parts.append(f"{key} = ${i}")
            if isinstance(value, dict):
                values.append(json.dumps(value))
            else:
                values.append(value)

        values.append(mission_id)

        pool = await get_pool()
        row = await pool.fetchrow(f"""
            UPDATE long_running_missions
            SET {', '.join(set_parts)}
            WHERE id = ${len(values)}
            RETURNING *
        """, *values)

        return Mission(**dict(row)) if row else None

    @staticmethod
    async def update_mission_progress(
        mission_id: UUID,
        progress_pct: int,
        health: str,
        metrics: Optional[dict] = None
    ) -> Optional[Mission]:
        """Update mission progress and health"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            UPDATE long_running_missions
            SET progress_pct = $2, health = $3, metrics = COALESCE($4, metrics)
            WHERE id = $1
            RETURNING *
        """, mission_id, progress_pct, health, json.dumps(metrics) if metrics else None)

        return Mission(**dict(row)) if row else None

    # ========================================================================
    # PHASES
    # ========================================================================

    @staticmethod
    async def create_phase(
        mission_id: UUID,
        phase_number: int,
        name: str,
        objective: str,
        start_date: date,
        target_end_date: date,
        expected_outcomes: Optional[List[str]] = None,
        requires_approval: bool = True
    ) -> MissionPhase:
        """Create a mission phase"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO mission_phases (
                mission_id, phase_number, name, objective,
                start_date, target_end_date, expected_outcomes,
                requires_approval
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """,
            mission_id, phase_number, name, objective,
            start_date, target_end_date,
            json.dumps(expected_outcomes) if expected_outcomes else None,
            requires_approval
        )
        return MissionPhase(**dict(row))

    @staticmethod
    async def get_phases(mission_id: UUID) -> List[MissionPhase]:
        """Get all phases for a mission"""
        pool = await get_pool()
        rows = await pool.fetch("""
            SELECT * FROM mission_phases
            WHERE mission_id = $1
            ORDER BY phase_number
        """, mission_id)
        return [MissionPhase(**dict(row)) for row in rows]

    @staticmethod
    async def get_active_phase(mission_id: UUID) -> Optional[MissionPhase]:
        """Get the currently active phase"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            SELECT * FROM mission_phases
            WHERE mission_id = $1 AND status = 'active'
            LIMIT 1
        """, mission_id)
        return MissionPhase(**dict(row)) if row else None

    @staticmethod
    async def approve_phase(phase_id: UUID, approved_by: str = "user") -> MissionPhase:
        """Approve a phase to start"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            UPDATE mission_phases
            SET status = 'active', approved_at = NOW(), approved_by = $2
            WHERE id = $1
            RETURNING *
        """, phase_id, approved_by)
        return MissionPhase(**dict(row))

    # ========================================================================
    # WEEKLY PLANS
    # ========================================================================

    @staticmethod
    async def create_weekly_plan(
        mission_id: UUID,
        phase_id: Optional[UUID],
        week_number: int,
        week_start: date,
        objectives: List[str],
        tasks: Optional[dict] = None
    ) -> WeeklyPlan:
        """Create a weekly plan"""
        week_end = week_start + timedelta(days=6)
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO mission_weekly_plans (
                mission_id, phase_id, week_number,
                week_start, week_end, objectives, tasks
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """,
            mission_id, phase_id, week_number,
            week_start, week_end,
            objectives,
            json.dumps(tasks) if tasks else None
        )
        return WeeklyPlan(**dict(row))

    @staticmethod
    async def get_current_week(mission_id: UUID) -> Optional[WeeklyPlan]:
        """Get the current week's plan"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            SELECT * FROM mission_weekly_plans
            WHERE mission_id = $1
            AND week_start <= CURRENT_DATE
            AND week_end >= CURRENT_DATE
            LIMIT 1
        """, mission_id)
        return WeeklyPlan(**dict(row)) if row else None

    @staticmethod
    async def complete_weekly_review(
        weekly_plan_id: UUID,
        review_notes: str,
        what_worked: List[str],
        what_didnt: List[str],
        adjustments: List[str]
    ) -> WeeklyPlan:
        """Complete the weekly review"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            UPDATE mission_weekly_plans
            SET status = 'completed',
                review_completed = TRUE,
                review_notes = $2,
                what_worked = $3,
                what_didnt = $4,
                adjustments_for_next = $5
            WHERE id = $1
            RETURNING *
        """,
            weekly_plan_id, review_notes,
            what_worked, what_didnt, adjustments
        )
        return WeeklyPlan(**dict(row))

    # ========================================================================
    # SCHEDULED ACTIONS
    # ========================================================================

    @staticmethod
    async def create_action(
        mission_id: UUID,
        person_id: UUID,
        action_type: str,
        description: str,
        scheduled_date: date,
        scheduled_time: Optional[str] = None,
        weekly_plan_id: Optional[UUID] = None,
        instructions: Optional[dict] = None,
        trigger_type: str = "scheduled"
    ) -> ScheduledAction:
        """Create a scheduled action"""
        # Convert time string to datetime.time if provided
        time_value = None
        if scheduled_time:
            try:
                from datetime import time as dt_time
                parts = scheduled_time.split(":")
                time_value = dt_time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                pass  # Invalid time format, leave as None

        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO mission_scheduled_actions (
                mission_id, person_id, weekly_plan_id,
                action_type, description, scheduled_date,
                scheduled_time, instructions, trigger_type
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """,
            mission_id, person_id, weekly_plan_id,
            action_type, description, scheduled_date,
            time_value,
            json.dumps(instructions) if instructions else None,
            trigger_type
        )
        return ScheduledAction(**dict(row))

    @staticmethod
    async def get_todays_actions(person_id: UUID) -> List[TodayAction]:
        """Get all actions for today"""
        pool = await get_pool()
        rows = await pool.fetch(
            "SELECT * FROM get_todays_mission_actions($1)",
            person_id
        )
        return [TodayAction(**dict(row)) for row in rows]

    @staticmethod
    async def get_due_actions(within_hours: int = 1) -> List[ScheduledAction]:
        """Get actions due within the next N hours (for scheduler)"""
        pool = await get_pool()
        rows = await pool.fetch("""
            SELECT * FROM mission_scheduled_actions
            WHERE status = 'scheduled'
            AND scheduled_date = CURRENT_DATE
            AND (scheduled_time IS NULL
                 OR scheduled_time <= (CURRENT_TIME + interval '1 hour' * $1))
            AND (scheduled_time IS NULL OR scheduled_time >= CURRENT_TIME)
            ORDER BY scheduled_time NULLS LAST
        """, within_hours)
        return [ScheduledAction(**dict(row)) for row in rows]

    @staticmethod
    async def start_action(action_id: UUID, agent_session_id: UUID) -> ScheduledAction:
        """Mark an action as running"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            UPDATE mission_scheduled_actions
            SET status = 'running',
                agent_session_id = $2,
                started_at = NOW()
            WHERE id = $1
            RETURNING *
        """, action_id, agent_session_id)
        return ScheduledAction(**dict(row))

    @staticmethod
    async def complete_action(
        action_id: UUID,
        success: bool,
        outcome: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> ScheduledAction:
        """Mark an action as completed or failed"""
        status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
        pool = await get_pool()
        row = await pool.fetchrow("""
            UPDATE mission_scheduled_actions
            SET status = $2,
                success = $3,
                outcome = $4,
                error_message = $5,
                completed_at = NOW()
            WHERE id = $1
            RETURNING *
        """,
            action_id, status.value, success,
            json.dumps(outcome) if outcome else None,
            error_message
        )
        return ScheduledAction(**dict(row))

    # ========================================================================
    # CHECKPOINTS
    # ========================================================================

    @staticmethod
    async def create_checkpoint(
        mission_id: UUID,
        checkpoint_type: str,
        metrics_snapshot: dict,
        progress_pct: int,
        health: str,
        analysis: Optional[str] = None,
        recommendations: Optional[List[str]] = None,
        risks: Optional[List[str]] = None
    ) -> MissionCheckpoint:
        """Create a progress checkpoint"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO mission_checkpoints (
                mission_id, checkpoint_date, checkpoint_type,
                metrics_snapshot, progress_pct, health,
                analysis, recommendations, risks
            ) VALUES ($1, CURRENT_DATE, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """,
            mission_id, checkpoint_type,
            json.dumps(metrics_snapshot), progress_pct, health,
            analysis, recommendations, risks
        )
        return MissionCheckpoint(**dict(row))

    # ========================================================================
    # MISSION DATA (Generic records)
    # ========================================================================

    @staticmethod
    async def record_data(
        person_id: UUID,
        record_type: str,
        data: dict,
        mission_id: Optional[UUID] = None,
        record_date: Optional[date] = None,
        source: Optional[str] = None
    ) -> MissionData:
        """Record generic mission data"""
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO mission_data (
                person_id, mission_id, record_type,
                data, record_date, source
            ) VALUES ($1, $2, $3, $4, COALESCE($5, CURRENT_DATE), $6)
            RETURNING *
        """,
            person_id, mission_id, record_type,
            json.dumps(data), record_date, source
        )
        return MissionData(**dict(row))

    @staticmethod
    async def get_mission_data(
        mission_id: UUID,
        record_type: Optional[str] = None,
        since: Optional[date] = None
    ) -> List[MissionData]:
        """Get mission data records"""
        pool = await get_pool()

        query = "SELECT * FROM mission_data WHERE mission_id = $1"
        params = [mission_id]

        if record_type:
            query += f" AND record_type = ${len(params) + 1}"
            params.append(record_type)

        if since:
            query += f" AND record_date >= ${len(params) + 1}"
            params.append(since)

        query += " ORDER BY record_date DESC, created_at DESC"

        rows = await pool.fetch(query, *params)
        return [MissionData(**dict(row)) for row in rows]

    @staticmethod
    async def aggregate_expenses(
        person_id: UUID,
        since: Optional[date] = None,
        mission_id: Optional[UUID] = None
    ) -> dict:
        """Aggregate expense data by category"""
        pool = await get_pool()

        query = """
            SELECT
                data->>'category' as category,
                SUM((data->>'amount')::numeric) as total,
                COUNT(*) as count
            FROM mission_data
            WHERE person_id = $1
            AND record_type = 'expense'
        """
        params = [person_id]

        if mission_id:
            query += f" AND mission_id = ${len(params) + 1}"
            params.append(mission_id)

        if since:
            query += f" AND record_date >= ${len(params) + 1}"
            params.append(since)

        query += " GROUP BY data->>'category' ORDER BY total DESC"

        rows = await pool.fetch(query, *params)
        return {
            "by_category": [dict(row) for row in rows],
            "total": sum(float(row["total"]) for row in rows)
        }
