"""
Training Plan Service
======================

Servicio para generar y gestionar planes de entrenamiento adaptativos en ATLAS.

Funciones principales:
- generate_weekly_plan(): Genera un plan semanal usando IA
- get_current_plan(): Obtiene el plan activo actual
- update_session(): Actualiza una sesión planificada
- auto_detect_completed_sessions(): Detecta automáticamente sesiones completadas
- get_plan_history(): Obtiene el historial de planes
"""

import logging
import json
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.services.ai_service import AIService
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession, AdaptivePlanAdjustment
from app.models.workout import Workout

logger = logging.getLogger("app.services.training_plan_service")


class TrainingPlanService:
    """Servicio para gestión de planes de entrenamiento adaptativos."""

    @staticmethod
    def generate_weekly_plan(
        db: Session,
        user_id: str,
        goal: str,
        week_start: Optional[date] = None,
        training_days: Optional[List[str]] = None,
        time_available: Optional[Dict[str, int]] = None,
        session_types: Optional[List[str]] = None,
        intensity_preference: Optional[str] = None,
        consider_readiness: bool = True,
        restrictions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera un plan de entrenamiento semanal completo usando IA.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            goal: Objetivo del usuario para la semana
            week_start: Fecha de inicio de la semana (default: lunes actual)
            training_days: Lista de días de entrenamiento (e.g. ["monday", "wednesday"])
            time_available: Dict con minutos por día (e.g. {"monday": 60})
            session_types: Lista de tipos de sesión deseados (e.g. ["strength", "running"])
            intensity_preference: "low", "medium", o "high"
            consider_readiness: Si se debe considerar el readiness score actual
            restrictions: Restricciones (lesiones, zonas a evitar)

        Returns:
            Dict con el plan completo incluyendo ID del plan
        """
        try:
            if week_start is None:
                today = date.today()
                week_start = today - timedelta(days=today.weekday())

            week_end = week_start + timedelta(days=6)

            # Mapeo correcto de nombres de días reales a las fechas
            days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dates = [week_start + timedelta(days=i) for i in range(7)]
            day_date_map = {days_es[d.weekday()]: d.isoformat() for d in dates}
            
            # Para el prompt, mantenemos el orden cronológico
            ordered_days = [days_es[d.weekday()] for d in dates]

            existing_plan = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.user_id == user_id,
                    AdaptiveTrainingPlan.week_start_date == week_start,
                    AdaptiveTrainingPlan.status == 'active'
                )
            ).first()

            if existing_plan:
                return {
                    "error": "Ya existe un plan activo para esta semana",
                    "plan_id": existing_plan.id,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat()
                }

            logger.info(f"Obteniendo perfil atlético para user_id={user_id}")
            profile = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)

            identity = profile.get("athlete_identity", {})
            fitness = profile.get("fitness_baseline", {})
            sleep = profile.get("sleep_patterns", {})
            recovery = profile.get("recovery_capacity", {})
            risk = profile.get("overreaching_risk", {})

            coach_context = profile.get("coach_context_summary", "")

            acwr_ratio = risk.get("acwr_ratio", 1.0)
            risk_level = risk.get("risk_level", "optimal")

            if acwr_ratio < 0.8:
                load_action = "subir"
            elif acwr_ratio > 1.3:
                load_action = "bajar"
            else:
                load_action = "mantener"

            system_prompt = (
                "Eres ATLAS Coach, un entrenador personal de alto rendimiento "
                "especializado en atletas masters (40+). Generas planes de entrenamiento "
                "científicamente fundamentados, personalizados y progresivos. "
                "RESPONDES ÚNICAMENTE CON JSON VÁLIDO. Sin markdown, sin texto extra, "
                "sin bloques de código. Solo el objeto JSON."
            )

            best_days_int = fitness.get('best_training_days', [])
            best_days_str = [days_es[day] if 0 <= day < 7 else str(day) for day in best_days_int]

            day_map = {
                "monday": "Lunes", "tuesday": "Martes", "wednesday": "Miércoles",
                "thursday": "Jueves", "friday": "Viernes", "saturday": "Sábado",
                "sunday": "Domingo"
            }

            if training_days:
                training_days_formatted = ", ".join(day_map.get(d, d) for d in training_days)
            else:
                training_days_formatted = "Según perfil"

            if time_available:
                time_formatted = ", ".join(
                    f"{day_map.get(d, d)}: {m} min" for d, m in time_available.items()
                )
            else:
                time_formatted = "Según perfil"

            if session_types:
                session_types_formatted = ", ".join(session_types)
            else:
                session_types_formatted = "Según perfil"

            user_prompt = f"""Genera un plan de entrenamiento semanal completo y detallado.

PERFIL DEL ATLETA:
{coach_context}

DATOS CLAVE:
- Sesiones/semana recientes: {fitness.get('weekly_sessions_avg', 0):.1f}
- Fuerza/semana: {fitness.get('strength_sessions_per_week', 0)} sesiones de {fitness.get('avg_strength_duration_min', 0)} min media
- Cardio/semana: {fitness.get('cardio_sessions_per_week', 0)} sesiones
- ACWR actual: {acwr_ratio:.3f} ({risk_level}) — puede {load_action} carga
- Sueño reciente: {sleep.get('sleep_avg_recent_4w', 0):.2f}h (déficit: {sleep.get('sleep_debt_7d_hours', 0):.1f}h esta semana)
- Recovery score hoy: {recovery.get('recovery_score', 0):.1f}/100
- Mejor día de entrenamiento histórico: {', '.join(best_days_str) if best_days_str else 'N/A'}
- Racha máxima consecutiva: {recovery.get('max_consecutive_training_days', 0)} días

OBJETIVO DEL USUARIO: {goal}
DÍAS DE ENTRENAMIENTO: {training_days_formatted}
TIEMPO POR DÍA: {time_formatted}
TIPOS DE SESIÓN DESEADOS: {session_types_formatted}
INTENSIDAD PREFERIDA: {intensity_preference or "Según perfil"}
CONSIDERAR READINESS ACTUAL: {"Sí" if consider_readiness else "No"}
RESTRICCIONES: {restrictions or "Ninguna"}
SEMANA: {ordered_days[0]} {dates[0].strftime('%d/%m')} al {ordered_days[6]} {dates[6].strftime('%d/%m')}

FECHAS EXACTAS DE CADA DÍA (DEBES usar estas fechas en el campo "date" de cada sesión):
{chr(10).join(f"- {{day}}: {{date}}" for day, date in day_date_map.items())}

RESTRICCIONES IMPORTANTES E INQUEBRANTABLES:
- DÍAS PERMITIDOS: {training_days_formatted}.
- DEBES programar sesiones de entrenamiento ÚNICAMENTE en los días permitidos.
- Los días NO incluidos en los permitidos DEBEN programarse como "session_type": "rest" de forma obligatoria, sin excepciones.
- Atleta masters 47 años: la recuperación es prioritaria, por lo que respetar sus días libres es crítico.
- Si dos días permitidos son consecutivos y hay conflicto de recuperación, ajusta la intensidad, pero NO cambies el día de entrenamiento.
- Incluir al menos 1 sesión de movilidad/flexibilidad en la semana.

ESTRUCTURA JSON REQUERIDA:
{{
  "weekly_goal": "Objetivo específico y medible de esta semana",
  "reasoning": "2-3 frases explicando por qué este plan para este atleta",
  "total_planned_minutes": int,
  "sessions": [
    {{
      "date": "YYYY-MM-DD",
      "day_of_week": "Lunes",
      "session_type": "strength|running|trail_running|mobility|hiit|rest|active_recovery",
      "title": "Nombre descriptivo de la sesión",
      "description": "Descripción detallada del objetivo de la sesión",
      "duration_minutes": int,
      "intensity": "low|medium|high",
      "exercises": [
        {{
          "name": "Nombre del ejercicio",
          "sets": int,
          "reps": "8-10",
          "weight_kg": float,
          "rest_seconds": int,
          "muscle_group": "chest|back|legs|shoulders|arms|core|full_body",
          "notes": "Indicación técnica importante"
        }}
      ],
      "running_details": {{
        "type": "easy|tempo|intervals|long_run|recovery_run",
        "distance_km": float,
        "target_pace_min_km": "5:30",
        "heart_rate_zone": "Z1|Z2|Z3|Z4|Z5",
        "structure": "Descripción de la estructura (ej: 10min calentamiento + 20min tempo + 10min vuelta calma)"
      }},
      "mobility_details": {{
        "focus": "lower_body|upper_body|full_body|spine",
        "techniques": ["foam_rolling", "stretching_estático", "yoga", "respiración"],
        "key_exercises": ["ejercicio 1", "ejercicio 2", "ejercicio 3"]
      }}
    }}
  ],
  "weekly_notes": "Notas generales para la semana",
  "nutrition_focus": "Un consejo nutricional específico para el objetivo",
  "sleep_reminder": "Recordatorio personalizado sobre el sueño basado en el déficit detectado"
}}
"""

            logger.info("Llamando a LLM para generar plan de entrenamiento...")
            ai_service = AIService()
            messages = [{"role": "user", "content": user_prompt}]
            response = ai_service._generate_chat_response(messages, system_prompt)

            content = response["content"]
            logger.info(f"Respuesta recibida de {response['provider']}")

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                plan_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON del LLM: {e}")
                logger.error(f"Contenido recibido: {content[:500]}...")
                raise Exception("El LLM no retornó JSON válido. Por favor intenta de nuevo.")

            # Corregir fechas y forzar descansos en días no seleccionados
            allowed_days = [day_map.get(d, d) for d in training_days] if training_days else None

            for session_data in plan_data.get("sessions", []):
                llm_date = session_data.get("date", "")
                day_name = session_data.get("day_of_week", "")
                if day_name in day_date_map:
                    correct_date = day_date_map[day_name]
                    if llm_date != correct_date:
                        logger.warning(f"Fixing LLM date {llm_date} -> {correct_date} for {day_name}")
                        session_data["date"] = correct_date

                # Post-procesado estricto: forzar descanso si no es día permitido
                if allowed_days and day_name not in allowed_days:
                    if session_data.get("session_type") not in ["rest", "active_recovery"]:
                        logger.warning(f"Forcing rest on {day_name} (LLM hallucinated a workout)")
                        session_data["session_type"] = "rest"
                        session_data["title"] = "Descanso Programado"
                        session_data["description"] = "Día libre según tus preferencias de entrenamiento."
                        session_data["duration_minutes"] = 0
                        session_data["intensity"] = "low"
                        session_data.pop("exercises", None)
                        session_data.pop("running_details", None)
                        session_data.pop("mobility_details", None)

            logger.info("Guardando plan en base de datos...")
            training_plan = AdaptiveTrainingPlan(
                user_id=user_id,
                week_start_date=week_start,
                week_end_date=week_end,
                goal=goal,
                status='active',
                plan_json=json.dumps(plan_data, ensure_ascii=False),
                ai_reasoning=plan_data.get("reasoning", ""),
                fitness_snapshot=json.dumps(profile, ensure_ascii=False)
            )

            db.add(training_plan)
            db.flush()

            for session_data in plan_data.get("sessions", []):
                planned_session = AdaptivePlannedSession(
                    plan_id=training_plan.id,
                    session_date=datetime.strptime(session_data["date"], "%Y-%m-%d").date(),
                    day_of_week=session_data["day_of_week"],
                    session_type=session_data["session_type"],
                    title=session_data["title"],
                    description=session_data.get("description", ""),
                    duration_minutes=session_data.get("duration_minutes"),
                    intensity=session_data.get("intensity"),
                    exercises_json=json.dumps(session_data.get("exercises", []), ensure_ascii=False) if session_data.get("exercises") else None,
                    running_details_json=json.dumps(session_data.get("running_details", {}), ensure_ascii=False) if session_data.get("running_details") else None
                )
                db.add(planned_session)

            db.commit()

            logger.info(f"Plan generado exitosamente con ID={training_plan.id}")

            result = plan_data.copy()
            result["plan_id"] = training_plan.id
            result["week_start"] = week_start.isoformat()
            result["week_end"] = week_end.isoformat()
            result["created_at"] = training_plan.created_at.isoformat()

            return result

        except Exception as e:
            logger.error(f"Error generando plan semanal: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def get_current_plan(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el plan activo actual.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Dict con el plan completo y progreso, o None si no hay plan activo
        """
        try:
            today = date.today()

            plan = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.user_id == user_id,
                    AdaptiveTrainingPlan.status == 'active',
                    AdaptiveTrainingPlan.week_start_date <= today,
                    AdaptiveTrainingPlan.week_end_date >= today
                )
            ).first()

            if not plan:
                return None

            sessions = db.query(AdaptivePlannedSession).filter(
                AdaptivePlannedSession.plan_id == plan.id
            ).order_by(AdaptivePlannedSession.session_date).all()

            completed_count = sum(1 for s in sessions if s.completed)
            total_count = len(sessions)
            progress = {
                "completed": completed_count,
                "total": total_count,
                "percentage": (completed_count / total_count * 100) if total_count > 0 else 0
            }

            plan_data = json.loads(plan.plan_json)

            sessions_dict = {}
            for session in sessions:
                session_data = {
                    "id": session.id,
                    "date": session.session_date.isoformat(),
                    "day_of_week": session.day_of_week,
                    "session_type": session.session_type,
                    "title": session.title,
                    "description": session.description,
                    "duration_minutes": session.duration_minutes,
                    "intensity": session.intensity,
                    "completed": session.completed,
                    "garmin_activity_id": session.garmin_activity_id,
                    "user_notes": session.user_notes,
                    "modified_by_user": session.modified_by_user,
                    "adaptation_reason": session.adaptation_reason
                }

                if session.exercises_json:
                    session_data["exercises"] = json.loads(session.exercises_json)
                if session.running_details_json:
                    session_data["running_details"] = json.loads(session.running_details_json)

                sessions_dict[session.session_date.isoformat()] = session_data

            for session in plan_data.get("sessions", []):
                session_date = session["date"]
                if session_date in sessions_dict:
                    session.update(sessions_dict[session_date])

            return {
                "plan_id": plan.id,
                "week_start": plan.week_start_date.isoformat(),
                "week_end": plan.week_end_date.isoformat(),
                "goal": plan.goal,
                "status": plan.status,
                "created_at": plan.created_at.isoformat(),
                "ai_reasoning": plan.ai_reasoning,
                "progress": progress,
                "plan": plan_data
            }

        except Exception as e:
            logger.error(f"Error obteniendo plan actual: {e}", exc_info=True)
            raise

    @staticmethod
    def update_session(
        db: Session,
        session_id: int,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actualiza una sesión planificada.

        Args:
            db: Sesión de base de datos
            session_id: ID de la sesión
            changes: Diccionario con los cambios a aplicar

        Returns:
            Dict con la sesión actualizada
        """
        try:
            session = db.query(AdaptivePlannedSession).filter(
                AdaptivePlannedSession.id == session_id
            ).first()

            if not session:
                raise Exception(f"Sesión con ID {session_id} no encontrada")

            for key, value in changes.items():
                if hasattr(session, key):
                    if key in ["exercises_json", "running_details_json"] and value is not None:
                        setattr(session, key, json.dumps(value, ensure_ascii=False))
                    else:
                        setattr(session, key, value)

            session.modified_by_user = True

            db.commit()

            result = {
                "id": session.id,
                "date": session.session_date.isoformat(),
                "day_of_week": session.day_of_week,
                "session_type": session.session_type,
                "title": session.title,
                "description": session.description,
                "duration_minutes": session.duration_minutes,
                "intensity": session.intensity,
                "completed": session.completed,
                "garmin_activity_id": session.garmin_activity_id,
                "user_notes": session.user_notes,
                "modified_by_user": session.modified_by_user,
                "adaptation_reason": session.adaptation_reason
            }

            if session.exercises_json:
                result["exercises"] = json.loads(session.exercises_json)
            if session.running_details_json:
                result["running_details"] = json.loads(session.running_details_json)

            logger.info(f"Sesión {session_id} actualizada exitosamente")
            return result

        except Exception as e:
            logger.error(f"Error actualizando sesión {session_id}: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def auto_detect_completed_sessions(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Detecta automáticamente sesiones completadas basándose en actividades de Garmin.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Lista de sesiones marcadas como completadas
        """
        try:
            current_plan = TrainingPlanService.get_current_plan(db, user_id)
            if not current_plan:
                return []

            plan_id = current_plan["plan_id"]

            planned_sessions = db.query(AdaptivePlannedSession).filter(
                and_(
                    AdaptivePlannedSession.plan_id == plan_id,
                    AdaptivePlannedSession.completed == False
                )
            ).all()

            completed_sessions = []

            type_mapping = {
                "strength": "strength_training",
                "running": "running",
                "trail_running": "trail_running",
                "hiit": "indoor_cardio",
                "mobility": "yoga",
                "active_recovery": "walking"
            }

            for planned_session in planned_sessions:
                session_date = planned_session.session_date
                session_type = planned_session.session_type

                target_types = [session_type]
                if session_type in type_mapping:
                    target_types.append(type_mapping[session_type])

                workouts = db.query(Workout).filter(
                    and_(
                        Workout.user_id == user_id,
                        Workout.date == session_date.isoformat()
                    )
                ).all()

                for workout in workouts:
                    workout_sport = None
                    if workout.description:
                        try:
                            desc_data = json.loads(workout.description)
                            workout_sport = desc_data.get("sport")
                        except Exception:
                            pass

                    if workout_sport in target_types:
                        planned_session.completed = True
                        planned_session.garmin_activity_id = str(workout.id)

                        completed_sessions.append({
                            "session_id": planned_session.id,
                            "date": session_date.isoformat(),
                            "session_type": session_type,
                            "title": planned_session.title,
                            "garmin_activity_id": str(workout.id)
                        })

                        logger.info(f"Sesión {planned_session.id} marcada como completada (Garmin activity {workout.id})")
                        break

            db.commit()

            return completed_sessions

        except Exception as e:
            logger.error(f"Error detectando sesiones completadas: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def get_plan_history(db: Session, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de planes de entrenamiento.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Número máximo de planes a retornar

        Returns:
            Lista de planes con información resumida
        """
        try:
            plans = db.query(AdaptiveTrainingPlan).filter(
                AdaptiveTrainingPlan.user_id == user_id
            ).order_by(AdaptiveTrainingPlan.created_at.desc()).limit(limit).all()

            result = []
            for plan in plans:
                sessions = db.query(AdaptivePlannedSession).filter(
                    AdaptivePlannedSession.plan_id == plan.id
                ).all()

                completed_count = sum(1 for s in sessions if s.completed)
                total_count = len(sessions)

                result.append({
                    "plan_id": plan.id,
                    "week_start": plan.week_start_date.isoformat(),
                    "week_end": plan.week_end_date.isoformat(),
                    "goal": plan.goal,
                    "status": plan.status,
                    "created_at": plan.created_at.isoformat(),
                    "completed_sessions": completed_count,
                    "total_sessions": total_count,
                    "completion_percentage": (completed_count / total_count * 100) if total_count > 0 else 0
                })

            return result

        except Exception as e:
            logger.error(f"Error obteniendo historial de planes: {e}", exc_info=True)
            raise

    @staticmethod
    def cancel_plan(db: Session, plan_id: int) -> bool:
        """
        Cancela un plan de entrenamiento.

        Args:
            db: Sesión de base de datos
            plan_id: ID del plan

        Returns:
            True si se canceló exitosamente
        """
        try:
            plan = db.query(AdaptiveTrainingPlan).filter(
                AdaptiveTrainingPlan.id == plan_id
            ).first()

            if not plan:
                raise Exception(f"Plan con ID {plan_id} no encontrado")

            plan.status = 'cancelled'
            db.commit()

            logger.info(f"Plan {plan_id} cancelado exitosamente")
            return True

        except Exception as e:
            logger.error(f"Error cancelando plan {plan_id}: {e}", exc_info=True)
            db.rollback()
            raise
