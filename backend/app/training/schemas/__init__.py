"""
VITALIS Training Engine - Schemas (Pydantic)
=============================================

Schemas para serialización/deserialización de datos.
Separación clara entre Create, Update, Response y filtros.
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from app.training.domain.models import (
    SetStatus, WorkoutStatus, WorkoutType, MuscleGroup, 
    AdaptationReason
)


# ============================================================================
# EXERCISE LIBRARY SCHEMAS
# ============================================================================

class ExerciseLibraryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    primary_muscle: MuscleGroup
    secondary_muscles: List[MuscleGroup] = []
    exercise_type: WorkoutType = WorkoutType.STRENGTH
    recommended_rpe_range: List[float] = Field(default=[7.0, 9.0], min_length=2, max_length=2)
    recommended_rest_seconds: int = Field(default=120, ge=0, le=600)
    recommended_tempo: str = Field(default="2-0-2", pattern=r"^\d+-\d+-\d+$")
    equipment_needed: List[str] = []
    difficulty_level: int = Field(default=1, ge=1, le=5)
    video_url: Optional[str] = None
    image_url: Optional[str] = None


class ExerciseLibraryCreate(ExerciseLibraryBase):
    pass


class ExerciseLibraryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    primary_muscle: Optional[MuscleGroup] = None
    secondary_muscles: Optional[List[MuscleGroup]] = None
    exercise_type: Optional[WorkoutType] = None
    recommended_rpe_range: Optional[List[float]] = None
    recommended_rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    recommended_tempo: Optional[str] = Field(None, pattern=r"^\d+-\d+-\d+$")
    equipment_needed: Optional[List[str]] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    video_url: Optional[str] = None
    image_url: Optional[str] = None


class ExerciseLibraryResponse(ExerciseLibraryBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXERCISE SET SCHEMAS
# ============================================================================

class ExerciseSetBase(BaseModel):
    set_number: int = Field(..., ge=1)
    
    # Planificación
    planned_reps: int = Field(..., ge=1, le=100)
    planned_weight_kg: float = Field(..., ge=0)
    planned_rpe: float = Field(..., ge=1, le=10)
    planned_tempo: str = Field(default="2-0-2")
    planned_rest_seconds: int = Field(default=120, ge=0)
    
    # Ejecución (opcional en creación)
    actual_reps: Optional[int] = Field(None, ge=0, le=100)
    actual_weight_kg: Optional[float] = Field(None, ge=0)
    actual_rpe: Optional[float] = Field(None, ge=1, le=10)
    actual_tempo: Optional[str] = None
    actual_rest_seconds: Optional[int] = Field(None, ge=0)
    
    status: SetStatus = SetStatus.PLANNED
    
    # Notas
    user_notes: Optional[str] = None
    form_video_url: Optional[str] = None


class ExerciseSetCreate(ExerciseSetBase):
    pass


class ExerciseSetUpdate(BaseModel):
    """Para actualizar ejecución real del set"""
    actual_reps: int = Field(..., ge=0, le=100)
    actual_weight_kg: float = Field(..., ge=0)
    actual_rpe: float = Field(..., ge=1, le=10)
    actual_tempo: Optional[str] = None
    actual_rest_seconds: Optional[int] = Field(None, ge=0)
    status: SetStatus = SetStatus.COMPLETED
    user_notes: Optional[str] = None
    form_video_url: Optional[str] = None


class ExerciseSetResponse(ExerciseSetBase):
    id: str
    block_id: str
    
    # Métricas calculadas
    volume_kg: Optional[float]
    rir: Optional[float]  # Reps in Reserve
    rpe_deviation: Optional[float]
    performance_rating: Optional[float]
    
    created_at: datetime
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXERCISE BLOCK SCHEMAS
# ============================================================================

class ExerciseBlockBase(BaseModel):
    exercise_id: str
    execution_order: int = Field(default=0, ge=0)
    
    # Configuración
    target_sets: int = Field(default=3, ge=1, le=10)
    target_rpe: float = Field(default=8.0, ge=1, le=10)
    rest_seconds_between_sets: int = Field(default=120, ge=0, le=600)
    tempo: str = Field(default="2-0-2")
    
    # Progresión
    progression_scheme: str = Field(default="linear")
    weight_increment_kg: float = Field(default=0, ge=0)


class ExerciseBlockCreate(ExerciseBlockBase):
    sets: List[ExerciseSetCreate] = []


class ExerciseBlockUpdate(BaseModel):
    execution_order: Optional[int] = Field(None, ge=0)
    target_sets: Optional[int] = Field(None, ge=1, le=10)
    target_rpe: Optional[float] = Field(None, ge=1, le=10)
    rest_seconds_between_sets: Optional[int] = Field(None, ge=0, le=600)
    tempo: Optional[str] = None
    block_completed: Optional[bool] = None


class ExerciseBlockResponse(ExerciseBlockBase):
    id: str
    workout_id: str
    exercise: ExerciseLibraryResponse
    sets: List[ExerciseSetResponse]
    
    # Resumen
    block_completed: bool
    average_rpe_actual: Optional[float]
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT SCHEMAS
# ============================================================================

class WorkoutBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    workout_type: WorkoutType = WorkoutType.STRENGTH
    scheduled_date: Optional[datetime] = None
    estimated_duration_minutes: int = Field(default=60, ge=15, le=180)
    
    # Datos de contexto
    readiness_score_at_creation: Optional[float] = Field(None, ge=0, le=100)


class WorkoutCreate(WorkoutBase):
    plan_id: Optional[str] = None
    exercise_blocks: List[ExerciseBlockCreate] = []


class WorkoutUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[WorkoutStatus] = None
    scheduled_date: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    
    # Datos de ejecución
    actual_duration_minutes: Optional[int] = Field(None, ge=0)
    readiness_score_at_execution: Optional[float] = Field(None, ge=0, le=100)
    
    user_notes: Optional[str] = None


class WorkoutResponse(WorkoutBase):
    id: str
    user_id: str
    plan_id: Optional[str]
    
    status: WorkoutStatus
    completed_date: Optional[datetime]
    
    exercise_blocks: List[ExerciseBlockResponse]
    
    # Resumen
    total_sets_planned: int
    total_sets_completed: int
    total_volume_kg: float
    average_rpe_actual: Optional[float]
    
    created_at: datetime
    updated_at: Optional[datetime]
    version: int
    
    user_notes: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TRAINING PLAN SCHEMAS
# ============================================================================

class TrainingPlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    plan_type: WorkoutType = WorkoutType.STRENGTH
    duration_weeks: int = Field(default=4, ge=1, le=16)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_sessions_per_week: int = Field(default=3, ge=1, le=7)
    target_volume_per_session: int = Field(default=15, ge=5, le=40)


class TrainingPlanCreate(TrainingPlanBase):
    workouts: List[WorkoutCreate] = []
    generation_params: Optional[Dict[str, Any]] = None


class TrainingPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[WorkoutStatus] = None
    duration_weeks: Optional[int] = Field(None, ge=1, le=16)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_sessions_per_week: Optional[int] = Field(None, ge=1, le=7)


class TrainingPlanResponse(TrainingPlanBase):
    id: str
    user_id: str
    status: WorkoutStatus
    
    workouts: List[WorkoutResponse]
    
    created_at: datetime
    updated_at: Optional[datetime]
    version: int
    
    generation_params: Optional[Dict[str, Any]]
    adaptation_history: List[Dict[str, Any]]
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT FEEDBACK SCHEMAS
# ============================================================================

class WorkoutFeedbackCreate(BaseModel):
    workout_id: str
    
    # Feedback subjetivo
    overall_rpe: float = Field(..., ge=1, le=10)
    fatigue_level: int = Field(..., ge=1, le=10)
    enjoyment_level: int = Field(..., ge=1, le=10)
    motivation_level: int = Field(..., ge=1, le=10)
    sleep_quality_previous_night: Optional[int] = Field(None, ge=1, le=10)
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    
    # Feedback al sistema
    suggested_changes: List[str] = []
    user_notes: Optional[str] = None


class WorkoutFeedbackResponse(WorkoutFeedbackCreate):
    id: str
    user_id: str
    
    # Métricas calculadas
    completion_percentage: float
    volume_achievement: float
    rpe_accuracy: float
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TRAINING GENERATION SCHEMAS
# ============================================================================

class TrainingGenerationRequest(BaseModel):
    """Request para generar rutina automáticamente"""
    user_id: str
    
    # Contexto
    readiness_score: float = Field(..., ge=0, le=100)
    fatigue_score: Optional[float] = Field(None, ge=0, le=100)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    
    # Preferencias
    workout_type: WorkoutType = WorkoutType.STRENGTH
    target_duration_minutes: int = Field(default=60, ge=15, le=120)
    muscle_groups: List[MuscleGroup] = []
    exclude_exercises: List[str] = []  # IDs de ejercicios a excluir
    
    # Reglas
    base_rpe: float = Field(default=8.0, ge=1, le=10)
    total_sets: int = Field(default=15, ge=5, le=30)
    
    # Opcional: forzar ejercicios específicos
    include_exercises: List[str] = []  # IDs de ejercicios a incluir


class TrainingAdaptationRequest(BaseModel):
    """Request para adaptar rutina existente"""
    workout_id: str
    
    # Razón de adaptación
    reason: AdaptationReason
    custom_reason: Optional[str] = None
    
    # Nuevas condiciones
    new_readiness_score: Optional[float] = Field(None, ge=0, le=100)
    time_constraint_minutes: Optional[int] = Field(None, ge=15)
    
    # Cambios manuales solicitados
    requested_changes: Dict[str, Any] = {}  # {"decrease_volume": 0.2}


class SetFeedbackRequest(BaseModel):
    """Request para feedback de un set específico"""
    set_id: str
    
    # Ejecución real
    actual_reps: int = Field(..., ge=0, le=100)
    actual_weight_kg: float = Field(..., ge=0)
    actual_rpe: float = Field(..., ge=1, le=10)
    actual_tempo: Optional[str] = None
    actual_rest_seconds: int = Field(..., ge=0)
    
    # Estado
    status: SetStatus = SetStatus.COMPLETED
    
    # Notas
    user_notes: Optional[str] = None
    form_video_url: Optional[str] = None


# ============================================================================
# INTEGRATION SCHEMAS
# ============================================================================

class ExternalWorkoutPush(BaseModel):
    """Schema para exportar workout a app externa (ej: wger)"""
    workout_id: str
    target_app: str = Field(..., description="wger, strong, etc.")
    
    # Opciones
    include_feedback: bool = False
    include_notes: bool = True


class ExternalWorkoutPull(BaseModel):
    """Schema para importar workout desde app externa"""
    source_app: str
    external_workout_id: str
    user_id: str
    
    # Datos raw (formato depende de source_app)
    raw_data: Dict[str, Any]


class IntegrationResponse(BaseModel):
    success: bool
    message: str
    external_id: Optional[str] = None
    errors: List[str] = []


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class UserTrainingStats(BaseModel):
    """Estadísticas de entrenamiento del usuario"""
    user_id: str
    
    # Totales
    total_workouts: int
    total_workouts_completed: int
    total_sets_completed: int
    total_volume_kg: float
    
    # Promedios
    avg_rpe_last_7d: float
    avg_rpe_last_30d: float
    avg_workout_duration: float
    
    # Tendencias
    volume_trend: str  # increasing, stable, decreasing
    fatigue_trend: str
    
    # Estimaciones de rendimiento
    estimated_1rm_squat: Optional[float]
    estimated_1rm_bench: Optional[float]
    estimated_1rm_deadlift: Optional[float]


class FatigueAnalysis(BaseModel):
    """Análisis de fatiga acumulada"""
    user_id: str
    
    acute_load_7d: float  # Carga aguda
    chronic_load_28d: float  # Carga crónica
    acute_chronic_ratio: float  # Ratio ACWR
    
    fatigue_status: str  # low, optimal, high, excessive
    recommendation: str  # continue, caution, reduce, rest
    
    workload_distribution: Dict[str, float]  # Por grupo muscular
