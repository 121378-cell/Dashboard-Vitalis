"""
ATLAS VIVO — Modelo de Estado del Atleta.

Snapshot narrativo del estado del atleta en un momento dado.
Compuesto por 6 dimensiones calculadas a partir de datos crudos
(readiness, biométricos, entrenos, etc.) y una narrativa sintetizada.

Este modelo representa la "capa de interpretación" de ATLAS:
no son datos planos, sino una lectura semántica del estado del atleta.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class AthleteState(Base):
    """
    Snapshot del estado narrativo del atleta.

    Cada fila representa una foto del estado en una fecha concreta.
    Las dimensiones (energy, adherence, momentum, risk, motivation)
    son valores calculados por AthleteStateService.
    """

    __tablename__ = "athlete_state_snapshots"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)

    # ─── Dimensiones del estado ──────────────────────────────────────

    # Energía: Capacidad física percibida
    # depleted|fragile|stable|rising|peak
    energy_state = Column(String, default="stable", index=True)

    # Adherencia: Seguimiento del plan
    # disconnected|inconsistent|compliant|consistent|locked_in
    adherence_state = Column(String, default="compliant", index=True)

    # Momentum: Trayectoria de progreso
    # stalled|regressing|neutral|building|compounding
    momentum_state = Column(String, default="neutral", index=True)

    # Riesgo: Probabilidad de lesión/sobreentrenamiento
    # low|moderate|high|acute
    risk_state = Column(String, default="low", index=True)

    # Motivación: Engagement y actitud
    # motivated|flat|avoidant|frustrated|resilient
    motivation_state = Column(String, default="motivated")

    # Fase de entrenamiento actual
    # build|consolidate|deload|recover|re-entry
    training_phase = Column(String, default="build")

    # ─── Métricas numéricas ──────────────────────────────────────────

    # Confianza en el plan: qué tan bien está funcionando (0.0-1.0)
    trust_in_plan = Column(Float, default=0.5)

    # Confianza del atleta en sí mismo (0.0-1.0)
    confidence = Column(Float, default=0.5)

    # Readiness real del día (si está disponible)
    readiness_score = Column(Float, nullable=True)

    # ─── Narrativa ───────────────────────────────────────────────────

    # Resumen en lenguaje natural del estado
    narrative_summary = Column(Text, nullable=True)

    # Estilo de coaching recomendado para hoy
    # firm_supportive|clinical_alert|celebratory_sharp|strategic_coach|light_humor
    recommended_coaching_style = Column(String, default="firm_supportive")

    # ─── Metadatos ──────────────────────────────────────────────────

    # Qué triggers se dispararon para llegar a este estado
    triggers_fired = Column(JSON, default=list)

    # Valores raw de cada dimensión antes de clasificación
    dimensions_raw = Column(JSON, default=dict)

    # Versión del algoritmo de cálculo
    algorithm_version = Column(String, default="1.0.0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<AthleteState {self.snapshot_date} "
            f"energy={self.energy_state} risk={self.risk_state} "
            f"momentum={self.momentum_state}>"
        )
