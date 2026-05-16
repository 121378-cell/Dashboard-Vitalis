"""
ATLAS Interventions API
=======================

Endpoints REST para gestionar intervenciones proactivas del sistema.

Autor: ATLAS Team
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user_id
from app.services.intervention_service import InterventionService
from app.services.intervention_outcome_service import InterventionOutcomeService
from app.db.session import SessionLocal
from app.models.atlas_intervention import AtlasIntervention

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InterventionResponse(BaseModel):
    id: int
    intervention_type: str
    autonomy_level: str
    title: str
    message: str
    priority: str
    status: str
    created_at: str
    responded_at: Optional[str] = None
    executed_at: Optional[str] = None
    decision_deadline: Optional[str] = None
    response: Optional[str] = None
    outcome_score: Optional[float] = None
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class InterventionStatsResponse(BaseModel):
    total: int
    pending: int
    accepted: int
    rejected: int
    acceptance_rate: float


class RespondRequest(BaseModel):
    response: str  # accepted, rejected, snoozed
    response_data: Optional[dict] = None


class TriggerInterventionRequest(BaseModel):
    intervention_type: str
    message: Optional[str] = None
    payload: Optional[dict] = None


class OutcomeStatsResponse(BaseModel):
    total: int
    by_type: list[dict]
    avg_score: Optional[float] = None
    acceptance_rate: Optional[float] = None
    outcome_distribution: dict

    class Config:
        # Permitir alias opcional para compatibilidad con frontend
        from_attributes = True


class BestChannelResponse(BaseModel):
    best_channel: str
    scores_by_channel: dict
    confidence: float
    sample_size: int

    class Config:
        from_attributes = True


class BestTimingResponse(BaseModel):
    best_timing: str
    scores_by_timing: dict
    confidence: float
    sample_size: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _intervention_to_dict(intervention) -> dict:
    """Convierte un modelo de intervención a dict para respuesta."""
    return {
        "id": intervention.id,
        "intervention_type": intervention.intervention_type,
        "autonomy_level": intervention.autonomy_level,
        "title": intervention.title,
        "message": intervention.message,
        "priority": intervention.priority,
        "status": intervention.status,
        "created_at": (
            intervention.created_at.isoformat()
            if intervention.created_at else None
        ),
        "responded_at": (
            intervention.responded_at.isoformat()
            if intervention.responded_at else None
        ),
        "executed_at": (
            intervention.executed_at.isoformat()
            if intervention.executed_at else None
        ),
        "decision_deadline": (
            intervention.decision_deadline.isoformat()
            if intervention.decision_deadline else None
        ),
        "response": intervention.response,
        "outcome_score": intervention.outcome_score,
        "metadata": intervention.extra_data,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[InterventionResponse])
def list_interventions(
    days: int = Query(default=30, ge=1, le=365),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    skip: int = Query(default=0, ge=0, description="Results to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Historial de intervenciones del usuario."""
    interventions = InterventionService.get_history(
        user_id, days=days, status_filter=status,
        skip=skip, limit=limit,
    )
    return [_intervention_to_dict(i) for i in interventions]


@router.get("/pending", response_model=list[InterventionResponse])
def list_pending(
    skip: int = Query(default=0, ge=0, description="Results to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Intervenciones pendientes (no expiradas)."""
    interventions = InterventionService.get_pending(
        user_id, skip=skip, limit=limit,
    )
    return [_intervention_to_dict(i) for i in interventions]


@router.get("/active", response_model=list[InterventionResponse])
def list_active(
    skip: int = Query(default=0, ge=0, description="Results to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Intervenciones activas de los últimos 7 días."""
    interventions = InterventionService.get_active(
        user_id, skip=skip, limit=limit,
    )
    return [_intervention_to_dict(i) for i in interventions]


@router.get("/stats", response_model=InterventionStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Estadísticas de intervenciones."""
    return InterventionService.get_stats(user_id)


@router.get("/outcome-stats", response_model=OutcomeStatsResponse)
def get_outcome_stats(
    intervention_type: Optional[str] = Query(default=None, description="Filter by intervention type"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Estadísticas de efectividad de intervenciones (outcome scores)."""
    return InterventionOutcomeService.get_outcome_stats(
        user_id=user_id,
        intervention_type=intervention_type,
        db=db,
    )


@router.get("/outcome-stats/best-channel", response_model=BestChannelResponse)
def get_best_channel(
    intervention_type: str = Query(..., description="Intervention type to analyze"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Mejor canal de entrega para un tipo de intervención basado en outcomes históricos."""
    return InterventionOutcomeService.get_best_channel(
        user_id=user_id,
        intervention_type=intervention_type,
        db=db,
    )


@router.get("/outcome-stats/best-timing", response_model=BestTimingResponse)
def get_best_timing(
    intervention_type: str = Query(..., description="Intervention type to analyze"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Mejor franja horaria para un tipo de intervención basado en outcomes históricos."""
    return InterventionOutcomeService.get_best_timing(
        user_id=user_id,
        intervention_type=intervention_type,
        db=db,
    )


@router.post("/respond/{intervention_id}")
def respond_to_intervention(
    intervention_id: int,
    request: RespondRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Responder a una intervención (accept/reject/snooze)."""
    success = InterventionService.respond_to_intervention(
        intervention_id=intervention_id,
        user_id=user_id,
        response=request.response,
        response_data=request.response_data,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="No se pudo procesar la respuesta. "
                   "Verifica que la intervención existe y está pendiente.",
        )

    return {"message": f"Intervención {request.response}"}


@router.post("/trigger")
def trigger_intervention(
    request: TriggerInterventionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Activar manualmente una intervención (para testing o solicitud del usuario)."""
    from app.core.autonomy_policy import InterventionType

    try:
        itype = InterventionType[request.intervention_type.upper()]
    except KeyError:
        valid = [t.name for t in InterventionType]
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de intervención inválido. Válidos: {', '.join(valid)}",
        )

    intervention = InterventionService.create_intervention(
        user_id=user_id,
        intervention_type=itype,
        custom_message=request.message,
        payload=request.payload,
    )

    if not intervention:
        raise HTTPException(
            status_code=400,
            detail="No se pudo crear la intervención "
                   "(quizás está en cooldown o bloqueada por autonomía).",
        )

    return _intervention_to_dict(intervention)


@router.get("/{intervention_id}", response_model=InterventionResponse)
def get_intervention(
    intervention_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Detalle de una intervención específica."""
    with SessionLocal() as sess:
        intervention = sess.query(AtlasIntervention).filter(
            AtlasIntervention.id == intervention_id,
            AtlasIntervention.user_id == user_id,
        ).first()

    if not intervention:
        raise HTTPException(status_code=404, detail="Intervención no encontrada")

    return _intervention_to_dict(intervention)


@router.delete("/{intervention_id}")
def delete_intervention(
    intervention_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Eliminar una intervención."""
    success = InterventionService.delete_intervention(
        intervention_id=intervention_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Intervención no encontrada",
        )

    return {"message": "Intervención eliminada"}
