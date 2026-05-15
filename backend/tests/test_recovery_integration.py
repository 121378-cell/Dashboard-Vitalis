import json
import os
import sys
from datetime import date, datetime, timezone, timedelta
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
from app.models.memory import AtlasMemory
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.injury_prevention_service import (
    InjuryPreventionService,
    AlertLevel,
    RecoveryStatus,
    RecoverySession,
    Alert,
)
from app.services.memory_service import MemoryService


# ---------------------------------------------------------------------------
# App de test
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Recovery API")
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

def _create_injury_memory(
    db_session,
    user_id="test_user",
    content="Dolor en hombro derecho",
    importance=7,
    date_str=None,
    tags=None,
    memory_type="injury",
):
    if date_str is None:
        date_str = date.today().isoformat()
    if tags is None:
        tags = ["injury", "shoulder_right", "pain_level_7"]

    mem = AtlasMemory(
        user_id=user_id,
        type=memory_type,
        content=content,
        date=date_str,
        importance=importance,
        tags=tags,
        source="user_report",
    )
    db_session.add(mem)
    db_session.commit()
    db_session.refresh(mem)
    return mem


def _make_status(
    alert_level=AlertLevel.GREEN,
    alerts=None,
    readiness_penalty=0.0,
    active_injuries=None,
    zones_to_avoid=None,
    recommendations=None,
    forecast_risk=0.0,
):
    return RecoveryStatus(
        alert_level=alert_level,
        alerts=alerts or [],
        readiness_penalty=readiness_penalty,
        active_injuries=active_injuries or [],
        zones_to_avoid=zones_to_avoid or [],
        recommendations=recommendations or [],
        forecast_risk=forecast_risk,
    )


# ============================================================
# TestRecoveryStatusEndpoint
# ============================================================

class TestRecoveryStatusEndpoint:
    API_PATH = "/api/v1/recovery/status"

    def test_status_green(self, client, headers):
        """Green level returns no alerts, zero penalty."""
        status = _make_status(
            alert_level=AlertLevel.GREEN,
            recommendations=["Todo bien, sigue entrenando"],
        )
        with patch.object(InjuryPreventionService, "get_current_status", return_value=status):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_level"] == "optimal"
        assert data["readiness_penalty"] == 0.0
        assert len(data["alerts"]) == 0

    def test_status_yellow(self, client, headers):
        """Yellow level with alerts and penalty."""
        alert = Alert(level=AlertLevel.YELLOW, reason="HRV baja", indicator="hrv",
                      value=35.0, threshold=45.0, action_required="reducir carga")
        status = _make_status(
            alert_level=AlertLevel.YELLOW,
            alerts=[alert],
            readiness_penalty=15.0,
            recommendations=["Reduce carga esta semana"],
        )
        with patch.object(InjuryPreventionService, "get_current_status", return_value=status):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_level"] == "caution"
        assert data["readiness_penalty"] == 15.0
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["reason"] == "HRV baja"

    def test_status_red_with_active_injuries(self, client, headers):
        """Red level with active injuries and zones to avoid."""
        status = _make_status(
            alert_level=AlertLevel.RED,
            readiness_penalty=50.0,
            active_injuries=[{"zone": "shoulder_right", "pain_level": 8}],
            zones_to_avoid=["shoulder_right"],
            recommendations=["Consulta a un profesional"],
            forecast_risk=0.85,
        )
        with patch.object(InjuryPreventionService, "get_current_status", return_value=status):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_level"] == "stop"
        assert data["readiness_penalty"] == 50.0
        assert "shoulder_right" in data["zones_to_avoid"]
        assert data["forecast_risk"] == 0.85

    def test_status_unauthorized(self, client):
        """No x-user-id -> 401."""
        with patch.object(InjuryPreventionService, "get_current_status") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestRecoverySessionEndpoint
# ============================================================

