"""
Master Plan Service
===================

Servicio para gestión de planes maestros de entrenamiento a largo plazo.

Funciones principales:
- create_master_plan(): Crea un plan maestro con periodización científica
- get_active_master_plan(): Obtiene el plan maestro activo actual
- propose_next_week(): Propone la siguiente semana del plan
- confirm_week(): Confirma una semana propuesta
- get_master_plan_progress(): Obtiene el progreso del plan maestro
"""

import logging
import json
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, text

from app.services.ai_service import AIService
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from app.services.training_plan_service import TrainingPlanService
from app.models.master_plan import MasterPlan
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession

logger = logging.getLogger("app.services.master_plan_service")


def _clean_json_response(content: str) -> dict:
    """Limpia y parsea respuesta JSON del LLM manejando todos los formatos posibles."""
    if not content:
        raise ValueError("Respuesta vacía del LLM")

    content = content.strip()

    for pattern in ['```json\n', '```json', '```\n', '```']:
        if content.startswith(pattern):
            content = content[len(pattern):]
            break
    if content.endswith('```'):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = content[first_brace:last_brace + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Content preview: {json_candidate[:500]}")
            raise ValueError(f"No se pudo parsear respuesta del LLM como JSON: {e}")

    raise ValueError("No se encontró JSON válido en la respuesta del LLM")


class MasterPlanService:

    @staticmethod
    def create_master_plan(
        db: Session,
        user_id: str,
        goal: str,
        target_date: Optional[date] = None,
        preferred_days: Optional[List[str]] = None,
        time_per_session_minutes: int = 60,
        intensity_preference: str = "medium",
        restrictions: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            today = date.today()

            if target_date:
                total_weeks = max(4, min(52, (target_date - today).days // 7))
            else:
                total_weeks = 8

            profile = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
            coach_context = profile.get("coach_context_summary", "")
            risk = profile.get("overreaching_risk", {})
            acwr_ratio = risk.get("acwr_ratio", 1.0)

            system_prompt = (
                "Eres ATLAS, coach de alto rendimiento. Diseñas estrategias de entrenamiento "
                "a largo plazo basadas en periodización científica. Respondes SOLO en JSON válido, "
                "sin markdown ni texto extra."
            )

            user_prompt = (
                f"Genera un Plan Maestro de Entrenamiento con periodización científica.\n\n"
                f"PERFIL DEL ATLETA:\n{coach_context}\n\n"
                f"ACWR actual: {acwr_ratio:.3f}\n\n"
                f"OBJETIVO: {goal}\n"
                f"FECHA LÍMITE: {target_date.isoformat() if target_date else 'Sin fecha límite (8 semanas renovables)'}\n"
                f"TOTAL DE SEMANAS: {total_weeks}\n\n"
                f"PREFERENCIAS:\n"
                f"- Días preferidos: {', '.join(preferred_days) if preferred_days else 'Según perfil'}\n"
                f"- Tiempo por sesión: {time_per_session_minutes} minutos\n"
                f"- Intensidad preferida: {intensity_preference}\n"
                f"- Restricciones: {restrictions or 'Ninguna'}\n\n"
                f"ESTRUCTURA JSON REQUERIDA:\n"
                '{{\n'
                '  "title": "Nombre descriptivo del plan",\n'
                '  "strategy": "Resumen de la estrategia de periodización (2-3 frases)",\n'
                '  "phases": [\n'
                '    {{\n'
                '      "phase_number": 1,\n'
                '      "name": "Nombre de la fase (ej: Adaptación Anatómica)",\n'
                '      "description": "Descripción del objetivo y enfoque de esta fase",\n'
                '      "start_week": 1,\n'
                '      "end_week": 3,\n'
                '      "focus": ["strength", "mobility"],\n'
                '      "intensity": "low",\n'
                '      "weekly_volume_hours": 3.5\n'
                '    }}\n'
                '  ],\n'
                '  "milestones": [\n'
                '    {{\n'
                '      "week": 4,\n'
                '      "description": "Descripción del hito esperado",\n'
                '      "metric": "strength_volume",\n'
                '      "target": "Aumentar volumen de fuerza en 15%"\n'
                '    }}\n'
                '  ],\n'
                '  "weekly_template": {{\n'
                f'    "default_training_days": {preferred_days or ["monday", "wednesday", "friday"]},\n'
                f'    "default_session_duration_minutes": {time_per_session_minutes},\n'
                f'    "default_intensity": "{intensity_preference}"\n'
                '  }}\n'
                '}}\n\n'
                f"REGLAS:\n"
                f"- Las fases deben cubrir todas las {total_weeks} semanas sin solapamientos\n"
                f"- Cada fase debe tener objetivos claros y progresivos\n"
                f"- Incluir al menos 3 milestones intermedios\n"
                f"- Considerar el ACWR actual para la carga de la primera fase\n"
                f"- La última fase debe incluir una descarga (deload) si hay fecha objetivo"
            )

            ai_service = AIService()
            messages = [{"role": "user", "content": user_prompt}]

            MAX_RETRIES = 2
            plan_data = None
            last_error = None
            for attempt in range(1, MAX_RETRIES + 2):
                response = ai_service._generate_chat_response(messages, system_prompt)
                try:
                    plan_data = _clean_json_response(response["content"])
                    logger.info(f"Plan maestro generado por {response['provider']} (intento {attempt})")
                    break
                except ValueError as parse_err:
                    last_error = parse_err
                    logger.warning(f"Intento {attempt}/{MAX_RETRIES + 1}: JSON parse failed - {parse_err}")
                    if attempt <= MAX_RETRIES:
                        messages.append({"role": "assistant", "content": response["content"]})
                        messages.append({
                            "role": "user",
                            "content": "Tu respuesta anterior no fue JSON válido. Responde SOLO con el JSON solicitado, sin texto adicional ni bloques de código markdown."
                        })
                        time.sleep(1)
                    else:
                        logger.error("Todos los intentos de parseo fallaron para plan maestro")
                        raise

            if plan_data is None:
                raise last_error or ValueError("No se pudo generar el plan maestro")

            master_plan = MasterPlan(
                user_id=user_id,
                title=plan_data["title"],
                goal=goal,
                target_date=target_date,
                start_date=today,
                status="active",
                total_weeks=total_weeks,
                current_week=1,
                phases_json=json.dumps(plan_data["phases"], ensure_ascii=False),
                milestones_json=json.dumps(plan_data["milestones"], ensure_ascii=False),
                ai_strategy=plan_data.get("strategy", ""),
                preferences_json=json.dumps({
                    "preferred_days": preferred_days,
                    "time_per_session_minutes": time_per_session_minutes,
                    "intensity_preference": intensity_preference,
                    "restrictions": restrictions
                }, ensure_ascii=False)
            )

            db.add(master_plan)
            db.flush()

            phases = plan_data["phases"]
            phase1 = phases[0] if phases else {}
            phase1_name = phase1.get("name", "Fase 1")
            phase1_description = phase1.get("description", "")
            phase1_focus = phase1.get("focus", ["strength"])
            phase1_intensity = phase1.get("intensity", intensity_preference)

            phase_goal = f"Fase 1 - {phase1_name}: {phase1_description}. {goal}"

            time_available = {day: time_per_session_minutes for day in (preferred_days or ["monday", "wednesday", "friday"])}

            first_week = TrainingPlanService.generate_weekly_plan(
                db=db,
                user_id=user_id,
                goal=phase_goal,
                week_start=today,
                training_days=preferred_days,
                time_available=time_available,
                session_types=phase1_focus,
                intensity_preference=phase1_intensity,
                consider_readiness=True,
                restrictions=restrictions
            )

            weekly_plan = db.query(AdaptiveTrainingPlan).filter(
                AdaptiveTrainingPlan.id == first_week["plan_id"]
            ).first()

            if weekly_plan:
                weekly_plan.master_plan_id = master_plan.id
                weekly_plan.phase_number = 1
                weekly_plan.week_number = 1
                weekly_plan.confirmed_by_user = False

            db.commit()

            return {
                "master_plan": {
                    "id": master_plan.id,
                    "title": master_plan.title,
                    "goal": master_plan.goal,
                    "target_date": master_plan.target_date.isoformat() if master_plan.target_date else None,
                    "start_date": master_plan.start_date.isoformat(),
                    "total_weeks": master_plan.total_weeks,
                    "current_week": master_plan.current_week,
                    "phases": plan_data["phases"],
                    "milestones": plan_data["milestones"],
                    "strategy": master_plan.ai_strategy,
                    "preferences": json.loads(master_plan.preferences_json) if master_plan.preferences_json else {}
                },
                "first_week": first_week
            }

        except Exception as e:
            logger.error(f"Error creando plan maestro: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def get_active_master_plan(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            master_plan = db.query(MasterPlan).filter(
                and_(
                    MasterPlan.user_id == user_id,
                    MasterPlan.status == "active"
                )
            ).order_by(MasterPlan.created_at.desc()).first()

            if not master_plan:
                return None

            completed_weeks = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.master_plan_id == master_plan.id,
                    AdaptiveTrainingPlan.status == "completed"
                )
            ).count()

            current_week = master_plan.current_week

            phases = json.loads(master_plan.phases_json) if master_plan.phases_json else []
            current_phase = None
            for phase in phases:
                if phase.get("start_week") <= current_week <= phase.get("end_week"):
                    current_phase = phase
                    break

            current_weekly_plan = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.master_plan_id == master_plan.id,
                    AdaptiveTrainingPlan.week_number == current_week
                )
            ).first()

            next_unconfirmed = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.master_plan_id == master_plan.id,
                    AdaptiveTrainingPlan.confirmed_by_user == False
                )
            ).order_by(AdaptiveTrainingPlan.week_number).first()

            days_remaining = None
            if master_plan.target_date:
                days_remaining = (master_plan.target_date - date.today()).days

            result = {
                "id": master_plan.id,
                "title": master_plan.title,
                "goal": master_plan.goal,
                "status": master_plan.status,
                "start_date": master_plan.start_date.isoformat() if master_plan.start_date else None,
                "target_date": master_plan.target_date.isoformat() if master_plan.target_date else None,
                "total_weeks": master_plan.total_weeks,
                "current_week": current_week,
                "completed_weeks": completed_weeks,
                "phases": phases,
                "current_phase": current_phase,
                "milestones": json.loads(master_plan.milestones_json) if master_plan.milestones_json else [],
                "strategy": master_plan.ai_strategy,
                "preferences": json.loads(master_plan.preferences_json) if master_plan.preferences_json else {},
                "days_remaining": days_remaining,
                "current_weekly_plan": {
                    "id": current_weekly_plan.id,
                    "week_start": current_weekly_plan.week_start_date.isoformat(),
                    "week_end": current_weekly_plan.week_end_date.isoformat(),
                    "goal": current_weekly_plan.goal,
                    "status": current_weekly_plan.status,
                    "week_number": current_weekly_plan.week_number,
                    "phase_number": current_weekly_plan.phase_number,
                    "confirmed_by_user": current_weekly_plan.confirmed_by_user
                } if current_weekly_plan else None,
                "next_unconfirmed_week": {
                    "id": next_unconfirmed.id,
                    "week_number": next_unconfirmed.week_number,
                    "phase_number": next_unconfirmed.phase_number,
                    "goal": next_unconfirmed.goal
                } if next_unconfirmed else None
            }

            return result

        except Exception as e:
            logger.error(f"Error obteniendo plan maestro activo: {e}", exc_info=True)
            raise

    @staticmethod
    def propose_next_week(db: Session, master_plan_id: int) -> Dict[str, Any]:
        try:
            master_plan = db.query(MasterPlan).filter(MasterPlan.id == master_plan_id).first()

            if not master_plan:
                raise Exception(f"Plan maestro con ID {master_plan_id} no encontrado")

            next_week = master_plan.current_week + 1

            if next_week > master_plan.total_weeks:
                return {"error": "Plan completado", "message": "El plan maestro ha finalizado. Considera crear uno nuevo."}

            phases = json.loads(master_plan.phases_json) if master_plan.phases_json else []
            current_phase = None
            for phase in phases:
                if phase.get("start_week") <= next_week <= phase.get("end_week"):
                    current_phase = phase
                    break

            previous_week_plan = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.master_plan_id == master_plan.id,
                    AdaptiveTrainingPlan.week_number == master_plan.current_week
                )
            ).first()

            previous_week_data = None
            if previous_week_plan:
                previous_week_data = {
                    "goal": previous_week_plan.goal,
                    "status": previous_week_plan.status,
                    "plan_json": json.loads(previous_week_plan.plan_json) if previous_week_plan.plan_json else {}
                }

            readiness_scores = []
            try:
                rows = db.execute(
                    text("SELECT readiness_score FROM daily_readiness WHERE user_id = :uid ORDER BY date DESC LIMIT 7"),
                    {"uid": master_plan.user_id}
                ).fetchall()
                readiness_scores = [row[0] for row in rows]
            except Exception:
                readiness_scores = []

            acwr_ratio = 1.0
            try:
                profile = AthleticIntelligenceService.get_full_athletic_profile(db, master_plan.user_id)
                risk = profile.get("overreaching_risk", {})
                acwr_ratio = risk.get("acwr_ratio", 1.0)
            except Exception:
                pass

            phase_name = current_phase.get("name", f"Fase {current_phase.get('phase_number', '')}") if current_phase else "Transición"
            phase_description = current_phase.get("description", "") if current_phase else ""
            phase_focus = current_phase.get("focus", ["strength"]) if current_phase else ["strength"]
            phase_intensity = current_phase.get("intensity", "medium") if current_phase else "medium"

            phase_context = ""
            if current_phase:
                phase_context = f"\nContexto de fase actual: {phase_name} - {phase_description}"
                phase_context += f"\nEnfoque de fase: {', '.join(phase_focus)}"
                phase_context += f"\nIntensidad de fase: {phase_intensity}"

            if previous_week_data:
                phase_context += f"\n\nSemana anterior completada con estado: {previous_week_data['status']}"

            if readiness_scores:
                avg_readiness = sum(readiness_scores) / len(readiness_scores)
                phase_context += f"\nReadiness promedio últimos 7 días: {avg_readiness:.1f}/100"

            if acwr_ratio != 1.0:
                phase_context += f"\nACWR actual: {acwr_ratio:.3f}"

            preferences = json.loads(master_plan.preferences_json) if master_plan.preferences_json else {}
            preferred_days = preferences.get("preferred_days", ["monday", "wednesday", "friday"])
            time_per_session = preferences.get("time_per_session_minutes", 60)
            restrictions = preferences.get("restrictions")

            phase_goal = f"Fase {current_phase.get('phase_number', '')} - {phase_name}: {phase_description}. {master_plan.goal}"

            week_start = master_plan.start_date + timedelta(weeks=next_week - 1)

            time_available = {day: time_per_session for day in preferred_days}

            proposed_week = TrainingPlanService.generate_weekly_plan(
                db=db,
                user_id=master_plan.user_id,
                goal=phase_goal,
                week_start=week_start,
                training_days=preferred_days,
                time_available=time_available,
                session_types=phase_focus,
                intensity_preference=phase_intensity,
                consider_readiness=True,
                restrictions=restrictions
            )

            weekly_plan = db.query(AdaptiveTrainingPlan).filter(
                AdaptiveTrainingPlan.id == proposed_week["plan_id"]
            ).first()

            if weekly_plan:
                weekly_plan.master_plan_id = master_plan.id
                weekly_plan.phase_number = current_phase.get("phase_number", 1) if current_phase else 1
                weekly_plan.week_number = next_week
                weekly_plan.confirmed_by_user = False

            db.commit()

            return proposed_week

        except Exception as e:
            logger.error(f"Error proponiendo siguiente semana: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def confirm_week(db: Session, weekly_plan_id: int) -> Dict[str, Any]:
        try:
            weekly_plan = db.query(AdaptiveTrainingPlan).filter(
                AdaptiveTrainingPlan.id == weekly_plan_id
            ).first()

            if not weekly_plan:
                raise Exception(f"Plan semanal con ID {weekly_plan_id} no encontrado")

            weekly_plan.confirmed_by_user = True
            weekly_plan.status = "active"

            master_plan = None
            if weekly_plan.master_plan_id:
                master_plan = db.query(MasterPlan).filter(
                    MasterPlan.id == weekly_plan.master_plan_id
                ).first()

            if master_plan:
                master_plan.current_week = weekly_plan.week_number

            db.commit()

            result = {
                "id": weekly_plan.id,
                "week_start": weekly_plan.week_start_date.isoformat(),
                "week_end": weekly_plan.week_end_date.isoformat(),
                "goal": weekly_plan.goal,
                "status": weekly_plan.status,
                "week_number": weekly_plan.week_number,
                "phase_number": weekly_plan.phase_number,
                "confirmed_by_user": weekly_plan.confirmed_by_user,
                "master_plan_current_week": master_plan.current_week if master_plan else None
            }

            return result

        except Exception as e:
            logger.error(f"Error confirmando semana: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def get_master_plan_progress(db: Session, master_plan_id: int) -> Dict[str, Any]:
        try:
            master_plan = db.query(MasterPlan).filter(
                MasterPlan.id == master_plan_id
            ).first()

            if not master_plan:
                raise Exception(f"Plan maestro con ID {master_plan_id} no encontrado")

            phases = json.loads(master_plan.phases_json) if master_plan.phases_json else []
            milestones = json.loads(master_plan.milestones_json) if master_plan.milestones_json else []
            current_week = master_plan.current_week

            phase_timeline = []
            for phase in phases:
                start_week = phase.get("start_week", 1)
                end_week = phase.get("end_week", 1)

                if current_week > end_week:
                    status = "completed"
                elif start_week <= current_week <= end_week:
                    status = "current"
                else:
                    status = "pending"

                phase_timeline.append({
                    "phase_number": phase.get("phase_number"),
                    "name": phase.get("name"),
                    "description": phase.get("description"),
                    "start_week": start_week,
                    "end_week": end_week,
                    "focus": phase.get("focus", []),
                    "intensity": phase.get("intensity"),
                    "status": status
                })

            achieved_milestones = []
            try:
                personal_records = db.execute(
                    text("SELECT metric, value, date FROM personal_records WHERE user_id = :uid ORDER BY date DESC"),
                    {"uid": master_plan.user_id}
                ).fetchall()

                pr_lookup = {}
                for row in personal_records:
                    metric = row[0]
                    if metric not in pr_lookup:
                        pr_lookup[metric] = row

                for milestone in milestones:
                    metric = milestone.get("metric", "")
                    target = milestone.get("target", "")
                    achieved = metric in pr_lookup
                    achieved_milestones.append({
                        "week": milestone.get("week"),
                        "description": milestone.get("description"),
                        "metric": metric,
                        "target": target,
                        "achieved": achieved
                    })
            except Exception:
                for milestone in milestones:
                    achieved_milestones.append({
                        "week": milestone.get("week"),
                        "description": milestone.get("description"),
                        "metric": milestone.get("metric", ""),
                        "target": milestone.get("target", ""),
                        "achieved": False
                    })

            completed_weeks = db.query(AdaptiveTrainingPlan).filter(
                and_(
                    AdaptiveTrainingPlan.master_plan_id == master_plan.id,
                    AdaptiveTrainingPlan.status == "completed"
                )
            ).count()

            completion_pct = (completed_weeks / master_plan.total_weeks * 100) if master_plan.total_weeks > 0 else 0

            return {
                "id": master_plan.id,
                "title": master_plan.title,
                "goal": master_plan.goal,
                "status": master_plan.status,
                "current_week": current_week,
                "total_weeks": master_plan.total_weeks,
                "completed_weeks": completed_weeks,
                "completion_pct": round(completion_pct, 1),
                "phase_timeline": phase_timeline,
                "milestones": achieved_milestones,
                "days_remaining": (master_plan.target_date - date.today()).days if master_plan.target_date else None,
                "start_date": master_plan.start_date.isoformat() if master_plan.start_date else None,
                "target_date": master_plan.target_date.isoformat() if master_plan.target_date else None
            }

        except Exception as e:
            logger.error(f"Error obteniendo progreso del plan maestro: {e}", exc_info=True)
            raise
