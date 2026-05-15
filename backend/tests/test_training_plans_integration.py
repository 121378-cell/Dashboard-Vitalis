"""
Integration tests for Training Plans endpoints.
================================================

Endpoints:
- POST /api/v1/plans/generate
- GET  /api/v1/plans/current
- PUT  /api/v1/plans/sessions/{session_id}
- POST /api/v1/plans/detect-completed
- GET  /api/v1/plans/history
- DELETE /api/v1/plans/{plan_id}
- POST /api/v1/plans/sessions/{session_id}/adapt
- PUT  /api/v1/plans/sessions/{session_id}/complete
- GET  /api/v1/plans/sessions/{session_id}/progression
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
from app.models.adaptive_training_plan import AdaptivePlannedSession, AdaptivePlanAdjustment
from app.models.training_plan import WeeklyPlan, PlanSession, PersonalRecord
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.training_plan_service import TrainingPlanService
from app.services.ai_service import AIService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Training Plans API")
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

SAMPLE_WEEK_START = date.today().isoformat()
SAMPLE_WEEK_END = (date.today() + timedelta(days=6)).isoformat()

SAMPLE_GENERATED_PLAN = {
    "plan_id": 1,
    "week_start": SAMPLE_WEEK_START,
    "week_end": SAMPLE_WEEK_END,
    "goal": "mejorar_resistencia",
    "sessions": [
        {
            "day": "Lunes",
            "session_type": "cardio",
            "title": "Carrera suave",
            "duration_minutes": 45,
            "intensity": "moderada",
            "description": "Carrera continua a ritmo conversacional",
        },
        {
            "day": "Miércoles",
            "session_type": "strength",
            "title": "Fuerza general",
            "duration_minutes": 60,
            "intensity": "alta",
            "description": "Circuito de fuerza compuesto",
            "exercises": [
                {"name": "Sentadilla", "sets": 4, "reps": 8, "weight": 80},
                {"name": "Press banca", "sets": 4, "reps": 8, "weight": 60},
            ],
        },
    ],
    "weekly_metrics": {"total_sessions": 2, "total_minutes": 105},
}

SAMPLE_CURRENT_PLAN = {
    "plan_id": 1,
    "week_start": SAMPLE_WEEK_START,
    "week_end": SAMPLE_WEEK_END,
    "goal": "mejorar_resistencia",
    "status": "active",
    "created_at": datetime.now().isoformat(),
    "ai_reasoning": "Plan basado en perfil atlético",
    "progress": {"completed": 1, "total": 2, "percentage": 50.0},
    "plan": {"sessions": SAMPLE_GENERATED_PLAN["sessions"], "weekly_metrics": SAMPLE_GENERATED_PLAN["weekly_metrics"]},
}

SAMPLE_UPDATED_SESSION = {
    "id": 1,
    "day": "Lunes",
    "session_type": "cardio",
    "title": "Carrera moderada",
    "duration_minutes": 50,
    "intensity": "alta",
    "description": "Carrera a ritmo rápido",
    "completed": False,
}

SAMPLE_HISTORY_PLANS = [
    {"plan_id": 1, "week_start": (date.today() - timedelta(days=7)).isoformat(), "goal": "fuerza", "status": "completed"},
    {"plan_id": 2, "week_start": SAMPLE_WEEK_START, "goal": "mejorar_resistencia", "status": "active"},
]


def _create_adaptive_session(
    db_session,
    plan_id=1,
    session_date=None,
    day_of_week="Lunes",
    session_type="cardio",
    title="Carrera suave",
    description="Carrera continua",
    duration_minutes=45,
    intensity="moderada",
    exercises_json=None,
    completed=False,
):
    if session_date is None:
        session_date = date.today()
    session = AdaptivePlannedSession(
        plan_id=plan_id,
        session_date=session_date,
        day_of_week=day_of_week,
        session_type=session_type,
        title=title,
        description=description,
        duration_minutes=duration_minutes,
        intensity=intensity,
        exercises_json=exercises_json or json.dumps([]),
        completed=completed,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


# ============================================================
# TestGeneratePlanEndpoint — POST /training-plans/generate
# ============================================================

class TestGeneratePlanEndpoint:
    API_PATH = "/api/v1/plans/generate"

    def test_generate_success(self, client, headers):
        """Valid request → plan generated successfully."""
        with patch.object(TrainingPlanService, "generate_weekly_plan", return_value=SAMPLE_GENERATED_PLAN):
            resp = client.post(self.API_PATH, json={
                "goal": "mejorar_resistencia",
                "training_days": ["Lunes", "Miércoles", "Viernes"],
            }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Plan de entrenamiento generado" in data["message"]
        assert data["data"]["goal"] == "mejorar_resistencia"

    def test_generate_with_all_options(self, client, headers):
        """Full request with all optional fields."""
        with patch.object(TrainingPlanService, "generate_weekly_plan", return_value=SAMPLE_GENERATED_PLAN):
            resp = client.post(self.API_PATH, json={
                "goal": "fuerza",
                "week_start": date.today().isoformat(),
                "training_days": ["Lunes", "Miércoles"],
                "time_available": {"Lunes": 60, "Miércoles": 45},
                "session_types": ["strength", "cardio"],
                "intensity_preference": "moderada",
                "consider_readiness": True,
                "restrictions": "Evitar impacto en rodillas",
            }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_generate_conflict(self, client, headers):
        """Service returns error → 409 Conflict."""
        error_plan = {"error": "Ya existe un plan activo para esta semana", "plan_id": 1}
        with patch.object(TrainingPlanService, "generate_weekly_plan", return_value=error_plan):
            resp = client.post(self.API_PATH, json={
                "goal": "mejorar_resistencia",
                "training_days": ["Lunes"],
            }, headers=headers)
        assert resp.status_code == 409
        assert "Ya existe un plan activo" in resp.json()["detail"]

    def test_generate_invalid_week_start(self, client, headers):
        """Invalid date format → 400."""
        resp = client.post(self.API_PATH, json={
            "goal": "mejorar_resistencia",
            "week_start": "not-a-date",
            "training_days": ["Lunes"],
        }, headers=headers)
        assert resp.status_code == 400
        assert "Formato de fecha inválido" in resp.json()["detail"]

    def test_generate_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "generate_weekly_plan") as mock:
            resp = client.post(self.API_PATH, json={
                "goal": "mejorar_resistencia",
                "training_days": ["Lunes"],
            })
        assert resp.status_code == 401
        mock.assert_not_called()

    def test_generate_no_goal(self, client, headers):
        """Missing required goal field → 422."""
        resp = client.post(self.API_PATH, json={
            "training_days": ["Lunes"],
        }, headers=headers)
        assert resp.status_code == 422


# ============================================================
# TestGetCurrentPlanEndpoint — GET /training-plans/current
# ============================================================

class TestGetCurrentPlanEndpoint:
    API_PATH = "/api/v1/plans/current"

    def test_current_with_plan(self, client, headers):
        """Active plan exists → has_plan=True with data."""
        with patch.object(TrainingPlanService, "get_current_plan", return_value=SAMPLE_CURRENT_PLAN):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["has_plan"] is True
        assert data["data"]["goal"] == "mejorar_resistencia"

    def test_current_no_plan(self, client, headers):
        """No active plan → has_plan=False."""
        with patch.object(TrainingPlanService, "get_current_plan", return_value=None):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["has_plan"] is False
        assert "No hay plan activo" in data["message"]

    def test_current_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "get_current_plan") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestUpdateSessionEndpoint — PUT /training-plans/sessions/{session_id}
# ============================================================

class TestUpdateSessionEndpoint:
    API_PATH = "/api/v1/plans/sessions"

    def test_update_title(self, client, headers):
        """Update session title → success."""
        with patch.object(TrainingPlanService, "update_session", return_value=SAMPLE_UPDATED_SESSION):
            resp = client.put(f"{self.API_PATH}/1", json={
                "title": "Carrera moderada",
                "duration_minutes": 50,
                "intensity": "alta",
            }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Sesión actualizada" in data["message"]

    def test_update_completed_flag(self, client, headers):
        """Toggle completed status."""
        with patch.object(TrainingPlanService, "update_session", return_value=SAMPLE_UPDATED_SESSION):
            resp = client.put(f"{self.API_PATH}/1", json={
                "completed": True,
            }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_update_empty_body(self, client, headers):
        """No fields provided → 400."""
        resp = client.put(f"{self.API_PATH}/1", json={}, headers=headers)
        assert resp.status_code == 400
        assert "No se proporcionaron campos" in resp.json()["detail"]

    def test_update_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "update_session") as mock:
            resp = client.put(f"{self.API_PATH}/1", json={"title": "Test"}, headers={})
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestDetectCompletedEndpoint — POST /training-plans/detect-completed
# ============================================================

class TestDetectCompletedEndpoint:
    API_PATH = "/api/v1/plans/detect-completed"

    def test_detect_success(self, client, headers):
        """Auto-detect completed sessions → sessions returned."""
        completed = [{"session_id": 1, "session_title": "Carrera suave", "garmin_activity_id": "12345"}]
        with patch.object(TrainingPlanService, "auto_detect_completed_sessions", return_value=completed):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["detected_count"] == 1
        assert len(data["data"]["sessions"]) == 1

    def test_detect_none_found(self, client, headers):
        """No sessions detected → count 0."""
        with patch.object(TrainingPlanService, "auto_detect_completed_sessions", return_value=[]):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["detected_count"] == 0

    def test_detect_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "auto_detect_completed_sessions") as mock:
            resp = client.post(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestPlanHistoryEndpoint — GET /training-plans/history
# ============================================================

class TestPlanHistoryEndpoint:
    API_PATH = "/api/v1/plans/history"

    def test_history_with_plans(self, client, headers):
        """Historical plans exist → list returned."""
        with patch.object(TrainingPlanService, "get_plan_history", return_value=SAMPLE_HISTORY_PLANS):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["total"] == 2
        assert len(data["data"]["plans"]) == 2

    def test_history_empty(self, client, headers):
        """No historical plans → empty list."""
        with patch.object(TrainingPlanService, "get_plan_history", return_value=[]):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0
        assert data["data"]["plans"] == []

    def test_history_custom_limit(self, client, headers):
        """Custom limit param forwarded to service."""
        with patch.object(TrainingPlanService, "get_plan_history", return_value=SAMPLE_HISTORY_PLANS[:1]) as mock:
            resp = client.get(f"{self.API_PATH}?limit=1", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["plans"]) == 1
        # Verify limit was forwarded
        assert mock.call_args[1].get("limit") == 1 or mock.call_args[0][2] == 1

    def test_history_invalid_limit(self, client, headers):
        """limit=0 → 400, limit=51 → 400."""
        resp = client.get(f"{self.API_PATH}?limit=0", headers=headers)
        assert resp.status_code == 400
        resp = client.get(f"{self.API_PATH}?limit=51", headers=headers)
        assert resp.status_code == 400

    def test_history_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "get_plan_history") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestCancelPlanEndpoint — DELETE /training-plans/{plan_id}
# ============================================================

class TestCancelPlanEndpoint:
    API_PATH = "/api/v1/plans"

    def test_cancel_success(self, client, headers):
        """Cancel existing plan → success."""
        with patch.object(TrainingPlanService, "cancel_plan", return_value=True):
            resp = client.delete(f"{self.API_PATH}/1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "cancelado" in data["message"].lower()

    def test_cancel_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(TrainingPlanService, "cancel_plan") as mock:
            resp = client.delete(f"{self.API_PATH}/1")
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestAdaptSessionEndpoint — POST /training-plans/sessions/{session_id}/adapt
# ============================================================

class TestAdaptSessionEndpoint:
    API_PATH = "/api/v1/plans/sessions"

    def test_adapt_success(self, client, db_session, headers):
        """Adapt session via AI → updated session returned."""
        session = _create_adaptive_session(db_session, exercises_json=json.dumps(
            [{"name": "Sentadilla", "sets": 4, "reps": 8, "weight": 80}]
        ))
        adapted_json = json.dumps({
            "title": "Fuerza piernas modificada",
            "description": "Circuito de piernas ajustado",
            "exercises": [{"name": "Sentadilla búlgara", "sets": 3, "reps": 10, "weight": 60}],
            "session_type": "strength",
            "duration_minutes": 50,
            "intensity": "moderada",
        })
        ai_response = {"content": adapted_json}
        with patch.object(AIService, "_generate_chat_response", return_value=ai_response):
            resp = client.post(
                f"{self.API_PATH}/{session.id}/adapt",
                json={"user_request": "Cambia a ejercicios de piernas"},
                headers=headers,
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data["status"] == "success"
        assert "Sesión adaptada" in data["message"]
        assert data["data"]["title"] == "Fuerza piernas modificada"
        assert len(data["data"]["exercises"]) == 1

        # Verify adjustment was logged
        adjustment = db_session.query(AdaptivePlanAdjustment).filter(
            AdaptivePlanAdjustment.session_id == session.id
        ).first()
        assert adjustment is not None
        assert "Cambia a ejercicios de piernas" in adjustment.reason

    def test_adapt_session_not_found(self, client, headers):
        """Non-existent session → 404."""
        with patch.object(AIService, "_generate_chat_response") as mock:
            resp = client.post(
                f"{self.API_PATH}/99999/adapt",
                json={"user_request": "Cambia a ejercicios de piernas"},
                headers=headers,
            )
        assert resp.status_code == 404
        mock.assert_not_called()

    def test_adapt_unauthorized(self, client):
        """No x-user-id → 401."""
        with patch.object(AIService, "_generate_chat_response") as mock:
            resp = client.post(
                f"{self.API_PATH}/1/adapt",
                json={"user_request": "Test"},
            )
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestCompleteSessionEndpoint — PUT /training-plans/sessions/{session_id}/complete
# ============================================================

class TestCompleteSessionEndpoint:
    API_PATH = "/api/v1/plans/sessions"

    def test_complete_success(self, client, db_session, headers):
        """Mark session as completed → success."""
        session = _create_adaptive_session(db_session)
        resp = client.put(
            f"{self.API_PATH}/{session.id}/complete",
            json={"completed": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["completed"] is True
        assert "marcada como completada" in data["message"]

        # Verify DB was updated
        db_session.refresh(session)
        assert session.completed is True

    def test_complete_with_garmin_activity(self, client, db_session, headers):
        """Mark completed with Garmin activity ID."""
        session = _create_adaptive_session(db_session)
        resp = client.put(
            f"{self.API_PATH}/{session.id}/complete",
            json={"completed": True, "garmin_activity_id": "garmin_123"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["completed"] is True
        assert data["data"]["garmin_activity_id"] == "garmin_123"

        db_session.refresh(session)
        assert session.garmin_activity_id == "garmin_123"

    def test_complete_unmark(self, client, db_session, headers):
        """Toggle session back to incomplete."""
        session = _create_adaptive_session(db_session, completed=True)
        resp = client.put(
            f"{self.API_PATH}/{session.id}/complete",
            json={"completed": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["completed"] is False
        assert "no completada" in resp.json()["message"]

    def test_complete_not_found(self, client, headers):
        """Non-existent session → 404."""
        resp = client.put(
            f"{self.API_PATH}/99999/complete",
            json={"completed": True},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_complete_unauthorized(self, client):
        """No x-user-id → 401."""
        resp = client.put(
            f"{self.API_PATH}/1/complete",
            json={"completed": True},
        )
        assert resp.status_code == 401


# ============================================================
# TestSessionProgressionEndpoint — GET /training-plans/sessions/{session_id}/progression
# ============================================================

class TestSessionProgressionEndpoint:
    API_PATH = "/api/v1/plans/sessions"

    def test_progression_success(self, client, db_session, headers):
        """Existing session → progression suggestions returned."""
        session = _create_adaptive_session(db_session)
        expected_progressions = [
            {"exercise": "Sentadilla", "current_load": 80, "suggested_load": 85, "reason": "Progresión lineal"},
        ]
        with patch("app.api.api_v1.endpoints.training_plans.get_progressions_for_session",
                    return_value=expected_progressions):
            resp = client.get(f"{self.API_PATH}/{session.id}/progression", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["session_id"] == session.id
        assert len(data["data"]["progressions"]) == 1
        assert data["data"]["progressions"][0]["exercise"] == "Sentadilla"

    def test_progression_empty(self, client, db_session, headers):
        """No progression data → empty list."""
        session = _create_adaptive_session(db_session)
        with patch("app.api.api_v1.endpoints.training_plans.get_progressions_for_session",
                    return_value=[]):
            resp = client.get(f"{self.API_PATH}/{session.id}/progression", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["progressions"] == []

    def test_progression_not_found(self, client, headers):
        """Non-existent session → 404."""
        resp = client.get(f"{self.API_PATH}/99999/progression", headers=headers)
        assert resp.status_code == 404

    def test_progression_unauthorized(self, client):
        """No x-user-id → 401."""
        resp = client.get(f"{self.API_PATH}/1/progression")
        assert resp.status_code == 401
