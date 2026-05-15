from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.services.sync_service import SyncService
from app.services.athlete_profile_service import AthleteProfileService
from app.utils.garmin_exceptions import (
    GarminRateLimitError,
    GarminAuthError,
    GarminSessionError,
)
from datetime import date, timedelta

router = APIRouter()


@router.post("/garmin")
def sync_garmin(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    days: int = Query(1, description="Number of days to sync (max 7)"),
):
    """Sync Garmin health and activity data."""
    if days > 7:
        days = 7

    date_range = [(date.today() - timedelta(days=i)).isoformat() for i in range(days)]

    # 1. Obtener cliente una sola vez para toda la operación
    from app.models.token import Token
    from app.utils.garmin import get_garmin_client
    
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if not (creds and creds.garmin_email):
        raise HTTPException(status_code=400, detail="Garmin not connected")

    try:
        client, login_result = get_garmin_client(
            email=creds.garmin_email, 
            password=creds.garmin_password,
            db=db,
            user_id=user_id
        )
    except GarminRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except (GarminAuthError, GarminSessionError) as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not client:
        raise HTTPException(status_code=401, detail="Could not authenticate with Garmin")

    # 2. Ejecutar sincronizaciones usando el mismo cliente
    try:
        health_success = SyncService.sync_garmin_health(db, user_id, date_range, client=client)
        acts_success = SyncService.sync_garmin_activities(db, user_id, date_range, client=client)
    except GarminRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Garmin sync error: {error_msg}")

    if not health_success and not acts_success:
        raise HTTPException(status_code=500, detail="Failed to sync Garmin data")

    return {"success": True, "health": health_success, "activities": acts_success}


@router.post("/wger")
def sync_wger(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    try:
        success = SyncService.sync_wger_workouts(db, user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync Wger data")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wger sync error: {e}")


@router.post("/hevy")
def sync_hevy(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    try:
        success = SyncService.sync_hevy_workouts(db, user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync Hevy data")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hevy sync error: {e}")
