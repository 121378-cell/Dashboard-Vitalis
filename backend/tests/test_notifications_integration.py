"""
Tests de integracion para endpoints de Notifications (/api/v1/notifications/...)
Cubre los 7 endpoints: unread, unread-count, mark-read, history, send, register, briefing/today
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api.deps import get_db, get_current_user_id
from datetime import date, datetime

# --- Test App Setup ---
test_app = FastAPI()
from app.api.api_v1.endpoints.notifications import router
test_app.include_router(router, prefix="/notifications", tags=["notifications"])


@pytest.fixture(autouse=True)
def test_engine():
    """Creates a fresh in-memory SQLite database for each test."""
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
    """Overrides the get_db dependency with a test database session."""
    TestSession = sessionmaker(bind=test_engine)

    def _get_test_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _get_test_db
    yield
    test_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Test client with overridden dependencies."""
    test_app.dependency_overrides[get_current_user_id] = lambda: "test_user"
    return TestClient(test_app)


@pytest.fixture
def headers():
    """Headers with default user ID."""
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine, _override_db):
    """Provides a db_session for seeding data inside tests."""
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    yield db
    db.close()


# ===========================================================================
# 1. GET /notifications/unread — NO auth dep
# ===========================================================================
class TestUnreadEndpoint:
    API_PATH = "/notifications/unread"

    @pytest.fixture(autouse=True)
    def _no_auth(self):
        test_app.dependency_overrides.pop(get_current_user_id, None)
        yield

    def test_success_default_limit(self, client):
        """Should return unread notifications with default limit=20."""
        mock_result = [
            {"id": 1, "title": "Test", "message": "Hello", "read": False},
            {"id": 2, "title": "Another", "message": "World", "read": False},
        ]
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_unread",
            return_value=mock_result,
        ) as mock_get:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_get.assert_called_once()
        # limit is passed as positional arg: get_unread(db, limit)
        assert mock_get.call_args[0][1] == 20

    def test_success_custom_limit(self, client):
        """Should pass custom limit param to service."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_unread",
            return_value=[],
        ) as mock_get:
            resp = client.get(self.API_PATH, params={"limit": 5})
        assert resp.status_code == 200
        # limit is passed as positional arg: get_unread(db, limit)
        assert mock_get.call_args[0][1] == 5

    def test_empty(self, client):
        """Should return empty list when no unread notifications."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_unread",
            return_value=[],
        ):
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# 2. GET /notifications/unread-count — NO auth dep
# ===========================================================================
class TestUnreadCountEndpoint:
    API_PATH = "/notifications/unread-count"

    @pytest.fixture(autouse=True)
    def _no_auth(self):
        test_app.dependency_overrides.pop(get_current_user_id, None)
        yield

    def test_with_count(self, client):
        """Should return unread count."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_unread_count",
            return_value=5,
        ):
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert resp.json() == {"count": 5}

    def test_zero(self, client):
        """Should return 0 when no unread notifications."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_unread_count",
            return_value=0,
        ):
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert resp.json() == {"count": 0}


