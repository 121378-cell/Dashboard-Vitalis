from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Fitness Coach"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///atlas.db"
    
    # Auth
    GARMIN_EMAIL: Optional[str] = None
    GARMIN_PASSWORD: Optional[str] = None
    
    # AI Providers
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    PORT: int = 8005
    
    # Strava OAuth2
    STRAVA_CLIENT_ID: Optional[str] = None
    STRAVA_CLIENT_SECRET: Optional[str] = None
    STRAVA_REDIRECT_URI: str = "http://localhost:8005/api/v1/strava/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    
    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
