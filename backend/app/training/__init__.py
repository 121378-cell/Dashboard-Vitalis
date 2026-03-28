"""
VITALIS Training Engine - Init
================================

Módulo principal del sistema de entrenamiento inteligente.
"""

from app.training.domain.models import (
    ExerciseLibrary, TrainingPlan, Workout, ExerciseBlock, ExerciseSet,
    WorkoutFeedback, TrainingAdaptation, UserTrainingProfile,
    SetStatus, WorkoutStatus, WorkoutType, MuscleGroup, AdaptationReason
)

from app.training.schemas import (
    ExerciseLibraryCreate, ExerciseLibraryResponse,
    WorkoutCreate, WorkoutResponse, WorkoutUpdate,
    ExerciseSetCreate, ExerciseSetUpdate, ExerciseSetResponse,
    ExerciseBlockCreate, ExerciseBlockResponse,
    TrainingGenerationRequest, TrainingAdaptationRequest, SetFeedbackRequest,
    WorkoutFeedbackCreate, WorkoutFeedbackResponse,
    ExternalWorkoutPush, ExternalWorkoutPull, IntegrationResponse
)

from app.training.use_cases import (
    WorkoutGenerator, WorkoutAdapter, TrainingAnalyzer,
    TrainingEntityFactory, TrainingConstants
)

__all__ = [
    # Domain
    "ExerciseLibrary", "TrainingPlan", "Workout", "ExerciseBlock", "ExerciseSet",
    "WorkoutFeedback", "TrainingAdaptation", "UserTrainingProfile",
    "SetStatus", "WorkoutStatus", "WorkoutType", "MuscleGroup", "AdaptationReason",
    # Schemas
    "ExerciseLibraryCreate", "ExerciseLibraryResponse",
    "WorkoutCreate", "WorkoutResponse", "WorkoutUpdate",
    "ExerciseSetCreate", "ExerciseSetUpdate", "ExerciseSetResponse",
    "ExerciseBlockCreate", "ExerciseBlockResponse",
    "TrainingGenerationRequest", "TrainingAdaptationRequest", "SetFeedbackRequest",
    "WorkoutFeedbackCreate", "WorkoutFeedbackResponse",
    "ExternalWorkoutPush", "ExternalWorkoutPull", "IntegrationResponse",
    # Use Cases
    "WorkoutGenerator", "WorkoutAdapter", "TrainingAnalyzer",
    "TrainingEntityFactory", "TrainingConstants"
]
