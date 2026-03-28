"""
VITALIS Training Engine - Domain Models
========================================

Modelo de datos completo para el sistema de entrenamiento inteligente.
Diseñado con principios de Clean Architecture y ciencia del deporte.

Conceptos clave implementados:
- RPE (Rate of Perceived Exertion) / RIR (Reps in Reserve)
- Sobrecarga progresiva
- Fatiga acumulada y recuperación
- Periodización básica
- Versionado de workouts
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, 
    Text, Boolean, Enum, JSON, Interval, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func as sql_func
from datetime import datetime, timedelta
from enum import Enum as PyEnum
import uuid

from app.db.session import Base


# ============================================================================
# ENUMS
# ============================================================================

class SetStatus(PyEnum):
    """Estado de ejecución de un set"""
    PLANNED = "planned"           # Planificado, no ejecutado
    COMPLETED = "completed"       # Completado exitosamente
    FAILED = "failed"             # Fallado (no se alcanzaron reps)
    PARTIAL = "partial"           # Parcial (menos reps de lo planificado)
    SKIPPED = "skipped"         # Omitido


class WorkoutStatus(PyEnum):
    """Estado de un workout completo"""
    DRAFT = "draft"               # Borrador, no confirmado
    SCHEDULED = "scheduled"       # Programado para fecha
    IN_PROGRESS = "in_progress"   # En ejecución
    COMPLETED = "completed"       # Completado
    CANCELLED = "cancelled"       # Cancelado


class WorkoutType(PyEnum):
    """Tipo de entrenamiento"""
    STRENGTH = "strength"         # Fuerza máxima
    HYPERTROPHY = "hypertrophy"   # Hipertrofia
    POWER = "power"               # Potencia
    ENDURANCE = "endurance"       # Resistencia
    RECOVERY = "recovery"         # Recuperación activa
    DELoad = "deload"             # Descarga


class MuscleGroup(PyEnum):
    """Grupos musculares para clasificación"""
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    LEGS_QUADS = "legs_quads"
    LEGS_HAMSTRINGS = "legs_hamstrings"
    LEGS_GLUTES = "legs_glutes"
    CALVES = "calves"
    CORE = "core"
    FULL_BODY = "full_body"


class AdaptationReason(PyEnum):
    """Razones para adaptación de rutina"""
    HIGH_FATIGUE = "high_fatigue"           # Fatiga acumulada alta
    LOW_READINESS = "low_readiness"         # Readiness score bajo
    RPE_TOO_HIGH = "rpe_too_high"           # RPE real > objetivo
    RPE_TOO_LOW = "rpe_too_low"             # RPE real < objetivo
    TIME_CONSTRAINT = "time_constraint"     # Falta de tiempo
    OVERREACHING = "overreaching"           # Sobreentrenamiento
    PROGRESSION = "progression"             # Progresión normal


# ============================================================================
# MODELOS PRINCIPALES
# ============================================================================

class ExerciseLibrary(Base):
    """
    Biblioteca de ejercicios disponibles.
    Ejercicios predefinidos con metadata científica.
    """
    __tablename__ = "exercise_library"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Clasificación
    primary_muscle = Column(Enum(MuscleGroup), nullable=False)
    secondary_muscles = Column(JSON, default=list)  # Lista de grupos secundarios
    exercise_type = Column(Enum(WorkoutType), default=WorkoutType.STRENGTH)
    
    # Parámetros recomendados por ciencia del deporte
    recommended_rpe_range = Column(JSON, default=lambda: [7, 9])  # [min, max]
    recommended_rest_seconds = Column(Integer, default=120)
    recommended_tempo = Column(String, default="2-0-2")  # X-X-X (bajar-pausa-subir)
    
    # Metadata
    equipment_needed = Column(JSON, default=list)  # ["barbell", "rack"]
    difficulty_level = Column(Integer, default=1)  # 1-5
    video_url = Column(String)
    image_url = Column(String)
    
    # Relaciones
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())


class TrainingPlan(Base):
    """
    Plan de entrenamiento a largo plazo.
    Contiene múltiples Workouts organizados temporalmente.
    """
    __tablename__ = "training_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Metadata
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(WorkoutStatus), default=WorkoutStatus.SCHEDULED)
    
    # Periodización
    plan_type = Column(Enum(WorkoutType), default=WorkoutType.STRENGTH)
    duration_weeks = Column(Integer, default=4)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    
    # Parámetros de generación
    target_sessions_per_week = Column(Integer, default=3)
    target_volume_per_session = Column(Integer, default=15)  # Sets totales
    
    # Relaciones
    workouts = relationship("Workout", back_populates="plan", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    version = Column(Integer, default=1)
    
    # AI/Adaptación
    generation_params = Column(JSON, default=dict)  # Parámetros usados para generar
    adaptation_history = Column(JSON, default=list)  # Historial de cambios


class Workout(Base):
    """
    Sesión de entrenamiento individual.
    Contiene bloques de ejercicios con sets.
    """
    __tablename__ = "workouts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Metadata
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(WorkoutStatus), default=WorkoutStatus.SCHEDULED)
    workout_type = Column(Enum(WorkoutType), default=WorkoutType.STRENGTH)
    
    # Programación
    scheduled_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    estimated_duration_minutes = Column(Integer, default=60)
    actual_duration_minutes = Column(Integer)
    
    # Datos de contexto (para IA/heurísticas)
    readiness_score_at_creation = Column(Float)  # 0-100
    readiness_score_at_execution = Column(Float)
    fatigue_score = Column(Float)  # 0-100
    sleep_hours_last_night = Column(Float)
    
    # Relaciones
    plan = relationship("TrainingPlan", back_populates="workouts")
    exercise_blocks = relationship("ExerciseBlock", back_populates="workout", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    version = Column(Integer, default=1)
    
    # Resumen post-ejecución
    total_sets_planned = Column(Integer, default=0)
    total_sets_completed = Column(Integer, default=0)
    total_volume_kg = Column(Float, default=0)  # Suma (reps × weight)
    average_rpe_actual = Column(Float)
    
    # Notas del usuario
    user_notes = Column(Text)
    coach_notes = Column(Text)


class ExerciseBlock(Base):
    """
    Bloque de ejercicio dentro de un workout.
    Contiene múltiples sets del mismo ejercicio.
    """
    __tablename__ = "exercise_blocks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False)
    exercise_id = Column(String, ForeignKey("exercise_library.id"), nullable=False)
    
    # Orden de ejecución
    execution_order = Column(Integer, default=0)
    
    # Configuración del ejercicio en este workout
    target_sets = Column(Integer, default=3)
    target_rpe = Column(Float, default=8)  # RPE objetivo para todos los sets
    rest_seconds_between_sets = Column(Integer, default=120)
    tempo = Column(String, default="2-0-2")
    
    # Sobrecarga progresiva
    progression_scheme = Column(String, default="linear")  # linear, wave, rpe_based
    weight_increment_kg = Column(Float, default=0)  # Incremento planificado
    
    # Relaciones
    workout = relationship("Workout", back_populates="exercise_blocks")
    exercise = relationship("ExerciseLibrary")
    sets = relationship("ExerciseSet", back_populates="block", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    
    # Resumen
    block_completed = Column(Boolean, default=False)
    average_rpe_actual = Column(Float)


class ExerciseSet(Base):
    """
    Set individual con granularidad completa.
    Unidad mínima de trabajo con todos los parámetros científicos.
    """
    __tablename__ = "exercise_sets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    block_id = Column(String, ForeignKey("exercise_blocks.id"), nullable=False)
    
    # Orden
    set_number = Column(Integer, nullable=False)
    
    # Planificación (valores objetivo)
    planned_reps = Column(Integer, nullable=False)
    planned_weight_kg = Column(Float, nullable=False)
    planned_rpe = Column(Float, nullable=False)  # RPE objetivo
    planned_tempo = Column(String, default="2-0-2")
    planned_rest_seconds = Column(Integer, default=120)
    
    # Ejecución real (feedback del usuario)
    actual_reps = Column(Integer)
    actual_weight_kg = Column(Float)
    actual_rpe = Column(Float)  # RPE percibido post-set
    actual_tempo = Column(String)
    actual_rest_seconds = Column(Integer)
    
    # Estado
    status = Column(Enum(SetStatus), default=SetStatus.PLANNED)
    
    # Métricas derivadas
    volume_kg = Column(Float)  # actual_reps × actual_weight_kg
    rir = Column(Float)  # Reps in Reserve: 10 - actual_rpe
    
    # Análisis
    rpe_deviation = Column(Float)  # actual_rpe - planned_rpe
    performance_rating = Column(Float)  # 0-100, calculado
    
    # Relaciones
    block = relationship("ExerciseBlock", back_populates="sets")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Notas
    user_notes = Column(Text)
    form_video_url = Column(String)


class WorkoutFeedback(Base):
    """
    Feedback global de un workout completo.
    Para análisis de fatiga y adaptación de futuros workouts.
    """
    __tablename__ = "workout_feedback"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False, unique=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Feedback subjetivo
    overall_rpe = Column(Float)  # RPE promedio percibido del workout
    fatigue_level = Column(Integer)  # 1-10
    enjoyment_level = Column(Integer)  # 1-10
    motivation_level = Column(Integer)  # 1-10
    sleep_quality_previous_night = Column(Integer)  # 1-10
    stress_level = Column(Integer)  # 1-10
    
    # Feedback objetivo (comparado con plan)
    completion_percentage = Column(Float)  # sets completados / planificados
    volume_achievement = Column(Float)  # volumen real / planificado
    rpe_accuracy = Column(Float)  # qué tan cerca estuvieron los RPEs
    
    # Para adaptación
    suggested_changes = Column(JSON, default=list)  # ["increase_rest", "decrease_volume"]
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    user_notes = Column(Text)


class TrainingAdaptation(Base):
    """
    Registro de adaptaciones aplicadas a un plan/workout.
    Auditoría de decisiones de la IA/heurísticas.
    """
    __tablename__ = "training_adaptations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Razón de adaptación
    adaptation_reason = Column(Enum(AdaptationReason), nullable=False)
    trigger_value = Column(Float)  # Valor que disparó la adaptación
    trigger_threshold = Column(Float)  # Umbral superado
    
    # Cambios aplicados (diff)
    changes_applied = Column(JSON, nullable=False)  # {"rpe_adjustment": -1, "volume_reduction": 0.2}
    
    # Contexto
    readiness_score_at_adaptation = Column(Float)
    fatigue_score = Column(Float)
    recent_workouts_summary = Column(JSON)  # Resumen de últimos workouts
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    applied_by = Column(String, default="system")  # system, user, coach
    notes = Column(Text)


class UserTrainingProfile(Base):
    """
    Perfil de entrenamiento persistente del usuario.
    Preferencias, historial y parámetros para personalización.
    """
    __tablename__ = "user_training_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Preferencias
    preferred_workout_duration_minutes = Column(Integer, default=60)
    preferred_workouts_per_week = Column(Integer, default=3)
    preferred_training_type = Column(Enum(WorkoutType), default=WorkoutType.STRENGTH)
    
    # Límites y capacidades
    max_lifts = Column(JSON, default=dict)  # {"squat": 100, "bench": 80}
    training_age_months = Column(Integer, default=0)
    injury_history = Column(JSON, default=list)
    
    # Parámetros de progresión
    base_rpe_target = Column(Float, default=8)
    volume_tolerance = Column(Float, default=1.0)  # multiplicador
    recovery_capacity = Column(Float, default=1.0)  # multiplicador
    
    # Historial de adaptación
    average_workout_rpe_last_4 = Column(Float, default=0)
    total_volume_last_week = Column(Float, default=0)
    fatigue_trend = Column(String, default="stable")  # improving, stable, worsening
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    
    # Configuración personalizada
    custom_params = Column(JSON, default=dict)
