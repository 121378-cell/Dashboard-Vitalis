"""
Tests de integración: endpoints de AI (ai.py).
=================================================

Cubre los 5 endpoints del router ai:
- POST /chat (coaching chat con detección de workout/plan)
- GET /welcome-message (mensaje de bienvenida)
- GET /context-preview (debug: contexto sin LLM)
- POST /generate-plan (generar plan de 4 semanas)
- GET /daily-briefing (resumen matutino)

Usa FastAPI TestClient con dependencias override + StaticPool para
compartir la base SQLite en memoria entre fixtures y endpoints.
"""

import json
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.session import TrainingSession
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.ai_service import AIService


# ---------------------------------------------------------------------------
# App de test (sin lifespan de producción)
# ---------------------------------------------------------------------------

test_app = FastAPI(title="Test ATLAS AI API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SAMPLE_COACH_CONTEXT = {
    "prompt": "Eres ATLAS, el asistente personal de fitness.",
    "athlete_name": "Sergi",
    "athlete_age": 30,
    "readiness_score": 85,
    "bio_summary": "Atleta de nivel intermedio, objetivo hipertrofia.",
    "injury_summary": "clear",
    "context_meta": {
        "name": "Sergi",
        "age": 30,
        "readiness": 85,
        "bio": "Atleta de nivel intermedio",
        "injuries": "clear",
    },
}

SAMPLE_CHAT_RESPONSE = {
    "content": "¡Hola Sergi! Hoy tienes un entrenamiento de fuerza de pecho y tríceps. ¿Te parece bien?",
    "provider": "groq",
}

SAMPLE_WELCOME_MESSAGE = {
    "message": "¡Bienvenido, Sergi! Hoy es un gran día para entrenar.",
}

SAMPLE_GENERATED_PLAN = {
    "weeks": [
        {
            "week": 1,
            "days": [
                {"day": "Lunes", "focus": "Pecho", "exercises": ["Press banca 4x8"]},
                {"day": "Miércoles", "focus": "Espalda", "exercises": ["Dominadas 4x8"]},
            ],
        }
    ],
}

SAMPLE_BRIEFING = (
    "**Estado de Recuperación:** 85/100 - Bien recuperado.\n"
    "**Análisis de Carga (ACWR):** 1.1 - Carga equilibrada.\n"
    "**Recomendación del día:** Entrena pecho y tríceps con intensidad moderada-alta."
)


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
def headers():
    """Headers estándar de autenticación por x-user-id."""
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine):
    """Session directa para crear datos de prueba."""
    session = sessionmaker(bind=test_engine)()
    yield session
    session.close()


# ===========================================================================
# POST /chat
# ===========================================================================


