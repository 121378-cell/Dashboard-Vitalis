"""
ATLAS Intervention Outcome Service
====================================

Mide la efectividad de las intervenciones del sistema ATLAS VIVO.
Calcula outcome_score basado en 4 factores ponderados:

  - accepted (0-1):        0.4 peso — el usuario aceptó la acción
  - responded_time (0-1):  0.3 peso — rapidez de respuesta
  - subsequent_action (0-1): 0.2 peso — ejecutó la acción recomendada
  - adherence_impact (0-1): 0.1 peso — mejora en adherencia siguientes 48h

  outcome_score = sum(factor * peso) → clamped a [0.0, 1.0]

También aprende el mejor canal y momento del día para cada tipo de intervención.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger("app.services.intervention_outcome_service")

# Pesos para el cálculo del outcome_score (del modelo AtlasIntervention)
WEIGHTS = {
    "accepted": 0.4,
    "responded_time": 0.3,
    "subsequent_action": 0.2,
    "adherence_impact": 0.1,
}


class InterventionOutcomeService:
    """Mide efectividad de las intervenciones y aprende patrones óptimos."""

    @staticmethod
    def _get_db(db: Optional[Session] = None) -> Tuple[Session, bool]:
        """Obtiene sesión de DB, propia o compartida."""
        if db is not None:
            return db, False
        from app.db.session import SessionLocal
        return SessionLocal(), True

    # ── Cálculo de Outcome ──

    @staticmethod
    def _calculate_outcome_score(outcome: Dict[str, Any]) -> float:
        """
        Calcula outcome_score (0.0-1.0) a partir de los factores.

        Args:
            outcome: Dict con claves opcionales:
                - accepted (bool): usuario aceptó la intervención
                - responded_time_hours (float): horas hasta respuesta (menos = mejor)
                - subsequent_action (bool): ejecutó la acción recomendada
                - adherence_impact (float): 0.0-1.0 mejora en adherencia post-intervención

        Returns:
            float: puntuación 0.0-1.0
        """
        # Factor 1: Aceptación (0.4 peso)
        accepted_raw = 1.0 if outcome.get("accepted", False) else 0.0
        accepted_score = accepted_raw * WEIGHTS["accepted"]

        # Factor 2: Tiempo de respuesta (0.3 peso)
        #   <1h  = 1.0, 1-3h = 0.7, 3-6h = 0.4, 6-12h = 0.2, >12h = 0.0
        responded_hours = outcome.get("responded_time_hours")
        if responded_hours is not None:
            if responded_hours <= 1:
                time_score_raw = 1.0
            elif responded_hours <= 3:
                time_score_raw = 0.7
            elif responded_hours <= 6:
                time_score_raw = 0.4
            elif responded_hours <= 12:
                time_score_raw = 0.2
            else:
                time_score_raw = 0.0
        else:
            time_score_raw = 0.5  # Neutral si no hay datos
        time_score = time_score_raw * WEIGHTS["responded_time"]

        # Factor 3: Acción posterior (0.2 peso)
        subsequent_raw = 1.0 if outcome.get("subsequent_action", False) else 0.0
        subsequent_score = subsequent_raw * WEIGHTS["subsequent_action"]

        # Factor 4: Impacto en adherencia (0.1 peso)
        adherence_raw = outcome.get("adherence_impact", 0.5)  # Neutral por defecto
        adherence_score = min(1.0, max(0.0, adherence_raw)) * WEIGHTS["adherence_impact"]

        # Puntuación total
        total = accepted_score + time_score + subsequent_score + adherence_score
        return max(0.0, min(1.0, total))

    @staticmethod
    def _compute_responded_time_hours(
        intervention,
    ) -> Optional[float]:
        """Calcula horas entre created_at y responded_at de una intervención."""
        if intervention.created_at and intervention.responded_at:
            delta = intervention.responded_at - intervention.created_at
            return delta.total_seconds() / 3600
        return None

    @staticmethod
    def record_outcome(
        intervention_id: int,
        outcome: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Optional[float]:
        """
        Calcula y persiste el outcome_score de una intervención.

        Si no se proporciona outcome, lo deduce del estado de la intervención:
        - accepted=True si response=="accepted"
        - responded_time_hours desde created_at hasta responded_at

        Args:
            intervention_id: ID de la intervención
            outcome: Dict con factores opcionales (ver _calculate_outcome_score)
            db: Sesión SQLAlchemy (opcional)

        Returns:
            float: outcome_score calculado, o None si error
        """
        session, own_session = InterventionOutcomeService._get_db(db)
        try:
            from app.models.atlas_intervention import AtlasIntervention

            intervention = session.query(AtlasIntervention).filter(
                AtlasIntervention.id == intervention_id,
            ).first()

            if not intervention:
                logger.warning("Intervención %s no encontrada para outcome", intervention_id)
                return None

            # Si no se proporcionó outcome, deducir del estado de la intervención
            if outcome is None:
                outcome = {}

            # Auto-deducir factores disponibles
            if "accepted" not in outcome:
                outcome["accepted"] = intervention.response == "accepted"

            if "responded_time_hours" not in outcome:
                hours = InterventionOutcomeService._compute_responded_time_hours(intervention)
                if hours is not None:
                    outcome["responded_time_hours"] = hours

            if "subsequent_action" not in outcome:
                # Si se ejecutó (status=executed o executed_at not null), hubo acción
                outcome["subsequent_action"] = (
                    intervention.status == "executed"
                    or intervention.executed_at is not None
                )

            # Calcular y persistir
            score = InterventionOutcomeService._calculate_outcome_score(outcome)
            intervention.outcome_score = score

            session.commit()
            logger.info(
                "Outcome registrado: intervención %s → score %.2f",
                intervention_id, score,
            )
            return score

        except Exception as e:
            logger.error("Error registrando outcome para %s: %s", intervention_id, e)
            session.rollback()
            return None
        finally:
            if own_session:
                session.close()

    # ── Estadísticas ──

    @staticmethod
    def get_outcome_stats(
        user_id: str,
        intervention_type: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Estadísticas de efectividad de intervenciones para un usuario.

        Args:
            user_id: ID del usuario
            intervention_type: Filtrar por tipo (opcional)
            db: Sesión SQLAlchemy (opcional)

        Returns:
            Dict con: total, by_type[], avg_score, acceptance_rate, etc.
        """
        session, own_session = InterventionOutcomeService._get_db(db)
        try:
            from app.models.atlas_intervention import AtlasIntervention

            query = session.query(AtlasIntervention).filter(
                AtlasIntervention.user_id == user_id,
            )

            if intervention_type:
                query = query.filter(
                    AtlasIntervention.intervention_type == intervention_type,
                )

            interventions = query.all()

            if not interventions:
                return {
                    "total": 0,
                    "by_type": [],
                    "avg_score": None,
                    "acceptance_rate": None,
                    "outcome_distribution": {},
                }

            # Agrupar por tipo
            type_groups: Dict[str, list] = {}
            for inv in interventions:
                itype = inv.intervention_type
                if itype not in type_groups:
                    type_groups[itype] = []
                type_groups[itype].append(inv)

            by_type = []
            for itype, items in type_groups.items():
                with_score = [i for i in items if i.outcome_score is not None]
                accepted = [i for i in items if i.response == "accepted"]
                by_type.append({
                    "type": itype,
                    "count": len(items),
                    "avg_score": round(
                        sum(i.outcome_score for i in with_score) / len(with_score), 3
                    ) if with_score else None,
                    "acceptance_rate": round(
                        len(accepted) / len(items), 3
                    ) if items else None,
                })

            # Métricas globales
            with_score = [i for i in interventions if i.outcome_score is not None]
            accepted_total = [i for i in interventions if i.response == "accepted"]

            # Distribución de scores
            score_buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
            for inv in with_score:
                s = inv.outcome_score
                if s < 0.2:
                    score_buckets["0.0-0.2"] += 1
                elif s < 0.4:
                    score_buckets["0.2-0.4"] += 1
                elif s < 0.6:
                    score_buckets["0.4-0.6"] += 1
                elif s < 0.8:
                    score_buckets["0.6-0.8"] += 1
                else:
                    score_buckets["0.8-1.0"] += 1

            return {
                "total": len(interventions),
                "by_type": by_type,
                "avg_score": round(
                    sum(i.outcome_score for i in with_score) / len(with_score), 3
                ) if with_score else None,
                "acceptance_rate": round(
                    len(accepted_total) / len(interventions), 3
                ) if interventions else None,
                "outcome_distribution": score_buckets,
            }

        except Exception as e:
            logger.error("Error obteniendo stats para user %s: %s", user_id, e)
            return {
                "total": 0, "by_type": [], "avg_score": None,
                "acceptance_rate": None, "outcome_distribution": {},
            }
        finally:
            if own_session:
                session.close()

    @staticmethod
    def record_batch_outcomes(
        user_id: str,
        days: int = 7,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Recalcula outcomes para intervenciones recientes sin score.

        Útil como job de mantenimiento o para backfill.

        Args:
            user_id: ID del usuario
            days: Ventana hacia atrás en días

        Returns:
            Dict con: processed, updated, errors
        """
        session, own_session = InterventionOutcomeService._get_db(db)
        try:
            from app.models.atlas_intervention import AtlasIntervention

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            pending = session.query(AtlasIntervention).filter(
                AtlasIntervention.user_id == user_id,
                AtlasIntervention.outcome_score.is_(None),
                AtlasIntervention.status.in_(["accepted", "rejected", "executed", "expired"]),
                AtlasIntervention.created_at >= cutoff,
            ).all()

            updated = 0
            errors = 0
            for inv in pending:
                try:
                    score = InterventionOutcomeService.record_outcome(
                        intervention_id=inv.id,
                        outcome=None,  # Auto-deducir
                        db=session,
                    )
                    if score is not None:
                        updated += 1
                except Exception:
                    errors += 1

            return {
                "processed": len(pending),
                "updated": updated,
                "errors": errors,
            }

        except Exception as e:
            logger.error("Error en batch outcome para user %s: %s", user_id, e)
            return {"processed": 0, "updated": 0, "errors": 1}
        finally:
            if own_session:
                session.close()

    # ── Aprendizaje de Canal Óptimo ──

    @staticmethod
    def get_best_channel(
        user_id: str,
        intervention_type: str,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Determina el mejor canal para un tipo de intervención basado en
        outcomes históricos.

        Evalúa qué canal (app/telegram/system) ha tenido mejores scores
        para este tipo de intervención con este usuario.

        Args:
            user_id: ID del usuario
            intervention_type: Tipo de intervención

        Returns:
            Dict con: best_channel, scores_by_channel, confidence, sample_size
        """
        session, own_session = InterventionOutcomeService._get_db(db)
        try:
            from app.models.atlas_intervention import AtlasIntervention

            interventions = session.query(AtlasIntervention).filter(
                AtlasIntervention.user_id == user_id,
                AtlasIntervention.intervention_type == intervention_type,
                AtlasIntervention.outcome_score.isnot(None),
            ).all()

            if not interventions:
                return {
                    "best_channel": "app",  # Default
                    "scores_by_channel": {},
                    "confidence": 0.0,
                    "sample_size": 0,
                }

            # Los canales se infieren del autonomy_level y extra_data
            #   AUTONOMOUS (1) → ["app"]
            #   PROPOSAL (2)   → ["app", "system"]
            #   VALIDATION (3) → ["app", "telegram", "system"]
            from app.core.autonomy_policy import AutonomyLevel

            channel_scores: Dict[str, list] = {"app": [], "system": [], "telegram": []}
            for inv in interventions:
                try:
                    level = AutonomyLevel[inv.autonomy_level.upper()] if isinstance(inv.autonomy_level, str) else AutonomyLevel(inv.autonomy_level)
                except (KeyError, ValueError):
                    level = AutonomyLevel.PROPOSAL

                if level == AutonomyLevel.AUTONOMOUS:
                    channels = ["app"]
                elif level == AutonomyLevel.PROPOSAL:
                    channels = ["app", "system"]
                else:
                    channels = ["app", "telegram", "system"]

                if inv.outcome_score is not None:
                    for ch in channels:
                        channel_scores[ch].append(inv.outcome_score)

            scores_by_channel = {}
            for ch, scores in channel_scores.items():
                if scores:
                    scores_by_channel[ch] = {
                        "avg_score": round(sum(scores) / len(scores), 3),
                        "count": len(scores),
                    }

            # Mejor canal = mayor avg_score
            best = max(
                scores_by_channel.items(),
                key=lambda x: x[1]["avg_score"],
                default=("app", {"avg_score": 0.0}),
            )

            total_samples = sum(v["count"] for v in scores_by_channel.values())
            confidence = min(1.0, total_samples / 10)  # Confianza escala con muestras

            return {
                "best_channel": best[0],
                "scores_by_channel": scores_by_channel,
                "confidence": round(confidence, 2),
                "sample_size": total_samples,
            }

        except Exception as e:
            logger.error("Error obteniendo best channel: %s", e)
            return {
                "best_channel": "app",
                "scores_by_channel": {},
                "confidence": 0.0,
                "sample_size": 0,
            }
        finally:
            if own_session:
                session.close()

    # ── Aprendizaje de Momento Óptimo ──

    @staticmethod
    def get_best_timing(
        user_id: str,
        intervention_type: str,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Determina el mejor momento del día para un tipo de intervención.

        Agrupa intervenciones por franja horaria (mañana/mediodía/tarde/noche)
        y calcula el outcome_score promedio de cada franja.

        Args:
            user_id: ID del usuario
            intervention_type: Tipo de intervención

        Returns:
            Dict con: best_timing, scores_by_timing, confidence, sample_size
        """
        session, own_session = InterventionOutcomeService._get_db(db)
        try:
            from app.models.atlas_intervention import AtlasIntervention

            interventions = session.query(AtlasIntervention).filter(
                AtlasIntervention.user_id == user_id,
                AtlasIntervention.intervention_type == intervention_type,
                AtlasIntervention.outcome_score.isnot(None),
            ).all()

            if not interventions:
                return {
                    "best_timing": "morning",  # Default
                    "scores_by_timing": {},
                    "confidence": 0.0,
                    "sample_size": 0,
                }

            # Franjas horarias (basado en created_at)
            timing_scores: Dict[str, list] = {
                "morning": [],    # 06-12
                "afternoon": [],  # 12-18
                "evening": [],    # 18-22
                "night": [],      # 22-06
            }

            for inv in interventions:
                if inv.created_at is None:
                    continue
                hour = inv.created_at.hour
                if 6 <= hour < 12:
                    timing_scores["morning"].append(inv.outcome_score)
                elif 12 <= hour < 18:
                    timing_scores["afternoon"].append(inv.outcome_score)
                elif 18 <= hour < 22:
                    timing_scores["evening"].append(inv.outcome_score)
                else:
                    timing_scores["night"].append(inv.outcome_score)

            scores_by_timing = {}
            for timing, scores in timing_scores.items():
                if scores:
                    scores_by_timing[timing] = {
                        "avg_score": round(sum(scores) / len(scores), 3),
                        "count": len(scores),
                    }

            best = max(
                scores_by_timing.items(),
                key=lambda x: x[1]["avg_score"],
                default=("morning", {"avg_score": 0.0}),
            )

            total_samples = sum(v["count"] for v in scores_by_timing.values())
            confidence = min(1.0, total_samples / 10)

            return {
                "best_timing": best[0],
                "scores_by_timing": scores_by_timing,
                "confidence": round(confidence, 2),
                "sample_size": total_samples,
            }

        except Exception as e:
            logger.error("Error obteniendo best timing: %s", e)
            return {
                "best_timing": "morning",
                "scores_by_timing": {},
                "confidence": 0.0,
                "sample_size": 0,
            }
        finally:
            if own_session:
                session.close()


# Singleton para uso directo
outcome_service = InterventionOutcomeService()
