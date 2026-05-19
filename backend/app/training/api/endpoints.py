"""
VITALIS Training Engine - API Endpoints
=======================================

RESTful API para el sistema de entrenamiento inteligente.
Endpoints integrados en /api/v1/training/

Diseño:
- POST /workouts/generate - Generar rutina
- POST /workouts/adapt - Adaptar existente
- POST /sets/feedback - Recibir feedback
- GET /workouts/{id} - Obtener detalle
- POST /integration/push - Exportar
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy import or_
from datetime import datetime
from typing import Optional

from app.api.deps import get_db, get_current_user_id
from app.training.domain.models import (
    PlannedWorkout, TrainingPlan, ExerciseSet, WorkoutFeedback,
    WorkoutStatus, SetStatus, AdaptationReason, WorkoutType
)
from app.training.schemas import (
    WorkoutCreate, WorkoutResponse, WorkoutUpdate,
    TrainingGenerationRequest, TrainingAdaptationRequest,
    SetFeedbackRequest, ExerciseSetUpdate,
    WorkoutFeedbackCreate, WorkoutFeedbackResponse,
    ExternalWorkoutPush, ExternalWorkoutPull, IntegrationResponse,
    UserTrainingStats, FatigueAnalysis, ExerciseLibraryCreate, ExerciseLibraryResponse
)
from app.training.use_cases import (
    WorkoutGenerator, WorkoutAdapter, TrainingAnalyzer,
    TrainingEntityFactory, TrainingConstants, TrainingPlanGenerator
)

router = APIRouter(prefix="/training", tags=["training"])


# ============================================================================
# WORKOUT GENERATION
# ============================================================================

@router.post("/workouts/generate", response_model=WorkoutResponse)
def generate_workout(
    request: TrainingGenerationRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Genera un workout automáticamente basado en readiness y preferencias.
    
    - Analiza readiness score actual
    - Selecciona ejercicios óptimos
    - Distribuye volumen según fatiga
    - Ajusta RPE e intensidad
    """
    # Validar permisos
    if request.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para generar workouts para otro usuario"
        )
    
    # Generar workout
    generator = WorkoutGenerator(db)
    workout_schema = generator.generate_workout(request)
    
    # Crear entidad
    workout = TrainingEntityFactory.create_workout_from_schema(
        workout_schema, 
        current_user
    )
    
    # Guardar
    db.add(workout)
    db.commit()
    db.refresh(workout)
    
    return workout


