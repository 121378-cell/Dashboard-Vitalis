"""
ATLAS Daily Briefing Model
=========================

Model for storing pre-generated daily briefings for users.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.session import Base

class DailyBriefing(Base):
    __tablename__ = "daily_briefings"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)  # Could be UUID or user_id + date
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)  # Date of the briefing
    content = Column(Text, nullable=False)  # JSON content of the briefing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # We'll create a composite unique constraint on user_id and date to avoid duplicate briefings per day
    # But SQLAlchemy doesn't automatically create it, we'll rely on application logic or add it via migrations
    # For now, we'll handle duplicates in the service layer