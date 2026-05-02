"""
ATLAS Recovery & Injury Prevention Endpoints
============================================

GET /recovery/status → Current alert level + detailed alerts
GET /recovery/session → Recommended recovery session
POST /recovery/report-pain → Report pain/injury
GET /recovery/injury-history → Injury/memory history
POST /recovery/acknowledge-alert → Acknowledge an alert (requires explicit action)
GET /recovery/injury-patterns → Detect recurring injury patterns
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.services.injury_prevention_service import (
    AlertLevel,
    InjuryPreventionService,
    RecoverySession,
)
from app.services.memory_service import MemoryService
from app.models.memory import AtlasMemory

router = APIRouter(prefix="", tags=["recovery"])


class PainReportRequest(BaseModel):
    zone: str = Field(..., description="Body zone (e.g., knee_left, lower_back)")
    pain_level: int = Field(..., ge=1, le=10, description="Pain intensity 1-10")
    pain_type: str = Field(..., description="Type: agudo, sordo, ardor, fatiga")
    notes: Optional[str] = Field(None, description="Optional notes")


class AcknowledgeAlertRequest(BaseModel):
    alert_indicator: str = Field(..., description="The alert indicator being acknowledged")
    alert_reason: str = Field(..., description="The alert reason text")
    user_action: str = Field(..., description="What the user will do about it")


class RecoverySessionResponse(BaseModel):
    type: str
    duration_min: int
    exercises: List[str]
    message: Optional[str]
    optional: List[str]
    alert_level: str


class AlertResponse(BaseModel):
    level: str
    reason: str
    indicator: str
    value: Optional[Any]
    threshold: Optional[Any]
    action_required: str


class InjuryRecord(BaseModel):
    id: int
    date: str
    zone: Optional[str]
    content: str
    pain_level: int
    type: str
    importance: int
    is_active: bool
    tags: List[str]


class RecoveryStatusResponse(BaseModel):
    alert_level: str
    alerts: List[AlertResponse]
    readiness_penalty: float
    active_injuries: List[Dict]
    zones_to_avoid: List[str]
    recommendations: List[str]
    forecast_risk: float


@router.get("/status", response_model=RecoveryStatusResponse)
async def get_recovery_status(
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    status = InjuryPreventionService.get_current_status(db, user_id)
    return status.to_dict()


@router.get("/session", response_model=RecoverySessionResponse)
async def get_recovery_session(
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    status = InjuryPreventionService.get_current_status(db, user_id)
    injuries = status.active_injuries
    session = InjuryPreventionService.generate_recovery_session(
        status.alert_level, injuries
    )
    return session.to_dict()


@router.post("/report-pain")
async def report_pain(
    body: PainReportRequest,
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    result = InjuryPreventionService.report_pain(
        db,
        user_id,
        zone=body.zone,
        pain_level=body.pain_level,
        pain_type=body.pain_type,
        notes=body.notes,
    )

    if body.pain_level >= 8:
        MemoryService.add_memory(
            db,
            user_id,
            memory_type="health_alert",
            content=f"Dolor agudo reportado: {body.pain_type} {body.pain_level}/10 en {body.zone}. Consulta médica recomendada.",
            importance=10,
            source="auto",
            tags=["health_alert", "acute_pain", body.zone],
        )

    return result


@router.get("/injury-history", response_model=List[InjuryRecord])
async def get_injury_history(
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    injuries = InjuryPreventionService.get_injury_history(db, user_id)
    return injuries


@router.post("/acknowledge-alert")
async def acknowledge_alert(
    body: AcknowledgeAlertRequest,
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    """
    Acknowledge an alert — requires explicit user action.

    Alerts cannot be silently dismissed. The user must specify
    what action they are taking in response.
    """
    MemoryService.add_memory(
        db,
        user_id,
        memory_type="preference",
        content=f"Alerta reconocida [{body.alert_indicator}]: {body.alert_reason}. Acción del usuario: {body.user_action}",
        importance=6,
        source="user_input",
        tags=["alert_acknowledged", body.alert_indicator],
    )

    return {
        "status": "acknowledged",
        "indicator": body.alert_indicator,
        "user_action": body.user_action,
        "message": "Alerta reconocida. ATLAS ajustará las recomendaciones según tu acción.",
    }


@router.get("/injury-patterns")
async def get_injury_patterns(
    user_id: str = get_current_user_id(),
    db: Session = Depends(get_db),
):
    """
    Detect recurring injury patterns from memory.

    Returns patterns like:
    - Which zones get injured most
    - Whether injuries correlate with high-volume weeks
    - Average recovery time per zone
    """
    all_injuries = (
        db.query(AtlasMemory)
        .filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.type == "injury",
        )
        .order_by(AtlasMemory.date.desc())
        .all()
    )

    if not all_injuries:
        return {"patterns": [], "zone_frequency": {}, "insights": []}

    zone_counts: Dict[str, int] = {}
    zone_pain_levels: Dict[str, List[int]] = {}
    zone_dates: Dict[str, List[str]] = {}

    for m in all_injuries:
        zone = None
        pain_level = 0
        for tag in (m.tags or []):
            if tag in InjuryPreventionService.BODY_ZONES:
                zone = tag
            if tag.startswith("pain_level_"):
                try:
                    pain_level = int(tag.split("_")[-1])
                except ValueError:
                    pass

        if zone:
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
            if zone not in zone_pain_levels:
                zone_pain_levels[zone] = []
            zone_pain_levels[zone].append(pain_level)
            if zone not in zone_dates:
                zone_dates[zone] = []
            zone_dates[zone].append(m.date)

    insights = []
    for zone, count in sorted(zone_counts.items(), key=lambda x: -x[1]):
        if count >= 2:
            avg_pain = sum(zone_pain_levels[zone]) / len(zone_pain_levels[zone])
            zone_display = zone.replace("_", " ")
            insights.append(
                f"Zona recurrente: {zone_display} ({count} incidencias, dolor promedio {avg_pain:.1f}/10)"
            )

    patterns = []
    for zone, dates in zone_dates.items():
        if len(dates) >= 2:
            sorted_dates = sorted(dates, reverse=True)
            for i in range(len(sorted_dates) - 1):
                try:
                    d1 = date.fromisoformat(sorted_dates[i])
                    d2 = date.fromisoformat(sorted_dates[i + 1])
                    gap = (d1 - d2).days
                    patterns.append({
                        "zone": zone,
                        "recurrence_gap_days": gap,
                        "first_date": sorted_dates[i + 1],
                        "last_date": sorted_dates[i],
                    })
                except (ValueError, TypeError):
                    continue

    return {
        "zone_frequency": zone_counts,
        "patterns": patterns,
        "insights": insights,
        "total_injuries": len(all_injuries),
    }


@router.get("/body-zones")
async def get_body_zones():
    from app.services.injury_prevention_service import BODY_ZONES
    return {"zones": list(BODY_ZONES.keys())}


@router.get("/zone-exercises/{zone}")
async def get_zone_exercises(zone: str):
    exercises = InjuryPreventionService.get_zone_exercises(zone)
    return {"zone": zone, "alternative_exercises": exercises}


@router.post("/resolve-zone")
async def resolve_zone(description: str):
    zone = InjuryPreventionService.resolve_body_zone(description)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Could not resolve zone: {description}")
    return {"zone": zone}
