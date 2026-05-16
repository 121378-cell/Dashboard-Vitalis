"""
Tests for Readiness Calculator Pure Functions
================================================

Unit tests for all pure scoring functions in readiness_calculator.py.
These tests require no database mocks and run instantly.

Run: pytest backend/tests/test_readiness_calculator.py -v
"""

import pytest
from app.core.readiness_calculator import (
    score_hrv,
    score_sleep,
    score_sleep_with_quality,
    score_stress,
    score_rhr,
    score_body_battery,
    score_training_load_from_duration,
    score_to_status,
    generate_recommendation,
    calculate_baseline_from_values,
    calculate_readiness_score,
    ReadinessComponents,
    PersonalBaseline,
)


class TestScoreHRV:
    """Tests for HRV scoring function."""

    def test_high_hrv_above_baseline(self):
        """HRV well above baseline returns high score."""
        result = score_hrv(80, 50, 10)
        assert result == 100.0

    def test_hrv_slightly_above_baseline(self):
        """HRV slightly above baseline returns good score."""
        result = score_hrv(55, 50, 10)
        assert result == 80.0

    def test_hrv_at_baseline(self):
        """HRV at baseline returns good score."""
        result = score_hrv(50, 50, 10)
        assert result == 80.0

    def test_hrv_below_baseline(self):
        """HRV below baseline returns lower score."""
        result = score_hrv(40, 50, 10)
        assert result == 60.0

    def test_hrv_well_below_baseline(self):
        """HRV well below baseline returns poor score."""
        result = score_hrv(30, 50, 10)
        assert result == 20.0

    def test_hrv_no_baseline_absolute_scale(self):
        """When no baseline, use absolute scale."""
        result = score_hrv(70, 0, 0)
        assert result == 100.0
        result = score_hrv(55, 0, 0)
        assert result == 80.0
        result = score_hrv(40, 0, 0)
        assert result == 60.0
        result = score_hrv(30, 0, 0)
        assert result == 30.0

    def test_hrv_none_returns_zero(self):
        """None HRV returns 0."""
        result = score_hrv(None, 50, 10)
        assert result == 0.0


class TestScoreSleep:
    """Tests for sleep scoring function."""

    def test_optimal_sleep_8_hours(self):
        """8+ hours returns perfect score."""
        result = score_sleep(8.0, 0)
        assert result == 100.0

    def test_optimal_sleep_9_hours(self):
        """9 hours returns capped score."""
        result = score_sleep(9.0, 0)
        assert result == 100.0

    def test_good_sleep_7_hours(self):
        """7 hours returns good score."""
        result = score_sleep(7.0, 0)
        assert result == 85.0

    def test_acceptable_sleep_6_hours(self):
        """6 hours returns acceptable score."""
        result = score_sleep(6.0, 0)
        assert result == 60.0

    def test_low_sleep_5_hours(self):
        """5 hours returns low score."""
        result = score_sleep(5.0, 0)
        assert result == 30.0

    def test_very_low_sleep_4_hours(self):
        """4 hours returns very low score."""
        result = score_sleep(4.0, 0)
        assert result == 10.0

    def test_minimal_sleep_2_hours(self):
        """2 hours returns minimal score."""
        result = score_sleep(2.0, 0)
        assert result == 5.0


class TestScoreSleepWithQuality:
    """Tests for sleep quality scoring with deep/REM hours."""

    def test_sleep_with_good_recovery_hours(self):
        """Sleep with good deep+REM hours gets bonus."""
        base = score_sleep(7.0, 0)
        result = score_sleep_with_quality(7.0, 1.5, 1.5)
        assert result == min(100, base + 10)

    def test_sleep_with_moderate_recovery_hours(self):
        """Sleep with moderate recovery hours gets smaller bonus."""
        base = score_sleep(7.0, 0)
        result = score_sleep_with_quality(7.0, 1.0, 1.0)
        assert result == min(100, base + 5)

    def test_sleep_with_low_recovery_hours(self):
        """Sleep with low recovery hours gets penalty."""
        base = score_sleep(7.0, 0)
        result = score_sleep_with_quality(7.0, 0.2, 0.2)
        assert result == max(0, base - 10)


class TestScoreStress:
    """Tests for stress scoring function."""

    def test_very_low_stress(self):
        """Very low stress returns high score."""
        result = score_stress(15, 0)
        assert result == 100.0

    def test_low_stress(self):
        """Low stress returns good score."""
        result = score_stress(30, 0)
        assert result == 80.0 - (30 - 20) * 1.33

    def test_medium_stress(self):
        """Medium stress returns moderate score."""
        result = score_stress(45, 0)
        assert result == 60.0 - (45 - 35) * 1.33

    def test_high_stress(self):
        """High stress returns low score."""
        result = score_stress(60, 0)
        assert result == 40.0 - (60 - 50) * 1.0

    def test_very_high_stress(self):
        """Very high stress returns minimal score."""
        result = score_stress(80, 0)
        assert result == max(0, 20.0 - (80 - 70) * 0.5)

    def test_stress_none_returns_zero(self):
        """None stress returns 0."""
        result = score_stress(None, 0)
        assert result == 0.0


