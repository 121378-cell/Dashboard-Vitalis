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
    # --- Crash-safe logging: write directly to a file so errors survive stderr loss ---
    _crash_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lifespan_crash.log')
    _crash_log = open(_crash_log_path, 'a', encoding='utf-8')
    def _log_crash(msg: str):
        try:
            _crash_log.write(f"{msg}\n")
            _crash_log.flush()
        except Exception:
            pass

    _log_crash("=== LIFESPAN START ===")

    # Startup
    try:
        logger.info("ATLAS starting up...")
        logger.info("Database: SQLite database ready")
        _log_crash("ATLAS starting up...")
        
        # 1. Crear tablas si no existen (Indispensable para nuevos volúmenes en Fly.io)
        try:
            logger.info("Initializing database tables...")
            _log_crash("Step 1: Creating tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully.")
            _log_crash("Step 1: Tables created OK")
        except Exception as e:
            _log_crash(f"Step 1 FAILED: {e}")
            logger.error(f"Database table initialization error: {e}")

        # 2. Migracion de planned_workouts (tabla del training engine)
        try:
            logger.info("Running planned_workouts migration...")
            _log_crash("Step 2: planned_workouts migration...")
            from migrate_planned_workouts import (
                create_planned_workouts_table,
                migrate_adaptive_sessions
            )
            create_planned_workouts_table()
            migrate_adaptive_sessions()
            logger.info("planned_workouts migration completed.")
            _log_crash("Step 2: planned_workouts migration OK")
        except Exception as me:
            _log_crash(f"Step 2 FAILED: {me}")
            logger.error(f"planned_workouts migration error: {me}")

        # 3. Migracion de birth_date (columna faltante en users)
        try:
            logger.info("Running birth_date migration...")
            _log_crash("Step 3: birth_date migration...")
            from migrate_birth_date import migrate as migrate_birth_date, update_user_birth_date
            migrate_birth_date()
            update_user_birth_date()
            logger.info("birth_date migration completed.")
            _log_crash("Step 3: birth_date migration OK")
        except Exception as me:
            _log_crash(f"Step 3 FAILED: {me}")
            logger.error(f"birth_date migration error: {me}")

        # 4. Migracion de columnas faltantes en tokens
        try:
            logger.info("Checking for missing columns in tokens table...")
            _log_crash("Step 4: tokens columns check...")
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
            _log_crash("Step 4: tokens columns OK")
        except Exception as me:
            _log_crash(f"Step 4 FAILED: {me}")
            logger.error(f"tokens columns migration error: {me}")

        # 5. Bootstrap de credenciales (Plan B para Fly.io)
        try:
            _log_crash("Step 5: Bootstrapping credentials...")
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
            _log_crash("Step 5: Credentials bootstrap OK")
        except Exception as e:
            _log_crash(f"Step 5 FAILED: {e}")
            logger.error(f"Bootstrap credentials error: {e}")

        # 6. Start the scheduler
        try:
            logger.info("Starting scheduler...")
            _log_crash("Step 6: Starting scheduler...")
            start_scheduler()
            logger.info("Scheduler started successfully.")
            _log_crash("Step 6: Scheduler started OK")
        except Exception as e:
            _log_crash(f"Step 6 FAILED: {e}")
            logger.error(f"Scheduler start error: {e}")

        _log_crash("=== LIFESPAN STARTUP COMPLETE ===")

    except Exception as e:
        _log_crash(f"CRITICAL: Lifespan startup error: {e}")
        logger.error(f"CRITICAL: Lifespan startup error: {e}")
    finally:
        try:
            _crash_log.close()
        except Exception:
            pass

    yield
    # Shutdown
    logger.info("ATLAS shutting down...")
    try:
        shutdown_scheduler()
        logger.info("Scheduler shut down.")
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {e}")

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
