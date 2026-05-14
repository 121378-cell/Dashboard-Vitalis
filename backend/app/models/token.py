from sqlalchemy import Column, String, ForeignKey
from app.db.session import Base
from app.models.custom_types import EncryptedString

class Token(Base):
    __tablename__ = "tokens"
    __table_args__ = {'extend_existing': True}

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    # Columnas que coinciden con la base de datos SQLite real
    garmin_email = Column(String)           # Garmin email
    garmin_password = Column(EncryptedString())  # Garmin password (auto-encrypted)
    garmin_session = Column(String)          # Garmin session data (JSON)
    hevy_username = Column(String)           # Hevy username
    wger_api_key = Column(EncryptedString())        # Wger API key (auto-encrypted)
    fcm_token = Column(String)               # Firebase Cloud Messaging token