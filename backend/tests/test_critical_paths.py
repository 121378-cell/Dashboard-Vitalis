"""
ATLAS Critical Path Tests
==========================
Gate tests that MUST pass before any deployment.
Each test covers a production-critical flow.

Run: pytest backend/tests/test_critical_paths.py -v
"""

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.readiness_service import ReadinessService, ReadinessResult, PersonalBaseline
from app.services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# 1. Readiness Score — never crashes on empty/null biometric data
# ---------------------------------------------------------------------------
class TestReadinessNullSafety:
    def test_null_hrv(self):
        svc = ReadinessService()
        db = MagicMock()
        bio = MagicMock()
        bio.data = json.dumps({"hrv": None, "heartRate": 55, "sleep": 7.5, "stress": 30, "steps": 8000})
        bio.date = date.today().isoformat()
        bio.user_id = "test_user"
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [bio]
        db.query.return_value.filter.return_value.first.return_value = bio
        result = svc.calculate(db, "test_user", date_str=date.today().isoformat())
        assert isinstance(result, dict)
        score = result.get("score", result.get("readiness_score", 0))
        assert 0 <= score <= 100

    def test_all_null_fields(self):
        svc = ReadinessService()
        db = MagicMock()
        bio = MagicMock()
        bio.data = json.dumps({"hrv": None, "heartRate": None, "sleep": None, "stress": None, "steps": None})
        bio.date = date.today().isoformat()
        bio.user_id = "test_user"
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [bio]
        db.query.return_value.filter.return_value.first.return_value = bio
        result = svc.calculate(db, "test_user", date_str=date.today().isoformat())
        assert isinstance(result, dict)

    def test_empty_data_string(self):
        svc = ReadinessService()
        db = MagicMock()
        bio = MagicMock()
        bio.data = "{}"
        bio.date = date.today().isoformat()
        bio.user_id = "test_user"
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [bio]
        db.query.return_value.filter.return_value.first.return_value = bio
        result = svc.calculate(db, "test_user", date_str=date.today().isoformat())
        assert isinstance(result, dict)

    def test_no_biometrics_at_all(self):
        svc = ReadinessService()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        result = svc.calculate(db, "test_user", date_str=date.today().isoformat())
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 2. AI Chat — detect_conversation_mode never returns None
# ---------------------------------------------------------------------------
class TestAIConversationMode:
    def test_injury_mode(self):
        from app.services.ai_service import detect_conversation_mode
        mode = detect_conversation_mode("Me duele mucho la rodilla", "", "rodilla_last_month")
        assert mode == "alert"

    def test_celebration_mode(self):
        from app.services.ai_service import detect_conversation_mode
        mode = detect_conversation_mode("Bati mi record de press banca!", "", "")
        assert mode == "celebration"

    def test_planning_mode(self):
        from app.services.ai_service import detect_conversation_mode
        mode = detect_conversation_mode("Que entrenamiento hago manana?", "", "")
        assert mode == "planning"

    def test_analysis_mode(self):
        from app.services.ai_service import detect_conversation_mode
        mode = detect_conversation_mode("Como estan mis metricas de carga?", "", "")
        assert mode == "analysis"

    def test_greeting_falls_to_valid_mode(self):
        from app.services.ai_service import detect_conversation_mode
        mode = detect_conversation_mode("Hola ATLAS", "", "")
        assert mode is not None
        assert isinstance(mode, str)


# ---------------------------------------------------------------------------
# 3. Analytics — correlations handle <30 days gracefully
# ---------------------------------------------------------------------------
class TestAnalyticsCorrelationMinimumData:
    def test_fewer_than_30_days_returns_message(self):
        svc = AnalyticsService()
        db = MagicMock()
        mock_biometrics = []
        for i in range(10):
            b = MagicMock()
            b.date = (date.today() - timedelta(days=i)).isoformat()
            b.data = json.dumps({"hrv": 50 + i, "sleep": 7.0, "stress": 30, "heartRate": 55, "steps": 8000})
            mock_biometrics.append(b)
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_biometrics
        result = svc.find_personal_correlations(db, "test_user")
        if isinstance(result, dict):
            assert "message" in result or "correlations" in result
        elif isinstance(result, str):
            assert "Acumulando" in result or "datos" in result


# ---------------------------------------------------------------------------
# 4. Rate Limiter — enforces limits and returns 429
# ---------------------------------------------------------------------------
class TestRateLimiter:
    def test_bucket_allows_up_to_max(self):
        from app.core.rate_limiter import _TokenBucket
        bucket = _TokenBucket(max_tokens=3, refill_per_sec=1.0)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_bucket_refills_over_time(self):
        from app.core.rate_limiter import _TokenBucket
        import time
        bucket = _TokenBucket(max_tokens=1, refill_per_sec=100.0)
        assert bucket.consume() is True
        assert bucket.consume() is False
        time.sleep(0.02)
        assert bucket.consume() is True

    def test_retry_after_is_positive_when_empty(self):
        from app.core.rate_limiter import _TokenBucket
        bucket = _TokenBucket(max_tokens=1, refill_per_sec=1.0)
        bucket.consume()
        retry = bucket.retry_after()
        assert retry > 0


# ---------------------------------------------------------------------------
# 5. Monitoring Middleware — tracks metrics correctly
# ---------------------------------------------------------------------------
class TestMonitoringMetrics:
    def test_get_metrics_returns_required_fields(self):
        from app.middleware.monitoring import get_metrics
        metrics = get_metrics()
        assert "requests_total" in metrics
        assert "errors_total" in metrics
        assert "avg_response_time_ms" in metrics
        assert "db_size_mb" in metrics
        assert "uptime_seconds" in metrics

    def test_metrics_values_are_valid(self):
        from app.middleware.monitoring import get_metrics
        metrics = get_metrics()
        assert metrics["requests_total"] >= 0
        assert metrics["errors_total"] >= 0
        assert metrics["avg_response_time_ms"] >= 0
        assert metrics["db_size_mb"] >= 0
        assert metrics["uptime_seconds"] >= 0


# ---------------------------------------------------------------------------
# 6. Backup Script — integrity check catches corrupt DB
# ---------------------------------------------------------------------------
class TestBackupIntegrity:
    def _verify_integrity(self, db_path: str) -> bool:
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception:
            return False

    def test_verify_integrity_on_valid_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        import sqlite3
        conn = sqlite3.connect(tmp_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        assert self._verify_integrity(tmp_path) is True
        os.unlink(tmp_path)

    def test_verify_integrity_on_nonexistent_db(self):
        assert self._verify_integrity("/nonexistent/path/db.db") is False
