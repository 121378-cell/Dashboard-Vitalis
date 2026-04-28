from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class AtlasMemory(Base):
    """
    Long-Term Memory entry for ATLAS AI.

    Stores persistent facts about the athlete that accumulate over time
    and are injected into every AI context window.
    
    Types:
    - injury: Lesiones, molestias, restricciones físicas
    - achievement: PRs, hitos, logros destacados
    - pattern: Patrones de comportamiento recurrentes
    - preference: Preferencias explícitas del atleta
    - milestone: Metas de composición corporal alcanzadas
    - health_alert: Alertas de salud críticas (HRV bajo, etc.)
    """

    __tablename__ = "atlas_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)  # injury | achievement | pattern | preference | milestone | health_alert
    content = Column(Text, nullable=False)
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD
    importance = Column(Integer, default=5)  # 1-10
    tags = Column(JSON, default=list)  # Array of strings for categorization
    source = Column(String, default="auto")  # garmin_sync | user_input | ai_generated | auto
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
