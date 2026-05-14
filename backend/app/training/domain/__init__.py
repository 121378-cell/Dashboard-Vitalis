"""
VITALIS Training Engine - Domain Init
========================================
"""

from app.training.domain.models import (
    ExerciseLibrary, TrainingPlan, PlannedWorkout, ExerciseBlock, ExerciseSet,
    WorkoutFeedback, TrainingAdaptation, UserTrainingProfile,
    SetStatus, WorkoutStatus, WorkoutType, MuscleGroup, AdaptationReason
)

__all__ = [
    "ExerciseLibrary", "TrainingPlan", "PlannedWorkout", "ExerciseBlock", "ExerciseSet",
    "WorkoutFeedback", "TrainingAdaptation", "UserTrainingProfile",
    "SetStatus", "WorkoutStatus", "WorkoutType", "MuscleGroup", "AdaptationReason"
]
