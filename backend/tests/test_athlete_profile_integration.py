"""
Tests de integración: endpoints de athlete_profile.py.
=======================================================

Cubre los 2 endpoints del router athlete-profile:
- GET /athlete-profile (perfil completo del atleta)
- GET /athlete-profile/coach-context (contexto para el coach)

Usa FastAPI TestClient con dependencias override + StaticPool.
"""

import os
import sys
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
from app.services.athlete_profile_service import AthleteProfileService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Athlete Profile API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SAMPLE_PROFILE = {
    "user_id": "test_user",
    "name": "Sergi",
    "age": 30,
    "fitness_level": "intermedio",
    "activity_level": "activo",
    "sleep_quality": "buena",
    "recovery_capacity": "buena",
    "stress_level": "moderado",
    "avg_hrv": 65.0,
    "avg_rhr": 58.0,
    "avg_sleep": 7.5,
    "avg_stress": 28.0,
    "avg_steps": 8500,
    "total_workouts": 45,
    "streak_days": 12,
}

SAMPLE_COACH_CONTEXT = {
    "profile_summary": "Sergi es un atleta de nivel intermedio con buena recuperación.",
    "recommendations": {
        "intensity": "Mantener intensidad moderada-alta",
        "recovery": "Priorizar sueño esta semana",
        "sleep": "Mantener horario regular",
        "stress": "Incorporar meditación post-entreno",
    },
    "key_insights": [
        {"tema": "Progresión", "mensaje": "Has mejorado un 15% en fuerza en 4 semanas"},
    ],
    "aging_considerations": {
        "adjusted_intensity": "N/A",
        "recommendation": "Sin ajustes por edad",
    },
}


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


# ===========================================================================
# GET /athlete-profile
# ===========================================================================


class TestAthleteProfileEndpoint:
    """GET /athlete-profile/athlete-profile"""

    API_PATH = "/api/v1/athlete-profile/athlete-profile"

    def test_get_profile_success(self, client, headers):
        """GET athlete-profile → 200 + perfil completo."""
        with patch.object(
            AthleteProfileService, "get_profile_dict", return_value=SAMPLE_PROFILE
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test_user"
        assert data["fitness_level"] == "intermedio"
        assert data["total_workouts"] == 45

    def test_get_profile_error(self, client, headers):
        """AthleteProfileService lanza excepción → 500."""
        with patch.object(
            AthleteProfileService,
            "get_profile_dict",
            side_effect=Exception("DB connection error"),
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "DB connection error" in resp.json()["detail"]

    def test_get_profile_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /athlete-profile/coach-context
# ===========================================================================


class TestCoachContextEndpoint:
    """GET /athlete-profile/athlete-profile/coach-context"""

    API_PATH = "/api/v1/athlete-profile/athlete-profile/coach-context"

    def test_coach_context_success(self, client, headers):
        """GET coach-context → 200 + contexto completo."""
        with patch.object(
            AthleteProfileService, "get_coach_context", return_value=SAMPLE_COACH_CONTEXT
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "profile_summary" in data
        assert "recommendations" in data
        assert "key_insights" in data
        assert data["recommendations"]["intensity"] == "Mantener intensidad moderada-alta"

    def test_coach_context_error(self, client, headers):
        """AthleteProfileService lanza excepción → 500."""
        with patch.object(
            AthleteProfileService,
            "get_coach_context",
            side_effect=Exception("Service unavailable"),
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "Service unavailable" in resp.json()["detail"]

    def test_coach_context_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
