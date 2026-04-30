from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum

class ChallengeType(str, enum.Enum):
    steps = "steps"
    workouts = "workouts"
    volume = "volume"
    readiness = "readiness"

class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    type = Column(Enum(ChallengeType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    metric = Column(String, nullable=False)
    prize_xp = Column(Integer, default=0)
    participants = relationship("ChallengeParticipant", back_populates="challenge")

class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"
    challenge_id = Column(Integer, ForeignKey("challenges.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    current_value = Column(Float, default=0)
    rank = Column(Integer, default=0)
    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User", back_populates="challenge_participations")

class UserPublicProfile(Base):
    __tablename__ = "user_public_profile"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    display_name = Column(String, nullable=False)
    avatar_url = Column(String)
    is_public = Column(Boolean, default=False)
    total_workouts = Column(Integer, default=0)
    best_readiness = Column(Float, default=0)
    current_level = Column(Integer, default=1)
    user = relationship("User", back_populates="public_profile")
