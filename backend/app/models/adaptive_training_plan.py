"""
Adaptive Training Plan Models
==============================

Modelos SQLAlchemy para el sistema de planes de entrenamiento adaptativos de ATLAS.

Este sistema es complementario al sistema existente de WeeklyPlan y se enfoca
en planes adaptativos basados en Athletic Intelligence.

Tablas:
- adaptive_training_plans: Planes semanales de entrenamiento adaptativos
- adaptive_planned_sessions: Sesiones individuales dentro de un plan adaptativo
- adaptive_plan_adjustments: Registro de adaptaciones realizadas por el sistema
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class AdaptiveTrainingPlan(Base):
    """Modelo para planes de entrenamiento semanales adaptativos."""
    
    __tablename__ = "adaptive_training_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default='default_user', index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    week_start_date = Column(Date, nullable=False, index=True)
    week_end_date = Column(Date, nullable=False)
    goal = Column(String, nullable=False)
    status = Column(String, default='active')  # active/completed/cancelled
    plan_json = Column(Text, nullable=False)  # JSON completo del plan
    ai_reasoning = Column(Text)  # Por qué este plan
    fitness_snapshot = Column(Text)  # Snapshot del perfil atlético al generar
    
    # Relaciones
    sessions = relationship("AdaptivePlannedSession", back_populates="plan", cascade="all, delete-orphan")
    adjustments = relationship("AdaptivePlanAdjustment", back_populates="plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AdaptiveTrainingPlan(id={self.id}, week_start={self.week_start_date}, goal={self.goal})>"


class AdaptivePlannedSession(Base):
    """Modelo para sesiones individuales planificadas en sistema adaptativo."""
    
    __tablename__ = "adaptive_planned_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("adaptive_training_plans.id"), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    day_of_week = Column(String, nullable=False)  # 'Lunes', 'Martes', etc.
    session_type = Column(String, nullable=False)  # strength/running/trail/mobility/hiit/rest/active_recovery
    title = Column(String, nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer)
    intensity = Column(String)  # low/medium/high
    exercises_json = Column(Text)  # JSON lista ejercicios (solo para strength)
    running_details_json = Column(Text)  # JSON detalles running
    completed = Column(Boolean, default=False)
    garmin_activity_id = Column(String)  # ID actividad Garmin si se detecta automáticamente
    user_notes = Column(Text)
    modified_by_user = Column(Boolean, default=False)
    adaptation_reason = Column(Text)  # Si fue adaptada por el daily loop
    
    # Relaciones
    plan = relationship("AdaptiveTrainingPlan", back_populates="sessions")
    adjustments = relationship("AdaptivePlanAdjustment", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AdaptivePlannedSession(id={self.id}, date={self.session_date}, type={self.session_type})>"


class AdaptivePlanAdjustment(Base):
    """Modelo para registro de adaptaciones de planes adaptativos."""
    
    __tablename__ = "adaptive_plan_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("adaptive_training_plans.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("adaptive_planned_sessions.id"), nullable=True)
    adjustment_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text)
    original_session_json = Column(Text)
    adapted_session_json = Column(Text)
    biometrics_json = Column(Text)  # Métricas que motivaron el cambio
    
    # Relaciones
    plan = relationship("AdaptiveTrainingPlan", back_populates="adjustments")
    session = relationship("AdaptivePlannedSession", back_populates="adjustments")
    
    def __repr__(self):
        return f"<AdaptivePlanAdjustment(id={self.id}, plan_id={self.plan_id}, date={self.adjustment_date})>"
