from datetime import date
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    week_start = Column(String, index=True)  # YYYY-MM-DD
    week_end = Column(String, index=True)   # YYYY-MM-DD
    plan_data = Column(JSON)  # Full plan JSON with exercises, sets, reps, weights
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="active")  # active, completed, skipped, archived
    objective = Column(String, nullable=True)  # e.g., "strength", "hypertrophy", "endurance"
    ai_version = Column(String, default="1.0")
    
    # Relationships
    sessions = relationship("TrainingSession", back_populates="plan", cascade="all, delete-orphan")


class PlanSession(Base):
    __tablename__ = "planner_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("weekly_plans.id"), index=True)
    day_index = Column(Integer)  # 0-6 (Monday-Sunday relative to week_start)
    day_name = Column(String)     # e.g., "Monday", "PUSH"
    scheduled_date = Column(String)  # YYYY-MM-DD when this session should be done
    exercises_data = Column(JSON)  # List of exercises with targets
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    actual_data = Column(JSON, nullable=True)  # What was actually done
    skipped = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    plan = relationship("WeeklyPlan", back_populates="sessions")


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    exercise_name = Column(String, index=True)
    weight = Column(Integer)      # in kg (or lbs if user preference)
    reps = Column(Integer)
    rpe = Column(Integer, nullable=True)  # Rate of Perceived Exertion
    date = Column(String)         # YYYY-MM-DD
    source = Column(String)       # 'auto', 'manual', 'workout'
    plan_id = Column(Integer, ForeignKey("weekly_plans.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
