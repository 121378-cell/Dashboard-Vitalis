"""
Dashboard-Vitalis — Session Service
=====================================

Servicio de gestión de sesiones de entrenamiento.
Incluye generación de sesiones, análisis post-sesión e informes semanales.

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.session import TrainingSession, WeeklyReport
from app.services.athlete_profile_service import AthleteProfileService
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger("app.services.session")


class SessionService:
    """
    Servicio de gestión de sesiones de entrenamiento.
    """
    
    @staticmethod
    def should_train_today(user_id: str, db: Session) -> Dict:
        """
        Decide si hoy es día de entreno basándose en:
        - Readiness score (< 40 → descanso obligatorio)
        - Historial de días consecutivos entrenados (> 3 → descanso)
        - Patrón habitual del atleta (días de la semana que entrena)
        - Último informe semanal
        
        Returns:
            {train: bool, reason: str, suggested_type: str}
        """
        today = date.today()
        weekday = today.weekday()  # 0=Lunes, 6=Domingo
        
        # 1. Calcular readiness actual
        readiness = 50  # default
        try:
            readiness_score = AnalyticsService.get_readiness_score(db, user_id)
            readiness = readiness_score.get("score", 50)
        except Exception as e:
            logger.warning(f"No se pudo obtener readiness: {e}")
        
        # 2. Si readiness < 40 → descanso obligatorio
        if readiness < 40:
            return {
                "train": False,
                "reason": f"Readiness muy bajo ({readiness}/100). Recuperación prioritaria.",
                "suggested_type": "rest",
                "readiness": readiness
            }
        
        # 3. Contar días consecutivos entrenados
        consecutive_days = SessionService._count_consecutive_training_days(user_id, db)
        if consecutive_days >= 3:
            return {
                "train": False,
                "reason": f"{consecutive_days} días consecutivos entrenados. Descanso recomendado.",
                "suggested_type": "rest",
                "readiness": readiness
            }
        
        # 4. Verificar patrón habitual (últimas 8 semanas)
        training_days_pattern = SessionService._get_training_pattern(user_id, db)
        today_name = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                      "Friday", "Saturday", "Sunday"][weekday]
        
        # Si el atleta normalmente entrena este día de la semana
        if today_name in training_days_pattern:
            # Decidir tipo según readiness
            if readiness >= 70:
                suggested_type = "strength"
            elif readiness >= 55:
                suggested_type = "mixed"
            else:
                suggested_type = "easy"
            
            return {
                "train": True,
                "reason": f"Día de entreno habitual. Readiness: {readiness}/100",
                "suggested_type": suggested_type,
                "readiness": readiness
            }
        
        # 5. Si no es día habitual pero readiness es alto
        if readiness >= 75:
            return {
                "train": True,
                "reason": f"Día de descanso habitual pero readiness excelente ({readiness}/100). Entreno opcional.",
                "suggested_type": "easy",
                "readiness": readiness
            }
        
        # Por defecto: descanso
        return {
            "train": False,
            "reason": f"Día de descanso habitual. Readiness: {readiness}/100",
            "suggested_type": "rest",
            "readiness": readiness
        }
    
    
    @staticmethod
    def _count_consecutive_training_days(user_id: str, db: Session) -> int:
        """Cuenta días consecutivos con sesiones completadas."""
        today = date.today()
        consecutive = 0
        
        for i in range(1, 8):  # últimos 7 días
            check_date = today - timedelta(days=i)
            session = db.query(TrainingSession).filter(
                TrainingSession.user_id == user_id,
                TrainingSession.date == check_date.isoformat(),
                TrainingSession.status == "completed"
            ).first()
            
            if session:
                consecutive += 1
            else:
                break  # Se rompe la racha
        
        return consecutive
    
    
    @staticmethod
    def _get_training_pattern(user_id: str, db: Session) -> List[str]:
        """Analiza patrón de días de entreno de las últimas 8 semanas."""
        # Consultar sesiones de entreno de las últimas 8 semanas
        start_date = (date.today() - timedelta(weeks=8)).isoformat()
        
        sessions = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date >= start_date,
            TrainingSession.status.in_(["completed", "active"])
        ).all()
        
        # Contar por día de la semana
        day_counts = {"Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0,
                     "Friday": 0, "Saturday": 0, "Sunday": 0}
        
        for session in sessions:
            session_date = datetime.fromisoformat(session.date).date()
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday",
                       "Friday", "Saturday", "Sunday"][session_date.weekday()]
            day_counts[day_name] += 1
        
        # Días con > 50% de frecuencia (al menos 4 de 8 semanas)
        threshold = 4
        training_days = [day for day, count in day_counts.items() if count >= threshold]
        
        # Si no hay patrón claro, usar Lunes/Miércoles/Viernes como default
        if not training_days:
            training_days = ["Monday", "Wednesday", "Friday"]
        
        return training_days
    
    
    @staticmethod
    def generate_session_plan(user_id: str, db: Session, target_date: date = None, 
                              force_type: str = None) -> Dict:
        """
        Genera el plan de sesión usando ATLAS IA.
        
        Args:
            user_id: ID del usuario
            db: Sesión de base de datos
            target_date: Fecha de la sesión (default: hoy)
            force_type: Forzar tipo de sesión (strength/cardio/mixed/rest)
        
        Returns:
            Dict con el plan de sesión completo
        """
        from app.services.context_service import ContextService
        from app.core.readiness_engine import ReadinessEngine
        
        if target_date is None:
            target_date = date.today()
        
        # 1. Obtener readiness
        readiness_score = 50
        try:
            readiness_data = AnalyticsService.get_readiness_score(db, user_id)
            readiness_score = readiness_data.get("score", 50)
        except:
            pass
        
        # 2. Obtener perfil del atleta
        profile_summary = AthleteProfileService.get_profile_summary(user_id, db)
        
        # 3. Obtener última sesión
        last_session = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.status == "completed"
        ).order_by(TrainingSession.date.desc()).first()
        
        last_session_summary = "Sin sesiones previas registradas."
        if last_session and last_session.session_report:
            last_session_summary = f"Última sesión ({last_session.date}): {last_session.session_report[:200]}..."
        
        # 4. Obtener sesiones recientes (últimos 7 días)
        recent_cutoff = (target_date - timedelta(days=7)).isoformat()
        recent_sessions = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date >= recent_cutoff,
            TrainingSession.status == "completed"
        ).all()
        
        recent_summary = f"{len(recent_sessions)} sesiones en los últimos 7 días."
        
        # 5. Decidir tipo de sesión
        if force_type:
            session_type = force_type
        elif readiness_score >= 70:
            session_type = "strength"
        elif readiness_score >= 55:
            session_type = "mixed"
        else:
            session_type = "easy"
        
        # 6. Generar plan con IA (simplified - usando template por ahora)
        # En producción, esto llamaría al servicio de IA
        plan = SessionService._generate_plan_template(
            session_type, readiness_score, profile_summary
        )
        
        return {
            "session_name": plan["session_name"],
            "estimated_duration_min": plan["estimated_duration_min"],
            "warmup": plan["warmup"],
            "exercises": plan["exercises"],
            "cooldown": plan["cooldown"],
            "coach_notes": plan["coach_notes"],
            "readiness": readiness_score,
            "type": session_type
        }
    
    
    @staticmethod
    def _generate_plan_template(session_type: str, readiness: int, profile: str) -> Dict:
        """Genera un plan template según el tipo de sesión."""
        
        if session_type == "strength":
            return {
                "session_name": "Fuerza - Tren Superior",
                "estimated_duration_min": 65,
                "warmup": "5 min elíptica + movilidad articular hombros + 2x15 face pulls ligero",
                "exercises": [
                    {
                        "name": "Press Banca",
                        "muscle_group": "Pecho",
                        "sets": [
                            {
                                "set_number": 1,
                                "reps": 8,
                                "weight_kg": 80,
                                "rpe_target": 7,
                                "rest_seconds": 120,
                                "tempo": "3-1-1",
                                "notes": "Serie de activación"
                            },
                            {
                                "set_number": 2,
                                "reps": 6,
                                "weight_kg": 87.5,
                                "rpe_target": 8,
                                "rest_seconds": 180,
                                "tempo": "3-1-1",
                                "notes": ""
                            },
                            {
                                "set_number": 3,
                                "reps": 6,
                                "weight_kg": 87.5,
                                "rpe_target": 8.5,
                                "rest_seconds": 180,
                                "tempo": "3-1-1",
                                "notes": "Última serie al fallo técnico"
                            }
                        ]
                    },
                    {
                        "name": "Remo Pendlay",
                        "muscle_group": "Espalda",
                        "sets": [
                            {
                                "set_number": 1,
                                "reps": 10,
                                "weight_kg": 70,
                                "rpe_target": 7,
                                "rest_seconds": 120,
                                "tempo": "2-1-2",
                                "notes": ""
                            },
                            {
                                "set_number": 2,
                                "reps": 8,
                                "weight_kg": 75,
                                "rpe_target": 8,
                                "rest_seconds": 150,
                                "tempo": "2-1-2",
                                "notes": ""
                            },
                            {
                                "set_number": 3,
                                "reps": 8,
                                "weight_kg": 75,
                                "rpe_target": 8,
                                "rest_seconds": 150,
                                "tempo": "2-1-2",
                                "notes": ""
                            }
                        ]
                    },
                    {
                        "name": "Press Militar",
                        "muscle_group": "Hombros",
                        "sets": [
                            {
                                "set_number": 1,
                                "reps": 10,
                                "weight_kg": 45,
                                "rpe_target": 7,
                                "rest_seconds": 90,
                                "tempo": "2-0-2",
                                "notes": ""
                            },
                            {
                                "set_number": 2,
                                "reps": 8,
                                "weight_kg": 50,
                                "rpe_target": 8,
                                "rest_seconds": 120,
                                "tempo": "2-0-2",
                                "notes": ""
                            }
                        ]
                    }
                ],
                "cooldown": "Estiramiento pectorales, dorsales y hombros. 5 min respiración diafragmática.",
                "coach_notes": f"Readiness {readiness}/100. Sesión de fuerza moderada-alta. Priorizar técnica sobre peso."
            }
        
        elif session_type == "mixed":
            return {
                "session_name": "Fuerza + Cardio - Full Body",
                "estimated_duration_min": 55,
                "warmup": "5 min cinta ligera + movilidad dinámica",
                "exercises": [
                    {
                        "name": "Sentadilla",
                        "muscle_group": "Piernas",
                        "sets": [
                            {"set_number": 1, "reps": 10, "weight_kg": 80, "rpe_target": 6, 
                             "rest_seconds": 120, "tempo": "3-1-1", "notes": "Activación"},
                            {"set_number": 2, "reps": 8, "weight_kg": 90, "rpe_target": 7,
                             "rest_seconds": 150, "tempo": "3-1-1", "notes": ""},
                            {"set_number": 3, "reps": 8, "weight_kg": 90, "rpe_target": 7.5,
                             "rest_seconds": 150, "tempo": "3-1-1", "notes": ""}
                        ]
                    },
                    {
                        "name": "Dominadas",
                        "muscle_group": "Espalda",
                        "sets": [
                            {"set_number": 1, "reps": 8, "weight_kg": 0, "rpe_target": 7,
                             "rest_seconds": 120, "tempo": "2-1-2", "notes": "Peso corporal"},
                            {"set_number": 2, "reps": 8, "weight_kg": 0, "rpe_target": 7.5,
                             "rest_seconds": 120, "tempo": "2-1-2", "notes": ""}
                        ]
                    }
                ],
                "cooldown": "10 min bicicleta estática suave + estiramientos",
                "coach_notes": f"Readiness {readiness}/100. Sesión mixta intensidad moderada. Terminar con cardio opcional si te sientes bien."
            }
        
        else:  # easy o rest
            return {
                "session_name": "Recuperación Activa - Movilidad",
                "estimated_duration_min": 30,
                "warmup": "5 min caminata ligera",
                "exercises": [
                    {
                        "name": "Foam Rolling",
                        "muscle_group": "Cuerpo completo",
                        "sets": [
                            {"set_number": 1, "reps": 1, "weight_kg": 0, "rpe_target": 3,
                             "rest_seconds": 0, "tempo": "controlado", "notes": "5 min rodillo espaldas, piernas"}
                        ]
                    },
                    {
                        "name": "Estiramientos Dinámicos",
                        "muscle_group": "Cuerpo completo",
                        "sets": [
                            {"set_number": 1, "reps": 10, "weight_kg": 0, "rpe_target": 4,
                             "rest_seconds": 30, "tempo": "lento", "notes": "Círculos, rotaciones, cat-cow"}
                        ]
                    },
                    {
                        "name": "Plancha",
                        "muscle_group": "Core",
                        "sets": [
                            {"set_number": 1, "reps": 1, "weight_kg": 0, "rpe_target": 5,
                             "rest_seconds": 60, "tempo": "20-0-20", "notes": "30-45 segundos mantenimiento"},
                            {"set_number": 2, "reps": 1, "weight_kg": 0, "rpe_target": 5,
                             "rest_seconds": 60, "tempo": "20-0-20", "notes": ""}
                        ]
                    }
                ],
                "cooldown": "5 min respiración consciente",
                "coach_notes": f"Readiness {readiness}/100. Día de recuperación activa. Prioriza calidad del sueño esta noche."
            }
    
    
    @staticmethod
    def analyze_session(session_id: str, db: Session) -> str:
        """
        Analiza la sesión completada con ATLAS.
        Compara plan vs ejecución real.
        Vincula datos de Garmin si existen.
        Genera informe en texto.
        """
        session = db.query(TrainingSession).filter(
            TrainingSession.id == session_id
        ).first()
        
        if not session:
            return "Error: Sesión no encontrada."
        
        if not session.actual_json:
            return "Error: No hay datos reales para analizar."
        
        plan_data = json.loads(session.plan_json) if session.plan_json else {}
        actual_data = json.loads(session.actual_json) if session.actual_json else {}
        
        # Análisis básico
        exercises_planned = len(plan_data.get("exercises", []))
        exercises_completed = 0
        total_sets_planned = 0
        total_sets_completed = 0
        avg_rpe_planned = 0
        avg_rpe_actual = 0
        rpe_count = 0
        
        for exercise in actual_data.get("exercises", []):
            exercise_completed = True
            for set_data in exercise.get("sets", []):
                if set_data.get("status") == "completed":
                    total_sets_completed += 1
                elif set_data.get("status") == "failed":
                    exercise_completed = False
                total_sets_planned += 1
                
                # RPE
                if set_data.get("rpe_target"):
                    avg_rpe_planned += set_data["rpe_target"]
                    rpe_count += 1
                if set_data.get("rpe_real"):
                    avg_rpe_actual += set_data["rpe_real"]
        
        if exercises_planned > 0:
            exercises_completed = sum(1 for e in actual_data.get("exercises", [])
                                     if all(s.get("status") == "completed" 
                                           for s in e.get("sets", [])))
        
        # Calcular porcentajes
        completion_rate = (total_sets_completed / total_sets_planned * 100) if total_sets_planned > 0 else 0
        avg_rpe_planned = avg_rpe_planned / rpe_count if rpe_count > 0 else 7
        avg_rpe_actual = avg_rpe_actual / rpe_count if rpe_count > 0 else 7
        
        # Generar informe
        report_parts = []
        
        # Cabecera
        report_parts.append(f"📊 INFORME DE SESIÓN - {plan_data.get('session_name', 'Entrenamiento')}")
        report_parts.append(f"📅 Fecha: {session.date}")
        
        # Métricas de cumplimiento
        report_parts.append(f"\n✅ CUMPLIMIENTO:")
        report_parts.append(f"   • Ejercicios completados: {exercises_completed}/{exercises_planned}")
        report_parts.append(f"   • Series completadas: {total_sets_completed}/{total_sets_planned} ({completion_rate:.0f}%)")
        
        # Intensidad
        report_parts.append(f"\n💪 INTENSIDAD:")
        report_parts.append(f"   • RPE objetivo medio: {avg_rpe_planned:.1f}/10")
        report_parts.append(f"   • RPE real medio: {avg_rpe_actual:.1f}/10")
        
        if avg_rpe_actual > avg_rpe_planned + 1:
            report_parts.append(f"   ⚠️ La sesión fue más intensa de lo planificado")
        elif avg_rpe_actual < avg_rpe_planned - 1:
            report_parts.append(f"   ℹ️ La sesión fue menos intensa de lo planificado")
        else:
            report_parts.append(f"   ✅ Intensidad alineada con el plan")
        
        # Datos de Garmin si existen
        if session.garmin_duration_min:
            report_parts.append(f"\n⌚ DATOS GARMIN:")
            report_parts.append(f"   • Duración: {session.garmin_duration_min:.0f} min")
            if session.garmin_hr_avg:
                report_parts.append(f"   • FC media: {session.garmin_hr_avg:.0f} bpm")
            if session.garmin_hr_max:
                report_parts.append(f"   • FC máx: {session.garmin_hr_max:.0f} bpm")
            if session.garmin_calories:
                report_parts.append(f"   • Calorías: {session.garmin_calories}")
        
        # Conclusión
        report_parts.append(f"\n📝 CONCLUSIÓN:")
        if completion_rate >= 90:
            report_parts.append("   Excelente sesión. Cumplimiento casi perfecto.")
        elif completion_rate >= 75:
            report_parts.append("   Buena sesión. Cumplimiento aceptable.")
        elif completion_rate >= 50:
            report_parts.append("   Sesión parcial. Considerar ajustar volumen próxima vez.")
        else:
            report_parts.append("   Sesión incompleta. Evaluar fatiga o factores externos.")
        
        return "\n".join(report_parts)
    
    
    @staticmethod
    def generate_weekly_report(user_id: str, db: Session) -> Dict:
        """
        Genera informe semanal analizando:
        - Todas las sesiones de la semana (plan vs real)
        - Biométricos diarios (readiness, sueño, estrés)
        - Tendencias de FC, HRV, pasos
        - Volumen total vs semana anterior
        - RPE medio real vs objetivo
        
        Returns:
            Dict con: informe, métricas, plan semana siguiente
        """
        today = date.today()
        # Calcular lunes y domingo de esta semana
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        week_start = monday.isoformat()
        week_end = sunday.isoformat()
        
        # Obtener sesiones de la semana
        sessions = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date >= week_start,
            TrainingSession.date <= week_end,
            TrainingSession.status == "completed"
        ).all()
        
        # Obtener biométricos de la semana
        biometrics = AnalyticsService.get_biometrics_for_range(
            db, user_id, week_start, week_end
        )
        
        # Análisis de sesiones
        total_sessions = len(sessions)
        completed_sets = 0
        planned_sets = 0
        total_rpe_real = 0
        rpe_count = 0
        total_duration = 0
        
        for session in sessions:
            if session.actual_json:
                actual = json.loads(session.actual_json)
                for exercise in actual.get("exercises", []):
                    for set_data in exercise.get("sets", []):
                        planned_sets += 1
                        if set_data.get("status") == "completed":
                            completed_sets += 1
                        if set_data.get("rpe_real"):
                            total_rpe_real += set_data["rpe_real"]
                            rpe_count += 1
            
            if session.garmin_duration_min:
                total_duration += session.garmin_duration_min
        
        # Métricas
        completion_rate = (completed_sets / planned_sets * 100) if planned_sets > 0 else 0
        avg_rpe = total_rpe_real / rpe_count if rpe_count > 0 else 0
        
        # Análisis de biométricos
        sleep_values = [b.get("sleep", 0) for b in biometrics if b.get("sleep", 0) > 0]
        stress_values = [b.get("stress", 0) for b in biometrics if b.get("stress", 0) > 0]
        hr_values = [b.get("heartRate", 0) for b in biometrics if b.get("heartRate", 0) > 0]
        
        avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
        avg_stress = sum(stress_values) / len(stress_values) if stress_values else 0
        avg_hr = sum(hr_values) / len(hr_values) if hr_values else 0
        
        # Generar informe
        report_parts = []
        report_parts.append(f"📊 INFORME SEMANAL - Semana del {monday.strftime('%d/%m')} al {sunday.strftime('%d/%m/%Y')}")
        report_parts.append("")
        report_parts.append(f"🗓️ RESUMEN DE ENTRENOS:")
        report_parts.append(f"   • Sesiones completadas: {total_sessions}")
        report_parts.append(f"   • Series completadas: {completed_sets}/{planned_sets} ({completion_rate:.0f}%)")
        report_parts.append(f"   • RPE medio semana: {avg_rpe:.1f}/10")
        report_parts.append(f"   • Tiempo total entrenado: {total_duration:.0f} min ({total_duration/60:.1f}h)")
        report_parts.append("")
        report_parts.append(f"💤 RECUPERACIÓN:")
        report_parts.append(f"   • Sueño medio: {avg_sleep:.1f}h")
        report_parts.append(f"   • Estrés medio: {avg_stress:.0f}/100")
        report_parts.append(f"   • FC reposo media: {avg_hr:.0f} bpm")
        report_parts.append("")
        
        # Análisis de tendencia
        if avg_sleep < 6:
            report_parts.append("⚠️ ALERTA: Sueño insuficiente esta semana (<6h media). Prioriza descanso.")
        if avg_stress > 60:
            report_parts.append("⚠️ ALERTA: Estrés elevado. Considera sesiones de menor volumen.")
        
        # Recomendación para próxima semana
        next_week_type = "strength" if completion_rate > 80 and avg_sleep > 6.5 else "mixed"
        
        next_week_plan = {
            "focus": next_week_type,
            "sessions_planned": 3 if total_sessions < 3 else 4,
            "volume_adjustment": "maintain" if completion_rate > 75 else "reduce"
        }
        
        report_parts.append("")
        report_parts.append(f"🎯 PLAN SEMANA SIGUIENTE:")
        report_parts.append(f"   • Enfoque: {next_week_plan['focus']}")
        report_parts.append(f"   • Sesiones planificadas: {next_week_plan['sessions_planned']}")
        report_parts.append(f"   • Ajuste de volumen: {next_week_plan['volume_adjustment']}")
        
        metrics = {
            "total_sessions": total_sessions,
            "completion_rate": round(completion_rate, 1),
            "avg_rpe": round(avg_rpe, 1),
            "total_duration_min": round(total_duration, 0),
            "avg_sleep": round(avg_sleep, 1),
            "avg_stress": round(avg_stress, 0),
            "avg_resting_hr": round(avg_hr, 0)
        }
        
        return {
            "report_text": "\n".join(report_parts),
            "metrics": metrics,
            "next_week_plan": next_week_plan,
            "week_start": week_start,
            "week_end": week_end
        }
