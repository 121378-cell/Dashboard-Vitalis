"""
Tests de integración: endpoints de daily loop (daily_loop.py).
===============================================================

Cubre los 3 endpoints del router daily_loop:
- GET /status  — estado de readiness cacheados
- POST /run-now  — ejecutar daily loop inmediatamente
- GET /history  — historial de daily readiness

Los servicios internos (DailyLoopService) se mockean para evitar
dependencias en la tabla raw SQL daily_readiness y ReadinessEngine.

Usa FastAPI TestClient con dependencias override + StaticPool.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.daily_loop_service import DailyLoopService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Daily Loop API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def test_engine():
    """Engine SQLite en memoria NUEVO para cada test."""
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
    """
    Override de get_db + patch SessionLocal.
    """
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
    """TestClient con x-user-id header."""
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def db_session(test_engine):
    """Session directa para crear datos de prueba."""
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

SAMPLE_STATUS_DATA = {
    "has_data": True,
    "readiness_score": 78,
    "category": "BUENO",
    "color": "green",
    "body_battery": 85.0,
    "resting_hr": 58,
    "sleep_hours": 7.5,
    "stress": 32,
    "hrv": 48,
    "biometrics_source": "garmin",
    "summary": "Buena recuperación. Listo para entrenar.",
    "insights": [
        {"type": "recovery", "message": "HRV estable, buena recuperación"},
        {"type": "sleep", "message": "7.5h de sueño, dentro del rango óptimo"},
    ],
    "session_adaptation": None,
}

SAMPLE_HISTORY_DATA = [
    {
        "date": (date.today() - timedelta(days=2)).isoformat(),
        "readiness_score": 82,
        "category": "ÓPTIMO",
        "color": "green",
        "body_battery": 90.0,
        "resting_hr": 55,
        "sleep_hours": 8.0,
        "stress": 28,
        "summary": "Recuperación óptima",
    },
    {
        "date": (date.today() - timedelta(days=1)).isoformat(),
        "readiness_score": 65,
        "category": "MODERADO",
        "color": "yellow",
        "body_battery": 60.0,
        "resting_hr": 62,
        "sleep_hours": 6.0,
        "stress": 45,
        "summary": "Fatiga moderada, considerar descanso",
    },
]

SAMPLE_RUN_RESULT = {
    "has_data": True,
    "readiness_score": 78,
    "category": "BUENO",
    "color": "green",
    "body_battery": 85.0,
    "resting_hr": 58,
    "sleep_hours": 7.5,
    "stress": 32,
    "summary": "Daily loop completado. Buena recuperación.",
    "insights": [
        {"type": "recovery", "message": "HRV estable"},
        {"type": "readiness", "message": "Puntuación 78/100"},
    ],
    "session_adaptation": {
        "type": "MAINTENANCE",
        "description": "Sesión de mantenimiento",
    },
}


# ===========================================================================
# GET /status
# ===========================================================================


class TestDailyStatusEndpoint:
    """GET /api/v1/daily/status"""

    API_PATH = "/api/v1/daily/status"

    def test_status_with_data(self, client, headers):
        """Datos de readiness cacheados → 200 + datos completos."""
        with patch.object(DailyLoopService, "get_status") as mock:
            mock.return_value = SAMPLE_STATUS_DATA

            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is True
        assert data["readiness_score"] == 78
        assert data["category"] == "BUENO"
        assert data["color"] == "green"
        assert data["body_battery"] == 85.0
        assert data["resting_hr"] == 58
        assert data["sleep_hours"] == 7.5
        assert len(data["insights"]) == 2
        assert data["summary"] == "Buena recuperación. Listo para entrenar."

    def test_status_no_data(self, client, headers):
        """Sin datos de readiness → 200 + has_data=False."""
        with patch.object(DailyLoopService, "get_status") as mock:
            mock.return_value = {"has_data": False}

            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is False

    def test_status_error(self, client, headers):
        """Error interno → 200 + has_data=False + mensaje de error."""
        with patch.object(DailyLoopService, "get_status") as mock:
            mock.return_value = {"has_data": False, "error": "Error de conexión"}

            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is False
        assert "error" in data

    def test_status_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /run-now
# ===========================================================================


class TestRunDailyLoopEndpoint:
    """POST /api/v1/daily/run-now"""

    API_PATH = "/api/v1/daily/run-now"

    def test_run_success(self, client, headers):
        """Ejecución completa → 200 + resultado del loop."""
        with patch.object(DailyLoopService, "run_daily_loop") as mock:
            mock.return_value = SAMPLE_RUN_RESULT

            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["readiness_score"] == 78
        assert data["category"] == "BUENO"
        assert data["summary"].startswith("Daily loop completado")
        assert len(data["insights"]) == 2
        assert data["session_adaptation"]["type"] == "MAINTENANCE"

    def test_run_no_data(self, client, headers):
        """Loop ejecutado sin suficientes datos → 200 + has_data=False."""
        with patch.object(DailyLoopService, "run_daily_loop") as mock:
            mock.return_value = {"has_data": False, "message": "No hay datos biométricos para hoy"}

            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is False

    def test_run_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /history
# ===========================================================================


class TestDailyHistoryEndpoint:
    """GET /api/v1/daily/history"""

    API_PATH = "/api/v1/daily/history"

    def test_history_with_data(self, client, headers):
        """Historial con datos → 200 + listado."""
        with patch.object(DailyLoopService, "get_history") as mock:
            mock.return_value = SAMPLE_HISTORY_DATA

            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["readiness_score"] == 82
        assert data[0]["category"] == "ÓPTIMO"
        assert data[1]["readiness_score"] == 65
        assert data[1]["category"] == "MODERADO"
        # Orden cronológico
        assert data[0]["date"] < data[1]["date"]

    def test_history_empty(self, client, headers):
        """Sin historial → 200 + []."""
        with patch.object(DailyLoopService, "get_history") as mock:
            mock.return_value = []

            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_custom_days(self, client, headers):
        """Parámetro days personalizado → pasado al servicio."""
        with patch.object(DailyLoopService, "get_history") as mock:
            mock.return_value = [SAMPLE_HISTORY_DATA[0]]

            resp = client.get(f"{self.API_PATH}?days=7", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        # Verificar que el servicio recibió days=7
        mock.assert_called_once()
        call_args = mock.call_args[0]  # (db, user_id, days)
        assert call_args[2] == 7

    def test_history_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_history_invalid_days(self, client, headers):
        """Parámetro days fuera de rango (0) → 422."""
        resp = client.get(f"{self.API_PATH}?days=0", headers=headers)
        assert resp.status_code == 422
