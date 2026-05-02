"""
TESTS UNITARIOS - AI SERVICE v2.0 (ATLAS Persona)
=================================================
Pruebas para:
- detect_conversation_mode: clasificacion de modo de conversacion
- build_atlas_system_prompt: generacion de prompt dinamico
- ReadinessService._score_training_load: scoring de carga de entrenamiento

Ejecutar:
cd backend && python -m pytest tests/unit/test_ai_service.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, timedelta


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def mock_workouts_normal():
    workouts = []
    for i in range(5):
        w = Mock()
        w.duration = 3600  # 60 min
        w.date = date.today() - timedelta(days=i)
        workouts.append(w)
    return workouts


@pytest.fixture
def mock_workouts_none():
    return []


@pytest.fixture
def mock_workouts_extreme():
    workouts = []
    for i in range(7):
        w = Mock()
        w.duration = 14400  # 240 min
        w.date = date.today() - timedelta(days=i)
        workouts.append(w)
    return workouts


# =============================================================================
# TESTS - detect_conversation_mode
# =============================================================================

class TestDetectConversationMode:
    """Tests para detect_conversation_mode."""

    def test_alert_on_pain_with_injury(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "tengo dolor en el hombro",
            "",
            "active_injury"
        )
        assert result == "alert"

    def test_alert_on_lesion_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "mi lesion me molesta",
            "",
            "active_injury"
        )
        assert result == "alert"

    def test_alert_on_duele_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "me duele la espalda",
            "",
            "active_injury"
        )
        assert result == "alert"

    def test_alert_on_molestia_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "tengo molestia en la rodilla",
            "",
            "active_injury"
        )
        assert result == "alert"

    def test_alert_on_low_readiness(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "como estoy hoy",
            "",
            "",
            readiness_score=25
        )
        assert result == "alert"

    def test_alert_on_critical_biometrics(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "que tal",
            "🔴 AVISO: HRV bajo",
            ""
        )
        assert result == "alert"

    def test_alert_on_critico_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "que tal",
            "estado crítico de fatiga",
            ""
        )
        assert result == "alert"

    def test_celebration_on_pr(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "conseguí un PR en banca!",
            "",
            ""
        )
        assert result == "celebration"

    def test_celebration_on_record(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "batí mi record de prensa",
            "",
            ""
        )
        assert result == "celebration"

    def test_celebration_on_mejor_marca(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "mejor marca personal hoy",
            "",
            ""
        )
        assert result == "celebration"

    def test_planning_on_entreno(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "que entreno hoy?",
            "",
            ""
        )
        assert result == "planning"

    def test_planning_on_workout(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "quiero hacer un workout",
            "",
            ""
        )
        assert result == "planning"

    def test_planning_on_gym(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "vamos al gym",
            "",
            ""
        )
        assert result == "planning"

    def test_planning_on_rutina(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "dame mi rutina de hoy",
            "",
            ""
        )
        assert result == "planning"

    def test_analysis_on_datos(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "muestrame mis datos",
            "",
            ""
        )
        assert result == "analysis"

    def test_analysis_on_readiness_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "como esta mi readiness?",
            "",
            ""
        )
        assert result == "analysis"

    def test_analysis_on_hrv_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "que tal mi hrv?",
            "",
            ""
        )
        assert result == "analysis"

    def test_motivation_on_cansado(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "estoy muy cansado",
            "",
            ""
        )
        assert result == "motivation"

    def test_motivation_on_no_puedo(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "no puedo más",
            "",
            ""
        )
        assert result == "motivation"

    def test_fallback_analysis_on_generic_message(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "hola",
            "",
            ""
        )
        assert result == "analysis"

    def test_fallback_planning_on_high_readiness(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "hola",
            "",
            "",
            readiness_score=85
        )
        assert result == "planning"

    def test_fallback_analysis_on_moderate_readiness(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "hola",
            "",
            "",
            readiness_score=50
        )
        assert result == "analysis"

    def test_alert_priority_over_celebration(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "conseguí un PR pero tengo dolor",
            "",
            "active_injury"
        )
        assert result == "alert"

    def test_no_injury_no_alert_on_pain(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "tengo dolor",
            "",
            ""
        )
        assert result != "alert"

    def test_celebration_on_logre(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "logré subir 50kg en banca",
            "",
            ""
        )
        assert result == "celebration"

    def test_planning_on_plan_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "necesito un plan para esta semana",
            "",
            ""
        )
        assert result == "planning"

    def test_analysis_on_tendencia(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "cual es mi tendencia?",
            "",
            ""
        )
        assert result == "analysis"

    def test_analysis_on_acwr_keyword(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "como va mi acwr?",
            "",
            ""
        )
        assert result == "analysis"

    def test_motivation_on_animo(self):
        from app.services.ai_service import detect_conversation_mode
        result = detect_conversation_mode(
            "necesito animo",
            "",
            ""
        )
        assert result == "motivation"


# =============================================================================
# TESTS - _score_training_load
# =============================================================================

class TestScoreTrainingLoad:
    """Tests para ReadinessService._score_training_load."""

    def test_no_workouts_returns_100(self, mock_db):
        mock_db.query.return_value.filter.return_value.all.return_value = []
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score == 100.0

    def test_light_training_returns_high_score(self, mock_db, mock_workouts_normal):
        mock_db.query.return_value.filter.return_value.all.return_value = mock_workouts_normal
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score >= 60.0

    def test_extreme_training_returns_low_score(self, mock_db, mock_workouts_extreme):
        mock_db.query.return_value.filter.return_value.all.return_value = mock_workouts_extreme
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score <= 40.0

    def test_score_range_0_100(self, mock_db, mock_workouts_normal):
        mock_db.query.return_value.filter.return_value.all.return_value = mock_workouts_normal
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert 0 <= score <= 100

    def test_zero_duration_workout(self, mock_db):
        w = Mock()
        w.duration = 0
        w.date = date.today()
        mock_db.query.return_value.filter.return_value.all.return_value = [w]
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score == 100.0

    def test_none_duration_workout(self, mock_db):
        w = Mock()
        w.duration = None
        w.date = date.today()
        mock_db.query.return_value.filter.return_value.all.return_value = [w]
        from app.services.readiness_service import ReadinessService
        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score == 100.0


# =============================================================================
# TESTS - build_atlas_system_prompt
# =============================================================================

class TestBuildAtlasSystemPrompt:
    """Tests para build_atlas_system_prompt (estructura y cache)."""

    @patch("app.services.readiness_service.ReadinessService.calculate")
    @patch("app.services.injury_prevention_service.InjuryPreventionService.get_current_status")
    @patch("app.services.analytics_service.AnalyticsService.calculate_acwr")
    @patch("app.services.athlete_profile_service.AthleteProfileService.get_profile_summary")
    @patch("app.services.exercise_service.ExerciseService.get_context_summary")
    @patch("app.services.memory_service.MemoryService.get_memory_context_string")
    def test_returns_dict_with_prompt_and_name(self, mock_mem, mock_ex, mock_prof, mock_an, mock_inj, mock_read):
        from app.services.ai_service import build_atlas_system_prompt, _prompt_cache

        _prompt_cache.clear()

        mock_read.return_value = {"score": 75, "status": "good", "recommendation": "test", "baseline": {}}
        mock_inj.return_value = Mock(to_dict=Mock(return_value={"alert_level": "optimal", "active_injuries": [], "zones_to_avoid": [], "alerts": []}))
        mock_an.return_value = {"ratio": 1.0, "status": "mantenimiento", "message": ""}
        mock_prof.return_value = "Perfil no disponible"
        mock_ex.return_value = "Ejercicios: ..."
        mock_mem.return_value = "Memoria: ..."

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = build_atlas_system_prompt(mock_db, "user1")

        assert isinstance(result, dict)
        assert "prompt" in result
        assert "athlete_name" in result
        assert "athlete_age" in result
        assert "step_target" in result
        assert "readiness_score" in result
        assert "bio_summary" in result
        assert "injury_summary" in result

    @patch("app.services.readiness_service.ReadinessService.calculate")
    @patch("app.services.injury_prevention_service.InjuryPreventionService.get_current_status")
    @patch("app.services.analytics_service.AnalyticsService.calculate_acwr")
    @patch("app.services.athlete_profile_service.AthleteProfileService.get_profile_summary")
    @patch("app.services.exercise_service.ExerciseService.get_context_summary")
    @patch("app.services.memory_service.MemoryService.get_memory_context_string")
    def test_prompt_contains_athlete_name(self, mock_mem, mock_ex, mock_prof, mock_an, mock_inj, mock_read):
        from app.services.ai_service import build_atlas_system_prompt, _prompt_cache

        _prompt_cache.clear()

        mock_read.return_value = {"score": 75, "status": "good", "recommendation": "test", "baseline": {}}
        mock_inj.return_value = Mock(to_dict=Mock(return_value={"alert_level": "optimal", "active_injuries": [], "zones_to_avoid": [], "alerts": []}))
        mock_an.return_value = {"ratio": 1.0, "status": "mantenimiento", "message": ""}
        mock_prof.return_value = "Perfil no disponible"
        mock_ex.return_value = "Ejercicios: ..."
        mock_mem.return_value = ""

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = build_atlas_system_prompt(mock_db, "user1")

        assert "Sergi" in result["prompt"]

    @patch("app.services.readiness_service.ReadinessService.calculate")
    @patch("app.services.injury_prevention_service.InjuryPreventionService.get_current_status")
    @patch("app.services.analytics_service.AnalyticsService.calculate_acwr")
    @patch("app.services.athlete_profile_service.AthleteProfileService.get_profile_summary")
    @patch("app.services.exercise_service.ExerciseService.get_context_summary")
    @patch("app.services.memory_service.MemoryService.get_memory_context_string")
    def test_cache_returns_same_result(self, mock_mem, mock_ex, mock_prof, mock_an, mock_inj, mock_read):
        from app.services.ai_service import build_atlas_system_prompt, _prompt_cache

        _prompt_cache.clear()

        mock_read.return_value = {"score": 75, "status": "good", "recommendation": "test", "baseline": {}}
        mock_inj.return_value = Mock(to_dict=Mock(return_value={"alert_level": "optimal", "active_injuries": [], "zones_to_avoid": [], "alerts": []}))
        mock_an.return_value = {"ratio": 1.0, "status": "mantenimiento", "message": ""}
        mock_prof.return_value = "Perfil no disponible"
        mock_ex.return_value = "Ejercicios: ..."
        mock_mem.return_value = ""

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result1 = build_atlas_system_prompt(mock_db, "user1")
        result2 = build_atlas_system_prompt(mock_db, "user1")

        assert result1["prompt"] == result2["prompt"]
        assert mock_read.call_count == 1


# =============================================================================
# TESTS - ReadinessService.load_score_penalty_logic
# =============================================================================

class TestLoadScorePenaltyLogic:
    """Verify load_score inversion: 0-40 = bad (high load), 60-100 = good (low load)."""

    def test_score_training_load_returns_inverted_scale(self, mock_db):
        from app.services.readiness_service import ReadinessService
        # 5 workouts * 60min / 7 days = ~43 avg_daily_min → score ~80
        workouts = []
        for i in range(5):
            w = Mock()
            w.duration = 3600
            w.date = date.today() - timedelta(days=i)
            workouts.append(w)
        mock_db.query.return_value.filter.return_value.all.return_value = workouts

        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score >= 60  # Moderate to low load = high score (good)

    def test_high_volume_produces_low_score(self, mock_db):
        from app.services.readiness_service import ReadinessService
        # Extreme volume: 7 * 240min / 7 = 240 avg_daily_min → score ~20
        workouts = []
        for i in range(7):
            w = Mock()
            w.duration = 14400  # 240 min
            w.date = date.today() - timedelta(days=i)
            workouts.append(w)
        mock_db.query.return_value.filter.return_value.all.return_value = workouts

        score = ReadinessService._score_training_load(mock_db, "user1", days=7)
        assert score <= 40  # High load = low score (bad/risk)


# =============================================================================
# EJECUCION DIRECTA
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
