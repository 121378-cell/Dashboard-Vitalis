"""
ATLAS VIVO — Modelo de Eventos Internos.

Cada evento representa algo que ocurrió en el sistema:
sincronización completada, workout registrado, alerta disparada, etc.

Estos eventos alimentan el intervention engine para que ATLAS
pueda reaccionar proactivamente.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.db.session import Base


class AtlasEvent(Base):
    """
    Evento interno del sistema ATLAS.

    Tipos de evento (event_type):
    - biometrics_synced:      Sincronización Garmin completada
    - workout_logged:         Nuevo workout registrado
    - pain_reported:          Usuario reportó dolor/molestia
    - readiness_computed:     Readiness calculado en daily loop
    - daily_loop_completed:   Ciclo diario terminado
    - plan_adjusted:          Plan de entrenamiento ajustado
    - notification_opened:    Usuario abrió una notificación
    - workout_missed:         Sesión planificada no ejecutada
    - recovery_mode_activated:Modo recuperación activado
    - check_in_submitted:     Usuario respondió un check-in
    - streak_milestone:       Racha alcanzó un hito
    - state_changed:          Estado del atleta cambió significativamente
    """

    __tablename__ = "atlas_events"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, default=dict)
    source = Column(String, default="system")
    correlation_id = Column(String, nullable=True)
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<AtlasEvent id={self.id} type={self.event_type} "
            f"user={self.user_id} processed={self.processed}>"
        )
