from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.services.analytics_service import AnalyticsService
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from typing import Optional
from datetime import timedelta
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/correlations")
def get_correlations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    days: int = Query(90, ge=30, le=365),
):
    return AnalyticsService.find_personal_correlations(db, user_id, days)


@router.get("/readiness-forecast")
def get_readiness_forecast(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    days_ahead: int = Query(3, ge=1, le=7),
):
    return AnalyticsService.forecast_readiness(db, user_id, days_ahead)


@router.get("/plateaus")
def get_plateaus(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    exercise: Optional[str] = Query(None),
    weeks: int = Query(6, ge=4, le=12),
):
    return AnalyticsService.detect_plateau(db, user_id, exercise, weeks)


@router.get("/optimal-volume")
def get_optimal_volume(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return AnalyticsService.find_optimal_volume(db, user_id)


@router.get("/insights")
def get_insights(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return AnalyticsService.get_monthly_insights(db, user_id)


# =============================================================================
# ATHLETIC INTELLIGENCE ENDPOINTS
# =============================================================================

# Cache simple en memoria para el endpoint profile
_profile_cache = {}
_profile_cache_timestamp = None
_CACHE_DURATION = 30 * 60  # 30 segundos


@router.get("/intelligence/profile")
def get_athletic_profile(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Obtiene el perfil atlético completo del atleta.
    
    Cache de 30 minutos para no recalcular en cada request.
    Si hay error en alguna subfunción, retorna datos parciales con campo "errors".
    """
    global _profile_cache, _profile_cache_timestamp
    
    current_time = time.time()
    
    # Verificar si hay cache válido
    if (_profile_cache_timestamp and 
        current_time - _profile_cache_timestamp < _CACHE_DURATION and
        user_id in _profile_cache):
        return _profile_cache[user_id]
    
    try:
        # Generar perfil completo
        profile = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
        
        # Guardar en cache
        _profile_cache[user_id] = profile
        _profile_cache_timestamp = current_time
        
        return profile
        
    except Exception as e:
        # En caso de error, retornar datos parciales con errores
        logger.error(f"Error generating athletic profile: {e}")
        
        return {
            "generated_at": time.time(),
            "user_id": user_id,
            "errors": [f"Error generando perfil: {str(e)}"],
            "fitness_baseline": {"insufficient_data": True},
            "sleep_patterns": {"insufficient_data": True},
            "recovery_capacity": {"insufficient_data": True},
            "overreaching_risk": {"insufficient_data": True}
        }


@router.get("/intelligence/overreaching-check")
def get_overreaching_check(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Obtiene solo el análisis de riesgo de sobreentrenamiento.
    
    Sin cache - siempre fresco para decisiones inmediatas.
    """
    try:
        overreaching_risk = AthleticIntelligenceService.detect_overreaching_risk(db, user_id)
        return overreaching_risk
    except Exception as e:
        logger.error(f"Error checking overreaching risk: {e}")
        return {
            "risk_level": "insufficient_data",
            "recommendation": f"Error analizando riesgo: {str(e)}",
            "acwr_ratio": None,
            "acute_load_min": None,
            "chronic_load_min": None,
            "additional_risk_factors": 0
        }
