"""Unit tests for the consolidated readiness engine."""

from app.core.readiness_engine import (
    ReadinessEngine,
    ReadinessStatus,
    ReadinessFactors,
    compute_readiness_score,
)


def test_engine_initializes_with_expected_defaults():
    engine = ReadinessEngine("user-1")

    assert engine.user_id == "user-1"
    assert engine.WEIGHTS["sleep"] == 0.30
    assert sum(engine.WEIGHTS.values()) == 1.0


def test_calculate_readiness_returns_score_and_factors():
    engine = ReadinessEngine("user-1")
    score, factors = engine.calculate_readiness(
        {
            "heart_rate": 48,
            "hrv": 60,
            "sleep_hours": 8,
            "stress_level": 20,
            "steps": 17500,
            "steps_prev_7d_avg": 17000,
            "is_rest_day": False,
            "exercise_load_7d": 1.0,
        }
    )

    assert 0 <= score <= 100
    assert isinstance(factors, ReadinessFactors)
    assert 0 <= factors.sleep_score <= 100
    assert 0 <= factors.recovery_score <= 100


def test_status_mapping_boundaries():
    assert ReadinessStatus.HIGH.value == "high"
    assert ReadinessStatus.MEDIUM.value == "medium"
    assert ReadinessStatus.LOW.value == "low"


def test_compute_readiness_score_returns_full_payload():
    result = compute_readiness_score(
        "test-user",
        {
            "heart_rate": 50,
            "hrv": 55,
            "sleep_hours": 7.2,
            "stress_level": 35,
            "steps": 12000,
            "steps_prev_7d_avg": 11000,
            "is_rest_day": False,
        },
    )

    assert set(["readiness_score", "status", "factors", "recommendation", "timestamp", "user_id", "version"]).issubset(result.keys())
    assert result["user_id"] == "test-user"
    assert result["version"] == "1.0"
    assert result["status"] in {"low", "medium", "high"}
