"""
Tests para InterventionOutcomeService.
========================================

Verifica:
1. record_outcome() — cálculo de outcome_score y auto-deducción desde el estado
2. get_outcome_stats() — agregación, filtros, datos vacíos
3. get_best_channel() — aprendizaje de canal óptimo
4. get_best_timing() — aprendizaje de franja horaria óptima
5. record_batch_outcomes() — backfill de scores faltantes
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.atlas_intervention import AtlasIntervention
from app.services.intervention_outcome_service import InterventionOutcomeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def test_engine():
    """Engine SQLite en memoria NUEVO para cada test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _patch_session_local(test_engine):
    """Parchea SessionLocal en app.db.session (lazy import dentro del service)."""
    mock_session = sessionmaker(bind=test_engine)
    patcher = patch(
        "app.db.session.SessionLocal",
        mock_session,
    )
    patcher.start()
    yield
    patcher.stop()


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
# Tests: record_outcome — cálculo con factores explícitos
# ---------------------------------------------------------------------------


class TestRecordOutcome:
    """Cálculo y persistencia de outcome_score."""

    def test_record_outcome_with_explicit_factors(self, db_session):
        """Factores explícitos: accepted=True, 0.5h respuesta, acción posterior, adherence=0.8.
        accepted=1.0*0.4=0.4, time(0.5h<1h)=1.0*0.3=0.3, subsequent=1.0*0.2=0.2, adherence=0.8*0.1=0.08
        Total = 0.98
        """
        intervention = _create_intervention(db_session)
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
            outcome={
                "accepted": True,
                "responded_time_hours": 0.5,
                "subsequent_action": True,
                "adherence_impact": 0.8,
            },
        )
        assert score is not None
        assert score == pytest.approx(0.98, abs=0.001)

    def test_record_outcome_rejected_slow(self, db_session):
        """Rechazada, 12h respuesta: score bajo.
        accepted=0.0*0.4=0.0, time(12h)=0.2*0.3=0.06, subsequent=0.0*0.2=0.0, adherence=0.0*0.1=0.0
        Total = 0.06
        """
        intervention = _create_intervention(db_session)
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
            outcome={
                "accepted": False,
                "responded_time_hours": 12,
                "subsequent_action": False,
                "adherence_impact": 0.0,
            },
        )
        assert score is not None
        assert score == pytest.approx(0.06, abs=0.001)

    def test_record_outcome_auto_deduced_from_accepted(self, db_session):
        """Auto-deducción: response='accepted', executed_at presente, 2h respuesta."""
        now = datetime.now(timezone.utc)
        intervention = _create_intervention(
            db_session,
            status="completed",
            response="accepted",
            responded_at=now,
            executed_at=now,
            created_at=now - timedelta(hours=2),
        )
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
        )
        assert score is not None
        # accepted=True, 2h response→time=0.7, subsequent_action=True, adherence=default 0.5
        # 0.4 + 0.7*0.3 + 0.2 + 0.5*0.1 = 0.4 + 0.21 + 0.2 + 0.05 = 0.86
        assert score == pytest.approx(0.86, abs=0.001)

    def test_record_outcome_auto_deduced_from_rejected(self, db_session):
        """Auto-deducción: response='rejected', sin ejecución, 1h respuesta."""
        now = datetime.now(timezone.utc)
        intervention = _create_intervention(
            db_session,
            status="expired",
            response="rejected",
            responded_at=now,
            executed_at=None,
            created_at=now - timedelta(hours=1),
        )
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
        )
        assert score is not None
        # accepted=False, 1h→time=1.0, subsequent_action=False, adherence=0.5
        # 0.0 + 1.0*0.3 + 0.0 + 0.5*0.1 = 0.0 + 0.3 + 0.0 + 0.05 = 0.35
        assert score == pytest.approx(0.35, abs=0.001)

    def test_record_outcome_persisted_in_db(self, db_session):
        """El outcome_score se persiste correctamente en la BD."""
        intervention = _create_intervention(db_session)
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
            outcome={
                "accepted": True,
                "responded_time_hours": 1,
                "subsequent_action": True,
                "adherence_impact": 0.5,
            },
        )
        assert score is not None
        db_session.expire_all()
        reloaded = db_session.query(AtlasIntervention).filter_by(id=intervention.id).first()
        assert reloaded.outcome_score == pytest.approx(score, abs=0.001)

    def test_record_outcome_nonexistent_intervention(self, db_session):
        """Intervención inexistente → None sin error."""
        score = InterventionOutcomeService.record_outcome(
            intervention_id=99999,
            outcome={"accepted": True, "responded_time_hours": 1, "subsequent_action": True},
        )
        assert score is None

    def test_record_outcome_already_scored(self, db_session):
        """Intervención ya con score → se recalcula."""
        intervention = _create_intervention(db_session, outcome_score=0.5)
        score = InterventionOutcomeService.record_outcome(
            intervention_id=intervention.id,
            outcome={
                "accepted": True,
                "responded_time_hours": 0.1,
                "subsequent_action": True,
                "adherence_impact": 1.0,
            },
        )
        assert score is not None
        # 0.4 + 1.0*0.3 + 0.2 + 1.0*0.1 = 1.0
        assert score == pytest.approx(1.0, abs=0.001)


