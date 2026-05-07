"""
Training Plans API Endpoints
=============================

REST API para el sistema de planes de entrenamiento adaptativos de ATLAS.

Rutas:
- POST   /api/plans/generate          → Genera plan semanal completo
- GET    /api/plans/current           → Plan activo actual
- PUT    /api/plans/sessions/{id}     → Actualiza sesión planificada
- POST   /api/plans/detect-completed  → Detecta sesiones completadas automáticamente
- GET    /api/plans/history           → Historial de planes
- DELETE /api/plans/{id}              → Cancela plan

Autor: ATLAS Team
Version: 1.0.0
"""

import json
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.services.training_plan_service import TrainingPlanService

router = APIRouter()


class GeneratePlanRequest(BaseModel):
    """Request model para generar un plan de entrenamiento."""
    goal: str = Field(..., description="Objetivo del usuario para la semana")
    week_start: Optional[str] = Field(None, description="Fecha de inicio de la semana (YYYY-MM-DD), default: lunes actual")


class UpdateSessionRequest(BaseModel):
    """Request model para actualizar una sesión."""
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    intensity: Optional[str] = None
    exercises: Optional[List[dict]] = None
    running_details: Optional[dict] = None
    completed: Optional[bool] = None
    user_notes: Optional[str] = None


@router.post("/generate", summary="Genera plan semanal completo")
async def generate_weekly_plan(
    request: GeneratePlanRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Genera un plan de entrenamiento semanal completo usando IA.
    
    El plan se basa en el perfil atlético del usuario, incluyendo:
    - Nivel de fitness y capacidad cardiovascular
    - Patrones de sueño y recuperación
    - Riesgo de sobreentrenamiento (ACWR)
    - Historial de entrenamiento
    
    Args:
        request: Objeto con goal y opcionalmente week_start
        user_id: ID del usuario autenticado
        db: Sesión de base de datos
        
    Returns:
        Plan de entrenamiento completo con todas las sesiones
    """
    try:
        # Parsear week_start si se proporciona
        week_start_date = None
        if request.week_start:
            try:
                week_start_date = date.fromisoformat(request.week_start)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )
        
        # Generar plan
        plan = TrainingPlanService.generate_weekly_plan(
            db=db,
            user_id=user_id,
            goal=request.goal,
            week_start=week_start_date
        )
        
        # Verificar si hubo error (plan ya existe)
        if "error" in plan:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=plan["error"]
            )
        
        return {
            "status": "success",
            "data": plan,
            "message": "Plan de entrenamiento generado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando plan: {str(e)}"
        )


@router.get("/current", summary="Plan activo actual")
async def get_current_plan(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el plan de entrenamiento activo para la semana actual.
    
    Returns:
        Plan completo con progreso de sesiones completadas
    """
    try:
        plan = TrainingPlanService.get_current_plan(db, user_id)
        
        if not plan:
            return {
                "status": "success",
                "has_plan": False,
                "message": "No hay plan activo para esta semana"
            }
        
        return {
            "status": "success",
            "has_plan": True,
            "data": plan
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo plan actual: {str(e)}"
        )


@router.put("/sessions/{session_id}", summary="Actualiza sesión planificada")
async def update_session(
    session_id: int,
    request: UpdateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Actualiza una sesión planificada.
    
    Permite modificar:
    - Título y descripción
    - Duración e intensidad
    - Ejercicios (para sesiones de fuerza)
    - Detalles de running (para sesiones de cardio)
    - Marcar como completada
    - Añadir notas del usuario
    
    Args:
        session_id: ID de la sesión a actualizar
        request: Campos a actualizar
        user_id: ID del usuario autenticado
        db: Sesión de base de datos
        
    Returns:
        Sesión actualizada
    """
    try:
        # Construir diccionario de cambios
        changes = {}
        if request.title is not None:
            changes["title"] = request.title
        if request.description is not None:
            changes["description"] = request.description
        if request.duration_minutes is not None:
            changes["duration_minutes"] = request.duration_minutes
        if request.intensity is not None:
            changes["intensity"] = request.intensity
        if request.exercises is not None:
            changes["exercises_json"] = request.exercises
        if request.running_details is not None:
            changes["running_details_json"] = request.running_details
        if request.completed is not None:
            changes["completed"] = request.completed
        if request.user_notes is not None:
            changes["user_notes"] = request.user_notes
        
        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron campos para actualizar"
            )
        
        # Actualizar sesión
        updated_session = TrainingPlanService.update_session(
            db=db,
            session_id=session_id,
            changes=changes
        )
        
        return {
            "status": "success",
            "data": updated_session,
            "message": "Sesión actualizada exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando sesión: {str(e)}"
        )


@router.post("/detect-completed", summary="Detecta sesiones completadas automáticamente")
async def detect_completed_sessions(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Detecta automáticamente sesiones completadas basándose en actividades de Garmin.
    
    Busca actividades de Garmin que coincidan con sesiones planificadas
    y las marca como completadas automáticamente.
    
    Returns:
        Lista de sesiones marcadas como completadas
    """
    try:
        completed_sessions = TrainingPlanService.auto_detect_completed_sessions(db, user_id)
        
        return {
            "status": "success",
            "data": {
                "detected_count": len(completed_sessions),
                "sessions": completed_sessions
            },
            "message": f"{len(completed_sessions)} sesiones detectadas como completadas"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detectando sesiones completadas: {str(e)}"
        )


@router.get("/history", summary="Historial de planes")
async def get_plan_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el historial de planes de entrenamiento.
    
    Args:
        limit: Número máximo de planes a retornar (default: 10)
        user_id: ID del usuario autenticado
        db: Sesión de base de datos
        
    Returns:
        Lista de planes con información resumida
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El límite debe estar entre 1 y 50"
            )
        
        history = TrainingPlanService.get_plan_history(db, user_id, limit)
        
        return {
            "status": "success",
            "data": {
                "total": len(history),
                "plans": history
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo historial de planes: {str(e)}"
        )


@router.delete("/{plan_id}", summary="Cancela plan")
async def cancel_plan(
    plan_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Cancela un plan de entrenamiento.
    
    Cambia el estado del plan a 'cancelled'.
    
    Args:
        plan_id: ID del plan a cancelar
        user_id: ID del usuario autenticado
        db: Sesión de base de datos
        
    Returns:
        Confirmación de cancelación
    """
    try:
        success = TrainingPlanService.cancel_plan(db, plan_id)
        
        return {
            "status": "success",
            "message": f"Plan {plan_id} cancelado exitosamente"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelando plan: {str(e)}"
        )
