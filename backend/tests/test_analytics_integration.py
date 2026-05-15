"""Integration tests for Analytics endpoints."""
import os
import sys
import time
from unittest.mock import patch, Mock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.db.base import Base
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.analytics_service import AnalyticsService
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from app.api.api_v1.endpoints import analytics as analytics_module

test_app = FastAPI(title="Test ATLAS Analytics API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _override_db(test_engine):
    TestSession = sessionmaker(bind=test_engine)

    def _get_test_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides = {}
    from app.api.deps import get_db
    test_app.dependency_overrides[get_db] = _get_test_db

    patcher = patch("app.db.session.SessionLocal", TestSession)
    patcher.start()

    yield

    patcher.stop()
    test_app.dependency_overrides = {}


@pytest.fixture
def client():
    return TestClient(test_app)


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture(autouse=True)
def _clear_profile_cache():
    """Clear the in-memory profile cache before each test."""
    analytics_module._profile_cache.clear()
    analytics_module._profile_cache_timestamp = None
    yield


# =============================================================================
# TestCorrelationsEndpoint
# =============================================================================

class TestCorrelationsEndpoint:
    """GET /api/v1/analytics/correlations"""

    API_PATH = f"{settings.API_V1_STR}/analytics/correlations"

    SAMPLE_CORRELATIONS = {
        "correlations": [
            {"x": "sleep", "y": "readiness", "r": 0.72, "strength": "fuerte"},
            {"x": "hrv", "y": "readiness", "r": 0.45, "strength": "moderada"},
        ],
        "insights": ["Dormir bien mejora tu readiness"],
        "days_analyzed": 90,
    }

    def test_success(self, client, headers):
        """Returns correlations data."""
        with patch.object(AnalyticsService, "find_personal_correlations",
                          return_value=self.SAMPLE_CORRELATIONS):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["correlations"]) == 2
        assert data["days_analyzed"] == 90

    def test_empty(self, client, headers):
        """Empty correlations."""
        with patch.object(AnalyticsService, "find_personal_correlations",
                          return_value={}):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_invalid_days(self, client, headers):
        """days=29 → 422 (ge=30), days=366 → 422 (le=365)."""
        resp = client.get(f"{self.API_PATH}?days=29", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days=366", headers=headers)
        assert resp.status_code == 422

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestReadinessForecastEndpoint
# =============================================================================

class TestReadinessForecastEndpoint:
    """GET /api/v1/analytics/readiness-forecast"""

    API_PATH = f"{settings.API_V1_STR}/analytics/readiness-forecast"

    SAMPLE_FORECAST = {
        "forecast": [
            {"day": 1, "readiness": 75},
            {"day": 2, "readiness": 72},
            {"day": 3, "readiness": 68},
        ],
        "trend": "declining",
    }

    def test_success(self, client, headers):
        """Returns readiness forecast."""
        with patch.object(AnalyticsService, "forecast_readiness",
                          return_value=self.SAMPLE_FORECAST):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["forecast"]) == 3
        assert data["trend"] == "declining"

    def test_empty(self, client, headers):
        """Empty forecast."""
        with patch.object(AnalyticsService, "forecast_readiness",
                          return_value={}):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_invalid_days_ahead(self, client, headers):
        """days_ahead=0 → 422 (ge=1), days_ahead=8 → 422 (le=7)."""
        resp = client.get(f"{self.API_PATH}?days_ahead=0", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days_ahead=8", headers=headers)
        assert resp.status_code == 422

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestPlateausEndpoint
# =============================================================================

class TestPlateausEndpoint:
    """GET /api/v1/analytics/plateaus"""

    API_PATH = f"{settings.API_V1_STR}/analytics/plateaus"

    SAMPLE_PLATEAUS = {
        "plateaus": [
            {"exercise": "Bench Press", "weeks_stalled": 4, "suggestion": "Cambia el esquema de repeticiones"},
        ],
        "total_analyzed": 1,
    }

    def test_success(self, client, headers):
        """Returns plateaus data."""
        with patch.object(AnalyticsService, "detect_plateau",
                          return_value=self.SAMPLE_PLATEAUS):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["plateaus"]) == 1
        assert data["total_analyzed"] == 1

    def test_with_exercise_param(self, client, headers):
        """Passing exercise parameter filters results."""
        with patch.object(AnalyticsService, "detect_plateau",
                          return_value=self.SAMPLE_PLATEAUS) as mock:
            resp = client.get(f"{self.API_PATH}?exercise=Bench+Press", headers=headers)
        assert resp.status_code == 200
        # Verify exercise was forwarded
        call_args = mock.call_args[0]
        assert call_args[2] == "Bench Press"  # 3rd positional arg = exercise_name

    def test_empty(self, client, headers):
        """No plateaus."""
        with patch.object(AnalyticsService, "detect_plateau",
                          return_value={"plateaus": [], "total_analyzed": 0}):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total_analyzed"] == 0

    def test_invalid_weeks(self, client, headers):
        """weeks=3 → 422 (ge=4), weeks=13 → 422 (le=12)."""
        resp = client.get(f"{self.API_PATH}?weeks=3", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?weeks=13", headers=headers)
        assert resp.status_code == 422

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestOptimalVolumeEndpoint
# =============================================================================

class TestOptimalVolumeEndpoint:
    """GET /api/v1/analytics/optimal-volume"""

    API_PATH = f"{settings.API_V1_STR}/analytics/optimal-volume"

    SAMPLE_VOLUME = {
        "optimal_volume_per_week": 180,
        "current_volume": 150,
        "recommendation": "Incrementa 10-15% el volumen semanal",
        "by_muscle_group": {
            "Chest": {"optimal": 60, "current": 50},
            "Back": {"optimal": 60, "current": 40},
        },
    }

    def test_success(self, client, headers):
        """Returns optimal volume data."""
        with patch.object(AnalyticsService, "find_optimal_volume",
                          return_value=self.SAMPLE_VOLUME):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["optimal_volume_per_week"] == 180
        assert "Chest" in data["by_muscle_group"]

    def test_empty(self, client, headers):
        """Empty volume data."""
        with patch.object(AnalyticsService, "find_optimal_volume",
                          return_value={}):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestInsightsEndpoint
# =============================================================================

class TestInsightsEndpoint:
    """GET /api/v1/analytics/insights"""

    API_PATH = f"{settings.API_V1_STR}/analytics/insights"

    SAMPLE_INSIGHTS = {
        "month": "March",
        "year": 2025,
        "total_workouts": 20,
        "highlights": ["Has mejorado tu volumen semanal un 15%"],
        "recommendations": ["Aumenta el descanso entre sesiones de pierna"],
    }

    def test_success(self, client, headers):
        """Returns monthly insights."""
        with patch.object(AnalyticsService, "get_monthly_insights",
                          return_value=self.SAMPLE_INSIGHTS):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == "March"
        assert len(data["highlights"]) == 1

    def test_empty(self, client, headers):
        """Empty insights."""
        with patch.object(AnalyticsService, "get_monthly_insights",
                          return_value={}):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestAthleticProfileEndpoint
# =============================================================================

class TestAthleticProfileEndpoint:
    """GET /api/v1/analytics/intelligence/profile"""

    API_PATH = f"{settings.API_V1_STR}/analytics/intelligence/profile"

    SAMPLE_PROFILE = {
        "generated_at": 1234567890,
        "user_id": "test_user",
        "fitness_baseline": {"vo2max": 45, "hrv_baseline": 65},
        "sleep_patterns": {"avg_sleep": 7.5, "quality": "good"},
        "recovery_capacity": {"hrv_trend": "stable", "score": 78},
        "overreaching_risk": {"risk_level": "low", "acwr_ratio": 0.9},
    }

    def test_success(self, client, headers):
        """Returns full athletic profile."""
        with patch.object(AthleticIntelligenceService, "get_full_athletic_profile",
                          return_value=self.SAMPLE_PROFILE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test_user"
        assert data["fitness_baseline"]["vo2max"] == 45
        assert data["overreaching_risk"]["risk_level"] == "low"

    def test_cache_hit(self, client, headers):
        """Second call uses cache — service called only once."""
        mock_obj = Mock(return_value=self.SAMPLE_PROFILE)
        with patch.object(AthleticIntelligenceService, "get_full_athletic_profile", mock_obj):
            # First call — should invoke service
            resp1 = client.get(self.API_PATH, headers=headers)
            assert resp1.status_code == 200
            # Second call — should use cache
            resp2 = client.get(self.API_PATH, headers=headers)
            assert resp2.status_code == 200
        # Service should have been called exactly once
        assert mock_obj.call_count == 1

    def test_error_returns_partial_data(self, client, headers):
        """Service raises Exception → 200 with partial data and errors field."""
        with patch.object(AthleticIntelligenceService, "get_full_athletic_profile",
                          side_effect=ValueError("DB connection failed")):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["errors"]) > 0
        assert data["fitness_baseline"]["insufficient_data"] is True
        assert data["sleep_patterns"]["insufficient_data"] is True
        assert data["recovery_capacity"]["insufficient_data"] is True
        assert data["overreaching_risk"]["insufficient_data"] is True
        assert data["user_id"] == "test_user"

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# =============================================================================
# TestOverreachingCheckEndpoint
# =============================================================================

class TestOverreachingCheckEndpoint:
    """GET /api/v1/analytics/intelligence/overreaching-check"""

    API_PATH = f"{settings.API_V1_STR}/analytics/intelligence/overreaching-check"

    SAMPLE_RISK = {
        "risk_level": "moderate",
        "acwr_ratio": 1.3,
        "acute_load_min": 450,
        "chronic_load_min": 350,
        "additional_risk_factors": 1,
        "recommendation": "Considera un día de descanso activo",
    }

    def test_success(self, client, headers):
        """Returns overreaching risk analysis."""
        with patch.object(AthleticIntelligenceService, "detect_overreaching_risk",
                          return_value=self.SAMPLE_RISK):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "moderate"
        assert data["acwr_ratio"] == 1.3

    def test_high_risk(self, client, headers):
        """High risk level."""
        high_risk = dict(self.SAMPLE_RISK)
        high_risk["risk_level"] = "high"
        high_risk["acwr_ratio"] = 1.8
        with patch.object(AthleticIntelligenceService, "detect_overreaching_risk",
                          return_value=high_risk):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["risk_level"] == "high"

    def test_error_returns_insufficient_data(self, client, headers):
        """Service raises Exception → 200 with insufficient_data fallback."""
        with patch.object(AthleticIntelligenceService, "detect_overreaching_risk",
                          side_effect=RuntimeError("Service unavailable")):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "insufficient_data"
        assert data["acwr_ratio"] is None
        assert data["acute_load_min"] is None
        assert data["chronic_load_min"] is None
        assert data["additional_risk_factors"] == 0

    def test_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
