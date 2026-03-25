import json
import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.biometrics import Biometrics

logger = logging.getLogger("app.services.analytics_service")

class AnalyticsService:
    @staticmethod
    def get_hrv_baseline(db: Session, user_id: str, days: int = 7) -> float:
        """Calculate the average HRV over the last N days (excluding today)."""
        today = date.today().isoformat()
        
        # Fetch last N days of biometrics
        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date < today
        ).order_by(desc(Biometrics.date)).limit(days).all()
        
        if not bios:
            return 0.0
            
        hrv_values = []
        for bio in bios:
            data = json.loads(bio.data)
            hrv = data.get("hrv", 0)
            if hrv > 0:
                hrv_values.append(hrv)
        
        if not hrv_values:
            return 0.0
            
        return sum(hrv_values) / len(hrv_values)

    @staticmethod
    def get_rhr_baseline(db: Session, user_id: str, days: int = 7) -> float:
        """Calculate the average RHR over the last N days (excluding today)."""
        today = date.today().isoformat()
        
        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date < today
        ).order_by(desc(Biometrics.date)).limit(days).all()
        
        if not bios:
            return 0.0
            
        rhr_values = []
        for bio in bios:
            data = json.loads(bio.data)
            rhr = data.get("heartRate", 0) # resting heart rate
            if rhr > 0:
                rhr_values.append(rhr)
        
        if not rhr_values:
            return 0.0
            
        return sum(rhr_values) / len(rhr_values)

    @staticmethod
    def get_readiness_score(db: Session, user_id: str) -> dict:
        """
        Compare today's metrics with baselines to determine readiness.
        Returns a dict with score and status.
        """
        today_str = date.today().isoformat()
        today_bio = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == today_str
        ).first()
        
        if not today_bio:
            return {"score": 0, "status": "unknown", "message": "No data for today"}
            
        today_data = json.loads(today_bio.data)
        today_hrv = today_data.get("hrv", 0)
        today_rhr = today_data.get("heartRate", 0)
        
        hrv_baseline = AnalyticsService.get_hrv_baseline(db, user_id)
        rhr_baseline = AnalyticsService.get_rhr_baseline(db, user_id)
        
        # Basic Readiness Logic (to be refined in Sprint 2)
        score = 70 # start with base
        
        if hrv_baseline > 0:
            hrv_diff = ((today_hrv - hrv_baseline) / hrv_baseline) * 100
            if hrv_diff > 10: score += 10 # Good recovery
            elif hrv_diff < -15: score -= 20 # Potential overtraining/illness
            
        if rhr_baseline > 0:
            rhr_diff = today_rhr - rhr_baseline
            if rhr_diff > 5: score -= 15 # Stress/low recovery
            elif rhr_diff < -3: score += 5 # Good fitness trend
            
        score = max(0, min(100, score))
        
        status = "excellent" if score >= 85 else "good" if score >= 65 else "fair" if score >= 45 else "poor"
        
        return {
            "score": score,
            "status": status,
            "hrv_baseline": round(hrv_baseline, 1),
            "rhr_baseline": round(rhr_baseline, 1),
            "hrv_today": today_hrv,
            "rhr_today": today_rhr
        }
