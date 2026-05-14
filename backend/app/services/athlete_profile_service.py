"""
Servicio de Perfil de Atleta para Atlas Coach
===============================================

Este servicio mantiene el perfil completo del atleta basado en
datos históricos de Garmin y lo pone a disposición del coach
para personalizar recomendaciones.

El perfil incluye:
- Estadísticas históricas de todas las métricas
- Patrones de comportamiento
- Tendencias de recuperación
- Nivel de condición física
- Preferencias de entrenamiento
"""

import json
import logging
import statistics
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
from dataclasses import dataclass, asdict

from app.models.biometrics import Biometrics
from app.models.workout import Workout

logger = logging.getLogger("app.services.athlete_profile")


@dataclass
class AthleteStatistics:
    """Estadísticas históricas del atleta."""
    average: float
    std: float
    min: float
    max: float
    days_with_data: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AthleteProfile:
    """Perfil completo del atleta."""
    user_id: str
    generated_at: str
    
    # Información personal
    name: Optional[str]
    birth_date: Optional[str]
    age: Optional[int]
    
    # Cobertura de datos
    total_biometrics_records: int
    total_activities: int
    oldest_date: Optional[str]
    newest_date: Optional[str]
    days_covered: int
    
    # Estadísticas históricas
    sleep: AthleteStatistics
    steps: AthleteStatistics
    hrv: AthleteStatistics
    stress: AthleteStatistics
    resting_heart_rate: AthleteStatistics
    body_battery: AthleteStatistics
    
    # Perfil de atleta
    activity_level: str
    sleep_quality: str
    recovery_capacity: str
    stress_level: str
    fitness_level: str
    
    # Patrones detectados
    patterns: Dict[str, Any]
    
    # Readiness actual
    current_readiness: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['sleep'] = self.sleep.to_dict()
        result['steps'] = self.steps.to_dict()
        result['hrv'] = self.hrv.to_dict()
        result['stress'] = self.stress.to_dict()
        result['resting_heart_rate'] = self.resting_heart_rate.to_dict()
        result['body_battery'] = self.body_battery.to_dict()
        return result


