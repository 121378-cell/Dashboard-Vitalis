"""Athletic Intelligence Service para ATLAS
==========================================

Servicio de inteligencia deportiva que analiza datos históricos
del atleta para proporcionar insights al coach de ATLAS.

Características:
- Análisis de baseline de fitness sin HRV (FR245 no lo mide)
- Detección de riesgo de sobreentrenamiento
- Análisis de patrones de sueño
- Evaluación de capacidad de recuperación
- Perfil atlético completo

Autor: ATLAS Team
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.models.user import User

logger = logging.getLogger("app.services.athletic_intelligence")


class AthleticIntelligenceService:
    """Servicio de inteligencia deportiva para ATLAS."""
    
    # Constantes para clasificación de fitness
    ELITE_RHR_THRESHOLD = 45
    ADVANCED_RHR_THRESHOLD = 50
    INTERMEDIATE_RHR_THRESHOLD = 60
    
    ELITE_SESSIONS_THRESHOLD = 5.0
    ADVANCED_SESSIONS_THRESHOLD = 4.0
    INTERMEDIATE_SESSIONS_THRESHOLD = 3.0
    
    # Constantes para ACWR
    ACWR_OPTIMAL_MIN = 0.8
    ACWR_OPTIMAL_MAX = 1.3
    ACWR_RISK_MEDIUM_MAX = 1.5
    
    @staticmethod
    def analyze_fitness_baseline(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Analiza el baseline de fitness del atleta.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Diccionario con análisis de baseline de fitness
        """
        logger.info(f"Analyzing fitness baseline for user {user_id}")
        
        result = {
            "weekly_sessions_avg": None,
            "strength_sessions_per_week": None,
            "cardio_sessions_per_week": None,
            "mobility_sessions_per_week": None,
            "avg_strength_duration_min": None,
            "resting_hr_avg": None,
            "resting_hr_trend": "stable",
            "fitness_level": "beginner",
            "best_training_days": [],
            "total_training_hours_2y": None,
            "primary_sport": "strength_training",
            "data_quality_notes": []
        }
        
        try:
            # a) Frecuencia de entrenamiento (últimas 12 semanas)
            twelve_weeks_ago = (datetime.now() - timedelta(weeks=12)).isoformat()
            
            # Obtener actividades de las últimas 12 semanas
            recent_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= twelve_weeks_ago
                )
            ).all()
            
            # Obtener todas las actividades para cálculo más preciso
            all_workouts = db.query(Workout).filter(
                Workout.user_id == user_id
            ).all()
            
            if not all_workouts:
                result["data_quality_notes"].append("No hay actividades disponibles")
                return result
            
            # Usar todas las actividades para cálculo más preciso
            workouts_for_analysis = all_workouts
            
            # Calcular sesiones por semana (usar todas las actividades)
            if all_workouts:
                # Calcular rango de fechas
                dates = [w.date.date() for w in all_workouts if w.date]
                if dates:
                    date_range_days = (max(dates) - min(dates)).days
                    if date_range_days > 0:
                        weeks_count = date_range_days / 7
                    else:
                        weeks_count = 1
                else:
                    weeks_count = 1
                
                result["weekly_sessions_avg"] = len(all_workouts) / weeks_count
            
            # Desglose por tipo de actividad (usar todas las actividades)
            strength_count = 0
            cardio_count = 0
            mobility_count = 0
            training_days = [0] * 7  # 0=lunes, 6=domingo
            
            for workout in all_workouts:
                # Extraer tipo de actividad del JSON en description
                sport = "unknown"
                if workout.description:
                    try:
                        desc_data = json.loads(workout.description)
                        sport = desc_data.get("sport", "unknown")
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
                
                # Clasificar por tipo
                if sport == "strength_training":
                    strength_count += 1
                elif sport in ["running", "trail_running"]:
                    cardio_count += 1
                elif sport in ["yoga", "pilates"]:
                    mobility_count += 1
                
                # Día de la semana
                if workout.date:
                    day_of_week = workout.date.weekday()
                    training_days[day_of_week] += 1
            
            result["strength_sessions_per_week"] = strength_count / weeks_count
            result["cardio_sessions_per_week"] = cardio_count / weeks_count
            result["mobility_sessions_per_week"] = mobility_count / weeks_count
            
            # Mejores días de entrenamiento
            max_days = max(training_days) if training_days else 0
            result["best_training_days"] = [i for i, count in enumerate(training_days) if count == max_days]
            
            # b) Volumen de fuerza (últimas 8 semanas vs 8 semanas anteriores)
            eight_weeks_ago = (datetime.now() - timedelta(weeks=8)).isoformat()
            sixteen_weeks_ago = (datetime.now() - timedelta(weeks=16)).isoformat()
            
            # Sesiones de fuerza recientes
            recent_strength = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= eight_weeks_ago,
                    Workout.source == "garmin"
                )
            ).all()
            
            # Filtrar solo strength_training
            recent_strength_filtered = []
            for workout in recent_strength:
                if workout.description:
                    try:
                        desc_data = json.loads(workout.description)
                        if desc_data.get("sport") == "strength_training":
                            recent_strength_filtered.append(workout)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            # Sesiones de fuerza anteriores
            previous_strength = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= sixteen_weeks_ago,
                    Workout.date < eight_weeks_ago,
                    Workout.source == "garmin"
                )
            ).all()
            
            # Filtrar solo strength_training
            previous_strength_filtered = []
            for workout in previous_strength:
                if workout.description:
                    try:
                        desc_data = json.loads(workout.description)
                        if desc_data.get("sport") == "strength_training":
                            previous_strength_filtered.append(workout)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            # Calcular duración media
            if recent_strength_filtered:
                total_duration = sum(w.duration or 0 for w in recent_strength_filtered)
                result["avg_strength_duration_min"] = (total_duration / len(recent_strength_filtered)) / 60
            
            # Calcular calorías medias
            if recent_strength_filtered:
                total_calories = sum(w.calories or 0 for w in recent_strength_filtered)
                result["avg_strength_calories"] = total_calories / len(recent_strength_filtered)
            
            # c) Capacidad cardiovascular
            # FC reposo promedio últimos 30 días
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            recent_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= thirty_days_ago
                )
            ).order_by(Biometrics.date.desc()).all()
            
            rhr_values = []
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        rhr = data.get("heartRate")
                        if rhr and rhr > 0:
                            rhr_values.append(rhr)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if rhr_values:
                result["resting_hr_avg"] = sum(rhr_values) / len(rhr_values)
                
                # Tendencia: últimos 14 días vs 14 anteriores
                if len(rhr_values) >= 14:
                    recent_rhr = rhr_values[:14]
                    previous_rhr = rhr_values[14:]
                    
                    recent_avg = sum(recent_rhr) / len(recent_rhr)
                    previous_avg = sum(previous_rhr) / len(previous_rhr)
                    
                    if recent_avg < previous_avg - 2:
                        result["resting_hr_trend"] = "improving"
                    elif recent_avg > previous_avg + 2:
                        result["resting_hr_trend"] = "declining"
                    else:
                        result["resting_hr_trend"] = "stable"
            
            # Velocidad/ritmo medio en sesiones de running válidas
            # FILTRAR sesiones corruptas: duration_seconds = 3960 AND calories = 740
            running_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.source == "garmin"
                )
            ).all()
            
            valid_running_sessions = []
            for workout in running_workouts:
                if workout.description:
                    try:
                        desc_data = json.loads(workout.description)
                        sport = desc_data.get("sport")
                        
                        # Filtrar sesiones corruptas
                        if sport in ["running", "trail_running"]:
                            duration = workout.duration or 0
                            calories = workout.calories or 0
                            
                            # Filtrar duplicados corruptos
                            if duration == 3960 and calories == 740:
                                result["data_quality_notes"].append(f"Sesión running corrupta filtrada: {workout.external_id}")
                                continue
                            
                            valid_running_sessions.append(workout)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            # Calcular estadísticas de running
            if valid_running_sessions:
                total_distance = 0
                total_duration = 0
                
                for workout in valid_running_sessions:
                    if workout.description:
                        try:
                            desc_data = json.loads(workout.description)
                            distance = desc_data.get("distance", 0)
                            total_distance += distance
                            total_duration += workout.duration or 0
                        except Exception as e:
                            logger.debug(f"Error parsing running stats: {e}")
                
                if total_duration > 0:
                    result["avg_running_pace_min_km"] = (total_duration / 60) / (total_distance / 1000) if total_distance > 0 else None
            
            # d) Calcular fitness_level sin HRV
            if result["resting_hr_avg"] and result["weekly_sessions_avg"]:
                rhr = result["resting_hr_avg"]
                sessions = result["weekly_sessions_avg"]
                
                if rhr < AthleticIntelligenceService.ELITE_RHR_THRESHOLD and sessions >= AthleticIntelligenceService.ELITE_SESSIONS_THRESHOLD:
                    result["fitness_level"] = "elite"
                elif rhr < AthleticIntelligenceService.ADVANCED_RHR_THRESHOLD and sessions >= AthleticIntelligenceService.ADVANCED_SESSIONS_THRESHOLD:
                    result["fitness_level"] = "advanced"
                elif rhr < AthleticIntelligenceService.INTERMEDIATE_RHR_THRESHOLD and sessions >= AthleticIntelligenceService.INTERMEDIATE_SESSIONS_THRESHOLD:
                    result["fitness_level"] = "intermediate"
                else:
                    result["fitness_level"] = "beginner"
            
            # Total horas de entrenamiento (2 años)
            two_years_ago = (datetime.now() - timedelta(days=730)).isoformat()
            all_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= two_years_ago
                )
            ).all()
            
            total_duration = sum(w.duration or 0 for w in all_workouts)
            result["total_training_hours_2y"] = total_duration / 3600
            
            # Determinar deporte principal
            sport_counts = {}
            for workout in all_workouts:
                if workout.description:
                    try:
                        desc_data = json.loads(workout.description)
                        sport = desc_data.get("sport", "unknown")
                        sport_counts[sport] = sport_counts.get(sport, 0) + 1
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if sport_counts:
                result["primary_sport"] = max(sport_counts.items(), key=lambda x: x[1])[0]
            
        except Exception as e:
            logger.error(f"Error analyzing fitness baseline: {e}")
            result["data_quality_notes"].append(f"Error en análisis: {str(e)}")
        
        return result
    
    @staticmethod
    def analyze_sleep_patterns(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Analiza los patrones de sueño del atleta.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Diccionario con análisis de patrones de sueño
        """
        logger.info(f"Analyzing sleep patterns for user {user_id}")
        
        result = {
            "sleep_avg_recent_4w": None,
            "sleep_avg_historical": None,
            "poor_sleep_pct": None,
            "critical_sleep_pct": None,
            "sleep_debt_7d_hours": None,
            "sleep_trend": "stable",
            "chronic_sleep_deficit": False
        }
        
        try:
            # Obtener datos de sueño de las últimas 4 semanas
            four_weeks_ago = (datetime.now() - timedelta(weeks=4)).isoformat()
            
            recent_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= four_weeks_ago
                )
            ).order_by(Biometrics.date.desc()).all()
            
            # Obtener datos históricos (2 años)
            two_years_ago = (datetime.now() - timedelta(days=730)).isoformat()
            
            historical_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= two_years_ago
                )
            ).all()
            
            # Extraer datos de sueño recientes
            recent_sleep_values = []
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        sleep = data.get("sleep")
                        if sleep and sleep > 0:
                            recent_sleep_values.append(sleep)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            # Extraer datos de sueño históricos
            historical_sleep_values = []
            for bio in historical_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        sleep = data.get("sleep")
                        if sleep and sleep > 0:
                            historical_sleep_values.append(sleep)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            # Calcular promedios
            if recent_sleep_values:
                result["sleep_avg_recent_4w"] = sum(recent_sleep_values) / len(recent_sleep_values)
                
                # Calcular porcentajes de sueño pobre
                poor_sleep_count = sum(1 for s in recent_sleep_values if s < 7)
                critical_sleep_count = sum(1 for s in recent_sleep_values if s < 6)
                
                result["poor_sleep_pct"] = (poor_sleep_count / len(recent_sleep_values)) * 100
                result["critical_sleep_pct"] = (critical_sleep_count / len(recent_sleep_values)) * 100
            
            if historical_sleep_values:
                result["sleep_avg_historical"] = sum(historical_sleep_values) / len(historical_sleep_values)
                
                # Determinar déficit crónico
                result["chronic_sleep_deficit"] = result["sleep_avg_historical"] < 7.0
            
            # Calcular deuda de sueño últimos 7 días
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            last_7_days_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= seven_days_ago
                )
            ).order_by(Biometrics.date.desc()).all()
            
            sleep_debt = 0
            for bio in last_7_days_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        sleep = data.get("sleep")
                        if sleep:
                            sleep_debt += max(0, 7.5 - sleep)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            result["sleep_debt_7d_hours"] = sleep_debt
            
            # Calcular tendencia de sueño
            if len(recent_sleep_values) >= 14:
                recent_2w = recent_sleep_values[:14]
                previous_2w = recent_sleep_values[14:]
                
                recent_avg = sum(recent_2w) / len(recent_2w)
                previous_avg = sum(previous_2w) / len(previous_2w)
                
                if recent_avg > previous_avg + 0.3:
                    result["sleep_trend"] = "improving"
                elif recent_avg < previous_avg - 0.3:
                    result["sleep_trend"] = "declining"
                else:
                    result["sleep_trend"] = "stable"
            
        except Exception as e:
            logger.error(f"Error analyzing sleep patterns: {e}")
        
        return result
    
    @staticmethod
    def analyze_recovery_capacity(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Analiza la capacidad de recuperación del atleta.
        
        SIN HRV - usa proxies: Body Battery, Resting HR, Stress
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Diccionario con análisis de capacidad de recuperación
        """
        logger.info(f"Analyzing recovery capacity for user {user_id}")
        
        result = {
            "body_battery_avg": None,
            "body_battery_trend": "stable",
            "low_battery_days_pct": None,
            "rhr_fatigue_days_recent": 0,
            "stress_avg_30d": None,
            "high_stress_days_pct": None,
            "max_consecutive_training_days": 0,
            "avg_rest_days_between_blocks": None,
            "recovery_score": None
        }
        
        try:
            # a) Body Battery
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            recent_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= thirty_days_ago
                )
            ).order_by(Biometrics.date.desc()).all()
            
            body_battery_values = []
            for bio in recent_biometrics:
                # Filtrar valores > 100 (datos corruptos)
                if bio.body_battery and 0 <= bio.body_battery <= 100:
                    body_battery_values.append(bio.body_battery)
                elif bio.body_battery and bio.body_battery > 100:
                    logger.warning(f"Body Battery corrupto filtrado: {bio.body_battery} (fecha: {bio.date})")
            
            if body_battery_values:
                result["body_battery_avg"] = sum(body_battery_values) / len(body_battery_values)
                
                # Calcular porcentaje de días con BB < 40
                low_battery_count = sum(1 for bb in body_battery_values if bb < 40)
                result["low_battery_days_pct"] = (low_battery_count / len(body_battery_values)) * 100
                
                # Calcular tendencia
                if len(body_battery_values) >= 14:
                    recent_2w = body_battery_values[:14]
                    previous_2w = body_battery_values[14:]
                    
                    recent_avg = sum(recent_2w) / len(recent_2w)
                    previous_avg = sum(previous_2w) / len(previous_2w)
                    
                    if recent_avg > previous_avg + 5:
                        result["body_battery_trend"] = "improving"
                    elif recent_avg < previous_avg - 5:
                        result["body_battery_trend"] = "declining"
                    else:
                        result["body_battery_trend"] = "stable"
            
            # b) Resting Heart Rate como proxy de recuperación
            rhr_values = []
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        rhr = data.get("heartRate")
                        if rhr and rhr > 0:
                            rhr_values.append(rhr)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if rhr_values:
                rhr_avg = sum(rhr_values) / len(rhr_values)
                
                # Días con RHR elevado (> media + 3 bpm) últimas 2 semanas
                fourteen_days_ago = (datetime.now() - timedelta(days=14)).isoformat()
                
                recent_14d_biometrics = db.query(Biometrics).filter(
                    and_(
                        Biometrics.user_id == user_id,
                        Biometrics.date >= fourteen_days_ago
                    )
                ).order_by(Biometrics.date.desc()).all()
                
                rhr_fatigue_days = 0
                for bio in recent_14d_biometrics:
                    if bio.data:
                        try:
                            data = json.loads(bio.data)
                            rhr = data.get("heartRate")
                            if rhr and rhr > rhr_avg + 3:
                                rhr_fatigue_days += 1
                        except Exception as e:
                            logger.debug(f"Error parsing running stats: {e}")
                
                result["rhr_fatigue_days_recent"] = rhr_fatigue_days
            
            # c) Stress
            stress_values = []
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        stress = data.get("stress")
                        if stress is not None:
                            stress_values.append(stress)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if stress_values:
                result["stress_avg_30d"] = sum(stress_values) / len(stress_values)
                
                # Porcentaje de días con stress > 50
                high_stress_count = sum(1 for s in stress_values if s > 50)
                result["high_stress_days_pct"] = (high_stress_count / len(stress_values)) * 100
            
            # d) Consecutive training days
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            recent_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= thirty_days_ago
                )
            ).order_by(Workout.date.asc()).all()
            
            if recent_workouts:
                # Calcular días consecutivos máximos
                max_consecutive = 0
                current_consecutive = 0
                
                for i, workout in enumerate(recent_workouts):
                    if i == 0:
                        current_consecutive = 1
                    else:
                        # Verificar si es el mismo día o el siguiente día
                        prev_date = recent_workouts[i-1].date.date() if recent_workouts[i-1].date else None
                        curr_date = workout.date.date() if workout.date else None
                        
                        if prev_date and curr_date:
                            if (curr_date - prev_date).days <= 1:
                                current_consecutive += 1
                            else:
                                max_consecutive = max(max_consecutive, current_consecutive)
                                current_consecutive = 1
                
                max_consecutive = max(max_consecutive, current_consecutive)
                result["max_consecutive_training_days"] = max_consecutive
                
                # Calcular promedio de días de descanso entre bloques
                if len(recent_workouts) > 1:
                    rest_days = []
                    for i in range(1, len(recent_workouts)):
                        prev_date = recent_workouts[i-1].date.date() if recent_workouts[i-1].date else None
                        curr_date = recent_workouts[i].date.date() if recent_workouts[i].date else None
                        
                        if prev_date and curr_date:
                            days_between = (curr_date - prev_date).days
                            if days_between > 1:
                                rest_days.append(days_between - 1)
                    
                    if rest_days:
                        result["avg_rest_days_between_blocks"] = sum(rest_days) / len(rest_days)
            
            # Calcular recovery_score sin HRV
            if result["body_battery_avg"] is not None and result["stress_avg_30d"] is not None and rhr_avg:
                # Calcular score de RHR
                if rhr_avg < 50:
                    rhr_score = 100
                elif rhr_avg < 55:
                    rhr_score = 80
                elif rhr_avg < 60:
                    rhr_score = 60
                else:
                    rhr_score = 40
                
                # Recovery score = (body_battery_avg + (100 - stress_avg) + rhr_score) / 3
                recovery_score = (
                    result["body_battery_avg"] +
                    (100 - result["stress_avg_30d"]) +
                    rhr_score
                ) / 3
                
                result["recovery_score"] = max(0, min(100, recovery_score))
            
        except Exception as e:
            logger.error(f"Error analyzing recovery capacity: {e}")
        
        return result
    
    @staticmethod
    def detect_overreaching_risk(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Detecta riesgo de sobreentrenamiento usando ACWR.
        
        Acute:Chronic Workload Ratio sin potencia - usar duración en minutos.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Diccionario con análisis de riesgo de sobreentrenamiento
        """
        logger.info(f"Detecting overreaching risk for user {user_id}")
        
        result = {
            "acwr_ratio": None,
            "acute_load_min": None,
            "chronic_load_min": None,
            "risk_level": "insufficient_data",
            "additional_risk_factors": 0,
            "recommendation": "No hay suficientes datos para evaluar el riesgo"
        }
        
        try:
            # Calcular carga aguda (últimos 7 días)
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            acute_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= seven_days_ago
                )
            ).all()
            
            acute_load_min = sum(w.duration or 0 for w in acute_workouts)
            result["acute_load_min"] = acute_load_min
            
            # Calcular carga crónica (promedio semanal de los últimos 28 días)
            twenty_eight_days_ago = (datetime.now() - timedelta(days=28)).isoformat()
            
            chronic_workouts = db.query(Workout).filter(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= twenty_eight_days_ago
                )
            ).all()
            
            chronic_load_min = sum(w.duration or 0 for w in chronic_workouts)
            chronic_load_avg_week = chronic_load_min / 4  # 4 semanas
            
            result["chronic_load_min"] = chronic_load_avg_week
            
            # Calcular ACWR
            if chronic_load_avg_week > 0:
                result["acwr_ratio"] = acute_load_min / chronic_load_avg_week
                
                # Clasificar riesgo
                if result["acwr_ratio"] < AthleticIntelligenceService.ACWR_OPTIMAL_MIN:
                    result["risk_level"] = "detraining"
                    result["recommendation"] = "Carga muy baja - riesgo de detraining. Considera aumentar volumen gradualmente."
                elif result["acwr_ratio"] <= AthleticIntelligenceService.ACWR_OPTIMAL_MAX:
                    result["risk_level"] = "optimal"
                    result["recommendation"] = "Carga óptima - balance entre entrenamiento y recuperación."
                elif result["acwr_ratio"] <= AthleticIntelligenceService.ACWR_RISK_MEDIUM_MAX:
                    result["risk_level"] = "risk_medium"
                    result["recommendation"] = "Carga moderadamente alta - monitorea recuperación y considera reducir volumen."
                else:
                    result["risk_level"] = "risk_high"
                    result["recommendation"] = "Carga muy alta - riesgo significativo de sobreentrenamiento. Reduce volumen inmediatamente."
            else:
                result["risk_level"] = "insufficient_data"
                result["recommendation"] = "No hay suficientes datos históricos para calcular ACWR."
            
            # Señales adicionales de fatiga
            additional_risk_factors = 0
            
            # RHR elevado últimos 3 días
            fourteen_days_ago = (datetime.now() - timedelta(days=14)).isoformat()
            
            recent_biometrics = db.query(Biometrics).filter(
                and_(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= fourteen_days_ago
                )
            ).order_by(Biometrics.date.desc()).limit(3).all()
            
            rhr_values = []
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        rhr = data.get("heartRate")
                        if rhr and rhr > 0:
                            rhr_values.append(rhr)
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if rhr_values:
                rhr_avg = sum(rhr_values) / len(rhr_values)
                elevated_rhr_count = sum(1 for rhr in rhr_values if rhr > rhr_avg + 4)
                
                if elevated_rhr_count >= 2:
                    additional_risk_factors += 1
            
            # Body Battery bajo últimos 3 días
            low_battery_count = 0
            for bio in recent_biometrics:
                if bio.body_battery and bio.body_battery < 40:
                    low_battery_count += 1
            
            if low_battery_count >= 2:
                additional_risk_factors += 1
            
            # Sueño pobre últimos 3 noches
            poor_sleep_count = 0
            for bio in recent_biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        sleep = data.get("sleep")
                        if sleep and sleep < 6:
                            poor_sleep_count += 1
                    except Exception as e:
                        logger.debug(f"Error parsing workout data: {e}")
            
            if poor_sleep_count >= 2:
                additional_risk_factors += 1
            
            result["additional_risk_factors"] = additional_risk_factors
            
            # Elevar categoría de riesgo si hay factores adicionales
            if additional_risk_factors >= 2 and result["risk_level"] in ["optimal", "risk_medium"]:
                if result["risk_level"] == "optimal":
                    result["risk_level"] = "risk_medium"
                elif result["risk_level"] == "risk_medium":
                    result["risk_level"] = "risk_high"
                
                result["recommendation"] += " Señales adicionales de fatiga detectadas."
            
        except Exception as e:
            logger.error(f"Error detecting overreaching risk: {e}")
        
        return result
    
    @staticmethod
    def get_full_athletic_profile(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Obtiene el perfil atlético completo del atleta.
        
        Combina todas las funciones de análisis en un perfil completo.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
        
        Returns:
            Diccionario con perfil atlético completo
        """
        logger.info(f"Generating full athletic profile for user {user_id}")
        
        # Obtener información del usuario
        user = db.query(User).filter(User.id == user_id).first()
        
        # Calcular edad dinámicamente
        age = user.age if user else None
        age_group = "unknown"
        if age:
            if age < 30:
                age_group = "young_adult"
            elif age < 40:
                age_group = "adult"
            elif age < 50:
                age_group = "masters_athlete"
            else:
                age_group = "senior"
        
        # Analizar baseline de fitness
        fitness_baseline = AthleticIntelligenceService.analyze_fitness_baseline(db, user_id)
        
        # Analizar patrones de sueño
        sleep_patterns = AthleticIntelligenceService.analyze_sleep_patterns(db, user_id)
        
        # Analizar capacidad de recuperación
        recovery_capacity = AthleticIntelligenceService.analyze_recovery_capacity(db, user_id)
        
        # Detectar riesgo de sobreentrenamiento
        overreaching_risk = AthleticIntelligenceService.detect_overreaching_risk(db, user_id)
        
        # Generar resumen para el coach
        coach_context_summary = AthleticIntelligenceService._generate_coach_context_summary(
            user, fitness_baseline, sleep_patterns, recovery_capacity, overreaching_risk
        )
        
        # Determinar mix de deportes
        sports_mix = ["strength_training"]
        if fitness_baseline.get("cardio_sessions_per_week", 0) > 0:
            sports_mix.append("running")
            sports_mix.append("trail_running")
        if fitness_baseline.get("mobility_sessions_per_week", 0) > 0:
            sports_mix.append("yoga")
            sports_mix.append("pilates")
        if fitness_baseline.get("walking_sessions_per_week", 0) > 0:
            sports_mix.append("walking")
        
        # Construir perfil completo
        full_profile = {
            "generated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "athlete_identity": {
                "name": user.name if user else "Atleta",
                "age": age,
                "age_group": age_group,
                "primary_sport": fitness_baseline.get("primary_sport", "strength_training"),
                "sports_mix": sports_mix
            },
            "fitness_baseline": fitness_baseline,
            "sleep_patterns": sleep_patterns,
            "recovery_capacity": recovery_capacity,
            "overreaching_risk": overreaching_risk,
            "coach_context_summary": coach_context_summary
        }
        
        return full_profile
    
    @staticmethod
    def _generate_coach_context_summary(
        user: User,
        fitness_baseline: Dict[str, Any],
        sleep_patterns: Dict[str, Any],
        recovery_capacity: Dict[str, Any],
        overreaching_risk: Dict[str, Any]
    ) -> str:
        """
        Genera un resumen del contexto del coach en español.
        
        Args:
            user: Usuario del atleta
            fitness_baseline: Análisis de baseline de fitness
            sleep_patterns: Análisis de patrones de sueño
            recovery_capacity: Análisis de capacidad de recuperación
            overreaching_risk: Análisis de riesgo de sobreentrenamiento
        
        Returns:
            Párrafo en español resumiendo el estado del atleta
        """
        name = user.name if user else "El atleta"
        age = user.age if user else "N/A"
        fitness_level = fitness_baseline.get("fitness_level", "unknown")
        weekly_sessions = fitness_baseline.get("weekly_sessions_avg", 0)
        rhr = fitness_baseline.get("resting_hr_avg", 0)
        primary_sport = fitness_baseline.get("primary_sport", "entrenamiento")
        total_hours = fitness_baseline.get("total_training_hours_2y", 0)
        
        sleep_avg = sleep_patterns.get("sleep_avg_historical", 0)
        sleep_deficit = sleep_patterns.get("chronic_sleep_deficit", False)
        
        recovery_score = recovery_capacity.get("recovery_score", 0)
        body_battery = recovery_capacity.get("body_battery_avg", 0)
        stress = recovery_capacity.get("stress_avg_30d", 0)
        
        risk_level = overreaching_risk.get("risk_level", "unknown")
        
        # Construir resumen
        summary_parts = []
        
        # Identidad y nivel
        if age != "N/A":
            summary_parts.append(f"{name} es un atleta de {age} años con nivel {fitness_level} (FC reposo {rhr:.0f} bpm, {weekly_sessions:.1f} sesiones/semana).")
        else:
            summary_parts.append(f"{name} es un atleta con nivel {fitness_level} (FC reposo {rhr:.0f} bpm, {weekly_sessions:.1f} sesiones/semana).")
        
        # Historial de entrenamiento
        if total_hours > 0:
            summary_parts.append(f"Lleva {total_hours:.0f} horas de entrenamiento en los últimos 2 años con {primary_sport} como disciplina principal.")
        
        # Patrones de sueño
        if sleep_deficit:
            summary_parts.append(f"Presenta un déficit de sueño crónico (media histórica {sleep_avg:.1f}h < 7h óptimos).")
        else:
            summary_parts.append(f"Mantiene buenos hábitos de sueño (media histórica {sleep_avg:.1f}h).")
        
        # Recuperación
        summary_parts.append(f"Recuperación basada en Body Battery ({body_battery:.0f}) y stress ({stress:.0f}/100) dado que el dispositivo no mide HRV.")
        
        # Riesgo de sobreentrenamiento
        if risk_level == "optimal":
            summary_parts.append("Carga de entrenamiento actual es óptima.")
        elif risk_level == "risk_medium":
            summary_parts.append("Carga de entrenamiento moderadamente alta - monitorea recuperación.")
        elif risk_level == "risk_high":
            summary_parts.append("Carga de entrenamiento alta - riesgo de sobreentrenamiento.")
        
        return " ".join(summary_parts)