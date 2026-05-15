"""Integration tests for Dashboard endpoints."""
import json
import os
import sys
from datetime import date, datetime, timedelta
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
from app.models.biometrics import Biometrics
from app.api.api_v1.api import api_router
from app.core.config import settings

test_app = FastAPI(title="Test ATLAS Dashboard API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


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
    return TestClient(test_app)


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine):
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


class TestGetKPIsEndpoint:
    """GET /api/v1/dashboard/kpis"""

    API_PATH = f"{settings.API_V1_STR}/dashboard/kpis"

    def test_kpis_with_workouts_and_biometrics(self, client, headers, db_session):
        """Seed 3 workouts + 2 biometrics → verify all KPIs calculated."""
        today = date.today()
        for i in range(3):
            d = today - timedelta(days=i * 5)
            db_session.add(Workout(
                user_id="test_user", name="Fuerza",
                date=datetime.combine(d, datetime.min.time()),
                duration=3600, calories=300,
            ))
        for i in range(2):
            d = today - timedelta(days=i * 10)
            db_session.add(Biometrics(
                user_id="test_user", date=d.isoformat(),
                data=json.dumps({
                    "lastSevenDaysAvgRHR": 55, "sleep": 7.5,
                    "stress": 25, "steps": 8000,
                }),
                body_battery=75.0, training_readiness=80,
            ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["activities_30d"] == 3
        assert data["calories_30d"] == 900
        assert data["training_minutes_30d"] == 180
        assert data["avg_rhr"] == 55.0
        assert data["avg_sleep"] == 7.5
        assert data["avg_stress"] == 25.0
        assert data["avg_bb"] == 75.0
        assert data["avg_steps"] == 8000
        assert data["avg_readiness"] == 80
        assert data["strength_30d"] == 3
        assert data["cardio_30d"] == 0
        assert data["biometrics_days_30d"] == 2
        assert data["weekly_sessions_avg"] > 0
        assert data["total_workouts"] >= 3

    def test_kpis_no_data(self, client, headers):
        """No data → zeros and Nones."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["activities_30d"] == 0
        assert data["calories_30d"] == 0
        assert data["training_minutes_30d"] == 0
        assert data["weekly_sessions_avg"] == 0
        assert data["avg_rhr"] is None
        assert data["avg_sleep"] is None
        assert data["avg_stress"] is None
        assert data["avg_bb"] is None
        assert data["avg_steps"] is None
        assert data["avg_readiness"] is None
        assert data["activity_change_pct"] is None
        assert data["total_workouts"] == 0
        assert data["strength_30d"] == 0
        assert data["cardio_30d"] == 0
        assert data["biometrics_days_30d"] == 0

    def test_kpis_strength_cardio_keywords(self, client, headers, db_session):
        """Verify keyword matching: 'Fuerza' → 1 strength, 'Carrera'+'Trail' → 2 cardio."""
        today = date.today()
        for name in ["Fuerza pesada", "Carrera suave", "Trail montaña"]:
            db_session.add(Workout(
                user_id="test_user", name=name,
                date=datetime.combine(today - timedelta(days=1), datetime.min.time()),
                duration=1800, calories=200,
            ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["strength_30d"] == 1
        assert data["cardio_30d"] == 2

    def test_kpis_activity_change(self, client, headers, db_session):
        """5 prev + 2 current → -60% change."""
        today = date.today()
        for i in range(5):
            d = today - timedelta(days=40 + i)
            db_session.add(Workout(
                user_id="test_user", name="Fuerza",
                date=datetime.combine(d, datetime.min.time()),
                duration=1800, calories=150,
            ))
        for i in range(2):
            d = today - timedelta(days=i * 5)
            db_session.add(Workout(
                user_id="test_user", name="Fuerza",
                date=datetime.combine(d, datetime.min.time()),
                duration=1800, calories=150,
            ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["activities_30d"] == 2
        assert data["activity_change_pct"] == -60

    def test_kpis_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


class TestActivityHeatmapEndpoint:
    """GET /api/v1/dashboard/activity-heatmap"""

    API_PATH = f"{settings.API_V1_STR}/dashboard/activity-heatmap"

    def test_heatmap_with_data(self, client, headers, db_session):
        """3 workouts across weeks → verify total aggregation."""
        today = date.today()
        for offset, name in [(14, "Fuerza"), (7, "Carrera"), (0, "Yoga")]:
            db_session.add(Workout(
                user_id="test_user", name=name,
                date=datetime.combine(today - timedelta(days=offset), datetime.min.time()),
                duration=3600, calories=300,
            ))
        db_session.commit()

        resp = client.get(f"{self.API_PATH}?weeks=4", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        assert sum(d["value"] for d in data) == 3
        assert sum(d["calories"] for d in data) == 900

    def test_heatmap_empty(self, client, headers):
        """No data → weeks entries with zeros."""
        resp = client.get(f"{self.API_PATH}?weeks=3", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        for d in data:
            assert d["value"] == 0
            assert d["minutes"] == 0
            assert d["calories"] == 0

    def test_heatmap_custom_weeks(self, client, headers):
        """weeks=10 → 10 entries."""
        resp = client.get(f"{self.API_PATH}?weeks=10", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_heatmap_invalid_weeks_zero(self, client, headers):
        """weeks=0 → 422 (ge=1)."""
        resp = client.get(f"{self.API_PATH}?weeks=0", headers=headers)
        assert resp.status_code == 422

    def test_heatmap_invalid_weeks_over(self, client, headers):
        """weeks=200 → 422 (le=104)."""
        resp = client.get(f"{self.API_PATH}?weeks=200", headers=headers)
        assert resp.status_code == 422

    def test_heatmap_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


class TestTrainingDistributionEndpoint:
    """GET /api/v1/dashboard/training-distribution"""

    API_PATH = f"{settings.API_V1_STR}/dashboard/training-distribution"

    def test_distribution_mixed(self, client, headers, db_session):
        """Mixed types → correct distribution categories."""
        today = date.today()
        names = ["Fuerza pesada", "Press militar", "Carrera 5k", "HIIT intenso", "Yoga matutino"]
        for name in names:
            db_session.add(Workout(
                user_id="test_user", name=name,
                date=datetime.combine(today - timedelta(days=1), datetime.min.time()),
                duration=1800, calories=100,
            ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        types = {d["type"]: d["value"] for d in data}
        assert types.get("Strength") == 2
        assert types.get("Cardio") == 1
        assert types.get("HIIT") == 1
        assert types.get("Mobility") == 1

    def test_distribution_default_strength(self, client, headers, db_session):
        """Unmatched keyword → defaults to Strength."""
        db_session.add(Workout(
            user_id="test_user", name="Entrenamiento general",
            date=datetime.combine(date.today() - timedelta(days=1), datetime.min.time()),
            duration=1800, calories=100,
        ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(d["type"] == "Strength" and d["value"] == 1 for d in data)

    def test_distribution_empty(self, client, headers):
        """No data → empty list."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_distribution_custom_days(self, client, headers, db_session):
        """days=30 still returns data."""
        db_session.add(Workout(
            user_id="test_user", name="Fuerza",
            date=datetime.combine(date.today() - timedelta(days=1), datetime.min.time()),
            duration=1800, calories=100,
        ))
        db_session.commit()

        resp = client.get(f"{self.API_PATH}?days=30", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_distribution_invalid_days(self, client, headers):
        """days=6 → 422 (ge=7), days=366 → 422 (le=365)."""
        resp = client.get(f"{self.API_PATH}?days=6", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days=366", headers=headers)
        assert resp.status_code == 422

    def test_distribution_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


class TestReadinessTrendEndpoint:
    """GET /api/v1/dashboard/readiness-trend-line"""

    API_PATH = f"{settings.API_V1_STR}/dashboard/readiness-trend-line"

    def test_trend_with_data(self, client, headers, db_session):
        """2 biometrics + workouts → verify readiness score + volume."""
        today = date.today()
        for offset in [2, 1]:
            d = today - timedelta(days=offset)
            db_session.add(Biometrics(
                user_id="test_user", date=d.isoformat(),
                data=json.dumps({
                    "lastSevenDaysAvgRHR": 55, "sleep": 8.0,
                    "stress": 20, "steps": 10000,
                }),
            ))
            db_session.add(Workout(
                user_id="test_user", name="Fuerza",
                date=datetime.combine(d, datetime.min.time()),
                duration=3600, calories=300,
            ))
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        for entry in data:
            assert 0 <= entry["readiness"] <= 100
            assert entry["volume"] == 60
            assert entry["avgHr"] is None

    def test_trend_empty(self, client, headers):
        """No data → empty list."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_trend_custom_days(self, client, headers, db_session):
        """days=30 → returns data."""
        db_session.add(Biometrics(
            user_id="test_user", date=date.today().isoformat(),
            data=json.dumps({"lastSevenDaysAvgRHR": 60, "sleep": 7}),
        ))
        db_session.commit()

        resp = client.get(f"{self.API_PATH}?days=30", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_trend_invalid_days(self, client, headers):
        """days=6 → 422 (ge=7), days=366 → 422 (le=365)."""
        resp = client.get(f"{self.API_PATH}?days=6", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?days=366", headers=headers)
        assert resp.status_code == 422

    def test_trend_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


class TestMuscleVolumeEndpoint:
    """GET /api/v1/dashboard/muscle-volume"""

    API_PATH = f"{settings.API_V1_STR}/dashboard/muscle-volume"

    def test_volume_with_keywords(self, client, headers, db_session):
        """'Bench Press' → Chest, 'Sentadilla' → Legs."""
        today = date.today()
        db_session.add(Workout(
            user_id="test_user", name="Bench Press",
            date=datetime.combine(today - timedelta(days=2), datetime.min.time()),
            duration=3600, calories=300,
        ))
        db_session.add(Workout(
            user_id="test_user", name="Sentadilla",
            date=datetime.combine(today - timedelta(days=1), datetime.min.time()),
            duration=2700, calories=250,
        ))
        db_session.commit()

        resp = client.get(f"{self.API_PATH}?weeks=4", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        total_chest = sum(d["Chest"] for d in data)
        total_legs = sum(d["Legs"] for d in data)
        assert total_chest >= 60
        assert total_legs >= 45

    def test_volume_default_distribution(self, client, headers, db_session):
        """Strength workout with no muscle match → equally to Chest/Back/Legs."""
        db_session.add(Workout(
            user_id="test_user", name="Fuerza general",
            date=datetime.combine(date.today() - timedelta(days=1), datetime.min.time()),
            duration=3600, calories=300,
        ))
        db_session.commit()

        resp = client.get(f"{self.API_PATH}?weeks=4", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        total_chest = sum(d["Chest"] for d in data)
        total_back = sum(d["Back"] for d in data)
        total_legs = sum(d["Legs"] for d in data)
        assert total_chest == 20
        assert total_back == 20
        assert total_legs == 20

    def test_volume_empty(self, client, headers):
        """No data → weeks entries with zeros."""
        resp = client.get(f"{self.API_PATH}?weeks=4", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        for d in data:
            assert d["Chest"] == 0
            assert d["Back"] == 0
            assert d["Legs"] == 0
            assert d["Shoulders"] == 0
            assert d["Arms"] == 0
            assert d["Core"] == 0

    def test_volume_custom_weeks(self, client, headers):
        """weeks=8 → 8 entries."""
        resp = client.get(f"{self.API_PATH}?weeks=8", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 8

    def test_volume_invalid_weeks(self, client, headers):
        """weeks=3 → 422 (ge=4), weeks=60 → 422 (le=52)."""
        resp = client.get(f"{self.API_PATH}?weeks=3", headers=headers)
        assert resp.status_code == 422
        resp = client.get(f"{self.API_PATH}?weeks=60", headers=headers)
        assert resp.status_code == 422

    def test_volume_unauthorized(self, client):
        """401 without x-user-id."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
