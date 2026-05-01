"""
ATLAS Readiness Score v2
=========================

Adaptive Personal Baseline Algorithm v2:
- Learns personal baseline from 30-day history
- Adaptive weights based on data availability
- Training load penalty to prevent overtraining
- Personalized recommendations

Components:
- HRV: 35% weight (relative to personal baseline)
- Sleep: 25% weight (absolute scale)
- Stress: 20% weight (inverted)
- Resting HR: 20% weight (relative to personal baseline)
- Training Load: Penalty factor for high volume weeks

Output: ReadinessResult with score, status, recommendation, components

Autor: ATLAS Team
Version: 2.0.0
"""

import json
import logging
import statistics
from datetime import date, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.models.biometrics import Biometrics

logger = logging.getLogger("app.services.readiness")


@dataclass
class PersonalBaseline:
    """Personal baseline metrics calculated from history."""
    hrv_mean: float = 0.0
    hrv_std: float = 0.0
    sleep_mean: float = 0.0
    rhr_mean: float = 0.0
    stress_mean: float = 0.0
    days_available: int = 0


@dataclass
class ReadinessResult:
    """Complete readiness assessment result."""
    score: int
    status: str
    recommendation: str
    component_scores: Dict[str, float]
    baseline_used: PersonalBaseline
    overtraining_risk: bool


