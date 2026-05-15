"""
Tests de integración para endpoints de master_plan.py
======================================================
Cubre los 6 endpoints del router master-plan (prefix: /master-plan en /api/v1):
- POST   /master-plan/create                           → Crear plan maestro
- GET    /master-plan/active                           → Plan activo
- GET    /master-plan/{master_plan_id}/progress        → Progreso del plan
- POST   /master-plan/{master_plan_id}/propose-next-week → Proponer siguiente semana
- POST   /master-plan/weeks/{weekly_plan_id}/confirm   → Confirmar semana
- DELETE /master-plan/{master_plan_id}                 → Cancelar plan
"""

import os
import sys
from unittest.mock import patch
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.base import Base
from app.models.master_plan import MasterPlan
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.master_plan_service import MasterPlanService

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Test App ──────────────────────────────────────────────────────────────
test_app = FastAPI(title="Test ATLAS MasterPlan API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _override_db(test_engine):
    """Override get_db dependency for in-memory test DB."""
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

    yield

    test_app.dependency_overrides = {}


@pytest.fixture
def client(test_engine):
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine):
    """Direct DB session for seeding test data."""
    TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
    db = TestSessionLocal()
    yield db
    db.close()


# ── Sample Data ────────────────────────────────────────────────────────────

SAMPLE_MASTER_PLAN = {
    "id": 1,
    "title": "Plan de 12 semanas",
    "goal": "Aumentar sentadilla a 150kg",
    "start_date": date.today().isoformat(),
    "target_date": "2025-06-01",
    "status": "active",
    "total_weeks": 12,
    "current_week": 1,
}

SAMPLE_PROGRESS = {
    "master_plan_id": 1,
    "total_weeks": 12,
    "completed_weeks": 3,
    "progress_pct": 25.0,
    "current_week": 4,
}

SAMPLE_WEEKLY_PROPOSAL = {
    "week_number": 4,
    "sessions": [
        {"day": "Monday", "focus": "Push", "exercises": []},
        {"day": "Thursday", "focus": "Pull", "exercises": []},
    ],
}

SAMPLE_CONFIRMED_WEEK = {
    "weekly_plan_id": 10,
    "week_number": 3,
    "status": "confirmed",
}


