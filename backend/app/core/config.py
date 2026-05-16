import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from pathlib import Path

# Ruta base del directorio 'backend/'
_BACKEND_DIR = Path(__file__).parent.parent.parent
_DB_PATH = _BACKEND_DIR / "atlas_v2.db"

# Fallback: Usa valor de entorno DATABASE_URL si está definido, sino usa ruta local
default_db_url = os.getenv("DATABASE_URL", f"sqlite:///{_DB_PATH}")

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Fitness Coach"
    API_V1_STR: str = "/api/v1"

    # Database — sqlite:////data/atlas_v2.db en Fly.io (volumen persistente)
    DATABASE_URL: str = default_db_url
    
    # Auth
    GARMIN_EMAIL: Optional[str] = None
    GARMIN_PASSWORD: Optional[str] = None
    GARMIN_TOKEN_DIR: str = "/data/.garth"
    
    # JWT Secret (cambiar en produccion)
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30 days
    JWT_ADMIN_PASSWORD: Optional[str] = None  # Password para login single-user
    
    # AI Providers
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    PORT: int = 8005
    
    # Strava OAuth2
    STRAVA_CLIENT_ID: Optional[str] = None
    STRAVA_CLIENT_SECRET: Optional[str] = None
    STRAVA_REDIRECT_URI: str = "http://localhost:8001/api/v1/strava/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    FLY_APP_URL: str = "https://atlas-vitalis-backend.fly.dev"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Encryption
    FERNET_KEY: Optional[str] = None

    # Notifications
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATIONS_TELEGRAM_ENABLED: bool = True
    NOTIFICATIONS_SYSTEM_ENABLED: bool = True
    
    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
