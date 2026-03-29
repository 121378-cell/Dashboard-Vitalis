from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, workouts, biometrics, ai, sync, settings, readiness, readiness_ws, sessions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(biometrics.router, prefix="/biometrics", tags=["biometrics"])
api_router.include_router(readiness.router, prefix="/readiness", tags=["readiness"])
api_router.include_router(readiness_ws.router, prefix="", tags=["websocket"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
