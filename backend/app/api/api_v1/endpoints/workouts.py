from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.workout import Workout
from typing import List

router = APIRouter()

@router.get("/")
def get_workouts(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    limit: int = Query(20, ge=1, le=100)
):
    workouts = db.query(Workout).filter(Workout.user_id == user_id).order_by(Workout.date.desc()).limit(limit).all()
    return workouts