class TestChatEndpoint:
    """POST /ai/chat"""

    API_PATH = "/api/v1/ai/chat"

    def test_workout_existing_session(self, client, db_session, headers):
        """Keyword workout + sesión existente → returns session plan."""
        # Crear sesión existente para hoy
        today_str = date.today().isoformat()
        session = TrainingSession(
            user_id="test_user",
            date=today_str,
            status="planned",
            generated_by="atlas",
            plan_json=json.dumps({"exercises": ["Press banca 4x8"]}),
        )
        db_session.add(session)
        db_session.commit()

        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "¿Qué entreno hoy?"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "session_plan"
        assert data["provider"] == "atlas_session"
        assert data["session_id"] == session.id
        assert "Press banca" in data["content"]

    def test_workout_new_session(self, client, headers):
        """Keyword workout + sin sesión → genera nueva + persiste."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch("app.services.session_service.SessionService.generate_session_plan") as mock_generate,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT
            mock_generate.return_value = {"exercises": ["Sentadillas 4x10"]}

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "Quiero entrenar hoy"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "session_plan"
        assert data["provider"] == "atlas_session"
        assert "Sentadillas" in data["content"]
        mock_generate.assert_called_once()

    def test_workout_new_session_after_completed(self, client, db_session, headers):
        """Keyword workout + sesión completada hoy → genera nueva."""
        today_str = date.today().isoformat()
        session = TrainingSession(
            user_id="test_user",
            date=today_str,
            status="completed",
            generated_by="atlas",
            plan_json=json.dumps({"exercises": ["Press 4x8"]}),
        )
        db_session.add(session)
        db_session.commit()

        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch("app.services.session_service.SessionService.generate_session_plan") as mock_gen,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT
            mock_gen.return_value = {"exercises": ["Remo 4x10"]}

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "Vamos a entrenar"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "session_plan"
        assert "Remo" in data["content"]
        mock_gen.assert_called_once()

    def test_plan_trigger(self, client, headers):
        """Keyword plan semanal → genera weekly plan."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch("app.services.training_plan_service.TrainingPlanService.generate_weekly_plan") as mock_plan,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT
            mock_plan.return_value = {
                "weeks": [{"week": 1, "focus": "Hipertrofia"}],
                "plan_id": "plan_123",
            }

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "Generar plan semanal"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "weekly_plan"
        assert data["provider"] == "atlas_plan"
        assert data["plan_id"] == "plan_123"
        mock_plan.assert_called_once()

    def test_plan_trigger_conflict(self, client, headers):
        """Keyword plan semanal + plan ya existe → returns error."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch("app.services.training_plan_service.TrainingPlanService.generate_weekly_plan") as mock_plan,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT
            mock_plan.return_value = {
                "error": "Ya tienes un plan activo para esta semana",
                "plan_id": "existing_plan",
            }

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "Crear plan de entrenamiento"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "plan_exists"
        assert "Ya tienes" in data["content"]

    def test_standard_chat(self, client, headers):
        """Mensaje normal → AIService.chat con contexto de coach."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch.object(AIService, "chat", return_value=SAMPLE_CHAT_RESPONSE) as mock_chat,
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "¿Cómo voy esta semana?"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == SAMPLE_CHAT_RESPONSE["content"]
        assert data["provider"] == SAMPLE_CHAT_RESPONSE["provider"]
        assert data["mode"] in ["analysis", "planning", "motivation", "monitoring", "general"]
        mock_chat.assert_called_once()

    def test_chat_ai_error(self, client, headers):
        """AIService.chat lanza excepción → respuesta de error."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch.object(AIService, "chat", side_effect=Exception("API timeout")),
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT

            resp = client.post(
                self.API_PATH,
                json={
                    "messages": [{"role": "user", "content": "?Como estoy?"}]
                },
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "servicio" in data["content"].lower()
        assert "ia" in data["content"].lower()
        assert data["provider"] == "error"
        assert "error" in data

    def test_chat_empty_messages(self, client, headers):
        """Lista de mensajes vacía → fallback a chat estándar."""
        with (
            patch("app.api.api_v1.endpoints.ai.build_coach_context") as mock_context,
            patch.object(AIService, "chat", return_value=SAMPLE_CHAT_RESPONSE),
        ):
            mock_context.return_value = SAMPLE_COACH_CONTEXT

            resp = client.post(
                self.API_PATH,
                json={"messages": []},
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == SAMPLE_CHAT_RESPONSE["provider"]

    def test_chat_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(
            self.API_PATH,
            json={"messages": [{"role": "user", "content": "hola"}]},
        )
        assert resp.status_code == 401


# ===========================================================================
# GET /welcome-message
# ===========================================================================


class TestWelcomeMessageEndpoint:
    """GET /ai/welcome-message"""

    API_PATH = "/api/v1/ai/welcome-message"

    def test_welcome_success(self, client, headers):
        """GET welcome-message → 200 + mensaje."""
        with patch(
            "app.api.api_v1.endpoints.ai.generate_welcome_message",
            return_value=SAMPLE_WELCOME_MESSAGE,
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "Bienvenido" in data["message"]

    def test_welcome_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /context-preview
# ===========================================================================


class TestContextPreviewEndpoint:
    """GET /ai/context-preview"""

    API_PATH = "/api/v1/ai/context-preview"

    def test_context_success(self, client, headers):
        """GET context-preview → 200 + todos los campos de contexto."""
        with patch(
            "app.api.api_v1.endpoints.ai.build_coach_context",
            return_value=SAMPLE_COACH_CONTEXT,
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_prompt"] == SAMPLE_COACH_CONTEXT["prompt"]
        assert data["athlete_name"] == SAMPLE_COACH_CONTEXT["athlete_name"]
        assert data["athlete_age"] == SAMPLE_COACH_CONTEXT["athlete_age"]
        assert data["readiness_score"] == SAMPLE_COACH_CONTEXT["readiness_score"]
        assert data["bio_summary"] == SAMPLE_COACH_CONTEXT["bio_summary"]
        assert data["injury_summary"] == SAMPLE_COACH_CONTEXT["injury_summary"]
        assert data["context_meta"] == SAMPLE_COACH_CONTEXT["context_meta"]

    def test_context_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# POST /generate-plan
# ===========================================================================


class TestGeneratePlanEndpoint:
    """POST /ai/generate-plan"""

    API_PATH = "/api/v1/ai/generate-plan"

    def test_generate_success(self, client, headers):
        """POST generate-plan → 200 + plan JSON."""
        with patch(
            "app.api.api_v1.endpoints.ai.ai_service.generate_response",
            return_value=json.dumps(SAMPLE_GENERATED_PLAN),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert data["plan"]["weeks"][0]["week"] == 1

    def test_generate_custom_params(self, client, headers):
        """POST generate-plan con objective y level personalizados."""
        with patch(
            "app.api.api_v1.endpoints.ai.ai_service.generate_response",
            return_value=json.dumps(SAMPLE_GENERATED_PLAN),
        ) as mock_gen:
            resp = client.post(
                self.API_PATH,
                params={"objective": "fuerza", "level": "avanzado"},
                headers=headers,
            )
        assert resp.status_code == 200
        mock_gen.assert_called_once()
        # Verificar que el prompt incluye los parámetros personalizados
        call_args = mock_gen.call_args[0]
        prompt = call_args[0]
        assert "fuerza" in prompt.lower()
        assert "avanzado" in prompt.lower()

    def test_generate_error(self, client, headers):
        """ai_service.generate_response lanza excepción → 500."""
        with patch(
            "app.api.api_v1.endpoints.ai.ai_service.generate_response",
            side_effect=Exception("LLM error"),
        ):
            resp = client.post(self.API_PATH, headers=headers)
        assert resp.status_code == 500
        assert "LLM error" in resp.json()["detail"]

    def test_generate_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.post(self.API_PATH)
        assert resp.status_code == 401


# ===========================================================================
# GET /daily-briefing
# ===========================================================================


class TestDailyBriefingEndpoint:
    """GET /ai/daily-briefing"""

    API_PATH = "/api/v1/ai/daily-briefing"

    def test_briefing_success(self, client, headers):
        """GET daily-briefing → 200 + briefing."""
        with (
            patch(
                "app.api.api_v1.endpoints.ai.build_coach_context",
                return_value=SAMPLE_COACH_CONTEXT,
            ),
            patch(
                "app.api.api_v1.endpoints.ai.ai_service.generate_response",
                return_value=SAMPLE_BRIEFING,
            ),
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "briefing" in data
        assert "Recuperación" in data["briefing"]
        assert "ACWR" in data["briefing"]

    def test_briefing_error(self, client, headers):
        """ai_service.generate_response lanza excepción → 500."""
        with (
            patch(
                "app.api.api_v1.endpoints.ai.build_coach_context",
                return_value=SAMPLE_COACH_CONTEXT,
            ),
            patch(
                "app.api.api_v1.endpoints.ai.ai_service.generate_response",
                side_effect=Exception("Briefing error"),
            ),
        ):
            resp = client.get(self.API_PATH, headers=headers)
        assert resp.status_code == 500

    def test_briefing_unauthorized(self, client):
        """Sin x-user-id → 401."""
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401
