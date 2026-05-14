"""
UNIT TESTS - READINESS ENGINE v2.0
===================================
Pruebas para el motor consolidado de Readiness Score.
Corregido para importar desde app.core.readiness_engine (API real).

Ejecutar:
cd backend && python -m pytest tests/unit/test_readiness_engine.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import Mock

from app.core.readiness_engine import (
    ReadinessEngine,
    ReadinessStatus,
    ReadinessFactors,
    compute_readiness_score,
)


@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def engine(mock_db):
    return ReadinessEngine("test_user", mock_db)


@pytest.fixture
def sample_biometric_data():
    return {
        "heart_rate": 60,
        "hrv": 55,
        "sleep_hours": 7.5,
        "sleep_score": 85,
        "stress_level": 35,
        "steps": 10000,
        "steps_prev_7d_avg": 10000,
        "is_rest_day": False,
        "exercise_load_7d": 1.0,
    }


class TestInitialization:
    def test_engine_creates_with_user_id(self, mock_db):
        engine = ReadinessEngine("user1", mock_db)
        assert engine.user_id == "user1"

    def test_engine_loads_baselines(self, mock_db):
        engine = ReadinessEngine("user1", mock_db)
        assert engine.baselines is not None
        assert "hr_resting" in engine.baselines


class TestSleepScore:
    def test_sleep_optimal(self, engine):
        score = engine.calculate_sleep_score(7.5)
        assert 80 <= score <= 100

    def test_sleep_insufficient(self, engine):
        score = engine.calculate_sleep_score(4.0)
        assert score < 40

    def test_sleep_excessive(self, engine):
        score_normal = engine.calculate_sleep_score(8.0)
        score_excess = engine.calculate_sleep_score(12.0)
        assert score_excess < score_normal
        assert score_excess > 60

    def test_sleep_with_quality_bonus(self, engine):
        base_score = engine.calculate_sleep_score(7.0)
        quality_score = engine.calculate_sleep_score(7.0, sleep_quality=90)
        assert quality_score < base_score
        assert quality_score > base_score * 0.9


class TestRecoveryScore:
    def test_hrv_excellent(self, engine):
        score = engine.calculate_recovery_score(65, 55)
        assert score >= 80

    def test_hrv_normal(self, engine):
        score = engine.calculate_recovery_score(52, 55)
        assert 50 <= score <= 95

    def test_hrv_poor(self, engine):
        score = engine.calculate_recovery_score(35, 55)
        assert score < 60

    def test_hrv_none_returns_neutral(self, engine):
        score = engine.calculate_recovery_score(None)
        assert score == 75.0


class TestStrainScore:
    def test_low_stress(self, engine):
        score = engine.calculate_strain_score(20)
        assert score >= 80

    def test_high_stress(self, engine):
        score = engine.calculate_strain_score(70)
        assert score < 50


class TestActivityBalance:
    def test_rest_day_optimal(self, engine):
        score = engine.calculate_activity_balance(6000, 10000, is_rest_day=True)
        assert score >= 70

    def test_training_day_sweet_spot(self, engine):
        score = engine.calculate_activity_balance(11000, 10000, is_rest_day=False)
        assert score >= 70


class TestHRBaselineScore:
    def test_normal_hr(self, engine):
        score = engine.calculate_hr_baseline_score(48)
        assert score >= 80

    def test_elevated_hr(self, engine):
        score = engine.calculate_hr_baseline_score(60)
        assert score < 100


class TestReadinessCalculation:
    def test_perfect_conditions(self, engine, sample_biometric_data):
        data = sample_biometric_data.copy()
        data["sleep_hours"] = 8.0
        data["heart_rate"] = 48
        data["stress_level"] = 20
        score, factors = engine.calculate_readiness(data)
        assert score >= 70
        assert isinstance(factors, ReadinessFactors)

    def test_poor_conditions(self, engine, sample_biometric_data):
        data = sample_biometric_data.copy()
        data["sleep_hours"] = 4.0
        data["heart_rate"] = 75
        data["stress_level"] = 70
        score, factors = engine.calculate_readiness(data)
        assert score < 60

    def test_score_range_bounds(self, engine, sample_biometric_data):
        extreme_data = sample_biometric_data.copy()
        extreme_data["sleep_hours"] = 12.0
        extreme_data["steps"] = 50000
        score, _ = engine.calculate_readiness(extreme_data)
        assert 0 <= score <= 100

    def test_factors_returned(self, engine, sample_biometric_data):
        score, factors = engine.calculate_readiness(sample_biometric_data)
        assert isinstance(factors, ReadinessFactors)
        assert 0 <= factors.sleep_score <= 100
        assert 0 <= factors.recovery_score <= 100
        assert 0 <= factors.strain_score <= 100
        assert 0 <= factors.activity_balance <= 100
        assert 0 <= factors.hr_baseline <= 100


class TestPublicAPI:
    def test_compute_readiness_score_structure(self, sample_biometric_data):
        result = compute_readiness_score(
            user_id="test_user",
            biometric_data=sample_biometric_data,
            db_session=None,
        )
        assert "readiness_score" in result
        assert "status" in result
        assert "factors" in result
        assert "recommendation" in result


class TestReadinessStatus:
    def test_status_values(self):
        assert ReadinessStatus.LOW.value == "low"
        assert ReadinessStatus.MEDIUM.value == "medium"
        assert ReadinessStatus.HIGH.value == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
