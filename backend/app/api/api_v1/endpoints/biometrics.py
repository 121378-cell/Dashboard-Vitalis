from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.biometrics import Biometrics
from datetime import date
import json

router = APIRouter()

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
    
    if biometric:
        data = json.loads(biometric.data)
        return {**data, "source": biometric.source}
    
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
        "readiness": 78,
        "status": "good",
        "overtraining": False,
        "source": "demo"
    }
