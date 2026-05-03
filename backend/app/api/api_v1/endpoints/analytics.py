from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService
from typing import Optional

router = APIRouter()


@router.get("/correlations")
def get_correlations(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    days: int = Query(90, ge=30, le=365),
):
    return AnalyticsService.find_personal_correlations(db, user_id, days)


@router.get("/readiness-forecast")
def get_readiness_forecast(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    days_ahead: int = Query(3, ge=1, le=7),
):
    return AnalyticsService.forecast_readiness(db, user_id, days_ahead)


@router.get("/plateaus")
def get_plateaus(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    exercise: Optional[str] = Query(None),
    weeks: int = Query(6, ge=4, le=12),
):
    return AnalyticsService.detect_plateau(db, user_id, exercise, weeks)


@router.get("/optimal-volume")
def get_optimal_volume(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
):
    return AnalyticsService.find_optimal_volume(db, user_id)


@router.get("/insights")
def get_insights(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
):
    return AnalyticsService.get_monthly_insights(db, user_id)
