"""
TESTS UNITARIOS - Analytics Service (Prompt 15)
================================================
Pruebas para:
- _pearson_r: calculo de correlacion de Pearson
- _ewma: media exponencialmente ponderada
- _linear_slope: pendiente de regresion lineal
- _clamp: limitacion de rango
- find_personal_correlations: correlaciones personales
- forecast_readiness: prediccion de readiness
- detect_plateau: deteccion de estancamiento
- find_optimal_volume: volumen optimo
- get_monthly_insights: insights mensuales

Ejecutar:
cd backend && python -m pytest tests/unit/test_analytics_service.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, timedelta


# =============================================================================
# TESTS - Helper functions
# =============================================================================

class TestPearsonR:
    def test_perfect_positive(self):
        from app.services.analytics_service import _pearson_r
        r = _pearson_r([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert r is not None
        assert abs(r - 1.0) < 0.01

    def test_perfect_negative(self):
        from app.services.analytics_service import _pearson_r
        r = _pearson_r([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert r is not None
        assert abs(r + 1.0) < 0.01

    def test_no_correlation(self):
        from app.services.analytics_service import _pearson_r
        r = _pearson_r([1, 2, 3, 4, 5], [5, 1, 4, 2, 3])
        assert r is not None
        assert abs(r) < 0.5

    def test_too_few_points(self):
        from app.services.analytics_service import _pearson_r
        assert _pearson_r([1, 2], [3, 4]) is None

    def test_zero_variance(self):
        from app.services.analytics_service import _pearson_r
        r = _pearson_r([1, 1, 1, 1, 1], [2, 3, 4, 5, 6])
        assert r is None

    def test_mismatched_lengths(self):
        from app.services.analytics_service import _pearson_r
        assert _pearson_r([1, 2, 3], [4, 5]) is None


class TestEWMA:
    def test_basic(self):
        from app.services.analytics_service import _ewma
        result = _ewma([10, 20, 30], alpha=0.3)
        assert len(result) == 3
        assert result[0] == 10

    def test_empty(self):
        from app.services.analytics_service import _ewma
        assert _ewma([]) == []

    def test_single_value(self):
        from app.services.analytics_service import _ewma
        assert _ewma([42]) == [42]

    def test_alpha_1(self):
        from app.services.analytics_service import _ewma
        result = _ewma([10, 20, 30], alpha=1.0)
        assert result == [10, 20, 30]


class TestLinearSlope:
    def test_positive_trend(self):
        from app.services.analytics_service import _linear_slope
        slope = _linear_slope([10, 20, 30, 40, 50])
        assert slope > 0

    def test_negative_trend(self):
        from app.services.analytics_service import _linear_slope
        slope = _linear_slope([50, 40, 30, 20, 10])
        assert slope < 0

    def test_flat(self):
        from app.services.analytics_service import _linear_slope
        slope = _linear_slope([30, 30, 30, 30, 30])
        assert abs(slope) < 0.01

    def test_single_value(self):
        from app.services.analytics_service import _linear_slope
        assert _linear_slope([42]) == 0.0

    def test_two_values(self):
        from app.services.analytics_service import _linear_slope
        slope = _linear_slope([0, 10])
        assert slope == pytest.approx(10.0)


class TestClamp:
    def test_within_range(self):
        from app.services.analytics_service import _clamp
        assert _clamp(50, 0, 100) == 50

    def test_below_min(self):
        from app.services.analytics_service import _clamp
        assert _clamp(-10, 0, 100) == 0

    def test_above_max(self):
        from app.services.analytics_service import _clamp
        assert _clamp(150, 0, 100) == 100


# =============================================================================
# TESTS - Correlations
# =============================================================================

class TestFindPersonalCorrelations:
    def test_insufficient_data(self):
        from app.services.analytics_service import AnalyticsService
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = AnalyticsService.find_personal_correlations(mock_db, "user1", days=10)
        assert result["status"] == "accumulating"
        assert "Acumulando datos" in result["message"]

    @patch("app.services.analytics_service.AnalyticsService._fetch_daily_data")
    def test_sufficient_data_returns_correlations(self, mock_fetch):
        from app.services.analytics_service import AnalyticsService

        days = 35
        data = []
        for i in range(days):
            d = date.today() - timedelta(days=i)
            data.append({
                "date": d.isoformat(),
                "hrv": 50 + i * 0.5,
                "hr": 60,
                "sleep": 7 + (i % 3),
                "stress": 30,
                "steps": 8000,
                "workouts": [{"duration_min": 60, "avg_hr": 130, "rpe": 6, "hour": 18}] if i % 3 == 0 else [],
                "weekday": d.weekday(),
                "is_rest": i % 3 != 0,
            })
        mock_fetch.return_value = data

        mock_db = Mock()
        result = AnalyticsService.find_personal_correlations(mock_db, "user1", days=90)

        assert result["status"] == "ok"
        assert "correlations" in result
        assert "insights" in result

    @patch("app.services.analytics_service.AnalyticsService._fetch_daily_data")
    def test_sleep_to_hrv_correlation(self, mock_fetch):
        from app.services.analytics_service import AnalyticsService

        days = 35
        data = []
        for i in range(days):
            d = date.today() - timedelta(days=days - i)
            sleep = 6.0 if i % 2 == 0 else 8.0
            hrv = 40 + sleep * 5
            data.append({
                "date": d.isoformat(),
                "hrv": hrv,
                "hr": 60,
                "sleep": sleep,
                "stress": 30,
                "steps": 8000,
                "workouts": [],
                "weekday": d.weekday(),
                "is_rest": True,
            })
        mock_fetch.return_value = data

        mock_db = Mock()
        result = AnalyticsService.find_personal_correlations(mock_db, "user1", days=90)
        assert result["status"] == "ok"
        s2h = result["correlations"].get("sleep_to_hrv", {})
        assert s2h.get("r") is not None


# =============================================================================
# TESTS - Forecast
# =============================================================================

class TestForecastReadiness:
    @patch("app.services.readiness_service.ReadinessService.calculate")
    def test_insufficient_data(self, mock_readiness):
        from app.services.analytics_service import AnalyticsService

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = AnalyticsService.forecast_readiness(mock_db, "user1")
        assert result["status"] == "accumulating"
        assert result["forecasts"] == []

    @patch("app.services.readiness_service.ReadinessService.calculate")
    def test_forecast_structure(self, mock_readiness):
        from app.services.analytics_service import AnalyticsService

        mock_readiness.return_value = {"score": 70}

        bios = []
        for i in range(14):
            b = Mock()
            b.date = (date.today() - timedelta(days=i)).isoformat()
            b.data = '{"hrv": 50, "sleep": 7, "heartRate": 60, "stress": 30}'
            bios.append(b)

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = bios

        result = AnalyticsService.forecast_readiness(mock_db, "user1", days_ahead=3)

        if result["status"] == "ok":
            assert len(result["forecasts"]) == 3
            for f in result["forecasts"]:
                assert "date" in f
                assert "predicted_score" in f
                assert "confidence" in f
                assert 0 <= f["predicted_score"] <= 100
                assert 0 <= f["confidence"] <= 1


# =============================================================================
# TESTS - Plateau Detection
# =============================================================================

class TestDetectPlateau:
    def test_no_prs(self):
        from app.services.analytics_service import AnalyticsService
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = AnalyticsService.detect_plateau(mock_db, "user1")
        assert result["status"] == "no_data"
        assert result["plateaus"] == []

    def test_plateau_detected(self):
        from app.services.analytics_service import AnalyticsService

        prs = []
        for i in range(6):
            pr = Mock()
            pr.exercise_name = "Bench Press"
            pr.weight = 45  # Stuck at 45kg
            pr.reps = 8
            pr.date = (date.today() - timedelta(weeks=i)).isoformat()
            prs.append(pr)

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = prs
        result = AnalyticsService.detect_plateau(mock_db, "user1")
        assert result["status"] == "ok"
        assert len(result["plateaus"]) >= 1
        assert result["plateaus"][0]["exercise"] == "Bench Press"

    def test_progressing_exercise(self):
        from app.services.analytics_service import AnalyticsService

        prs = []
        for i in range(6):
            pr = Mock()
            pr.exercise_name = "Squat"
            pr.weight = 60 + i * 5
            pr.reps = 5
            pr.date = (date.today() - timedelta(weeks=i)).isoformat()
            prs.append(pr)

        mock_db = Mock()
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value.all.return_value = prs
        mock_db.query.return_value = query_mock

        result = AnalyticsService.detect_plateau(mock_db, "user1", exercise_name="Squat")
        assert result["status"] == "progressing"

    def test_specific_exercise_filter(self):
        from app.services.analytics_service import AnalyticsService

        prs = []
        for i in range(6):
            pr = Mock()
            pr.exercise_name = "Bench Press"
            pr.weight = 45
            pr.reps = 8
            pr.date = (date.today() - timedelta(weeks=i)).isoformat()
            prs.append(pr)

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = prs

        chain = mock_db.query.return_value.filter
        chain.return_value.filter.return_value.order_by.return_value.all.return_value = prs

        result = AnalyticsService.detect_plateau(mock_db, "user1", exercise_name="Bench Press")
        assert result["plateaus"][0]["exercise"] == "Bench Press"


# =============================================================================
# TESTS - Optimal Volume
# =============================================================================

class TestFindOptimalVolume:
    def test_insufficient_weeks(self):
        from app.services.analytics_service import AnalyticsService
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = AnalyticsService.find_optimal_volume(mock_db, "user1")
        assert result["status"] == "accumulating"


# =============================================================================
# TESTS - Monthly Insights
# =============================================================================

class TestMonthlyInsights:
    @patch("app.services.analytics_service.AnalyticsService.find_optimal_volume")
    @patch("app.services.analytics_service.AnalyticsService.detect_plateau")
    @patch("app.services.analytics_service.AnalyticsService.find_personal_correlations")
    def test_caching(self, mock_corr, mock_plateau, mock_vol):
        from app.services.analytics_service import AnalyticsService, _insight_cache

        _insight_cache.clear()

        mock_corr.return_value = {"status": "accumulating", "insights": [], "correlations": {}}
        mock_plateau.return_value = {"status": "no_data", "plateaus": []}
        mock_vol.return_value = {"status": "accumulating"}

        mock_db = Mock()
        r1 = AnalyticsService.get_monthly_insights(mock_db, "user1")
        r2 = AnalyticsService.get_monthly_insights(mock_db, "user1")

        assert r1 == r2
        assert mock_corr.call_count == 1

    @patch("app.services.analytics_service.AnalyticsService.find_optimal_volume")
    @patch("app.services.analytics_service.AnalyticsService.detect_plateau")
    @patch("app.services.analytics_service.AnalyticsService.find_personal_correlations")
    def test_max_5_insights(self, mock_corr, mock_plateau, mock_vol):
        from app.services.analytics_service import AnalyticsService, _insight_cache

        _insight_cache.clear()

        insights = [{"id": f"i{i}", "importance": "media", "text": f"Insight {i}"} for i in range(8)]
        mock_corr.return_value = {"status": "ok", "insights": insights, "correlations": {}}
        mock_plateau.return_value = {"status": "ok", "plateaus": []}
        mock_vol.return_value = {"status": "ok", "optimal_volume_min": 200}

        mock_db = Mock()
        result = AnalyticsService.get_monthly_insights(mock_db, "user1")
        assert len(result["insights"]) <= 5


# =============================================================================
# EJECUCION DIRECTA
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
