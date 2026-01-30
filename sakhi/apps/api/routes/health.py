"""Health data API routes - sync from Apple Health / Android Health Connect."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import dbfetchrow, dbfetchall, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.services.body.state_engine import get_body_state


router = APIRouter(prefix="/health", tags=["health"])


# === Request/Response Models ===


class HealthDataRecord(BaseModel):
    """Single health data record from mobile app."""
    type: str = Field(..., description="Data type: sleep, activity, heart, respiratory, body, nutrition, mindfulness")
    data: Dict[str, Any] = Field(..., description="The health data payload")
    recorded_at: datetime = Field(..., description="When the measurement was taken")


class HealthSyncRequest(BaseModel):
    """Batch sync request from mobile app."""
    source: str = Field(..., description="Data source: apple_health, android_health, wearable")
    records: List[HealthDataRecord] = Field(..., description="Health data records to sync")


class SelfReportBodyRequest(BaseModel):
    """Self-reported body state check-in."""
    energy_level: Optional[float] = Field(None, ge=0, le=1)
    fatigue_level: Optional[float] = Field(None, ge=0, le=1)
    tension_neck_shoulders: Optional[float] = Field(None, ge=0, le=1)
    tension_back: Optional[float] = Field(None, ge=0, le=1)
    tension_jaw: Optional[float] = Field(None, ge=0, le=1)
    hunger_level: Optional[float] = Field(None, ge=0, le=1)
    digestion_quality: Optional[str] = Field(None, description="good, sluggish, hyperactive, irregular")
    bloating: Optional[bool] = None
    elimination_regular: Optional[bool] = None
    feeling_cold: Optional[bool] = None
    feeling_hot: Optional[bool] = None
    hydration_level: Optional[float] = Field(None, ge=0, le=1)
    breath_quality: Optional[str] = Field(None, description="deep, moderate, shallow, irregular")
    cravings: Optional[List[str]] = Field(None, description="sweet, salty, warm, cold, heavy, light, spicy")
    notes: Optional[str] = None


class BodyStateResponse(BaseModel):
    """Current body state response."""
    vitals: Dict[str, Any]
    sleep: Dict[str, Any]
    energy: Dict[str, Any]
    dosha_body: Dict[str, Any]
    agni: Dict[str, Any]
    ojas: Dict[str, Any]
    tension_map: Dict[str, Any]
    prana: Dict[str, Any]
    summary: Dict[str, Any]
    updated_at: Optional[str]


# === Endpoints ===


@router.post("/sync/{person_id}")
async def sync_health_data(
    person_id: str,
    request: HealthSyncRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Sync health data from mobile app (Apple Health / Android Health Connect).

    The mobile app collects health data in the background and periodically
    syncs it to this endpoint. Data is stored in health_data_sync table
    and processed by the body_refresh worker.

    Example payload:
    ```json
    {
        "source": "apple_health",
        "records": [
            {
                "type": "sleep",
                "data": {
                    "duration_hours": 7.5,
                    "deep_sleep_percent": 18,
                    "rem_percent": 22,
                    "interruptions": 2
                },
                "recorded_at": "2024-01-28T07:00:00Z"
            },
            {
                "type": "heart",
                "data": {
                    "type": "resting_heart_rate",
                    "value": 62
                },
                "recorded_at": "2024-01-28T08:00:00Z"
            }
        ]
    }
    ```
    """
    person_id = await resolve_person_id(person_id) or person_id

    # Validate person exists
    person = await dbfetchrow(
        "SELECT id FROM persons WHERE id = $1",
        person_id,
    )
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Insert records
    inserted = 0
    for record in request.records:
        await dbexec(
            """
            INSERT INTO health_data_sync (person_id, source, data_type, data, recorded_at)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            person_id,
            request.source,
            record.type,
            json.dumps(record.data, ensure_ascii=False, default=str),
            record.recorded_at,
        )
        inserted += 1

    # Trigger body refresh in background
    background_tasks.add_task(_trigger_body_refresh, person_id)

    return {
        "success": True,
        "records_synced": inserted,
        "source": request.source,
    }


@router.post("/self-report/{person_id}")
async def submit_self_report(
    person_id: str,
    request: SelfReportBodyRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Submit self-reported body state check-in.

    Users can report their physical state including:
    - Energy and fatigue levels
    - Tension areas (neck, back, jaw)
    - Digestion quality and hunger
    - Temperature sensations
    - Breath quality
    - Cravings (reveal dosha imbalances)

    This supplements health app data for complete body awareness.
    """
    person_id = await resolve_person_id(person_id) or person_id

    await dbexec(
        """
        INSERT INTO self_report_body (
            person_id, energy_level, fatigue_level,
            tension_neck_shoulders, tension_back, tension_jaw,
            hunger_level, digestion_quality, bloating, elimination_regular,
            feeling_cold, feeling_hot, hydration_level,
            breath_quality, cravings, notes
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        )
        """,
        person_id,
        request.energy_level,
        request.fatigue_level,
        request.tension_neck_shoulders,
        request.tension_back,
        request.tension_jaw,
        request.hunger_level,
        request.digestion_quality,
        request.bloating,
        request.elimination_regular,
        request.feeling_cold,
        request.feeling_hot,
        request.hydration_level,
        request.breath_quality,
        request.cravings,
        request.notes,
    )

    # Trigger body refresh in background
    background_tasks.add_task(_trigger_body_refresh, person_id)

    return {
        "success": True,
        "message": "Body check-in recorded",
    }


@router.get("/body-state/{person_id}")
async def get_current_body_state(person_id: str) -> Dict[str, Any]:
    """
    Get current body state for a person.

    Returns comprehensive physical state including:
    - Vitals (HR, HRV, SpO2)
    - Sleep quality and patterns
    - Energy levels and trends
    - Ayurvedic dosha body assessment
    - Agni (digestive fire) state
    - Ojas (vital essence) level
    - Tension map
    - Prana (breath) quality
    - Summary with recommendations
    """
    person_id = await resolve_person_id(person_id) or person_id

    body_state = await get_body_state(person_id)

    return body_state


@router.get("/history/{person_id}")
async def get_body_state_history(
    person_id: str,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Get body state history for longitudinal analysis.

    Returns daily snapshots of body state for pattern analysis.
    """
    person_id = await resolve_person_id(person_id) or person_id

    rows = await dbfetchall(
        """
        SELECT
            DATE(computed_at) as date,
            AVG(overall_score) as avg_overall,
            AVG(vata_score) as avg_vata,
            AVG(pitta_score) as avg_pitta,
            AVG(kapha_score) as avg_kapha,
            AVG(ojas_level) as avg_ojas,
            AVG(sleep_quality) as avg_sleep,
            AVG(energy_level) as avg_energy
        FROM body_state_history
        WHERE person_id = $1
          AND computed_at > NOW() - INTERVAL '%s days'
        GROUP BY DATE(computed_at)
        ORDER BY date DESC
        """ % days,
        person_id,
    )

    return {
        "person_id": person_id,
        "days": days,
        "history": [
            {
                "date": str(row["date"]),
                "overall_score": row["avg_overall"],
                "vata_score": row["avg_vata"],
                "pitta_score": row["avg_pitta"],
                "kapha_score": row["avg_kapha"],
                "ojas_level": row["avg_ojas"],
                "sleep_quality": row["avg_sleep"],
                "energy_level": row["avg_energy"],
            }
            for row in rows
        ],
    }


@router.get("/recommendations/{person_id}")
async def get_body_recommendations(person_id: str) -> Dict[str, Any]:
    """
    Get personalized body recommendations based on current state.

    Returns Ayurvedic recommendations translated to everyday language.
    """
    from sakhi.apps.api.services.response.translation import translate_body_state

    person_id = await resolve_person_id(person_id) or person_id

    body_state = await get_body_state(person_id)
    summary = body_state.get("summary", {})

    # Translate to friendly language
    translated = translate_body_state(body_state)

    return {
        "person_id": person_id,
        "primary_need": translated.get("primary_need"),
        "overall_status": translated.get("overall_status"),
        "dosha_status": translated.get("dosha_status"),
        "recommendations": translated.get("recommendations", []),
        "confidence": summary.get("confidence", 0),
    }


# === Helper Functions ===


async def _trigger_body_refresh(person_id: str) -> None:
    """Trigger body refresh worker for a person."""
    from sakhi.apps.worker.tasks.body_refresh import run_body_refresh

    try:
        await run_body_refresh(person_id)
    except Exception as e:
        # Log but don't fail the request
        import logging
        logging.error(f"[health] Body refresh failed for {person_id}: {e}")


__all__ = ["router"]
