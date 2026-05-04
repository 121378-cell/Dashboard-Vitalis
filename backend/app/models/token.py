from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from app.db.session import Base

class Token(Base):
    __tablename__ = "tokens"
    __table_args__ = {'extend_existing': True}

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    # Columnas que coinciden con la base de datos SQLite real
    email = Column(String)           # Garmin email (nombre real en DB)
    password = Column(String)        # Garmin password (nombre real en DB)
    garmin_session = Column(String)

    # Firebase Cloud Messaging token for push notifications
    fcm_token = Column(String, nullable=True)

    # Rate limiting fields
    garmin_rate_limited_until = Column(DateTime(timezone=True), nullable=True)
    last_login_attempt = Column(DateTime(timezone=True), nullable=True)
    login_attempts_count = Column(Integer, default=0)

    wger_api_key = Column(String)
    hevy_username = Column(String)

    # Strava OAuth2 tokens
    strava_access_token = Column(String)
    strava_refresh_token = Column(String)
    strava_expires_at = Column(DateTime(timezone=True), nullable=True)
    strava_athlete_id = Column(String)
    strava_connected = Column(Boolean, default=False)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Property para compatibilidad hacia atrás
    @property
    def garmin_email(self):
        return self.email
    
    @garmin_email.setter
    def garmin_email(self, value):
        self.email = value
    
    @property
    def garmin_password(self):
        return self.password
    
    @garmin_password.setter
    def garmin_password(self, value):
        self.password = value
