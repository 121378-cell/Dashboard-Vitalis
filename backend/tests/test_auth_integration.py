"""
Tests de integración: endpoints de autenticación (auth.py).
==========================================================

Cubre los 6 endpoints del router auth:
- POST /garmin/login (login a Garmin)
- GET /status (estado de autenticación Garmin)
- POST /disconnect (desconectar Garmin)
- POST /jwt/login (login con email/password)
- POST /jwt/register (registro de nuevo usuario)
- POST /jwt/refresh (refrescar token JWT)

Usa FastAPI TestClient con dependencias override + StaticPool para
compartir la base SQLite en memoria entre fixtures y endpoints.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.user import User
from app.models.token import Token
from app.api.api_v1.api import api_router
from app.core.config import settings


# ---------------------------------------------------------------------------
# App de test (sin lifespan de producción)
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS Auth API")
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
def db_session(test_engine):
    """Session directa para crear datos de prueba."""
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


@pytest.fixture
def headers():
    """Headers estándar de autenticación por x-user-id."""
    return {"x-user-id": "test_user"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(db_session, user_id="test_user", name="Test User", email="test@test.com"):
    """Crea un User de prueba."""
    user = User(id=user_id, name=name, email=email)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_token(db_session, user_id="test_user", garmin_email="test@garmin.com"):
    """Crea un Token de prueba con garmin_email."""
    token = Token(user_id=user_id, garmin_email=garmin_email)
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


def _create_valid_refresh_token(user_id="test_user"):
    """Genera un refresh token JWT válido para pruebas."""
    from jose import jwt as jose_jwt
    expire = datetime.utcnow() + timedelta(days=30)
    token = jose_jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


# ===========================================================================
# POST /garmin/login
# ===========================================================================


class TestGarminLoginEndpoint:
    """POST /auth/garmin/login"""

    API_PATH = "/api/v1/auth/garmin/login"

    def test_login_success(self, client, db_session):
        """Credenciales válidas → 200 + success + User/Token creados."""
        with patch("app.api.api_v1.endpoints.auth.get_garmin_client") as mock_garmin:
            mock_garmin.return_value = (Mock(), None)

            resp = client.post(
                self.API_PATH,
                json={"email": "test@garmin.com", "password": "secret123"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        # Verificar que se creó User y Token
        user = db_session.query(User).filter(User.id == "default_user").first()
        assert user is not None
        assert user.name == "Sergi"

        token = db_session.query(Token).filter(Token.user_id == "default_user").first()
        assert token is not None
        assert token.garmin_email == "test@garmin.com"

    def test_login_custom_user_id(self, client, db_session):
        """user_id personalizado → 200 + User con ese id."""
        with patch("app.api.api_v1.endpoints.auth.get_garmin_client") as mock_garmin:
            mock_garmin.return_value = (Mock(), None)

            resp = client.post(
                self.API_PATH,
                json={
                    "email": "test@garmin.com",
                    "password": "secret123",
                    "user_id": "custom_user",
                },
            )
        assert resp.status_code == 200

        user = db_session.query(User).filter(User.id == "custom_user").first()
        assert user is not None

    def test_login_existing_user_updates_token(self, client, db_session):
        """Usuario ya existente con Token → actualiza credenciales."""
        _create_user(db_session, user_id="default_user")
        _create_token(db_session, user_id="default_user", garmin_email="old@garmin.com")

        with patch("app.api.api_v1.endpoints.auth.get_garmin_client") as mock_garmin:
            mock_garmin.return_value = (Mock(), None)

            resp = client.post(
                self.API_PATH,
                json={"email": "new@garmin.com", "password": "new_pass"},
            )
        assert resp.status_code == 200

        token = db_session.query(Token).filter(Token.user_id == "default_user").first()
        assert token is not None
        # Credenciales actualizadas
        assert token.garmin_email == "new@garmin.com"

    def test_login_invalid_credentials(self, client):
        """Credenciales inválidas → 500 (el except Exception general atrapa el HTTPException)."""
        with patch("app.api.api_v1.endpoints.auth.get_garmin_client") as mock_garmin:
            mock_garmin.return_value = (None, None)

            resp = client.post(
                self.API_PATH,
                json={"email": "bad@garmin.com", "password": "wrong"},
            )
        assert resp.status_code == 500

    def test_login_server_error(self, client):
        """Error interno (get_garmin_client lanza excepción) → 500."""
        with patch("app.api.api_v1.endpoints.auth.get_garmin_client") as mock_garmin:
            mock_garmin.side_effect = Exception("Connection timeout")

            resp = client.post(
                self.API_PATH,
                json={"email": "test@garmin.com", "password": "secret123"},
            )
        assert resp.status_code == 500


# ===========================================================================
# GET /status
# ===========================================================================


class TestAuthStatusEndpoint:
    """GET /auth/status"""

    API_PATH = "/api/v1/auth/status"

    def test_status_authenticated(self, client, db_session, headers):
        """Token con garmin_email → authenticated=True."""
        _create_token(db_session, user_id="test_user", garmin_email="test@garmin.com")

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True

    def test_status_not_authenticated_no_token(self, client, headers):
        """Sin Token → authenticated=False."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is False

    def test_status_not_authenticated_empty_email(self, client, db_session, headers):
        """Token sin garmin_email → authenticated=False."""
        token = Token(user_id="test_user")
        db_session.add(token)
        db_session.commit()

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is False

    def test_status_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /disconnect
# ===========================================================================


