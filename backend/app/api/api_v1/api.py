from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, workouts, biometrics, ai, sync

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(biometrics.router, prefix="/biometrics", tags=["biometrics"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
