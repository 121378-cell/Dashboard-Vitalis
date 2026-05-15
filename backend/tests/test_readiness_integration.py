"""
Integration tests for Readiness endpoints.
===========================================

Endpoints:
- GET /api/v1/readiness/           (v1 legacy)
- GET /api/v1/readiness/score      (v2)
- GET /api/v1/readiness/trend      (historical)
- GET /api/v1/readiness/forecast   (projection)
- POST /api/v1/readiness/calculate (manual)
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
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
from app.models.biometrics import Biometrics
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.readiness_service import ReadinessService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Readiness API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def db_session(test_engine):
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def other_headers():
    return {"x-user-id": "other_user"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_BIO_DATA = json.dumps({
    "heartRate": 58,
    "hrv": 65,
    "sleep": 7.5,
    "sleepScore": 82,
    "stress": 32,
    "steps": 8500,
})

SAMPLE_LEGACY_RESPONSE = {
    "readiness_score": 78,
    "status": "good",
    "factors": {
        "sleep": 82.0,
        "recovery": 75.0,
        "strain": 70.0,
        "activity_balance": 80.0,
        "hr_baseline": 85.0,
    },
    "recommendation": "Buena recuperación, buen momento para entrenar.",
    "timestamp": datetime.now().isoformat(),
    "user_id": "test_user",
    "version": "2.0",
}

SAMPLE_SCORE_RESPONSE = {
    "score": 78,
    "status": "good",
    "recommendation": "Buena recuperación. Puedes entrenar con intensidad moderada.",
    "components": {"hrv": 75.0, "sleep": 82.0, "stress": 68.0, "rhr": 80.0, "load": 85.0},
    "baseline": {
        "hrv_mean": 62.0, "hrv_std": 8.0,
        "rhr_mean": 60.0, "rhr_std": 4.0,
        "sleep_mean": 7.2, "stress_mean": 35.0,
        "days_available": 14,
    },
    "overtraining_risk": False,
    "date": date.today().isoformat(),
}

SAMPLE_TREND_RESPONSE = [
    {"date": (date.today() - timedelta(days=2)).isoformat(), "score": 82, "status": "excellent", "overtraining_risk": False},
    {"date": (date.today() - timedelta(days=1)).isoformat(), "score": 75, "status": "good", "overtraining_risk": False},
    {"date": date.today().isoformat(), "score": 78, "status": "good", "overtraining_risk": False},
]

SAMPLE_FORECAST_RESPONSE = [
    {"date": (date.today() + timedelta(days=1)).isoformat(), "score": 76, "status": "good", "recommendation": "Mantén la intensidad.", "confidence": 0.85},
    {"date": (date.today() + timedelta(days=2)).isoformat(), "score": 72, "status": "moderate", "recommendation": "Considera un día de recuperación.", "confidence": 0.70},
    {"date": (date.today() + timedelta(days=3)).isoformat(), "score": 68, "status": "moderate", "recommendation": "Reduce carga.", "confidence": 0.55},
]


def _create_biometric(
    db_session,
    user_id="test_user",
    date_str=None,
    data=SAMPLE_BIO_DATA,
    source="health_connect",
    body_battery=None,
    training_readiness=None,
):
    if date_str is None:
        date_str = date.today().isoformat()
    bio = Biometrics(
        user_id=user_id,
        date=date_str,
        data=data,
        source=source,
        body_battery=body_battery,
        training_readiness=training_readiness,
    )
    db_session.add(bio)
    db_session.commit()
    db_session.refresh(bio)
    return bio


# ============================================================
# TestGetReadinessEndpoint (Legacy v1) — GET /readiness/
# ============================================================

class TestGetReadinessEndpoint:
    API_PATH = "/api/v1/readiness/"

    def test_get_with_biometrics(self, client, db_session, headers):
        """Biometric exists → legacy readiness score returned."""
        _create_biometric(db_session)
        with patch("app.core.readiness_engine.compute_readiness_score",
                    return_value=SAMPLE_LEGACY_RESPONSE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["readiness_score"] == 78
        assert data["status"] == "good"
        assert data["version"] == "2.0"

    def test_get_no_biometrics(self, client, headers):
        """No biometric → 404."""
        with patch("app.core.readiness_engine.compute_readiness_score") as mock:
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 404
        detail = resp.json().get("detail", "")
        assert "no hay datos biométricos" in detail.lower()
        mock.assert_not_called()

    def test_get_with_extra_fields(self, client, db_session, headers):
        """Biometric with body_battery and training_readiness is parsed correctly."""
        _create_biometric(db_session, body_battery=72.0, training_readiness=80,
                          data=json.dumps({"heartRate": 55, "hrv": 70, "sleep": 8.0,
                                           "sleepScore": 90, "stress": 25, "steps": 12000}))
        with patch("app.core.readiness_engine.compute_readiness_score",
                    return_value=SAMPLE_LEGACY_RESPONSE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200

    def test_get_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch("app.core.readiness_engine.compute_readiness_score") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestReadinessScoreEndpoint (v2) — GET /readiness/score
# ============================================================

class TestReadinessScoreEndpoint:
    API_PATH = "/api/v1/readiness/score"

    def test_score_with_data(self, client, headers):
        """ReadinessService.calculate returns valid score → 200."""
        with patch.object(ReadinessService, "calculate", return_value=SAMPLE_SCORE_RESPONSE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 78
        assert data["status"] == "good"
        assert data["components"]["hrv"] == 75.0
        assert data["components"]["sleep"] == 82.0
        assert data["overtraining_risk"] is False
        assert "date" in data

    def test_score_no_data(self, client, headers):
        """calculate returns score=None → 404."""
        no_data = {
            "score": None, "status": "no_data",
            "recommendation": "No hay datos disponibles",
            "components": {}, "baseline": {},
            "overtraining_risk": False, "date": date.today().isoformat(),
        }
        with patch.object(ReadinessService, "calculate", return_value=no_data):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 404

    def test_score_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(ReadinessService, "calculate") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestReadinessTrendEndpoint — GET /readiness/trend
# ============================================================

class TestReadinessTrendEndpoint:
    API_PATH = "/api/v1/readiness/trend"

    def test_trend_with_data(self, client, headers):
        """get_trend returns list → 200 with chronological data."""
        with patch.object(ReadinessService, "get_trend", return_value=SAMPLE_TREND_RESPONSE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["score"] == 82
        assert data[1]["status"] == "good"
        assert data[2]["overtraining_risk"] is False

    def test_trend_empty(self, client, headers):
        """get_trend returns [] → 404."""
        with patch.object(ReadinessService, "get_trend", return_value=[]):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 404

    def test_trend_custom_days(self, client, headers):
        """Passes days param to the service."""
        with patch.object(ReadinessService, "get_trend", return_value=SAMPLE_TREND_RESPONSE[:1]) as mock:
            resp = client.get(f"{self.API_PATH}?days=7", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        # Verify days was forwarded to service
        assert mock.call_args[1].get("days") == 7 or mock.call_args[0][2] == 7

    def test_trend_invalid_days(self, client, headers):
        """days=0 → 422, days=366 → 422."""
        resp = client.get(f"{self.API_PATH}?days=0", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days=366", headers=headers)
        assert resp.status_code == 422

    def test_trend_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(ReadinessService, "get_trend") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestReadinessForecastEndpoint — GET /readiness/forecast
# ============================================================

class TestReadinessForecastEndpoint:
    API_PATH = "/api/v1/readiness/forecast"

    def test_forecast_with_data(self, client, headers):
        """get_forecast returns list → 200 with projection data."""
        with patch.object(ReadinessService, "get_forecast", return_value=SAMPLE_FORECAST_RESPONSE):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["score"] == 76
        assert data[0]["confidence"] == 0.85
        assert "recommendation" in data[0]

    def test_forecast_empty(self, client, headers):
        """get_forecast returns [] → 404."""
        with patch.object(ReadinessService, "get_forecast", return_value=[]):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 404

    def test_forecast_custom_days(self, client, headers):
        """Custom days param is forwarded."""
        custom_forecast = SAMPLE_FORECAST_RESPONSE[:2]
        with patch.object(ReadinessService, "get_forecast", return_value=custom_forecast) as mock:
            resp = client.get(f"{self.API_PATH}?days=5", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        # Verify days was forwarded
        call_days = mock.call_args[1].get("days", mock.call_args[0][2] if len(mock.call_args[0]) > 2 else None)
        assert call_days == 5

    def test_forecast_invalid_days(self, client, headers):
        """days=0 → 422, days=8 → 422 (max 7)."""
        resp = client.get(f"{self.API_PATH}?days=0", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days=8", headers=headers)
        assert resp.status_code == 422

    def test_forecast_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(ReadinessService, "get_forecast") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestCalculateReadinessEndpoint — POST /readiness/calculate
# ============================================================

class TestCalculateReadinessEndpoint:
    API_PATH = "/api/v1/readiness/calculate"

    def test_calculate_success(self, client, headers):
        """calculate returns valid score → 200 with data_source='manual'."""
        expected = dict(SAMPLE_SCORE_RESPONSE)
        expected["data_source"] = "manual"
        with patch.object(ReadinessService, "calculate", return_value=SAMPLE_SCORE_RESPONSE):
            resp = client.post(self.API_PATH, json={}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 78
        assert data.get("data_source") == "manual"

    def test_calculate_error(self, client, headers):
        """Service raises exception → 400."""
        with patch.object(ReadinessService, "calculate", side_effect=ValueError("Algo salió mal")):
            resp = client.post(self.API_PATH, json={}, headers=headers)
        assert resp.status_code == 400
        assert "error" in resp.json().get("detail", "").lower()

    def test_calculate_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(ReadinessService, "calculate") as mock:
            resp = client.post(self.API_PATH, json={})
        assert resp.status_code == 401
        mock.assert_not_called()