class ReadinessService:
    """
    Calculate athlete readiness score v2 with adaptive personal baseline.
    
    The v2 algorithm learns each athlete's normal ranges and adjusts
    scoring accordingly, providing truly personalized readiness assessment.
    
    Algorithm v2:
    1. Calculate personal baselines from 30-day history
    2. Score individual components normalized 0-100:
       - HRV (relative to baseline)
       - Sleep (absolute scale)
       - Stress (inverted)
       - Resting HR (relative to baseline)
       - Training load (last 7 days)
    3. Adaptive weights based on data availability
    4. Weighted final score with load penalty
    5. Generate personalized recommendation
    """

    # Base weights (will be renormalized if data is missing)
    BASE_WEIGHTS = {
        'hrv': 0.35,
        'sleep': 0.25,
        'stress': 0.20,
        'rhr': 0.20,
    }

    @classmethod
    def calculate(cls, db: Session, user_id: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive readiness score v2.
        
        Args:
            db: Database session
            user_id: User ID
            date_str: Target date (YYYY-MM-DD), defaults to today
            
        Returns:
            Complete readiness result as dictionary
        """
        target_date = date_str or date.today().isoformat()
        
        # Fetch today's biometrics
        row = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == target_date
        ).first()
        
        if not row or not row.data:
            return {
                "score": None,
                "status": "no_data",
                "recommendation": "No hay datos disponibles. Sincroniza tu dispositivo.",
                "components": {},
                "baseline": {},
                "overtraining_risk": False,
                "date": target_date,
            }
        
        try:
            data = json.loads(row.data)
        except json.JSONDecodeError:
            return {
                "score": None,
                "status": "invalid_data",
                "recommendation": "Error en datos biométricos.",
                "date": target_date,
            }
        
        # Calculate personal baseline from 30-day history
        baseline = cls._calculate_personal_baseline(db, user_id, days=30)
        
        # Extract today's metrics
        hrv = data.get("hrv")
        sleep = data.get("sleep")
        stress = data.get("stress")
        rhr = data.get("heartRate")
        
        # Calculate individual component scores
        hrv_score = cls._score_hrv(hrv, baseline.hrv_mean, baseline.hrv_std) if hrv else 0.0
        sleep_score = cls._score_sleep(sleep, baseline.sleep_mean) if sleep else 0.0
        stress_score = cls._score_stress(stress) if stress is not None else 0.0
        rhr_score = cls._score_rhr(rhr, baseline.rhr_mean, baseline.rhr_std) if rhr else 0.0
        
        # Calculate training load score
        load_score = cls._score_training_load(db, user_id, days=7)
        
        # Determine adaptive weights based on data availability
        available_weights = {}
        component_scores = {}
        
        if hrv and baseline.hrv_mean > 0:
            available_weights['hrv'] = cls.BASE_WEIGHTS['hrv']
            component_scores['hrv'] = round(hrv_score, 1)
        
        if sleep:
            available_weights['sleep'] = cls.BASE_WEIGHTS['sleep']
            component_scores['sleep'] = round(sleep_score, 1)
        
        if stress is not None:
            available_weights['stress'] = cls.BASE_WEIGHTS['stress']
            component_scores['stress'] = round(stress_score, 1)
        
        if rhr and baseline.rhr_mean > 0:
            available_weights['rhr'] = cls.BASE_WEIGHTS['rhr']
            component_scores['rhr'] = round(rhr_score, 1)
        
        # Renormalize weights if some data is missing
        total_weight = sum(available_weights.values())
        if total_weight == 0:
            # No baseline data available - fall back to generic scoring
            available_weights = cls.BASE_WEIGHTS.copy()
            total_weight = sum(available_weights.values())
        
        normalized_weights = {k: v / total_weight for k, v in available_weights.items()}

        # Calculate weighted score (load_score excluded - it uses inverted scale, only penalty applied below)
        raw_score = (
            component_scores.get("hrv", 0) * normalized_weights.get("hrv", 0) +
            component_scores.get("sleep", 0) * normalized_weights.get("sleep", 0) +
            component_scores.get("stress", 0) * normalized_weights.get("stress", 0) +
            component_scores.get("rhr", 0) * normalized_weights.get("rhr", 0)
        )

        component_scores["load"] = round(load_score, 1)

        # Penalizacion por carga acumulada (evitar sobreentrenamiento)
        # load_score: 0-40 = very high load (bad), 60-100 = low load (good)
        # Invert for penalty: high_load_penalty = (40 - load_score) / 40
        if load_score < 40:
            high_load_penalty = 1.0 - (load_score / 40)
            raw_score *= (1.0 - high_load_penalty * 0.5)  # up to -50% for extreme load
        elif load_score > 80:
            raw_score *= 0.85  # light overtraining signal bonus
        
        final_score = round(max(0, min(100, raw_score)))
        status = cls._score_to_status(final_score)
        
        # Determine overtraining risk
        overtraining_risk = (
            load_score > 85 or
            (hrv_score < 30 and baseline.hrv_mean > 0) or
            (rhr_score < 30 and baseline.rhr_mean > 0) or
            (load_score > 80 and final_score < 40)
        )
        
        # Generate personalized recommendation
        recommendation = cls._generate_recommendation(final_score, data, baseline, component_scores)
        
        return {
            "score": final_score,
            "status": status,
            "recommendation": recommendation,
            "components": component_scores,
            "baseline": {
                "hrv_mean": round(baseline.hrv_mean, 1) if baseline.hrv_mean > 0 else None,
                "hrv_std": round(baseline.hrv_std, 1) if baseline.hrv_std > 0 else None,
                "rhr_mean": round(baseline.rhr_mean, 1) if baseline.rhr_mean > 0 else None,
                "rhr_std": round(baseline.rhr_std, 1) if baseline.rhr_std > 0 else None,
                "sleep_mean": round(baseline.sleep_mean, 1) if baseline.sleep_mean > 0 else None,
                "stress_mean": round(baseline.stress_mean, 1) if baseline.stress_mean > 0 else None,
                "days_available": baseline.days_available,
            },
            "overtraining_risk": overtraining_risk,
            "date": target_date,
        }

    @classmethod
    def _calculate_personal_baseline(
        cls, db: Session, user_id: str, days: int = 30
    ) -> PersonalBaseline:
        """
        Calculate personal baseline from historical data.
        
        Uses the last N days of biometrics to establish what's
        "normal" for this specific athlete.
        """
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).order_by(Biometrics.date.desc()).limit(days).all()
        
        hrv_values = []
        sleep_values = []
        rhr_values = []
        stress_values = []
        
        for row in rows:
            if not row.data:
                continue
            try:
                data = json.loads(row.data)
                
                if (hrv := data.get("hrv")) and hrv > 0:
                    hrv_values.append(float(hrv))
                if (sleep := data.get("sleep")) and sleep > 0:
                    sleep_values.append(float(sleep))
                if (rhr := data.get("heartRate")) and rhr > 0:
                    rhr_values.append(float(rhr))
                if (stress := data.get("stress")) and stress > 0:
                    stress_values.append(float(stress))
                    
            except (json.JSONDecodeError, ValueError):
                continue
        
        baseline = PersonalBaseline(days_available=len(rows))
        
        # Calculate statistics for each metric
        if len(hrv_values) >= 7:
            baseline.hrv_mean = statistics.mean(hrv_values)
            if len(hrv_values) >= 2:
                baseline.hrv_std = statistics.stdev(hrv_values)
        
        if len(sleep_values) >= 7:
            baseline.sleep_mean = statistics.mean(sleep_values)
        
        if len(rhr_values) >= 7:
            baseline.rhr_mean = statistics.mean(rhr_values)
            if len(rhr_values) >= 2:
                baseline.rhr_std = statistics.stdev(rhr_values)
        
        if len(stress_values) >= 7:
            baseline.stress_mean = statistics.mean(stress_values)
        
        return baseline

    @staticmethod
    def _score_hrv(hrv: float, baseline_mean: float, baseline_std: float) -> float:
        """
        Score HRV relative to personal baseline.
        
        Higher HRV = better recovery. Score based on how many
        standard deviations above/below the mean.
        """
        if baseline_mean <= 0:
            # No baseline - use absolute scale
            if hrv >= 70:
                return 100.0
            elif hrv >= 55:
                return 80.0
            elif hrv >= 40:
                return 60.0
            return 30.0
        
        if baseline_std <= 0:
            baseline_std = baseline_mean * 0.1  # Assume 10% variability
        
        # Score based on z-score
        z_score = (hrv - baseline_mean) / baseline_std
        
        if z_score >= 1.0:
            return 100.0  # Exceptional
        elif z_score >= 0.5:
            return 90.0   # Very good
        elif z_score >= 0:
            return 80.0   # Good (above average)
        elif z_score >= -0.5:
            return 60.0   # Below average
        elif z_score >= -1.0:
            return 40.0   # Poor
        else:
            return 20.0   # Very poor (possible overtraining)

    @staticmethod
    def _score_sleep(hours: float, baseline_mean: float = 0) -> float:
        """
        Score sleep duration.
        
        Optimal: 7-9 hours
        Penalty for < 6 hours
        """
        if hours >= 8.0:
            return 100.0
        elif hours >= 7.0:
            return 85.0 + (hours - 7.0) * 15.0
        elif hours >= 6.0:
            return 60.0 + (hours - 6.0) * 25.0
        elif hours >= 5.0:
            return 30.0 + (hours - 5.0) * 30.0
        elif hours >= 4.0:
            return 10.0 + (hours - 4.0) * 20.0
        else:
            return max(0, hours / 4.0 * 10.0)

    @staticmethod
    def _score_stress(stress: float, baseline_mean: float = 0) -> float:
        """
        Score stress level (inverted - lower is better).
        """
        if stress <= 20:
            return 100.0
        elif stress <= 35:
            return 80.0 - (stress - 20) * 1.33
        elif stress <= 50:
            return 60.0 - (stress - 35) * 1.33
        elif stress <= 70:
            return 40.0 - (stress - 50) * 1.0
        else:
            return max(0, 20.0 - (stress - 70) * 0.5)

    @staticmethod
    def _score_rhr(rhr: float, baseline_mean: float, baseline_std: float) -> float:
        """
        Score resting heart rate relative to personal baseline.
        
        Lower RHR is better (lower score is better for RHR, but we invert for readiness).
        """
        if baseline_mean <= 0:
            # No baseline - use absolute scale
            if rhr <= 50:
                return 100.0
            elif rhr <= 60:
                return 80.0
            elif rhr <= 70:
                return 60.0
            elif rhr <= 80:
                return 40.0
            return 20.0
        
        if baseline_std <= 0:
            baseline_std = baseline_mean * 0.05  # Assume 5% variability
        
        # Lower RHR is better (negative z-score is good)
        z_score = (rhr - baseline_mean) / baseline_std
        
        if z_score <= -1.0:
            return 100.0  # Exceptional
        elif z_score <= -0.5:
            return 90.0
        elif z_score <= 0:
            return 80.0  # At or below baseline
        elif z_score <= 0.5:
            return 60.0  # Slightly elevated
        elif z_score <= 1.0:
            return 40.0  # Elevated
        elif z_score <= 1.5:
            return 20.0  # Very elevated (possible fatigue)
        else:
            return 10.0  # Critically elevated

    @staticmethod
    def _score_training_load(
        db: Session, user_id: str, days: int = 7
    ) -> float:
        """
        Calculate training load score for the last N days.
        
        Returns 0-100 score where:
        - 0-40: Very high load (risk of overtraining)
        - 40-60: High load 
        - 60-80: Moderate/optimal load
        - 80-100: Low load (undertraining or recovery week)
        """
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).all()
        
        total_duration = 0
        active_days = 0
        
        for row in rows:
            if not row.data:
                continue
            try:
                data = json.loads(row.data)
                duration = data.get("workout_duration", 0) or 0
                
                if duration > 0:
                    total_duration += duration
                    active_days += 1
                    
            except (json.JSONDecodeError, ValueError):
                continue
        
        if active_days == 0:
            return 100.0  # No training = low load (recovery)
        
        # Calculate average daily training duration in hours
        avg_daily_hours = total_duration / days / 60
        
        # Score based on volume
        # Healthy range: 0.5-2.0 hours/day on average (30-120 min)
        if avg_daily_hours < 0.5:  # < 30 min average
            return 100.0  # Very low load (recovery week)
        elif avg_daily_hours < 1.0:  # 30-60 min
            return 90.0
        elif avg_daily_hours < 1.5:  # 60-90 min
            return 80.0  # Optimal range
        elif avg_daily_hours < 2.0:  # 90-120 min
            return 60.0  # Moderate-high
        elif avg_daily_hours < 3.0:  # 120-180 min
            return 40.0  # High load
        else:  # > 3 hours average
            return 20.0  # Very high load (overtraining risk)

    @staticmethod
    def _score_to_status(score: int) -> str:
        """Convert numeric score to status string."""
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "moderate"
        elif score >= 30:
            return "poor"
        return "rest"

    @staticmethod
    def _generate_recommendation(
        score: int, data: Dict, baseline: PersonalBaseline, components: Optional[Dict[str, float]] = None
    ) -> str:
        load_score = components.get("load", 50) if components else 50
        if load_score < 40:
            return "Día de descanso total. Tu cuerpo lo necesita para progresar."

        if score >= 85:
            return "Día óptimo para entrenamiento de alta intensidad. Tu cuerpo está en peak."
        elif score >= 70:
            return "Buen día para entrenar. Puedes trabajar al 80-90% de tu capacidad."
        elif score >= 50:
            return "Entrenamiento moderado recomendado. Evita volumen máximo hoy."
        elif score >= 30:
            return "Recuperación activa: movilidad, caminata o yoga. No fuerces."
        else:
            return "Día de descanso total. Tu cuerpo lo necesita para progresar."

    @classmethod
    def get_trend(
        cls, db: Session, user_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get readiness trend for the last N days.
        
        Returns list of daily readiness scores.
        """
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).order_by(Biometrics.date.asc()).all()
        
        trend = []
        for row in rows:
            result = cls.calculate(db, user_id, row.date)
            if result.get("score") is not None:
                trend.append({
                    "date": row.date,
                    "score": result["score"],
                    "status": result["status"],
                    "overtraining_risk": result["overtraining_risk"],
                })
        
        return trend

    @classmethod
    def get_forecast(
        cls, db: Session, user_id: str, days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate simple readiness forecast for next N days.
        
        Based on current trend and training load.
        This is a basic projection - not a sophisticated ML model.
        """
        # Get current readiness
        today_result = cls.calculate(db, user_id)
        
        if today_result.get("score") is None:
            return []
        
        current_score = today_result["score"]
        load_score = today_result["components"].get("load", 50)
        
        # Get trend from last 7 days
        trend = cls.get_trend(db, user_id, days=7)
        
        # Calculate trend direction
        if len(trend) >= 3:
            recent_scores = [t["score"] for t in trend[-3:]]
            trend_direction = statistics.mean(recent_scores) - current_score
        else:
            trend_direction = 0
        
        # Generate forecast
        forecast = []
        for i in range(1, days + 1):
            # Simple projection: current score + trend - load decay
            # High load days tend to have lower readiness the next day
            projected_score = current_score + (trend_direction * i * 0.3)
            
            # Training load decay factor
            if load_score > 80:  # Very high load (note: inverted scale, >80 = low load)
                projected_score += (3 * i)  # +3 per day with rest
            elif load_score < 40:  # Very high load (<40 is high load)
                projected_score -= (5 * i)  # -5 per day after heavy load
            elif load_score < 60:
                projected_score -= (2 * i)  # -2 per day after moderate load
            
            projected_score = max(0, min(100, round(projected_score)))
            
            # Determine status
            status = cls._score_to_status(projected_score)
            
            # Generate recommendation based on forecast
            if projected_score >= 70:
                rec = "Proyección favorable para entrenamiento"
            elif projected_score >= 50:
                rec = "Entrenamiento moderado recomendado"
            else:
                rec = "Recuperación activa recomendada"
            
            forecast_date = (date.today() + timedelta(days=i)).isoformat()
            
            forecast.append({
                "date": forecast_date,
                "score": projected_score,
                "status": status,
                "recommendation": rec,
                "confidence": round(max(0.3, 1.0 - (i * 0.2)), 2),
            })
        
        return forecast

    @classmethod
    def calculate_and_store(cls, db: Session, user_id: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate readiness and store result in daily_briefings table.
        
        Args:
            db: Database session
            user_id: User ID
            date_str: Target date (YYYY-MM-DD), defaults to today
            
        Returns:
            Readiness result dictionary
        """
        result = cls.calculate(db, user_id, date_str)
        
        # Store in daily_briefings table if we have a score
        if result.get("score") is not None:
            try:
                from app.models.daily_briefing import DailyBriefing
                from datetime import date as date_type
                
                target_date = date_str or date.today().isoformat()
                existing = db.query(DailyBriefing).filter(
                    DailyBriefing.user_id == user_id,
                    DailyBriefing.date == target_date
                ).first()
                
                import json
                content = json.dumps({
                    "readiness_score": result["score"],
                    "status": result["status"],
                    "recommendation": result["recommendation"],
                    "components": result.get("components", {})
                })
                
                if existing:
                    existing.content = content
                else:
                    briefing = DailyBriefing(
                        id=f"{user_id}_{target_date}",
                        user_id=user_id,
                        date=target_date,
                        content=content
                    )
                    db.add(briefing)
                
                db.commit()
                logger.info(f"Stored readiness for user {user_id} on {target_date}")
            except Exception as e:
                logger.error(f"Error storing readiness: {e}", exc_info=True)
        
        return result