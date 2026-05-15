import json
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.db.base import Base
from app.models.workout import Workout
from app.models.training_plan import PersonalRecord
from app.api.api_v1.api import api_router
from app.core.config import settings


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Workouts API")
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
    """Override de get_db + patch SessionLocal."""
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


@pytest.fixture
def other_headers():
    return {"x-user-id": "other_user"}


# ---------- Helpers ----------

def _create_workout(
    db_session,
    user_id="test_user",
    name="Morning Workout",
    source="health_connect",
    external_id=None,
    date=None,
    duration=1800,
    calories=300,
    description="",
):
    if external_id is None:
        external_id = f"ext_{datetime.now(timezone.utc).timestamp()}_{name.replace(' ', '_')}"
    if date is None:
        date = datetime.now(timezone.utc)

    w = Workout(
        user_id=user_id,
        name=name,
        source=source,
        external_id=external_id,
        date=date,
        duration=duration,
        calories=calories,
        description=description,
    )
    db_session.add(w)
    db_session.commit()
    db_session.refresh(w)
    return w


def _create_pr(
    db_session,
    user_id="test_user",
    exercise_name="Bench Press",
    weight=80,
    reps=5,
    date="2025-06-01",
    source="manual",
):
    pr = PersonalRecord(
        user_id=user_id,
        exercise_name=exercise_name,
        weight=weight,
        reps=reps,
        date=date,
        source=source,
    )
    db_session.add(pr)
    db_session.commit()
    db_session.refresh(pr)
    return pr


# ============================================================
# TestGetWorkoutsEndpoint
# ============================================================

