"""
Tests de integración para endpoints de settings.py
Ruta: /api/v1/settings/
Todos los endpoints son sync (def, no async def) y usan get_current_user_id.
Sin try/except → las excepciones se propagan como 500 (FastAPI las maneja).
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.api.deps import get_db, get_current_user_id

# ---------------------------------------------------------------------------
# Fixtures de base de datos en memoria
# ---------------------------------------------------------------------------

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def _setup_db():
    """Crea tablas antes de cada test y las limpia después."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Proporciona una sesión de BD limpia."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_app():
    """App FastAPI con los routers de settings montados y DB override."""
    app = FastAPI()
    from app.api.api_v1.endpoints.settings import router

    app.include_router(router, prefix="/settings")

    def _override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_id] = lambda: "test_user"
    return app


@pytest.fixture
def client(test_app):
    """TestClient para la app de settings."""
    return TestClient(test_app)


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def _no_auth(test_app):
    """Remueve el override de get_current_user_id para tests 401."""
    test_app.dependency_overrides.pop(get_current_user_id, None)
    yield


# ---------------------------------------------------------------------------
# Helpers de base de datos
# ---------------------------------------------------------------------------

def _create_token(db_session, user_id="test_user", wger_api_key="test_key", hevy_username="test_hevy", garmin_email=None):
    """Crea un registro Token de prueba."""
    from app.models.token import Token
    token = Token(
        user_id=user_id,
        wger_api_key=wger_api_key,
        hevy_username=hevy_username,
        garmin_email=garmin_email,
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


def _create_user(db_session, user_id="test_user", name="Test User"):
    """Crea un registro User de prueba."""
    from app.models.user import User
    user = User(id=user_id, name=name)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ===========================================================================
# GET /settings/services
# ===========================================================================

class TestGetServices:
    API_PATH = "/settings/services"

    def test_with_credentials(self, client, db_session, headers):
        """Con Token existente → devuelve wger_api_key y hevy_username."""
        _create_token(db_session, wger_api_key="my_key", hevy_username="my_hevy")

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["wger_api_key"] == "my_key"
        assert data["hevy_username"] == "my_hevy"

    def test_without_credentials(self, client, headers):
        """Sin Token → devuelve strings vacíos."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["wger_api_key"] == ""
        assert data["hevy_username"] == ""

    # Sin try/except en el endpoint — no se testea propagación de error
    def test_unauthorized(self, client, _no_auth):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# ===========================================================================
# POST /settings/services
# ===========================================================================

class TestSaveServices:
    API_PATH = "/settings/services"

    def test_save_both(self, client, db_session, headers):
        """Envía wger_api_key y hevy_username → se guardan y retorna success."""
        resp = client.post(
            self.API_PATH,
            json={"wger_api_key": "new_key", "hevy_username": "new_hevy"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verificar en BD
        from app.models.token import Token
        db = TestSession()
        try:
            token = db.query(Token).filter(Token.user_id == "test_user").first()
            assert token is not None
            assert token.wger_api_key == "new_key"
            assert token.hevy_username == "new_hevy"
        finally:
            db.close()

    def test_save_partial(self, client, db_session, headers):
        """Envía solo wger_api_key → solo se actualiza ese campo."""
        _create_token(db_session, wger_api_key="old_key", hevy_username="existing")

        resp = client.post(
            self.API_PATH,
            json={"wger_api_key": "updated_key"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verificar en BD
        from app.models.token import Token
        db = TestSession()
        try:
            token = db.query(Token).filter(Token.user_id == "test_user").first()
            assert token.wger_api_key == "updated_key"
            assert token.hevy_username == "existing"  # no cambió
        finally:
            db.close()

    # Sin try/except en el endpoint — no se testea propagación de error
    def test_unauthorized(self, client, _no_auth):
        """Sin x-user-id → 401."""
        resp = client.post(
            self.API_PATH,
            json={"wger_api_key": "x"},
            headers={},
        )
        assert resp.status_code == 401


# ===========================================================================
# GET /settings/profile
# ===========================================================================

class TestGetProfile:
    API_PATH = "/settings/profile"

    def test_with_user(self, client, db_session, headers):
        """Usuario existe → devuelve perfil completo."""
        _create_user(db_session, name="Sergi")
        _create_token(db_session, garmin_email="sergi@test.com")

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True
        assert data["name"] == "Sergi"
        assert data["age"] == 47
        assert data["garmin_connected"] is True
        assert data["garmin_email"] == "sergi@test.com"

    def test_without_user(self, client, headers):
        """Usuario no existe → exists: False."""
        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is False

    def test_without_garmin(self, client, db_session, headers):
        """Usuario sin garmin → garmin_connected: False."""
        _create_user(db_session)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True
        assert data["garmin_connected"] is False
        assert data["garmin_email"] is None

    def test_default_name(self, client, db_session, headers):
        """Usuario sin nombre → default 'Sergi'."""
        _create_user(db_session, name=None)

        resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # El endpoint tiene: user.name if user and user.name else "Sergi"
        assert data["name"] == "Sergi"

    # Sin try/except en el endpoint — no se testea propagación de error
    def test_unauthorized(self, client, _no_auth):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# ===========================================================================
# POST /settings/profile
# ===========================================================================

class TestSaveProfile:
    API_PATH = "/settings/profile"

    def test_create_new_user(self, client, headers):
        """Usuario no existe → se crea con el nombre y retorna success."""
        resp = client.post(
            self.API_PATH,
            json="Nuevo Usuario",  # Body es un string directo
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["name"] == "Nuevo Usuario"

        # Verificar en BD
        from app.models.user import User
        db = TestSession()
        try:
            user = db.query(User).filter(User.id == "test_user").first()
            assert user is not None
            assert user.name == "Nuevo Usuario"
        finally:
            db.close()

    def test_update_existing_user(self, client, db_session, headers):
        """Usuario existe → se actualiza el nombre."""
        _create_user(db_session, name="Original")

        resp = client.post(
            self.API_PATH,
            json="Actualizado",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["name"] == "Actualizado"

        # Verificar en BD
        from app.models.user import User
        db = TestSession()
        try:
            user = db.query(User).filter(User.id == "test_user").first()
            assert user.name == "Actualizado"
        finally:
            db.close()

    # Sin try/except en el endpoint — no se testea propagación de error
    def test_unauthorized(self, client, _no_auth):
        """Sin x-user-id → 401."""
        resp = client.post(
            self.API_PATH,
            json="Test",
            headers={},
        )
        assert resp.status_code == 401
