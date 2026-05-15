"""
Test de integración: emit → process_pending → evaluate_triggers.

Verifica el flujo completo del bus de eventos:
1. emit() crea un evento en la BD
2. process_pending() lo recoge, lo marca procesado y llama a evaluate_triggers()
3. InterventionService.evaluate_triggers() evalúa si debe crear una intervención
4. Si procede, crea un AtlasIntervention persistido
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Asegurar que el directorio backend está en sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.atlas_event import AtlasEvent
from app.models.atlas_intervention import AtlasIntervention
from app.services.event_bus_service import emit, process_pending, get_stats
from app.core.autonomy_policy import InterventionType


@pytest.fixture(scope="function")
def test_engine():
    """
    Crea un engine SQLite en memoria NUEVO para cada test.
    Garantiza aislamiento total entre tests (no hay contaminación).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _patch_session_local(test_engine):
    """Parchea SessionLocal en todos los módulos que lo usan."""
    mock_session = sessionmaker(bind=test_engine)
    patchers = [
        patch("app.services.event_bus_service.SessionLocal", mock_session),
        patch("app.services.intervention_service.SessionLocal", mock_session),
    ]
    for p in patchers:
        p.start()
    yield
    for p in reversed(patchers):
        p.stop()


@pytest.fixture
def mock_athlete_state():
    """Mockea _get_athlete_state para evitar dependencia con servicios externos."""
    patcher = patch(
        "app.services.intervention_service.InterventionService._get_athlete_state",
        return_value={
            "energy": "stable",
            "adherence": "compliant",
            "momentum": "neutral",
            "risk": "low",
            "motivation": "steady",
            "training_phase": "maintenance",
            "readiness_score": 75,
            "injury_risk": "low",
        },
    )
    yield patcher.start()
    patcher.stop()


# ─── Tests ─────────────────────────────────────────────────────────────────


class TestEventBusIntegration:
    """Flujo completo: emit → process_pending → evaluate_triggers."""

    def test_emit_and_process_triggers_intervention(self, mock_athlete_state):
        """
        Emitir un evento con tipo mapeado a intervención.
        process_pending() debe crear un AtlasIntervention.
        """
        # 1. Emitir evento que dispara intervención
        event = emit(
            user_id="test_user",
            event_type="fatigue_detected",
            payload={"fatigue_level": 8, "source": "readiness_analysis"},
            source="test_integration",
        )
        assert event is not None
        assert event.id is not None
        assert event.processed is False

        # 2. Procesar eventos pendientes
        results = process_pending(dry_run=False)

        # 3. Verificar que se generó una intervención
        assert len(results) == 1, f"Esperaba 1 intervención, obtuvo {len(results)}"
        result = results[0]
        assert result["event_id"] == event.id
        assert result["event_type"] == "fatigue_detected"
        assert result["user_id"] == "test_user"
        assert result["intervention"] is not None

        intervention = result["intervention"]
        assert intervention.user_id == "test_user"
        assert intervention.source_event_id == event.id
        assert intervention.status == "pending"
        # fatigue_detected → [RECOVERY_ACTIVATE, INTENSITY_ADJUST]
        # El servicio almacena intervention_type.name.lower()
        assert intervention.intervention_type in (
            InterventionType.RECOVERY_ACTIVATE.name.lower(),
            InterventionType.INTENSITY_ADJUST.name.lower(),
        )

    def test_emit_and_process_no_intervention_for_unmapped_event(self, mock_athlete_state):
        """
        Eventos sin mapeo en EVENT_TO_INTERVENTION no generan intervención.
        """
        event = emit(
            user_id="test_user",
            event_type="unknown_event_type",
            payload={"test": True},
            source="test_integration",
        )
        assert event is not None

        results = process_pending(dry_run=False)
        assert len(results) == 0, (
            f"Evento sin mapeo no debería generar intervenciones, "
            f"obtuvo {len(results)}"
        )

    def test_dry_run_does_not_persist(self, mock_athlete_state):
        """
        dry_run=True procesa pero no marca eventos como procesados
        ni persiste intervenciones.
        """
        event = emit(
            user_id="test_user",
            event_type="fatigue_detected",
            payload={"fatigue_level": 8},
            source="test_integration",
        )
        assert event is not None

        # dry_run: simula pero no persiste
        results = process_pending(dry_run=True)

        # Debe devolver resultados simulados
        assert len(results) == 1
        assert results[0]["intervention"] is not None

        # Verificar que NO se persiste: evento sigue sin procesar
        from app.services.event_bus_service import count_pending

        pending_count = count_pending(user_id="test_user")
        assert pending_count >= 1, (
            "dry_run no marca eventos como procesados, "
            f"pending={pending_count}"
        )

    def test_multiple_events_processed_in_batch(self, mock_athlete_state):
        """
        Múltiples eventos se procesan correctamente en un solo lote.
        """
        # Emitir 3 eventos
        types_and_payloads = [
            ("adherence_drop", {"drop": 0.3}),
            ("fatigue_detected", {"fatigue_level": 7}),
            ("milestone_reached", {"milestone": "10k_run"}),
        ]

        for etype, payload in types_and_payloads:
            emit(
                user_id="test_user",
                event_type=etype,
                payload=payload,
                source="test_batch",
            )

        # Procesar todos
        results = process_pending(dry_run=False)

        # adherence_drop → [ADHERENCE_NUDGE, CHECK_IN_REQUEST]
        # fatigue_detected → [RECOVERY_ACTIVATE, INTENSITY_ADJUST]
        # milestone_reached → [OPPORTUNITY]
        # Los 3 deberían mapear a al menos una intervención
        event_types_generated = {r["event_type"] for r in results}
        assert len(results) == 3, (
            f"Esperaba 3 intervenciones, obtuvo {len(results)}. "
            f"Tipos generados: {event_types_generated}"
        )

        assert event_types_generated == {
            "adherence_drop",
            "fatigue_detected",
            "milestone_reached",
        }

        # Cada resultado debe tener su intervención
        for r in results:
            assert r["intervention"] is not None, (
                f"Evento {r['event_type']} no generó intervención"
            )
            assert r["intervention"].user_id == "test_user"
            assert r["intervention"].status == "pending"

    def test_stats_after_processing(self, mock_athlete_state):
        """
        get_stats() refleja el estado después de procesar eventos.
        """
        # Emitir y procesar
        emit(user_id="test_user", event_type="fatigue_detected", source="test_stats")
        process_pending(dry_run=False)

        # Verificar stats
        stats = get_stats(user_id="test_user")
        assert stats["user_id"] == "test_user"
        assert stats["total"] >= 1
        assert stats["pending"] == 0  # Todos procesados
        assert "fatigue_detected" in stats["by_type"]
