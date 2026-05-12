from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class MasterPlan(Base):
    __tablename__ = "master_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default='default_user', index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
    target_date = Column(Date)
    start_date = Column(Date, nullable=False)
    status = Column(String, default='active')
    total_weeks = Column(Integer)
    current_week = Column(Integer, default=1)
    phases_json = Column(Text)
    milestones_json = Column(Text)
    ai_strategy = Column(Text)
    preferences_json = Column(Text)

    weeks = relationship("AdaptiveTrainingPlan", back_populates="master_plan")

    def __repr__(self):
        return f"<MasterPlan(id={self.id}, title={self.title}, status={self.status})>"
