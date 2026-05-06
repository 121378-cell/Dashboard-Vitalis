"""
Endpoint para el perfil del atleta
===================================

Este endpoint expone el perfil completo del atleta para que el coach
de Atlas pueda acceder a toda la información necesaria para
personalizar sus recomendaciones.

Endpoints:
- GET /api/v1/athlete-profile: Obtiene el perfil completo del atleta
- GET /api/v1/athlete-profile/coach-context: Obtiene el contexto para el coach
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.session import get_db
from app.services.athlete_profile_service import AthleteProfileService

router = APIRouter()


@router.get("/athlete-profile")
def get_athlete_profile(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene el perfil completo del atleta.
    
    Args:
        user_id: ID del usuario (default: "default_user")
        db: Sesión de base de datos
    
    Returns:
        Perfil completo del atleta con estadísticas históricas
    """
    try:
        profile = AthleteProfileService.get_profile_dict(db, user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/athlete-profile/coach-context")
def get_coach_context(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene el contexto completo para el coach de Atlas.
    
    Este endpoint proporciona toda la información que el coach necesita
    para entender al atleta y personalizar sus recomendaciones.
    
    Args:
        user_id: ID del usuario (default: "default_user")
        db: Sesión de base de datos
    
    Returns:
        Contexto completo para el coach incluyendo:
        - Perfil del atleta
        - Recomendaciones personalizadas
        - Insights clave
    """
    try:
        context = AthleteProfileService.get_coach_context(db, user_id)
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