def _create_master_plan(db_session, user_id="test_user", plan_id=1, status="active"):
    """Seed a MasterPlan record and return it."""
    plan = MasterPlan(
        id=plan_id,
        user_id=user_id,
        title="Plan de prueba",
        goal="Aumentar sentadilla a 150kg",
        start_date=date.today(),
        target_date=date(2025, 6, 1),
        status=status,
        total_weeks=12,
        current_week=1,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


# ══════════════════════════════════════════════════════════════════════════
# POST /master-plan/create
# ══════════════════════════════════════════════════════════════════════════


class TestCreateMasterPlanEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan/create"

    def test_success(self, client, headers):
        with patch.object(
            MasterPlanService, "create_master_plan",
            return_value=SAMPLE_MASTER_PLAN,
        ) as mock_create:
            resp = client.post(
                self.API_PATH,
                json={
                    "goal": "Aumentar sentadilla a 150kg",
                    "preferred_days": ["monday", "wednesday", "friday"],
                    "time_per_session_minutes": 60,
                },
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == 1
        assert data["data"]["goal"] == "Aumentar sentadilla a 150kg"
        mock_create.assert_called_once()

    def test_success_with_target_date(self, client, headers):
        with patch.object(
            MasterPlanService, "create_master_plan",
            return_value=SAMPLE_MASTER_PLAN,
        ) as mock_create:
            resp = client.post(
                self.API_PATH,
                json={
                    "goal": "Correr 10k",
                    "target_date": "2025-08-15",
                    "preferred_days": ["monday", "thursday"],
                    "time_per_session_minutes": 45,
                    "intensity_preference": "high",
                },
                headers=headers,
            )

        assert resp.status_code == 200
        # Verify target_date was parsed to date object
        args, kwargs = mock_create.call_args
        assert kwargs["target_date"] == date(2025, 8, 15)

    def test_success_with_restrictions(self, client, headers):
        with patch.object(
            MasterPlanService, "create_master_plan",
            return_value=SAMPLE_MASTER_PLAN,
        ):
            resp = client.post(
                self.API_PATH,
                json={
                    "goal": "Ganar masa muscular",
                    "restrictions": "Hombro derecho lesionado - evitar press militar",
                    "preferred_days": ["monday", "tuesday", "thursday", "friday", "saturday"],
                    "time_per_session_minutes": 60,
                },
                headers=headers,
            )

        assert resp.status_code == 200

    def test_error(self, client, headers):
        with patch.object(
            MasterPlanService, "create_master_plan",
            side_effect=Exception("AI service unavailable"),
        ):
            resp = client.post(
                self.API_PATH,
                json={
                    "goal": "Test",
                    "preferred_days": ["monday"],
                    "time_per_session_minutes": 30,
                },
                headers=headers,
            )

        assert resp.status_code == 500

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={
                "goal": "Test",
                "preferred_days": ["monday"],
                "time_per_session_minutes": 30,
            },
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# GET /master-plan/active
# ══════════════════════════════════════════════════════════════════════════


class TestGetActiveMasterPlanEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan/active"

    def test_has_plan(self, client, headers):
        with patch.object(
            MasterPlanService, "get_active_master_plan",
            return_value=SAMPLE_MASTER_PLAN,
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["has_plan"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["status"] == "active"

    def test_no_plan(self, client, headers):
        with patch.object(
            MasterPlanService, "get_active_master_plan",
            return_value=None,
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["has_plan"] is False
        assert "no hay" in data["message"].lower()

    def test_error(self, client, headers):
        with patch.object(
            MasterPlanService, "get_active_master_plan",
            side_effect=Exception("DB error"),
        ):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client):
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# GET /master-plan/{master_plan_id}/progress
# ══════════════════════════════════════════════════════════════════════════
# NOTA: Este endpoint NO usa get_current_user_id


class TestGetMasterPlanProgressEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan"

    def test_success(self, client, headers):
        with patch.object(
            MasterPlanService, "get_master_plan_progress",
            return_value=SAMPLE_PROGRESS,
        ):
            resp = client.get(f"{self.API_PATH}/1/progress", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["master_plan_id"] == 1
        assert data["data"]["progress_pct"] == 25.0

    def test_error(self, client, headers):
        with patch.object(
            MasterPlanService, "get_master_plan_progress",
            side_effect=Exception("Plan not found"),
        ):
            with pytest.raises(Exception):
                client.get(f"{self.API_PATH}/999/progress", headers=headers)

    # Sin test_unauthorized: el endpoint no tiene get_current_user_id


# ══════════════════════════════════════════════════════════════════════════
# POST /master-plan/{master_plan_id}/propose-next-week
# ══════════════════════════════════════════════════════════════════════════
# NOTA: Este endpoint NO usa get_current_user_id


class TestProposeNextWeekEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan"

    def test_success(self, client, headers):
        with patch.object(
            MasterPlanService, "propose_next_week",
            return_value=SAMPLE_WEEKLY_PROPOSAL,
        ):
            resp = client.post(
                f"{self.API_PATH}/1/propose-next-week",
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["week_number"] == 4

    def test_error(self, client, headers):
        with patch.object(
            MasterPlanService, "propose_next_week",
            side_effect=Exception("No master plan found"),
        ):
            with pytest.raises(Exception):
                client.post(
                    f"{self.API_PATH}/999/propose-next-week",
                    headers=headers,
                )

    # Sin test_unauthorized: el endpoint no tiene get_current_user_id


# ══════════════════════════════════════════════════════════════════════════
# POST /master-plan/weeks/{weekly_plan_id}/confirm
# ══════════════════════════════════════════════════════════════════════════
# NOTA: Este endpoint NO usa get_current_user_id


class TestConfirmWeekEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan/weeks"

    def test_success(self, client, headers):
        with patch.object(
            MasterPlanService, "confirm_week",
            return_value=SAMPLE_CONFIRMED_WEEK,
        ):
            resp = client.post(
                f"{self.API_PATH}/10/confirm",
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "confirmed"
        assert "confirmada" in data["message"].lower()

    def test_error(self, client, headers):
        with patch.object(
            MasterPlanService, "confirm_week",
            side_effect=Exception("Weekly plan not found"),
        ):
            with pytest.raises(Exception):
                client.post(
                    f"{self.API_PATH}/999/confirm",
                    headers=headers,
                )

    # Sin test_unauthorized: el endpoint no tiene get_current_user_id


# ══════════════════════════════════════════════════════════════════════════
# DELETE /master-plan/{master_plan_id}
# ══════════════════════════════════════════════════════════════════════════


class TestCancelMasterPlanEndpoint:
    API_PATH = f"{settings.API_V1_STR}/master-plan"

    def test_success(self, client, headers, db_session):
        plan = _create_master_plan(db_session)
        resp = client.delete(f"{self.API_PATH}/{plan.id}", headers=headers)

        assert resp.status_code == 200
        assert "cancelado" in resp.json()["message"].lower()

        # Verify DB was updated
        db_session.refresh(plan)
        assert plan.status == "cancelled"

    def test_not_found(self, client, headers):
        resp = client.delete(f"{self.API_PATH}/999", headers=headers)

        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"].lower()

    # Sin test_unauthorized: el endpoint DELETE /{master_plan_id} NO usa get_current_user_id
    # (li mismo que progress, propose-next-week, confirm)
