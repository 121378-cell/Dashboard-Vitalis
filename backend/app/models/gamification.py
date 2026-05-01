from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., "first_blood", "iron_will"
    title = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # Could be an emoji or icon name
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    xp_reward = Column(Integer, default=0)

class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., "garmin_sync", "readiness_above_60"
    current_count = Column(Integer, default=0)
    best_count = Column(Integer, default=0)
    last_date = Column(DateTime(timezone=True))  # Last date the streak was updated

class XpLog(Base):
    __tablename__ = "xp_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    xp = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=False)  # e.g., "workout_completed", "daily_sync"
    date = Column(DateTime(timezone=True), server_default=func.now())

# Note: The user_level view is typically created via a database view or computed in the service.
# We'll compute it in the service for simplicity, but if you want a database view, you can create it via migration.