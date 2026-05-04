"""
Dashboard-Vitalis — Training Session Models
============================================

Modelos SQLAlchemy para el sistema de sesiones de entrenamiento.
Incluye TrainingSession (sesiones individuales) y WeeklyReport (informes semanales).

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

from uuid import uuid4

from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.sql import func

from app.db.session import Base


class TrainingSession(Base):
    """
    Sesión de entrenamiento individual.

    Representa una sesión planificada, activa o completada,
    con todos los datos del plan, ejecución real y análisis.
    """

    __tablename__ = "training_sessions"
    __table_args__ = {'extend_existing': True}

    # Identificación
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD

    # Estado y origen
    status = Column(String, default="planned")  # planned/active/completed/cancelled
    generated_by = Column(String, default="atlas")  # atlas/user

    # Vinculación con Garmin
    garmin_activity_id = Column(String, nullable=True, index=True)

    # Datos del plan (generado por ATLAS) - JSON con ejercicios planificados
    plan_json = Column(Text, nullable=True)

    # Datos reales (rellenados por usuario) - JSON con datos reales
    actual_json = Column(Text, nullable=True)

    # Análisis post-sesión - Informe generado por ATLAS
    session_report = Column(Text, nullable=True)

    # Métricas derivadas de Garmin (post-sync)
    garmin_hr_avg = Column(Float, nullable=True)
    garmin_hr_max = Column(Float, nullable=True)
    garmin_calories = Column(Integer, nullable=True)
    garmin_duration_min = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TrainingSession {self.id[:8]}: {self.user_id} - {self.date} ({self.status})>"


class WeeklyReport(Base):
    """
    Informe semanal de entrenamiento.

    Generado automáticamente los domingos, incluye análisis de la semana
    completa y plan para la siguiente.
    """

    __tablename__ = "weekly_reports"
    __table_args__ = {'extend_existing': True}

    # Identificación
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=False, index=True)

    # Periodo de la semana
    week_start = Column(String, nullable=False)  # YYYY-MM-DD (lunes)
    week_end = Column(String, nullable=False)    # YYYY-MM-DD (domingo)

    # Contenidos
    report_text = Column(Text, nullable=True)    # Informe narrativo de ATLAS
    metrics_json = Column(Text, nullable=True)   # Métricas de la semana en JSON
    next_week_plan = Column(Text, nullable=True)   # Plan para la siguiente semana

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WeeklyReport {self.id[:8]}: {self.user_id} - Semana {self.week_start}>"