class TestRecoverySessionEndpoint:
    API_PATH = "/api/v1/recovery/session"

    def test_session_green(self, client, headers):
        """Green level returns mobility/recovery session."""
        status = _make_status(alert_level=AlertLevel.GREEN)
        session = RecoverySession(
            session_type="mobility",
            duration_min=15,
            exercises=["neck_rolls", "shoulder_circles"],
            message="Sesion de movilidad",
            optional=["foam_rolling"],
        )

        status_patch = patch.object(InjuryPreventionService, "get_current_status", return_value=status)
        session_patch = patch.object(InjuryPreventionService, "generate_recovery_session", return_value=session)

        with status_patch, session_patch:
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "mobility"
        assert data["duration_min"] == 15
        assert "neck_rolls" in data["exercises"]
        assert data["alert_level"] == "optimal"

    def test_session_red_with_injuries(self, client, headers):
        """Red level returns active recovery with injury recommendations."""
        status = _make_status(
            alert_level=AlertLevel.RED,
            active_injuries=[{"zone": "knee_right", "pain_level": 8}],
        )
        session = RecoverySession(
            session_type="active_recovery",
            duration_min=30,
            exercises=["knee_stretches", "hip_openers"],
            message="Sesion de recuperacion activa",
            optional=["ice_application"],
            alert_level=AlertLevel.RED,
        )

        status_patch = patch.object(InjuryPreventionService, "get_current_status", return_value=status)
        session_patch = patch.object(InjuryPreventionService, "generate_recovery_session", return_value=session)

        with status_patch, session_patch:
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "active_recovery"
        assert data["alert_level"] == "stop"

    def test_session_unauthorized(self, client):
        """No x-user-id -> 401."""
        with patch.object(InjuryPreventionService, "get_current_status") as mock:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 401
        mock.assert_not_called()


# ============================================================
# TestReportPainEndpoint
# ============================================================

