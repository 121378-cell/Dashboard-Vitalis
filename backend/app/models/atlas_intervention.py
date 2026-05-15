"""
ATLAS Intervention Model
========================

Intervenciones proactivas del sistema: propuestas, acciones autónomas,
alertas. Cada intervención representa una decisión de ATLAS de actuar.

Autor: ATLAS Team
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.sql import func

from app.db.session import Base


class AtlasIntervention(Base):
    __tablename__ = "atlas_interventions"

    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Tipo de intervención (corresponde a InterventionType en autonomy_policy)
    intervention_type = Column(String(50), nullable=False, index=True)

    # Nivel de autonomía con el que se ejecutó (AUTONOMOUS, PROPOSAL, etc.)
    autonomy_level = Column(String(20), nullable=False, default="PROPOSAL")

    # Contenido de la intervención
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")

    # Estado del ciclo de vida
    # pending → accepted / rejected / expired
    # pending → executed (si es AUTONOMOUS)
    # executed / rejected → archived
    status = Column(String(20), nullable=False, default="pending", index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    responded_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    decision_deadline = Column(DateTime, nullable=True)

    # Enlace al evento que originó esta intervención
    source_event_id = Column(Integer, nullable=True)
    correlation_id = Column(String(64), nullable=True, index=True)

    # Respuesta del usuario
    response = Column(String(20), nullable=True)  # accepted / rejected / snoozed
    response_data = Column(JSON, nullable=True)

    # Métricas de efectividad (se llenan post-evaluación)
    outcome_score = Column(Float, nullable=True)
    adherence_impact = Column(Float, nullable=True)

    # Metadatos adicionales (contexto, razones, payload original)
    extra_data = Column(JSON, nullable=True)

    # Control interno
    is_active = Column(Boolean, default=True, nullable=False)
    error = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<AtlasIntervention id={self.id} "
            f"type={self.intervention_type} "
            f"status={self.status} "
            f"user={self.user_id}>"
        )
