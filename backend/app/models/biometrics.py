from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Biometrics(Base):
    __tablename__ = "biometrics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    date = Column(String)  # YYYY-MM-DD
    data = Column(String)  # JSON-encoded biometrics
    source = Column(String)
    
    # Advanced metrics added from AI_Fitness
    recovery_time = Column(Integer, nullable=True) # hours
    training_status = Column(String, nullable=True) # productive, maintenance, etc.
    hrv_status = Column(String, nullable=True) # balanced, unbalanced, etc.
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
