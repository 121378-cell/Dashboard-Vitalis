"""
ATLAS Readiness Calculator (Pure Functions)
============================================

Funciones puras de cálculo de readiness score.
No tienen dependencias de base de datos ni estado global.
Completamente testeables sin mocks de DB.

Autor: ATLAS Team
Version: 2.0.0
"""

import statistics
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class PersonalBaseline:
    """Personal baseline metrics calculated from history."""
    hrv_mean: float = 0.0
    hrv_std: float = 0.0
    sleep_mean: float = 0.0
    rhr_mean: float = 0.0
    rhr_std: float = 0.0
    stress_mean: float = 0.0
    body_battery_mean: float = 0.0
    days_available: int = 0


@dataclass
class ReadinessComponents:
    """Individual component scores for readiness calculation."""
    hrv_score: float = 0.0
    sleep_score: float = 0.0
    stress_score: float = 0.0
    rhr_score: float = 0.0
    body_battery_score: float = 50.0
    load_score: float = 50.0


def score_hrv(hrv: Optional[float], baseline_mean: float, baseline_std: float) -> float:
    """
    Score HRV relative to personal baseline.

    Higher HRV = better recovery. Score based on how many
    standard deviations above/below the mean.

    Args:
        hrv: HRV value in ms
        baseline_mean: Personal average HRV
        baseline_std: Standard deviation of HRV

    Returns:
        Score from 0-100
    """
    if hrv is None:
        return 0.0

    if baseline_mean <= 0:
        if hrv >= 70:
            return 100.0
        elif hrv >= 55:
            return 80.0
        elif hrv >= 40:
            return 60.0
        return 30.0

    if baseline_std <= 0:
        baseline_std = baseline_mean * 0.1

    z_score = (hrv - baseline_mean) / baseline_std

    if z_score >= 1.0:
        return 100.0
    elif z_score >= 0.5:
        return 90.0
    elif z_score >= 0:
        return 80.0
    elif z_score >= -0.5:
        return 60.0
    elif z_score >= -1.0:
        return 40.0
    else:
        return 20.0


