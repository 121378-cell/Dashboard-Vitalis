from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1 import api
from app.db.session import engine, Base
import app.db.base
from contextlib import asynccontextmanager
import logging
import os
import time
from app.services.scheduler_service import start_scheduler, shutdown_scheduler
from app.middleware.monitoring import MonitoringMiddleware, get_metrics
from app.core.rate_limiter import RateLimiterMiddleware

logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ATLAS starting up...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # 1. Crear tablas si no existen (Indispensable para nuevos volúmenes en Fly.io)
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # 2. Bootstrap de credenciales (Plan B para Fly.io)
        from app.db.session import SessionLocal
        from app.models.token import Token
        from app.models.user import User
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == "default_user").first()
            if not user:
                logger.info("Creating default_user...")
                user = User(id="default_user", email="sergi.marquez.al@gmail.com", full_name="Sergi")
                db.add(user)
                db.commit()
            
            token = db.query(Token).filter(Token.user_id == "default_user").first()
            if not token:
                logger.info("Bootstrapping Garmin credentials from Environment Variables...")
                token = Token(
                    user_id="default_user",
                    garmin_email=os.getenv("GARMIN_EMAIL"),
                    garmin_password=os.getenv("GARMIN_PASSWORD")
                )
                db.add(token)
                db.commit()
                logger.info("Garmin credentials bootstrapped successfully.")
        
        # 3. Start the scheduler
        logger.info("Starting scheduler...")
        start_scheduler()
        logger.info("Scheduler started successfully.")
        
    except Exception as e:
        logger.error(f"Error during bootstrap: {e}")

    yield
    # Shutdown
    logger.info("ATLAS shutting down...")
    shutdown_scheduler()
    logger.info("Scheduler shut down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Middleware para corregir Mixed Content en redirecciones (Detrás de Fly.io)
@app.middleware("http")
async def fix_https_redirect(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)

# CORS configuration
# Production: fly.dev + Capacitor mobile origins + local dev
origins = [
    "https://dashboard-vitalis.vercel.app",
    "https://dashboard-vitalis-git-main-sergimarquezbrugal-2353.vercel.app",
    "https://atlas-vitalis-backend.fly.dev",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost",
    "capacitor://localhost",
    "ionic://localhost",
    "https://*.fly.dev",
    "capacitor://",
    "ionic://",
]

if settings.ALLOW_ALL_ORIGINS:
    origins = ["*"]

app.add_middleware(MonitoringMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()

@app.get("/health")
def health_check():
    db_ok = False
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            db.execute("SELECT 1")
            db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "uptime_seconds": int(time.time() - _start_time),
    }

@app.get("/metrics")
def metrics_endpoint():
    return get_metrics()

app.include_router(api.api_router, prefix=settings.API_V1_STR)
