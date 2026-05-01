"""
ATLAS Training Planner API Endpoints
=====================================

REST API para el sistema de planificación de entrenamientos inteligente.

Rutas:
- POST /generate-week           → Genera plan semanal completo
- GET  /current-week            → Plan activo de la semana
- POST /complete-session        → Marcar sesión como completada + datos reales
- POST /skip-session            → Omitir sesión (reprograma al día siguiente)
- GET  /personal-records        → Todos los PRs del atleta
- POST /update-pr               → Actualizar PR manualmente
- GET  /weekly-stats            → Estadísticas semanales
- POST /reschedule-session      → Reprogramar sesión a otro día

Autor: ATLAS Team
Version: 2.0.0
"""

import json
from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.models.training_plan import WeeklyPlan, PlanSession, PersonalRecord
from app.services.planner_service import TrainingPlannerService
from app.services.readiness_service import ReadinessService

router = APIRouter()


class CompleteSessionRequest(BaseModel):
    session_id: int
    actual_data: dict = Field(..., description='{"exercises": [{name, sets, reps, weight, rpe, ...}]}')


class SkipSessionRequest(BaseModel):
    session_id: int
    reason: Optional[str] = None


class UpdatePRRequest(BaseModel):
    exercise_name: str
    weight: int
    reps: int
    rpe: Optional[int] = None
    notes: Optional[str] = None


class RescheduleSessionRequest(BaseModel):
    session_id: int
    new_date: str = Field(..., description="YYYY-MM-DD")


@router.post("/generate-week", summary="Genera plan semanal completo")
async def generate_weekly_plan(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        plan = await TrainingPlannerService.generate_weekly_plan(db, user_id)
        return {
            "status": "success",
            "data": plan,
            "message": "Weekly training plan generated successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating plan: {str(e)}",
        )


@router.get("/current-week", summary="Plan activo de la semana")
async def get_current_week(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today = date.today().isoformat()

    plan = (
        db.query(WeeklyPlan)
        .filter(
            WeeklyPlan.user_id == user_id,
            WeeklyPlan.status == "active",
            WeeklyPlan.week_start <= today,
            WeeklyPlan.week_end >= today,
        )
        .first()
    )

    if not plan:
        plan = (
            db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.user_id == user_id,
                WeeklyPlan.status == "archived",
            )
            .order_by(WeeklyPlan.week_end.desc())
            .first()
        )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No training plan found. Generate one first.",
        )

    sessions = (
        db.query(PlanSession)
        .filter(PlanSession.plan_id == plan.id)
        .order_by(PlanSession.day_index)
        .all()
    )

    readiness_forecast = ReadinessService.get_forecast(db, user_id, days=7)

    readiness_by_date = {}
    for r in readiness_forecast:
        readiness_by_date[r["date"]] = r.get("score", 50)

    sessions_data = []
    for s in sessions:
        readiness_score = readiness_by_date.get(s.scheduled_date, None)
        sessions_data.append(
            {
                "id": s.id,
                "day": s.day_index,
                "day_name": s.day_name,
                "scheduled_date": s.scheduled_date,
                "exercises": s.exercises_data,
                "completed": s.completed,
                "actual_data": s.actual_data,
                "skipped": s.skipped,
                "notes": s.notes,
                "readiness_score": readiness_score,
            }
        )

    return {
        "status": "success",
        "data": {
            "id": plan.id,
            "user_id": plan.user_id,
            "week_start": plan.week_start,
            "week_end": plan.week_end,
            "generated_at": plan.generated_at.isoformat(),
            "status": plan.status,
            "objective": plan.objective,
            "sessions": sessions_data,
            "plan_data": plan.plan_data,
        },
    }


