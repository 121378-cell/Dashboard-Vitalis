"""
Tests de API: endpoints GET /interventions/outcome-stats.
=========================================================

Verifica los 3 endpoints expuestos:
- GET /interventions/outcome-stats
- GET /interventions/outcome-stats/best-channel
- GET /interventions/outcome-stats/best-timing

Usa FastAPI TestClient con dependencias override para base de datos en memoria.
Crea una app de test independiente (sin lifespan de producción) para evitar
conflictos con migraciones y bootstrap.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Importar modelos ANTES de create_all para que se registren en Base.metadata
from app.db.base import Base
from app.models.atlas_intervention import AtlasIntervention
from app.api.api_v1.api import api_router
from app.core.config import settings


# ---------------------------------------------------------------------------
# App de test (sin lifespan de producción)
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS API")
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
    Override de get_db + patch SessionLocal para todos los servicios.
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_intervention(
    db_session,
    user_id="test_user",
    intervention_type="adherence_nudge",
    autonomy_level="PROPOSAL",
    status="pending",
    response=None,
    outcome_score=None,
    created_at=None,
    responded_at=None,
    executed_at=None,
):
    """Crea un AtlasIntervention de prueba."""
    now = created_at or datetime.now(timezone.utc)
    intervention = AtlasIntervention(
        user_id=user_id,
        intervention_type=intervention_type,
        autonomy_level=autonomy_level,
        title="Test Intervention",
        message="This is a test intervention.",
        priority="medium",
        status=status,
        created_at=now,
        responded_at=responded_at,
        executed_at=executed_at,
        response=response,
        outcome_score=outcome_score,
    )
    db_session.add(intervention)
    db_session.commit()
    db_session.refresh(intervention)
    return intervention


# ---------------------------------------------------------------------------
# Tests: GET /interventions/outcome-stats
# ---------------------------------------------------------------------------


class TestOutcomeStatsEndpoint:
    """GET /interventions/outcome-stats"""

    API_PATH = "/api/v1/interventions/outcome-stats"
    HEADERS = {"x-user-id": "test_user"}

    def test_stats_with_data(self, client, db_session):
        """Intervenciones con scores → stats completas."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            _create_intervention(
                db_session,
                intervention_type="adherence_nudge",
                status="completed",
                response="accepted" if i < 2 else "rejected",
                outcome_score=0.9 if i < 2 else 0.2,
                responded_at=now,
                executed_at=now if i < 2 else None,
                created_at=now - timedelta(hours=i + 1),
            )

        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["by_type"]) == 1
        assert data["by_type"][0]["type"] == "adherence_nudge"
        assert data["acceptance_rate"] == pytest.approx(0.667, abs=0.001)
        assert data["avg_score"] == pytest.approx(0.667, abs=0.001)
        assert "outcome_distribution" in data

    def test_stats_empty(self, client, db_session):
        """Sin intervenciones → stats vacías."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["by_type"] == []
        assert data["avg_score"] is None
        assert data["acceptance_rate"] is None

    def test_stats_filter_by_type(self, client, db_session):
        """Filtro por intervention_type."""
        now = datetime.now(timezone.utc)
        _create_intervention(
            db_session, intervention_type="check_in", status="completed",
            response="accepted", outcome_score=0.8, responded_at=now,
        )
        _create_intervention(
            db_session, intervention_type="fatigue_alert", status="completed",
            response="accepted", outcome_score=0.9, responded_at=now,
        )

        resp = client.get(
            self.API_PATH,
            headers=self.HEADERS,
            params={"intervention_type": "check_in"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["by_type"][0]["type"] == "check_in"

    def test_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/outcome-stats/best-channel
# ---------------------------------------------------------------------------


class TestBestChannelEndpoint:
    """GET /interventions/outcome-stats/best-channel"""

    API_PATH = "/api/v1/interventions/outcome-stats/best-channel"
    HEADERS = {"x-user-id": "test_user"}

    def test_best_channel_found(self, client, db_session):
        """Intervenciones con distintos autonomy_level → mejor canal."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            _create_intervention(
                db_session, intervention_type="adherence_nudge",
                autonomy_level="AUTONOMOUS", status="completed",
                response="accepted", outcome_score=0.9,
                responded_at=now, executed_at=now,
            )
        for i in range(2):
            _create_intervention(
                db_session, intervention_type="adherence_nudge",
                autonomy_level="PROPOSAL", status="completed",
                response="accepted", outcome_score=0.6,
                responded_at=now, executed_at=now,
            )

        resp = client.get(
            self.API_PATH,
            headers=self.HEADERS,
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_channel"] == "app"
        assert data["sample_size"] > 0
        assert "scores_by_channel" in data

    def test_best_channel_no_data(self, client, db_session):
        """Sin datos → defaults."""
        resp = client.get(
            self.API_PATH,
            headers={"x-user-id": "empty_user"},
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_channel"] == "app"
        assert data["sample_size"] == 0

    def test_missing_required_param(self, client):
        """Falta intervention_type (required) → 422."""
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 422

    def test_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(
            self.API_PATH,
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/outcome-stats/best-timing
# ---------------------------------------------------------------------------


class TestBestTimingEndpoint:
    """GET /interventions/outcome-stats/best-timing"""

    API_PATH = "/api/v1/interventions/outcome-stats/best-timing"
    HEADERS = {"x-user-id": "test_user"}

    def test_best_timing_found(self, client, db_session):
        """Intervenciones en distintas horas → mejor timing."""
        base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(3):
            _create_intervention(
                db_session, intervention_type="adherence_nudge",
                status="completed", response="accepted",
                outcome_score=0.85,
                created_at=base.replace(hour=8),
                responded_at=base.replace(hour=8),
                executed_at=base.replace(hour=8),
            )
        for i in range(2):
            _create_intervention(
                db_session, intervention_type="adherence_nudge",
                status="completed", response="accepted",
                outcome_score=0.55,
                created_at=base.replace(hour=15),
                responded_at=base.replace(hour=15),
                executed_at=base.replace(hour=15),
            )

        resp = client.get(
            self.API_PATH,
            headers=self.HEADERS,
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_timing"] == "morning"
        assert data["sample_size"] == 5

    def test_best_timing_no_data(self, client, db_session):
        """Sin datos → defaults."""
        resp = client.get(
            self.API_PATH,
            headers={"x-user-id": "empty_user"},
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_timing"] == "morning"
        assert data["sample_size"] == 0

    def test_missing_required_param(self, client):
        """Falta intervention_type (required) → 422."""
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 422

    def test_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(
            self.API_PATH,
            params={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 401
