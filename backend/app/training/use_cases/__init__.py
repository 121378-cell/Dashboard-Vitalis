"""
VITALIS Training Engine - Use Cases (Core Business Logic)
=========================================================

Lógica de generación, adaptación y análisis de entrenamientos.
Implementación basada en reglas + heurísticas científicas.

Conceptos implementados:
- RPE/RIR como métrica central
- Sobrecarga progresiva
- Fatiga acumulada (ACWR)
- Periodización básica
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import logging
import math

from app.training.domain.models import (
    ExerciseLibrary, TrainingPlan, PlannedWorkout, ExerciseBlock, ExerciseSet,
    WorkoutFeedback, TrainingAdaptation, UserTrainingProfile,
    SetStatus, WorkoutStatus, WorkoutType, MuscleGroup, AdaptationReason
)
from app.training.schemas import (
    TrainingGenerationRequest, TrainingAdaptationRequest, SetFeedbackRequest,
    WorkoutCreate, ExerciseBlockCreate, ExerciseSetCreate
)
from app.models.biometrics import Biometrics
from app.models.user import User

logger = logging.getLogger("app.training.use_cases")


# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

class TrainingConstants:
    """Constantes basadas en ciencia del entrenamiento"""
    
    # Rangos RPE por objetivo
    RPE_STRENGTH = (8.5, 9.5)
    RPE_HYPERTROPHY = (7.0, 8.5)
    RPE_POWER = (7.0, 8.0)
    RPE_ENDURANCE = (6.0, 7.5)
    RPE_RECOVERY = (4.0, 6.0)
    
    # Volumen por grupo muscular por sesión (sets)
    VOLUME_LOW = 8
    VOLUME_MODERATE = 15
    VOLUME_HIGH = 20
    
    # Límites de recuperación
    MAX_SESSIONS_PER_WEEK = 6
    MIN_REST_DAYS = 1
    
    # Progresión
    WEIGHT_INCREMENT_STRENGTH = 2.5  # kg
    WEIGHT_INCREMENT_HYPERTROPHY = 1.25  # kg
    
    # Fatiga
    ACWR_OPTIMAL_MIN = 0.8
    ACWR_OPTIMAL_MAX = 1.3
    ACWR_HIGH_RISK = 1.5


# ============================================================================
# GENERADOR DE RUTINAS (AI + HEURÍSTICAS)
# ============================================================================

class WorkoutGenerator:
    """
    Generador inteligente de rutinas basado en reglas heurísticas.
    Combina ciencia del deporte con inputs del usuario.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.constants = TrainingConstants()
    
    def generate_workout(self, request: TrainingGenerationRequest) -> WorkoutCreate:
        """
        Genera un workout completo basado en parámetros de entrada.
        
        Algoritmo:
        1. Determinar intensidad objetivo (RPE) basado en readiness
        2. Seleccionar ejercicios según grupos musculares
        3. Distribuir volumen (sets) óptimamente
        4. Calcular progresión de cargas
        """
        logger.info(f"[TRAINING_ENGINE] Generando workout para user {request.user_id}")
        
        # Paso 1: Determinar parámetros base según readiness
        base_rpe, volume_factor, rest_multiplier = self._calculate_training_parameters(
            request.readiness_score,
            request.fatigue_score,
            request.stress_level
        )
        
        # Paso 2: Seleccionar ejercicios
        exercises = self._select_exercises(
            request.workout_type,
            request.muscle_groups,
            request.exclude_exercises,
            request.include_exercises
        )
        
        # Paso 3: Crear bloques con sets
        exercise_blocks = []
        for exercise in exercises:
            block = self._create_exercise_block(
                exercise,
                request.workout_type,
                base_rpe,
                volume_factor,
                rest_multiplier,
                request.total_sets // len(exercises)
            )
            exercise_blocks.append(block)
        
        # Paso 4: Construir workout
        workout = WorkoutCreate(
            name=self._generate_workout_name(request.workout_type, request.muscle_groups),
            description=self._generate_description(request),
            workout_type=request.workout_type,
            scheduled_date=datetime.utcnow() + timedelta(days=1),
            estimated_duration_minutes=request.target_duration_minutes,
            readiness_score_at_creation=request.readiness_score,
            exercise_blocks=exercise_blocks,
            plan_id=None
        )
        
        logger.info(f"[TRAINING_ENGINE] Workout generado: {len(exercise_blocks)} ejercicios")
        return workout
    
    def _calculate_training_parameters(
        self,
        readiness: float,
        fatigue: Optional[float],
        stress: Optional[int]
    ) -> Tuple[float, float, float]:
        """
        Calcula parámetros de entrenamiento basado en estado del usuario.
        
        Returns:
            (base_rpe, volume_factor, rest_multiplier)
        """
        # RPE base según readiness
        if readiness >= 90:
            base_rpe = 8.5
            volume_factor = 1.0
            rest_multiplier = 1.0
        elif readiness >= 75:
            base_rpe = 8.0
            volume_factor = 0.95
            rest_multiplier = 1.0
        elif readiness >= 60:
            base_rpe = 7.5
            volume_factor = 0.85
            rest_multiplier = 1.1
        elif readiness >= 40:
            base_rpe = 7.0
            volume_factor = 0.75
            rest_multiplier = 1.2
        else:
            # Muy fatigado - sesión de recuperación
            base_rpe = 6.0
            volume_factor = 0.5
            rest_multiplier = 1.3
        
        # Ajustar por fatiga adicional
        if fatigue and fatigue > 70:
            base_rpe -= 0.5
            volume_factor *= 0.8
        
        # Ajustar por estrés
        if stress and stress > 7:
            base_rpe -= 0.5
            volume_factor *= 0.9
        
        return max(5.0, base_rpe), max(0.3, volume_factor), min(1.5, rest_multiplier)
    
    def _select_exercises(
        self,
        workout_type: WorkoutType,
        muscle_groups: List[MuscleGroup],
        exclude: List[str],
        include: List[str]
    ) -> List[ExerciseLibrary]:
        """Selecciona ejercicios de la biblioteca"""
        
        query = self.db.query(ExerciseLibrary)
        
        # Filtros básicos
        if muscle_groups:
            query = query.filter(ExerciseLibrary.primary_muscle.in_(muscle_groups))
        
        query = query.filter(ExerciseLibrary.exercise_type == workout_type)
        
        if exclude:
            query = query.filter(~ExerciseLibrary.id.in_(exclude))
        
        # Ejercicios obligatorios primero
        exercises = []
        if include:
            mandatory = self.db.query(ExerciseLibrary).filter(
                ExerciseLibrary.id.in_(include)
            ).all()
            exercises.extend(mandatory)
        
        # Completar con ejercicios adicionales
        existing_ids = {e.id for e in exercises}
        additional = query.filter(
            ~ExerciseLibrary.id.in_(existing_ids)
        ).limit(6 - len(exercises)).all()
        
        exercises.extend(additional)
        
        # Ordenar: compuestos primero, aislamientos después
        exercises.sort(key=lambda e: 0 if e.difficulty_level <= 2 else 1)
        
        return exercises[:6]  # Máximo 6 ejercicios
    
    def _create_exercise_block(
        self,
        exercise: ExerciseLibrary,
        workout_type: WorkoutType,
        base_rpe: float,
        volume_factor: float,
        rest_multiplier: float,
        target_sets: int
    ) -> ExerciseBlockCreate:
        """Crea un bloque de ejercicio con sets"""
        
        # Ajustar sets por volumen
        adjusted_sets = max(2, int(target_sets * volume_factor))
        
        # Calcular RPE por set (progresión)
        sets = []
        for i in range(adjusted_sets):
            # Primeros sets: RPE más bajo (warmup effect)
            # Últimos sets: RPE objetivo
            if adjusted_sets == 1:
                set_rpe = base_rpe
            elif i < adjusted_sets // 2:
                set_rpe = base_rpe - 0.5
            else:
                set_rpe = base_rpe
            
            # Estimar peso basado en ejercicio
            estimated_weight = self._estimate_starting_weight(exercise, set_rpe)
            
            set_data = ExerciseSetCreate(
                set_number=i + 1,
                planned_reps=self._get_reps_for_type(workout_type),
                planned_weight_kg=estimated_weight,
                planned_rpe=round(set_rpe, 1),
                planned_tempo=exercise.recommended_tempo,
                planned_rest_seconds=int(exercise.recommended_rest_seconds * rest_multiplier),
                status=SetStatus.PLANNED
            )
            sets.append(set_data)
        
        return ExerciseBlockCreate(
            exercise_id=exercise.id,
            execution_order=0,  # Se ordena después
            target_sets=adjusted_sets,
            target_rpe=base_rpe,
            rest_seconds_between_sets=int(exercise.recommended_rest_seconds * rest_multiplier),
            tempo=exercise.recommended_tempo,
            progression_scheme="linear",
            weight_increment_kg=TrainingConstants.WEIGHT_INCREMENT_STRENGTH,
            sets=sets
        )
    
    def _estimate_starting_weight(self, exercise: ExerciseLibrary, rpe: float) -> float:
        """Estima peso inicial basado en ejercicio y RPE"""
        # En implementación real, usaría historial del usuario
        # Stub con valores conservadores
        default_weights = {
            MuscleGroup.LEGS_QUADS: 60.0,
            MuscleGroup.LEGS_HAMSTRINGS: 50.0,
            MuscleGroup.CHEST: 40.0,
            MuscleGroup.BACK: 50.0,
            MuscleGroup.SHOULDERS: 30.0,
        }
        base = default_weights.get(exercise.primary_muscle, 40.0)
        
        # Ajustar por RPE (RPE más alto = peso más alto)
        rpe_factor = (rpe - 5) / 5  # 0.0 a 1.0
        return round(base * (0.7 + 0.3 * rpe_factor), 1)
    
    def _get_reps_for_type(self, workout_type: WorkoutType) -> int:
        """Reps recomendadas según tipo de entrenamiento"""
        rep_ranges = {
            WorkoutType.STRENGTH: 5,
            WorkoutType.HYPERTROPHY: 10,
            WorkoutType.POWER: 3,
            WorkoutType.ENDURANCE: 15,
            WorkoutType.RECOVERY: 12,
        }
        return rep_ranges.get(workout_type, 10)
    
    def _generate_workout_name(
        self,
        workout_type: WorkoutType,
        muscle_groups: List[MuscleGroup]
    ) -> str:
        """Genera nombre descriptivo"""
        type_names = {
            WorkoutType.STRENGTH: "Fuerza",
            WorkoutType.HYPERTROPHY: "Hipertrofia",
            WorkoutType.POWER: "Potencia",
            WorkoutType.ENDURANCE: "Resistencia",
        }
        
        type_name = type_names.get(workout_type, "Entrenamiento")
        
        if muscle_groups:
            group_names = [mg.value.replace("_", " ").title() for mg in muscle_groups]
            return f"{type_name} - {', '.join(group_names[:2])}"
        
        return f"{type_name} - {datetime.now().strftime('%d/%m')}"
    
    def _generate_description(self, request: TrainingGenerationRequest) -> str:
        """Genera descripción con contexto"""
        readiness_text = "alta" if request.readiness_score >= 75 else "moderada" if request.readiness_score >= 50 else "baja"
        return f"Rutina generada para readiness {readiness_text} ({request.readiness_score:.0f}/100). Enfocada en {request.workout_type.value}."


