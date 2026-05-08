"""
ATLAS Daily Loop Endpoints
===========================

GET  /daily/status   — Retorna el último resultado guardado (sin recalcular)
POST /daily/run-now  — Ejecuta run_daily_loop() inmediatamente
GET  /daily/history  — Retorna los últimos N registros de daily_readiness
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db, get_current_user_id
from app.services.daily_loop_service import DailyLoopService

router = APIRouter()


@router.get("/status", summary="Get today's cached readiness status")
async def get_daily_status(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = DailyLoopService.get_status(db, user_id)
    return result


@router.post("/run-now", summary="Run daily loop now and return result")
async def run_daily_loop_now(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = DailyLoopService.run_daily_loop(db, user_id)
    return result


@router.get("/history", summary="Get daily readiness history")
async def get_daily_history(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = DailyLoopService.get_history(db, user_id, days)
    return result
