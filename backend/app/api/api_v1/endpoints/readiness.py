"""
VITALIS READINESS API ENDPOINT
==============================
FastAPI endpoint para el sistema de Readiness Score

Ruta: /api/v1/readiness
Métodos:
- GET /readiness - Obtener score actual del usuario
- GET /readiness/history - Historial de scores
- POST /readiness/calculate - Calcular con datos proporcionados
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json

from app.api.deps import get_db, get_current_user_id
from app.models.biometrics import Biometrics
from app.models.user import User
from app.core.readiness_engine import compute_readiness_score, ReadinessEngine

router = APIRouter()


@router.get("/readiness")
async def get_readiness_score(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Obtiene el Readiness Score actual del usuario basado en sus últimos datos biométricos.
    
    Returns:
    {
        "readiness_score": 78.5,
        "status": "high",
        "factors": {
            "sleep": 85.0,
            "recovery": 75.0,
            "strain": 90.0,
            "activity_balance": 70.0,
            "hr_baseline": 95.0
        },
        "recommendation": "Preparado para entrenamiento de alta intensidad...",
        "timestamp": "2026-03-26T18:30:00",
        "user_id": "default_user",
        "version": "1.0",
        "data_source": "garmin"
    }
    """
    # Obtener datos biométricos más recientes
    latest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).first()
    
    if not latest_biometric:
        raise HTTPException(
            status_code=404,
            detail="No hay datos biométricos disponibles para calcular el score"
        )
    
    # Parsear datos JSON
    try:
        bio_data = json.loads(latest_biometric.data) if latest_biometric.data else {}
    except:
        bio_data = {}
    
    # Obtener promedios de 7 días para contexto
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id,
        Biometrics.date >= seven_days_ago
    ).all()
    
    # Calcular promedios de 7 días
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
    
    # Preparar datos para el engine
    input_data = {
        "heart_rate": bio_data.get("heartRate", 60),
        "hrv": bio_data.get("hrv"),  # Puede ser None para FR245
        "sleep_hours": bio_data.get("sleep", 0),
        "sleep_score": bio_data.get("sleepScore"),
        "stress_level": bio_data.get("stress", 50),
        "steps": bio_data.get("steps", 0),
        "steps_prev_7d_avg": steps_avg_7d,
        "is_rest_day": bio_data.get("steps", 0) < 8000,  # Heurística simple
        "exercise_load_7d": 1.0  # Placeholder - se calcularía de workouts
    }
    
    # Calcular score
    result = compute_readiness_score(user_id, input_data, db)
    
    return result


@router.get("/readiness/history")
async def get_readiness_history(
    user_id: str = Depends(get_current_user_id),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de Readiness Score de los últimos N días.
    
    Query params:
    - days: Número de días a consultar (1-365, default 30)
    
    Returns:
    {
        "history": [
            {
                "date": "2026-03-25",
                "score": 82.3,
                "status": "high",
                "factors": {...}
            },
            ...
        ],
        "averages": {
            "score_7d": 75.4,
            "score_30d": 72.1,
            "trend": "improving"  // improving | stable | declining
        }
    }
    """
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id,
        Biometrics.date >= start_date
    ).order_by(Biometrics.date.asc()).all()
    
    if not biometrics:
        return {
            "history": [],
            "averages": None,
            "message": "No hay datos suficientes para generar historial"
        }
    
    # Calcular score para cada día
    engine = ReadinessEngine(user_id, db)
    history = []
    scores = []
    
    # Calcular promedio de 7 días para pasos
    all_steps = []
    for b in biometrics:
        if b.data:
            try:
                data = json.loads(b.data)
                if data.get("steps"):
                    all_steps.append(data["steps"])
            except:
                pass
    
    global_avg_steps = sum(all_steps) / len(all_steps) if all_steps else 10000
    
    for bio in biometrics:
        try:
            data = json.loads(bio.data) if bio.data else {}
        except:
            continue
        
        input_data = {
            "heart_rate": data.get("heartRate", 60),
            "hrv": data.get("hrv"),
            "sleep_hours": data.get("sleep", 0),
            "stress_level": data.get("stress", 50),
            "steps": data.get("steps", 0),
            "steps_prev_7d_avg": global_avg_steps,
            "is_rest_day": data.get("steps", 0) < 8000,
            "exercise_load_7d": 1.0
        }
        
        score, factors = engine.calculate_readiness(input_data)
        scores.append(score)
        
        from app.core.readiness_engine import ReadinessStatus
        if score >= 71:
            status = ReadinessStatus.HIGH.value
        elif score >= 41:
            status = ReadinessStatus.MEDIUM.value
        else:
            status = ReadinessStatus.LOW.value
        
        history.append({
            "date": bio.date,
            "score": score,
            "status": status,
            "factors": factors.to_dict()
        })
    
    # Calcular tendencias
    if len(scores) >= 7:
        avg_7d = sum(scores[-7:]) / 7
        avg_30d = sum(scores[-30:]) / min(30, len(scores))
        
        if len(scores) >= 14:
            avg_prev_7d = sum(scores[-14:-7]) / 7
            if avg_7d > avg_prev_7d + 5:
                trend = "improving"
            elif avg_7d < avg_prev_7d - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
    else:
        avg_7d = sum(scores) / len(scores) if scores else 0
        avg_30d = avg_7d
        trend = "insufficient_data"
    
    return {
        "history": history,
        "averages": {
            "score_7d": round(avg_7d, 1),
            "score_30d": round(avg_30d, 1),
            "trend": trend
        },
        "total_days": len(history)
    }


@router.post("/readiness/calculate")
async def calculate_readiness_manual(
    data: dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Calcula el Readiness Score con datos proporcionados manualmente.
    
    Útil para testing o cuando se quieren probar diferentes escenarios.
    
    Body (JSON):
    {
        "heart_rate": 48,
        "sleep_hours": 7.5,
        "stress_level": 30,
        "steps": 12000,
        "steps_prev_7d_avg": 10000,
        "is_rest_day": false
    }
    
    Returns: Misma estructura que GET /readiness
    """
    try:
        result = compute_readiness_score(user_id, data, db)
        result["data_source"] = "manual"
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error calculando readiness score: {str(e)}"
        )


# ==================== MODELOS Pydantic (para documentación) ====================

from pydantic import BaseModel, Field

class ReadinessFactorsResponse(BaseModel):
    sleep: float = Field(..., description="Score de sueño (0-100)")
    recovery: float = Field(..., description="Score de recuperación/HRV (0-100)")
    strain: float = Field(..., description="Score de strain/estrés (0-100)")
    activity_balance: float = Field(..., description="Balance de actividad (0-100)")
    hr_baseline: float = Field(..., description="Desviación FC baseline (0-100)")

class ReadinessResponse(BaseModel):
    readiness_score: float = Field(..., ge=0, le=100, description="Score total 0-100")
    status: str = Field(..., description="low | medium | high")
    factors: ReadinessFactorsResponse
    recommendation: str = Field(..., description="Recomendación accionable")
    timestamp: str
    user_id: str
    version: str
    data_source: str = Field("garmin", description="Origen de los datos")

class ReadinessHistoryEntry(BaseModel):
    date: str
    score: float
    status: str
    factors: ReadinessFactorsResponse

class ReadinessAverages(BaseModel):
    score_7d: float
    score_30d: float
    trend: str = Field(..., description="improving | stable | declining | insufficient_data")

class ReadinessHistoryResponse(BaseModel):
    history: List[ReadinessHistoryEntry]
    averages: Optional[ReadinessAverages]
    total_days: int
    message: Optional[str]