class TestDisconnectEndpoint:
    """POST /auth/disconnect"""

    API_PATH = "/api/v1/auth/disconnect"

    def test_disconnect_with_token(self, client, db_session, headers):
        """Token existente → 200 + Token eliminado."""
        _create_token(db_session, user_id="test_user", garmin_email="test@garmin.com")

        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verificar que el Token fue eliminado
        token = db_session.query(Token).filter(Token.user_id == "test_user").first()
        assert token is None

    def test_disconnect_no_token(self, client, headers):
        """Sin Token → 200 (no hay nada que eliminar)."""
        resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_disconnect_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /jwt/login
# ===========================================================================


class TestJwtLoginEndpoint:
    """POST /auth/jwt/login"""

    API_PATH = "/api/v1/auth/jwt/login"

    def test_login_success_dev_mode(self, client, db_session):
        """Login sin JWT_ADMIN_PASSWORD (dev mode) → 200 + tokens."""
        _create_user(db_session, email="test@test.com")

        resp = client.post(
            self.API_PATH,
            json={"email": "test@test.com", "password": "any_password"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@test.com"

    def test_login_by_user_id_fallback(self, client, db_session):
        """Login con user_id como fallback → 200 + tokens."""
        _create_user(db_session, user_id="test_user", email="test_user")

        resp = client.post(
            self.API_PATH,
            json={"email": "test_user", "password": "any"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_with_admin_password(self, client, db_session):
        """Login con JWT_ADMIN_PASSWORD correcto → 200 + tokens."""
        _create_user(db_session, email="test@test.com")

        with patch.object(settings, "JWT_ADMIN_PASSWORD", "admin_pass"):
            resp = client.post(
                self.API_PATH,
                json={"email": "test@test.com", "password": "admin_pass"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client, db_session):
        """Login con JWT_ADMIN_PASSWORD y contraseña incorrecta → 401."""
        _create_user(db_session, email="test@test.com")

        with patch.object(settings, "JWT_ADMIN_PASSWORD", "real_pass"):
            resp = client.post(
                self.API_PATH,
                json={"email": "test@test.com", "password": "wrong_pass"},
            )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_user_not_found(self, client):
        """Email no registrado → 401."""
        resp = client.post(
            self.API_PATH,
            json={"email": "nonexistent@test.com", "password": "pass"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()


# ===========================================================================
# POST /jwt/register
# ===========================================================================


class TestJwtRegisterEndpoint:
    """POST /auth/jwt/register"""

    API_PATH = "/api/v1/auth/jwt/register"

    def test_register_success(self, client, db_session):
        """Registro de nuevo usuario → 200 + tokens + user creado."""
        resp = client.post(
            self.API_PATH,
            json={"email": "new@test.com", "password": "pass123", "name": "New User"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "new@test.com"
        assert data["user"]["name"] == "New User"

        # Verificar en DB
        user = db_session.query(User).filter(User.email == "new@test.com").first()
        assert user is not None
        assert user.name == "New User"

    def test_register_duplicate_email(self, client, db_session):
        """Email ya registrado → 400."""
        _create_user(db_session, email="existing@test.com")

        resp = client.post(
            self.API_PATH,
            json={
                "email": "existing@test.com",
                "password": "pass123",
                "name": "Duplicate",
            },
        )
        assert resp.status_code == 400
        assert "registrado" in resp.json()["detail"].lower()

    def test_register_with_admin_password(self, client, db_session):
        """Registro con JWT_ADMIN_PASSWORD correcto → 200."""
        with patch.object(settings, "JWT_ADMIN_PASSWORD", "admin_pass"):
            resp = client.post(
                self.API_PATH,
                json={
                    "email": "new@test.com",
                    "password": "admin_pass",
                    "name": "New User",
                },
            )
        assert resp.status_code == 200
        assert "access_token" in resp.json()


# ===========================================================================
# POST /jwt/refresh
# ===========================================================================


class TestJwtRefreshEndpoint:
    """POST /auth/jwt/refresh"""

    API_PATH = "/api/v1/auth/jwt/refresh"

    def test_refresh_success(self, client, db_session):
        """Refresh token válido → 200 + nuevo access_token."""
        _create_user(db_session, user_id="test_user")
        refresh_token = _create_valid_refresh_token("test_user")

        # Body(...) sin embed=True espera el valor raw como JSON válido
        resp = client.post(
            self.API_PATH,
            content=json.dumps(refresh_token),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Decodificar y verificar que el nuevo token contiene el user_id correcto
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            data["access_token"],
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "test_user"
        # No debe tener type=refresh
        assert payload.get("type") != "refresh"

    def test_refresh_invalid_token(self, client):
        """Token malformado → 401."""
        resp = client.post(
            self.API_PATH,
            content=json.dumps("invalid_token_string"),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        assert "invalido" in resp.json()["detail"].lower()

    def test_refresh_wrong_type(self, client, db_session):
        """Token de acceso (no refresh) → 401."""
        _create_user(db_session, user_id="test_user")

        # Crear un access token en lugar de refresh token
        from jose import jwt as jose_jwt
        expire = datetime.utcnow() + timedelta(minutes=30)
        access_token = jose_jwt.encode(
            {"sub": "test_user", "exp": expire},  # Sin type="refresh"
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        resp = client.post(
            self.API_PATH,
            content=json.dumps(access_token),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        assert "invalido" in resp.json()["detail"].lower()

    def test_refresh_user_not_found(self, client):
        """Refresh token de usuario que no existe en DB → 401."""
        refresh_token = _create_valid_refresh_token("nonexistent_user")

        resp = client.post(
            self.API_PATH,
            content=json.dumps(refresh_token),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        assert "no encontrado" in resp.json()["detail"].lower()