class TestScoreRHR:
    """Tests for resting heart rate scoring."""

    def test_very_low_rhr(self):
        """Very low RHR returns high score."""
        result = score_rhr(45, 60, 5)
        assert result == 100.0

    def test_low_rhr(self):
        """Low RHR returns good score."""
        result = score_rhr(55, 60, 5)
        assert result == 90.0

    def test_at_baseline_rhr(self):
        """RHR at baseline returns good score."""
        result = score_rhr(60, 60, 5)
        assert result == 80.0

    def test_above_baseline_rhr(self):
        """RHR above baseline returns lower score."""
        result = score_rhr(65, 60, 5)
        assert result == 60.0

    def test_well_above_baseline_rhr(self):
        """RHR well above baseline returns poor score."""
        result = score_rhr(75, 60, 5)
        assert result == 20.0

    def test_no_baseline_absolute_scale(self):
        """When no baseline, use absolute scale."""
        result = score_rhr(50, 0, 0)
        assert result == 100.0
        result = score_rhr(65, 0, 0)
        assert result == 60.0
        result = score_rhr(85, 0, 0)
        assert result == 20.0

    def test_rhr_none_returns_zero(self):
        """None RHR returns 0."""
        result = score_rhr(None, 60, 5)
        assert result == 0.0


class TestScoreBodyBattery:
    """Tests for body battery scoring."""

    def test_high_body_battery(self):
        """High body battery returns high score."""
        result = score_body_battery(90)
        assert result == 100.0

    def test_good_body_battery(self):
        """Good body battery returns good score."""
        result = score_body_battery(70)
        assert result == 90.0

    def test_moderate_body_battery(self):
        """Moderate body battery returns moderate score."""
        result = score_body_battery(50)
        assert result == 70.0

    def test_low_body_battery(self):
        """Low body battery returns low score."""
        result = score_body_battery(30)
        assert result == 50.0

    def test_very_low_body_battery(self):
        """Very low body battery returns very low score."""
        result = score_body_battery(10)
        assert result == 20.0

    def test_none_body_battery_returns_50(self):
        """None body battery returns default 50."""
        result = score_body_battery(None)
        assert result == 50.0


class TestScoreTrainingLoad:
    """Tests for training load scoring from duration."""

    def test_no_training_returns_100(self):
        """No training returns high score (recovery)."""
        result = score_training_load_from_duration(0, 7)
        assert result == 100.0

    def test_light_training(self):
        """Light training returns good score."""
        result = score_training_load_from_duration(120, 7)
        assert result == 90.0

    def test_moderate_training(self):
        """Moderate training returns moderate score."""
        result = score_training_load_from_duration(420, 7)
        assert result == 80.0

    def test_heavy_training(self):
        """Heavy training returns low score."""
        result = score_training_load_from_duration(840, 7)
        assert result == 40.0

    def test_very_heavy_training(self):
        """Very heavy training returns very low score."""
        result = score_training_load_from_duration(1500, 7)
        assert result == 20.0


class TestScoreToStatus:
    """Tests for score to status conversion."""

    def test_excellent(self):
        assert score_to_status(90) == "excellent"

    def test_good(self):
        assert score_to_status(75) == "good"

    def test_moderate(self):
        assert score_to_status(55) == "moderate"

    def test_poor(self):
        assert score_to_status(35) == "poor"

    def test_rest(self):
        assert score_to_status(20) == "rest"


class TestGenerateRecommendation:
    """Tests for recommendation generation."""

    def test_excellent_readiness(self):
        rec = generate_recommendation(90, {"load": 70})
        assert "óptimo" in rec or "peak" in rec.lower()

    def test_good_readiness(self):
        rec = generate_recommendation(75, {"load": 70})
        assert "Buen día" in rec

    def test_moderate_readiness(self):
        rec = generate_recommendation(55, {"load": 70})
        assert "moderado" in rec.lower()

    def test_poor_readiness(self):
        rec = generate_recommendation(35, {"load": 70})
        assert "Recuperación activa" in rec

    def test_rest_readiness(self):
        rec = generate_recommendation(20, {"load": 70})
        assert "descanso total" in rec.lower()

    def test_high_load_overrides_score(self):
        """High load training overrides readiness score recommendation."""
        rec = generate_recommendation(80, {"load": 30})
        assert "descanso" in rec.lower()