@router.post("/complete-session", summary="Marcar sesión como completada")
async def complete_session(
    request: CompleteSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(PlanSession).filter(PlanSession.id == request.session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    session.completed = True
    session.completed_at = date.today()
    session.actual_data = request.actual_data

    new_prs = []

    for ex_actual in request.actual_data.get("exercises", []):
        ex_name = ex_actual.get("name", "").lower()
        weight = ex_actual.get("weight", 0)
        reps = ex_actual.get("reps", 0)
        rpe = ex_actual.get("rpe", 0)

        if weight <= 0 or reps <= 0:
            continue

        existing_pr = (
            db.query(PersonalRecord)
            .filter(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_name.ilike(ex_name),
            )
            .order_by(PersonalRecord.weight.desc(), PersonalRecord.reps.desc())
            .first()
        )

        is_new_pr = False
        if existing_pr:
            if weight > existing_pr.weight or (
                weight == existing_pr.weight and reps > existing_pr.reps
            ):
                is_new_pr = True
                previous_weight = existing_pr.weight
                existing_pr.weight = weight
                existing_pr.reps = reps
                existing_pr.rpe = rpe
                existing_pr.date = date.today().isoformat()
                existing_pr.source = "workout"
                existing_pr.session_id = request.session_id
                new_prs.append(
                    {
                        "exercise": ex_name,
                        "weight": weight,
                        "reps": reps,
                        "previous_weight": previous_weight,
                        "previous_reps": existing_pr.reps,
                        "type": (
                            "weight_increase"
                            if weight > previous_weight
                            else "reps_increase"
                        ),
                    }
                )
        else:
            new_pr = PersonalRecord(
                user_id=user_id,
                exercise_name=ex_name,
                weight=weight,
                reps=reps,
                rpe=rpe,
                date=date.today().isoformat(),
                source="workout",
                session_id=request.session_id,
                notes="First recorded PR",
            )
            db.add(new_pr)
            db.flush()
            new_prs.append(
                {"exercise": ex_name, "weight": weight, "reps": reps, "type": "first_pr"}
            )
            is_new_pr = True

        if is_new_pr:
            from app.services.memory_service import MemoryService

            MemoryService.add_memory(
                db,
                user_id,
                memory_type="achievement",
                content=f"Nuevo record personal: {ex_name} - {weight}kg x {reps} reps",
                importance=9,
                source="workout",
                tags=["pr", "strength", ex_name],
            )

    db.commit()

    return {
        "status": "success",
        "data": {
            "session_id": session.id,
            "completed": True,
            "completed_at": session.completed_at.isoformat(),
            "new_personal_records": new_prs,
        },
        "message": "Session completed successfully",
    }


@router.post("/skip-session", summary="Omitir sesión de entrenamiento")
async def skip_session(
    request: SkipSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(PlanSession).filter(PlanSession.id == request.session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    session.skipped = True
    session.notes = request.reason or "Skipped by user request"

    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == session.plan_id).first()

    if plan:
        next_available = _find_next_available_day(db, plan, session.day_index)
        if next_available:
            rescheduled = PlanSession(
                plan_id=plan.id,
                day_index=next_available["day_index"],
                day_name=session.day_name + " (reprogramada)",
                scheduled_date=next_available["date"],
                exercises_data=session.exercises_data,
                notes="Reprogramada tras omitir sesion anterior",
            )
            db.add(rescheduled)

    db.commit()

    return {
        "status": "success",
        "data": {
            "session_id": session.id,
            "skipped": True,
            "notes": session.notes,
        },
        "message": "Session skipped and rescheduled",
    }


@router.post("/reschedule-session", summary="Reprogramar sesión a otro dia")
async def reschedule_session(
    request: RescheduleSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(PlanSession).filter(PlanSession.id == request.session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    old_date = session.scheduled_date
    session.scheduled_date = request.new_date
    session.notes = f"Reprogramada de {old_date} a {request.new_date}"

    db.commit()

    return {
        "status": "success",
        "data": {
            "session_id": session.id,
            "old_date": old_date,
            "new_date": request.new_date,
        },
        "message": "Session rescheduled",
    }


@router.get("/personal-records", summary="Todos los PRs del atleta")
async def get_personal_records(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    prs = (
        db.query(PersonalRecord)
        .filter(PersonalRecord.user_id == user_id)
        .order_by(PersonalRecord.date.desc())
        .all()
    )

    grouped = {}
    for pr in prs:
        if pr.exercise_name not in grouped:
            grouped[pr.exercise_name] = []
        grouped[pr.exercise_name].append(
            {
                "id": pr.id,
                "weight": pr.weight,
                "reps": pr.reps,
                "rpe": pr.rpe,
                "date": pr.date,
                "source": pr.source,
                "notes": pr.notes,
            }
        )

    current_prs = {}
    for ex_name, pr_list in grouped.items():
        current_prs[ex_name] = pr_list[0]

    return {
        "status": "success",
        "data": {
            "personal_records": current_prs,
            "total_exercises": len(current_prs),
            "all_records": grouped,
        },
    }


@router.post("/update-pr", summary="Actualizar PR manualmente")
async def update_pr(
    request: UpdatePRRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_pr = (
        db.query(PersonalRecord)
        .filter(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_name.ilike(request.exercise_name),
        )
        .order_by(PersonalRecord.weight.desc(), PersonalRecord.reps.desc())
        .first()
    )

    if existing_pr:
        existing_pr.weight = request.weight
        existing_pr.reps = request.reps
        existing_pr.rpe = request.rpe
        existing_pr.date = date.today().isoformat()
        existing_pr.source = "manual"
        existing_pr.notes = request.notes or existing_pr.notes
        pr = existing_pr
    else:
        pr = PersonalRecord(
            user_id=user_id,
            exercise_name=request.exercise_name,
            weight=request.weight,
            reps=request.reps,
            rpe=request.rpe,
            date=date.today().isoformat(),
            source="manual",
            notes=request.notes,
        )
        db.add(pr)

    db.commit()
    db.refresh(pr)

    return {
        "status": "success",
        "data": {
            "id": pr.id,
            "exercise_name": pr.exercise_name,
            "weight": pr.weight,
            "reps": pr.reps,
            "rpe": pr.rpe,
            "date": pr.date,
            "source": pr.source,
            "notes": pr.notes,
        },
        "message": "Personal record updated",
    }


@router.get("/weekly-stats", summary="Estadisticas semanales")
async def get_weekly_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    sessions = (
        db.query(PlanSession)
        .join(WeeklyPlan)
        .filter(
            WeeklyPlan.user_id == user_id,
            PlanSession.scheduled_date >= week_start.isoformat(),
            PlanSession.scheduled_date <= week_end.isoformat(),
        )
        .all()
    )

    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.completed)
    skipped_sessions = sum(1 for s in sessions if s.skipped)

    total_duration = 0
    total_exercises = 0
    for s in sessions:
        if s.actual_data:
            for ex in s.actual_data.get("exercises", []):
                total_exercises += 1
                sets = ex.get("sets", 3)
                total_duration += sets * 3

    return {
        "status": "success",
        "data": {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "skipped_sessions": skipped_sessions,
            "completion_rate": (
                round(completed_sessions / total_sessions * 100, 1)
                if total_sessions > 0
                else 0
            ),
            "total_duration_minutes": total_duration,
            "total_exercises": total_exercises,
        },
    }


def _find_next_available_day(
    db: Session, plan: WeeklyPlan, after_day_index: int
) -> Optional[dict]:
    existing_sessions = (
        db.query(PlanSession)
        .filter(PlanSession.plan_id == plan.id)
        .all()
    )
    scheduled_days = {s.day_index for s in existing_sessions}

    week_start = date.fromisoformat(plan.week_start)

    for day_offset in range(after_day_index + 1, 7):
        if day_offset not in scheduled_days:
            return {
                "day_index": day_offset,
                "date": (week_start + timedelta(days=day_offset)).isoformat(),
            }

    for day_offset in range(0, after_day_index):
        if day_offset not in scheduled_days:
            return {
                "day_index": day_offset,
                "date": (week_start + timedelta(days=day_offset)).isoformat(),
            }

    return None
