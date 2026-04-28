"""
ATLAS Readiness Score v1
=========================

Algorithm:
- HRV:        35% weight (compare with 30-day personal baseline)
- Sleep:      25% weight (< 6h penalty, > 8h bonus)
- Stress:     20% weight (inverted, lower is better)
- Resting HR: 20% weight (compare with 30-day personal baseline)

Output: score 0-100 with status excellent/good/moderate/poor/rest.

Autor: ATLAS Team
"""

import json
import logging
import statistics
from datetime import date, timedelta
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session

from app.models.biometrics import Biometrics

logger = logging.getLogger("app.services.readiness")


class ReadinessService:
    """Calculate athlete readiness score from biometric data."""

    HRV_WEIGHT = 0.35
    SLEEP_WEIGHT = 0.25
    STRESS_WEIGHT = 0.20
    RHR_WEIGHT = 0.20

    @staticmethod
    def get_baseline(
        db: Session,
        user_id: str,
        metric_key: str,
        days: int = 30
    ) -> Optional[float]:
        """Calculate personal baseline (median) for a metric over N days."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).all()

        values = []
        for row in rows:
            try:
                data = json.loads(row.data) if row.data else {}
                val = data.get(metric_key)
                if val is not None:
                    values.append(float(val))
            except (json.JSONDecodeError, ValueError):
                continue

        if len(values) < 7:
            return None

        return statistics.median(values)

    @staticmethod
    def _hrv_score(hrv: float, baseline: Optional[float]) -> float:
        """HRV score: higher HRV relative to baseline is better."""
        if not baseline or baseline <= 0:
            # No baseline: use absolute scale
            if hrv >= 70:
                return 100.0
            elif hrv >= 55:
                return 80.0
            elif hrv >= 40:
                return 60.0
            else:
                return 30.0

        ratio = hrv / baseline
        if ratio >= 1.15:
            return 100.0
        elif ratio >= 1.0:
            return 80.0 + (ratio - 1.0) * 133.0  # 1.0->80, 1.15->100
        elif ratio >= 0.85:
            return 60.0 + (ratio - 0.85) * 133.0  # 0.85->60, 1.0->80
        elif ratio >= 0.70:
            return 30.0 + (ratio - 0.70) * 200.0  # 0.70->30, 0.85->60
        else:
            return max(0, ratio / 0.70 * 30.0)

    @staticmethod
    def _sleep_score(hours: float) -> float:
        """Sleep score: optimal 7-9h, penalize < 6h, cap at 9h."""
        if hours >= 8.0:
            return 100.0
        elif hours >= 7.0:
            return 85.0 + (hours - 7.0) * 15.0  # 7.0->85, 8.0->100
        elif hours >= 6.0:
            return 60.0 + (hours - 6.0) * 25.0  # 6.0->60, 7.0->85
        elif hours >= 5.0:
            return 30.0 + (hours - 5.0) * 30.0  # 5.0->30, 6.0->60
        elif hours >= 4.0:
            return 10.0 + (hours - 4.0) * 20.0  # 4.0->10, 5.0->30
        else:
            return max(0, hours / 4.0 * 10.0)

    @staticmethod
    def _stress_score(stress: float) -> float:
        """Stress score: inverted, lower stress is better."""
        if stress <= 20:
            return 100.0
        elif stress <= 35:
            return 80.0 - (stress - 20) * 1.33  # 20->100, 35->60
        elif stress <= 50:
            return 60.0 - (stress - 35) * 1.33  # 35->60, 50->40
        elif stress <= 70:
            return 40.0 - (stress - 50) * 1.0   # 50->40, 70->20
        else:
            return max(0, 20.0 - (stress - 70) * 0.5)

    @staticmethod
    def _rhr_score(rhr: float, baseline: Optional[float]) -> float:
        """Resting HR score: lower RHR relative to baseline is better."""
        if not baseline or baseline <= 0:
            if rhr <= 50:
                return 100.0
            elif rhr <= 60:
                return 80.0
            elif rhr <= 70:
                return 60.0
            elif rhr <= 80:
                return 40.0
            else:
                return 20.0

        ratio = rhr / baseline
        if ratio <= 0.90:
            return 100.0
        elif ratio <= 1.0:
            return 80.0 + (1.0 - ratio) * 200.0  # 0.90->100, 1.0->80
        elif ratio <= 1.10:
            return 60.0 + (1.10 - ratio) * 200.0  # 1.0->80, 1.10->60
        elif ratio <= 1.25:
            return 30.0 + (1.25 - ratio) * 200.0  # 1.10->60, 1.25->30
        else:
            return max(0, 30.0 - (ratio - 1.25) * 60.0)

    @staticmethod
    def calculate(
        db: Session,
        user_id: str,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate readiness score for a given date (default: today)."""
        target_date = date_str or date.today().isoformat()

        # Fetch today's biometrics
        row = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == target_date
        ).first()

        if not row or not row.data:
            logger.warning(f"No biometrics data for {user_id} on {target_date}")
            return {
                "score": None,
                "status": "no_data",
                "components": {},
                "baseline_days": 0,
                "date": target_date,
            }

        try:
            data = json.loads(row.data)
        except json.JSONDecodeError:
            return {"score": None, "status": "invalid_data", "date": target_date}

        # Get baselines
        hrv_baseline = ReadinessService.get_baseline(db, user_id, "hrv", days=30)
        rhr_baseline = ReadinessService.get_baseline(db, user_id, "heartRate", days=30)

        # Count available baseline days
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        baseline_rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).count()

        # Extract metrics
        hrv = data.get("hrv")
        sleep = data.get("sleep")
        stress = data.get("stress")
        rhr = data.get("heartRate")

        # Calculate component scores (0-100 each)
        hrv_score = ReadinessService._hrv_score(hrv, hrv_baseline) if hrv is not None else None
        sleep_score = ReadinessService._sleep_score(sleep) if sleep is not None else None
        stress_score = ReadinessService._stress_score(stress) if stress is not None else None
        rhr_score = ReadinessService._rhr_score(rhr, rhr_baseline) if rhr is not None else None

        components = {
            "hrv": {"value": hrv, "score": hrv_score, "weight": ReadinessService.HRV_WEIGHT, "baseline": hrv_baseline},
            "sleep": {"value": sleep, "score": sleep_score, "weight": ReadinessService.SLEEP_WEIGHT},
            "stress": {"value": stress, "score": stress_score, "weight": ReadinessService.STRESS_WEIGHT},
            "resting_hr": {"value": rhr, "score": rhr_score, "weight": ReadinessService.RHR_WEIGHT, "baseline": rhr_baseline},
        }

        # Compute weighted score from available components
        total_weight = 0.0
        weighted_sum = 0.0

        for key, comp in components.items():
            if comp["score"] is not None:
                weighted_sum += comp["score"] * comp["weight"]
                total_weight += comp["weight"]

        if total_weight == 0:
            return {
                "score": None,
                "status": "no_data",
                "components": components,
                "baseline_days": baseline_rows,
                "date": target_date,
            }

        # Normalize if not all components are present
        raw_score = weighted_sum / total_weight
        score = round(min(100, max(0, raw_score)))

        # Determine status
        if score >= 85:
            status = "excellent"
        elif score >= 70:
            status = "good"
        elif score >= 50:
            status = "moderate"
        elif score >= 30:
            status = "poor"
        else:
            status = "rest"

        return {
            "score": score,
            "status": status,
            "components": components,
            "baseline_days": baseline_rows,
            "date": target_date,
        }