class TestCalculateBaselineFromValues:
    """Tests for baseline calculation from value lists."""

    def test_baseline_with_sufficient_data(self):
        """Baseline calculated when enough data points."""
        result = calculate_baseline_from_values(
            hrv_values=[50, 52, 48, 51, 49, 50, 53, 52, 49, 51],
            sleep_values=[7, 7.5, 8, 7.2, 7.8, 7, 7.5, 7.2, 7.8, 7],
            rhr_values=[60, 62, 59, 61, 60, 62, 59, 61, 60, 62],
            stress_values=[30, 35, 32, 31, 33, 30, 35, 32, 31, 33],
            body_battery_values=[80, 82, 78, 81, 79, 80, 82, 78, 81, 79],
        )
        assert result.days_available == 10
        assert 48 <= result.hrv_mean <= 52
        assert result.hrv_std > 0
        assert 7 <= result.sleep_mean <= 8
        assert 59 <= result.rhr_mean <= 62

    def test_baseline_with_insufficient_data(self):
        """Baseline returns zeros when not enough data."""
        result = calculate_baseline_from_values(
            hrv_values=[50, 52],
            sleep_values=[7, 7.5],
            rhr_values=[60, 62],
            stress_values=[30, 35],
            body_battery_values=[80, 82],
        )
        assert result.hrv_mean == 0.0
        assert result.sleep_mean == 0.0
        assert result.rhr_mean == 0.0


class TestCalculateReadinessScore:
    """Tests for the main readiness score calculation."""

    def test_high_all_components(self):
        """High scores across all components give high readiness."""
        components = ReadinessComponents(
            hrv_score=90,
            sleep_score=90,
            stress_score=90,
            rhr_score=90,
            body_battery_score=90,
            load_score=90,
        )
        baseline = PersonalBaseline(hrv_mean=50, hrv_std=10, rhr_mean=60, rhr_std=5)

        score, status, risk = calculate_readiness_score(components, baseline)

        assert score >= 70
        assert status in ["excellent", "good"]
        assert risk is False

    def test_low_hrv_triggers_overtraining_risk(self):
        """Very low HRV score triggers overtraining risk."""
        components = ReadinessComponents(
            hrv_score=20,
            sleep_score=80,
            stress_score=80,
            rhr_score=80,
            body_battery_score=80,
            load_score=80,
        )
        baseline = PersonalBaseline(hrv_mean=50, hrv_std=10, rhr_mean=60, rhr_std=5)

        score, status, risk = calculate_readiness_score(components, baseline)

        assert risk is True

    def test_low_body_battery_penalizes_score(self):
        """Low body battery reduces the final score."""
        components_normal = ReadinessComponents(
            hrv_score=80, sleep_score=80, stress_score=80, rhr_score=80,
            body_battery_score=90, load_score=80
        )
        components_low_bb = ReadinessComponents(
            hrv_score=80, sleep_score=80, stress_score=80, rhr_score=80,
            body_battery_score=15, load_score=80
        )
        baseline = PersonalBaseline(hrv_mean=50, hrv_std=10, rhr_mean=60, rhr_std=5)

        score_normal, _, _ = calculate_readiness_score(components_normal, baseline)
        score_low_bb, _, _ = calculate_readiness_score(components_low_bb, baseline)

        assert score_low_bb < score_normal

    def test_high_load_penalty_applied(self):
        """High training load applies penalty to score."""
        components_normal_load = ReadinessComponents(
            hrv_score=80, sleep_score=80, stress_score=80, rhr_score=80,
            body_battery_score=80, load_score=90
        )
        components_high_load = ReadinessComponents(
            hrv_score=80, sleep_score=80, stress_score=80, rhr_score=80,
            body_battery_score=80, load_score=30
        )
        baseline = PersonalBaseline(hrv_mean=50, hrv_std=10, rhr_mean=60, rhr_std=5)

        score_normal, _, _ = calculate_readiness_score(components_normal_load, baseline)
        score_high_load, _, _ = calculate_readiness_score(components_high_load, baseline)

        assert score_high_load < score_normal

    def test_no_hrv_or_rhr_baseline_uses_available_weights(self):
        """When no baseline for HRV/RHR, uses available data only."""
        components = ReadinessComponents(
            hrv_score=0,
            sleep_score=85,
            stress_score=80,
            rhr_score=0,
            body_battery_score=80,
            load_score=80,
        )
        baseline = PersonalBaseline(hrv_mean=0, hrv_std=0, rhr_mean=0, rhr_std=0)

        score, status, risk = calculate_readiness_score(components, baseline, apply_load_penalty=False)

        assert 0 < score <= 100
        assert status in ["excellent", "good", "moderate", "poor", "rest"]