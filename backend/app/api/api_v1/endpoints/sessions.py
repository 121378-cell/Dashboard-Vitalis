"""
Dashboard-Vitalis — Sessions API Endpoints
===========================================

Endpoints REST para gestión de sesiones de entrenamiento.

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

import json
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.models.session import TrainingSession, WeeklyReport
from app.services.session_service import SessionService

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class SetData(BaseModel):
    set_number: int
    reps: int
    weight_kg: float
    rpe_target: float
    rest_seconds: int
    tempo: str
    notes: str = ""


class ExerciseData(BaseModel):
    name: str
    muscle_group: str
    sets: List[SetData]


class SessionPlan(BaseModel):
    session_name: str
    estimated_duration_min: int
    warmup: str
    exercises: List[ExerciseData]
    cooldown: str
    coach_notes: str


class ActualSetData(BaseModel):
    set_number: int
    reps: int
    weight_kg: float
    rpe_target: float
    rpe_real: Optional[float] = None
    rest_seconds: int
    tempo: str
    status: str = "pending"  # pending/completed/partial/failed
    notes: str = ""


class ActualExerciseData(BaseModel):
    name: str
    muscle_group: str
    sets: List[ActualSetData]


class SaveSessionRequest(BaseModel):
    actual_data: List[ActualExerciseData]


class SessionResponse(BaseModel):
    id: str
    user_id: str
    date: str
    status: str
    generated_by: str
    plan: Optional[dict] = None
    actual: Optional[dict] = None
    session_report: Optional[str] = None
    garmin_activity_id: Optional[str] = None
    garmin_hr_avg: Optional[float] = None
    garmin_hr_max: Optional[float] = None
    garmin_calories: Optional[int] = None
    garmin_duration_min: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WeeklyReportResponse(BaseModel):
    id: str
    user_id: str
    week_start: str
    week_end: str
    report_text: Optional[str] = None
    metrics: Optional[dict] = None
    next_week_plan: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ShouldTrainResponse(BaseModel):
    train: bool
    reason: str
    suggested_type: str
    readiness: float


class GenerateSessionResponse(BaseModel):
    session_id: str
    date: str
    status: str
    plan: dict
    should_train: ShouldTrainResponse
    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=GenerateSessionResponse)
def generate_session(
    target_date: Optional[str] = None,
    force_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Genera una sesión de entrenamiento para hoy (o fecha indicada).
    Si ya existe sesión para la fecha, la devuelve sin regenerar.
    """
    # Determinar fecha objetivo
    if target_date:
        try:
            session_date = datetime.fromisoformat(target_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    else:
        session_date = date.today()
    
    date_str = session_date.isoformat()
    
    # Verificar si ya existe sesión para esta fecha
    existing = db.query(TrainingSession).filter(
        TrainingSession.user_id == user_id,
        TrainingSession.date == date_str
    ).first()
    
    if existing:
        # Devolver sesión existente
        plan = json.loads(existing.plan_json) if existing.plan_json else {}
        should_train = SessionService.should_train_today(user_id, db)
        
        return GenerateSessionResponse(
            session_id=existing.id,
            date=date_str,
            status=existing.status,
            plan=plan,
            should_train=ShouldTrainResponse(**should_train),
            message="Sesión existente recuperada"
        )
    
    # Decidir si debe entrenar hoy
    should_train = SessionService.should_train_today(user_id, db)
    
    # Generar plan
    plan_data = SessionService.generate_session_plan(
        user_id, db, session_date, force_type=force_type
    )
    
    # Crear sesión en BD
    session = TrainingSession(
        user_id=user_id,
        date=date_str,
        status="planned",
        generated_by="atlas",
        plan_json=json.dumps(plan_data)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return GenerateSessionResponse(
        session_id=session.id,
        date=date_str,
        status="planned",
        plan=plan_data,
        should_train=ShouldTrainResponse(**should_train),
        message="Nueva sesión generada" if should_train["train"] else "Sesión de recuperación generada"
    )


@router.get("/today", response_model=Optional[SessionResponse])
def get_today_session(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Devuelve la sesión de hoy si existe.
    Incluye status: planned/active/completed
    """
    today_str = date.today().isoformat()
    
    session = db.query(TrainingSession).filter(
        TrainingSession.user_id == user_id,
        TrainingSession.date == today_str
    ).first()
    
    if not session:
        return None
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        date=session.date,
        status=session.status,
        generated_by=session.generated_by,
        plan=json.loads(session.plan_json) if session.plan_json else None,
        actual=json.loads(session.actual_json) if session.actual_json else None,
        session_report=session.session_report,
        garmin_activity_id=session.garmin_activity_id,
        garmin_hr_avg=session.garmin_hr_avg,
        garmin_hr_max=session.garmin_hr_max,
        garmin_calories=session.garmin_calories,
        garmin_duration_min=session.garmin_duration_min,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Devuelve el detalle completo de una sesión específica.
    """
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id,
        TrainingSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        date=session.date,
        status=session.status,
        generated_by=session.generated_by,
        plan=json.loads(session.plan_json) if session.plan_json else None,
        actual=json.loads(session.actual_json) if session.actual_json else None,
        session_report=session.session_report,
        garmin_activity_id=session.garmin_activity_id,
        garmin_hr_avg=session.garmin_hr_avg,
        garmin_hr_max=session.garmin_hr_max,
        garmin_calories=session.garmin_calories,
        garmin_duration_min=session.garmin_duration_min,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/{session_id}/save", response_model=SessionResponse)
def save_session(
    session_id: str,
    request: SaveSessionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Guarda los datos reales de la sesión (RPE reales, pesos, estados).
    Cambia status a "completed" y dispara análisis post-sesión.
    """
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id,
        TrainingSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="La sesión ya está completada y no puede modificarse")
    
    # Convertir actual_data a formato para guardar
    actual_dict = {
        "exercises": [
            {
                "name": ex.name,
                "muscle_group": ex.muscle_group,
                "sets": [
                    {
                        "set_number": s.set_number,
                        "reps": s.reps,
                        "weight_kg": s.weight_kg,
                        "rpe_target": s.rpe_target,
                        "rpe_real": s.rpe_real,
                        "rest_seconds": s.rest_seconds,
                        "tempo": s.tempo,
                        "status": s.status,
                        "notes": s.notes
                    }
                    for s in ex.sets
                ]
            }
            for ex in request.actual_data
        ]
    }
    
    # Actualizar sesión
    session.actual_json = json.dumps(actual_dict)
    session.status = "completed"
    session.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    # Disparar análisis automático
    try:
        report = SessionService.analyze_session(session_id, db)
        session.session_report = report
        db.commit()
    except Exception as e:
        # No fallar si el análisis da error
        pass
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        date=session.date,
        status=session.status,
        generated_by=session.generated_by,
        plan=json.loads(session.plan_json) if session.plan_json else None,
        actual=json.loads(session.actual_json) if session.actual_json else None,
        session_report=session.session_report,
        garmin_activity_id=session.garmin_activity_id,
        garmin_hr_avg=session.garmin_hr_avg,
        garmin_hr_max=session.garmin_hr_max,
        garmin_calories=session.garmin_calories,
        garmin_duration_min=session.garmin_duration_min,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/{session_id}/analyze", response_model=dict)
def analyze_session_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Genera el informe de la sesión con ATLAS.
    Vincula datos de Garmin si hay actividad del mismo día.
    """
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id,
        TrainingSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if not session.actual_json:
        raise HTTPException(status_code=400, detail="La sesión no tiene datos reales para analizar")
    
    # Generar informe
    try:
        report = SessionService.analyze_session(session_id, db)
        session.session_report = report
        db.commit()
        
        return {
            "session_id": session_id,
            "report": report,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando informe: {str(e)}")


@router.get("/history", response_model=List[SessionResponse])
def get_session_history(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Historial de sesiones de entrenamiento.
    Parámetro 'days' especifica cuántos días hacia atrás consultar (default: 30).
    """
    cutoff_date = (date.today() - timedelta(days=days)).isoformat()
    
    sessions = db.query(TrainingSession).filter(
        TrainingSession.user_id == user_id,
        TrainingSession.date >= cutoff_date
    ).order_by(TrainingSession.date.desc()).all()
    
    return [
        SessionResponse(
            id=s.id,
            user_id=s.user_id,
            date=s.date,
            status=s.status,
            generated_by=s.generated_by,
            plan=json.loads(s.plan_json) if s.plan_json else None,
            actual=json.loads(s.actual_json) if s.actual_json else None,
            session_report=s.session_report,
            garmin_activity_id=s.garmin_activity_id,
            garmin_hr_avg=s.garmin_hr_avg,
            garmin_hr_max=s.garmin_hr_max,
            garmin_calories=s.garmin_calories,
            garmin_duration_min=s.garmin_duration_min,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.post("/weekly-report/generate", response_model=WeeklyReportResponse)
def generate_weekly_report(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Genera el informe semanal.
    Analiza todas las sesiones + biométricos de la semana.
    Genera plan para la semana siguiente.
    """
    # Generar informe
    report_data = SessionService.generate_weekly_report(user_id, db)
    
    # Guardar en BD
    weekly_report = WeeklyReport(
        user_id=user_id,
        week_start=report_data["week_start"],
        week_end=report_data["week_end"],
        report_text=report_data["report_text"],
        metrics_json=json.dumps(report_data["metrics"]),
        next_week_plan=json.dumps(report_data["next_week_plan"])
    )
    
    db.add(weekly_report)
    db.commit()
    db.refresh(weekly_report)
    
    return WeeklyReportResponse(
        id=weekly_report.id,
        user_id=weekly_report.user_id,
        week_start=weekly_report.week_start,
        week_end=weekly_report.week_end,
        report_text=weekly_report.report_text,
        metrics=json.loads(weekly_report.metrics_json) if weekly_report.metrics_json else None,
        next_week_plan=json.loads(weekly_report.next_week_plan) if weekly_report.next_week_plan else None,
        created_at=weekly_report.created_at
    )


@router.get("/weekly-report/latest", response_model=Optional[WeeklyReportResponse])
def get_latest_weekly_report(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Devuelve el último informe semanal disponible.
    """
    report = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == user_id
    ).order_by(WeeklyReport.week_start.desc()).first()
    
    if not report:
        return None
    
    return WeeklyReportResponse(
        id=report.id,
        user_id=report.user_id,
        week_start=report.week_start,
        week_end=report.week_end,
        report_text=report.report_text,
        metrics=json.loads(report.metrics_json) if report.metrics_json else None,
        next_week_plan=json.loads(report.next_week_plan) if report.next_week_plan else None,
        created_at=report.created_at
    )


@router.get("/should-train/today", response_model=ShouldTrainResponse)
def should_train_today(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Consulta si hoy es día de entreno según readiness y patrón histórico.
    """
    result = SessionService.should_train_today(user_id, db)
    return ShouldTrainResponse(**result)
