"""
Tests de integración: endpoints de sync.py.
=============================================

Cubre los 3 endpoints del router sync:
- POST /sync/garmin  (sincronización Garmin health + activities)
- POST /sync/wger    (sincronización Wger)
- POST /sync/hevy    (sincronización Hevy)

Usa FastAPI TestClient con dependencias override + StaticPool.
"""

import os
import sys
from unittest.mock import patch, Mock, MagicMock
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.token import Token
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.sync_service import SyncService
from app.utils.garmin_exceptions import GarminRateLimitError, GarminAuthError, GarminSessionError


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Sync API")
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
    Override de get_db + patch SessionLocal para interceptar
    llamadas a SessionLocal() dentro de servicios.
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
def headers():
    """Headers estándar de autenticación por x-user-id."""
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine):
    """Session directa para crear datos de prueba."""
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_token(db_session, user_id="test_user", garmin_email="test@garmin.com"):
    """Crea un Token de prueba con credenciales Garmin."""
    token = Token(user_id=user_id, garmin_email=garmin_email, garmin_password="secret")
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


# ===========================================================================
# POST /sync/garmin
# ===========================================================================


class TestSyncGarminEndpoint:
    """POST /sync/garmin"""

    API_PATH = "/api/v1/sync/garmin"

    def test_sync_success(self, client, db_session, headers):
        """Credenciales OK + sync exitoso → 200 + success."""
        _create_token(db_session)

        with (
            patch("app.utils.garmin.get_garmin_client") as mock_get_client,
            patch.object(SyncService, "sync_garmin_health", return_value=True) as mock_health,
            patch.object(SyncService, "sync_garmin_activities", return_value=True) as mock_acts,
        ):
            mock_get_client.return_value = (Mock(), {"success": True})

            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["health"] is True
        assert data["activities"] is True
        mock_health.assert_called_once()
        mock_acts.assert_called_once()

    def test_sync_custom_days(self, client, db_session, headers):
        """days=3 → 200, rango de 3 días."""
        _create_token(db_session)

        with (
            patch("app.utils.garmin.get_garmin_client") as mock_get_client,
            patch.object(SyncService, "sync_garmin_health", return_value=True),
            patch.object(SyncService, "sync_garmin_activities", return_value=True),
        ):
            mock_get_client.return_value = (Mock(), {"success": True})

            resp = client.post(self.API_PATH, params={"days": 3}, headers=headers)
        assert resp.status_code == 200

    def test_sync_days_capped_at_7(self, client, db_session, headers):
        """days=10 → se capa a 7."""
        _create_token(db_session)

        with (
            patch("app.utils.garmin.get_garmin_client") as mock_get_client,
            patch.object(SyncService, "sync_garmin_health", return_value=True) as mock_health,
            patch.object(SyncService, "sync_garmin_activities", return_value=True),
        ):
            mock_get_client.return_value = (Mock(), {"success": True})

            resp = client.post(self.API_PATH, params={"days": 10}, headers=headers)
        assert resp.status_code == 200
        # Verificar que date_range tiene 7 elementos
        call_args = mock_health.call_args[0]
        date_range_arg = call_args[2]  # date_range es el 3er arg posicional
        assert len(date_range_arg) == 7

    def test_sync_garmin_not_connected(self, client, headers):
        """Sin credenciales Garmin → 400."""
        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 400
        assert "not connected" in resp.json()["detail"].lower()

    def test_sync_rate_limit(self, client, db_session, headers):
        """get_garmin_client lanza GarminRateLimitError → 429."""
        _create_token(db_session)

        with patch(
            "app.utils.garmin.get_garmin_client",
            side_effect=GarminRateLimitError("Rate limit exceeded"),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 429

    def test_sync_auth_error(self, client, db_session, headers):
        """get_garmin_client lanza GarminAuthError → 401."""
        _create_token(db_session)

        with patch(
            "app.utils.garmin.get_garmin_client",
            side_effect=GarminAuthError("Auth failed"),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 401

    def test_sync_session_error(self, client, db_session, headers):
        """get_garmin_client lanza GarminSessionError → 401."""
        _create_token(db_session)

        with patch(
            "app.utils.garmin.get_garmin_client",
            side_effect=GarminSessionError("Session expired"),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 401

    def test_sync_no_client(self, client, db_session, headers):
        """get_garmin_client devuelve None → 401."""
        _create_token(db_session)

        with patch(
            "app.utils.garmin.get_garmin_client",
            return_value=(None, None),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 401
        assert "authenticate" in resp.json()["detail"].lower()

    def test_sync_both_fail(self, client, db_session, headers):
        """health y activities fallan → 500."""
        _create_token(db_session)

        with (
            patch("app.utils.garmin.get_garmin_client") as mock_get_client,
            patch.object(SyncService, "sync_garmin_health", return_value=False),
            patch.object(SyncService, "sync_garmin_activities", return_value=False),
        ):
            mock_get_client.return_value = (Mock(), {"success": True})

            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower()

    def test_sync_server_error(self, client, db_session, headers):
        """SyncService lanza excepción → 500."""
        _create_token(db_session)

        with (
            patch("app.utils.garmin.get_garmin_client") as mock_get_client,
            patch.object(
                SyncService, "sync_garmin_health", side_effect=Exception("DB timeout")
            ),
        ):
            mock_get_client.return_value = (Mock(), {"success": True})

            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "Garmin sync error" in resp.json()["detail"]

    def test_sync_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /sync/wger
# ===========================================================================


class TestSyncWgerEndpoint:
    """POST /sync/wger"""

    API_PATH = "/api/v1/sync/wger"

    def test_sync_wger_success(self, client, headers):
        """Wger sync exitoso → 200."""
        with patch.object(
            SyncService, "sync_wger_workouts", return_value=True
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_sync_wger_fail(self, client, headers):
        """Wger sync falla → 500."""
        with patch.object(
            SyncService, "sync_wger_workouts", return_value=False
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower()

    def test_sync_wger_error(self, client, headers):
        """SyncService lanza excepción → 500."""
        with patch.object(
            SyncService, "sync_wger_workouts", side_effect=Exception("Wger API error")
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500

    def test_sync_wger_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /sync/hevy
# ===========================================================================


class TestSyncHevyEndpoint:
    """POST /sync/hevy"""

    API_PATH = "/api/v1/sync/hevy"

    def test_sync_hevy_success(self, client, headers):
        """Hevy sync exitoso → 200."""
        with patch.object(
            SyncService, "sync_hevy_workouts", return_value=True
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_sync_hevy_fail(self, client, headers):
        """Hevy sync falla → 500."""
        with patch.object(
            SyncService, "sync_hevy_workouts", return_value=False
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower()

    def test_sync_hevy_error(self, client, headers):
        """SyncService lanza excepción → 500."""
        with patch.object(
            SyncService, "sync_hevy_workouts", side_effect=Exception("Hevy API error")
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500

    def test_sync_hevy_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401
