from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base

class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    source = Column(String)  # 'garmin', 'wger', 'hevy'
    external_id = Column(String)
    name = Column(String)
    description = Column(String)
    date = Column(DateTime)
    duration = Column(Integer)  # in seconds
    calories = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'source', 'external_id', name='_user_source_external_uc'),
        {'extend_existing': True},
    )
