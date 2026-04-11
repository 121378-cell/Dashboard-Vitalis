from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1 import api
from app.db.session import engine, Base
# Importar base para asegurar que todos los modelos están registrados
import app.db.base 
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ATLAS starting up...")
    
    # 1. Crear tablas si no existen (Indispensable para nuevos volúmenes en Fly.io)
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

    yield
    # Shutdown
    logger.info("ATLAS shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configuración de CORS refinada para Producción
# Incluimos la URL de Vercel y localhost para desarrollo
origins = [
    "https://dashboard-vitalis.vercel.app",
    "https://dashboard-vitalis-git-main-sergimarquezbrugal-2353.vercel.app", # URL de preview de Vercel
    "http://localhost:5173",
    "http://localhost:3000",
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
