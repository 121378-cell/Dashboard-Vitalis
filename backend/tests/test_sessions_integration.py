"""
Tests de integración: endpoints de sessions.py.
================================================

Cubre los 9 endpoints del router sessions:
- POST  /generate
- GET   /today
- GET   /{session_id}
- POST  /{session_id}/save
- POST  /{session_id}/analyze
- GET   /history
- POST  /weekly-report/generate
- GET   /weekly-report/latest
- GET   /should-train/today

Usa FastAPI TestClient con dependencias override + StaticPool.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.session import TrainingSession, WeeklyReport
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.session_service import SessionService

# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Sessions API")
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


def _create_session(
    db_session,
    user_id="test_user",
    date_str=None,
    status="planned",
    plan_json=None,
    actual_json=None,
    session_report=None,
):
    """Crea un TrainingSession de prueba."""
    if date_str is None:
        date_str = date.today().isoformat()
    if plan_json is None:
        plan_json = json.dumps({
            "type": "strength",
            "exercises": [
                {"name": "Bench Press", "sets": 3, "reps": 10, "weight_kg": 60}
            ]
        })
    session = TrainingSession(
        user_id=user_id,
        date=date_str,
        status=status,
        generated_by="atlas",
        plan_json=plan_json,
        actual_json=actual_json,
        session_report=session_report,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def _create_weekly_report(
    db_session,
    user_id="test_user",
    week_start=None,
    week_end=None,
    report_text="Test report",
    metrics=None,
    next_week_plan=None
):
    """Crea un WeeklyReport de prueba."""
    if week_start is None:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
    if week_end is None:
        today = date.today()
        week_end = (today + timedelta(days=6 - today.weekday())).isoformat()
    if metrics is None:
        metrics = {"volume": 5000, "sessions": 3}
    if next_week_plan is None:
        next_week_plan = {"focus": "strength", "sessions": 4}

    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        report_text=report_text,
        metrics_json=json.dumps(metrics),
        next_week_plan=json.dumps(next_week_plan),
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


# ===========================================================================
# POST /sessions/generate
# ===========================================================================


class TestGenerateSessionEndpoint:
    """POST /sessions/generate"""

    API_PATH = "/api/v1/sessions/generate"

    SAMPLE_SHOULD_TRAIN = {"train": True, "reason": "Día de entrenamiento", "suggested_type": "strength", "readiness": 85}

    def test_generate_new(self, client, db_session, headers):
        """Sin sesión existente → genera nueva sesión."""
        with (
            patch.object(SessionService, "should_train_today", return_value=self.SAMPLE_SHOULD_TRAIN),
            patch.object(SessionService, "generate_session_plan", return_value={
                "type": "strength",
                "exercises": [{"name": "Bench Press", "sets": 3, "reps": 10}],
            }),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"]
        assert data["status"] == "planned"
        assert data["plan"]["type"] == "strength"
        assert data["should_train"]["train"] is True

    def test_generate_existing(self, client, db_session, headers):
        """Sesión ya existe para hoy → la devuelve."""
        session = _create_session(db_session, date_str=date.today().isoformat())

        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == str(session.id)
        assert data["message"] == "Sesión existente recuperada"

    def test_generate_with_force_type(self, client, db_session, headers):
        """force_type=cardio → se pasa al servicio."""
        with (
            patch.object(SessionService, "should_train_today", return_value=self.SAMPLE_SHOULD_TRAIN),
            patch.object(SessionService, "generate_session_plan", return_value={
                "type": "cardio",
                "exercises": [{"name": "Running", "duration_min": 30}],
            }) as mock_generate,
        ):
            resp = client.post(self.API_PATH, params={"force_type": "cardio"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"]["type"] == "cardio"
        # Verificar que force_type se pasó al servicio
        assert mock_generate.call_args[1].get("force_type") == "cardio"

    def test_generate_invalid_date(self, client, headers):
        """target_date con formato inválido → 400."""
        resp = client.post(self.API_PATH, params={"target_date": "not-a-date"}, headers=headers)
        assert resp.status_code == 400
        assert "fecha" in resp.json()["detail"].lower()

    def test_generate_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /sessions/today
# ===========================================================================


class TestGetTodaySessionEndpoint:
    """GET /sessions/today"""

    API_PATH = "/api/v1/sessions/today"

    def test_today_exists(self, client, db_session, headers):
        """Sesión existe para hoy → 200 + datos."""
        session = _create_session(db_session, date_str=date.today().isoformat())

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(session.id)
        assert data["date"] == date.today().isoformat()
        assert data["plan"]["type"] == "strength"

    def test_today_none(self, client, headers):
        """Sin sesión para hoy → 200 + null."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_today_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /sessions/{session_id}