# ---------------------------------------------------------------------------
# Tests: get_outcome_stats
# ---------------------------------------------------------------------------


class TestGetOutcomeStats:
    """Estadísticas agregadas de outcomes."""

    def test_stats_with_multiple_interventions(self, db_session):
        """Múltiples intervenciones con varios tipos."""
        now = datetime.now(timezone.utc)

        # 3 adherence_nudge: 2 aceptadas, 1 rechazada
        for i in range(3):
            _create_intervention(
                db_session,
                user_id="user_stats",
                intervention_type="adherence_nudge",
                status="completed",
                response="accepted" if i < 2 else "rejected",
                outcome_score=0.8 if i < 2 else 0.2,
                responded_at=now,
                executed_at=now if i < 2 else None,
            )

        # 1 fatigue_alert: aceptada
        _create_intervention(
            db_session,
            user_id="user_stats",
            intervention_type="fatigue_alert",
            status="completed",
            response="accepted",
            outcome_score=0.9,
            responded_at=now,
            executed_at=now,
        )

        stats = InterventionOutcomeService.get_outcome_stats(user_id="user_stats")

        assert stats["total"] == 4
        assert len(stats["by_type"]) == 2
        assert stats["acceptance_rate"] == pytest.approx(0.75, abs=0.001)  # 3/4
        # avg_score: (0.8+0.8+0.2+0.9) / 4 = 2.7/4 = 0.675
        assert stats["avg_score"] == pytest.approx(0.675, abs=0.001)

        type_map = {t["type"]: t for t in stats["by_type"]}
        assert "adherence_nudge" in type_map
        assert type_map["adherence_nudge"]["count"] == 3
        assert type_map["adherence_nudge"]["avg_score"] == pytest.approx(0.6, abs=0.001)

        assert "fatigue_alert" in type_map
        assert type_map["fatigue_alert"]["count"] == 1
        assert type_map["fatigue_alert"]["avg_score"] == pytest.approx(0.9, abs=0.001)

    def test_stats_filter_by_type(self, db_session):
        """Filtro por intervention_type."""
        now = datetime.now(timezone.utc)
        _create_intervention(
            db_session, user_id="user_filter", intervention_type="check_in",
            status="completed", response="accepted", outcome_score=0.8, responded_at=now,
        )
        _create_intervention(
            db_session, user_id="user_filter", intervention_type="fatigue_alert",
            status="completed", response="rejected", outcome_score=0.2, responded_at=now,
        )
        stats = InterventionOutcomeService.get_outcome_stats(
            user_id="user_filter",
            intervention_type="check_in",
        )
        assert stats["total"] == 1
        assert stats["avg_score"] == pytest.approx(0.8, abs=0.001)
        assert len(stats["by_type"]) == 1

    def test_stats_empty_user(self, db_session):
        """Usuario sin intervenciones → estadísticas vacías."""
        stats = InterventionOutcomeService.get_outcome_stats(user_id="nonexistent_user")
        assert stats["total"] == 0
        assert stats["by_type"] == []
        assert stats["avg_score"] is None
        assert stats["acceptance_rate"] is None  # None, no 0.0
        assert stats["outcome_distribution"] == {}

    def test_stats_outcome_distribution(self, db_session):
        """Distribución de outcomes en buckets correctos."""
        now = datetime.now(timezone.utc)
        # bucket 0.8-1.0: score 0.9
        _create_intervention(db_session, user_id="user_dist", outcome_score=0.9,
                             response="accepted", status="completed", responded_at=now, executed_at=now)
        # bucket 0.4-0.6: score 0.5
        _create_intervention(db_session, user_id="user_dist", outcome_score=0.5,
                             response="accepted", status="completed", responded_at=now, executed_at=now)
        # bucket 0.0-0.2: score 0.2. BUT 0.2 < 0.4 so it's in 0.2-0.4, not 0.0-0.2
        # Wait, s < 0.2 → 0.0-0.2. So 0.2 goes to 0.2-0.4 bucket
        # Let me trace: if s < 0.2 → 0.0-0.2, elif s < 0.4 → 0.2-0.4. So 0.2 goes to 0.2-0.4
        _create_intervention(db_session, user_id="user_dist", outcome_score=0.2,
                             response="rejected", status="completed", responded_at=now)
        # bucket 0.0-0.2: score 0.1
        _create_intervention(db_session, user_id="user_dist", outcome_score=0.1,
                             response="rejected", status="completed", responded_at=now)
        # sin score (outcome_score=None): no cuenta en distribución
        _create_intervention(db_session, user_id="user_dist", outcome_score=None, status="pending")

        stats = InterventionOutcomeService.get_outcome_stats(user_id="user_dist")
        buckets = stats["outcome_distribution"]
        assert buckets["0.8-1.0"] == 1  # 0.9
        assert buckets["0.4-0.6"] == 1  # 0.5
        assert buckets["0.2-0.4"] == 1  # 0.2
        assert buckets["0.0-0.2"] == 1  # 0.1


