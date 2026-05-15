"""
Tests de integración para endpoints de memory.py
==================================================
Cubre los 3 endpoints del router memory (prefix: /memory en /api/v1):
- GET    /memory/summary        → Resumen de memorias
- POST   /memory/entry          → Agregar entrada de memoria
- DELETE /memory/{memory_id}    → Eliminar entrada de memoria
"""

import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.base import Base
from app.models.memory import AtlasMemory
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.services.memory_service import MemoryService

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Test App ──────────────────────────────────────────────────────────────
test_app = FastAPI(title="Test ATLAS Memory API")
test_app.include_router(api_router, prefix=settings.API_V1_STR)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def test_engine():
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
    """Override get_db dependency for in-memory test DB."""
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

    yield

    test_app.dependency_overrides = {}


@pytest.fixture
def client(test_engine):
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def db_session(test_engine):
    """Direct DB session for seeding test data."""
    TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
    db = TestSessionLocal()
    yield db
    db.close()


# ── Sample Data ────────────────────────────────────────────────────────────

SAMPLE_SUMMARY = {
    "memories": [
        {
            "id": 1,
            "type": "achievement",
            "content": "Nuevo record en Press Banca: 100kg x 8 reps",
            "date": "2025-01-15",
            "importance": 8,
            "source": "workout",
        },
        {
            "id": 2,
            "type": "injury",
            "content": "Molestia leve en hombro derecho durante press militar",
            "date": "2025-01-10",
            "importance": 7,
            "source": "user",
        },
    ],
    "count": 2,
    "period_days": 90,
}


def _make_memory_response(
    mem_id=1,
    mem_type="achievement",
    content="Test memory",
    date="2025-01-15",
    importance=5,
    source="user",
):
    """Create a mock AtlasMemory-like object for add_memory return."""
    _id = mem_id
    _type = mem_type
    _content = content
    _date = date
    _imp = importance
    _src = source

    class FakeMemory:
        pass

    FakeMemory.id = _id
    FakeMemory.type = _type
    FakeMemory.content = _content
    FakeMemory.date = _date
    FakeMemory.importance = _imp
    FakeMemory.source = _src
    return FakeMemory()


# ══════════════════════════════════════════════════════════════════════════
# GET /memory/summary
# ══════════════════════════════════════════════════════════════════════════


class TestMemorySummaryEndpoint:
    API_PATH = f"{settings.API_V1_STR}/memory/summary"

    def test_success_default_params(self, client, headers):
        with patch.object(
            MemoryService, "get_memory_summary", return_value=SAMPLE_SUMMARY
        ) as mock_summary:
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["memories"]) == 2
        assert data["period_days"] == 90
        assert data["memories"][0]["type"] == "achievement"
        # Verify default days=90, types=None
        mock_summary.assert_called_once()
        args, kwargs = mock_summary.call_args
        assert kwargs.get("days") == 90
        assert kwargs.get("types") is None

    def test_success_with_type_filter(self, client, headers):
        with patch.object(
            MemoryService, "get_memory_summary", return_value=SAMPLE_SUMMARY
        ) as mock_summary:
            resp = client.get(
                f"{self.API_PATH}?days=30&types=injury,achievement",
                headers=headers,
            )

        assert resp.status_code == 200
        args, kwargs = mock_summary.call_args
        assert kwargs.get("days") == 30
        assert kwargs.get("types") == ["injury", "achievement"]

    def test_success_empty(self, client, headers):
        empty = {"memories": [], "count": 0, "period_days": 90}
        with patch.object(
            MemoryService, "get_memory_summary", return_value=empty
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["memories"] == []

    def test_error(self, client, headers):
        with patch.object(
            MemoryService, "get_memory_summary",
            side_effect=Exception("DB connection error"),
        ):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client):
        resp = client.get(self.API_PATH)
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# POST /memory/entry
# ══════════════════════════════════════════════════════════════════════════


class TestCreateMemoryEntryEndpoint:
    API_PATH = f"{settings.API_V1_STR}/memory/entry"

    def test_success(self, client, headers):
        fake_memory = _make_memory_response(
            mem_id=10, mem_type="achievement",
            content="Completé 5x5 en sentadilla",
            importance=7,
        )
        with patch.object(
            MemoryService, "add_memory", return_value=fake_memory
        ) as mock_add:
            resp = client.post(
                self.API_PATH,
                json={
                    "type": "achievement",
                    "content": "Completé 5x5 en sentadilla",
                    "importance": 7,
                    "source": "user",
                },
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 10
        assert data["type"] == "achievement"
        assert data["content"] == "Completé 5x5 en sentadilla"
        assert data["importance"] == 7
        assert data["source"] == "user"

        mock_add.assert_called_once()

    def test_success_with_date(self, client, headers):
        fake_memory = _make_memory_response(date="2025-02-01")
        with patch.object(MemoryService, "add_memory", return_value=fake_memory):
            resp = client.post(
                self.API_PATH,
                json={
                    "type": "milestone",
                    "content": "Primer entreno del mes",
                    "date": "2025-02-01",
                    "importance": 3,
                },
                headers=headers,
            )

        assert resp.status_code == 200
        assert resp.json()["date"] == "2025-02-01"

    def test_invalid_type(self, client, headers):
        resp = client.post(
            self.API_PATH,
            json={
                "type": "invalid_type",
                "content": "Some memory",
                "importance": 5,
            },
            headers=headers,
        )

        assert resp.status_code == 400
        assert "Invalid memory type" in resp.json()["detail"]

    def test_error(self, client, headers):
        with patch.object(
            MemoryService, "add_memory",
            side_effect=Exception("Failed to save memory"),
        ):
            with pytest.raises(Exception):
                client.post(
                    self.API_PATH,
                    json={
                        "type": "achievement",
                        "content": "Test",
                        "importance": 5,
                    },
                    headers=headers,
                )

    def test_unauthorized(self, client):
        resp = client.post(
            self.API_PATH,
            json={"type": "achievement", "content": "Test", "importance": 5},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# DELETE /memory/{memory_id}
# ══════════════════════════════════════════════════════════════════════════


class TestDeleteMemoryEntryEndpoint:
    API_PATH = f"{settings.API_V1_STR}/memory"

    def test_success(self, client, headers):
        with patch.object(
            MemoryService, "delete_memory", return_value=True
        ) as mock_delete:
            resp = client.delete(f"{self.API_PATH}/5", headers=headers)

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_delete.assert_called_once()

    def test_not_found(self, client, headers):
        with patch.object(
            MemoryService, "delete_memory", return_value=False
        ):
            resp = client.delete(f"{self.API_PATH}/999", headers=headers)

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_error(self, client, headers):
        with patch.object(
            MemoryService, "delete_memory",
            side_effect=Exception("DB error"),
        ):
            with pytest.raises(Exception):
                client.delete(f"{self.API_PATH}/1", headers=headers)

    def test_unauthorized(self, client):
        resp = client.delete(f"{self.API_PATH}/1")
        assert resp.status_code == 401