# ===========================================================================


class TestGetSessionDetailEndpoint:
    """GET /sessions/{session_id}"""

    API_PATH = "/api/v1/sessions"

    def test_detail_found(self, client, db_session, headers):
        """Sesión existe → 200 + detalle completo."""
        session = _create_session(db_session)

        resp = client.get(f"{self.API_PATH}/{session.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(session.id)
        assert data["status"] == "planned"

    def test_detail_not_found(self, client, headers):
        """Sesión no existe → 404."""
        resp = client.get(f"{self.API_PATH}/nonexistent-id", headers=headers)
        assert resp.status_code == 404
        assert "no encontrada" in resp.json()["detail"].lower()

    def test_detail_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(f"{self.API_PATH}/some-id")
        assert resp.status_code == 401


# ===========================================================================
# POST /sessions/{session_id}/save
# ===========================================================================


class TestSaveSessionEndpoint:
    """POST /sessions/{session_id}/save"""

    API_PATH = "/api/v1/sessions"

    SAVE_PAYLOAD = {
        "actual_data": [
            {
                "name": "Bench Press",
                "muscle_group": "chest",
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 10,
                        "weight_kg": 60,
                        "rpe_target": 7,
                        "rpe_real": 8,
                        "rest_seconds": 90,
                        "tempo": "2010",
                        "status": "completed",
                        "notes": "",
                    }
                ],
            }
        ]
    }

    def test_save_success(self, client, db_session, headers):
        """Sesión planned → guardar datos → completed + 200."""
        session = _create_session(db_session, status="planned")

        with patch.object(SessionService, "analyze_session", return_value="Report OK"):
            resp = client.post(
                f"{self.API_PATH}/{session.id}/save",
                json=self.SAVE_PAYLOAD,
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["actual"] is not None
        assert data["actual"]["exercises"][0]["name"] == "Bench Press"

    def test_save_not_found(self, client, headers):
        """session_id inválido → 404."""
        resp = client.post(
            f"{self.API_PATH}/nonexistent-id/save",
            json=self.SAVE_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 404

    def test_save_already_completed(self, client, db_session, headers):
        """Sesión ya completada → 400."""
        session = _create_session(
            db_session,
            status="completed",
            actual_json=json.dumps({"exercises": []}),
        )

        resp = client.post(
            f"{self.API_PATH}/{session.id}/save",
            json=self.SAVE_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 400
        assert "completada" in resp.json()["detail"].lower()

    def test_save_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(f"{self.API_PATH}/some-id/save", json=self.SAVE_PAYLOAD)
        assert resp.status_code == 401


# ===========================================================================
# POST /sessions/{session_id}/analyze
# ===========================================================================


class TestAnalyzeSessionEndpoint:
    """POST /sessions/{session_id}/analyze"""

    API_PATH = "/api/v1/sessions"

    def test_analyze_success(self, client, db_session, headers):
        """Sesión con actual_json → analizar → report OK."""
        session = _create_session(
            db_session,
            status="completed",
            actual_json=json.dumps({
                "exercises": [{"name": "Bench Press", "sets": [{"reps": 10}]}]
            }),
        )

        with patch.object(SessionService, "analyze_session", return_value="Great session!"):
            resp = client.post(f"{self.API_PATH}/{session.id}/analyze", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["report"] == "Great session!"

    def test_analyze_not_found(self, client, headers):
        """session_id inválido → 404."""
        resp = client.post(f"{self.API_PATH}/nonexistent-id/analyze", headers=headers)
        assert resp.status_code == 404

    def test_analyze_no_actual_data(self, client, db_session, headers):
        """Sesión sin actual_json → 400."""
        session = _create_session(db_session, status="planned", actual_json=None)

        resp = client.post(f"{self.API_PATH}/{session.id}/analyze", headers=headers)
        assert resp.status_code == 400
        assert "datos reales" in resp.json()["detail"].lower()

    def test_analyze_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(f"{self.API_PATH}/some-id/analyze")
        assert resp.status_code == 401


# ===========================================================================
# GET /sessions/history
# ===========================================================================


class TestGetSessionHistoryEndpoint:
    """GET /sessions/history"""

    API_PATH = "/api/v1/sessions/history"

    def test_history_with_data(self, client, db_session, headers):
        """Varias sesiones → lista ordenada descendente."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        s1 = _create_session(db_session, date_str=today)
        s2 = _create_session(db_session, date_str=yesterday)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Orden descendente: today primero
        assert data[0]["id"] == str(s1.id)

    def test_history_with_days_param(self, client, db_session, headers):
        """days=7 → solo sesiones de los últimos 7 días."""
        old_date = (date.today() - timedelta(days=60)).isoformat()
        _create_session(db_session, date_str=old_date)

        resp = client.get(self.API_PATH, params={"days": 7}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # La sesión de hace 60 días no debería aparecer
        assert len(data) == 0

    def test_history_empty(self, client, headers):
        """Sin sesiones → lista vacía."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /sessions/weekly-report/generate
# ===========================================================================


class TestGenerateWeeklyReportEndpoint:
    """POST /sessions/weekly-report/generate"""

    API_PATH = "/api/v1/sessions/weekly-report/generate"

    SAMPLE_REPORT = {
        "week_start": (date.today() - timedelta(days=date.today().weekday())).isoformat(),
        "week_end": (date.today() + timedelta(days=6 - date.today().weekday())).isoformat(),
        "report_text": "Buena semana de entrenamiento",
        "metrics": {"volume": 5000, "sessions": 3, "streak": 5},
        "next_week_plan": {"focus": "strength", "sessions": 4, "notes": "Aumentar carga"},
    }

    def test_generate_success(self, client, headers):
        """Generar reporte semanal → 200 + datos."""
        with patch.object(
            SessionService, "generate_weekly_report", return_value=self.SAMPLE_REPORT
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_text"] == "Buena semana de entrenamiento"
        assert data["metrics"]["volume"] == 5000
        assert data["next_week_plan"]["focus"] == "strength"

    def test_generate_error(self, client, headers):
        """SessionService lanza excepción → 500."""
        with patch.object(
            SessionService, "generate_weekly_report", side_effect=Exception("Service error")
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500

    def test_generate_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /sessions/weekly-report/latest
# ===========================================================================


class TestGetLatestWeeklyReportEndpoint:
    """GET /sessions/weekly-report/latest"""

    API_PATH = "/api/v1/sessions/weekly-report/latest"

    def test_latest_exists(self, client, db_session, headers):
        """Reporte existe → 200 + datos."""
        report = _create_weekly_report(db_session)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(report.id)
        assert data["report_text"] == "Test report"

    def test_latest_none(self, client, headers):
        """Sin reportes → 200 + null."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_latest_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /sessions/should-train/today
# ===========================================================================


class TestShouldTrainTodayEndpoint:
    """GET /sessions/should-train/today"""

    API_PATH = "/api/v1/sessions/should-train/today"

    def test_should_train_true(self, client, headers):
        """Readiness OK → train=True."""
        with patch.object(
            SessionService,
            "should_train_today",
            return_value={"train": True, "reason": "Día de entrenamiento", "suggested_type": "strength", "readiness": 85},
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["train"] is True
        assert data["readiness"] == 85

    def test_should_train_false(self, client, headers):
        """Fatiga alta → train=False."""
        with patch.object(
            SessionService,
            "should_train_today",
            return_value={"train": False, "reason": "Fatiga acumulada", "suggested_type": "recovery", "readiness": 45},
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["train"] is False
        assert data["readiness"] == 45

    def test_should_train_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
