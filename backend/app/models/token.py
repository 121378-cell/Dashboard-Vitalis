from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.sql import func
from app.db.session import Base

class Token(Base):
    __tablename__ = "tokens"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    garmin_email = Column(String)
    garmin_password = Column(String)
    garmin_session = Column(String)
    
    # Rate limiting fields
    garmin_rate_limited_until = Column(DateTime(timezone=True), nullable=True)
    last_login_attempt = Column(DateTime(timezone=True), nullable=True)
    login_attempts_count = Column(Integer, default=0)
    
    wger_api_key = Column(String)
    hevy_username = Column(String)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
