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

from app.training.domain.models import (
    ExerciseLibrary, TrainingPlan, Workout, ExerciseBlock, ExerciseSet,
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
        workout: Workout,
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
    
    def _adapt_for_low_readiness(self, workout: Workout, readiness: float) -> List[Dict]:
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
    
    def _adapt_for_time_constraint(self, workout: Workout, minutes: int) -> List[Dict]:
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
    
    def _reduce_volume(self, workout: Workout, factor: float) -> List[Dict]:
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
    
    def _reduce_intensity(self, workout: Workout, rpe_reduction: float) -> List[Dict]:
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
        workout: Workout,
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
        workout: Workout,
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
        sets = self.db.query(ExerciseSet).join(ExerciseBlock).join(Workout).filter(
            Workout.user_id == user_id,
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
        
        sets = self.db.query(ExerciseSet).join(ExerciseBlock).join(Workout).filter(
            Workout.user_id == user_id,
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
# FACTORY PARA CREACIÓN DE ENTIDADES
# ============================================================================

class TrainingEntityFactory:
    """Factory para crear entidades del dominio"""
    
    @staticmethod
    def create_workout_from_schema(
        schema: WorkoutCreate,
        user_id: str
    ) -> Workout:
        """Crea modelo Workout desde schema"""
        
        workout = Workout(
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
