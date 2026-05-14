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
from sqlalchemy import text

logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ATLAS starting up...")
    logger.info(f"Database: SQLite database ready")
    
    # 1. Crear tablas si no existen (Indispensable para nuevos volúmenes en Fly.io)
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # 2. Migracion de planned_workouts (tabla del training engine)
        try:
            logger.info("Running planned_workouts migration...")
            from migrate_planned_workouts import (
                create_planned_workouts_table,
                migrate_adaptive_sessions
            )
            create_planned_workouts_table()
            migrate_adaptive_sessions()
            logger.info("planned_workouts migration completed.")
        except Exception as me:
            logger.error(f"planned_workouts migration error: {me}")

        # 3. Migracion de birth_date (columna faltante en users)
        try:
            logger.info("Running birth_date migration...")
            from migrate_birth_date import migrate as migrate_birth_date, update_user_birth_date
            migrate_birth_date()
            update_user_birth_date()
            logger.info("birth_date migration completed.")
        except Exception as me:
            logger.error(f"birth_date migration error: {me}")

        # 4. Migracion de columnas faltantes en tokens
        try:
            logger.info("Checking for missing columns in tokens table...")
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(tokens)"))
                token_cols = {row[1] for row in result.fetchall()}
                from app.models.token import Token
                model_cols = {str(c.name) for c in Token.__table__.columns}
                missing = model_cols - token_cols
                if missing:
                    type_map = {
                        'VARCHAR': 'VARCHAR', 'STRING': 'VARCHAR',
                        'TEXT': 'TEXT',
                        'INTEGER': 'INTEGER',
                        'FLOAT': 'FLOAT', 'REAL': 'FLOAT',
                        'BOOLEAN': 'BOOLEAN',
                        'DATETIME': 'DATETIME', 'DATE': 'DATE',
                    }
                    for col_name in missing:
                        raw_type = str(
                            next((c.type for c in Token.__table__.columns if c.name == col_name), '')
                        ).upper().split('(')[0]
                        safe_type = type_map.get(raw_type, 'VARCHAR')
                        logger.info(f"Adding missing column tokens.{col_name} ({safe_type})...")
                        conn.execute(text(
                            f"ALTER TABLE tokens ADD COLUMN {col_name} {safe_type}"
                        ))
                    conn.commit()
                    logger.info(f"Added missing columns: {', '.join(missing)}")
                else:
                    logger.info("All tokens columns present")
        except Exception as me:
            logger.error(f"tokens columns migration error: {me}")

        # 5. Bootstrap de credenciales (Plan B para Fly.io)
        from app.db.session import SessionLocal
        from app.models.token import Token
        from app.models.user import User
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == "default_user").first()
            if not user:
                logger.info("Creating default_user...")
                user = User(
            id="default_user",
            email=os.getenv("ATLAS_USER_EMAIL", "user@example.com"),
            name=os.getenv("ATLAS_USER_NAME", "Athlete"),
        )
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
        
        # 6. Start the scheduler
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

# CORS configuration — exact origins only, no wildcards
origins = [
    "https://dashboard-vitalis.vercel.app",
    "https://dashboard-vitalis-git-main-sergimarquezbrugal-2353.vercel.app",
    "https://atlas-vitalis-backend.fly.dev",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost",
    "capacitor://localhost",
    "ionic://localhost",
]

app.add_middleware(MonitoringMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-user-id"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

_start_time = time.time()

@app.get("/health")
def health_check():
    db_ok = False
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "uptime_seconds": int(time.time() - _start_time),
    }

@app.get("/metrics")
def metrics_endpoint():
    return get_metrics()

app.include_router(api.api_router, prefix=settings.API_V1_STR)
