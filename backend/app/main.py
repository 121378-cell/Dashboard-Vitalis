from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1 import api
from app.db.session import engine, Base
# Importar base para asegurar que todos los modelos están registrados
import app.db.base 
from contextlib import asynccontextmanager
import logging
import os

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
                user = User(id="default_user", email="sergi.marquez.al@gmail.com", full_name="Atleta ATLAS")
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
                
    except Exception as e:
        logger.error(f"Error during bootstrap: {e}")

    yield
    # Shutdown
    logger.info("ATLAS shutting down...")

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

# Configuración de CORS refinada para Producción
# Incluimos la URL de Vercel y localhost para desarrollo
origins = [
    "https://dashboard-vitalis.vercel.app",
    "https://dashboard-vitalis-git-main-sergimarquezbrugal-2353.vercel.app", # URL de preview de Vercel
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost",       # Android Capacitor base origin
    "capacitor://localhost"   # iOS Capacitor base origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(api.api_router, prefix=settings.API_V1_STR)
