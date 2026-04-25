from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from app.api.deps import get_db, get_current_user_id
from app.models.biometrics import Biometrics
from app.models.workout import Workout
import json

router = APIRouter()

from app.services.analytics_service import AnalyticsService


@router.get("/")
def get_biometrics(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    date_str: str = Query(None),
):
    if not date_str:
        date_str = date.today().isoformat()

    biometric = (
        db.query(Biometrics)
        .filter(Biometrics.user_id == user_id, Biometrics.date == date_str)
        .first()
    )

    # Get advanced readiness and baselines
    readiness = AnalyticsService.get_readiness_score(db, user_id)

    # Get all workouts for the date to calculate cumulative totals
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    workouts = db.query(Workout).filter(
        Workout.user_id == user_id,
        func.date(Workout.date) == target_date.date()
    ).all()
    
    total_workout_calories = sum(w.calories for w in workouts)
    total_workout_duration = sum(w.duration for w in workouts)

    if biometric:
        data = json.loads(biometric.data)
        # Baseline calories from biometrics (active calories, may be 0)
        baseline_calories = data.get("calories", 0) or 0
        # Total = baseline + workout calories
        total_calories = baseline_calories + total_workout_calories
        
        # Merge baseline info with workout aggregation
        return {
            **data,
            "source": biometric.source,
            "readiness": readiness.get("score"),
            "status": readiness.get("status"),
            "hrv_baseline": readiness.get("hrv_baseline"),
            "rhr_baseline": readiness.get("rhr_baseline"),
            "recovery_time": biometric.recovery_time,
            "training_status": biometric.training_status,
            "hrv_status": biometric.hrv_status,
            # Cumulative totals including workouts
            "calories_baseline": baseline_calories,
            "calories_workouts": total_workout_calories,
            "calories_total": total_calories,
            "workout_duration": total_workout_duration,
            "workout_count": len(workouts),
        }

    # No data found for this date - still include workout totals
    return {
        "heartRate": None,
        "hrv": None,
        "spo2": None,
        "stress": None,
        "steps": None,
        "sleep": None,
        "calories": None,
        "calories_baseline": 0,
        "calories_workouts": total_workout_calories,
        "calories_total": total_workout_calories,
        "workout_duration": total_workout_duration,
        "workout_count": len(workouts),
        "respiration": None,
        "readiness": readiness.get("score"),
        "status": readiness.get("status"),
        "hrv_baseline": readiness.get("hrv_baseline"),
        "rhr_baseline": readiness.get("rhr_baseline"),
        "overtraining": False,
        "source": "none",
    }


@router.post("/")
def upsert_biometrics(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Recibe biométricos desde el cliente (Health Connect / móvil) y los guarda por día.
    Mantiene compatibilidad con el modelo `Biometrics.data` (JSON string).
    """
    try:
        date_str = payload.get("date") or date.today().isoformat()
        source = payload.get("source") or "health_connect"

        existing = (
            db.query(Biometrics)
            .filter(Biometrics.user_id == user_id, Biometrics.date == date_str)
            .first()
        )
        if not existing:
            existing = Biometrics(user_id=user_id, date=date_str)
            db.add(existing)

        existing.data = json.dumps(payload)
        existing.source = source
        db.commit()

        return {"success": True, "user_id": user_id, "date": date_str, "source": source}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