# ============================================================================
# ADAPTADOR DE RUTINAS (FEEDBACK LOOP)
# ============================================================================

class WorkoutAdapter:
    """
    Adapta rutinas existentes basado en feedback real y estado actual.
    Implementa el ciclo de mejora continua.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def adapt_workout(
        self,
        workout: PlannedWorkout,
        request: TrainingAdaptationRequest
    ) -> List[Dict[str, Any]]:
        """
        Adapta un workout existente basado en nueva información.
        
        Returns:
            Lista de cambios aplicados
        """
        logger.info(f"[TRAINING_ENGINE] Adaptando workout {workout.id}")
        
        changes = []
        
        # Adaptación por readiness bajo
        if request.new_readiness_score and request.new_readiness_score < 60:
            changes.extend(self._adapt_for_low_readiness(workout, request.new_readiness_score))
        
        # Adaptación por tiempo limitado
        if request.time_constraint_minutes:
            changes.extend(self._adapt_for_time_constraint(workout, request.time_constraint_minutes))
        
        # Adaptación por razón específica
        if request.reason == AdaptationReason.HIGH_FATIGUE:
            changes.extend(self._reduce_volume(workout, 0.3))
        elif request.reason == AdaptationReason.RPE_TOO_HIGH:
            changes.extend(self._reduce_intensity(workout, 1.0))
        
        # Aplicar cambios manuales
        if request.requested_changes:
            changes.extend(self._apply_manual_changes(workout, request.requested_changes))
        
        # Registrar adaptación
        self._log_adaptation(workout, request, changes)
        
        logger.info(f"[TRAINING_ENGINE] Adaptación completada: {len(changes)} cambios")
        return changes
    
    def process_set_feedback(
        self,
        set_data: ExerciseSet,
        feedback: SetFeedbackRequest
    ) -> Dict[str, Any]:
        """
        Procesa feedback de un set individual y genera recomendaciones.
        
        Análisis:
        - Diferencia RPE planificado vs real
        - Si falló: recomendar reducción
        - Si RPE muy bajo: recomendar progresión
        """
        analysis = {
            "rpe_deviation": feedback.actual_rpe - set_data.planned_rpe,
            "volume_achieved": feedback.actual_reps * feedback.actual_weight_kg,
            "recommendation": None,
            "confidence": 0.8
        }
        
        # Análisis de desviación
        if feedback.status == SetStatus.FAILED:
            analysis["recommendation"] = "reduce_weight_5_percent"
            analysis["message"] = "Set fallado - reducir peso 5%"
        elif feedback.actual_reps < set_data.planned_reps * 0.8:
            analysis["recommendation"] = "reduce_weight_2_5_percent"
            analysis["message"] = "Reps insuficientes - reducir peso"
        elif analysis["rpe_deviation"] > 1.5:
            analysis["recommendation"] = "reduce_intensity"
            analysis["message"] = f"RPE {feedback.actual_rpe} muy alto vs {set_data.planned_rpe} planificado"
        elif analysis["rpe_deviation"] < -1.5:
            analysis["recommendation"] = "increase_weight"
            analysis["message"] = f"RPE {feedback.actual_rpe} bajo - considerar subir peso"
        else:
            analysis["recommendation"] = "maintain"
            analysis["message"] = "RPE en rango óptimo - mantener carga"
        
        return analysis
    
    def _adapt_for_low_readiness(self, workout: PlannedWorkout, readiness: float) -> List[Dict]:
        """Reduce intensidad y volumen para readiness bajo"""
        changes = []
        
        # Reducir RPE objetivo en todos los sets
        for block in workout.exercise_blocks:
            for set_data in block.sets:
                old_rpe = set_data.planned_rpe
                new_rpe = max(5.0, old_rpe - 1.5)
                set_data.planned_rpe = new_rpe
                changes.append({
                    "type": "reduce_rpe",
                    "block_id": block.id,
                    "old_value": old_rpe,
                    "new_value": new_rpe,
                    "reason": f"Low readiness: {readiness}"
                })
        
        return changes
    
    def _adapt_for_time_constraint(self, workout: PlannedWorkout, minutes: int) -> List[Dict]:
        """Reduce ejercicios para ajustarse a tiempo disponible"""
        changes = []
        
        estimated_time = workout.estimated_duration_minutes
        if estimated_time > minutes:
            # Eliminar ejercicios de aislamiento (últimos en orden)
            isolation_blocks = [b for b in workout.exercise_blocks 
                              if b.exercise.difficulty_level >= 3]
            
            while workout.estimated_duration_minutes > minutes and isolation_blocks:
                block = isolation_blocks.pop()
                workout.exercise_blocks.remove(block)
                changes.append({
                    "type": "remove_exercise",
                    "block_id": block.id,
                    "exercise_name": block.exercise.name,
                    "reason": f"Time constraint: {minutes}min"
                })
                workout.estimated_duration_minutes -= 10  # Estimación
        
        return changes
    
    def _reduce_volume(self, workout: PlannedWorkout, factor: float) -> List[Dict]:
        """Reduce volumen por factor dado"""
        changes = []
        
        for block in workout.exercise_blocks:
            old_sets = len(block.sets)
            new_sets = max(2, int(old_sets * (1 - factor)))
            
            if new_sets < old_sets:
                # Eliminar sets del final
                block.sets = block.sets[:new_sets]
                block.target_sets = new_sets
                
                changes.append({
                    "type": "reduce_sets",
                    "block_id": block.id,
                    "old_value": old_sets,
                    "new_value": new_sets,
                    "reason": "High fatigue"
                })
        
        return changes
    
    def _reduce_intensity(self, workout: PlannedWorkout, rpe_reduction: float) -> List[Dict]:
        """Reduce intensidad (RPE)"""
        changes = []
        
        for block in workout.exercise_blocks:
            for set_data in block.sets:
                old_rpe = set_data.planned_rpe
                new_rpe = max(5.0, old_rpe - rpe_reduction)
                set_data.planned_rpe = new_rpe
                
                changes.append({
                    "type": "reduce_rpe",
                    "set_id": set_data.id,
                    "old_value": old_rpe,
                    "new_value": new_rpe
                })
        
        return changes
    
    def _apply_manual_changes(
        self,
        workout: PlannedWorkout,
        changes: Dict[str, Any]
    ) -> List[Dict]:
        """Aplica cambios manuales solicitados"""
        applied = []
        
        if "decrease_volume" in changes:
            factor = changes["decrease_volume"]
            applied.extend(self._reduce_volume(workout, factor))
        
        if "increase_rest" in changes:
            factor = changes["increase_rest"]
            for block in workout.exercise_blocks:
                block.rest_seconds_between_sets = int(
                    block.rest_seconds_between_sets * factor
                )
                for set_data in block.sets:
                    set_data.planned_rest_seconds = int(
                        set_data.planned_rest_seconds * factor
                    )
                applied.append({
                    "type": "increase_rest",
                    "block_id": block.id,
                    "factor": factor
                })
        
        return applied
    
    def _log_adaptation(
        self,
        workout: PlannedWorkout,
        request: TrainingAdaptationRequest,
        changes: List[Dict]
    ):
        """Registra adaptación para auditoría"""
        adaptation = TrainingAdaptation(
            workout_id=workout.id,
            user_id=workout.user_id,
            adaptation_reason=request.reason,
            changes_applied=changes,
            readiness_score_at_adaptation=request.new_readiness_score
        )
        self.db.add(adaptation)
        self.db.commit()


# ============================================================================
# ANÁLISIS Y ESTADÍSTICAS
# ============================================================================

class TrainingAnalyzer:
    """
    Análisis de datos de entrenamiento para insights y decisiones.
    Implementa métricas de ciencia del deporte.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_acwr(self, user_id: str) -> Dict[str, float]:
        """
        Calcula Acute:Chronic Workload Ratio.
        
        ACWR = Carga Aguda (7 días) / Carga Crónica (28 días promedio)
        
        Rangos:
        - < 0.8: Bajo (bajo estímulo)
        - 0.8-1.3: Óptimo
        - 1.3-1.5: Alto riesgo
        - > 1.5: Alto riesgo de lesión
        """
        now = datetime.utcnow()
        acute_start = now - timedelta(days=7)
        chronic_start = now - timedelta(days=28)
        
        # Carga aguda (últimos 7 días)
        acute_load = self._calculate_volume(user_id, acute_start, now)
        
        # Carga crónica (28 días promedio semanal)
        chronic_load_4weeks = self._calculate_volume(user_id, chronic_start, now)
        chronic_load = chronic_load_4weeks / 4  # Promedio semanal
        
        if chronic_load == 0:
            acwr = 0
        else:
            acwr = acute_load / chronic_load
        
        # Determinar estado
        if acwr < 0.8:
            status = "low"
        elif acwr <= 1.3:
            status = "optimal"
        elif acwr <= 1.5:
            status = "high"
        else:
            status = "excessive"
        
        return {
            "acute_load": acute_load,
            "chronic_load": chronic_load,
            "acwr": acwr,
            "status": status,
            "recommendation": self._acwr_recommendation(acwr)
        }
    
    def _calculate_volume(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> float:
        """Calcula volumen total (kg) en período"""
        sets = self.db.query(ExerciseSet).join(ExerciseBlock).join(PlannedWorkout).filter(
            PlannedWorkout.user_id == user_id,
            ExerciseSet.status == SetStatus.COMPLETED,
            ExerciseSet.completed_at >= start,
            ExerciseSet.completed_at <= end
        ).all()
        
        return sum(s.actual_reps * s.actual_weight_kg for s in sets 
                  if s.actual_reps and s.actual_weight_kg)
    
    def _acwr_recommendation(self, acwr: float) -> str:
        """Recomendación basada en ACWR"""
        if acwr < 0.8:
            return "Aumentar volumen gradualmente"
        elif acwr <= 1.3:
            return "Continuar con carga actual"
        elif acwr <= 1.5:
            return "Reducir volumen 10-15%"
        else:
            return "Reducir volumen 20%+ y descansar"
    
    def analyze_rpe_trends(self, user_id: str, days: int = 14) -> Dict[str, Any]:
        """Analiza tendencias de RPE"""
        start = datetime.utcnow() - timedelta(days=days)
        
        sets = self.db.query(ExerciseSet).join(ExerciseBlock).join(PlannedWorkout).filter(
            PlannedWorkout.user_id == user_id,
            ExerciseSet.status == SetStatus.COMPLETED,
            ExerciseSet.completed_at >= start,
            ExerciseSet.actual_rpe != None
        ).all()
        
        if not sets:
            return {"error": "No hay datos suficientes"}
        
        rpes = [s.actual_rpe for s in sets]
        avg_rpe = sum(rpes) / len(rpes)
        
        # Dividir en primera y segunda mitad
        mid = len(rpes) // 2
        first_half = sum(rpes[:mid]) / len(rpes[:mid]) if rpes[:mid] else 0
        second_half = sum(rpes[mid:]) / len(rpes[mid:]) if rpes[mid:] else 0
        
        trend = "improving" if second_half < first_half else "worsening" if second_half > first_half else "stable"
        
        return {
            "average_rpe": round(avg_rpe, 2),
            "trend": trend,
            "total_sets": len(sets),
            "rpe_distribution": {
                "easy": len([r for r in rpes if r < 7]),
                "moderate": len([r for r in rpes if 7 <= r < 9]),
                "hard": len([r for r in rpes if r >= 9])
            }
        }


# ============================================================================
# GENERADOR DE PLANES DE ENTRENAMIENTO
# ============================================================================

class TrainingPlanGenerator:
    """
    Generador de planes de entrenamiento a largo plazo con periodización.
    Crea macros-ciclos basados en objetivos, experiencia y disponibilidad.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.workout_generator = WorkoutGenerator(db)
        self.constants = TrainingConstants()
    
    def generate_training_plan(self, user_id: str, weeks: int = 4, 
                             workouts_per_week: int = 3, 
                             workout_type: WorkoutType = WorkoutType.STRENGTH,
                             goal: Optional[str] = None,
                             experience_level: str = "intermediate",
                             available_days: Optional[List[int]] = None) -> TrainingPlanCreate:
        """
        Genera un plan de entrenamiento completo con periodización.
        
        Args:
            user_id: ID del usuario
            weeks: Número de semanas del plan
            workouts_per_week: Sesiones por semana
            workout_type: Tipo principal de entrenamiento
            goal: Objetivo específico (strength_gain, weight_loss, etc.)
            experience_level: beginner, intermediate, advanced
            available_days: Días de la semana disponibles (0=lunes, 6=domingo)
            
        Returns:
            TrainingPlanComplete con workouts generados para cada semana
        """
        # Obtener perfil de entrenamiento del usuario
        user_profile = self._get_user_training_profile(user_id)
        
        # Determinar parámetros de periodización basado en objetivo y experiencia
        periodization_params = self._determine_periodization_params(
            goal, experience_level, weeks
        )
        
        # Generar workouts para cada semana
        all_workouts = []
        
        for week in range(weeks):
            # Calcular factores de semana basada en periodización
            week_factor = self._calculate_week_factor(
                week, weeks, periodization_params
            )
            
            # Generar workouts para esta semana
            week_workouts = self._generate_week_workouts(
                user_id, week + 1, workouts_per_week, 
                workout_type, week_factor, user_profile,
                available_days
            )
            
            all_workouts.extend(week_workouts)
        
        # Crear nombre y descripción del plan
        plan_name = self._generate_plan_name(workout_type, goal, weeks)
        plan_description = self._generate_plan_description(
            workout_type, goal, weeks, experience_level
        )
        
        # Parámetros de generación para tracking
        generation_params = {
            "weeks": weeks,
            "workouts_per_week": workouts_per_week,
            "workout_type": workout_type.value if hasattr(workout_type, 'value') else str(workout_type),
            "goal": goal,
            "experience_level": experience_level,
            "available_days": available_days,
            "periodization_type": periodization_params.get("type", "linear")
        }
        
        return TrainingPlanCreate(
            name=plan_name,
            description=plan_description,
            plan_type=workout_type,
            duration_weeks=weeks,
            target_sessions_per_week=workouts_per_week,
            workouts=all_workouts,
            generation_params=generation_params
        )
    
    def _get_user_training_profile(self, user_id: str) -> Dict[str, Any]:
        """Obtiene el perfil de entrenamiento del usuario"""
        profile = self.db.query(UserTrainingProfile).filter(
            UserTrainingProfile.user_id == user_id
        ).first()
        
        if not profile:
            # Crear perfil por defecto si no existe
            profile = UserTrainingProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        
        return {
            "preferred_duration": profile.preferred_workout_duration_minutes,
            "preferred_freq": profile.preferred_workouts_per_week,
            "preferred_type": profile.preferred_training_type,
            "max_lifts": profile.max_lifts or {},
            "training_age": profile.training_age_months or 0,
            "injury_history": profile.injury_history or [],
            "volume_tolerance": profile.volume_tolerance or 1.0,
            "recovery_capacity": profile.recovery_capacity or 1.0,
            "base_rpe_target": profile.base_rpe_target or 8.0
        }
    
    def _determine_periodization_params(self, goal: Optional[str], 
                                      experience_level: str, 
                                      weeks: int) -> Dict[str, Any]:
        """Determina parámetros de periodización basado en objetivo y experiencia"""
        
        # Parámetros por defecto (periodización lineal básica)
        params = {
            "type": "linear",
            "intensity_curve": "linear_increase",
            "volume_curve": "linear_decrease",
            "deload_frequency": 4,  # Cada 4 semanas
            "phases": []
        }
        
        # Ajustar basado en objetivo
        if goal == "strength_gain":
            params.update({
                "type": "undulating",
                "intensity_curve": "wave_like",
                "volume_curve": "step_wave",
                "focus": "intensity_over_volume",
                "rep_range_primary": (1, 5),  # Fuerza máxima
                "rep_range_secondary": (6, 10)  # Hipertrofia secundaria
            })
        elif goal == "hypertrophy":
            params.update({
                "type": "linear",
                "intensity_curve": "moderate_increase",
                "volume_curve": "moderate_decrease",
                "focus": "balanced",
                "rep_range_primary": (6, 12),  # Hipertrofia principal
                "rep_range_secondary": (12, 20)  # Resistencia muscular
            })
        elif goal == "endurance":
            params.update({
                "type": "linear",
                "intensity_curve": "stable",
                "volume_curve": "linear_increase",
                "focus": "volume_over_intensity",
                "rep_range_primary": (12, 20),  # Resistencia
                "rep_range_secondary": (20, 30)  # Resistencia extrema
            })
        elif goal == "weight_loss":
            params.update({
                "type": "hybrid",
                "intensity_curve": "interval_based",
                "volume_curve": "high_volume",
                "focus": "metabolic_cost",
                "rep_range_primary": (8, 15),  # Moderado para mayor gasto
                "rep_range_secondary": (15, 25)  # Alta resistencia
            })
        
        # Ajustar basado en nivel de experiencia
        if experience_level == "beginner":
            params.update({
                "intensity_modifier": 0.7,  # Comenzar más conservador
                "complexity": "simple",
                "exercise_variety": "low",
                "technique_focus": True
            })
        elif experience_level == "advanced":
            params.update({
                "intensity_modifier": 1.2,  # Puede manejar más intensidad
                "complexity": "high",
                "exercise_variety": "high",
                "technique_focus": False
            })
        else:  # intermediate
            params.update({
                "intensity_modifier": 1.0,
                "complexity": "moderate",
                "exercise_variety": "moderate",
                "technique_focus": False
            })
        
        # Ajustar frecuencia de descarga basada en experiencia y objetivo
        if experience_level == "beginner":
            params["deload_frequency"] = max(4, weeks // 2)  # Descarga más frecuente para principiantes
        elif goal == "strength_gain" and experience_level == "advanced":
            params["deload_frequency"] = 3  # Descarga más frecuente para levantadores avanzados
        
        # Definir fases del plan
        params["phases"] = self._define_plan_phases(weeks, params["deload_frequency"], goal)
        
        return params
    
    def _define_plan_phases(self, total_weeks: int, deload_frequency: int, 
                          goal: Optional[str]) -> List[Dict[str, Any]]:
        """Define las fases del plan de entrenamiento"""
        phases = []
        current_week = 1
        
        while current_week <= total_weeks:
            # Determinar si es semana de descarga
            is_deload = (current_week % deload_frequency == 0 and 
                        current_week != total_weeks and 
                        current_week > deload_frequency)
            
            if is_deload:
                phase_name = "Deload"
                phase_goal = "Recuperación y adaptación"
                intensity_mod = 0.6
                volume_mod = 0.6
                duration = 1
            else:
                # Fase normal de entrenamiento
                if goal == "strength_gain":
                    if current_week <= total_weeks * 0.4:
                        phase_name = "Acumulación"
                        phase_goal = "Base de fuerza y técnica"
                        intensity_mod = 0.8
                        volume_mod = 1.0
                    elif current_week <= total_weeks * 0.7:
                        phase_name = "Intensificación"
                        phase_goal = "Máxima fuerza y densidad"
                        intensity_mod = 1.0
                        volume_mod = 0.9
                    else:
                        phase_name = "Realización"
                        phase_goal = "Pico de potencia y prueba"
                        intensity_mod = 1.1
                        volume_mod = 0.8
                elif goal == "hypertrophy":
                    phase_name = "Hipertrofia Progresiva"
                    phase_goal = "Crecimiento muscular sostenido"
                    intensity_mod = 0.9
                    volume_mod = 1.1
                elif goal == "endurance":
                    phase_name = "Base Aeróbica"
                    phase_goal = "Capacidad de trabajo sostenida"
                    intensity_mod = 0.7
                    volume_mod = 1.2
                else:
                    phase_name = "Entrenamiento General"
                    phase_goal = "Fitness y salud general"
                    intensity_mod = 0.9
                    volume_mod = 1.0
                
                # Calcular duración de la fase (mínimo 2 semanas, máximo restante)
                remaining_weeks = total_weeks - current_week + 1
                if remaining_weeks <= 2:
                    duration = remaining_weeks
                elif remaining_weeks <= 4:
                    duration = remaining_weeks
                else:
                    duration = min(4, remaining_weeks // 2)
                    duration = max(2, duration)  # Al menos 2 semanas
            
            phases.append({
                "name": phase_name,
                "goal": phase_goal,
                "start_week": current_week,
                "end_week": min(current_week + duration - 1, total_weeks),
                "intensity_modifier": intensity_mod,
                "volume_modifier": volume_mod,
                "is_deload": is_deload
            })
            
            current_week += duration
        
        return phases
    
    def _calculate_week_factor(self, week_index: int, total_weeks: int, 
                             periodization_params: Dict[str, Any]) -> Dict[str, float]:
        """Calcula factores de intensidad y volumen para una semana específica"""
        week_num = week_index + 1  # Convertir a 1-indexed
        
        # Encontrar la fase actual
        current_phase = None
        for phase in periodization_params["phases"]:
            if phase["start_week"] <= week_num <= phase["end_week"]:
                current_phase = phase
                break
        
        if not current_phase:
            # Por defecto, usar factores neutros
            return {
                "intensity_factor": 1.0,
                "volume_factor": 1.0,
                "is_deload": False
            }
        
        # Calcular progresión dentro de la fase
        phase_duration = phase["end_week"] - phase["start_week"] + 1
        week_in_phase = week_num - phase["start_week"] + 1
        
        if phase_duration > 1:
            progress = (week_in_phase - 1) / (phase_duration - 1)  # 0.0 a 1.0
        else:
            progress = 0.5  # Semana única en medio
        
        # Aplicar curvas de intensidd y volumen
        intensity_curve = periodization_params.get("intensity_curve", "linear")
        volume_curve = periodization_params.get("volume_curve", "linear")
        
        if intensity_curve == "linear":
            intensity_progress = progress
        elif intensity_curve == "exponential":
            intensity_progress = progress ** 0.5  # Raíz cuadrada para inicio lento
        elif intensity_curve == "wave_like":
            # Ondular: subir-bajar-subir para periodización ondulada
            intensity_progress = 0.5 + 0.5 * math.sin(progress * math.pi * 2)
        else:
            intensity_progress = progress
        
        if volume_curve == "linear":
            volume_progress = 1.0 - progress  # Volumen típicamente disminuye
        elif volume_curve == "step_wave":
            # Paso-onda para fuerza: volumen alto, medio, alto, medio
            phase_progress = week_in_phase / phase_duration
            volume_progress = 1.0 - 0.3 * (math.sin(phase_progress * math.pi * 4) + 1) / 2
        else:
            volume_progress = 1.0 - progress
        
        # Aplicar modificadores de la fase
        intensity_factor = (
            current_phase["intensity_modifier"] * 
            (0.5 + 0.5 * intensity_progress)  # Rango 0.5-1.0 del modificador
        )
        
        volume_factor = (
            current_phase["volume_modifier"] * 
            volume_progress
        )
        
        # Aplicar modificadores globales de experiencia
        intensity_factor *= periodization_params.get("intensity_modifier", 1.0)
        
        return {
            "intensity_factor": max(0.3, min(1.5, intensity_factor)),
            "volume_factor": max(0.3, min(1.8, volume_factor)),
            "is_deload": current_phase["is_deload"]
        }
    
    def _generate_week_workouts(self, user_id: str, week_number: int,
                              workouts_per_week: int, workout_type: WorkoutType,
                              week_factor: Dict[str, float], 
                              user_profile: Dict[str, Any],
                              available_days: Optional[List[int]]) -> List[WorkoutCreate]:
        """Genera los workouts para una semana específica"""
        workouts = []
        
        # Determinar días de entrenamiento para esta semana
        if available_days is None:
            # Distribuir uniformemente a lo largo de la semana
            training_days = [0, 2, 4]  # Lunes, Miércoles, Viernes por defecto
            if workouts_per_week > 3:
                training_days = [0, 1, 3, 4, 6]  # Añadir martes, jueves, domingo
            elif workouts_per_week == 4:
                training_days = [0, 2, 3, 5]  # Lunes, Miércoles, Jueves, Sábado
            elif workouts_per_week == 5:
                training_days = [0, 1, 3, 4, 6]  # Lunes, Martes, Jueves, Viernes, Domingo
            elif workouts_per_week == 6:
                training_days = [0, 1, 2, 3, 4, 5]  # Lunes a Sábado (descanso domingo)
            elif workouts_per_week == 7:
                training_days = [0, 1, 2, 3, 4, 5, 6]  # Todos los días
            else:
                # Para 1-2 entrenamiento por semana, distribuir bien
                if workouts_per_week == 1:
                    training_days = [3]  # Miércoles
                elif workouts_per_week == 2:
                    training_days = [1, 4]  # Martes y Viernes
        else:
            # Usar días disponibles, tomar los primeros N necesarios
            training_days = available_days[:workouts_per_week]
            # Si no hay suficientes días disponibles, repetir desde el inicio
            while len(training_days) < workouts_per_week:
                training_days.extend(available_days)
            training_days = training_days[:workouts_per_week]
        
        # Generar un workout para cada día de entrenamiento
        for i, day_index in enumerate(training_days[:workouts_per_week]):
            # Calcular fecha del workout (asumiendo que la semana empieza en lunes)
            # En una implementación real, esto vendría de una fecha de inicio
            workout_date = datetime.utcnow() + timedelta(
                days=(week_number - 1) * 7 + day_index
            )
            
            # Ajustar parámetros basados en factores de la semana
            adjusted_readiness = min(100, max(0, 
                user_profile.get("base_rpe_target", 8.0) * 12.5  # Convertir RPE a readiness aproximado
            ))
            
            # Aplicar fatiga semanal acumulada (simplificado)
            weekly_fatigue = min(30, (week_number - 1) * 5)  # Aumenta ligeramente cada semana
            adjusted_readiness = max(20, adjusted_readiness - weekly_fatigue)
            
            workout_request = TrainingGenerationRequest(
                user_id=user_id,
                readiness_score=adjusted_readiness,
                fatigue_score=min(100, weekly_fatigue + 10),
                stress_level=user_profile.get("base_rpe_target", 8.0),
                workout_type=workout_type,
                target_duration_minutes=user_profile.get("preferred_duration", 60),
                muscle_groups=[],  # Dejar vacío para selección equilibrada
                exclude_exercises=[],
                include_exercises=[],
                base_rpe=8.0 * week_factor["intensity_factor"],
                total_sets=int(15 * week_factor["volume_factor"])
            )
            
            # Generar el workout
            workout_schema = self.workout_generator.generate_workout(workout_request)
            
            # Personalizar nombre y descripción
            week_name = f"Semana {week_number}, Día {i+1}"
            if day_index < 7:
                day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                week_name = f"{day_names[day_index]} Semana {week_number}"
            
            workout_schema.name = f"{workout_type.value.title()} - {week_name}"
            workout_schema.description = (
                f"Entrenamiento de {workout_type.value} - Semana {week_number} "
                f"(Intensidad: {week_factor['intensity_factor']:.1f}x, "
                f"Volumen: {week_factor['volume_factor']:.1f}x)"
            )
            
            # Marcar como parte del plan (el plan_id se establecerá al crear la entidad)
            workouts.append(workout_schema)
        
        return workouts
    
    def _generate_plan_name(self, workout_type: WorkoutType, 
                          goal: Optional[str], weeks: int) -> str:
        """Genera nombre descriptivo para el plan"""
        type_names = {
            WorkoutType.STRENGTH: "Fuerza",
            WorkoutType.HYPERTROPHY: "Hipertrofia",
            WorkoutType.POWER: "Potencia",
            WorkoutType.ENDURANCE: "Resistencia",
            WorkoutType.RECOVERY: "Recuperación",
            WorkoutType.DELoad: "Descarga"
        }
        
        type_name = type_names.get(workout_type, "Entrenamiento")
        
        if goal:
            goal_names = {
                "strength_gain": "Fuerza Máxima",
                "hypertrophy": "Crecimiento Muscular",
                "endurance": "Resistencia Aeróbica",
                "weight_loss": "Pérdida de Grasa",
                "maintenance": "Mantenimiento"
            }
            goal_name = goal_names.get(goal, goal.title())
            return f"Plan {goal_name} - {type_name} ({weeks}s)"
        else:
            return f"Plan {type_name} General ({weeks}s)"
    
    def _generate_plan_description(self, workout_type: WorkoutType,
                                 goal: Optional[str], weeks: int,
                                 experience_level: str) -> str:
        """Genera descripción detallada del plan"""
        desc = f"Plan de entrenamiento de {workout_type.value} diseñado para "
        
        if experience_level == "beginner":
            desc += "principiantes que buscan establecer una base sólida. "
        elif experience_level == "intermediate":
            desc += "atletas intermedios que buscan progreso consistente. "
        else:
            desc += "atletas avanzados que buscan superar plataformas. "
        
        if goal:
            goal_desc = {
                "strength_gain": "aumentar la fuerza máxima en levantamientos básicos.",
                "hypertrophy": "maximizar el crecimiento muscular en todos los grupos principales.",
                "endurance": "mejorar la capacidad de trabajo sostenido y resistencia muscular.",
                "weight_loss": "reducir grasa corporal preservando masa muscular mediante entrenamiento de alta intensidad.",
                "maintenance": "mantener el nivel actual de fuerza y condición física."
            }.get(goal, "mejorar el estado físico general.")
            desc += goal_desc
        else:
            desc += "lograr un equilibrio entre fuerza, resistencia y condición física general."
        
        desc += f" El plan se desarrolla durante {weeks} semanas con progresión sistemática."
        
        return desc

# ============================================================================
# FACTORY PARA CREACIÓN DE ENTIDADES
# ============================================================================

class TrainingEntityFactory:
    """Factory para crear entidades del dominio"""
    
    @staticmethod
    def create_workout_from_schema(
        schema: WorkoutCreate,
        user_id: str
    ) -> PlannedWorkout:
        """Crea modelo PlannedWorkout desde schema"""
        
        workout = PlannedWorkout(
            user_id=user_id,
            plan_id=schema.plan_id,
            name=schema.name,
            description=schema.description,
            workout_type=schema.workout_type,
            scheduled_date=schema.scheduled_date,
            estimated_duration_minutes=schema.estimated_duration_minutes,
            readiness_score_at_creation=schema.readiness_score_at_creation,
            status=WorkoutStatus.SCHEDULED,
            total_sets_planned=0,
            total_sets_completed=0,
            total_volume_kg=0
        )
        
        # Crear bloques
        for block_schema in schema.exercise_blocks:
            block = ExerciseBlock(
                exercise_id=block_schema.exercise_id,
                execution_order=block_schema.execution_order,
                target_sets=block_schema.target_sets,
                target_rpe=block_schema.target_rpe,
                rest_seconds_between_sets=block_schema.rest_seconds_between_sets,
                tempo=block_schema.tempo,
                progression_scheme=block_schema.progression_scheme,
                weight_increment_kg=block_schema.weight_increment_kg
            )
            
            # Crear sets
            for set_schema in block_schema.sets:
                set_data = ExerciseSet(
                    set_number=set_schema.set_number,
                    planned_reps=set_schema.planned_reps,
                    planned_weight_kg=set_schema.planned_weight_kg,
                    planned_rpe=set_schema.planned_rpe,
                    planned_tempo=set_schema.planned_tempo,
                    planned_rest_seconds=set_schema.planned_rest_seconds,
                    status=SetStatus.PLANNED
        )
        block.sets.append(set_data)
        workout.total_sets_planned += 1
        
        workout.exercise_blocks.append(block)
    
    return workout

    @staticmethod
    def create_training_plan_from_schema(
        schema: TrainingPlanCreate,
        user_id: str
    ) -> TrainingPlan:
        """Crea modelo TrainingPlan desde schema"""
        
        plan = TrainingPlan(
            user_id=user_id,
            name=schema.name,
            description=schema.description,
            plan_type=schema.plan_type,
            duration_weeks=schema.duration_weeks,
            target_sessions_per_week=schema.target_sessions_per_week,
            target_volume_per_session=schema.target_volume_per_session,
            status=WorkoutStatus.SCHEDULED,
            generation_params=schema.generation_params or {},
            adaptation_history=schema.adaptation_history or []
        )
        
        return plan
