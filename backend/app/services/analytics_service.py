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
        Wrapper que usa el ReadinessEngine consolidado.
        Mantiene compatibilidad con endpoints existentes.
        """
        from app.core.readiness_engine import ReadinessEngine
        
        # Obtener datos de hoy
        today_str = date.today().isoformat()
        today_bio = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == today_str
        ).first()
        
        if not today_bio:
            return {"score": 0, "status": "unknown", "message": "No data for today"}
        
        try:
            today_data = json.loads(today_bio.data)
        except:
            return {"score": 0, "status": "error", "message": "Invalid data format"}
        
        # Crear engine y calcular
        engine = ReadinessEngine(user_id, db)

        input_data = {
            "heart_rate": today_data.get("heartRate", 60),
            "hrv": today_data.get("hrv"),
            "sleep_hours": today_data.get("sleep", 0),
            "stress_level": today_data.get("stress", 50),
            "steps": today_data.get("steps", 0),
            "steps_prev_7d_avg": 10000,
            "is_rest_day": today_data.get("steps", 0) < 8000,
            "exercise_load_7d": 1.0
        }
        
        score, factors = engine.calculate_readiness(input_data)
        
        # Mapear status al formato antiguo
        status_map = {
            "high": "excellent" if score >= 85 else "good",
            "medium": "fair" if score < 65 else "good",
            "low": "poor"
        }
        
        return {
            "score": int(score),
            "status": status_map.get("high" if score >= 71 else "medium" if score >= 41 else "low", "good"),
            "hrv_baseline": engine.baselines.get("hrv_avg", 55),
            "rhr_baseline": engine.baselines.get("hr_resting_avg", 60),
            "hrv_today": today_data.get("hrv", 0),
            "rhr_today": today_data.get("heartRate", 0)
        }
