import json
import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.biometrics import Biometrics
from app.models.workout import Workout

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
    def get_workload_for_period(db: Session, user_id: str, days: int) -> float:
        """Calculate total workload (Duration * AvgHR) for a given period."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date >= start_date,
            Workout.date < end_date
        ).all()
        
        total_load = 0.0
        for w in workouts:
            try:
                metrics = json.loads(w.description) if w.description else {}
                avg_hr = metrics.get("avgHR", 120) # Fallback to moderate HR
                duration_min = w.duration / 60
                # Simple load estimation: Duration (min) * Avg HR
                # In a real scenario, this would use TRIMP or Garmin's native load
                total_load += duration_min * avg_hr
            except:
                total_load += (w.duration / 60) * 120
                
        return total_load

    @staticmethod
    def calculate_acwr(db: Session, user_id: str) -> dict:
        """
        Calculates the Acute:Chronic Workload Ratio.
        Acute (7 days) / Chronic (28 days / 4)
        Optimal range: 0.8 - 1.3
        """
        acute_load = AnalyticsService.get_workload_for_period(db, user_id, 7)
        chronic_load_total = AnalyticsService.get_workload_for_period(db, user_id, 28)
        
        # Chronic load is the average weekly load over 4 weeks
        chronic_load_avg = chronic_load_total / 4
        
        if chronic_load_avg == 0:
            return {"ratio": 1.0, "status": "mantenimiento", "message": "Datos insuficientes para ACWR"}
            
        ratio = acute_load / chronic_load_avg
        
        status = "óptimo"
        message = "Tu progresión de carga es ideal."
        
        if ratio > 1.5:
            status = "peligro"
            message = "¡CUIDADO! Estás aumentando la carga demasiado rápido. Riesgo de lesión alto."
        elif ratio > 1.3:
            status = "sobreesfuerzo"
            message = "Carga elevada. Asegura una buena recuperación."
        elif ratio < 0.8:
            status = "desentrenamiento"
            message = "La carga es baja. Podrías perder adaptaciones físicas."
            
        return {
            "ratio": round(ratio, 2),
            "status": status,
            "message": message,
            "acute": round(acute_load, 1),
            "chronic_avg": round(chronic_load_avg, 1)
        }

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
