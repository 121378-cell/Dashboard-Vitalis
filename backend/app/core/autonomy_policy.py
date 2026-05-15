"""
ATLAS VIVO — Política de Autonomía.

Define qué puede hacer ATLAS sin consultar, qué necesita validación,
y cómo se escalan/desactivan las intervenciones según contexto.
"""

from enum import IntEnum, Enum
from datetime import timedelta


class AutonomyLevel(IntEnum):
    AUTONOMOUS = 1    # Sin consulta — ejecuta directamente
    PROPOSAL = 2      # Propuesta con aceptación rápida (toast/banner)
    VALIDATION = 3    # Requiere validación explícita del usuario
    FORBIDDEN = 4     # Prohibido — no se puede hacer


class InterventionType(str, Enum):
    INTENSITY_ADJUST = "intensity_adjustment"
    SESSION_REROUTE = "session_reroute"
    RECOVERY_ACTIVATE = "recovery_activation"
    ADHERENCE_NUDGE = "adherence_nudge"
    CHECK_IN_REQUEST = "check_in_request"
    PLAN_PROPOSAL = "plan_proposal"
    RISK_ALERT = "risk_alert"
    OPPORTUNITY = "opportunity_alert"
    WEEKLY_REVIEW = "weekly_review"


# ─── Matriz de Autonomía Base ───────────────────────────────────────────────
# Cada tipo de intervención tiene un nivel de autonomía por defecto.
# La EscalationPolicy puede anular estos valores según contexto.

AUTONOMY_MATRIX: dict[InterventionType, AutonomyLevel] = {
    InterventionType.INTENSITY_ADJUST: AutonomyLevel.AUTONOMOUS,   # Bajo riesgo, reversible
    InterventionType.SESSION_REROUTE: AutonomyLevel.PROPOSAL,      # Medio impacto
    InterventionType.RECOVERY_ACTIVATE: AutonomyLevel.AUTONOMOUS,  # Protege salud
    InterventionType.ADHERENCE_NUDGE: AutonomyLevel.AUTONOMOUS,    # Bajo riesgo
    InterventionType.CHECK_IN_REQUEST: AutonomyLevel.AUTONOMOUS,   # Informativo
    InterventionType.PLAN_PROPOSAL: AutonomyLevel.VALIDATION,      # Estratégico
    InterventionType.RISK_ALERT: AutonomyLevel.AUTONOMOUS,         # Urgente
    InterventionType.OPPORTUNITY: AutonomyLevel.PROPOSAL,          # Oportunidad
    InterventionType.WEEKLY_REVIEW: AutonomyLevel.PROPOSAL,        # Informativo + táctico
}


def get_autonomy_level(intervention_type: InterventionType) -> AutonomyLevel:
    """Devuelve el nivel de autonomía para un tipo de intervención."""
    return AUTONOMY_MATRIX.get(intervention_type, AutonomyLevel.VALIDATION)


# ─── Política de Cooldowns ──────────────────────────────────────────────────
# Tiempo mínimo entre intervenciones del mismo tipo para evitar saturación.

COOLDOWNS: dict[InterventionType, timedelta] = {
    InterventionType.INTENSITY_ADJUST: timedelta(hours=12),
    InterventionType.ADHERENCE_NUDGE: timedelta(hours=24),
    InterventionType.RISK_ALERT: timedelta(hours=6),
    InterventionType.CHECK_IN_REQUEST: timedelta(hours=8),
    InterventionType.RECOVERY_ACTIVATE: timedelta(hours=24),
    InterventionType.OPPORTUNITY: timedelta(hours=6),
    InterventionType.WEEKLY_REVIEW: timedelta(hours=0),  # Sin cooldown
    InterventionType.PLAN_PROPOSAL: timedelta(hours=48),
    InterventionType.SESSION_REROUTE: timedelta(hours=12),
}

# Límites diarios totales por categoría de riesgo
MAX_DAILY_INTERVENTIONS: dict[str, int] = {
    "low_risk": 3,
    "medium_risk": 2,
    "high_risk": 5,  # Alertas de salud no se limitan igual
}

# Umbral de saturación: si se superan N intervenciones en 24h, silenciar
SATURATION_THRESHOLD: int = 8
SATURATION_COOLDOWN_HOURS: int = 12

# Tiempo mínimo entre intervenciones del mismo cooldown_key
MIN_INTERVAL_BY_KEY: timedelta = timedelta(hours=4)


def get_cooldown(intervention_type: InterventionType) -> timedelta:
    """Devuelve el cooldown para un tipo de intervención."""
    return COOLDOWNS.get(intervention_type, timedelta(hours=12))


# ─── Política de Escalación ─────────────────────────────────────────────────
# Define cómo se comporta el sistema ante falta de respuesta o gravedad.

class EscalationPolicy:

    # Si una propuesta no recibe respuesta en N intentos consecutivos,
    # se escala a AUTONOMOUS (actuar sin esperar)
    AUTO_ESCALATE_AFTER_MISSED: int = 2

    # Si el usuario rechaza el mismo tipo de intervención N veces seguidas,
    # se desactiva (FORBIDDEN) para no molestar
    AUTO_DISABLE_AFTER_REJECTIONS: int = 3

    # Umbrales que anulan la matriz base según estado del atleta.
    # Cuando se cumple la condición, se fuerza este nivel de autonomía.
    ESCALATION_THRESHOLDS: dict[str, dict[str, AutonomyLevel]] = {
        "risk_state": {
            "high": AutonomyLevel.AUTONOMOUS,
            "acute": AutonomyLevel.AUTONOMOUS,
        },
        "adherence_state": {
            "disconnected": AutonomyLevel.VALIDATION,
        },
        "energy_state": {
            "depleted": AutonomyLevel.PROPOSAL,
        },
    }


def resolve_autonomy(
    intervention_type: InterventionType,
    athlete_state: dict | None = None,
) -> AutonomyLevel:
    """
    Resuelve el nivel de autonomía efectivo:
    1. Parte de la matriz base
    2. Aplica escalación por estado del atleta (si aplica)
    """
    base_level = get_autonomy_level(intervention_type)

    if not athlete_state:
        return base_level

    # Verificar thresholds de escalación
    for dimension, thresholds in EscalationPolicy.ESCALATION_THRESHOLDS.items():
        current_value = athlete_state.get(dimension)
        if current_value and current_value in thresholds:
            escalated = thresholds[current_value]
            # Escalar solo si es más permisivo que el nivel base
            if int(escalated) < int(base_level):
                return escalated

    return base_level
