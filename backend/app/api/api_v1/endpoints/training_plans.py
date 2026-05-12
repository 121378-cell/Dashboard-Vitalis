"""
Training Plans API Endpoints
=============================

REST API para el sistema de planes de entrenamiento adaptativos de ATLAS.

Rutas:
- POST /api/plans/generate → Genera plan semanal completo
- GET /api/plans/current → Plan activo actual
- PUT /api/plans/sessions/{id} → Actualiza sesión planificada
- POST /api/plans/detect-completed → Detecta sesiones completadas automáticamente
- GET /api/plans/history → Historial de planes
- DELETE /api/plans/{id} → Cancela plan
- POST /api/plans/sessions/{id}/adapt → Adapta sesión basándose en petición del usuario
- PUT /api/plans/sessions/{id}/complete → Marca sesión como completada
- GET /api/plans/sessions/{id}/progression → Datos de progresión de ejercicios

Autor: ATLAS Team
Version: 1.1.0
"""

import json
from datetime import date
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.services.training_plan_service import TrainingPlanService
from app.services.ai_service import AIService
from app.services.exercise_progression_service import get_progressions_for_session
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession, AdaptivePlanAdjustment

router = APIRouter()


class GeneratePlanRequest(BaseModel):
    """Request model para generar un plan de entrenamiento."""
    goal: str = Field(..., description="Objetivo del usuario para la semana")
    week_start: Optional[str] = Field(None, description="Fecha de inicio de la semana (YYYY-MM-DD)")
    training_days: Optional[List[str]] = Field(None, description="Días de entrenamiento: monday,tuesday,etc")
    time_available: Optional[Dict[str, int]] = Field(None, description="Minutos disponibles por día: {'monday': 60}")
    session_types: Optional[List[str]] = Field(None, description="Tipos de sesión deseados: strength,running,etc")
    intensity_preference: Optional[str] = Field(None, description="low, medium, high")
    consider_readiness: Optional[bool] = Field(True, description="Si ATLAS debe considerar readiness actual")
    restrictions: Optional[str] = Field(None, description="Lesiones o restricciones")


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


class AdaptSessionRequest(BaseModel):
    """Request model para adaptar una sesión."""
    user_request: str = Field(..., description="Petición del usuario para modificar la sesión")


class CompleteSessionRequest(BaseModel):
    """Request model para marcar sesión como completada."""
    completed: bool = Field(..., description="Marcar como completada")
    garmin_activity_id: Optional[str] = Field(None, description="ID de actividad Garmin asociada")


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
        request: Objeto con goal y opciones de configuración
        user_id: ID del usuario autenticado
        db: Sesión de base de datos

    Returns:
        Plan de entrenamiento completo con todas las sesiones
    """
    try:
        week_start_date = None
        if request.week_start:
            try:
                week_start_date = date.fromisoformat(request.week_start)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )

        plan = TrainingPlanService.generate_weekly_plan(
            db=db,
            user_id=user_id,
            goal=request.goal,
            week_start=week_start_date,
            training_days=request.training_days,
            time_available=request.time_available,
            session_types=request.session_types,
            intensity_preference=request.intensity_preference,
            consider_readiness=request.consider_readiness,
            restrictions=request.restrictions
        )

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


@router.post("/sessions/{session_id}/adapt", summary="Adapta sesión basándose en petición del usuario")
async def adapt_session(
    session_id: int,
    request: AdaptSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Adapta una sesión de entrenamiento basándose en la petición del usuario usando IA.

    El usuario puede pedir modificaciones como:
    - Cambiar ejercicios específicos
    - Ajustar intensidad o duración
    - Sustituir un ejercicio por otro
    - Añadir o quitar ejercicios

    La adaptación se registra como un AdaptivePlanAdjustment para trazabilidad.

    Args:
        session_id: ID de la sesión a adaptar
        request: Petición del usuario con la modificación deseada
        user_id: ID del usuario autenticado
        db: Sesión de base de datos

    Returns:
        Sesión adaptada con los nuevos ejercicios/detalles
    """
    try:
        session = db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.id == session_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con ID {session_id} no encontrada"
            )

        current_session_data = {
            "session_type": session.session_type,
            "title": session.title,
            "description": session.description,
            "duration_minutes": session.duration_minutes,
            "intensity": session.intensity,
        }

        if session.exercises_json:
            current_session_data["exercises"] = json.loads(session.exercises_json)
        if session.running_details_json:
            current_session_data["running_details"] = json.loads(session.running_details_json)

        original_session_json = json.dumps(current_session_data, ensure_ascii=False)

        ai_service = AIService()
        system_prompt = "Eres ATLAS Coach. Modifica la sesión de entrenamiento según la petición del usuario. RESPONDE SOLO CON JSON VÁLIDO del mismo formato que la sesión original."
        user_prompt = f"SESION ACTUAL:\n{json.dumps(current_session_data, ensure_ascii=False)}\n\nPETICION DEL USUARIO: {request.user_request}\n\nRetorna la sesión modificada en el mismo formato JSON."
        messages = [{"role": "user", "content": user_prompt}]
        response = ai_service._generate_chat_response(messages, system_prompt)
        content = response["content"]

        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        adapted_data = json.loads(content.strip())

        adapted_session_json = json.dumps(adapted_data, ensure_ascii=False)

        adjustment = AdaptivePlanAdjustment(
            plan_id=session.plan_id,
            session_id=session_id,
            reason=request.user_request,
            original_session_json=original_session_json,
            adapted_session_json=adapted_session_json
        )
        db.add(adjustment)

        if "exercises" in adapted_data:
            session.exercises_json = json.dumps(adapted_data["exercises"], ensure_ascii=False)
        if "running_details" in adapted_data:
            session.running_details_json = json.dumps(adapted_data["running_details"], ensure_ascii=False)
        if "title" in adapted_data:
            session.title = adapted_data["title"]
        if "description" in adapted_data:
            session.description = adapted_data["description"]
        if "duration_minutes" in adapted_data:
            session.duration_minutes = adapted_data["duration_minutes"]
        if "intensity" in adapted_data:
            session.intensity = adapted_data["intensity"]
        if "session_type" in adapted_data:
            session.session_type = adapted_data["session_type"]

        session.adaptation_reason = request.user_request

        db.commit()

        result = {
            "id": session.id,
            "date": session.session_date.isoformat(),
            "day_of_week": session.day_of_week,
            "session_type": session.session_type,
            "title": session.title,
            "description": session.description,
            "duration_minutes": session.duration_minutes,
            "intensity": session.intensity,
            "completed": session.completed,
            "adaptation_reason": session.adaptation_reason,
            "adjustment_id": adjustment.id
        }
        if session.exercises_json:
            result["exercises"] = json.loads(session.exercises_json)
        if session.running_details_json:
            result["running_details"] = json.loads(session.running_details_json)

        return {
            "status": "success",
            "data": result,
            "message": "Sesión adaptada exitosamente"
        }

    except json.JSONDecodeError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parseando respuesta de IA: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adaptando sesión: {str(e)}"
        )


