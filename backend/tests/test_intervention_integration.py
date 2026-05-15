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
    is_active=True,
    decision_deadline=None,
    title="Test Intervention",
    message="This is a test intervention.",
    priority="medium",
):
    """Crea un AtlasIntervention de prueba."""
    now = created_at or datetime.now(timezone.utc)
    intervention = AtlasIntervention(
        user_id=user_id,
        intervention_type=intervention_type,
        autonomy_level=autonomy_level,
        title=title,
        message=message,
        priority=priority,
        status=status,
        created_at=now,
        responded_at=responded_at,
        executed_at=executed_at,
        response=response,
        outcome_score=outcome_score,
        is_active=is_active,
        decision_deadline=decision_deadline,
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


# ---------------------------------------------------------------------------
# Tests: GET /interventions/pending
# ---------------------------------------------------------------------------


class TestPendingEndpoint:
    """GET /interventions/pending"""

    API_PATH = "/api/v1/interventions/pending"
    HEADERS = {"x-user-id": "test_user"}

    def test_pending_with_data(self, client, db_session):
        """Intervenciones pendientes → 200 + listado ordenado DESC."""
        # Crear 2 pendientes (sin deadline → no expiran)
        i1 = _create_intervention(db_session, status="pending", created_at=datetime.now(timezone.utc))
        i2 = _create_intervention(
            db_session, status="pending",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Deberían venir ordenados DESC por created_at
        assert data[0]["id"] == i1.id  # i1 más reciente
        assert data[1]["id"] == i2.id
        assert data[0]["status"] == "pending"

    def test_pending_empty(self, client):
        """Sin intervenciones → 200 + []."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pending_other_user(self, client, db_session):
        """Intervenciones de otro usuario → vacío."""
        _create_intervention(db_session, user_id="other_user", status="pending")
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pending_excludes_responded(self, client, db_session):
        """Intervenciones no-pending no aparecen."""
        _create_intervention(db_session, status="accepted", response="accepted")
        _create_intervention(db_session, status="rejected", response="rejected")
        _create_intervention(db_session, status="executed")
        _create_intervention(db_session, status="pending")  # Solo esta debería aparecer
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_pending_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/active
# ---------------------------------------------------------------------------


class TestActiveEndpoint:
    """GET /interventions/active"""

    API_PATH = "/api/v1/interventions/active"
    HEADERS = {"x-user-id": "test_user"}

    def test_active_with_data(self, client, db_session):
        """Intervenciones activas recientes → 200 + listado."""
        i1 = _create_intervention(db_session, status="pending", created_at=datetime.now(timezone.utc))
        i2 = _create_intervention(
            db_session, status="accepted", response="accepted",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == i1.id  # Más reciente primero
        assert data[1]["id"] == i2.id

    def test_active_empty(self, client):
        """Sin intervenciones → 200 + []."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_active_excludes_old(self, client, db_session):
        """Intervención de hace 10 días → no listada."""
        _create_intervention(
            db_session, status="pending",
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_active_excludes_inactive(self, client, db_session):
        """Intervención con is_active=False → no listada."""
        _create_intervention(
            db_session, status="pending", is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_active_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/ (listado con filtros)
# ---------------------------------------------------------------------------


class TestListEndpoint:
    """GET /interventions/"""

    API_PATH = "/api/v1/interventions/"
    HEADERS = {"x-user-id": "test_user"}

    def test_list_with_data(self, client, db_session):
        """Intervenciones existentes → 200 + listado ordenado DESC."""
        now = datetime.now(timezone.utc)
        i1 = _create_intervention(
            db_session, status="pending", created_at=now,
        )
        i2 = _create_intervention(
            db_session, status="accepted", response="accepted",
            created_at=now - timedelta(hours=2),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == i1.id  # Más reciente primero
        assert data[1]["id"] == i2.id

    def test_list_filters_by_days(self, client, db_session):
        """Intervención fuera del rango default de 30 días → no listada."""
        _create_intervention(
            db_session, status="pending",
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_custom_days(self, client, db_session):
        """Parámetro days=60 incluye intervención de hace 45 días."""
        _create_intervention(
            db_session, status="pending",
            created_at=datetime.now(timezone.utc) - timedelta(days=45),
        )
        resp = client.get(f"{self.API_PATH}?days=60", headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_list_filters_by_status(self, client, db_session):
        """Filtro status=accepted → solo intervenciones accepted."""
        _create_intervention(db_session, status="pending", created_at=datetime.now(timezone.utc))
        i2 = _create_intervention(
            db_session, status="accepted", response="accepted",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        resp = client.get(f"{self.API_PATH}?status=accepted", headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == i2.id
        assert data[0]["status"] == "accepted"

    def test_list_empty(self, client):
        """Sin intervenciones → 200 + []."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_other_user(self, client, db_session):
        """Intervenciones de otro usuario → vacío."""
        _create_intervention(db_session, user_id="other_user", status="pending",
                             created_at=datetime.now(timezone.utc))
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401

    def test_list_invalid_days(self, client):
        """Parámetro days fuera de rango (0) → 422."""
        resp = client.get(f"{self.API_PATH}?days=0", headers=self.HEADERS)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: GET /interventions/stats
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    """GET /interventions/stats"""

    API_PATH = "/api/v1/interventions/stats"
    HEADERS = {"x-user-id": "test_user"}

    def test_stats_with_data(self, client, db_session):
        """Intervenciones con varios estados → stats correctos."""
        _create_intervention(db_session, status="accepted", response="accepted",
                             created_at=datetime.now(timezone.utc))
        _create_intervention(db_session, status="accepted", response="accepted",
                             created_at=datetime.now(timezone.utc))
        _create_intervention(db_session, status="rejected", response="rejected",
                             created_at=datetime.now(timezone.utc))
        _create_intervention(db_session, status="pending",
                             created_at=datetime.now(timezone.utc))
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert data["pending"] == 1
        assert data["accepted"] == 2
        assert data["rejected"] == 1
        # acceptance_rate = 2 / (2 + 1) * 100 = 66.7
        assert data["acceptance_rate"] == 66.7

    def test_stats_empty(self, client):
        """Sin intervenciones → todo en 0."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["accepted"] == 0
        assert data["rejected"] == 0
        assert data["acceptance_rate"] == 0

    def test_stats_other_user(self, client, db_session):
        """Intervenciones de otro usuario → todo en 0."""
        _create_intervention(db_session, user_id="other_user", status="accepted",
                             response="accepted", created_at=datetime.now(timezone.utc))
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["acceptance_rate"] == 0

    def test_stats_only_pending(self, client, db_session):
        """Solo intervenciones pending → acceptance_rate=0 (sin accepted+rejected)."""
        _create_intervention(db_session, status="pending",
                             created_at=datetime.now(timezone.utc))
        _create_intervention(db_session, status="pending",
                             created_at=datetime.now(timezone.utc))
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["pending"] == 2
        assert data["accepted"] == 0
        assert data["rejected"] == 0
        assert data["acceptance_rate"] == 0

    def test_stats_all_rejected(self, client, db_session):
        """Todas rechazadas → acceptance_rate=0."""
        _create_intervention(db_session, status="rejected", response="rejected",
                             created_at=datetime.now(timezone.utc))
        _create_intervention(db_session, status="rejected", response="rejected",
                             created_at=datetime.now(timezone.utc))
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["accepted"] == 0
        assert data["rejected"] == 2
        assert data["acceptance_rate"] == 0

    def test_stats_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/outcome-stats (estadísticas de efectividad)
# ---------------------------------------------------------------------------


class TestOutcomeStatsEndpoint:
    """GET /interventions/outcome-stats"""

    API_PATH = "/api/v1/interventions/outcome-stats"
    HEADERS = {"x-user-id": "test_user"}

    def test_outcome_stats_with_data(self, client, db_session):
        """Intervenciones con outcome_scores → stats completos."""
        now = datetime.now(timezone.utc)
        # 2 adherence_nudge: 1 accepted, 1 rejected
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            status="accepted", response="accepted", outcome_score=0.85,
            created_at=now,
        )
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            status="rejected", response="rejected", outcome_score=0.2,
            created_at=now - timedelta(hours=1),
        )
        # 1 check_in_request: accepted
        _create_intervention(
            db_session, intervention_type="check_in_request",
            status="accepted", response="accepted", outcome_score=0.9,
            created_at=now - timedelta(hours=2),
        )

        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["by_type"]) == 2
        assert data["avg_score"] is not None
        assert data["acceptance_rate"] is not None
        assert isinstance(data["outcome_distribution"], dict)
        # by_type items have type, count, avg_score, acceptance_rate
        for entry in data["by_type"]:
            assert "type" in entry
            assert "count" in entry
            assert entry["count"] > 0

    def test_outcome_stats_filter_by_type(self, client, db_session):
        """Filtro ?intervention_type=adherence_nudge → solo ese tipo."""
        now = datetime.now(timezone.utc)
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            status="accepted", response="accepted", outcome_score=0.85,
            created_at=now,
        )
        _create_intervention(
            db_session, intervention_type="check_in_request",
            status="accepted", response="accepted", outcome_score=0.9,
            created_at=now - timedelta(hours=1),
        )
        resp = client.get(
            f"{self.API_PATH}?intervention_type=adherence_nudge",
            headers=self.HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["by_type"]) == 1
        assert data["by_type"][0]["type"] == "adherence_nudge"

    def test_outcome_stats_empty(self, client):
        """Sin intervenciones → valores por defecto."""
        resp = client.get(self.API_PATH, headers={"x-user-id": "empty_user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["by_type"] == []
        assert data["avg_score"] is None
        assert data["acceptance_rate"] is None
        assert data["outcome_distribution"] == {}

    def test_outcome_stats_other_user(self, client, db_session):
        """Intervenciones de otro usuario → vacío."""
        _create_intervention(
            db_session, user_id="other_user", intervention_type="adherence_nudge",
            status="accepted", response="accepted", outcome_score=0.85,
            created_at=datetime.now(timezone.utc),
        )
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_outcome_stats_unauthorized(self, client):
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

    def test_best_channel_with_data(self, client, db_session):
        """Intervenciones con diferentes autonomy_levels → mejor canal."""
        now = datetime.now(timezone.utc)
        # AUTONOMOUS → canal "app" con score alto
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            autonomy_level="AUTONOMOUS", status="accepted",
            response="accepted", outcome_score=0.9,
            created_at=now,
        )
        # PROPOSAL → canales "app" + "system"
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            autonomy_level="PROPOSAL", status="rejected",
            response="rejected", outcome_score=0.3,
            created_at=now - timedelta(hours=1),
        )
        resp = client.get(
            f"{self.API_PATH}?intervention_type=adherence_nudge",
            headers=self.HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_channel"] in ("app", "system")
        assert isinstance(data["scores_by_channel"], dict)
        assert len(data["scores_by_channel"]) > 0
        assert isinstance(data["confidence"], float)
        assert data["sample_size"] > 0

    def test_best_channel_no_data(self, client):
        """Sin datos → valores por defecto."""
        resp = client.get(
            f"{self.API_PATH}?intervention_type=adherence_nudge",
            headers=self.HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_channel"] == "app"
        assert data["scores_by_channel"] == {}
        assert data["confidence"] == 0.0
        assert data["sample_size"] == 0

    def test_best_channel_missing_type(self, client):
        """Falta ?intervention_type (required) → 422."""
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 422

    def test_best_channel_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(f"{self.API_PATH}?intervention_type=adherence_nudge")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/outcome-stats/best-timing
# ---------------------------------------------------------------------------


class TestBestTimingEndpoint:
    """GET /interventions/outcome-stats/best-timing"""

    API_PATH = "/api/v1/interventions/outcome-stats/best-timing"
    HEADERS = {"x-user-id": "test_user"}

    def test_best_timing_with_data(self, client, db_session):
        """Intervenciones en diferentes horas → mejor franja horaria."""
        now = datetime.now(timezone.utc)
        # Mañana (6-12) con score alto
        morning = now.replace(hour=8, minute=0, second=0, microsecond=0)
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            status="accepted", response="accepted", outcome_score=0.9,
            created_at=morning,
        )
        # Noche (22-06) con score bajo
        night = now.replace(hour=23, minute=0, second=0, microsecond=0)
        _create_intervention(
            db_session, intervention_type="adherence_nudge",
            status="rejected", response="rejected", outcome_score=0.2,
            created_at=night,
        )
        resp = client.get(
            f"{self.API_PATH}?intervention_type=adherence_nudge",
            headers=self.HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_timing"] in ("morning", "afternoon", "evening", "night")
        assert isinstance(data["scores_by_timing"], dict)
        assert len(data["scores_by_timing"]) > 0
        assert isinstance(data["confidence"], float)
        assert data["sample_size"] > 0

    def test_best_timing_no_data(self, client):
        """Sin datos → valores por defecto."""
        resp = client.get(
            f"{self.API_PATH}?intervention_type=adherence_nudge",
            headers=self.HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["best_timing"] == "morning"
        assert data["scores_by_timing"] == {}
        assert data["confidence"] == 0.0
        assert data["sample_size"] == 0

    def test_best_timing_missing_type(self, client):
        """Falta ?intervention_type (required) → 422."""
        resp = client.get(self.API_PATH, headers=self.HEADERS)
        assert resp.status_code == 422

    def test_best_timing_unauthorized(self, client):
        """Sin header de autenticación → 401."""
        resp = client.get(f"{self.API_PATH}?intervention_type=adherence_nudge")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interventions/{intervention_id}
# ---------------------------------------------------------------------------


class TestGetInterventionEndpoint:
    """GET /interventions/{intervention_id}"""

    API_PATH = "/api/v1/interventions"
    HEADERS = {"x-user-id": "test_user"}

    def test_get_by_id_found(self, client, db_session):
        """Intervención existente → 200 + datos completos."""
        now = datetime.now(timezone.utc)
        inv = _create_intervention(
            db_session, status="pending",
            title="Intervención de prueba",
            message="Mensaje de prueba",
            priority="high",
            created_at=now,
        )
        resp = client.get(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == inv.id
        assert data["intervention_type"] == "adherence_nudge"
        assert data["autonomy_level"] == "PROPOSAL"
        assert data["title"] == "Intervención de prueba"
        assert data["message"] == "Mensaje de prueba"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert data["created_at"] is not None
        assert data["response"] is None
        assert data["outcome_score"] is None
        assert data["metadata"] is None

    def test_get_by_id_with_response(self, client, db_session):
        """Intervención con respuesta completa → 200 + todos los campos."""
        now = datetime.now(timezone.utc)
        inv = _create_intervention(
            db_session, status="accepted", response="accepted",
            outcome_score=0.85,
            created_at=now - timedelta(hours=24),
            responded_at=now - timedelta(hours=2),
            executed_at=now,
        )
        resp = client.get(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "accepted"
        assert data["outcome_score"] == 0.85
        assert data["responded_at"] is not None
        assert data["executed_at"] is not None

    def test_get_by_id_not_found(self, client):
        """ID inexistente → 404."""
        resp = client.get(f"{self.API_PATH}/99999", headers=self.HEADERS)
        assert resp.status_code == 404
        assert "no encontrada" in resp.json()["detail"].lower()

    def test_get_by_id_wrong_user(self, client, db_session):
        """Intervención de otro usuario → 404 (filtro por user_id)."""
        inv = _create_intervention(db_session, user_id="other_user", status="pending")
        resp = client.get(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp.status_code == 404

    def test_get_by_id_unauthorized(self, client, db_session):
        """Sin header de autenticación → 401."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.get(f"{self.API_PATH}/{inv.id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: DELETE /interventions/{intervention_id}
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    """DELETE /interventions/{intervention_id}"""

    API_PATH = "/api/v1/interventions"
    HEADERS = {"x-user-id": "test_user"}

    def test_delete_found(self, client, db_session):
        """Eliminar intervención existente → 200 + ya no existe."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.delete(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Intervención eliminada"

        # Verificar que ya no existe
        resp2 = client.get(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp2.status_code == 404

    def test_delete_not_found(self, client):
        """ID inexistente → 404."""
        resp = client.delete(f"{self.API_PATH}/99999", headers=self.HEADERS)
        assert resp.status_code == 404
        assert "no encontrada" in resp.json()["detail"].lower()

    def test_delete_wrong_user(self, client, db_session):
        """Intervención de otro usuario → 404 (filtro por user_id)."""
        inv = _create_intervention(db_session, user_id="other_user", status="pending")
        resp = client.delete(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp.status_code == 404

    def test_delete_unauthorized(self, client, db_session):
        """Sin header de autenticación → 401."""
        inv = _create_intervention(db_session, status="pending")
        resp = client.delete(f"{self.API_PATH}/{inv.id}")
        assert resp.status_code == 401

    def test_delete_twice(self, client, db_session):
        """Eliminar dos veces → 200 primera, 404 segunda."""
        inv = _create_intervention(db_session, status="pending")
        # Primera vez
        resp1 = client.delete(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp1.status_code == 200
        # Segunda vez
        resp2 = client.delete(f"{self.API_PATH}/{inv.id}", headers=self.HEADERS)
        assert resp2.status_code == 404
