from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.models.workout import Workout
from typing import List
from datetime import datetime, date

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