def score_sleep(hours: float, baseline_mean: float = 0) -> float:
    """
    Score sleep duration.

    Optimal: 7-9 hours
    Penalty for < 6 hours

    Args:
        hours: Total sleep hours
        baseline_mean: Ignored (kept for API compatibility)

    Returns:
        Score from 0-100
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


def score_sleep_with_quality(
    hours: float,
    deep_hours: Optional[float] = None,
    rem_hours: Optional[float] = None
) -> float:
    """
    Score sleep quality considering duration + sleep architecture (deep + REM).

    Args:
        hours: Total sleep hours
        deep_hours: Deep sleep hours
        rem_hours: REM sleep hours

    Returns:
        Score from 0-100
    """
    base_score = score_sleep(hours, 0)

    if deep_hours is not None and rem_hours is not None:
        recovery_hours = (deep_hours or 0) + (rem_hours or 0)
        if recovery_hours >= 2.0:
            base_score = min(100, base_score + 10)
        elif recovery_hours >= 1.5:
            base_score = min(100, base_score + 5)
        elif recovery_hours < 0.5:
            base_score = max(0, base_score - 10)

    return base_score


def score_stress(stress: Optional[float], baseline_mean: float = 0) -> float:
    """
    Score stress level (inverted - lower is better).

    Args:
        stress: Stress level (0-100)
        baseline_mean: Ignored (kept for API compatibility)

    Returns:
        Score from 0-100
    """
    if stress is None:
        return 0.0

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


def score_rhr(rhr: Optional[float], baseline_mean: float, baseline_std: float) -> float:
    """
    Score resting heart rate relative to personal baseline.

    Lower RHR is better (lower score is better for RHR, but we invert for readiness).

    Args:
        rhr: Resting heart rate in bpm
        baseline_mean: Personal average RHR
        baseline_std: Standard deviation of RHR

    Returns:
        Score from 0-100
    """
    if rhr is None:
        return 0.0

    if baseline_mean <= 0:
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
        baseline_std = baseline_mean * 0.05

    z_score = (rhr - baseline_mean) / baseline_std

    if z_score <= -1.0:
        return 100.0
    elif z_score <= -0.5:
        return 90.0
    elif z_score <= 0:
        return 80.0
    elif z_score <= 0.5:
        return 60.0
    elif z_score <= 1.0:
        return 40.0
    elif z_score <= 1.5:
        return 20.0
    else:
        return 10.0


def score_body_battery(body_battery: Optional[float]) -> float:
    """
    Score body battery as energy availability (0-100).

    Args:
        body_battery: Body battery value (0-100)

    Returns:
        Score from 0-100
    """
    if body_battery is None:
        return 50.0

    if body_battery >= 80:
        return 100.0
    elif body_battery >= 60:
        return 80.0 + (body_battery - 60) * 1.0
    elif body_battery >= 40:
        return 60.0 + (body_battery - 40) * 1.0
    elif body_battery >= 20:
        return 40.0 + (body_battery - 20) * 1.0
    else:
        return max(0, body_battery * 2.0)


def score_training_load_from_duration(total_minutes: int, days: int = 7) -> float:
    """
    Calculate training load score from total workout duration.

    Returns 0-100 score where:
    - 0-40: Very high load (risk of overtraining)
    - 40-60: High load
    - 60-80: Moderate/optimal load
    - 80-100: Low load (undertraining or recovery week)

    Args:
        total_minutes: Total workout duration in minutes
        days: Number of days to average over

    Returns:
        Score from 0-100
    """
    if total_minutes <= 0 or days <= 0:
        return 100.0

    avg_daily_min = total_minutes / days

    if avg_daily_min < 30:
        return 100.0
    elif avg_daily_min < 60:
        return 90.0
    elif avg_daily_min < 90:
        return 80.0
    elif avg_daily_min < 120:
        return 60.0
    elif avg_daily_min < 180:
        return 40.0
    else:
        return 20.0


def score_to_status(score: int) -> str:
    """
    Convert numeric score to status string.

    Args:
        score: Readiness score (0-100)

    Returns:
        Status string
    """
    if score >= 85:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "moderate"
    elif score >= 30:
        return "poor"
    return "rest"


def generate_recommendation(score: int, components: Optional[Dict[str, float]] = None) -> str:
    """
    Generate personalized recommendation based on readiness score.

    Args:
        score: Readiness score (0-100)
        components: Component scores dict

    Returns:
        Recommendation string
    """
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


def calculate_baseline_from_values(
    hrv_values: list,
    sleep_values: list,
    rhr_values: list,
    stress_values: list,
    body_battery_values: list
) -> PersonalBaseline:
    """
    Calculate personal baseline from lists of values.

    Requires at least 7 days of data for each metric to calculate baseline.

    Args:
        hrv_values: List of HRV values
        sleep_values: List of sleep hours
        rhr_values: List of resting HR values
        stress_values: List of stress values
        body_battery_values: List of body battery values

    Returns:
        PersonalBaseline dataclass
    """
    baseline = PersonalBaseline()

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

    if len(body_battery_values) >= 7:
        baseline.body_battery_mean = statistics.mean(body_battery_values)

    return baseline


def calculate_readiness_score(
    components: ReadinessComponents,
    baseline: PersonalBaseline,
    apply_load_penalty: bool = True,
    apply_body_battery_modifier: bool = True
) -> Tuple[int, str, bool]:
    """
    Calculate final readiness score from component scores.

    Pure function - no database or external dependencies.

    Args:
        components: ReadinessComponents with individual scores
        baseline: PersonalBaseline for reference
        apply_load_penalty: Whether to apply training load penalty
        apply_body_battery_modifier: Whether to apply body battery modifier

    Returns:
        Tuple of (final_score, status, overtraining_risk)
    """
    weights = {
        'hrv': 0.35,
        'sleep': 0.25,
        'stress': 0.20,
        'rhr': 0.20,
    }

    available_weights = {}
    component_scores = {}

    if components.hrv_score > 0 and baseline.hrv_mean > 0:
        available_weights['hrv'] = weights['hrv']
        component_scores['hrv'] = components.hrv_score

    if components.sleep_score > 0:
        available_weights['sleep'] = weights['sleep']
        component_scores['sleep'] = components.sleep_score

    if components.stress_score > 0:
        available_weights['stress'] = weights['stress']
        component_scores['stress'] = components.stress_score

    if components.rhr_score > 0 and baseline.rhr_mean > 0:
        available_weights['rhr'] = weights['rhr']
        component_scores['rhr'] = components.rhr_score

    total_weight = sum(available_weights.values())
    if total_weight == 0:
        available_weights = weights.copy()
        total_weight = sum(available_weights.values())

    normalized_weights = {k: v / total_weight for k, v in available_weights.items()}

    raw_score = (
        component_scores.get("hrv", 0) * normalized_weights.get("hrv", 0) +
        component_scores.get("sleep", 0) * normalized_weights.get("sleep", 0) +
        component_scores.get("stress", 0) * normalized_weights.get("stress", 0) +
        component_scores.get("rhr", 0) * normalized_weights.get("rhr", 0)
    )

    if apply_load_penalty:
        load_score = components.load_score
        if load_score < 40:
            high_load_penalty = 1.0 - (load_score / 40)
            raw_score *= (1.0 - high_load_penalty * 0.5)
        elif load_score < 60:
            moderate_penalty = 1.0 - (load_score / 60)
            raw_score *= (1.0 - moderate_penalty * 0.15)

    if apply_body_battery_modifier and components.body_battery_score > 0:
        body_battery = components.body_battery_score
        if body_battery < 20:
            raw_score *= 0.6
        elif body_battery < 40:
            raw_score *= 0.8
        elif body_battery > 90:
            raw_score *= 1.05

    final_score = round(max(0, min(100, raw_score)))
    status = score_to_status(final_score)

    overtraining_risk = (
        components.load_score < 40 or
        (components.hrv_score < 30 and baseline.hrv_mean > 0) or
        (components.rhr_score < 30 and baseline.rhr_mean > 0) or
        (components.load_score < 60 and final_score < 40)
    )

    return final_score, status, overtraining_risk