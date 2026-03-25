from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Biometrics(Base):
    __tablename__ = "biometrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    date = Column(String)  # YYYY-MM-DD
    data = Column(String)  # JSON-encoded biometrics
    source = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
