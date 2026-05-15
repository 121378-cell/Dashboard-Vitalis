"""
Tests de integracion para endpoints de Strava (/api/v1/strava/...)
Cubre los 6 endpoints: auth, callback, status, disconnect, activities, sync
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, class_mapper
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api.deps import get_db, get_current_user_id
from app.models.token import Token
from datetime import datetime, timedelta
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Dynamically add strava_ columns to Token model so the ORM can load them
# These columns exist in production via raw migration but are missing from
# the model definition. We add them here to make the test DB schema match.
# ---------------------------------------------------------------------------
_strava_columns = [
    ("strava_access_token", sa.String),
    ("strava_refresh_token", sa.String),
    ("strava_expires_at", sa.DateTime),
    ("strava_athlete_id", sa.String),
    ("strava_connected", sa.String),
]
for col_name, col_type in _strava_columns:
    col = sa.Column(col_name, col_type)
    Token.__table__.append_column(col)
    mapper = class_mapper(Token)
    mapper.add_property(col_name, col)

# --- Test App Setup ---
test_app = FastAPI()
from app.api.api_v1.endpoints.strava import router
test_app.include_router(router, prefix="/strava", tags=["strava"])


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


# ---------------------------------------------------------------------------
# Helper: seed a Token with strava fields in the test DB
# ---------------------------------------------------------------------------
def _seed_strava_token(db_session, **kwargs):
    """Creates or updates a Token with strava fields for testing."""
    user_id = kwargs.pop("user_id", "test_user")
    token = db_session.query(Token).filter(Token.user_id == user_id).first()
    if not token:
        token = Token(user_id=user_id)
        db_session.add(token)
    for key, value in kwargs.items():
        setattr(token, key, value)
    db_session.commit()
    # Refresh to ensure ORM caches the strava_ columns
    db_session.refresh(token)
    return token


@pytest.fixture
def db_session(test_engine, _override_db):
    """Provides a db_session for seeding data inside tests."""
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    yield db
    db.close()


# ===========================================================================
# 1. GET /strava/auth  — no auth, no DB
# ===========================================================================
class TestStravaAuthEndpoint:
    API_PATH = "/strava/auth"

    def test_redirects_to_strava(self, client):
        """Should return a redirect to Strava OAuth URL."""
        with patch("app.api.api_v1.endpoints.strava.settings") as mock_settings:
            mock_settings.STRAVA_CLIENT_ID = "test_client_id"
            mock_settings.STRAVA_REDIRECT_URI = "http://localhost/callback"
            resp = client.get(self.API_PATH, follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "strava.com" in resp.headers.get("location", "").lower()

    def test_includes_redirect_uri(self, client):
        """Should include the configured redirect_uri in the auth URL."""
        with patch("app.api.api_v1.endpoints.strava.settings") as mock_settings:
            mock_settings.STRAVA_CLIENT_ID = "test_client_id"
            mock_settings.STRAVA_REDIRECT_URI = "http://localhost/callback"
            resp = client.get(self.API_PATH, follow_redirects=False)
        location = resp.headers.get("location", "")
        assert "redirect_uri=http" in location.lower().replace("%3D", "=")


# ===========================================================================
# 2. GET /strava/callback — no auth (uses hardcoded user)
# ===========================================================================
class TestStravaCallbackEndpoint:
    API_PATH = "/strava/callback"

    def test_success_redirects_with_tokens(self, client):
        """Should exchange code for tokens and redirect to frontend."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_at": 9999999999,
            "athlete": {"id": 12345},
        }

        with patch("app.api.api_v1.endpoints.strava.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "http://localhost:5173"
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_instance.post.return_value = mock_response
                resp = client.get(
                    self.API_PATH,
                    params={"code": "test_auth_code", "scope": "read"},
                    follow_redirects=False,
                )
        assert resp.status_code in (302, 307)
        assert "strava_connected=true" in resp.headers.get("location", "")

    def test_error_redirects_with_error(self, client):
        """Should redirect to frontend with error when httpx call fails."""
        with patch("app.api.api_v1.endpoints.strava.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "http://localhost:5173"
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                # Make the httpx call raise an exception (not return 400)
                # The endpoint catches generic Exception and redirects to error
                mock_instance.post.side_effect = Exception("Connection error")
                resp = client.get(
                    self.API_PATH,
                    params={"code": "bad_code"},
                    follow_redirects=False,
                )
        assert resp.status_code in (302, 307)
        assert "strava_error=true" in resp.headers.get("location", "")


# ===========================================================================
# 3. GET /strava/status
# ===========================================================================
class TestStravaStatusEndpoint:
    API_PATH = "/strava/status"

    def test_connected(self, client, headers, db_session):
        """Should report connected=true with valid token."""
        _seed_strava_token(
            db_session,
            strava_access_token="valid_token",
            strava_refresh_token="refresh_123",
            strava_expires_at=datetime.utcnow() + timedelta(days=30),
            strava_athlete_id="12345",
            strava_connected="true",
        )
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["expired"] is False
        assert data["athlete_id"] == "12345"

    def test_connected_expired(self, client, headers, db_session):
        """Should report expired=true when token is past expiry."""
        _seed_strava_token(
            db_session,
            strava_access_token="expired_token",
            strava_refresh_token="refresh_123",
            strava_expires_at=datetime.utcnow() - timedelta(days=1),
            strava_athlete_id="12345",
            strava_connected="true",
        )
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["expired"] is True

    def test_not_connected(self, client, headers):
        """Should report connected=false when no token exists."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["expired"] is False
        assert data["athlete_id"] is None

    def test_connected_disabled(self, client, headers, db_session):
        """Should report connected=false when strava_connected != 'true'."""
        _seed_strava_token(
            db_session,
            strava_access_token="some_token",
            strava_connected="false",
        )
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# ===========================================================================
# 4. POST /strava/disconnect
# ===========================================================================
class TestStravaDisconnectEndpoint:
    API_PATH = "/strava/disconnect"

    def test_disconnect_with_token(self, client, headers, db_session):
        """Should clear strava fields and return success."""
        _seed_strava_token(
            db_session,
            strava_access_token="token_123",
            strava_refresh_token="refresh_123",
            strava_expires_at=datetime.utcnow() + timedelta(days=30),
            strava_athlete_id="12345",
            strava_connected="true",
        )
        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        # Verify DB was updated using a fresh session
        TestSession = sessionmaker(bind=db_session.bind)
        with TestSession() as fresh_db:
            token = fresh_db.query(Token).filter(Token.user_id == "test_user").first()
            assert token.strava_access_token is None
            assert token.strava_connected == "false"

    def test_disconnect_without_token(self, client, headers):
        """Should return success even when no token exists."""
        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.post(self.API_PATH, headers={})
        assert resp.status_code == 401


# ===========================================================================
# 5. GET /strava/activities
# ===========================================================================
class TestStravaActivitiesEndpoint:
    API_PATH = "/strava/activities"

    def test_success(self, client, headers, db_session):
        """Should fetch activities from Strava API and return them."""
        _seed_strava_token(
            db_session,
            strava_access_token="valid_token",
            strava_refresh_token="refresh_123",
            strava_connected="true",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Morning Run", "type": "Run"},
            {"id": 2, "name": "Evening Ride", "type": "Ride"},
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_token_refresh_and_retry(self, client, headers, db_session):
        """Should refresh token on 401 and retry the request."""
        _seed_strava_token(
            db_session,
            strava_access_token="old_token",
            strava_refresh_token="refresh_123",
            strava_connected="true",
        )

        mock_401 = MagicMock()
        mock_401.status_code = 401

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = [{"id": 42, "name": "Retried Run"}]

        mock_refresh = MagicMock()
        mock_refresh.status_code = 200
        mock_refresh.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_at": 9999999999,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.side_effect = [mock_401, mock_200]
            mock_instance.post.return_value = mock_refresh
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_token_refresh_fail_returns_401(self, client, headers, db_session):
        """Should return 401 when token refresh fails."""
        _seed_strava_token(
            db_session,
            strava_access_token="old_token",
            strava_refresh_token="refresh_123",
            strava_connected="true",
        )

        mock_401 = MagicMock()
        mock_401.status_code = 401

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_401
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 401

    def test_no_token(self, client, headers):
        """Should return 401 when Strava is not connected."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 401
        assert "no conectado" in resp.json().get("detail", "").lower()

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# ===========================================================================
# 6. POST /strava/sync
# ===========================================================================
class TestStravaSyncEndpoint:
    API_PATH = "/strava/sync"

    def test_success(self, client, headers, db_session):
        """Should sync activities and return sync results."""
        mock_result = {
            "success": True,
            "synced_count": 5,
            "skipped_count": 2,
            "total_received": 7,
            "errors": [],
        }
        with patch(
            "app.api.api_v1.endpoints.strava.strava_service.sync_recent_activities",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = mock_result
            resp = client.post(self.API_PATH, params={"days": 30}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["synced_count"] == 5

    def test_error(self, client, headers):
        """Should return 400 when sync reports failure."""
        mock_result = {"success": False, "error": "Strava no conectado"}
        with patch(
            "app.api.api_v1.endpoints.strava.strava_service.sync_recent_activities",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = mock_result
            resp = client.post(self.API_PATH, params={"days": 7}, headers=headers)
        assert resp.status_code == 400
        assert "no conectado" in resp.json().get("detail", "").lower()

    def test_unauthorized(self, client):
        """Should return 401 without x-user-id header."""
        test_app.dependency_overrides.pop(get_current_user_id, None)
        resp = client.post(self.API_PATH, headers={})
        assert resp.status_code == 401
