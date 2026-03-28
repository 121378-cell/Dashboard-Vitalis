"""
VITALIS Training Engine - Database Migration Script
===================================================

Crea las tablas necesarias para el sistema de entrenamiento.
Ejecutar: cd backend && python training_migration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.session import Base, engine
from app.training.domain import models as training_models

def migrate_training_tables():
    """Crea todas las tablas del Training Engine"""
    
    print("🚀 VITALIS Training Engine - Database Migration")
    print("=" * 60)
    
    try:
        # Crear todas las tablas del módulo training
        training_models.Base.metadata.create_all(bind=engine, tables=[
            training_models.ExerciseLibrary.__table__,
            training_models.TrainingPlan.__table__,
            training_models.Workout.__table__,
            training_models.ExerciseBlock.__table__,
            training_models.ExerciseSet.__table__,
            training_models.WorkoutFeedback.__table__,
            training_models.TrainingAdaptation.__table__,
            training_models.UserTrainingProfile.__table__,
        ])
        
        print("\n✅ Tablas creadas exitosamente:")
        print("   - exercise_library")
        print("   - training_plans")
        print("   - workouts")
        print("   - exercise_blocks")
        print("   - exercise_sets")
        print("   - workout_feedback")
        print("   - training_adaptations")
        print("   - user_training_profiles")
        
        # Seed ejercicios básicos
        seed_exercises()
        
        print("\n🎉 Migración completada!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def seed_exercises():
    """Inserta ejercicios básicos en la biblioteca"""
    from sqlalchemy.orm import Session
    from app.training.domain.models import ExerciseLibrary, MuscleGroup, WorkoutType
    
    print("\n📚 Seed: Insertando ejercicios base...")
    
    db = Session(bind=engine)
    
    exercises = [
        # Piernas
        {
            "name": "Squat",
            "description": "Sentadilla con barra",
            "primary_muscle": MuscleGroup.LEGS_QUADS.value,
            "secondary_muscles": [MuscleGroup.LEGS_GLUTES.value, MuscleGroup.LEGS_HAMSTRINGS.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 180,
            "equipment_needed": ["barbell", "rack"],
            "difficulty_level": 3
        },
        {
            "name": "Romanian Deadlift",
            "description": "Peso muerto rumano",
            "primary_muscle": MuscleGroup.LEGS_HAMSTRINGS.value,
            "secondary_muscles": [MuscleGroup.LEGS_GLUTES.value, MuscleGroup.BACK.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 150,
            "equipment_needed": ["barbell"],
            "difficulty_level": 3
        },
        {
            "name": "Leg Press",
            "description": "Prensa de piernas",
            "primary_muscle": MuscleGroup.LEGS_QUADS.value,
            "secondary_muscles": [MuscleGroup.LEGS_GLUTES.value],
            "exercise_type": WorkoutType.HYPERTROPHY.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 120,
            "equipment_needed": ["leg_press_machine"],
            "difficulty_level": 2
        },
        # Pecho
        {
            "name": "Bench Press",
            "description": "Press de banca con barra",
            "primary_muscle": MuscleGroup.CHEST.value,
            "secondary_muscles": [MuscleGroup.TRICEPS.value, MuscleGroup.SHOULDERS.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 180,
            "equipment_needed": ["barbell", "bench"],
            "difficulty_level": 3
        },
        {
            "name": "Dumbbell Flyes",
            "description": "Aperturas con mancuernas",
            "primary_muscle": MuscleGroup.CHEST.value,
            "secondary_muscles": [],
            "exercise_type": WorkoutType.HYPERTROPHY.value,
            "recommended_rpe_range": [7, 8],
            "recommended_rest_seconds": 90,
            "equipment_needed": ["dumbbells", "bench"],
            "difficulty_level": 2
        },
        # Espalda
        {
            "name": "Pull-ups",
            "description": "Dominadas",
            "primary_muscle": MuscleGroup.BACK.value,
            "secondary_muscles": [MuscleGroup.BICEPS.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 150,
            "equipment_needed": ["pull_up_bar"],
            "difficulty_level": 3
        },
        {
            "name": "Barbell Row",
            "description": "Remo con barra",
            "primary_muscle": MuscleGroup.BACK.value,
            "secondary_muscles": [MuscleGroup.BICEPS.value, MuscleGroup.LEGS_HAMSTRINGS.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 150,
            "equipment_needed": ["barbell"],
            "difficulty_level": 3
        },
        # Hombros
        {
            "name": "Overhead Press",
            "description": "Press militar",
            "primary_muscle": MuscleGroup.SHOULDERS.value,
            "secondary_muscles": [MuscleGroup.TRICEPS.value],
            "exercise_type": WorkoutType.STRENGTH.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 150,
            "equipment_needed": ["barbell"],
            "difficulty_level": 3
        },
        {
            "name": "Lateral Raises",
            "description": "Elevaciones laterales",
            "primary_muscle": MuscleGroup.SHOULDERS.value,
            "secondary_muscles": [],
            "exercise_type": WorkoutType.HYPERTROPHY.value,
            "recommended_rpe_range": [7, 8],
            "recommended_rest_seconds": 90,
            "equipment_needed": ["dumbbells"],
            "difficulty_level": 1
        },
        # Brazos
        {
            "name": "Barbell Curl",
            "description": "Curl de bíceps con barra",
            "primary_muscle": MuscleGroup.BICEPS.value,
            "secondary_muscles": [],
            "exercise_type": WorkoutType.HYPERTROPHY.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 90,
            "equipment_needed": ["barbell"],
            "difficulty_level": 2
        },
        {
            "name": "Tricep Dips",
            "description": "Fondos para tríceps",
            "primary_muscle": MuscleGroup.TRICEPS.value,
            "secondary_muscles": [MuscleGroup.CHEST.value],
            "exercise_type": WorkoutType.HYPERTROPHY.value,
            "recommended_rpe_range": [7, 9],
            "recommended_rest_seconds": 90,
            "equipment_needed": ["dip_station"],
            "difficulty_level": 2
        },
        # Core
        {
            "name": "Plank",
            "description": "Plancha abdominal",
            "primary_muscle": MuscleGroup.CORE.value,
            "secondary_muscles": [],
            "exercise_type": WorkoutType.ENDURANCE.value,
            "recommended_rpe_range": [6, 8],
            "recommended_rest_seconds": 60,
            "equipment_needed": [],
            "difficulty_level": 1
        },
    ]
    
    count = 0
    for ex_data in exercises:
        # Verificar si ya existe
        existing = db.query(ExerciseLibrary).filter(
            ExerciseLibrary.name == ex_data["name"]
        ).first()
        
        if not existing:
            exercise = ExerciseLibrary(**ex_data)
            db.add(exercise)
            count += 1
    
    db.commit()
    db.close()
    
    print(f"   ✅ {count} ejercicios insertados")


if __name__ == "__main__":
    success = migrate_training_tables()
    sys.exit(0 if success else 1)
