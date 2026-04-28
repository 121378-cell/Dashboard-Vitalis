from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.db.session import Base


class AtlasMemory(Base):
    """
    Long-Term Memory entry for ATLAS AI.

    Stores persistent facts about the athlete that accumulate over time
    and are injected into every AI context window.
    """

    __tablename__ = "atlas_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)  # injury, achievement, pattern, preference, milestone
    content = Column(Text, nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    importance = Column(Integer, default=5)  # 1-10
    source = Column(String, default="auto")  # auto, user, coach, garmin_sync
    created_at = Column(DateTime(timezone=True), server_default=func.now())
