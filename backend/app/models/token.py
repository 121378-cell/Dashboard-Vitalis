from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Token(Base):
    __tablename__ = "tokens"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    email = Column(String)
    password = Column(String)
    garmin_session = Column(String)
    wger_api_key = Column(String)
    hevy_username = Column(String)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
