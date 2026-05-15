"""
Tests de integración: endpoints POST /respond y POST /trigger.
=============================================================

Verifica el flujo completo de intervenciones vía API:
- POST /interventions/respond/{id} → responder (accept/reject/snooze)
- POST /interventions/trigger → crear intervención manual

Usa FastAPI TestClient con dependencias override + StaticPool para
compartir la base SQLite en memoria entre fixtures y servicio.
"""

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    Override de get_db + patch SessionLocal para interceptar
    llamadas a SessionLocal() dentro de InterventionService.
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

    # También parchear módulos que importan SessionLocal con 'from ... import' (módulo-level)
    from app.services import intervention_service
    patcher2 = patch.object(intervention_service, "SessionLocal", TestSession)
    patcher2.start()

    from app.api.api_v1.endpoints import interventions as interventions_module
    patcher3 = patch.object(interventions_module, "SessionLocal", TestSession)
    patcher3.start()

    yield

    patcher3.stop()
    patcher2.stop()
    patcher.stop()
    test_app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def _mock_notifications():
    """Mock NotificationService para evitar efectos secundarios."""
    with patch("app.services.notification_service.NotificationService.send_notification") as mock:
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
# Tests: POST /interventions/respond/{intervention_id}
# ---------------------------------------------------------------------------


class TestRespondEndpoint:
    """POST /interventions/respond/{intervention_id}"""

    API_PATH = "/api/v1/interventions/respond"
    HEADERS = {"x-user-id": "test_user"}

    def test_respond_accepted(self, client, db_session):
        """Aceptar una intervención pendiente → 200 + status accepted."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "accepted"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Intervención accepted"

        # Verificar persistencia
        db_session.refresh(inv)
        # Al aceptar, execute_intervention actualiza status a "executed"
        assert inv.status == "executed"
        assert inv.response == "accepted"
        assert inv.responded_at is not None
        assert inv.outcome_score is not None

    def test_respond_rejected(self, client, db_session):
        """Rechazar una intervención pendiente → 200 + status rejected."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "rejected"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Intervención rejected"

        db_session.refresh(inv)
        assert inv.status == "rejected"
        assert inv.response == "rejected"
        assert inv.responded_at is not None
        assert inv.outcome_score is not None

    def test_respond_snoozed(self, client, db_session):
        """Posponer una intervención pendiente → 200 + deadline extendido."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "snoozed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Intervención snoozed"

        db_session.refresh(inv)
        assert inv.status == "pending"  # Snoozed mantiene pending
        assert inv.response == "snoozed"
        # deadline debe ser futuro (4h después)
        assert inv.decision_deadline is not None
        # SQLite almacena sin timezone; comparar naive con naive
        from datetime import datetime as dt_naive
        assert inv.decision_deadline > dt_naive.utcnow() - timedelta(hours=1)

    def test_respond_not_found(self, client):
        """Intervención inexistente → 400."""
        resp = client.post(
            f"{self.API_PATH}/99999",
            headers=self.HEADERS,
            json={"response": "accepted"},
        )
        assert resp.status_code == 400
        assert "no se pudo procesar" in resp.json()["detail"].lower()

    def test_respond_already_responded(self, client, db_session):
        """Intervención ya respondida → 400."""
        now = datetime.now(timezone.utc)
        inv = _create_intervention(
            db_session, status="accepted", response="accepted",
            responded_at=now,
        )
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "accepted"},
        )
        assert resp.status_code == 400

    def test_respond_invalid_response(self, client, db_session):
        """Respuesta inválida → 400 (validación en InterventionService)."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "invalid_option"},
        )
        assert resp.status_code == 400

    def test_respond_unauthorized(self, client, db_session):
        """Sin header de autenticación → 401."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            json={"response": "accepted"},
        )
        assert resp.status_code == 401

    def test_respond_wrong_user(self, client, db_session):
        """Intervención de otro usuario → 400 (no encontrada por user_id)."""
        inv = _create_intervention(db_session, user_id="other_user", status="pending")
        resp = client.post(
            f"{self.API_PATH}/{inv.id}",
            headers=self.HEADERS,
            json={"response": "accepted"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: POST /interventions/trigger
# ---------------------------------------------------------------------------


class TestTriggerEndpoint:
    """POST /interventions/trigger"""

    API_PATH = "/api/v1/interventions/trigger"
    HEADERS = {"x-user-id": "test_user"}

    def test_trigger_adherence_nudge(self, client, db_session):
        """Trigger tipo adherence_nudge → 200 + intervención creada."""
        resp = client.post(
            self.API_PATH,
            headers=self.HEADERS,
            json={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intervention_type"] == "adherence_nudge"
        assert data["autonomy_level"] == "AUTONOMOUS"
        assert data["status"] in ("pending", "executed")
        assert data["id"] > 0

    def test_trigger_check_in_request(self, client, db_session):
        """Trigger tipo check_in_request → 200."""
        resp = client.post(
            self.API_PATH,
            headers=self.HEADERS,
            json={"intervention_type": "check_in_request"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intervention_type"] == "check_in_request"

    def test_trigger_with_custom_message(self, client, db_session):
        """Trigger con mensaje personalizado → 200 + message coincide."""
        resp = client.post(
            self.API_PATH,
            headers=self.HEADERS,
            json={
                "intervention_type": "adherence_nudge",
                "message": "Mensaje personalizado de prueba",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Mensaje personalizado de prueba"

    def test_trigger_invalid_type(self, client):
        """Tipo de intervención inválido → 400."""
        resp = client.post(
            self.API_PATH,
            headers=self.HEADERS,
            json={"intervention_type": "non_existent_type"},
        )
        assert resp.status_code == 400
        assert "inválido" in resp.json()["detail"].lower()

    def test_trigger_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.post(
            self.API_PATH,
            json={"intervention_type": "adherence_nudge"},
        )
        assert resp.status_code == 401

    def test_trigger_missing_type(self, client):
        """Falta intervention_type (required) → 422."""
        resp = client.post(
            self.API_PATH,
            headers=self.HEADERS,
            json={},
        )
        assert resp.status_code == 422
