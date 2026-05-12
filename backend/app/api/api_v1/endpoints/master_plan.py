import json
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.services.master_plan_service import MasterPlanService
from app.models.master_plan import MasterPlan

router = APIRouter()


class CreateMasterPlanRequest(BaseModel):
    goal: str = Field(..., description="Descripción del objetivo final")
    target_date: Optional[str] = Field(None, description="Fecha límite YYYY-MM-DD (null = plan continuo)")
    preferred_days: List[str] = Field(["monday", "tuesday", "thursday", "friday", "saturday"], description="Días preferidos")
    time_per_session_minutes: int = Field(60, description="Minutos por sesión")
    intensity_preference: Optional[str] = Field(None, description="low/medium/high/atlas_decides")
    restrictions: Optional[str] = Field(None, description="Lesiones o restricciones")


@router.post("/create")
def create_master_plan_endpoint(
    request: CreateMasterPlanRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        parsed_target_date = None
        if request.target_date:
            parsed_target_date = date.fromisoformat(request.target_date)

        result = MasterPlanService.create_master_plan(
            db=db,
            user_id=user_id,
            goal=request.goal,
            target_date=parsed_target_date,
            preferred_days=request.preferred_days,
            time_per_session_minutes=request.time_per_session_minutes,
            intensity_preference=request.intensity_preference,
            restrictions=request.restrictions,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/active")
def get_active_master_plan_endpoint(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = MasterPlanService.get_active_master_plan(db=db, user_id=user_id)
    if result is None:
        return {"status": "success", "has_plan": False, "message": "No hay plan maestro activo"}
    return {"status": "success", "has_plan": True, "data": result}


@router.get("/{master_plan_id}/progress")
def get_master_plan_progress_endpoint(
    master_plan_id: int,
    db: Session = Depends(get_db),
):
    result = MasterPlanService.get_master_plan_progress(db=db, master_plan_id=master_plan_id)
    return {"status": "success", "data": result}


@router.post("/{master_plan_id}/propose-next-week")
def propose_next_week_endpoint(
    master_plan_id: int,
    db: Session = Depends(get_db),
):
    result = MasterPlanService.propose_next_week(db=db, master_plan_id=master_plan_id)
    return {"status": "success", "data": result}


@router.post("/weeks/{weekly_plan_id}/confirm")
def confirm_week_endpoint(
    weekly_plan_id: int,
    db: Session = Depends(get_db),
):
    result = MasterPlanService.confirm_week(db=db, weekly_plan_id=weekly_plan_id)
    return {"status": "success", "data": result, "message": "Semana confirmada"}


@router.delete("/{master_plan_id}")
def cancel_master_plan_endpoint(
    master_plan_id: int,
    db: Session = Depends(get_db),
):
    plan = db.query(MasterPlan).filter(MasterPlan.id == master_plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan maestro no encontrado",
        )
    plan.status = "cancelled"
    db.commit()
    return {"status": "success", "message": "Plan cancelado"}
