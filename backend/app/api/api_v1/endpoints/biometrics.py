from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.models.biometrics import Biometrics
from datetime import date
import json

router = APIRouter()

from app.services.analytics_service import AnalyticsService


@router.get("/")
def get_biometrics(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    date_str: str = Query(None),
):
    if not date_str:
        date_str = date.today().isoformat()

    biometric = (
        db.query(Biometrics)
        .filter(Biometrics.user_id == user_id, Biometrics.date == date_str)
        .first()
    )

    # Get advanced readiness and baselines
    readiness = AnalyticsService.get_readiness_score(db, user_id)

    if biometric:
        data = json.loads(biometric.data)
        # Merge baseline info
        return {
            **data,
            "source": biometric.source,
            "readiness": readiness.get("score"),
            "status": readiness.get("status"),
            "hrv_baseline": readiness.get("hrv_baseline"),
            "rhr_baseline": readiness.get("rhr_baseline"),
            "recovery_time": biometric.recovery_time,
            "training_status": biometric.training_status,
            "hrv_status": biometric.hrv_status,
        }

    # No data found for this date
    return {
        "heartRate": None,
        "hrv": None,
        "spo2": None,
        "stress": None,
        "steps": None,
        "sleep": None,
        "calories": None,
        "respiration": None,
        "readiness": readiness.get("score"),
        "status": readiness.get("status"),
        "hrv_baseline": readiness.get("hrv_baseline"),
        "rhr_baseline": readiness.get("rhr_baseline"),
        "overtraining": False,
        "source": "none",
    }


@router.post("/")
def upsert_biometrics(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Recibe biométricos desde el cliente (Health Connect / móvil) y los guarda por día.
    Mantiene compatibilidad con el modelo `Biometrics.data` (JSON string).
    """
    try:
        date_str = payload.get("date") or date.today().isoformat()
        source = payload.get("source") or "health_connect"

        existing = (
            db.query(Biometrics)
            .filter(Biometrics.user_id == user_id, Biometrics.date == date_str)
            .first()
        )
        if not existing:
            existing = Biometrics(user_id=user_id, date=date_str)
            db.add(existing)

        existing.data = json.dumps(payload)
        existing.source = source
        db.commit()

        return {"success": True, "user_id": user_id, "date": date_str, "source": source}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