# ===========================================================================
# 3. POST /notifications/mark-read — NO auth dep
# ===========================================================================
class TestMarkReadEndpoint:
    API_PATH = "/notifications/mark-read"

    @pytest.fixture(autouse=True)
    def _no_auth(self):
        test_app.dependency_overrides.pop(get_current_user_id, None)
        yield

    def test_mark_by_id(self, client):
        """Should mark a specific notification as read by id."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.mark_read",
            return_value=True,
        ) as mock_read:
            resp = client.post(self.API_PATH, json={"id": 42})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["marked"] == 1
        mock_read.assert_called_once()
        args, kwargs = mock_read.call_args
        assert 42 in args or args[1] == 42

    def test_mark_all(self, client):
        """Should mark all notifications as read."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.mark_all_read",
            return_value=10,
        ) as mock_all:
            resp = client.post(self.API_PATH, json={"all": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["marked"] == 10

    def test_not_found(self, client):
        """Should return 404 when notification id not found."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.mark_read",
            return_value=False,
        ):
            resp = client.post(self.API_PATH, json={"id": 999})
        assert resp.status_code == 404

    def test_bad_request_no_id_no_all(self, client):
        """Should return 400 when neither id nor all provided."""
        resp = client.post(self.API_PATH, json={})
        assert resp.status_code == 400


# ===========================================================================
# 4. GET /notifications/history — NO auth dep
# ===========================================================================
class TestHistoryEndpoint:
    API_PATH = "/notifications/history"

    @pytest.fixture(autouse=True)
    def _no_auth(self):
        test_app.dependency_overrides.pop(get_current_user_id, None)
        yield

    def test_success_default_days(self, client):
        """Should return history with default days=7."""
        mock_result = [{"id": 1, "title": "Past notification"}]
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_history",
            return_value=mock_result,
        ) as mock_hist:
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        # days is passed as positional arg: get_history(db, days)
        assert mock_hist.call_args[0][1] == 7

    def test_success_custom_days(self, client):
        """Should pass custom days param to service."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_history",
            return_value=[],
        ) as mock_hist:
            resp = client.get(self.API_PATH, params={"days": 30})
        assert resp.status_code == 200
        # days is passed as positional arg: get_history(db, days)
        assert mock_hist.call_args[0][1] == 30

    def test_empty(self, client):
        """Should return empty list when no history."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.get_history",
            return_value=[],
        ):
            resp = client.get(self.API_PATH)
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# 5. POST /notifications/send — NO auth dep
# ===========================================================================
class TestSendEndpoint:
    API_PATH = "/notifications/send"

    @pytest.fixture(autouse=True)
    def _no_auth(self):
        test_app.dependency_overrides.pop(get_current_user_id, None)
        yield

    def test_success(self, client):
        """Should send notification and return result."""
        mock_result = {"success": True, "notification_id": 1}
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.send_notification",
            return_value=mock_result,
        ) as mock_send:
            resp = client.post(
                self.API_PATH,
                json={
                    "title": "Test Title",
                    "message": "Test Message",
                    "notification_type": "alert",
                    "priority": "high",
                    "channels": ["app", "telegram"],
                },
            )
        assert resp.status_code == 200
        assert resp.json() == mock_result
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert kwargs["title"] == "Test Title"
        assert kwargs["message"] == "Test Message"

    def test_minimal_payload(self, client):
        """Should work with only required fields."""
        with patch(
            "app.api.api_v1.endpoints.notifications.NotificationService.send_notification",
            return_value={"success": True},
        ):
            resp = client.post(
                self.API_PATH,
                json={"title": "Min", "message": "Minimal"},
            )
        assert resp.status_code == 200


# ===========================================================================
# 6. POST /notifications/register
# ===========================================================================
class TestRegisterFCMEndpoint:
    API_PATH = "/notifications/register"

    def test_success(self, client, headers):
        """Should register FCM token successfully."""
        with patch(
            "app.services.push_service.push_service"
        ) as mock_push:
            mock_push.register_token.return_value = True
            resp = client.post(
                self.API_PATH,
                json={"fcm_token": "fcm_token_abc123"},
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "registered" in data["message"].lower()

    def test_failure(self, client, headers):
        """Should return 400 when FCM registration fails."""
        with patch(
            "app.services.push_service.push_service"
        ) as mock_push:
            mock_push.register_token.return_value = False
            resp = client.post(
                self.API_PATH,
                json={"fcm_token": "invalid_token"},
                headers=headers,
            )
        assert resp.status_code == 400

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.post(
            self.API_PATH,
            json={"fcm_token": "test_token"},
            headers={},
        )
        assert resp.status_code == 401


# ===========================================================================
# 7. GET /notifications/briefing/today
# ===========================================================================
class TestBriefingTodayEndpoint:
    API_PATH = "/notifications/briefing/today"

    def test_with_briefing(self, client, headers, db_session):
        """Should return today's briefing content."""
        from app.models.daily_briefing import DailyBriefing

        from datetime import datetime

        briefing = DailyBriefing(
            id="brief-001",
            user_id="test_user",
            date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            content='{"summary": "Good day for training", "readiness": 85}',
        )
        db_session.add(briefing)
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"]["summary"] == "Good day for training"
        assert data["content"]["readiness"] == 85

    def test_no_briefing(self, client, headers):
        """Should return empty content when no briefing for today."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "No briefing available" in data.get("message", "")

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401