@router.put("/sessions/{session_id}/complete", summary="Marca sesión como completada")
async def complete_session(
    session_id: int,
    request: CompleteSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Marca una sesión planificada como completada.

    Opcionalmente se puede asociar una actividad de Garmin a la sesión completada.

    Args:
        session_id: ID de la sesión a completar
        request: Datos de completado (completed flag y garmin_activity_id opcional)
        user_id: ID del usuario autenticado
        db: Sesión de base de datos

    Returns:
        Sesión actualizada con estado de completado
    """
    try:
        session = db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.id == session_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con ID {session_id} no encontrada"
            )

        session.completed = request.completed

        if request.garmin_activity_id is not None:
            session.garmin_activity_id = request.garmin_activity_id

        db.commit()

        result = {
            "id": session.id,
            "date": session.session_date.isoformat(),
            "day_of_week": session.day_of_week,
            "session_type": session.session_type,
            "title": session.title,
            "description": session.description,
            "duration_minutes": session.duration_minutes,
            "intensity": session.intensity,
            "completed": session.completed,
            "garmin_activity_id": session.garmin_activity_id,
            "user_notes": session.user_notes,
            "adaptation_reason": session.adaptation_reason
        }

        if session.exercises_json:
            result["exercises"] = json.loads(session.exercises_json)
        if session.running_details_json:
            result["running_details"] = json.loads(session.running_details_json)

        return {
            "status": "success",
            "data": result,
            "message": "Sesión marcada como completada" if request.completed else "Sesión marcada como no completada"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completando sesión: {str(e)}"
        )


@router.get("/sessions/{session_id}/progression", summary="Datos de progresión de ejercicios")
async def get_session_progression(
    session_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene sugerencias de progresión para los ejercicios de una sesión.

    Analiza el historial de entrenamiento del usuario para sugerir
    progresiones de carga, volumen o intensidad en los ejercicios
    planificados en la sesión.

    Args:
        session_id: ID de la sesión
        user_id: ID del usuario autenticado
        db: Sesión de base de datos

    Returns:
        Lista de sugerencias de progresión por ejercicio
    """
    try:
        session = db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.id == session_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con ID {session_id} no encontrada"
            )

        progressions = get_progressions_for_session(
            db=db,
            user_id=user_id,
            session_id=session_id
        )

        return {
            "status": "success",
            "data": {
                "session_id": session_id,
                "progressions": progressions
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo progresiones: {str(e)}"
        )
