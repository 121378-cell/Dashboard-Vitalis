"""
Tests de integración para endpoints de planner.py
==================================================
Cubre los 8 endpoints del router planner (prefix: /planner en /api/v1):
- POST /planner/generate-week         → Genera plan semanal
- GET  /planner/current-week          → Plan activo de la semana
- POST /planner/complete-session      → Marcar sesión completada
- POST /planner/skip-session          → Omitir sesión
- POST /planner/reschedule-session    → Reprogramar sesión
- GET  /planner/personal-records      → Todos los PRs del atleta
- POST /planner/update-pr             → Actualizar PR manualmente
- GET  /planner/weekly-stats          → Estadísticas semanales
"""

import os
import sys
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.base import Base
from app.models.training_plan import WeeklyPlan, PlanSession, PersonalRecord
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.planner_service import TrainingPlannerService
from app.services.readiness_service import ReadinessService
from app.services.memory_service import MemoryService

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Test App ──────────────────────────────────────────────────────────────
test_app = FastAPI(title="Test ATLAS Planner API")
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

SAMPLE_WEEKLY_PLAN = {
    "plan": {
        "week": 1,
        "objective": "hypertrophy",
        "sessions": [
            {"day": "Monday", "focus": "Push", "exercises": []},
            {"day": "Wednesday", "focus": "Pull", "exercises": []},
            {"day": "Friday", "focus": "Legs", "exercises": []},
        ],
    }
}

SAMPLE_FORECAST = [
    {"date": (date.today() + timedelta(days=i)).isoformat(), "score": 75 + i * 3}
    for i in range(7)
]


# ── Helpers ────────────────────────────────────────────────────────────────


def _create_weekly_plan(db_session, user_id="test_user", status="active", days_offset=0):
    """Seed a WeeklyPlan record and return it."""
    today = date.today() + timedelta(days=days_offset)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    plan = WeeklyPlan(
        user_id=user_id,
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        plan_data=SAMPLE_WEEKLY_PLAN,
        status=status,
        objective="hypertrophy",
    )
    db_session.add(plan)
    db_session.flush()
    return plan


