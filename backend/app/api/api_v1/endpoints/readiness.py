"""
VITALIS READINESS API ENDPOINTS v2
===================================

FastAPI endpoints para el sistema de Readiness Score v2.

Rutas:
- GET /api/v1/readiness - Obtener score actual del usuario (v1 legacy)
- GET /api/v1/readiness/score - Obtener score completo actual (v2)
- GET /api/v1/readiness/trend - Historial de scores (30 días)
- GET /api/v1/readiness/forecast - Predicción próximos 3 días
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json

from app.api.deps import get_db, get_current_user_id
from app.models.biometrics import Biometrics
from app.models.user import User
from app.services.readiness_service import ReadinessService

router = APIRouter()


@router.get("/readiness", summary="Readiness score actual (v1 legacy)")
async def get_readiness_score(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    [Legacy] Obtiene el Readiness Score actual del usuario basado en sus últimos datos biométricos.
    Mantenido para compatibilidad con integraciones existentes.
    """
    latest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).first()
    
    if not latest_biometric:
        raise HTTPException(
            status_code=404,
            detail="No hay datos biométricos disponibles para calcular el score"
        )
    
    try:
        bio_data = json.loads(latest_biometric.data) if latest_biometric.data else {}
    except:
        bio_data = {}
    
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id,
        Biometrics.date >= seven_days_ago
    ).all()
    
    steps_7d = []
    for b in recent_biometrics:
        if b.data:
            try:
                data = json.loads(b.data)
                if data.get("steps"):
                    steps_7d.append(data["steps"])
            except:
                pass
    
    steps_avg_7d = sum(steps_7d) / len(steps_7d) if steps_7d else 10000
    
    input_data = {
        "heart_rate": bio_data.get("heartRate", 60),
        "hrv": bio_data.get("hrv"),
        "sleep_hours": bio_data.get("sleep", 0),
        "sleep_score": bio_data.get("sleepScore"),
        "stress_level": bio_data.get("stress", 50),
        "steps": bio_data.get("steps", 0),
        "steps_prev_7d_avg": steps_avg_7d,
        "is_rest_day": bio_data.get("steps", 0) < 8000,
        "exercise_load_7d": 1.0
    }
    
    from app.core.readiness_engine import compute_readiness_score
    result = compute_readiness_score(user_id, input_data, db)
    
    return result


@router.get("/readiness/score", summary="Readiness score completo (v2)")
async def get_readiness_score_v2(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Obtiene el Readiness Score actual del usuario (v2).
    
    Returns:
    {
      "score": int,              // 0-100
      "status": str,             // excellent|good|moderate|poor|rest
      "recommendation": str,     // Recomendación personalizada
      "components": {            // Scores individuales 0-100
        "hrv": float,
        "sleep": float,
        "stress": float,
        "rhr": float,
        "load": float
      },
      "baseline": {               // baseline personal calculado
        "hrv_mean": float|null,
        "hrv_std": float|null,
        "rhr_mean": float|null,
        "rhr_std": float|null,
        "sleep_mean": float|null,
        "stress_mean": float|null,
        "days_available": int
      },
      "overtraining_risk": bool,
      "date": str
    }
    """
    result = ReadinessService.calculate(db, user_id)
    
    if result.get("score") is None:
        raise HTTPException(
            status_code=404,
            detail=result.get("recommendation", "No hay datos disponibles")
        )
    
    return result


@router.get("/readiness/trend", summary="Historial de readiness")
async def get_readiness_trend(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365, description="Días a consultar")
):
    """
    Obtiene el historial de Readiness Score de los últimos N días.
    
    Returns:
    [
      {
        "date": str,             // YYYY-MM-DD
        "score": int,            // 0-100
        "status": str,           // excellent|good|moderate|poor|rest
        "overtraining_risk": bool
      },
      ...
    ]
    """
    trend = ReadinessService.get_trend(db, user_id, days=days)
    
    if not trend:
        raise HTTPException(
            status_code=404,
            detail="No hay datos suficientes para generar historial"
        )
    
    return trend


@router.get("/readiness/forecast", summary="Predicción de readiness")
async def get_readiness_forecast(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    days: int = Query(default=3, ge=1, le=7, description="Días a proyectar")
):
    """
    Genera una predicción simple del readiness score para los próximos N días.
    
    Returns:
    [
      {
        "date": str,             // YYYY-MM-DD (futuro)
        "score": int,            // 0-100 (proyectado)
        "status": str,           // excellent|good|moderate|poor|rest
        "recommendation": str,   // Recomendación basada en proyección
        "confidence": float      // 0.3-1.0
      },
      ...
    ]
    """
    forecast = ReadinessService.get_forecast(db, user_id, days=days)
    
    if not forecast:
        raise HTTPException(
            status_code=404,
            detail="No hay datos suficientes para generar predicción"
        )
    
    return forecast


@router.post("/readiness/calculate", summary="Calcular readiness manualmente")
async def calculate_readiness_manual(
    data: dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Calcula el Readiness Score con datos proporcionados manualmente.
    
    Returns: Misma estructura que GET /readiness/score
    """
    try:
        result = ReadinessService.calculate(db, user_id)
        result["data_source"] = "manual"
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error calculando readiness score: {str(e)}"
        )


# Pydantic models para documentación
from pydantic import BaseModel, Field

class ReadinessFactorsResponse(BaseModel):
    hrv: float = Field(..., description="Score HRV (0-100)")
    sleep: float = Field(..., description="Score de sueño (0-100)")
    stress: float = Field(..., description="Score de estrés (0-100)")
    rhr: float = Field(..., description="Score FC reposo (0-100)")
    load: float = Field(..., description="Carga de entrenamiento (0-100)")

class ReadinessResponse(BaseModel):
    score: float = Field(..., ge=0, le=100, description="Score total 0-100")
    status: str = Field(..., description="excellent|good|moderate|poor|rest")
    recommendation: str = Field(..., description="Recomendación accionable")
    components: ReadinessFactorsResponse
    baseline: dict
    overtraining_risk: bool
    date: str
