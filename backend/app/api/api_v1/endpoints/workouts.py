from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db, get_current_user_id
from app.models.workout import Workout
from app.models.training_plan import PersonalRecord
from typing import List, Optional
from datetime import datetime, date, timedelta
import json

router = APIRouter()

@router.get("/")
def get_workouts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100)
):
    workouts = db.query(Workout).filter(Workout.user_id == user_id).order_by(Workout.date.desc()).limit(limit).all()
    return workouts


@router.post("/")
def upsert_workout(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Recibe un workout desde el cliente (p.ej. Health Connect) y lo guarda.
    Deduplica por (user_id, source, external_id) para evitar duplicados.
    """
    try:
        source = payload.get("source") or "health_connect"
        external_id = payload.get("external_id") or payload.get("id")
        if not external_id:
            raise HTTPException(status_code=400, detail="Missing external_id")

        external_id = str(external_id)

        workout = (
            db.query(Workout)
            .filter(
                Workout.user_id == user_id,
                Workout.source == source,
                Workout.external_id == external_id,
            )
            .first()
        )
        if not workout:
            workout = Workout(user_id=user_id, source=source, external_id=external_id)
            db.add(workout)

        workout.name = payload.get("name") or payload.get("title") or "Workout"
        workout.description = payload.get("description") or ""

        # Fecha/hora: aceptar ISO o YYYY-MM-DD; fallback a "ahora"
        raw_date = payload.get("date") or payload.get("startTime") or payload.get("start_date")
        dt: datetime
        if isinstance(raw_date, str) and raw_date:
            try:
                if len(raw_date) == 10:
                    dt = datetime.combine(date.fromisoformat(raw_date), datetime.min.time())
                else:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.utcnow()
        else:
            dt = datetime.utcnow()

        workout.date = dt
        workout.duration = int(payload.get("duration") or 0)
        workout.calories = int(payload.get("calories") or 0)

        db.commit()
        return {
            "success": True,
            "user_id": user_id,
            "id": workout.id,
            "source": source,
            "external_id": external_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
def get_recent_workouts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = Query(None, description="Filter: strength, cardio, all"),
):
    query = db.query(Workout).filter(Workout.user_id == user_id)

    if activity_type == "strength":
        query = query.filter(Workout.name.ilike("%fuerza%") | Workout.name.ilike("%strength%"))
    elif activity_type == "cardio":
        query = query.filter(
            Workout.name.ilike("%carrera%") |
            Workout.name.ilike("%running%") |
            Workout.name.ilike("%trail%") |
            Workout.name.ilike("%caminar%") |
            Workout.name.ilike("%walk%")
        )

    workouts = query.order_by(Workout.date.desc()).limit(limit).all()

    result = []
    for w in workouts:
        desc_data = {}
        try:
            desc_data = json.loads(w.description) if w.description else {}
        except Exception:
            pass

        workout_type = "strength"
        name_lower = (w.name or "").lower()
        if any(k in name_lower for k in ["carrera", "running", "trail", "caminar", "walk"]):
            workout_type = "cardio"

        result.append({
            "id": w.id,
            "name": w.name,
            "date": w.date.isoformat() if isinstance(w.date, datetime) else str(w.date)[:10],
            "duration_min": (w.duration or 0) // 60,
            "calories": w.calories or 0,
            "type": workout_type,
            "source": w.source,
            "avgHR": desc_data.get("avgHR"),
            "rpe": desc_data.get("rpe"),
            "sport": desc_data.get("sport"),
        })

    return result


@router.get("/personal-records")
def get_personal_records(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    exercise: Optional[str] = Query(None),
):
    query = db.query(PersonalRecord).filter(PersonalRecord.user_id == user_id)

    if exercise:
        query = query.filter(PersonalRecord.exercise_name.ilike(f"%{exercise}%"))

    records = query.order_by(PersonalRecord.date.desc()).all()

    if not records:
        return _seed_default_prs(db, user_id)

    return [
        {
            "date": r.date,
            "exercise": r.exercise_name,
            "pr": r.weight,
            "reps": r.reps,
            "unit": "kg",
            "muscle": _exercise_to_muscle(r.exercise_name),
            "source": r.source,
        }
        for r in records
    ]


MUSCLE_MAP = {
    "bench": "Chest", "press": "Shoulders", "squat": "Legs",
    "deadlift": "Back", "row": "Back", "curl": "Arms",
    "overhead": "Shoulders", "dip": "Chest", "pull": "Back",
    "lunge": "Legs", "extension": "Legs",
}


def _exercise_to_muscle(exercise_name: str) -> str:
    name = (exercise_name or "").lower()
    for kw, muscle in MUSCLE_MAP.items():
        if kw in name:
            return muscle
    return "Full Body"


def _seed_default_prs(db: Session, user_id: str):
    from datetime import date as date_type

    default_prs = [
        {"exercise_name": "Bench Press", "weight": 52, "reps": 5, "date": "2025-04-12", "source": "manual"},
        {"exercise_name": "Squat", "weight": 85, "reps": 5, "date": "2025-03-28", "source": "manual"},
        {"exercise_name": "Deadlift", "weight": 110, "reps": 3, "date": "2025-03-10", "source": "manual"},
        {"exercise_name": "Overhead Press", "weight": 42, "reps": 5, "date": "2025-02-22", "source": "manual"},
        {"exercise_name": "Barbell Row", "weight": 70, "reps": 5, "date": "2025-02-05", "source": "manual"},
        {"exercise_name": "Bicep Curl", "weight": 25, "reps": 8, "date": "2025-01-18", "source": "manual"},
    ]

    for pr_data in default_prs:
        existing = db.query(PersonalRecord).filter(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_name == pr_data["exercise_name"],
        ).first()
        if not existing:
            record = PersonalRecord(
                user_id=user_id,
                exercise_name=pr_data["exercise_name"],
                weight=pr_data["weight"],
                reps=pr_data["reps"],
                date=pr_data["date"],
                source=pr_data["source"],
            )
            db.add(record)

    db.commit()

    records = db.query(PersonalRecord).filter(
        PersonalRecord.user_id == user_id
    ).order_by(PersonalRecord.date.desc()).all()

    return [
        {
            "date": r.date,
            "exercise": r.exercise_name,
            "pr": r.weight,
            "reps": r.reps,
            "unit": "kg",
            "muscle": _exercise_to_muscle(r.exercise_name),
            "source": r.source,
        }
        for r in records
    ]
