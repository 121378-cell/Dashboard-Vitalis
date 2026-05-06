from sqlalchemy import Column, String, ForeignKey
from app.db.session import Base

class Token(Base):
    __tablename__ = "tokens"
    __table_args__ = {'extend_existing': True}

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    # Columnas que coinciden con la base de datos SQLite real
    garmin_email = Column(String)           # Garmin email
    garmin_password = Column(String)        # Garmin password
    garmin_session = Column(String)          # Garmin session data (JSON)
    hevy_username = Column(String)           # Hevy username
    wger_api_key = Column(String)           # Wger API key