@router.post("/plans/generate", response_model=dict)
def generate_training_plan(
    weeks: int = 4,
    workouts_per_week: int = 3,
    workout_type: str = "strength",
    goal: Optional[str] = None,
    experience_level: str = "intermediate",
    available_days: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Genera un plan de entrenamiento completo (macro-ciclo).
    
    - Periodización básica
    - Distribución de cargas
    - Progresión semanal
    - Personalización basada en objetivos y experiencia
    """
    # Validar permisos
    if weeks < 1 or weeks > 52:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de semanas debe estar entre 1 y 52"
        )
    
    if workouts_per_week < 1 or workouts_per_week > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los entrenamientos por semana deben estar entre 1 y 7"
        )
    
    # Validar que los días disponibles sean válidos (0-6)
    if available_days:
        for day in available_days:
            if day < 0 or day > 6:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Los días disponibles deben estar entre 0 (lunes) y 6 (domingo)"
                )
    
    # Generar plan de entrenamiento completo
    generator = TrainingPlanGenerator(db)
    plan_schema = generator.generate_training_plan(
        user_id=current_user,
        weeks=weeks,
        workouts_per_week=workouts_per_week,
        workout_type=WorkoutType(workout_type),
        goal=goal,
        experience_level=experience_level,
        available_days=available_days
    )
    
    # Crear entidad de plan de entrenamiento
    plan = TrainingEntityFactory.create_training_plan_from_schema(
        plan_schema, 
        current_user
    )
    
    # Guardar
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return {
        "message": "Plan de entrenamiento generado exitosamente",
        "plan_id": plan.id,
        "user_id": current_user,
        "weeks": weeks,
        "workouts_per_week": workouts_per_week,
        "workout_type": workout_type,
        "goal": goal,
        "experience_level": experience_level,
        "total_workouts": len(plan_schema.workouts)
    }


# ============================================================================
# WORKOUT ADAPTATION
# ============================================================================

@router.post("/workouts/adapt", response_model=dict)
def adapt_workout(
    request: TrainingAdaptationRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Adapta un workout existente basado en nueva información.
    
    Casos de uso:
    - Readiness bajo: reducir intensidad
    - Fatiga alta: reducir volumen
    - Tiempo limitado: eliminar ejercicios
    - RPE alto/bajo: ajustar cargas
    """
    # Obtener workout
    workout = db.query(Workout).filter(
        Workout.id == request.workout_id,
        Workout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    # Verificar que no esté completado
    if workout.status == WorkoutStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede adaptar un workout ya completado"
        )
    
    # Adaptar
    adapter = WorkoutAdapter(db)
    changes = adapter.adapt_workout(workout, request)
    
    # Guardar cambios
    db.commit()
    
    return {
        "workout_id": workout.id,
        "changes_applied": changes,
        "new_status": workout.status.value,
        "message": f"Adaptación completada: {len(changes)} cambios"
    }


@router.post("/sets/feedback", response_model=dict)
def submit_set_feedback(
    request: SetFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Recibe feedback de ejecución real de un set.
    
    Análisis:
    - Compara RPE planificado vs real
    - Calcula volumen alcanzado
    - Genera recomendación de ajuste
    - Actualiza métricas del usuario
    """
    # Obtener set
    set_data = db.query(ExerciseSet).join(ExerciseBlock).join(PlannedWorkout).filter(
        ExerciseSet.id == request.set_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not set_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Set no encontrado"
        )
    
    # Actualizar datos reales
    set_data.actual_reps = request.actual_reps
    set_data.actual_weight_kg = request.actual_weight_kg
    set_data.actual_rpe = request.actual_rpe
    set_data.actual_tempo = request.actual_tempo
    set_data.actual_rest_seconds = request.actual_rest_seconds
    set_data.status = request.status
    set_data.completed_at = datetime.utcnow() if request.status == SetStatus.COMPLETED else None
    
    # Calcular métricas
    set_data.volume_kg = request.actual_reps * request.actual_weight_kg
    set_data.rir = 10 - request.actual_rpe  # Reps in Reserve
    set_data.rpe_deviation = request.actual_rpe - set_data.planned_rpe
    
    # Análisis con adapter
    adapter = WorkoutAdapter(db)
    analysis = adapter.process_set_feedback(set_data, request)
    
    # Actualizar volumen del workout
    workout = set_data.block.workout
    workout.total_volume_kg += set_data.volume_kg or 0
    if request.status == SetStatus.COMPLETED:
        workout.total_sets_completed += 1
    
    db.commit()
    
    return {
        "set_id": set_data.id,
        "analysis": analysis,
        "updated_workout_stats": {
            "total_volume": workout.total_volume_kg,
            "sets_completed": workout.total_sets_completed
        }
    }


# ============================================================================
# WORKOUT CRUD
# ============================================================================

@router.get("/workouts", response_model=List[WorkoutResponse])
def list_workouts(
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Lista workouts del usuario con filtros opcionales"""
    query = db.query(PlannedWorkout).filter(PlannedWorkout.user_id == current_user)
    
    if status:
        query = query.filter(PlannedWorkout.status == status)
    
    workouts = query.order_by(PlannedWorkout.created_at.desc()).limit(limit).all()
    return workouts


@router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Obtiene detalle completo de un workout"""
    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    return workout


@router.patch("/workouts/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: str,
    update: WorkoutUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Actualiza información de un workout"""
    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    # Actualizar campos
    for field, value in update.dict(exclude_unset=True).items():
        setattr(workout, field, value)
    
    db.commit()
    db.refresh(workout)
    
    return workout


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Elimina un workout"""
    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    db.delete(workout)
    db.commit()
    
    return None


# ============================================================================
# WORKOUT FEEDBACK
# ============================================================================

@router.post("/workouts/{workout_id}/feedback", response_model=WorkoutFeedbackResponse)
def submit_workout_feedback(
    workout_id: str,
    feedback: WorkoutFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Feedback global de un workout completo.
    
    Métricas calculadas:
    - completion_percentage
    - volume_achievement
    - rpe_accuracy
    """
    # Verificar workout
    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == workout_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    # Calcular métricas
    completion_pct = (
        workout.total_sets_completed / workout.total_sets_planned * 100
        if workout.total_sets_planned > 0 else 0
    )
    
    # Calcular RPE accuracy
    sets_with_rpe = [s for s in workout.exercise_blocks 
                     for s in s.sets if s.actual_rpe is not None]
    if sets_with_rpe:
        rpe_diffs = [abs(s.actual_rpe - s.planned_rpe) for s in sets_with_rpe]
        rpe_accuracy = max(0, 100 - (sum(rpe_diffs) / len(rpe_diffs) * 10))
    else:
        rpe_accuracy = 0
    
    # Crear feedback
    feedback_record = WorkoutFeedback(
        workout_id=workout_id,
        user_id=current_user,
        overall_rpe=feedback.overall_rpe,
        fatigue_level=feedback.fatigue_level,
        enjoyment_level=feedback.enjoyment_level,
        motivation_level=feedback.motivation_level,
        sleep_quality_previous_night=feedback.sleep_quality_previous_night,
        stress_level=feedback.stress_level,
        completion_percentage=completion_pct,
        volume_achievement=workout.total_volume_kg,  # Simplificado
        rpe_accuracy=rpe_accuracy,
        suggested_changes=feedback.suggested_changes,
        user_notes=feedback.user_notes
    )
    
    db.add(feedback_record)
    db.commit()
    db.refresh(feedback_record)
    
    return feedback_record


# ============================================================================
# ANALYTICS
# ============================================================================

@router.get("/analytics/fatigue", response_model=dict)
def get_fatigue_analysis(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Análisis de fatiga acumulada (ACWR).
    
    - Acute Load (7 días)
    - Chronic Load (28 días promedio)
    - ACWR Ratio
    - Recomendación de acción
    """
    analyzer = TrainingAnalyzer(db)
    acwr_data = analyzer.calculate_acwr(current_user)
    
    return acwr_data


@router.get("/analytics/trends", response_model=dict)
def get_training_trends(
    days: int = 14,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Tendencias de entrenamiento reciente.
    
    - Promedio RPE
    - Distribución de intensidad
    - Tendencia (mejorando/empeorando/estable)
    """
    analyzer = TrainingAnalyzer(db)
    trends = analyzer.analyze_rpe_trends(current_user, days)
    
    return trends


# ============================================================================
# INTEGRATION (ADAPTER LAYER)
# ============================================================================

@router.post("/integration/push", response_model=IntegrationResponse)
def push_to_external_app(
    request: ExternalWorkoutPush,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Exporta workout a aplicación externa (wger, Strong, etc.).
    
    Adapter layer para compatibilidad con APIs externas.
    """
    # Obtener workout
    workout = db.query(PlannedWorkout).filter(
        PlannedWorkout.id == request.workout_id,
        PlannedWorkout.user_id == current_user
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout no encontrado"
        )
    
    # TODO: Implementar adapters específicos por app
    # Por ahora, stub con estructura genérica
    
    return IntegrationResponse(
        success=True,
        message=f"Workout exportado a {request.target_app} (simulado)",
        external_id=None,
        errors=[]
    )


@router.post("/integration/pull", response_model=WorkoutResponse)
def pull_from_external_app(
    request: ExternalWorkoutPull,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """
    Importa workout desde aplicación externa.
    
    Normaliza datos externos al formato interno.
    """
    # TODO: Implementar import adapters
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Importación desde apps externas - implementación pendiente"
    )


# ============================================================================
# EXERCISE LIBRARY
# ============================================================================

@router.get("/exercises", response_model=List[dict])
def list_exercises(
    muscle_group: Optional[str] = None,
    exercise_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Lista ejercicios disponibles con filtros (globales + custom del usuario)"""
    from app.training.domain.models import ExerciseLibrary
    
    query = db.query(ExerciseLibrary).filter(
        or_(
            ExerciseLibrary.is_custom == False,
            ExerciseLibrary.user_id == current_user
        )
    )
    
    if muscle_group:
        query = query.filter(ExerciseLibrary.primary_muscle == muscle_group)
    
    if exercise_type:
        query = query.filter(ExerciseLibrary.exercise_type == exercise_type)
    
    exercises = query.all()
    
    return [
        {
            "id": e.id,
            "name": e.name,
            "primary_muscle": e.primary_muscle.value if hasattr(e.primary_muscle, 'value') else e.primary_muscle,
            "exercise_type": e.exercise_type.value if hasattr(e.exercise_type, 'value') else e.exercise_type,
            "recommended_rpe": e.recommended_rpe_range,
            "difficulty": e.difficulty_level,
            "is_custom": e.is_custom
        }
        for e in exercises
    ]

@router.post("/exercises/custom", response_model=ExerciseLibraryResponse)
def create_custom_exercise(
    exercise: ExerciseLibraryCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_id)
):
    """Crea un ejercicio personalizado para el usuario actual."""
    from app.training.domain.models import ExerciseLibrary
    
    # Crear entidad
    new_exercise = ExerciseLibrary(
        **exercise.model_dump(exclude={"is_custom", "user_id"}),
        is_custom=True,
        user_id=current_user
    )
    
    db.add(new_exercise)
    db.commit()
    db.refresh(new_exercise)
    
    return new_exercise
