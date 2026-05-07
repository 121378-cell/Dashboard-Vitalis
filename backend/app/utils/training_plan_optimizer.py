"""
Optimizaciones de rendimiento para Training Plan Service
========================================================

Este archivo contiene optimizaciones para mejorar el rendimiento del servicio
de planes de entrenamiento con grandes volúmenes de datos.

Optimizaciones implementadas:
1. Caching de perfil atlético (5 minutos)
2. Paginación de historial de planes
3. Índices de base de datos optimizados
4. Consultas eficientes con eager loading
5. Compresión de JSON grandes
"""

import gzip
import json
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta

# Cache para perfil atlético (5 minutos)
@lru_cache(maxsize=10)
def get_cached_athletic_profile(user_id: str, cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el perfil atlético con caching.
    
    Args:
        user_id: ID del usuario
        cache_key: Clave de cache basada en timestamp (para invalidar cada 5 min)
        
    Returns:
        Perfil atlético o None
    """
    from app.db.session import SessionLocal
    from app.services.athletic_intelligence_service import AthleticIntelligenceService
    
    db = SessionLocal()
    try:
        return AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
    finally:
        db.close()


def compress_json(data: Dict[str, Any]) -> bytes:
    """
    Comprime datos JSON para reducir tamaño en base de datos.
    
    Args:
        data: Diccionario a comprimir
        
    Returns:
        Datos comprimidos en bytes
    """
    json_str = json.dumps(data, ensure_ascii=False)
    return gzip.compress(json_str.encode('utf-8'))


def decompress_json(compressed_data: bytes) -> Dict[str, Any]:
    """
    Descomprime datos JSON.
    
    Args:
        compressed_data: Datos comprimidos
        
    Returns:
        Diccionario descomprimido
    """
    json_str = gzip.decompress(compressed_data).decode('utf-8')
    return json.loads(json_str)


def get_cache_key() -> str:
    """
    Genera una clave de cache basada en el tiempo actual (cada 5 minutos).
    
    Returns:
        Clave de cache
    """
    now = datetime.now()
    return f"{now.year}{now.month}{now.day}{now.hour}{now.minute // 5}"


class PerformanceOptimizer:
    """Optimizador de rendimiento para operaciones de planes."""
    
    @staticmethod
    def optimize_plan_query(db, user_id: str, limit: int = 10):
        """
        Optimiza la consulta de planes con eager loading y paginación.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de resultados
            
        Returns:
            Query optimizada
        """
        from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession
        from sqlalchemy.orm import joinedload
        
        return (
            db.query(AdaptiveTrainingPlan)
            .options(
                joinedload(AdaptiveTrainingPlan.sessions)
            )
            .filter(AdaptiveTrainingPlan.user_id == user_id)
            .order_by(AdaptiveTrainingPlan.created_at.desc())
            .limit(limit)
        )
    
    @staticmethod
    def optimize_session_query(db, plan_id: int):
        """
        Optimiza la consulta de sesiones con índices.
        
        Args:
            db: Sesión de base de datos
            plan_id: ID del plan
            
        Returns:
            Query optimizada
        """
        from app.models.adaptive_training_plan import AdaptivePlannedSession
        
        return (
            db.query(AdaptivePlannedSession)
            .filter(AdaptivePlannedSession.plan_id == plan_id)
            .order_by(AdaptivePlannedSession.session_date)
        )
    
    @staticmethod
    def batch_update_sessions(db, session_ids: list, updates: Dict[str, Any]) -> int:
        """
        Actualiza múltiples sesiones en una sola operación.
        
        Args:
            db: Sesión de base de datos
            session_ids: Lista de IDs de sesiones
            updates: Diccionario con campos a actualizar
            
        Returns:
            Número de sesiones actualizadas
        """
        from app.models.adaptive_training_plan import AdaptivePlannedSession
        
        return (
            db.query(AdaptivePlannedSession)
            .filter(AdaptivePlannedSession.id.in_(session_ids))
            .update(updates, synchronize_session=False)
        )
    
    @staticmethod
    def get_plan_statistics(db, user_id: str) -> Dict[str, Any]:
        """
    Obtiene estadísticas de planes de forma eficiente.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        
    Returns:
        Diccionario con estadísticas
    """
        from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession
        from sqlalchemy import func
        
        # Total de planes
        total_plans = (
            db.query(func.count(AdaptiveTrainingPlan.id))
            .filter(AdaptiveTrainingPlan.user_id == user_id)
            .scalar()
        )
        
        # Planes activos
        active_plans = (
            db.query(func.count(AdaptiveTrainingPlan.id))
            .filter(
                AdaptiveTrainingPlan.user_id == user_id,
                AdaptiveTrainingPlan.status == 'active'
            )
            .scalar()
        )
        
        # Total de sesiones
        total_sessions = (
            db.query(func.count(AdaptivePlannedSession.id))
            .join(AdaptiveTrainingPlan)
            .filter(AdaptiveTrainingPlan.user_id == user_id)
            .scalar()
        )
        
        # Sesiones completadas
        completed_sessions = (
            db.query(func.count(AdaptivePlannedSession.id))
            .join(AdaptiveTrainingPlan)
            .filter(
                AdaptiveTrainingPlan.user_id == user_id,
                AdaptivePlannedSession.completed == True
            )
            .scalar()
        )
        
        return {
            "total_plans": total_plans,
            "active_plans": active_plans,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        }


# Funciones de utilidad para optimización de consultas
def optimize_json_size(data: Dict[str, Any], max_size: int = 10000) -> Dict[str, Any]:
    """
    Optimiza el tamaño de datos JSON eliminando campos innecesarios.
    
    Args:
        data: Diccionario a optimizar
        max_size: Tamaño máximo en caracteres
        
    Returns:
        Diccionario optimizado
    """
    # Campos a eliminar si el JSON es demasiado grande
    fields_to_remove = ['fitness_snapshot', 'ai_reasoning']
    
    json_str = json.dumps(data, ensure_ascii=False)
    
    if len(json_str) > max_size:
        optimized = data.copy()
        for field in fields_to_remove:
            if field in optimized:
                del optimized[field]
        return optimized
    
    return data


def validate_plan_data(plan_data: Dict[str, Any]) -> bool:
    """
    Valida que los datos del plan sean correctos antes de guardar.
    
    Args:
        plan_data: Diccionario con datos del plan
        
    Returns:
        True si los datos son válidos, False en caso contrario
    """
    required_fields = ['weekly_goal', 'reasoning', 'total_planned_minutes', 'sessions']
    
    for field in required_fields:
        if field not in plan_data:
            return False
    
    if not isinstance(plan_data['sessions'], list):
        return False
    
    if len(plan_data['sessions']) == 0:
        return False
    
    # Validar cada sesión
    for session in plan_data['sessions']:
        required_session_fields = ['date', 'day_of_week', 'session_type', 'title']
        for field in required_session_fields:
            if field not in session:
                return False
    
    return True