class TestReportPainEndpoint:
    API_PATH = "/api/v1/recovery/report-pain"

    def test_report_pain_normal(self, client, db_session, headers):
        """Pain < 8 saves injury memory and returns normal message."""
        resp = client.post(self.API_PATH, json={
            "zone": "lower_back",
            "pain_level": 4,
            "pain_type": "soreness",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "saved"
        assert "ajustara" in data["message"] or "ajustar" in data["message"]

        memories = db_session.query(AtlasMemory).filter(
            AtlasMemory.user_id == "test_user",
            AtlasMemory.type == "injury",
        ).all()
        assert len(memories) >= 1

    def test_report_pain_high_trigger_health_alert(self, client, db_session, headers):
        """Pain >= 8 creates injury + health_alert memories."""
        resp = client.post(self.API_PATH, json={
            "zone": "knee_right",
            "pain_level": 9,
            "pain_type": "sharp",
            "notes": "Dolor al correr",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "saved"
        assert "profesional" in data["message"]

        health_alerts = db_session.query(AtlasMemory).filter(
            AtlasMemory.user_id == "test_user",
            AtlasMemory.type == "health_alert",
        ).all()
        assert len(health_alerts) >= 1

    def test_report_pain_with_notes(self, client, db_session, headers):
        """Notes are included in the memory content."""
        resp = client.post(self.API_PATH, json={
            "zone": "shoulder_right",
            "pain_level": 5,
            "pain_type": "ache",
            "notes": "Despues de press militar",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "saved"

        memories = db_session.query(AtlasMemory).filter(
            AtlasMemory.user_id == "test_user",
        ).all()
        assert any("Despues de press militar" in m.content for m in memories)

    def test_report_pain_zones_to_avoid(self, client, db_session, headers):
        """Response includes zones_to_avoid with affected muscles."""
        resp = client.post(self.API_PATH, json={
            "zone": "shoulder_right",
            "pain_level": 6,
            "pain_type": "pain",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "zones_to_avoid" in data
        assert "shoulder_right" in data["zones_to_avoid"]

    def test_report_pain_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.post(self.API_PATH, json={
            "zone": "neck", "pain_level": 3, "pain_type": "stiffness",
        })
        assert resp.status_code == 401


# ============================================================
# TestInjuryHistoryEndpoint
# ============================================================

class TestInjuryHistoryEndpoint:
    API_PATH = "/api/v1/recovery/injury-history"

    def test_history_with_data(self, client, db_session, headers):
        """Returns injury memories formatted as records."""
        _create_injury_memory(db_session, tags=["injury", "shoulder_right", "pain_level_7"])
        _create_injury_memory(db_session, tags=["injury", "lower_back", "pain_level_4"],
                              date_str=(date.today() - timedelta(days=5)).isoformat())

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        pain_levels = {r["pain_level"] for r in data}
        assert 4 in pain_levels
        assert 7 in pain_levels

    def test_history_empty(self, client, headers):
        """No injury memories -> empty list."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_other_user(self, client, db_session, headers):
        """Other user's injuries not visible."""
        _create_injury_memory(db_session, user_id="other_user")
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ============================================================
# TestAcknowledgeAlertEndpoint
# ============================================================

class TestAcknowledgeAlertEndpoint:
    API_PATH = "/api/v1/recovery/acknowledge-alert"

    def test_acknowledge_success(self, client, db_session, headers):
        """Acknowledging creates a preference memory."""
        resp = client.post(self.API_PATH, json={
            "alert_indicator": "hrv_low",
            "alert_reason": "HRV por debajo del umbral",
            "user_action": "Tomare un dia de descanso",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "acknowledged"
        assert data["indicator"] == "hrv_low"

        memories = db_session.query(AtlasMemory).filter(
            AtlasMemory.user_id == "test_user",
            AtlasMemory.type == "preference",
        ).all()
        assert len(memories) >= 1
        assert "hrv_low" in str(memories[0].tags)

    def test_acknowledge_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.post(self.API_PATH, json={
            "alert_indicator": "test",
            "alert_reason": "test",
            "user_action": "test",
        })
        assert resp.status_code == 401


# ============================================================
# TestInjuryPatternsEndpoint
# ============================================================

class TestInjuryPatternsEndpoint:
    API_PATH = "/api/v1/recovery/injury-patterns"

    def test_patterns_with_data(self, client, db_session, headers):
        """Multiple injuries to same zone produce pattern insights."""
        today = date.today()
        _create_injury_memory(db_session, tags=["injury", "shoulder_right", "pain_level_7"],
                              content="Dolor hombro", date_str=(today - timedelta(days=10)).isoformat())
        _create_injury_memory(db_session, tags=["injury", "shoulder_right", "pain_level_5"],
                              content="Otro dolor hombro", date_str=(today - timedelta(days=3)).isoformat())
        _create_injury_memory(db_session, tags=["injury", "lower_back", "pain_level_4"],
                              content="Dolor lumbar", date_str=(today - timedelta(days=5)).isoformat())

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data["total_injuries"] >= 3
        assert "shoulder_right" in data["zone_frequency"]

    def test_patterns_no_injuries(self, client, headers):
        """No injury memories -> empty/false patterns."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["patterns"] == []
        assert data["zone_frequency"] == {}
        assert data["insights"] == []

    def test_patterns_unauthorized(self, client):
        """No x-user-id -> 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ============================================================
# TestBodyZonesEndpoint (public — no auth required)
# ============================================================

class TestBodyZonesEndpoint:
    API_PATH = "/api/v1/recovery/body-zones"

    def test_body_zones_list(self, client):
        """Returns a list of body zone keys."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        zones = data.get("zones", [])
        assert len(zones) > 10
        assert "neck" in zones
        assert "shoulder_right" in zones
        assert "knee_left" in zones

    def test_body_zones_includes_all_major(self, client):
        """Known zones are present."""
        resp = client.get(self.API_PATH)
        zones = resp.json().get("zones", [])
        for expected in ["neck", "chest", "core", "lower_back", "upper_back"]:
            assert expected in zones, f"Missing zone: {expected}"


# ============================================================
# TestZoneExercisesEndpoint (public — no auth required)
# ============================================================

class TestZoneExercisesEndpoint:
    API_PATH = "/api/v1/recovery/zone-exercises"

    def test_zone_exercises_found(self, client):
        """Known zone returns exercise list."""
        resp = client.get(f"{self.API_PATH}/neck")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "alternative_exercises" in data
        assert len(data["alternative_exercises"]) > 0
        assert data["zone"] == "neck"

    def test_zone_exercises_not_found(self, client):
        """Unknown zone returns empty list."""
        resp = client.get(f"{self.API_PATH}/nonexistent_zone_xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alternative_exercises"] == []

    def test_zone_exercises_knee_right(self, client):
        """knee_right has specific exercises."""
        resp = client.get(f"{self.API_PATH}/knee_right")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "alternative_exercises" in data
        assert len(data["alternative_exercises"]) > 0


# ============================================================
# TestResolveZoneEndpoint (public — no auth required)
# ============================================================

class TestResolveZoneEndpoint:
    API_PATH = "/api/v1/recovery/resolve-zone"

    def test_resolve_english(self, client):
        """English zone descriptions resolve correctly."""
        resp = client.post(self.API_PATH, params={"description": "knee"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.json() == {"zone": "knee_right"}

    def test_resolve_spanish(self, client):
        """Spanish zone descriptions resolve correctly."""
        resp = client.post(self.API_PATH, params={"description": "rodilla"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.json() == {"zone": "knee_right"}

    def test_resolve_left_right(self, client):
        """Left/right specifiers work."""
        resp = client.post(self.API_PATH, params={"description": "left shoulder"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.json() == {"zone": "shoulder_left"}

        resp = client.post(self.API_PATH, params={"description": "right shoulder"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert resp.json() == {"zone": "shoulder_right"}

    def test_resolve_unknown(self, client):
        """Unrecognized description -> 404."""
        resp = client.post(self.API_PATH, params={"description": "zzzzzxyz_nonexistent"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text[:200]}"