# ---------------------------------------------------------------------------
# Tests: get_best_channel
# ---------------------------------------------------------------------------


class TestGetBestChannel:
    """Aprendizaje de canal óptimo."""

    def test_best_channel_with_data(self, db_session):
        """Canal con mejor avg_score gana.
        PROPOSAL → [app, system], AUTONOMOUS → [app], VALIDATION → [app, telegram, system]
        """
        now = datetime.now(timezone.utc)

        # AUTONOMOUS → solo [app]: scores altos
        for i in range(3):
            _create_intervention(
                db_session, user_id="user_ch", intervention_type="adherence_nudge",
                autonomy_level="AUTONOMOUS",
                status="completed", response="accepted",
                outcome_score=0.9,
                responded_at=now, executed_at=now,
            )
        # PROPOSAL → [app, system]: scores medios
        for i in range(2):
            _create_intervention(
                db_session, user_id="user_ch", intervention_type="adherence_nudge",
                autonomy_level="PROPOSAL",
                status="completed", response="accepted",
                outcome_score=0.6,
                responded_at=now, executed_at=now,
            )
        # VALIDATION → [app, telegram, system]: scores bajos
        _create_intervention(
            db_session, user_id="user_ch", intervention_type="adherence_nudge",
            autonomy_level="VALIDATION",
            status="completed", response="accepted",
            outcome_score=0.4,
            responded_at=now, executed_at=now,
        )

        result = InterventionOutcomeService.get_best_channel(
            user_id="user_ch",
            intervention_type="adherence_nudge",
        )
        assert result["best_channel"] == "app"
        assert result["sample_size"] > 0

    def test_best_channel_no_data(self, db_session):
        """Sin datos → defaults a 'app'."""
        result = InterventionOutcomeService.get_best_channel(
            user_id="user_no_data",
            intervention_type="adherence_nudge",
        )
        assert result["best_channel"] == "app"
        assert result["sample_size"] == 0
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Tests: get_best_timing
# ---------------------------------------------------------------------------


