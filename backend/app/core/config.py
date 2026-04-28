from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Fitness Coach"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///atlas_v2.db"
    
    # Auth
    GARMIN_EMAIL: Optional[str] = None
    GARMIN_PASSWORD: Optional[str] = None
    GARMIN_TOKEN_DIR: str = "/data/.garth"
    
    # CORS
    ALLOW_ALL_ORIGINS: bool = False
    
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
    
    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