class TestGetWorkoutsEndpoint:
    API_PATH = "/api/v1/workouts/"

    def test_list_with_data(self, client, db_session, headers):
        """Returns all workouts ordered by date descending."""
        now = datetime.now(timezone.utc)
        _create_workout(db_session, name="First", date=now - timedelta(hours=3))
        _create_workout(db_session, name="Second", date=now - timedelta(hours=2))
        _create_workout(db_session, name="Third", date=now - timedelta(hours=1))

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3, f"Expected 3, got {len(data)}"
        assert data[0]["name"] == "Third"
        assert data[1]["name"] == "Second"
        assert data[2]["name"] == "First"

    def test_list_limit(self, client, db_session, headers):
        """Respects limit parameter."""
        now = datetime.now(timezone.utc)
        for i in range(5):
            _create_workout(db_session, name=f"W{i}", date=now - timedelta(hours=i))

        resp = client.get(f"{self.API_PATH}?limit=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "W0"

    def test_list_empty(self, client, headers):
        """No workouts -> empty list."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_other_user(self, client, db_session, headers):
        """Other user's workouts don't appear."""
        _create_workout(db_session, user_id="other_user", name="Not mine")
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_list_invalid_limit(self, client, headers):
        """limit=0 -> 422, limit=101 -> 422."""
        resp = client.get(f"{self.API_PATH}?limit=0", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?limit=101", headers=headers)
        assert resp.status_code == 422


# ============================================================
# TestUpsertWorkoutEndpoint
# ============================================================

class TestUpsertWorkoutEndpoint:
    API_PATH = "/api/v1/workouts/"

    def test_upsert_create_new(self, client, db_session, headers):
        """Creates a new workout record."""
        payload = {
            "external_id": "ext_001",
            "name": "Morning Run",
            "source": "garmin",
            "duration": 2700,
            "calories": 350,
        }
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["source"] == "garmin"
        assert data["external_id"] == "ext_001"

        workout = db_session.query(Workout).filter(
            Workout.external_id == "ext_001"
        ).first()
        assert workout is not None, "Workout not found in DB"
        assert workout.name == "Morning Run"
        assert workout.duration == 2700

    def test_upsert_update_existing(self, client, db_session, headers):
        """Same (user_id, source, external_id) -> updates, does not duplicate."""
        _create_workout(
            db_session,
            name="Original",
            source="health_connect",
            external_id="ext_002",
            calories=100,
        )

        payload = {
            "external_id": "ext_002",
            "name": "Updated Name",
            "source": "health_connect",
            "calories": 500,
        }
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200

        workouts = db_session.query(Workout).filter(
            Workout.external_id == "ext_002"
        ).all()
        assert len(workouts) == 1
        assert workouts[0].name == "Updated Name"
        assert workouts[0].calories == 500

    def test_upsert_missing_external_id(self, client, headers):
        """No external_id -> 400."""
        payload = {"name": "No ID Workout"}
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 400
        assert "Missing external_id" in resp.json()["detail"]

    def test_upsert_default_source(self, client, db_session, headers):
        """No source -> defaults to health_connect."""
        payload = {"external_id": "ext_003", "name": "Default Source"}
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["source"] == "health_connect"

        w = db_session.query(Workout).filter(Workout.external_id == "ext_003").first()
        assert w is not None
        assert w.source == "health_connect"

    def test_upsert_date_iso(self, client, db_session, headers):
        """ISO format date string is parsed correctly."""
        payload = {
            "external_id": "ext_iso",
            "name": "ISO Date",
            "date": "2025-06-15T10:30:00",
        }
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200

        workout = db_session.query(Workout).filter(
            Workout.external_id == "ext_iso"
        ).first()
        assert workout is not None
        assert workout.date.year == 2025
        assert workout.date.month == 6
        assert workout.date.day == 15

    def test_upsert_date_ymd(self, client, db_session, headers):
        """YYYY-MM-DD format date string is parsed correctly."""
        payload = {
            "external_id": "ext_ymd",
            "name": "YMD Date",
            "date": "2025-03-10",
        }
        resp = client.post(self.API_PATH, json=payload, headers=headers)
        assert resp.status_code == 200

        workout = db_session.query(Workout).filter(
            Workout.external_id == "ext_ymd"
        ).first()
        assert workout is not None
        assert workout.date.year == 2025
        assert workout.date.month == 3
        assert workout.date.day == 10

    def test_upsert_unauthorized(self, client):
        """No x-user-id -> 401."""
        payload = {"external_id": "ext_noauth", "name": "No Auth"}
        resp = client.post(self.API_PATH, json=payload)
        assert resp.status_code == 401


# ============================================================
# TestRecentWorkoutsEndpoint
# ============================================================

class TestRecentWorkoutsEndpoint:
    API_PATH = "/api/v1/workouts/recent"

    def test_recent_with_data(self, client, db_session, headers):
        """Returns recent workouts with parsed fields."""
        now = datetime.now(timezone.utc)
        _create_workout(db_session, name="Morning Run", date=now - timedelta(hours=2),
                        duration=3600, calories=400)
        _create_workout(db_session, name="Evening Walk", date=now - timedelta(hours=1),
                        duration=1800, calories=150)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Evening Walk"  # most recent first
        assert data[0]["duration_min"] == 30
        assert data[1]["duration_min"] == 60

    def test_recent_filter_strength(self, client, db_session, headers):
        """Filters by strength (contains 'fuerza' or 'strength')."""
        _create_workout(db_session, name="Cardio Run")
        _create_workout(db_session, name="Fuerza Total")

        resp = client.get(f"{self.API_PATH}?activity_type=strength", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Fuerza Total"

    def test_recent_filter_cardio(self, client, db_session, headers):
        """Filters by cardio (carrera, running, trail, caminar, walk)."""
        _create_workout(db_session, name="Full Body Strength")
        _create_workout(db_session, name="Morning Running")

        resp = client.get(f"{self.API_PATH}?activity_type=cardio", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "Running" in data[0]["name"]

    def test_recent_filter_all(self, client, db_session, headers):
        """activity_type=all returns everything (no filter applied)."""
        _create_workout(db_session, name="Run")
        _create_workout(db_session, name="Strength")

        resp = client.get(f"{self.API_PATH}?activity_type=all", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_recent_empty(self, client, headers):
        """No workouts -> empty list."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_recent_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_recent_workout_type_detection(self, client, db_session, headers):
        """Cardio keywords set type='cardio', others set type='strength'."""
        _create_workout(db_session, name="Trail Running")
        _create_workout(db_session, name="Bench Press")

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        types = {w["name"]: w["type"] for w in data}
        assert types["Trail Running"] == "cardio"
        assert types["Bench Press"] == "strength"

    def test_recent_parsed_description(self, client, db_session, headers):
        """JSON description is parsed into extra fields (avgHR, rpe, sport)."""
        desc = json.dumps({"avgHR": 145, "rpe": 7, "sport": "running"})
        _create_workout(db_session, name="HR Test", description=desc)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["avgHR"] == 145
        assert data[0]["rpe"] == 7
        assert data[0]["sport"] == "running"


# ============================================================
# TestPersonalRecordsEndpoint
# ============================================================

class TestPersonalRecordsEndpoint:
    API_PATH = "/api/v1/workouts/personal-records"

    def test_prs_with_data(self, client, db_session, headers):
        """Returns existing PRs with formatted response."""
        _create_pr(db_session, exercise_name="Bench Press", weight=80, reps=5)
        _create_pr(db_session, exercise_name="Squat", weight=100, reps=5)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        exercises = {r["exercise"]: r for r in data}
        assert exercises["Bench Press"]["pr"] == 80
        assert exercises["Bench Press"]["reps"] == 5
        assert exercises["Bench Press"]["unit"] == "kg"
        assert exercises["Bench Press"]["muscle"] == "Chest"
        assert exercises["Squat"]["muscle"] == "Legs"

    def test_prs_empty_seeds_defaults(self, client, db_session, headers):
        """No PRs -> auto-seeds default records."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6
        exercises = {r["exercise"] for r in data}
        assert "Bench Press" in exercises
        assert "Squat" in exercises
        assert "Deadlift" in exercises

    def test_prs_filter_exercise(self, client, db_session, headers):
        """Filters by exercise name (case-insensitive partial match)."""
        _create_pr(db_session, exercise_name="Bench Press", weight=80)
        _create_pr(db_session, exercise_name="Squat", weight=100)
        _create_pr(db_session, exercise_name="Incline Bench Press", weight=60)

        resp = client.get(f"{self.API_PATH}?exercise=bench", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("Bench" in r["exercise"] for r in data)

    def test_prs_filter_no_match_seeds_defaults(self, client, db_session, headers):
        """Filter with no matches triggers auto-seed of default PRs."""
        resp = client.get(f"{self.API_PATH}?exercise=zzzzzzz", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Endpoint can't distinguish "no records for user" from "filter didn't match"; seeds defaults
        assert len(data) >= 6

    def test_prs_muscle_mapping(self, client, db_session, headers):
        """Each exercise maps to correct muscle group."""
        exercises_muscles = [
            ("Bench Press", "Chest"),
            ("Overhead Press", "Shoulders"),
            ("Squat", "Legs"),
            ("Deadlift", "Back"),
            ("Barbell Row", "Back"),
            ("Bicep Curl", "Arms"),
            ("Dips", "Chest"),
            ("Pull-ups", "Back"),
            ("Lunges", "Legs"),
            ("Leg Extension", "Legs"),
            ("Unknown Exercise", "Full Body"),
        ]
        for exercise, _ in exercises_muscles:
            _create_pr(db_session, exercise_name=exercise)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        mapping = {r["exercise"]: r["muscle"] for r in data}
        for exercise, expected_muscle in exercises_muscles:
            assert mapping[exercise] == expected_muscle, (
                f"Expected '{exercise}' -> '{expected_muscle}', got '{mapping[exercise]}'"
            )

    def test_prs_other_user_seeds(self, client, db_session, headers):
        """Other user's existing PRs don't interfere -- empty user gets seeded defaults."""
        _create_pr(db_session, user_id="other_user", exercise_name="Deadlift", weight=200)
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6

    def test_prs_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_prs_date_and_source_fields(self, client, db_session, headers):
        """Response includes date and source fields."""
        _create_pr(db_session, exercise_name="Bench Press", weight=80, date="2025-06-01", source="manual")

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        r = data[0]
        assert r["date"] == "2025-06-01"
        assert r["source"] == "manual"
