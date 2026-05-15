"""
ATLAS VIVO — Servicio de Estado del Atleta.

Sintetiza el estado narrativo del atleta a partir de múltiples fuentes:
readiness, biométricos, historial de entrenos, alertas de lesión, etc.

Es la "capa de interpretación" de ATLAS: convierte datos crudos
en un diagnóstico semántico del momento del atleta.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import desc

from app.db.session import SessionLocal
from app.models.athlete_state import AthleteState
from app.models.biometrics import Biometrics
from app.models.session import TrainingSession
from app.models.workout import Workout
from app.services.readiness_service import ReadinessService
from app.services.injury_prevention_service import InjuryPreventionService

logger = logging.getLogger(__name__)


# ─── Constantes ─────────────────────────────────────────────────────────────

ENERGY_LEVELS = ["depleted", "fragile", "stable", "rising", "peak"]
ADHERENCE_LEVELS = ["disconnected", "inconsistent", "compliant", "consistent", "locked_in"]
MOMENTUM_LEVELS = ["stalled", "regressing", "neutral", "building", "compounding"]
RISK_LEVELS = ["low", "moderate", "high", "acute"]
MOTIVATION_LEVELS = ["frustrated", "avoidant", "flat", "motivated", "resilient"]

# Readiness thresholds for energy classification
ENERGY_READINESS_THRESHOLDS = {
    "depleted": (0, 35),
    "fragile": (35, 50),
    "stable": (50, 70),
    "rising": (70, 85),
    "peak": (85, 101),
}

# Days of history to consider for each dimension
LOOKBACK_ADHERENCE_DAYS = 14
LOOKBACK_MOMENTUM_DAYS = 21
LOOKBACK_MOTIVATION_DAYS = 14

# Adherence thresholds (fraction of planned sessions completed)
ADHERENCE_THRESHOLDS = {
    "disconnected": (0.0, 0.3),
    "inconsistent": (0.3, 0.6),
    "compliant": (0.6, 0.8),
    "consistent": (0.8, 0.95),
    "locked_in": (0.95, 1.01),
}

# ─── Core API ───────────────────────────────────────────────────────────────


class AthleteStateService:
    """
    Síntesis del estado narrativo del atleta.

    Todos los métodos son estáticos. El flujo principal es:

    1. compute_state(user_id) → calcula y persiste un nuevo snapshot
    2. get_state(user_id) → devuelve el último snapshot disponible
    3. Los métodos _determine_* se encargan de cada dimensión individual
    """

    @staticmethod
    def compute_state(user_id: str) -> Optional[AthleteState]:
        """
        Calcula el estado actual del atleta desde todas las fuentes disponibles.

        Este método debe ejecutarse después del daily loop, cuando los datos
        de readiness, biométricos y workouts están actualizados.

        Args:
            user_id: Identificador del atleta

        Returns:
            AthleState persistido, o None si no hay datos suficientes
        """
        try:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # 1. Recopilar datos raw de cada fuente
            with SessionLocal() as db:
                readiness_dict = ReadinessService.calculate(
                    db, user_id,
                    date_str=today.strftime("%Y-%m-%d"),
                )
                injury_status = InjuryPreventionService.get_current_status(db, user_id)
            recent_workouts = AthleteStateService._get_recent_workouts(user_id, days=LOOKBACK_ADHERENCE_DAYS)
            planned_sessions = AthleteStateService._get_planned_sessions(user_id, today)
            recent_biometrics = AthleteStateService._get_recent_biometrics(user_id, days=14)
            readiness = readiness_dict or {}

            # 2. Calcular cada dimensión
            energy = AthleteStateService._determine_energy(
                readiness_score=readiness.get("score"),
                biometrics=recent_biometrics,
            )
            adherence = AthleteStateService._determine_adherence(
                completed_workouts=recent_workouts,
                planned_sessions=planned_sessions,
            )
            momentum = AthleteStateService._determine_momentum(
                workouts=recent_workouts,
                readiness_score=readiness.get("score"),
            )
            risk = AthleteStateService._determine_risk(
                readiness_score=readiness.get("score"),
                injury_status=injury_status,
            )
            motivation = AthleteStateService._determine_motivation(
                recent_workouts=recent_workouts,
                planned_sessions=planned_sessions,
                adherence_level=adherence,
            )

            # 3. Métricas derivadas
            readiness_val = float(readiness.get("score", 0) or 0)
            trust = AthleteStateService._compute_trust_in_plan(adherence_level=adherence)
            confidence_val = AthleteStateService._compute_confidence(
                momentum_level=momentum,
                risk_level=risk,
            )

            # 4. Narrativa y estilo
            state_dims = {
                "energy": energy,
                "adherence": adherence,
                "momentum": momentum,
                "risk": risk,
                "motivation": motivation,
            }
            narrative = AthleteStateService._generate_narrative(state_dims, readiness_val)
            coaching_style = AthleteStateService._recommend_coaching_style(state_dims)

            # 5. Dimensiones raw para trazabilidad
            injury_alert = None
            if injury_status:
                injury_alert = getattr(injury_status, "alert_level", None)
                if injury_alert is not None:
                    injury_alert = str(injury_alert)

            dimensions_raw = {
                "readiness_score": readiness_val,
                "injury_alert_level": injury_alert,
                "recent_workout_count": len(recent_workouts),
                "planned_session_count": len(planned_sessions),
            }

            # 6. Persistir snapshot
            state = AthleteState(
                user_id=user_id,
                snapshot_date=today,
                energy_state=energy,
                adherence_state=adherence,
                momentum_state=momentum,
                risk_state=risk,
                motivation_state=motivation,
                readiness_score=readiness_val if readiness_val > 0 else None,
                trust_in_plan=trust,
                confidence=confidence_val,
                narrative_summary=narrative,
                recommended_coaching_style=coaching_style,
                dimensions_raw=dimensions_raw,
                algorithm_version="1.0.0",
            )

            with SessionLocal() as state_db:
                state_db.add(state)
                state_db.commit()
                state_db.refresh(state)

            logger.info(
                "Athlete state computed for %s: energy=%s adherence=%s "
                "momentum=%s risk=%s motivation=%s",
                user_id, energy, adherence, momentum, risk, motivation,
            )
            return state

        except Exception as e:
            logger.error("Failed to compute athlete state for %s: %s", user_id, e)
            return None

    @staticmethod
    def get_state(user_id: str) -> Optional[AthleteState]:
        """
        Obtiene el último snapshot de estado disponible.

        Args:
            user_id: Identificador del atleta

        Returns:
            Último AthleteState o None si no hay ninguno
        """
        try:
            with SessionLocal() as db:
                return (
                    db.query(AthleteState)
                    .filter(AthleteState.user_id == user_id)
                    .order_by(desc(AthleteState.snapshot_date))
                    .first()
                )
        except Exception as e:
            logger.error("Failed to get athlete state for %s: %s", user_id, e)
            return None

    @staticmethod
    def get_state_history(
        user_id: str,
        days: int = 30,
    ) -> list[AthleteState]:
        """
        Obtiene historial de snapshots de estado.

        Args:
            user_id: Identificador del atleta
            days: Días hacia atrás

        Returns:
            Lista de snapshots ordenados por fecha descendente
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            with SessionLocal() as db:
                return (
                    db.query(AthleteState)
                    .filter(
                        AthleteState.user_id == user_id,
                        AthleteState.snapshot_date >= cutoff,
                    )
                    .order_by(desc(AthleteState.snapshot_date))
                    .all()
                )
        except Exception as e:
            logger.error("Failed to get state history for %s: %s", user_id, e)
            return []

    # ─── Helpers de datos ─────────────────────────────────────────────

    @staticmethod
    def _get_recent_workouts(user_id: str, days: int) -> list[Workout]:
        """Obtiene workouts completados en los últimos N días."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            with SessionLocal() as db:
                return (
                    db.query(Workout)
                    .filter(
                        Workout.user_id == user_id,
                        Workout.date >= cutoff,
                    )
                    .order_by(Workout.date.desc())
                    .all()
                )
        except Exception as e:
            logger.warning("Failed to get recent workouts: %s", e)
            return []

    @staticmethod
    def _get_planned_sessions(user_id: str, today: datetime) -> list[TrainingSession]:
        """Obtiene sesiones planificadas para hoy y los próximos días."""
        try:
            with SessionLocal() as db:
                return (
                    db.query(TrainingSession)
                    .filter(
                        TrainingSession.user_id == user_id,
                        TrainingSession.date >= today.strftime("%Y-%m-%d"),
                    )
                    .all()
                )
        except Exception as e:
            logger.warning("Failed to get planned sessions: %s", e)
            return []

    @staticmethod
    def _get_recent_biometrics(user_id: str, days: int) -> list[Biometrics]:
        """Obtiene registros biométricos recientes."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            with SessionLocal() as db:
                return (
                    db.query(Biometrics)
                    .filter(
                        Biometrics.user_id == user_id,
                        Biometrics.date >= cutoff.strftime("%Y-%m-%d"),
                    )
                    .order_by(Biometrics.date.desc())
                    .all()
                )
        except Exception as e:
            logger.warning("Failed to get recent biometrics: %s", e)
            return []

    # ─── Clasificadores de dimensión ──────────────────────────────────

    @staticmethod
    def _determine_energy(
        readiness_score: Optional[float],
        biometrics: list[Biometrics],
    ) -> str:
        """
        Clasifica el nivel de energía basado en readiness y biométricos.

        depleted  → readiness < 35 o señal fuerte de fatiga
        fragile   → readiness 35-50
        stable    → readiness 50-70
        rising    → readiness 70-85 + tendencia positiva
        peak      → readiness > 85
        """
        if readiness_score is not None:
            for level, (low, high) in ENERGY_READINESS_THRESHOLDS.items():
                if low <= readiness_score < high:
                    # Si está en "stable" pero HRV bajo crónico, bajar a "fragile"
                    if level == "stable" and biometrics:
                        last_hrv = AthleteStateService._get_latest_hrv(biometrics)
                        if last_hrv is not None and last_hrv < 30:
                            return "fragile"
                    return level

        # Sin readiness: inferir de biométricos
        if biometrics:
            avg_hrv = AthleteStateService._get_avg_hrv(biometrics)
            if avg_hrv and avg_hrv < 25:
                return "depleted"
            return "stable"

        return "stable"

    @staticmethod
    def _determine_adherence(
        completed_workouts: list[Workout],
        planned_sessions: list[TrainingSession],
    ) -> str:
        """
        Clasifica la adherencia basada en workouts completados vs planificados.

        disconnected  → < 30% de adherencia
        inconsistent  → 30-60%
        compliant     → 60-80%
        consistent    → 80-95%
        locked_in     → > 95%
        """
        if not planned_sessions:
            # Sin plan: inferir de frecuencia de entrenamiento
            if not completed_workouts:
                return "disconnected"
            workout_count = len([w for w in completed_workouts
                                 if w.date >= datetime.now(timezone.utc) - timedelta(days=7)])
            if workout_count >= 5:
                return "consistent"
            if workout_count >= 3:
                return "compliant"
            if workout_count >= 1:
                return "inconsistent"
            return "disconnected"

        completed_count = sum(
            1 for s in planned_sessions if s.status == "completed"
        )

        ratio = completed_count / len(planned_sessions)
        for level, (low, high) in ADHERENCE_THRESHOLDS.items():
            if low <= ratio < high:
                return level

        return "compliant"

    @staticmethod
    def _determine_momentum(
        workouts: list[Workout],
        readiness_score: Optional[float],
    ) -> str:
        """
        Clasifica el momentum basado en tendencia de entrenos y readiness.

        stalled      → tendencia plana/decreciente y readiness bajo
        regressing   → tendencia claramente negativa
        neutral      → sin tendencia clara
        building     → tendencia positiva sostenida
        compounding  → tendencia positiva + readiness alto + sin alertas
        """
        if not workouts:
            return "neutral"

        # Calcular tendencia semanal (workouts por semana)            now = datetime.now(timezone.utc)
        week1_cutoff = now - timedelta(days=7)
        week2_cutoff = now - timedelta(days=14)

        week1 = len([w for w in workouts if w.date >= week1_cutoff])
        week2 = len([w for w in workouts if week2_cutoff <= w.date < week1_cutoff])

        trend = week1 - week2

        if trend > 2 and readiness_score and readiness_score > 75:
            return "compounding"
        if trend > 1:
            return "building"
        if trend > 0:
            return "neutral"
        if trend == 0:
            if readiness_score and readiness_score < 45:
                return "stalled"
            return "neutral"
        # trend < 0
        if trend < -2:
            return "regressing"
        return "stalled"

    @staticmethod
    def _determine_risk(
        readiness_score: Optional[float],
        injury_status: Any,
    ) -> str:
        """
        Clasifica el nivel de riesgo basado en readiness y alertas de lesión.

        low       → sin señales de riesgo
        moderate  → readiness bajo o alerta amarilla
        high      → readiness muy bajo o alerta naranja
        acute     → alerta roja
        """
        # Priorizar alertas de injury_prevention
        if injury_status:
            alert_level = getattr(injury_status, "alert_level", None)
            if alert_level is not None:
                alert_value = alert_level.value if hasattr(alert_level, "value") else str(alert_level)
                alert_map = {
                    "RED": "acute",
                    "ORANGE": "high",
                    "YELLOW": "moderate",
                    "GREEN": "low",
                }
                return alert_map.get(alert_value, "low")

        # Fallback a readiness
        if readiness_score is not None:
            if readiness_score < 25:
                return "acute"
            if readiness_score < 40:
                return "high"
            if readiness_score < 55:
                return "moderate"

        return "low"

    @staticmethod
    def _determine_motivation(
        recent_workouts: list[Workout],
        planned_sessions: list[TrainingSession],
        adherence_level: str,
    ) -> str:
        """
        Clasifica la motivación basada en engagement y adherencia.

        frustrated  → adherencia alta pero riesgo alto (quiere pero no puede)
        avoidant    → adherencia baja + sesiones planificadas (evita)
        flat        → adherencia baja sin plan (desconectado)
        motivated   → adherencia media-alta (normal)
        resilient   → adherencia alta + superó obstáculo reciente
        """
        if adherence_level in ("locked_in", "consistent"):
            # Podría ser "frustrated" si hay muchas sesiones no completadas por fatiga
            missed = len([s for s in planned_sessions if s.status == "cancelled"])
            if missed > 3:
                return "frustrated"
            return "resilient" if missed > 0 else "motivated"

        if adherence_level == "compliant":
            return "motivated"

        if adherence_level == "inconsistent":
            planned_count = len(planned_sessions)
            if planned_count > 3:
                return "avoidant"
            return "flat"

        if adherence_level == "disconnected":
            return "avoidant"

        return "motivated"

    # ─── Métricas derivadas ───────────────────────────────────────────

    @staticmethod
    def _compute_trust_in_plan(adherence_level: str) -> float:
        """
        Calcula confianza en el plan basada en adherencia.
        """
        trust_map = {
            "locked_in": 0.95,
            "consistent": 0.85,
            "compliant": 0.65,
            "inconsistent": 0.40,
            "disconnected": 0.20,
        }
        return trust_map.get(adherence_level, 0.5)

    @staticmethod
    def _compute_confidence(momentum_level: str, risk_level: str) -> float:
        """
        Calcula confianza del atleta basada en momentum y riesgo.
        """
        base = {
            "compounding": 0.90,
            "building": 0.75,
            "neutral": 0.55,
            "regressing": 0.35,
            "stalled": 0.30,
        }.get(momentum_level, 0.5)

        # Penalizar por riesgo
        risk_penalty = {
            "low": 0.0,
            "moderate": -0.1,
            "high": -0.25,
            "acute": -0.4,
        }.get(risk_level, 0.0)

        return max(0.0, min(1.0, base + risk_penalty))

    # ─── Narrativa y estilo ───────────────────────────────────────────

    @staticmethod
    def _generate_narrative(
        state: dict[str, str],
        readiness_score: float,
    ) -> str:
        """
        Genera un resumen narrativo del estado del atleta.

        El formato es una frase corta que captura lo esencial del momento.
        Se usa para el panel "ATLAS Live" y para iniciar conversaciones.
        """
        energy = state.get("energy", "stable")
        adherence = state.get("adherence", "compliant")
        momentum = state.get("momentum", "neutral")
        risk = state.get("risk", "low")
        motivation = state.get("motivation", "motivated")

        # Narrativas por combinación de dimensiones
        if risk in ("high", "acute"):
            return "ATLAS recomienda reducir carga. Señales de fatiga acumulada detectadas."

        if energy == "peak" and momentum == "compounding":
            return "Momento óptimo. Capacidad alta y progresión sostenida. Ventana para calidad."

        if adherence == "disconnected":
            return "Se detecta desconexión del plan. Una revisión suave podría ayudar a reenganchar."

        if energy == "depleted":
            return "Nivel de energia bajo. Considerar dia de recuperacion activa."

        if motivation == "frustrated":
            return "Quieres entrenar pero el cuerpo no responde. Es normal en ciclos de carga."

        if momentum == "building":
            return "Progresion positiva. La consistencia esta dando resultados."

        if adherence == "locked_in":
            return "Adherencia optima. La rutina esta consolidada."

        # Narrativa por defecto
        if readiness_score > 75:
            return "Buena disposicion para entrenar. Datos dentro de parametros normales."
        if readiness_score > 50:
            return "Estado equilibrado. Seguir con el plan segun lo previsto."

        return "Dia para entrenamiento consciente. Escuchar al cuerpo y ajustar si es necesario."

    @staticmethod
    def _recommend_coaching_style(state: dict[str, str]) -> str:
        """
        Recomienda el estilo de coaching más efectivo para el estado actual.

        Mapeo directo:
          risk=high/acute           → clinical_alert
          energy=peak+momentum=comp → celebratory_sharp
          adherence=disconnected    → light_humor
          momentum=building         → strategic_coach
          default                   → firm_supportive
        """
        risk = state.get("risk", "low")
        energy = state.get("energy", "stable")
        momentum = state.get("momentum", "neutral")
        adherence = state.get("adherence", "compliant")

        if risk in ("high", "acute"):
            return "clinical_alert"
        if energy == "peak" and momentum == "compounding":
            return "celebratory_sharp"
        if adherence == "disconnected":
            return "light_humor"
        if momentum == "building":
            return "strategic_coach"

        return "firm_supportive"

    # ─── Utilidades biométricas ───────────────────────────────────────

    @staticmethod
    def _get_latest_hrv(biometrics: list[Biometrics]) -> Optional[float]:
        """Obtiene el último HRV disponible."""
        try:
            for b in biometrics:
                if b.data:
                    import json
                    data = json.loads(b.data) if isinstance(b.data, str) else b.data
                    hrv = data.get("hrv") or data.get("hrv_score")
                    if hrv is not None:
                        return float(hrv)
        except Exception:
            pass
        return None

    @staticmethod
    def _get_avg_hrv(biometrics: list[Biometrics]) -> Optional[float]:
        """Calcula el HRV promedio de los registros disponibles."""
        hrv_values = []
        try:
            for b in biometrics:
                if b.data:
                    import json
                    data = json.loads(b.data) if isinstance(b.data, str) else b.data
                    hrv = data.get("hrv") or data.get("hrv_score")
                    if hrv is not None:
                        hrv_values.append(float(hrv))
        except Exception:
            pass
        if hrv_values:
            return sum(hrv_values) / len(hrv_values)
        return None
