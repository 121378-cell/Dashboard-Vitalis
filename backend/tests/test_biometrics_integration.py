"""
Tests de integración: endpoints de biometría (biometrics.py).
=============================================================

Cubre los 3 endpoints del router biometrics:
- GET / (obtener biométricos del día)
- POST / (crear/actualizar biométricos)
- GET /history (historial de biométricos)

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
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Biometrics API")
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


@pytest.fixture(autouse=True)
def _mock_readiness():
    """Mockea AnalyticsService.get_readiness_score para evitar dependencia en ReadinessEngine."""
    with patch.object(AnalyticsService, "get_readiness_score") as mock:
        mock.return_value = {
            "score": 75,
            "status": "good",
            "hrv_baseline": 55.0,
            "rhr_baseline": 60.0,
        }
        yield mock


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
# Helpers
# ---------------------------------------------------------------------------


def _create_biometric(
    db_session,
    user_id="test_user",
    date_str=None,
    data=None,
    source="garmin",
    recovery_time=None,
    training_status=None,
    hrv_status=None,
    body_battery=None,
):
    """Crea un registro Biometrics de prueba."""
    if date_str is None:
        date_str = date.today().isoformat()
    if data is None:
        data = {
            "heartRate": 68,
            "hrv": 45,
            "sleep": 7.5,
            "stress": 35,
            "steps": 8500,
            "calories": 2200,
        }
    bio = Biometrics(
        user_id=user_id,
        date=date_str,
        data=json.dumps(data),
        source=source,
        recovery_time=recovery_time,
        training_status=training_status,
        hrv_status=hrv_status,
        body_battery=body_battery,
    )
    db_session.add(bio)
    db_session.commit()
    db_session.refresh(bio)
    return bio


def _create_workout(
    db_session,
    user_id="test_user",
    date_val=None,
    duration=1800,
    calories=300,
    source="garmin",
):
    """Crea un Workout de prueba."""
    if date_val is None:
        date_val = datetime.now(timezone.utc)
    workout = Workout(
        user_id=user_id,
        source=source,
        external_id=f"ext_{calories}_{duration}",
        name="Test Workout",
        date=date_val,
        duration=duration,
        calories=calories,
    )
    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)
    return workout


# ===========================================================================
# GET /
# ===========================================================================


class TestGetBiometricsEndpoint:
    """GET /api/v1/biometrics/"""

    API_PATH = "/api/v1/biometrics/"

    def test_get_with_data(self, client, db_session, headers):
        """Biométricos existentes → 200 + datos completos con readiness."""
        _create_biometric(db_session)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["heartRate"] == 68
        assert data["hrv"] == 45
        assert data["sleep"] == 7.5
        assert data["stress"] == 35
        assert data["steps"] == 8500
        assert data["source"] == "garmin"
        # Readiness fields
        assert data["readiness"] == 75
        assert data["status"] == "good"
        assert data["hrv_baseline"] == 55.0
        assert data["rhr_baseline"] == 60.0
        # Workout defaults
        assert data["calories_baseline"] == 2200
        assert data["calories_workouts"] == 0
        assert data["calories_total"] == 2200
        assert data["workout_duration"] == 0
        assert data["workout_count"] == 0

    def test_get_without_data(self, client, headers):
        """Sin biométricos → 200 + estructura por defecto con readiness."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["heartRate"] is None
        assert data["hrv"] is None
        assert data["source"] == "none"
        assert data["readiness"] == 75
        assert data["calories_total"] == 0
        assert data["workout_count"] == 0

    def test_get_with_workouts(self, client, db_session, headers):
        """Biométricos + entrenamientos → 200 + calorías/duration combinados."""
        today_str = date.today().isoformat()
        _create_biometric(db_session, date_str=today_str)
        _create_workout(db_session, duration=3600, calories=500)
        _create_workout(db_session, duration=1800, calories=300)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Baseline (2200 de _create_biometric) + 500 + 300 = 3000
        assert data["calories_baseline"] == 2200
        assert data["calories_workouts"] == 800
        assert data["calories_total"] == 3000
        assert data["workout_duration"] == 5400  # 3600 + 1800
        assert data["workout_count"] == 2

    def test_get_custom_date(self, client, db_session, headers):
        """Parámetro date_str → datos de esa fecha específica."""
        _create_biometric(db_session, date_str="2024-01-15",
                          data={"heartRate": 72, "calories": 1800})

        resp = client.get(
            f"{self.API_PATH}?date_str=2024-01-15",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["heartRate"] == 72
        assert data["calories_baseline"] == 1800

    def test_get_custom_date_no_data(self, client, headers):
        """Date param sin datos → estructura por defecto."""
        resp = client.get(
            f"{self.API_PATH}?date_str=2024-06-01",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["heartRate"] is None
        assert data["source"] == "none"

    def test_get_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_get_with_extra_fields(self, client, db_session, headers):
        """Biométricos con recovery_time, training_status, hrv_status → incluidos."""
        _create_biometric(
            db_session,
            recovery_time=12,
            training_status="maintaining",
            hrv_status="balanced",
            body_battery=78.5,
        )
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["recovery_time"] == 12
        assert data["training_status"] == "maintaining"
        assert data["hrv_status"] == "balanced"


# ===========================================================================
# POST /
# ===========================================================================


class TestUpsertBiometricsEndpoint:
    """POST /api/v1/biometrics/"""

    API_PATH = "/api/v1/biometrics/"

    def test_upsert_create(self, client, db_session, headers):
        """Nuevos biométricos → 200 + registro creado en DB."""
        payload = {
            "heartRate": 72,
            "hrv": 50,
            "sleep": 8.0,
            "steps": 10000,
        }
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["user_id"] == "test_user"
        assert data["date"] == date.today().isoformat()
        assert data["source"] == "health_connect"

        # Verificar en DB
        bio = db_session.query(Biometrics).filter(
            Biometrics.user_id == "test_user",
            Biometrics.date == date.today().isoformat(),
        ).first()
        assert bio is not None
        stored = json.loads(bio.data)
        assert stored["heartRate"] == 72
        assert stored["hrv"] == 50

    def test_upsert_update(self, client, db_session, headers):
        """Biométricos existentes → 200 + datos actualizados."""
        _create_biometric(db_session, data={"heartRate": 68, "calories": 2000})

        payload = {"heartRate": 75, "calories": 2500, "sleep": 8.0}
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200

        # Verificar actualización
        bio = db_session.query(Biometrics).filter(
            Biometrics.user_id == "test_user",
            Biometrics.date == date.today().isoformat(),
        ).first()
        stored = json.loads(bio.data)
        assert stored["heartRate"] == 75
        assert stored["calories"] == 2500
        assert stored["sleep"] == 8.0

    def test_upsert_custom_date_and_source(self, client, db_session, headers):
        """Parámetros date y source personalizados."""
        payload = {"heartRate": 70, "date": "2024-03-15", "source": "health_connect"}
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2024-03-15"
        assert data["source"] == "health_connect"

        bio = db_session.query(Biometrics).filter(
            Biometrics.user_id == "test_user",
            Biometrics.date == "2024-03-15",
        ).first()
        assert bio is not None
        assert bio.source == "health_connect"

    def test_upsert_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH, json={"heartRate": 70})
        assert resp.status_code == 401


# ===========================================================================
# GET /history
# ===========================================================================


class TestBiometricsHistoryEndpoint:
    """GET /api/v1/biometrics/history"""

    API_PATH = "/api/v1/biometrics/history"

    def test_history_with_data(self, client, db_session, headers):
        """Múltiples registros → 200 + listado cronológico con métricas parseadas."""
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=2)).isoformat(),
            data={"heartRate": 68, "hrv": 45, "sleep": 7.5, "stress": 35, "steps": 8000},
        )
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=1)).isoformat(),
            data={"heartRate": 72, "hrv": 50, "sleep": 8.0, "stress": 30, "steps": 10000},
        )

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Orden cronológico ascendente
        assert data[0]["date"] == (date.today() - timedelta(days=2)).isoformat()
        assert data[1]["date"] == (date.today() - timedelta(days=1)).isoformat()
        # Métricas parseadas
        assert data[0]["restingHr"] == 68
        assert data[0]["hrv"] == 45
        assert data[0]["sleep"] == 7.5
        assert data[1]["restingHr"] == 72
        assert data[1]["hrv"] == 50

    def test_history_filter_by_metric(self, client, db_session, headers):
        """Parámetro metric → solo esa métrica en el resultado."""
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=1)).isoformat(),
            data={"heartRate": 68, "hrv": 45, "sleep": 7.5},
        )
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=2)).isoformat(),
            data={"heartRate": 72, "hrv": 50, "sleep": 8.0},
        )

        resp = client.get(f"{self.API_PATH}?metric=hrv", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        for entry in data:
            assert "hrv" in entry
            assert "date" in entry
            assert "restingHr" not in entry

    def test_history_metric_not_found(self, client, db_session, headers):
        """Metric filter pero el valor es None → excluido del resultado."""
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=1)).isoformat(),
            data={"heartRate": 68},  # Sin stress
        )
        resp = client.get(f"{self.API_PATH}?metric=stress", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_history_empty(self, client, headers):
        """Sin biométricos → 200 + []."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_custom_days(self, client, db_session, headers):
        """Parámetro days → filtrar por rango de fechas."""
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=5)).isoformat(),
            data={"heartRate": 68},
        )
        _create_biometric(
            db_session,
            date_str=(date.today() - timedelta(days=60)).isoformat(),
            data={"heartRate": 72},
        )
        # days=30 (default) → solo incluye el de hace 5 días
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_history_other_user(self, client, db_session, headers):
        """Biométricos de otro usuario → vacío."""
        _create_biometric(
            db_session,
            user_id="other_user",
            date_str=(date.today() - timedelta(days=1)).isoformat(),
            data={"heartRate": 68},
        )
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_history_invalid_days(self, client, headers):
        """Parámetro days fuera de rango (0) → 422."""
        resp = client.get(f"{self.API_PATH}?days=0", headers=headers)
        assert resp.status_code == 422