class AthleteProfileService:
    """Servicio para gestionar el perfil del atleta."""
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> AthleteStatistics:
        """Calcula estadísticas básicas de una lista de valores."""
        if not values:
            return AthleteStatistics(0, 0, 0, 0, 0)
        
        return AthleteStatistics(
            average=statistics.mean(values),
            std=statistics.stdev(values) if len(values) >= 2 else 0,
            min=min(values),
            max=max(values),
            days_with_data=len(values)
        )
    
    @staticmethod
    def determine_activity_level(avg_steps: float) -> str:
        """Determina el nivel de actividad basado en pasos promedio."""
        if avg_steps >= 15000:
            return "Muy activo"
        elif avg_steps >= 10000:
            return "Activo"
        elif avg_steps >= 7000:
            return "Moderadamente activo"
        else:
            return "Sedentario"
    
    @staticmethod
    def determine_sleep_quality(avg_sleep: float) -> str:
        """Determina la calidad del sueño basado en horas promedio."""
        if avg_sleep >= 8:
            return "Excelente"
        elif avg_sleep >= 7:
            return "Bueno"
        elif avg_sleep >= 6:
            return "Adecuado"
        else:
            return "Insuficiente"
    
    @staticmethod
    def determine_recovery_capacity(avg_hrv: float, days_with_data: int) -> str:
        """Determina la capacidad de recuperación basado en HRV promedio."""
        if days_with_data == 0:
            return "Unknown"
        if avg_hrv >= 60:
            return "Alta"
        elif avg_hrv >= 45:
            return "Media"
        else:
            return "Baja"
    
    @staticmethod
    def determine_stress_level(avg_stress: float) -> str:
        """Determina el nivel de estrés basado en promedio."""
        if avg_stress <= 30:
            return "Bajo"
        elif avg_stress <= 50:
            return "Moderado"
        else:
            return "Alto"
    
    @staticmethod
    def determine_fitness_level(avg_rhr: float, avg_steps: float) -> str:
        """Determina el nivel de condición física."""
        # FC reposo baja + alta actividad = buena condición física
        if avg_rhr <= 50 and avg_steps >= 10000:
            return "Alto"
        elif avg_rhr <= 55 and avg_steps >= 7000:
            return "Medio"
        elif avg_rhr <= 60:
            return "Bajo"
        else:
            return "Muy bajo"
    
    @staticmethod
    def detect_patterns(biometrics: List[Biometrics]) -> Dict[str, Any]:
        """Detecta patrones en los datos del atleta."""
        patterns = {
            "sleep_consistency": 0,
            "activity_consistency": 0,
            "recovery_trend": "stable",
            "stress_patterns": [],
            "best_training_days": [],
            "rest_days_needed": False
        }
        
        if len(biometrics) < 7:
            return patterns
        
        # Analizar consistencia del sueño
        sleep_values = []
        for bio in biometrics:
            if bio.data:
                try:
                    data = json.loads(bio.data)
                    if data.get("sleep"):
                        sleep_values.append(data["sleep"])
                except Exception as e:
                    logger.debug(f"Error parsing sleep data: {e}")
        
        if len(sleep_values) >= 7:
            sleep_std = statistics.stdev(sleep_values) if len(sleep_values) >= 2 else 0
            patterns["sleep_consistency"] = max(0, 100 - sleep_std * 10)
        
        # Analizar consistencia de actividad
        steps_values = []
        for bio in biometrics:
            if bio.data:
                try:
                    data = json.loads(bio.data)
                    if data.get("steps"):
                        steps_values.append(data["steps"])
                except Exception as e:
                    logger.debug(f"Error parsing steps data: {e}")
        
        if len(steps_values) >= 7:
            steps_std = statistics.stdev(steps_values) if len(steps_values) >= 2 else 0
            patterns["activity_consistency"] = max(0, 100 - (steps_std / 1000) * 10)
        
        # Detectar días de mejor rendimiento
        if len(steps_values) >= 7:
            avg_steps = statistics.mean(steps_values)
            patterns["best_training_days"] = [
                i for i, steps in enumerate(steps_values[-7:])
                if steps > avg_steps * 1.2
            ]
        
        return patterns
    
    @classmethod
    def get_profile(cls, db: Session, user_id: str) -> AthleteProfile:
        """
        Obtiene el perfil completo del atleta.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Perfil completo del atleta
        """
        # Obtener información del usuario
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        
        # Obtener todos los datos biométricos
        biometrics = db.query(Biometrics).filter(
            Biometrics.user_id == user_id
        ).order_by(Biometrics.date.asc()).all()
        
        # Obtener actividades
        activities = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.source == "garmin"
        ).all()
        
        # Calcular estadísticas para cada métrica
        sleep_values = []
        steps_values = []
        hrv_values = []
        stress_values = []
        rhr_values = []
        body_battery_values = []
        
        for bio in biometrics:
            if bio.data:
                try:
                    data = json.loads(bio.data)
                    
                    if data.get("sleep"):
                        sleep_values.append(data["sleep"])
                    
                    if data.get("steps"):
                        steps_values.append(data["steps"])
                    
                    if data.get("hrv"):
                        hrv_values.append(data["hrv"])
                    
                    if data.get("stress"):
                        stress_values.append(data["stress"])
                    
                    if data.get("heartRate"):
                        rhr_values.append(data["heartRate"])
                    
                    if bio.body_battery:
                        body_battery_values.append(bio.body_battery)
                        
                except Exception as e:
                    logger.debug(f"Error parsing biometric data in get_profile: {e}")
        
        # Calcular estadísticas
        sleep_stats = cls.calculate_statistics(sleep_values)
        steps_stats = cls.calculate_statistics(steps_values)
        hrv_stats = cls.calculate_statistics(hrv_values)
        stress_stats = cls.calculate_statistics(stress_values)
        rhr_stats = cls.calculate_statistics(rhr_values)
        body_battery_stats = cls.calculate_statistics(body_battery_values)
        
        # Determinar perfil de atleta
        activity_level = cls.determine_activity_level(steps_stats.average)
        sleep_quality = cls.determine_sleep_quality(sleep_stats.average)
        recovery_capacity = cls.determine_recovery_capacity(hrv_stats.average, hrv_stats.days_with_data)
        stress_level = cls.determine_stress_level(stress_stats.average)
        fitness_level = cls.determine_fitness_level(rhr_stats.average, steps_stats.average)
        
        # Detectar patrones
        patterns = cls.detect_patterns(biometrics)
        
        # Obtener readiness actual
        current_readiness = None
        try:
            from app.services.readiness_service import ReadinessService
            current_readiness = ReadinessService.calculate(db, user_id)
        except Exception as e:
            logger.warning(f"Error calculating current readiness: {e}")
        
        # Calcular rango de fechas
        oldest_date = biometrics[0].date if biometrics else None
        newest_date = biometrics[-1].date if biometrics else None
        days_covered = 0
        
        if oldest_date and newest_date:
            try:
                oldest = datetime.strptime(oldest_date, "%Y-%m-%d").date()
                newest = datetime.strptime(newest_date, "%Y-%m-%d").date()
                days_covered = (newest - oldest).days
            except Exception as e:
                logger.warning(f"Error parsing date range: {e}")
        
        # Extraer información personal del usuario
        name = user.name if user else None
        birth_date = user.birth_date.isoformat() if user and user.birth_date else None
        age = user.age if user else None
        
        # Crear perfil
        profile = AthleteProfile(
            user_id=user_id,
            generated_at=datetime.now().isoformat(),
            name=name,
            birth_date=birth_date,
            age=age,
            total_biometrics_records=len(biometrics),
            total_activities=len(activities),
            oldest_date=oldest_date,
            newest_date=newest_date,
            days_covered=days_covered,
            sleep=sleep_stats,
            steps=steps_stats,
            hrv=hrv_stats,
            stress=stress_stats,
            resting_heart_rate=rhr_stats,
            body_battery=body_battery_stats,
            activity_level=activity_level,
            sleep_quality=sleep_quality,
            recovery_capacity=recovery_capacity,
            stress_level=stress_level,
            fitness_level=fitness_level,
            patterns=patterns,
            current_readiness=current_readiness
        )
        
        return profile
    
    @classmethod
    def get_profile_dict(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Obtiene el perfil del atleta como diccionario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Perfil del atleta como diccionario
        """
        profile = cls.get_profile(db, user_id)
        return profile.to_dict()

    @classmethod
    def get_profile_summary(cls, user_id: str, db: Session) -> str:
        """
        Obtiene un resumen textual del perfil del atleta para contexto de IA.

        Args:
            user_id: ID del usuario
            db: Sesión de base de datos

        Returns:
            Resumen legible del perfil, o 'Perfil no disponible' si falla
        """
        try:
            profile = cls.get_profile(db, user_id)
            parts = []
            if profile.name:
                parts.append(f"Atleta: {profile.name}")
            if profile.age:
                parts.append(f"{profile.age} años")
            if profile.activity_level:
                parts.append(f"Nivel: {profile.activity_level}")
            if profile.steps and profile.steps.average:
                parts.append(f"{profile.steps.average:.0f} pasos/día")
            if profile.sleep and profile.sleep.average:
                parts.append(f"Sueño: {profile.sleep.average:.1f}h")
            if profile.hrv and profile.hrv.average:
                parts.append(f"HRV: {profile.hrv.average:.0f}ms")
            if profile.fitness_level:
                parts.append(f"Fitness: {profile.fitness_level}")
            if profile.recovery_capacity:
                parts.append(f"Recuperación: {profile.recovery_capacity}")
            return " | ".join(parts) if parts else "Perfil no disponible"
        except Exception:
            return "Perfil no disponible"
    
    @classmethod
    def get_coach_context(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Obtiene el contexto completo para el coach de Atlas.
        
        Este es el formato que el coach de Atlas usa para entender
        al atleta y personalizar sus recomendaciones.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Contexto completo para el coach
        """
        profile = cls.get_profile(db, user_id)
        
        # Obtener recomendaciones base
        base_training_intensity = cls._get_training_intensity_recommendation(profile)
        base_recovery_focus = cls._get_recovery_focus_recommendation(profile)
        base_sleep_optimization = cls._get_sleep_optimization_recommendation(profile)
        base_stress_management = cls._get_stress_management_recommendation(profile)
        
        # Ajustar recomendaciones basadas en edad
        age_adjusted_intensity = cls._get_age_adjusted_intensity(profile.age, base_training_intensity)
        age_appropriate_recommendation = cls._get_age_appropriate_recommendation(profile.age, profile.fitness_level)
        
        context = {
            "athlete_profile": profile.to_dict(),
            "personal_info": {
                "name": profile.name,
                "birth_date": profile.birth_date,
                "age": profile.age,
                "age_group": cls._determine_age_group(profile.age)
            },
            "coach_recommendations": {
                "training_intensity": age_adjusted_intensity,
                "recovery_focus": base_recovery_focus,
                "sleep_optimization": base_sleep_optimization,
                "stress_management": base_stress_management,
                "age_appropriate_focus": age_appropriate_recommendation
            },
            "aging_considerations": AthleteProfileService._get_aging_considerations(profile),
            "key_insights": cls._generate_key_insights(profile)
        }
        
        return context
    
    @staticmethod
    def _determine_age_group(age: Optional[int]) -> str:
        """Determina el grupo de edad del atleta."""
        if not age:
            return "unknown"
        if age < 30:
            return "young_adult"
        elif age < 40:
            return "adult"
        elif age < 50:
            return "middle_aged"
        else:
            return "senior"
    
    @staticmethod
    def _get_aging_considerations(profile: AthleteProfile) -> Dict[str, Any]:
        """Genera consideraciones específicas basadas en la edad."""
        if not profile.age:
            return {"message": "Edad no disponible para consideraciones de envejecimiento"}
        
        considerations = {
            "age": profile.age,
            "age_group": AthleteProfileService._determine_age_group(profile.age),
            "recovery_needs": "standard",
            "injury_prevention_priority": "moderate",
            "training_adaptation": "none"
        }
        
        if profile.age < 30:
            considerations.update({
                "recovery_needs": "moderate",
                "injury_prevention_priority": "low",
                "training_adaptation": "progressive_overload",
                "focus_areas": ["desarrollo_fuerza", "resistencia", "velocidad"]
            })
        elif profile.age < 40:
            considerations.update({
                "recovery_needs": "standard",
                "injury_prevention_priority": "moderate",
                "training_adaptation": "periodization",
                "focus_areas": ["rendimiento_optimo", "fuerza_mantenimiento", "resistencia"]
            })
        elif profile.age < 50:
            considerations.update({
                "recovery_needs": "enhanced",
                "injury_prevention_priority": "high",
                "training_adaptation": "modified_intensity",
                "focus_areas": ["mantenimiento_condicion", "movilidad", "prevencion_lesiones"]
            })
        else:
            considerations.update({
                "recovery_needs": "extended",
                "injury_prevention_priority": "very_high",
                "training_adaptation": "functional_focus",
                "focus_areas": ["salud_funcional", "movilidad", "longevidad_activa", "equilibrio"]
            })
        
        return considerations
    
    @staticmethod
    def _get_training_intensity_recommendation(profile: AthleteProfile) -> str:
        """Genera recomendación de intensidad de entrenamiento."""
        if profile.current_readiness and profile.current_readiness.get("score"):
            score = profile.current_readiness["score"]
            if score >= 85:
                return "Alta intensidad - El cuerpo está en peak para entrenamiento duro"
            elif score >= 70:
                return "Intensidad moderada-alta - Buen estado para entrenar al 80-90%"
            elif score >= 50:
                return "Intensidad moderada - Mantener volumen, evitar máximo esfuerzo"
            elif score >= 30:
                return "Baja intensidad - Recuperación activa recomendada"
            else:
                return "Muy baja intensidad - Descanso total necesario"
        
        # Fallback basado en perfil general
        if profile.fitness_level == "Alto":
            return "Alta intensidad - Buena condición física base"
        elif profile.fitness_level == "Medio":
            return "Intensidad moderada - Progresión gradual"
        else:
            return "Baja intensidad - Construir base aeróbica"
    
    @staticmethod
    def _get_recovery_focus_recommendation(profile: AthleteProfile) -> str:
        """Genera recomendación de enfoque de recuperación."""
        if profile.recovery_capacity == "Alta":
            return "Recuperación eficiente - Puede tolerar mayor carga de entrenamiento"
        elif profile.recovery_capacity == "Media":
            return "Recuperación moderada - Equilibrar carga y descanso"
        else:
            return "Recuperación prioritaria - Enfocarse en sueño y estrés"
    
    @staticmethod
    def _get_sleep_optimization_recommendation(profile: AthleteProfile) -> str:
        """Genera recomendación de optimización del sueño."""
        if profile.sleep_quality == "Excelente":
            return "Mantener hábitos de sueño actuales"
        elif profile.sleep_quality == "Bueno":
            return "Pequeños ajustes pueden mejorar rendimiento"
        elif profile.sleep_quality == "Adecuado":
            return "Priorizar 7-8 horas de sueño para optimizar recuperación"
        else:
            return "Crítico: Mejorar higiene del sueño y aumentar horas"
    
    @staticmethod
    def _get_stress_management_recommendation(profile: AthleteProfile) -> str:
        """Genera recomendación de manejo de estrés."""
        if profile.stress_level == "Bajo":
            return "Buen manejo del estrés - Mantener prácticas actuales"
        elif profile.stress_level == "Moderado":
            return "Incorporar técnicas de relajación post-entrenamiento"
        else:
            return "Prioritario: Reducir estrés para mejorar recuperación"
    
    @staticmethod
    def _generate_key_insights(profile: AthleteProfile) -> List[str]:
        """Genera insights clave sobre el atleta."""
        insights = []
        
        # Insight sobre nivel de actividad
        if profile.activity_level == "Muy activo":
            insights.append("Atleta muy activo con alta consistencia en entrenamiento")
        elif profile.activity_level == "Activo":
            insights.append("Atleta activo con buena base de entrenamiento")
        
        # Insight sobre condición física
        if profile.fitness_level == "Alto":
            insights.append(f"Excelente condición física (FC reposo: {profile.resting_heart_rate.average:.0f} bpm)")
        
        # Insight sobre sueño
        if profile.sleep_quality == "Insuficiente":
            insights.append("Oportunidad de mejora: Aumentar horas de sueño para optimizar recuperación")
        
        # Insight sobre patrones
        if profile.patterns.get("sleep_consistency", 0) > 70:
            insights.append("Alta consistencia en hábitos de sueño")
        
        if profile.patterns.get("activity_consistency", 0) > 70:
            insights.append("Alta consistencia en actividad física")
        
        # Insight sobre readiness actual
        if profile.current_readiness:
            score = profile.current_readiness.get("score")
            if score and score >= 85:
                insights.append("Estado actual óptimo para máximo rendimiento")
            elif score and score < 50:
                insights.append("Estado actual requiere enfoque en recuperación")
        
        # Insight sobre edad y envejecimiento
        if profile.age:
            if profile.age < 30:
                insights.append(f"Atleta joven ({profile.age} años) con alto potencial de desarrollo")
            elif profile.age < 40:
                insights.append(f"Atleta en edad madura ({profile.age} años) en pico de rendimiento")
            elif profile.age < 50:
                insights.append(f"Atleta experimentado ({profile.age} años) con enfoque en mantenimiento")
            else:
                insights.append(f"Atleta veterano ({profile.age} años) con enfoque en longevidad y salud")
        
        return insights
    
    @staticmethod
    def _get_age_appropriate_recommendation(age: Optional[int], fitness_level: str) -> str:
        """Genera recomendaciones apropiadas para la edad."""
        if not age:
            return "Mantener programa de entrenamiento actual"
        
        if age < 30:
            return "Enfoque en desarrollo de fuerza y resistencia con progresión constante"
        elif age < 40:
            return "Optimizar rendimiento con periodización inteligente"
        elif age < 50:
            return "Mantener condición física con énfasis en recuperación y prevención de lesiones"
        else:
            return "Priorizar salud funcional, movilidad y longevidad activa"
    
    @staticmethod
    def _get_age_adjusted_intensity(age: Optional[int], base_intensity: str) -> str:
        """Ajusta la intensidad recomendada basada en la edad."""
        if not age:
            return base_intensity
        
        if age < 30:
            # Atletas jóvenes pueden tolerar mayor intensidad
            return base_intensity.replace("moderada", "alta").replace("baja", "moderada")
        elif age < 40:
            # Atletas en edad madura mantienen intensidad
            return base_intensity
        elif age < 50:
            # Atletas de 40-50 necesitan ajuste moderado
            if "muy alta" in base_intensity.lower():
                return base_intensity.replace("muy alta", "alta")
            return base_intensity
        else:
            # Atletas mayores necesitan intensidad moderada
            if "alta" in base_intensity.lower():
                return base_intensity.replace("alta", "moderada")
            return base_intensity
