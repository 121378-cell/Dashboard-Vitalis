from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.sync_service import SyncService
from datetime import date, timedelta

router = APIRouter()

@router.post("/garmin")
def sync_garmin(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    days: int = Query(1, description="Number of days to sync (max 7)")
):
    """Sync Garmin health and activity data."""
    if days > 7:
        days = 7
    
    date_range = [(date.today() - timedelta(days=i)).isoformat() for i in range(days)]
    
    health_success = SyncService.sync_garmin_health(db, user_id, date_range)
    acts_success = SyncService.sync_garmin_activities(db, user_id, date_range)
    
    if not health_success and not acts_success:
        raise HTTPException(status_code=500, detail="Failed to sync Garmin data")
        
    return {"success": True, "health": health_success, "activities": acts_success}

@router.post("/wger")
def sync_wger(db: Session = Depends(get_db), user_id: str = "default_user"):
    success = SyncService.sync_wger_workouts(db, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to sync Wger data")
    return {"success": True}

@router.post("/hevy")
def sync_hevy(db: Session = Depends(get_db), user_id: str = "default_user"):
    success = SyncService.sync_hevy_workouts(db, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to sync Hevy data")
    return {"success": True}

