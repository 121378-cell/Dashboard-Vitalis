from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1 import api
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ATLAS starting up...")
    # Desactivamos el check bloqueante en el arranque para despliegue fluido en Fly.io
    # try:
    #     from app.core.health_check import check_all_services
    #     check_all_services()
    # except Exception as e:
    #     logger.warning(f"Health check failed during startup: {e}")
    yield
    # Shutdown
    logger.info("ATLAS shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(api.api_router, prefix=settings.API_V1_STR)