def _create_plan_session(
    db_session,
    plan_id,
    day_index=0,
    day_name="Push",
    scheduled_date=None,
    completed=False,
    skipped=False,
    exercises_data=None,
    actual_data=None,
):
    """Seed a PlanSession record and return it."""
    if scheduled_date is None:
        scheduled_date = (date.today() - timedelta(days=date.today().weekday()) + timedelta(days=day_index)).isoformat()
    if exercises_data is None:
        exercises_data = [
            {"name": "Bench Press", "sets": 4, "reps": 8, "weight": 80},
            {"name": "Overhead Press", "sets": 3, "reps": 10, "weight": 50},
        ]

    session = PlanSession(
        plan_id=plan_id,
        day_index=day_index,
        day_name=day_name,
        scheduled_date=scheduled_date,
        exercises_data=exercises_data,
        completed=completed,
        actual_data=actual_data,
        skipped=skipped,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _create_personal_record(
    db_session,
    user_id="test_user",
    exercise_name="bench press",
    weight=80,
    reps=8,
    rpe=8,
    source="workout",
    date_str=None,
):
    """Seed a PersonalRecord and return it."""
    if date_str is None:
        date_str = date.today().isoformat()
    pr = PersonalRecord(
        user_id=user_id,
        exercise_name=exercise_name,
        weight=weight,
        reps=reps,
        rpe=rpe,
        date=date_str,
        source=source,
    )
    db_session.add(pr)
    db_session.flush()
    return pr


# ══════════════════════════════════════════════════════════════════════════
# POST /planner/generate-week
# ══════════════════════════════════════════════════════════════════════════


class TestGenerateWeekEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/generate-week"

    def test_success(self, client, headers):
        with patch.object(
            TrainingPlannerService, "generate_weekly_plan", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = SAMPLE_WEEKLY_PLAN
            resp = client.post(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"] == SAMPLE_WEEKLY_PLAN
        assert "generated" in data["message"].lower()
        mock_gen.assert_called_once()

    def test_error(self, client, headers):
        with patch.object(
            TrainingPlannerService, "generate_weekly_plan", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.side_effect = Exception("AI service unavailable")
            resp = client.post(self.API_PATH, headers=headers)

        assert resp.status_code == 500
        assert "AI service unavailable" in resp.json()["detail"]

    def test_unauthorized(self, client):
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# GET /planner/current-week
# ══════════════════════════════════════════════════════════════════════════


class TestCurrentWeekEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/current-week"

    def test_active_plan(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session, status="active")
        _create_plan_session(db_session, plan_id=plan.id, day_index=0, day_name="Push")
        db_session.commit()

        with patch.object(ReadinessService, "get_forecast", return_value=SAMPLE_FORECAST):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == plan.id
        assert data["data"]["status"] == "active"
        assert len(data["data"]["sessions"]) == 1
        assert data["data"]["sessions"][0]["day_name"] == "Push"

    def test_archived_fallback(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session, status="archived", days_offset=-7)
        db_session.commit()

        with patch.object(ReadinessService, "get_forecast", return_value=SAMPLE_FORECAST):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["id"] == plan.id
        assert data["data"]["status"] == "archived"

    def test_no_plan(self, client, headers):
        with patch.object(ReadinessService, "get_forecast", return_value=[]):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 404
        assert "Generate one first" in resp.json()["detail"]

    def test_no_sessions(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session, status="active")
        db_session.commit()

        with patch.object(ReadinessService, "get_forecast", return_value=SAMPLE_FORECAST):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["sessions"]) == 0

    def test_unauthorized(self, client):
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# POST /planner/complete-session
# ══════════════════════════════════════════════════════════════════════════


class TestCompleteSessionEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/complete-session"

    def test_success_no_pr(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id)
        db_session.commit()

        actual_data = {"exercises": []}
        resp = client.post(
            self.API_PATH,
            json={"session_id": session.id, "actual_data": actual_data},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["completed"] is True
        assert data["data"]["new_personal_records"] == []

    def test_success_with_new_pr(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id)
        db_session.commit()

        with patch.object(MemoryService, "add_memory", return_value=None):
            actual_data = {
                "exercises": [
                    {"name": "Bench Press", "weight": 100, "reps": 10, "rpe": 9}
                ]
            }
            resp = client.post(
                self.API_PATH,
                json={"session_id": session.id, "actual_data": actual_data},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["new_personal_records"]) == 1
        assert data["data"]["new_personal_records"][0]["type"] == "first_pr"
        assert data["data"]["new_personal_records"][0]["exercise"] == "bench press"

        # Verify PR was persisted
        pr_in_db = db_session.query(PersonalRecord).filter(
            PersonalRecord.exercise_name == "bench press"
        ).first()
        assert pr_in_db is not None
        assert pr_in_db.weight == 100
        assert pr_in_db.reps == 10

    def test_success_with_update_pr(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id)
        _create_personal_record(db_session, exercise_name="bench press", weight=80, reps=8)
        db_session.commit()

        with patch.object(MemoryService, "add_memory", return_value=None):
            actual_data = {
                "exercises": [
                    {"name": "Bench Press", "weight": 100, "reps": 10, "rpe": 9}
                ]
            }
            resp = client.post(
                self.API_PATH,
                json={"session_id": session.id, "actual_data": actual_data},
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["new_personal_records"]) == 1
        assert data["data"]["new_personal_records"][0]["type"] == "weight_increase"

    def test_not_found(self, client, headers):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 9999, "actual_data": {"exercises": []}},
            headers=headers,
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_zero_weight_no_pr(self, client, headers, db_session):
        """Exercise with weight=0 should not create a PR."""
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id)
        db_session.commit()

        actual_data = {
            "exercises": [
                {"name": "Bench Press", "weight": 0, "reps": 0, "rpe": 0}
            ]
        }
        resp = client.post(
            self.API_PATH,
            json={"session_id": session.id, "actual_data": actual_data},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["new_personal_records"] == []

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 1, "actual_data": {"exercises": []}},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# POST /planner/skip-session
# ══════════════════════════════════════════════════════════════════════════


class TestSkipSessionEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/skip-session"

    def test_success_with_reschedule(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id, day_index=0)
        db_session.commit()

        resp = client.post(
            self.API_PATH,
            json={"session_id": session.id, "reason": "Feeling tired"},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["skipped"] is True
        assert "rescheduled" in data["message"].lower()

        # Verify the session was marked as skipped
        db_session.refresh(session)
        assert session.skipped is True
        assert session.notes == "Feeling tired"

        # Verify a rescheduled session was created
        rescheduled = (
            db_session.query(PlanSession)
            .filter(PlanSession.id != session.id)
            .first()
        )
        assert rescheduled is not None
        assert "reprogramada" in (rescheduled.day_name or "").lower()

    def test_success_without_reason(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(db_session, plan_id=plan.id, day_index=0)
        db_session.commit()

        resp = client.post(
            self.API_PATH,
            json={"session_id": session.id},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Skipped by user request" in data["data"]["notes"]

    def test_not_found(self, client, headers):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 9999},
            headers=headers,
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 1},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# POST /planner/reschedule-session
# ══════════════════════════════════════════════════════════════════════════


class TestRescheduleSessionEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/reschedule-session"

    def test_success(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session)
        session = _create_plan_session(
            db_session, plan_id=plan.id, day_index=0,
            scheduled_date="2025-01-06",
        )
        db_session.commit()
        old_date = session.scheduled_date

        new_date = "2025-01-08"
        resp = client.post(
            self.API_PATH,
            json={"session_id": session.id, "new_date": new_date},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["old_date"] == old_date
        assert data["data"]["new_date"] == new_date

        # Verify DB was updated
        db_session.refresh(session)
        assert session.scheduled_date == new_date

    def test_not_found(self, client, headers):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 9999, "new_date": "2025-01-08"},
            headers=headers,
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={"session_id": 1, "new_date": "2025-01-08"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# GET /planner/personal-records
# ══════════════════════════════════════════════════════════════════════════


class TestPersonalRecordsEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/personal-records"

    def test_with_records(self, client, headers, db_session):
        _create_personal_record(db_session, exercise_name="bench press", weight=100, reps=10)
        _create_personal_record(db_session, exercise_name="deadlift", weight=200, reps=5)
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["total_exercises"] == 2
        assert "bench press" in data["data"]["personal_records"]
        assert "deadlift" in data["data"]["personal_records"]
        assert data["data"]["personal_records"]["bench press"]["weight"] == 100

    def test_empty(self, client, headers):
        resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["total_exercises"] == 0
        assert data["data"]["personal_records"] == {}
        assert data["data"]["all_records"] == {}

    def test_unauthorized(self, client):
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# POST /planner/update-pr
# ══════════════════════════════════════════════════════════════════════════


class TestUpdatePREndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/update-pr"

    def test_create_new(self, client, headers, db_session):
        resp = client.post(
            self.API_PATH,
            json={
                "exercise_name": "Squat",
                "weight": 150,
                "reps": 5,
                "rpe": 9,
                "notes": "New PR!",
            },
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["exercise_name"] == "Squat"
        assert data["data"]["weight"] == 150
        assert data["data"]["source"] == "manual"

        # Verify persisted (exact case as sent)
        pr_in_db = db_session.query(PersonalRecord).filter(
            PersonalRecord.exercise_name == "Squat"
        ).first()
        assert pr_in_db is not None
        assert pr_in_db.weight == 150

    def test_update_existing(self, client, headers, db_session):
        _create_personal_record(db_session, exercise_name="bench press", weight=80, reps=8)
        db_session.commit()

        resp = client.post(
            self.API_PATH,
            json={
                "exercise_name": "Bench Press",
                "weight": 100,
                "reps": 10,
                "rpe": 9,
            },
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["weight"] == 100
        assert data["data"]["reps"] == 10
        assert data["data"]["source"] == "manual"

        # Verify DB updated (not duplicate)
        prs = db_session.query(PersonalRecord).filter(
            PersonalRecord.exercise_name == "bench press"
        ).all()
        assert len(prs) == 1
        assert prs[0].weight == 100

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={"exercise_name": "Squat", "weight": 150, "reps": 5},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# GET /planner/weekly-stats
# ══════════════════════════════════════════════════════════════════════════


class TestWeeklyStatsEndpoint:
    API_PATH = f"{settings.API_V1_STR}/planner/weekly-stats"

    def test_with_sessions(self, client, headers, db_session):
        plan = _create_weekly_plan(db_session, status="active")
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        _create_plan_session(
            db_session, plan_id=plan.id, day_index=0,
            scheduled_date=week_start.isoformat(),
            completed=True,
            actual_data={"exercises": [{"name": "Bench", "sets": 4}, {"name": "OHP", "sets": 3}]},
        )
        _create_plan_session(
            db_session, plan_id=plan.id, day_index=1,
            scheduled_date=(week_start + timedelta(days=1)).isoformat(),
            skipped=True,
        )
        _create_plan_session(
            db_session, plan_id=plan.id, day_index=2,
            scheduled_date=(week_start + timedelta(days=2)).isoformat(),
            completed=False,
        )
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        stats = data["data"]
        assert stats["total_sessions"] == 3
        assert stats["completed_sessions"] == 1
        assert stats["skipped_sessions"] == 1
        assert stats["completion_rate"] == round(1 / 3 * 100, 1)
        assert stats["total_exercises"] == 2  # Only completed sessions have actual_data
        assert stats["total_duration_minutes"] == 4 * 3 + 3 * 3  # sets * 3 per exercise

    def test_empty(self, client, headers):
        resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["total_sessions"] == 0
        assert stats["completed_sessions"] == 0
        assert stats["skipped_sessions"] == 0
        assert stats["completion_rate"] == 0
        assert stats["total_duration_minutes"] == 0
        assert stats["total_exercises"] == 0

    def test_unauthorized(self, client):
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