class TestGetBestTiming:
    """Aprendizaje de franja horaria óptima."""

    def test_best_timing_with_data(self, db_session):
        """Franja con mejor avg_score gana."""
        base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # morning (6-12): scores altos
        for i in range(3):
            _create_intervention(
                db_session, user_id="user_tm", intervention_type="adherence_nudge",
                status="completed", response="accepted",
                outcome_score=0.85,
                created_at=base.replace(hour=8),
                responded_at=base.replace(hour=8),
                executed_at=base.replace(hour=8),
            )
        # afternoon (12-18): scores medios
        for i in range(2):
            _create_intervention(
                db_session, user_id="user_tm", intervention_type="adherence_nudge",
                status="completed", response="accepted",
                outcome_score=0.55,
                created_at=base.replace(hour=15),
                responded_at=base.replace(hour=15),
                executed_at=base.replace(hour=15),
            )

        # Todas las intervenciones tienen outcome_score → sample_size incluye morning + afternoon
        result = InterventionOutcomeService.get_best_timing(
            user_id="user_tm",
            intervention_type="adherence_nudge",
        )
        assert result["best_timing"] == "morning"
        assert result["sample_size"] == 5  # 3 morning + 2 afternoon

    def test_best_timing_no_data(self, db_session):
        """Sin datos → defaults a 'morning'."""
        result = InterventionOutcomeService.get_best_timing(
            user_id="user_no_data",
            intervention_type="adherence_nudge",
        )
        assert result["best_timing"] == "morning"
        assert result["sample_size"] == 0
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Tests: record_batch_outcomes
# ---------------------------------------------------------------------------


class TestRecordBatchOutcomes:
    """Backfill de outcomes para intervenciones sin score."""

    def test_batch_fills_missing_scores(self, db_session):
        """Intervenciones sin score reciben score tras batch."""
        now = datetime.now(timezone.utc)

        # 2 intervenciones sin score, con respuesta (status debe ser accepted/rejected/executed/expired)
        for i in range(2):
            _create_intervention(
                db_session, user_id="user_batch", intervention_type="adherence_nudge",
                status="executed", response="accepted",
                responded_at=now, executed_at=now,
                created_at=now - timedelta(hours=1),
            )
        # 1 intervención ya con score (no debe recalcularse porque outcome_score ya no es NULL)
        _create_intervention(
            db_session, user_id="user_batch", intervention_type="adherence_nudge",
            status="executed", response="accepted",
            outcome_score=0.5,
            responded_at=now, executed_at=now,
            created_at=now - timedelta(hours=2),
        )
        # 1 intervención pendiente (status 'pending' no entra en batch)
        _create_intervention(
            db_session, user_id="user_batch", intervention_type="adherence_nudge",
            status="pending",
            created_at=now - timedelta(hours=3),
        )

        result = InterventionOutcomeService.record_batch_outcomes(
            user_id="user_batch",
            days=7,
        )
        assert result["processed"] == 2  # Solo las 2 con status accepted/rejected/executed/expired
        assert result["errors"] == 0
        assert result["updated"] == 2

    def test_batch_no_pending(self, db_session):
        """Sin intervenciones pendientes → 0 procesadas."""
        result = InterventionOutcomeService.record_batch_outcomes(
            user_id="user_empty",
            days=7,
        )
        assert result["processed"] == 0
        assert result["updated"] == 0
        assert result["errors"] == 0
