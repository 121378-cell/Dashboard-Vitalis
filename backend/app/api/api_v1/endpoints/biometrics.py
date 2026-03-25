from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.biometrics import Biometrics
from datetime import date
import json

router = APIRouter()

from app.services.analytics_service import AnalyticsService

@router.get("/")
def get_biometrics(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    date_str: str = Query(None)
):
    if not date_str:
        date_str = date.today().isoformat()
    
    biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id, 
        Biometrics.date == date_str
    ).first()
    
    # Get advanced readiness and baselines
    readiness = AnalyticsService.get_readiness_score(db, user_id)
    
    if biometric:
        data = json.loads(biometric.data)
        # Merge baseline info
        return {
            **data, 
            "source": biometric.source,
            "readiness": readiness.get("score", 70),
            "status": readiness.get("status", "good"),
            "hrv_baseline": readiness.get("hrv_baseline"),
            "rhr_baseline": readiness.get("rhr_baseline"),
            "recovery_time": biometric.recovery_time,
            "training_status": biometric.training_status,
            "hrv_status": biometric.hrv_status
        }
    
    # Fallback to demo data if nothing found
    return {
        "heartRate": 68,
        "hrv": 52,
        "spo2": 98,
        "stress": 32,
        "steps": 8420,
        "sleep": 7.5,
        "calories": 2100,
        "respiration": 14,
        "readiness": readiness.get("score", 78),
        "status": readiness.get("status", "good"),
        "hrv_baseline": readiness.get("hrv_baseline"),
        "rhr_baseline": readiness.get("rhr_baseline"),
        "overtraining": False,
        "source": "demo"
    }
