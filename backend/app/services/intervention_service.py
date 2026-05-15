"""
Intervention Service
====================

Corazón del sistema proactivo de ATLAS VIVO. Evalúa señales, decide
intervenciones, las ejecuta según política de autonomía y registra
resultados para aprendizaje continuo.

Flujo: Event → evaluate_triggers() → create_intervention() → deliver()
         → user responds → respond_to_intervention() → outcome tracking

Autor: ATLAS Team
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.autonomy_policy import (
    AutonomyLevel,
    InterventionType,
    get_autonomy_level,
    resolve_autonomy,
    get_cooldown,
)
from app.db.session import SessionLocal
from app.models.atlas_event import AtlasEvent
from app.models.atlas_intervention import AtlasIntervention

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa: evento → posible intervención
# ---------------------------------------------------------------------------
EVENT_TO_INTERVENTION: dict[str, list[InterventionType]] = {
    "injury_alert": [InterventionType.RISK_ALERT],
    "pain_reported": [InterventionType.RISK_ALERT, InterventionType.CHECK_IN_REQUEST],
    "fatigue_detected": [InterventionType.RECOVERY_ACTIVATE, InterventionType.INTENSITY_ADJUST],
    "adherence_drop": [InterventionType.ADHERENCE_NUDGE, InterventionType.CHECK_IN_REQUEST],
    "recovery_gap": [InterventionType.RECOVERY_ACTIVATE],
    "sleep_deficit": [InterventionType.RECOVERY_ACTIVATE],
    "strain_cliff": [InterventionType.INTENSITY_ADJUST, InterventionType.SESSION_REROUTE],
    "milestone_reached": [InterventionType.OPPORTUNITY],
    "readiness_computed": [InterventionType.INTENSITY_ADJUST],
    "workout_logged": [InterventionType.CHECK_IN_REQUEST],
    "session_completed": [InterventionType.INTENSITY_ADJUST],
    "goal_progress": [InterventionType.OPPORTUNITY],
}


class InterventionService:
    """Servicio central de intervenciones proactivas."""

    # ------------------------------------------------------------------
    # Evaluación de triggers
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_triggers(event: AtlasEvent) -> Optional[AtlasIntervention]:
        """
        Evalúa si un evento debe disparar una intervención.

        Llamado por event_bus_service.process_pending() para cada
        evento pendiente. Retorna la intervención creada o None.
        """
        try:
            possible_types = EVENT_TO_INTERVENTION.get(event.event_type)
            if not possible_types:
                return None

            # Obtener estado actual del atleta para evaluación de autonomía
            athlete_state = InterventionService._get_athlete_state(event.user_id)

            # Intentar cada tipo de intervención posible hasta que uno
            # pase los filtros (cooldown, límite diario, etc.)
            for itype in possible_types:
                if InterventionService._check_cooldown(event.user_id, itype):
                    continue
                if InterventionService._check_daily_limit(event.user_id):
                    continue

                return InterventionService.create_intervention(
                    user_id=event.user_id,
                    intervention_type=itype,
                    source_event_id=event.id,
                    correlation_id=event.correlation_id,
                    athlete_state=athlete_state,
                    payload=event.payload,
                )

            return None

        except Exception as e:
            logger.error("Error evaluando trigger para evento %s: %s", event.id, e)
            return None

    # ------------------------------------------------------------------
    # Creación de intervenciones
    # ------------------------------------------------------------------

    @staticmethod
    def create_intervention(
        user_id: str,
        intervention_type: InterventionType,
        source_event_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        athlete_state: Optional[dict] = None,
        payload: Optional[dict] = None,
        custom_message: Optional[str] = None,
        force_level: Optional[AutonomyLevel] = None,
    ) -> Optional[AtlasIntervention]:
        """
        Crea y entrega una intervención.

        - Determina nivel de autonomía (a menos que se force)
        - Si FORBIDDEN → descarta silenciosamente
        - Si AUTONOMOUS → ejecuta inmediatamente
        - Si PROPOSAL/VALIDATION → envía notificación al usuario
        """
        try:
            # 1. Resolver nivel de autonomía
            if force_level:
                level = force_level
            else:
                level = resolve_autonomy(
                    intervention_type,
                    athlete_state or {},
                )

            if level == AutonomyLevel.FORBIDDEN:
                logger.info(
                    "Intervención %s bloqueada (FORBIDDEN) para %s",
                    intervention_type.name, user_id,
                )
                return None

            # 2. Generar título y mensaje
            title, message = InterventionService._build_message(
                intervention_type, payload, athlete_state,
            )

            # 3. Persistir
            now = datetime.utcnow()
            deadline = now + timedelta(hours=24) if level in (
                AutonomyLevel.PROPOSAL, AutonomyLevel.VALIDATION,
            ) else None

            with SessionLocal() as db:
                intervention = AtlasIntervention(
                    user_id=user_id,
                    intervention_type=intervention_type.name.lower(),
                    autonomy_level=level.name,
                    title=title,
                    message=custom_message or message,
                    priority=InterventionService._resolve_priority(
                        intervention_type, athlete_state,
                    ),
                    status="pending",
                    created_at=now,
                    decision_deadline=deadline,
                    source_event_id=source_event_id,
                    correlation_id=correlation_id,
                    extra_data={
                        "athlete_state": athlete_state or {},
                        "payload": payload or {},
                        "intervention_type": intervention_type.name,
                    },
                )
                db.add(intervention)
                db.commit()
                db.refresh(intervention)

            # 4. Entregar según nivel de autonomía
            InterventionService._deliver(intervention, level)

            return intervention

        except Exception as e:
            logger.error("Error creando intervención: %s", e)
            return None

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    @staticmethod
    def execute_intervention(intervention_id: int) -> bool:
        """Ejecuta una intervención (acciones de sistema)."""
        try:
            with SessionLocal() as db:
                intervention = db.query(AtlasIntervention).filter(
                    AtlasIntervention.id == intervention_id,
                ).first()
                if not intervention:
                    logger.warning("Intervención %s no encontrada", intervention_id)
                    return False

                itype = InterventionType[intervention.intervention_type.upper()]

                # Acción según tipo
                success = InterventionService._execute_action(itype, intervention)

                if success:
                    intervention.status = "executed"
                    intervention.executed_at = datetime.utcnow()

                db.commit()
                return success

        except Exception as e:
            logger.error("Error ejecutando intervención %s: %s", intervention_id, e)
            return False

    @staticmethod
    def _execute_action(
        itype: InterventionType,
        intervention: AtlasIntervention,
    ) -> bool:
        """
        Ejecuta la acción concreta según el tipo de intervención.

        Cada tipo puede tener efectos diferentes en el sistema:
        - INTENSITY_ADJUST: ajustar plan de entrenamiento
        - RECOVERY_ACTIVATE: activar modo recuperación
        - ADHERENCE_NUDGE: enviar recordatorio adicional
        - RISK_ALERT: elevar nivel de alerta
        - Otros: acción mínima (log)
        """
        logger.info(
            "Ejecutando %s para %s (intervención %s)",
            itype.name, intervention.user_id, intervention.id,
        )

        # Por ahora: log + notificación de sistema
        from app.services.notification_service import NotificationService
        try:
            NotificationService.send_notification(
                title=f"⚡ ATLAS: {intervention.title}",
                message=intervention.message,
                notification_type="intervention_executed",
                priority="high" if intervention.priority == "high" else "medium",
                channels=["app", "system"],
                metadata={"intervention_id": intervention.id},
            )
        except Exception as e:
            logger.warning("Notificación de ejecución falló: %s", e)

        return True

    # ------------------------------------------------------------------
    # Respuesta del usuario
    # ------------------------------------------------------------------

    @staticmethod
    def respond_to_intervention(
        intervention_id: int,
        user_id: str,
        response: str,
        response_data: Optional[dict] = None,
    ) -> bool:
        """
        Procesa la respuesta del usuario a una intervención.

        Responses válidas: accepted, rejected, snoozed
        """
        valid_responses = {"accepted", "rejected", "snoozed"}
        if response not in valid_responses:
            logger.warning("Respuesta inválida: %s", response)
            return False

        try:
            with SessionLocal() as db:
                intervention = db.query(AtlasIntervention).filter(
                    AtlasIntervention.id == intervention_id,
                    AtlasIntervention.user_id == user_id,
                ).first()

                if not intervention:
                    logger.warning("Intervención %s no encontrada", intervention_id)
                    return False

                if intervention.status != "pending":
                    logger.warning(
                        "Intervención %s ya no está pendiente (status=%s)",
                        intervention_id, intervention.status,
                    )
                    return False

                intervention.response = response
                intervention.response_data = response_data or {}
                intervention.responded_at = datetime.utcnow()

                if response == "accepted":
                    intervention.status = "accepted"
                    # Si se acepta, ejecutar la acción
                    db.commit()
                    InterventionService.execute_intervention(intervention_id)
                elif response == "rejected":
                    intervention.status = "rejected"
                    db.commit()
                elif response == "snoozed":
                    # Reprogramar para 4h después
                    intervention.decision_deadline = datetime.utcnow() + timedelta(hours=4)
                    db.commit()

                return True

        except Exception as e:
            logger.error("Error procesando respuesta: %s", e)
            return False

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_pending(user_id: str) -> list[AtlasIntervention]:
        """Intervenciones pendientes (no expiradas)."""
        try:
            with SessionLocal() as db:
                now = datetime.utcnow()
                return db.query(AtlasIntervention).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.status == "pending",
                    (
                        AtlasIntervention.decision_deadline.is_(None)
                        | (AtlasIntervention.decision_deadline > now)
                    ),
                ).order_by(
                    AtlasIntervention.created_at.desc(),
                ).all()
        except Exception as e:
            logger.error("Error obteniendo intervenciones pendientes: %s", e)
            return []

    @staticmethod
    def get_active(user_id: str) -> list[AtlasIntervention]:
        """Intervenciones activas (pending + accepted + executed recientes)."""
        try:
            with SessionLocal() as db:
                cutoff = datetime.utcnow() - timedelta(days=7)
                return db.query(AtlasIntervention).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.created_at >= cutoff,
                    AtlasIntervention.is_active == True,
                ).order_by(
                    AtlasIntervention.created_at.desc(),
                ).all()
        except Exception as e:
            logger.error("Error obteniendo intervenciones activas: %s", e)
            return []

    @staticmethod
    def get_history(
        user_id: str,
        days: int = 30,
        status_filter: Optional[str] = None,
    ) -> list[AtlasIntervention]:
        """Historial de intervenciones."""
        try:
            with SessionLocal() as db:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = db.query(AtlasIntervention).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.created_at >= cutoff,
                )
                if status_filter:
                    query = query.filter(AtlasIntervention.status == status_filter)
                return query.order_by(
                    AtlasIntervention.created_at.desc(),
                ).all()
        except Exception as e:
            logger.error("Error obteniendo historial: %s", e)
            return []

    @staticmethod
    def get_stats(user_id: str) -> dict[str, Any]:
        """Estadísticas de intervenciones para un usuario."""
        try:
            with SessionLocal() as db:
                total = db.query(sa_func.count(AtlasIntervention.id)).filter(
                    AtlasIntervention.user_id == user_id,
                ).scalar() or 0

                pending = db.query(sa_func.count(AtlasIntervention.id)).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.status == "pending",
                ).scalar() or 0

                accepted = db.query(sa_func.count(AtlasIntervention.id)).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.status == "accepted",
                ).scalar() or 0

                rejected = db.query(sa_func.count(AtlasIntervention.id)).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.status == "rejected",
                ).scalar() or 0

                return {
                    "total": total,
                    "pending": pending,
                    "accepted": accepted,
                    "rejected": rejected,
                    "acceptance_rate": round(
                        accepted / (accepted + rejected) * 100, 1
                    ) if (accepted + rejected) > 0 else 0,
                }
        except Exception as e:
            logger.error("Error obteniendo stats: %s", e)
            return {}

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------

    @staticmethod
    def expire_pending() -> int:
        """Marca como expiradas las intervenciones pendientes vencidas."""
        try:
            with SessionLocal() as db:
                now = datetime.utcnow()
                expired = db.query(AtlasIntervention).filter(
                    AtlasIntervention.status == "pending",
                    AtlasIntervention.decision_deadline.isnot(None),
                    AtlasIntervention.decision_deadline < now,
                ).all()

                count = 0
                for inv in expired:
                    inv.status = "expired"
                    count += 1

                if count:
                    db.commit()
                    logger.info("Expiradas %s intervenciones pendientes", count)

                return count

        except Exception as e:
            logger.error("Error expirando intervenciones: %s", e)
            return 0

    @staticmethod
    def cleanup_old(days: int = 90) -> int:
        """Archiva intervenciones antiguas."""
        try:
            with SessionLocal() as db:
                cutoff = datetime.utcnow() - timedelta(days=days)
                old = db.query(AtlasIntervention).filter(
                    AtlasIntervention.created_at < cutoff,
                ).all()

                count = 0
                for inv in old:
                    inv.is_active = False
                    count += 1

                if count:
                    db.commit()
                    logger.info("Archivadas %s intervenciones antiguas", count)

                return count

        except Exception as e:
            logger.error("Error limpiando intervenciones: %s", e)
            return 0

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _get_athlete_state(user_id: str) -> Optional[dict]:
        """Obtiene el estado narrativo actual del atleta."""
        try:
            from app.services.athlete_state_service import AthleteStateService
            state = AthleteStateService.get_state(user_id)
            if state:
                return {
                    "energy": state.energy,
                    "adherence": state.adherence,
                    "momentum": state.momentum,
                    "risk": state.risk,
                    "motivation": state.motivation,
                    "training_phase": state.training_phase,
                    "readiness_score": state.readiness_score,
                }
        except Exception as e:
            logger.debug("No se pudo obtener estado del atleta: %s", e)
        return None

    @staticmethod
    def _build_message(
        itype: InterventionType,
        payload: Optional[dict],
        athlete_state: Optional[dict],
    ) -> tuple[str, str]:
        """Genera título y mensaje contextual para la intervención."""
        templates = {
            InterventionType.INTENSITY_ADJUST: (
                "Ajuste de intensidad",
                "He notado cambios en tu recuperación. ¿Revisamos la carga de hoy?",
            ),
            InterventionType.RECOVERY_ACTIVATE: (
                "Modo recuperación",
                "Tus señales sugieren que necesitas más descanso. ¿Activamos recuperación?",
            ),
            InterventionType.ADHERENCE_NUDGE: (
                "¿Todo bien?",
                "Llevas un tiempo sin entrenar. ¿Necesitas ajustar el plan?",
            ),
            InterventionType.SESSION_REROUTE: (
                "Cambio de sesión",
                "Tus métricas sugieren cambiar el entrenamiento de hoy.",
            ),
            InterventionType.CHECK_IN_REQUEST: (
                "¿Cómo te sientes?",
                "Una rápida actualización ayuda a ajustar tu plan.",
            ),
            InterventionType.RISK_ALERT: (
                "Alerta de riesgo",
                "He detectado señales que requieren atención. Revisemos juntos.",
            ),
            InterventionType.OPPORTUNITY: (
                "¡Buen momento!",
                "Tu tendencia es positiva. ¿Aprovechamos para un reto?",
            ),
            InterventionType.WEEKLY_REVIEW: (
                "Revisión semanal",
                "Tu plan semanal necesita ajustes. ¿Revisamos?",
            ),
            InterventionType.PLAN_PROPOSAL: (
                "Propuesta de plan",
                "Tengo una propuesta para tu próxima semana. ¿La revisamos?",
            ),
        }

        title, message = templates.get(
            itype,
            ("Notificación de ATLAS", "Tengo algo importante que contarte."),
        )

        # Personalizar según payload
        if payload:
            if "readiness_score" in payload:
                score = payload["readiness_score"]
                if score is not None and score < 50:
                    message = (
                        f"Tu readiness está en {score:.0f}. "
                        "Sugiero bajar la intensidad hoy."
                    )

            if "pain_level" in payload:
                level = payload["pain_level"]
                message = (
                    f"Reportaste dolor (nivel {level}). "
                    "¿Quieres que ajustemos el plan?"
                )

        return title, message

    @staticmethod
    def _resolve_priority(
        itype: InterventionType,
        athlete_state: Optional[dict],
    ) -> str:
        """Determina la prioridad de la intervención."""
        if itype in (InterventionType.RISK_ALERT,):
            return "high"
        if athlete_state:
            risk = athlete_state.get("risk", "low")
            if risk in ("acute", "high"):
                return "high"
            if risk == "moderate":
                return "medium"
        return "medium"

    @staticmethod
    def _check_cooldown(user_id: str, itype: InterventionType) -> bool:
        """True si el tipo de intervención está en cooldown."""
        try:
            cooldown = get_cooldown(itype)
            if cooldown.total_seconds() <= 0:
                return False

            cutoff = datetime.utcnow() - cooldown
            with SessionLocal() as db:
                recent = db.query(AtlasIntervention).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.intervention_type == itype.name.lower(),
                    AtlasIntervention.created_at >= cutoff,
                ).first()
                return recent is not None

        except Exception as e:
            logger.debug("Error en check_cooldown: %s", e)
            return False

    @staticmethod
    def _check_daily_limit(user_id: str) -> bool:
        """True si se excedió el límite diario de intervenciones."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=1)
            with SessionLocal() as db:
                count = db.query(sa_func.count(AtlasIntervention.id)).filter(
                    AtlasIntervention.user_id == user_id,
                    AtlasIntervention.created_at >= cutoff,
                ).scalar() or 0
                return count >= 8  # saturación
        except Exception as e:
            logger.debug("Error en check_daily_limit: %s", e)
            return False

    @staticmethod
    def _deliver(
        intervention: AtlasIntervention,
        level: AutonomyLevel,
    ) -> None:
        """Entrega la intervención al usuario según el nivel."""
        try:
            if level == AutonomyLevel.AUTONOMOUS:
                # Ejecutar inmediatamente
                InterventionService.execute_intervention(intervention.id)

            elif level in (AutonomyLevel.PROPOSAL, AutonomyLevel.VALIDATION):
                # Enviar notificación al usuario
                from app.services.notification_service import NotificationService
                NotificationService.send_notification(
                    title=f"💡 {intervention.title}",
                    message=intervention.message,
                    notification_type="intervention_proposal",
                    priority=intervention.priority,
                    channels=["app"],
                    action_url=f"/interventions/{intervention.id}",
                    metadata={
                        "intervention_id": intervention.id,
                        "intervention_type": intervention.intervention_type,
                        "autonomy_level": level.name,
                    },
                )
        except Exception as e:
            logger.error("Error delivering intervention %s: %s", intervention.id, e)
