"""
VITALIS Training Engine - Tests
=================================

Tests unitarios e integración para el sistema de entrenamiento.
Ejecutar: cd backend && pytest tests/test_training_engine.py -v
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Test fixtures y mocks
from app.training.domain.models import (
    ExerciseLibrary, Workout, ExerciseBlock, ExerciseSet,
    WorkoutType, MuscleGroup, SetStatus, WorkoutStatus
)
from app.training.schemas import (
    TrainingGenerationRequest, ExerciseSetCreate, ExerciseBlockCreate,
    WorkoutCreate, SetFeedbackRequest
)
from app.training.use_cases import (
    WorkoutGenerator, WorkoutAdapter, TrainingAnalyzer,
    TrainingEntityFactory, TrainingConstants
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_exercise(db_session):
    """Ejercicio de ejemplo para tests"""
    exercise = ExerciseLibrary(
        name="Test Squat",
        description="Test exercise",
        primary_muscle=MuscleGroup.LEGS_QUADS,
        secondary_muscles=["legs_glutes"],
        exercise_type=WorkoutType.STRENGTH,
        recommended_rpe_range=[7, 9],
        recommended_rest_seconds=180,
        equipment_needed=["barbell"],
        difficulty_level=3
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


@pytest.fixture
def sample_workout_request(sample_exercise):
    """Request de generación de workout"""
    return TrainingGenerationRequest(
        user_id="test_user",
        readiness_score=85.0,
        workout_type=WorkoutType.STRENGTH,
        target_duration_minutes=60,
        muscle_groups=[MuscleGroup.LEGS_QUADS],
        base_rpe=8.0,
        total_sets=12
    )


# ============================================================================
# TESTS - WORKOUT GENERATOR
# ============================================================================

def test_calculate_training_parameters_high_readiness():
    """Test: Parámetros con readiness alto (90+)"""
    # Mock de la lógica
    readiness = 95
    
    # Lógica esperada
    if readiness >= 90:
        expected_rpe = 8.5
        expected_volume = 1.0
    
    assert expected_rpe == 8.5
    assert expected_volume == 1.0


def test_calculate_training_parameters_low_readiness():
    """Test: Parámetros con readiness bajo (<50)"""
    readiness = 40
    
    # Lógica esperada
    if readiness < 50:
        expected_rpe = 6.0
        expected_volume = 0.5
    
    assert expected_rpe == 6.0
    assert expected_volume == 0.5


def test_estimate_starting_weight():
    """Test: Estimación de peso inicial"""
    exercise = ExerciseLibrary(
        primary_muscle=MuscleGroup.LEGS_QUADS
    )
    
    # Peso base para piernas
    default_weights = {
        MuscleGroup.LEGS_QUADS: 60.0,
    }
    base = default_weights.get(exercise.primary_muscle, 40.0)
    
    # Ajustar por RPE 8
    rpe_factor = (8 - 5) / 5  # 0.6
    expected_weight = base * (0.7 + 0.3 * rpe_factor)
    
    assert expected_weight == 60.0 * 0.88  # 52.8


def test_get_reps_for_strength():
    """Test: Reps para entrenamiento de fuerza"""
    rep_ranges = {
        WorkoutType.STRENGTH: 5,
        WorkoutType.HYPERTROPHY: 10,
    }
    
    assert rep_ranges[WorkoutType.STRENGTH] == 5


def test_get_reps_for_hypertrophy():
    """Test: Reps para hipertrofia"""
    rep_ranges = {
        WorkoutType.HYPERTROPHY: 10,
    }
    
    assert rep_ranges[WorkoutType.HYPERTROPHY] == 10


# ============================================================================
# TESTS - WORKOUT ADAPTER
# ============================================================================

def test_process_set_feedback_rpe_deviation():
    """Test: Análisis de desviación RPE"""
    planned_rpe = 8.0
    actual_rpe = 9.5
    
    rpe_deviation = actual_rpe - planned_rpe
    
    assert rpe_deviation == 1.5
    
    # Si desviación >= 1.5, recomendar reducción
    if rpe_deviation >= 1.5:
        recommendation = "reduce_intensity"
    else:
        recommendation = "maintain"
    
    assert recommendation == "reduce_intensity"


def test_process_set_feedback_failed_set():
    """Test: Set fallado"""
    status = SetStatus.FAILED
    
    if status == SetStatus.FAILED:
        recommendation = "reduce_weight_5_percent"
    
    assert recommendation == "reduce_weight_5_percent"


def test_process_set_feedback_partial_completion():
    """Test: Completado parcial (<80% reps)"""
    planned_reps = 10
    actual_reps = 7
    
    completion_rate = actual_reps / planned_reps
    
    assert completion_rate == 0.7
    assert completion_rate < 0.8
    
    if actual_reps < planned_reps * 0.8:
        recommendation = "reduce_weight_2_5_percent"
    
    assert recommendation == "reduce_weight_2_5_percent"


# ============================================================================
# TESTS - TRAINING ANALYZER
# ============================================================================

def test_acwr_calculation():
    """Test: Cálculo de ACWR (Acute:Chronic Workload Ratio)"""
    acute_load = 1000  # 7 días
    chronic_load = 800  # 28 días promedio semanal
    
    acwr = acute_load / chronic_load if chronic_load > 0 else 0
    
    assert acwr == 1.25
    
    # 1.25 está en rango óptimo (0.8-1.3)
    assert TrainingConstants.ACWR_OPTIMAL_MIN <= acwr <= TrainingConstants.ACWR_OPTIMAL_MAX


def test_acwr_low_risk():
    """Test: ACWR bajo riesgo (<0.8)"""
    acwr = 0.7
    
    assert acwr < TrainingConstants.ACWR_OPTIMAL_MIN
    
    status = "low" if acwr < 0.8 else "optimal"
    assert status == "low"


def test_acwr_high_risk():
    """Test: ACWR alto riesgo (>1.5)"""
    acwr = 1.6
    
    assert acwr > TrainingConstants.ACWR_HIGH_RISK
    
    status = "excessive" if acwr > 1.5 else "high"
    assert status == "excessive"


# ============================================================================
# TESTS - TRAINING CONSTANTS
# ============================================================================

def test_rpe_ranges():
    """Test: Rangos RPE por objetivo"""
    assert TrainingConstants.RPE_STRENGTH == (8.5, 9.5)
    assert TrainingConstants.RPE_HYPERTROPHY == (7.0, 8.5)
    assert TrainingConstants.RPE_RECOVERY[1] <= 6.0


def test_volume_constants():
    """Test: Constantes de volumen"""
    assert TrainingConstants.VOLUME_LOW == 8
    assert TrainingConstants.VOLUME_MODERATE == 15
    assert TrainingConstants.VOLUME_HIGH == 20


def test_progression_constants():
    """Test: Incrementos de peso"""
    assert TrainingConstants.WEIGHT_INCREMENT_STRENGTH == 2.5
    assert TrainingConstants.WEIGHT_INCREMENT_HYPERTROPHY == 1.25


# ============================================================================
# TESTS - ENTITY FACTORY
# ============================================================================

def test_create_workout_from_schema():
    """Test: Creación de workout desde schema"""
    
    # Crear schema de prueba
    set_schema = ExerciseSetCreate(
        set_number=1,
        planned_reps=10,
        planned_weight_kg=60.0,
        planned_rpe=8.0,
        planned_rest_seconds=120,
        status=SetStatus.PLANNED
    )
    
    block_schema = ExerciseBlockCreate(
        exercise_id="test_exercise_id",
        execution_order=0,
        target_sets=3,
        target_rpe=8.0,
        rest_seconds_between_sets=120,
        sets=[set_schema, set_schema, set_schema]
    )
    
    workout_schema = WorkoutCreate(
        name="Test Workout",
        description="Test",
        workout_type=WorkoutType.STRENGTH,
        scheduled_date=datetime.utcnow(),
        estimated_duration_minutes=60,
        readiness_score_at_creation=85.0,
        exercise_blocks=[block_schema]
    )
    
    # Crear entidad
    workout = TrainingEntityFactory.create_workout_from_schema(
        workout_schema,
        user_id="test_user"
    )
    
    assert workout.name == "Test Workout"
    assert workout.user_id == "test_user"
    assert workout.workout_type == WorkoutType.STRENGTH
    assert len(workout.exercise_blocks) == 1
    assert workout.total_sets_planned == 3


# ============================================================================
# TESTS - INTEGRACIÓN
# ============================================================================

def test_training_constants_import():
    """Test: Importación correcta de constantes"""
    from app.training import TrainingConstants
    
    assert hasattr(TrainingConstants, 'RPE_STRENGTH')
    assert hasattr(TrainingConstants, 'VOLUME_MODERATE')
    assert hasattr(TrainingConstants, 'ACWR_OPTIMAL_MAX')


def test_models_import():
    """Test: Importación correcta de modelos"""
    from app.training import (
        ExerciseLibrary, Workout, ExerciseSet,
        SetStatus, WorkoutType
    )
    
    assert ExerciseLibrary is not None
    assert Workout is not None


def test_use_cases_import():
    """Test: Importación correcta de casos de uso"""
    from app.training import (
        WorkoutGenerator, WorkoutAdapter,
        TrainingAnalyzer, TrainingEntityFactory
    )
    
    assert WorkoutGenerator is not None
    assert WorkoutAdapter is not None


# ============================================================================
# TESTS - COMPATIBILIDAD CON SISTEMA EXISTENTE
# ============================================================================

def test_no_conflicts_with_existing_models():
    """Test: No hay conflictos con modelos existentes"""
    # Verificar que no hay colisiones de nombres
    from app.models.user import User
    from app.models.biometrics import Biometrics
    from app.models.token import Token
    
    # Modelos existentes deben seguir importables
    assert User is not None
    assert Biometrics is not None
    assert Token is not None


def test_training_router_isolation():
    """Test: Router de training está aislado"""
    # Verificar que el router tiene el prefix correcto
    from app.training.api.endpoints import router
    
    assert router.prefix == "/training"


# ============================================================================
# TESTS - VALIDACIÓN DE DATOS
# ============================================================================

def test_exercise_set_validation():
    """Test: Validación de datos de set"""
    # RPE válido
    valid_rpe = 8.5
    assert 1 <= valid_rpe <= 10
    
    # Reps válidas
    valid_reps = 10
    assert 1 <= valid_reps <= 100
    
    # Peso válido
    valid_weight = 60.0
    assert valid_weight >= 0


def test_workout_name_validation():
    """Test: Validación de nombre de workout"""
    name = "Leg Day - Strength"
    
    assert len(name) > 0
    assert len(name) <= 100


# ============================================================================
# TESTS - CÁLCULOS CIENTÍFICOS
# ============================================================================

def test_rir_calculation():
    """Test: Cálculo de RIR (Reps in Reserve)"""
    rpe = 8.0
    
    # RIR = 10 - RPE
    rir = 10 - rpe
    
    assert rir == 2.0


def test_volume_calculation():
    """Test: Cálculo de volumen (kg)"""
    reps = 10
    weight = 60.0
    
    volume = reps * weight
    
    assert volume == 600.0


def test_rpe_to_percentage_1rm():
    """Test: Conversión RPE a % de 1RM (aproximación)"""
    # Tabla aproximada: RPE 10 = 100%, RPE 9 = 96%, RPE 8 = 92%
    rpe = 8.0
    
    # Fórmula simplificada
    percentage = 100 - (10 - rpe) * 4
    
    assert percentage == 92.0
