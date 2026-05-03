import json
import logging
import math
import statistics
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.models.training_plan import PersonalRecord

logger = logging.getLogger("app.services.analytics_service")

MIN_DATA_DAYS = 30
INSIGHT_CACHE_TTL = 7 * 24 * 3600  # 7 days in seconds

_insight_cache: Dict[str, Dict[str, Any]] = {}


@dataclass
class ReadinessForecast:
    date: str
    predicted_score: int
    confidence: float


@dataclass
class PlateauAlert:
    exercise: str
    weeks_stagnant: int
    current_weight: int
    suggestion: str


@dataclass
class InsightReport:
    correlations: Dict[str, Any]
    insights: List[Dict[str, Any]]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pearson_r(x: List[float], y: List[float]) -> Optional[float]:
    n = len(x)
    if n < 5 or len(y) != n:
        return None
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return None
    return _clamp(num / (den_x * den_y), -1.0, 1.0)


def _ewma(values: List[float], alpha: float = 0.3) -> List[float]:
    if not values:
        return []
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def _linear_slope(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(values)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(xs, values))
    den = sum((xi - mean_x) ** 2 for xi in xs)
    if den == 0:
        return 0.0
    return num / den


def _r_squared(x: List[float], y: List[float]) -> float:
    r = _pearson_r(x, y)
    return r ** 2 if r is not None else 0.0

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
        hrv = data.get("hrv") or 0
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
            rhr = data.get("heartRate") or 0
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
                avg_hr = metrics.get("avgHR") or 120
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
    def get_biometrics_for_range(db: Session, user_id: str, start_date: str, end_date: str) -> list:
        """Fetch biometrics data for a specific date range."""
        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= start_date,
            Biometrics.date <= end_date
        ).order_by(Biometrics.date).all()
        
        result = []
        for bio in bios:
            try:
                data = json.loads(bio.data)
                data['date'] = bio.date
                result.append(data)
            except:
                continue
        return result

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
            "heart_rate": today_data.get("heartRate") or 60,
            "hrv": today_data.get("hrv") or 0,
            "sleep_hours": today_data.get("sleep") or 0,
            "stress_level": today_data.get("stress") or 50,
            "steps": today_data.get("steps") or 0,
            "steps_prev_7d_avg": 10000,
            "is_rest_day": (today_data.get("steps") or 0) < 8000,
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
            "hrv_today": today_data.get("hrv") or 0,
            "rhr_today": today_data.get("heartRate") or 0
        }

    # =========================================================================
    # PROMPT 15 — ADVANCED ANALYTICS & ML
    # =========================================================================

    @staticmethod
    def _fetch_daily_data(db: Session, user_id: str, days: int) -> List[Dict[str, Any]]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.isoformat()

        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= start_str,
        ).order_by(Biometrics.date).all()

        bio_map: Dict[str, Dict[str, Any]] = {}
        for bio in bios:
            try:
                d = json.loads(bio.data)
                d["date"] = bio.date if isinstance(bio.date, str) else bio.date.isoformat() if bio.date else ""
                bio_map[d["date"]] = d
            except Exception:
                continue

        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date >= start_date,
        ).order_by(Workout.date).all()

        workout_map: Dict[str, List[Dict[str, Any]]] = {}
        for w in workouts:
            d_str = w.date.isoformat() if hasattr(w.date, "isoformat") else str(w.date)
            entry = {"duration_min": (w.duration or 0) / 60}
            try:
                metrics = json.loads(w.description) if w.description else {}
                entry["avg_hr"] = metrics.get("avgHR") or 0
                entry["rpe"] = metrics.get("rpe") or 0
                entry["hour"] = metrics.get("hour") or 0
            except Exception:
                entry["avg_hr"] = 0
                entry["rpe"] = 0
                entry["hour"] = 0
            workout_map.setdefault(d_str, []).append(entry)

        rows = []
        current = start_date
        while current <= end_date:
            d_str = current.isoformat()
            bio = bio_map.get(d_str, {})
            day_workouts = workout_map.get(d_str, [])
            rows.append({
                "date": d_str,
                "hrv": bio.get("hrv") or 0,
                "hr": bio.get("heartRate") or 0,
                "sleep": bio.get("sleep") or 0,
                "stress": bio.get("stress") or 0,
                "steps": bio.get("steps") or 0,
                "workouts": day_workouts,
                "weekday": current.weekday(),
                "is_rest": len(day_workouts) == 0,
            })
            current += timedelta(days=1)
        return rows

    @staticmethod
    def find_personal_correlations(db: Session, user_id: str, days: int = 90) -> Dict[str, Any]:
        data = AnalyticsService._fetch_daily_data(db, user_id, days)
        unique_dates = set(r["date"] for r in data if r["hrv"] > 0 or r["sleep"] > 0)
        if len(unique_dates) < MIN_DATA_DAYS:
            return {
                "status": "accumulating",
                "days_available": len(unique_dates),
                "days_required": MIN_DATA_DAYS,
                "message": f"Acumulando datos... {len(unique_dates)}/{MIN_DATA_DAYS} días necesarios.",
                "correlations": {},
                "insights": [],
            }

        sleep_vals = []
        hrv_next_vals = []
        for i in range(len(data) - 1):
            s = data[i]["sleep"]
            h = data[i + 1]["hrv"]
            if s > 0 and h > 0:
                sleep_vals.append(s)
                hrv_next_vals.append(h)

        sleep_to_hrv = _pearson_r(sleep_vals, hrv_next_vals)

        hrv_vals = []
        rpe_inv_vals = []
        for row in data:
            if row["hrv"] > 0 and row["workouts"]:
                avg_rpe = statistics.mean(w.get("rpe") or 5 for w in row["workouts"] if (w.get("rpe") or 0) > 0)
                if avg_rpe > 0:
                    hrv_vals.append(row["hrv"])
                    rpe_inv_vals.append(10 - avg_rpe)

        hrv_to_perf = _pearson_r(hrv_vals, rpe_inv_vals)

        rest_readiness = AnalyticsService._analyze_rest_impact(data)

        best_time = AnalyticsService._find_best_training_window(data)

        correlations = {
            "sleep_to_hrv": {
                "r": sleep_to_hrv,
                "label": "Sueño → HRV día siguiente",
                "strength": AnalyticsService._strength_label(sleep_to_hrv),
            },
            "hrv_to_performance": {
                "r": hrv_to_perf,
                "label": "HRV → Rendimiento entrenamiento",
                "strength": AnalyticsService._strength_label(hrv_to_perf),
            },
            "rest_days_to_readiness": rest_readiness,
            "best_training_time": best_time,
        }

        insights = AnalyticsService._generate_correlation_insights(correlations, data, user_id)

        return {
            "status": "ok",
            "days_analyzed": len(unique_dates),
            "correlations": correlations,
            "insights": insights,
        }

    @staticmethod
    def _strength_label(r: Optional[float]) -> str:
        if r is None:
            return "insuficiente"
        ar = abs(r)
        if ar >= 0.7:
            return "fuerte"
        elif ar >= 0.4:
            return "moderada"
        elif ar >= 0.2:
            return "débil"
        return "insignificante"

    @staticmethod
    def _analyze_rest_impact(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        rest_groups: Dict[int, List[float]] = {}
        i = 0
        while i < len(data):
            if data[i]["is_rest"]:
                rest_count = 0
                while i < len(data) and data[i]["is_rest"]:
                    rest_count += 1
                    i += 1
                if i < len(data):
                    next_hrv = data[i]["hrv"]
                    next_sleep = data[i]["sleep"]
                    composite = 0
                    if next_hrv > 0 and next_sleep > 0:
                        composite = (next_hrv / 80.0) * 50 + (min(next_sleep, 9) / 9.0) * 50
                    if composite > 0:
                        rest_groups.setdefault(rest_count, []).append(composite)
            else:
                i += 1

        avg_by_rest: Dict[int, float] = {}
        for k, vs in rest_groups.items():
            if vs:
                avg_by_rest[k] = statistics.mean(vs)

        best_rest = max(avg_by_rest, key=avg_by_rest.get) if avg_by_rest else 0
        best_score = avg_by_rest.get(best_rest, 0)

        return {
            "optimal_rest_days": best_rest,
            "average_readiness_after": round(best_score, 1),
            "breakdown": {str(k): round(v, 1) for k, v in sorted(avg_by_rest.items())},
        }

    @staticmethod
    def _find_best_training_window(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        hour_rpe: Dict[int, List[float]] = {}
        for row in data:
            for w in row["workouts"]:
                h = w.get("hour") or 0
                rpe = w.get("rpe") or 0
                if h > 0 and rpe > 0:
                    hour_rpe.setdefault(h, []).append(rpe)

        if not hour_rpe:
            return {"best_hour": None, "message": "Sin datos de hora de entrenamiento"}

        avg_by_hour = {h: statistics.mean(rpes) for h, rpes in hour_rpe.items() if rpes}
        if not avg_by_hour:
            return {"best_hour": None, "message": "Sin datos de hora de entrenamiento"}

        best_hour = min(avg_by_hour, key=avg_by_hour.get)
        avg_rpe = round(avg_by_hour[best_hour], 1)

        return {
            "best_hour": best_hour,
            "best_hour_label": f"{best_hour:02d}:00 - {best_hour + 1:02d}:00",
            "avg_rpe_at_best": avg_rpe,
            "all_hours": {str(h): round(r, 1) for h, r in sorted(avg_by_hour.items())},
        }

    @staticmethod
    def _generate_correlation_insights(
        correlations: Dict[str, Any],
        data: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        insights: List[Dict[str, Any]] = []

        s2h = correlations.get("sleep_to_hrv", {})
        r = s2h.get("r")
        if r is not None and abs(r) >= 0.2:
            sleep_vals = [d["sleep"] for d in data if d["sleep"] > 0]
            if sleep_vals:
                threshold = statistics.median(sleep_vals)
                high_sleep_hrv = [d["hrv"] for d in data if d["sleep"] > threshold and d["hrv"] > 0]
                low_sleep_hrv = [d["hrv"] for d in data if 0 < d["sleep"] <= threshold and d["hrv"] > 0]
                if high_sleep_hrv and low_sleep_hrv:
                    pct = round(((statistics.mean(high_sleep_hrv) / statistics.mean(low_sleep_hrv)) - 1) * 100, 0)
                    direction = "sube" if pct > 0 else "baja"
                    insights.append({
                        "id": "sleep_hrv",
                        "importance": "alta" if abs(r) >= 0.5 else "media",
                        "text": f"Cuando duermes más de {threshold:.1f}h, tu HRV al día siguiente {direction} un {abs(pct):.0f}% de media.",
                        "correlation_r": round(r, 3),
                    })

        h2p = correlations.get("hrv_to_performance", {})
        r = h2p.get("r")
        if r is not None and abs(r) >= 0.2:
            direction = "mejor" if r > 0 else "peor"
            insights.append({
                "id": "hrv_performance",
                "importance": "alta" if abs(r) >= 0.5 else "media",
                "text": f"Los días con HRV alto, tus entrenamientos tienen RPE {direction} (correlación {abs(r):.2f}).",
                "correlation_r": round(r, 3),
            })

        rest = correlations.get("rest_days_to_readiness", {})
        opt = rest.get("optimal_rest_days", 0)
        if opt > 0:
            insights.append({
                "id": "rest_optimal",
                "importance": "alta",
                "text": f"Necesitas exactamente {opt} día{'s' if opt > 1 else ''} de descanso para maximizar tu recuperación.",
                "correlation_r": None,
            })

        bt = correlations.get("best_training_time", {})
        bh = bt.get("best_hour")
        if bh is not None:
            insights.append({
                "id": "best_time",
                "importance": "media",
                "text": f"Tus mejores entrenamientos ocurren entre las {bh:02d}:00 y las {bh + 1:02d}:00h.",
                "correlation_r": None,
            })

        return insights[:5]

    @staticmethod
    def forecast_readiness(db: Session, user_id: str, days_ahead: int = 3) -> Dict[str, Any]:
        from app.services.readiness_service import ReadinessService

        end = date.today()
        start = end - timedelta(days=30)

        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= start.isoformat(),
        ).order_by(Biometrics.date).all()

        base_score = ReadinessService.calculate(db, user_id).get("score", 50)

        history: List[float] = []
        weekday_scores: Dict[int, List[float]] = {}
        unique_dates: set = set()

        for bio in bios:
            try:
                d = json.loads(bio.data)
                hrv = d.get("hrv") or 0
                sleep = d.get("sleep") or 0
                hr = d.get("heartRate") or 0
                if hrv > 0 or sleep > 0:
                    bio_hrv = hrv
                    bio_sleep = sleep
                    delta = 0.0
                    if bio_hrv > 0:
                        hrv_baseline = AnalyticsService.get_hrv_baseline(db, user_id, days=7)
                        if hrv_baseline > 0:
                            delta += (bio_hrv - hrv_baseline) / hrv_baseline * 10
                    if bio_sleep > 0:
                        delta += (bio_sleep - 7.0) * 2
                    score = _clamp(base_score + delta, 0, 100)
                    history.append(float(round(score)))

                    b_date = bio.date
                    if isinstance(b_date, str):
                        wd = date.fromisoformat(b_date).weekday()
                    elif hasattr(b_date, "weekday"):
                        wd = b_date.weekday()
                    else:
                        continue
                    weekday_scores.setdefault(wd, []).append(float(round(score)))
                    unique_dates.add(b_date if isinstance(b_date, str) else b_date.isoformat())
            except Exception:
                continue

        unique_days = len(unique_dates)

        if unique_days < 7:
            return {
                "status": "accumulating",
                "days_available": unique_days,
                "message": f"Acumulando datos... {unique_days}/7 días necesarios para predicción.",
                "forecasts": [],
            }

        if not history:
            history = [50.0]

        weekday_avg: Dict[int, float] = {}
        for wd, scores in weekday_scores.items():
            if scores:
                weekday_avg[wd] = statistics.mean(scores)

        overall_mean = statistics.mean(history) if history else 50.0
        for wd in range(7):
            if wd not in weekday_avg:
                weekday_avg[wd] = overall_mean

        trend = _linear_slope(history[-7:]) if len(history) >= 7 else 0.0
        smoothed = _ewma(history, alpha=0.3)
        base = smoothed[-1] if smoothed else overall_mean

        forecasts: List[Dict[str, Any]] = []
        today = date.today()
        for day_offset in range(1, days_ahead + 1):
            target_date = today + timedelta(days=day_offset)
            target_wd = target_date.weekday()
            wd_effect = weekday_avg.get(target_wd, overall_mean) - overall_mean
            predicted = base + trend * day_offset + wd_effect
            predicted = _clamp(predicted, 0, 100)
            confidence = max(0.3, 1.0 - (day_offset - 1) * 0.25)
            if len(history) < 14:
                confidence *= 0.6
            forecasts.append({
                "date": target_date.isoformat(),
                "weekday": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][target_wd],
                "predicted_score": round(predicted),
                "confidence": round(confidence, 2),
            })

        return {
            "status": "ok",
            "days_analyzed": unique_days,
            "forecasts": forecasts,
        }

    @staticmethod
    def detect_plateau(db: Session, user_id: str, exercise_name: Optional[str] = None, weeks: int = 6) -> Dict[str, Any]:
        end = date.today()
        start = end - timedelta(weeks=weeks)

        query = db.query(PersonalRecord).filter(
            PersonalRecord.user_id == user_id,
            PersonalRecord.date >= start.isoformat(),
        )
        if exercise_name:
            query = query.filter(PersonalRecord.exercise_name == exercise_name)

        prs = query.order_by(PersonalRecord.date).all()

        if not prs:
            return {
                "status": "no_data",
                "message": "No hay registros de entrenamiento en este periodo.",
                "plateaus": [],
            }

        by_exercise: Dict[str, List[Dict[str, Any]]] = {}
        for pr in prs:
            by_exercise.setdefault(pr.exercise_name, []).append({
                "date": pr.date,
                "weight": pr.weight,
                "reps": pr.reps,
            })

        plateaus: List[Dict[str, Any]] = []
        for ex_name, entries in by_exercise.items():
            if len(entries) < 4:
                continue
            weights = [e["weight"] for e in entries]
            slope = _linear_slope([float(w) for w in weights])
            max_w = max(weights)
            stagnant = sum(1 for w in weights if w == max_w)
            weeks_stagnant = max(1, stagnant // 2)

            if abs(slope) < 0.5:
                plateaus.append({
                    "exercise": ex_name,
                    "weeks_stagnant": weeks_stagnant,
                    "current_weight": max_w,
                    "slope_per_week": round(slope, 2),
                    "suggestion": AnalyticsService._plateau_suggestion(ex_name, entries),
                })

        if exercise_name and not plateaus:
            return {
                "status": "progressing",
                "message": f"{exercise_name} está progresando correctamente.",
                "plateaus": [],
            }

        return {
            "status": "ok",
            "plateaus": plateaus,
        }

    @staticmethod
    def _plateau_suggestion(exercise: str, entries: List[Dict[str, Any]]) -> str:
        variants: Dict[str, List[str]] = {
            "Bench Press": ["Incline Dumbbell Press", "Close-Grip Bench", "Paused Bench"],
            "Squat": ["Front Squat", "Bulgarian Split Squat", "Pause Squat"],
            "Deadlift": ["Romanian Deadlift", "Sumo Deadlift", "Deficit Deadlift"],
            "Overhead Press": ["Push Press", "Dumbbell Shoulder Press", "Z Press"],
            "Barbell Row": ["Pendlay Row", "Dumbbell Row", "T-Bar Row"],
        }
        ex_lower = exercise.lower()
        variant_list = []
        for key, vs in variants.items():
            if key.lower() in ex_lower or ex_lower in key.lower():
                variant_list = vs
                break

        if variant_list:
            return f"Estancado en {exercise}. Prueba: {', '.join(variant_list[:2])}. O considera un deload del 10% y progresa de nuevo."

        return f"Estancado en {exercise}. Considera: cambiar variante, técnica de intensidad (rest-pause, drop-sets), o deload del 10%."

    @staticmethod
    def find_optimal_volume(db: Session, user_id: str) -> Dict[str, Any]:
        end = date.today()
        start = end - timedelta(days=84)  # 12 weeks

        bios = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= start.isoformat(),
        ).order_by(Biometrics.date).all()

        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date >= start,
        ).order_by(Workout.date).all()

        bio_map: Dict[str, float] = {}
        for bio in bios:
            try:
                d = json.loads(bio.data)
                hrv = d.get("hrv") or 0
                sleep = d.get("sleep") or 0
                if hrv > 0:
                    bio_map[bio.date if isinstance(bio.date, str) else bio.date.isoformat()] = float(hrv)
            except Exception:
                continue

        week_data: Dict[str, Dict[str, Any]] = {}
        for w in workouts:
            d_str = w.date.isoformat() if hasattr(w.date, "isoformat") else str(w.date)
            from datetime import datetime as _dt
            try:
                d_obj = _dt.fromisoformat(d_str).date() if "T" not in d_str else _dt.fromisoformat(d_str).date()
            except Exception:
                continue
            week_start = (d_obj - timedelta(days=d_obj.weekday())).isoformat()
            dur = (w.duration or 0) / 60
            entry = week_data.setdefault(week_start, {"total_min": 0, "sessions": 0, "hrvs_after": []})
            entry["total_min"] += dur
            entry["sessions"] += 1

        for w_start, entry in week_data.items():
            ws_date = date.fromisoformat(w_start)
            for offset in range(5, 8):
                check_date = (ws_date + timedelta(days=offset)).isoformat()
                if check_date in bio_map:
                    entry["hrvs_after"].append(bio_map[check_date])

        if len(week_data) < 3:
            return {
                "status": "accumulating",
                "weeks_available": len(week_data),
                "message": f"Acumulando datos... {len(week_data)}/3 semanas necesarias.",
            }

        volume_hrv: List[Tuple[float, float]] = []
        for entry in week_data.values():
            if entry["hrvs_after"] and entry["total_min"] > 0:
                avg_hrv_after = statistics.mean(entry["hrvs_after"])
                volume_hrv.append((entry["total_min"], avg_hrv_after))

        if len(volume_hrv) < 3:
            return {
                "status": "insufficient_variation",
                "message": "Necesitas más variación en volumen para encontrar tu punto dulce.",
                "optimal_volume_min": None,
            }

        vols = [v for v, _ in volume_hrv]
        hrvs = [h for _, h in volume_hrv]

        best_idx = hrvs.index(max(hrvs))
        optimal_vol = vols[best_idx]

        return {
            "status": "ok",
            "optimal_volume_min": round(optimal_vol),
            "optimal_sessions_per_week": round(week_data[list(week_data.keys())[best_idx]]["sessions"]) if week_data else 3,
            "message": f"Tu volumen óptimo semanal es ~{round(optimal_vol)}min. Por encima, tu recuperación sufre.",
            "data_points": len(volume_hrv),
        }

    @staticmethod
    def get_monthly_insights(db: Session, user_id: str) -> Dict[str, Any]:
        import time as _time

        cache_key = f"insights_{user_id}"
        cached = _insight_cache.get(cache_key)
        if cached and (_time.time() - cached["ts"]) < INSIGHT_CACHE_TTL:
            return cached["data"]

        corr = AnalyticsService.find_personal_correlations(db, user_id, days=90)
        plateau = AnalyticsService.detect_plateau(db, user_id)
        volume = AnalyticsService.find_optimal_volume(db, user_id)

        top_insights: List[Dict[str, Any]] = list(corr.get("insights", []))

        for p in plateau.get("plateaus", []):
            top_insights.append({
                "id": f"plateau_{p['exercise']}",
                "importance": "alta",
                "text": f"Tu {p['exercise']} lleva {p['weeks_stagnant']} semana{'s' if p['weeks_stagnant'] > 1 else ''} estancado en {p['current_weight']}kg — posible plateau.",
                "suggestion": p.get("suggestion"),
            })

        if volume.get("status") == "ok" and volume.get("optimal_volume_min"):
            top_insights.append({
                "id": "optimal_volume",
                "importance": "media",
                "text": f"Tu volumen óptimo semanal es ~{volume['optimal_volume_min']}min de entrenamiento.",
            })

        top_insights = sorted(top_insights, key=lambda x: 0 if x.get("importance") == "alta" else 1)[:5]

        result = {
            "status": "ok",
            "generated_at": datetime.now().isoformat(),
            "insights": top_insights,
            "correlations_summary": corr.get("correlations", {}),
            "plateaus": plateau.get("plateaus", []),
            "optimal_volume": volume,
        }

        _insight_cache[cache_key] = {"data": result, "ts": _time.time()}
        return result
