"""
TESTS UNITARIOS - READINESS ENGINE v2.0
=======================================
Pruebas para el motor consolidado de Readiness Score.

Ejecutar:
    cd backend && python -m pytest tests/unit/test_readiness_engine.py -v
    
O:
    python -m pytest tests/unit/test_readiness_engine.py --cov=app.core.readiness_engine
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from app.core.readiness_engine import (
    ReadinessEngine,
    ReadinessStatus,
    AthleteProfile,
    ReadinessFactors,
    PersonalBaseline,
    compute_readiness_score,
    create_readiness_engine,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Mock de sesión SQLAlchemy."""
    return Mock()


@pytest.fixture
def default_engine(mock_db):
    """Engine con perfil HYBRID (default)."""
    return ReadinessEngine("test_user", mock_db, AthleteProfile.HYBRID)


@pytest.fixture
def sample_biometric_data():
    """Datos biométricos de ejemplo (usuario promedio)."""
    return {
        "heart_rate": 60,
        "hrv": 55,
        "sleep_hours": 7.5,
        "sleep_score": 85,
        "stress_level": 35,
        "steps": 10000,
        "steps_prev_7d_avg": 10000,
        "is_rest_day": False,
        "exercise_load_7d": 1.0
    }


@pytest.fixture
def sample_baseline():
    """Baseline personal de ejemplo."""
    return PersonalBaseline(
        hr_resting_avg=60,
        hr_resting_std=5,
        hrv_avg=55,
        hrv_std=10,
        sleep_avg_hours=7.0,
        sleep_optimal_hours=7.5,
        sleep_consistency=0.2,
        steps_avg=10000,
        steps_training_days=15000,
        steps_rest_days=5000,
        workout_frequency_weekly=4,
        workout_duration_avg=60,
        workout_intensity_baseline=6,
        recovery_pattern="normal",
        rest_day_hr_threshold=65,
        data_points=90,
        confidence=0.9
    )


# =============================================================================
# TESTS - INICIALIZACIÓN Y CONFIGURACIÓN
# =============================================================================

class TestInitialization:
    """Tests de inicialización del engine."""
    
    def test_default_profile_is_hybrid(self, mock_db):
        """El perfil por defecto debe ser HYBRID."""
        engine = ReadinessEngine("user1", mock_db)
        assert engine.profile == AthleteProfile.HYBRID
    
    def test_profile_weights_strength(self, mock_db):
        """STRENGTH debe tener pesos ajustados."""
        engine = ReadinessEngine("user1", mock_db, AthleteProfile.STRENGTH)
        assert engine.weights["sleep"] == 0.35
        assert engine.weights["hr_baseline"] == 0.20
    
    def test_profile_weights_endurance(self, mock_db):
        """ENDURANCE debe tener pesos ajustados."""
        engine = ReadinessEngine("user1", mock_db, AthleteProfile.ENDURANCE)
        assert engine.weights["recovery"] == 0.30
        assert engine.weights["strain"] == 0.25
    
    def test_default_weights(self, mock_db):
        """Los pesos base deben sumar 1.0."""
        engine = ReadinessEngine("user1", mock_db)
        total = sum(engine.weights.values())
        assert total == 1.0
    
    def test_all_profiles_weights_sum_to_one(self, mock_db):
        """Todos los perfiles deben tener pesos que sumen 1.0."""
        for profile in AthleteProfile:
            engine = ReadinessEngine("user1", mock_db, profile)
            total = sum(engine.weights.values())
            assert abs(total - 1.0) < 0.001, f"{profile.value} weights sum to {total}"


# =============================================================================
# TESTS - CÁLCULO DE SCORES INDIVIDUALES
# =============================================================================

class TestSleepScore:
    """Tests para calculate_sleep_score."""
    
    def test_sleep_optimal(self, default_engine, sample_baseline):
        """Sueño óptimo (7.5h) debe dar score alto."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_sleep_score(7.5)
        assert score >= 90
        assert score <= 100
    
    def test_sleep_insufficient(self, default_engine, sample_baseline):
        """Sueño insuficiente (<5h) debe penalizar fuerte."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_sleep_score(4.0)
        assert score < 40
    
    def test_sleep_excessive(self, default_engine, sample_baseline):
        """Sueño excesivo (>9h) debe tener decaimiento leve."""
        default_engine.baseline = sample_baseline
        score_normal = default_engine.calculate_sleep_score(8.0)
        score_excess = default_engine.calculate_sleep_score(10.0)
        assert score_excess < score_normal
        assert score_excess > 60  # No penaliza tanto como insuficiente
    
    def test_sleep_with_quality_bonus(self, default_engine, sample_baseline):
        """Calidad de sueño debe mejorar el score."""
        default_engine.baseline = sample_baseline
        base_score = default_engine.calculate_sleep_score(7.0)
        quality_score = default_engine.calculate_sleep_score(7.0, sleep_quality=90)
        assert quality_score > base_score


class TestRecoveryScore:
    """Tests para calculate_recovery_score (HRV)."""
    
    def test_hrv_excellent(self, default_engine, sample_baseline):
        """HRV >110% baseline = excelente recuperación."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_recovery_score(65, 55)  # ~118%
        assert score >= 90
    
    def test_hrv_normal(self, default_engine, sample_baseline):
        """HRV 90-110% = recuperación normal."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_recovery_score(52, 55)  # ~95%
        assert score >= 70
        assert score <= 90
    
    def test_hrv_poor(self, default_engine, sample_baseline):
        """HRV <80% = mala recuperación."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_recovery_score(40, 55)  # ~73%
        assert score < 70
    
    def test_hrv_none_returns_neutral(self, default_engine):
        """Sin HRV (FR245) debe retornar valor neutral."""
        score = default_engine.calculate_recovery_score(None)
        assert score == 75.0


class TestStrainScore:
    """Tests para calculate_strain_score."""
    
    def test_low_stress(self, default_engine):
        """Estrés bajo (<25) = excelente."""
        score = default_engine.calculate_strain_score(20)
        assert score >= 90
    
    def test_high_stress(self, default_engine):
        """Estrés alto (>60) = penalización fuerte."""
        score = default_engine.calculate_strain_score(70)
        assert score < 50
    
    def test_exercise_load_penalty(self, default_engine):
        """Carga excesiva debe penalizar el strain."""
        normal = default_engine.calculate_strain_score(30, None)
        overload = default_engine.calculate_strain_score(30, 1.6)
        assert overload < normal


class TestActivityBalance:
    """Tests para calculate_activity_balance."""
    
    def test_rest_day_optimal(self, default_engine, sample_baseline):
        """Día de descanso con pasos moderados (5000-8000) = óptimo."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_activity_balance(6000, 10000, is_rest_day=True)
        assert score >= 80
    
    def test_rest_day_sedentary(self, default_engine, sample_baseline):
        """Día de descanso muy sedentario (<3000) = penalizado."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_activity_balance(2000, 10000, is_rest_day=True)
        assert score < 70
    
    def test_training_day_sweet_spot(self, default_engine, sample_baseline):
        """Día entrenamiento 80-120% del promedio = óptimo."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_activity_balance(11000, 10000, is_rest_day=False)
        assert score >= 80
    
    def test_overtraining_volume(self, default_engine, sample_baseline):
        """>150% volumen = sobreentrenamiento detectado."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_activity_balance(20000, 10000, is_rest_day=False)
        assert score < 70


class TestHRBaselineScore:
    """Tests para calculate_hr_baseline_score."""
    
    def test_normal_hr(self, default_engine, sample_baseline):
        """FC = baseline = score perfecto."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_hr_baseline_score(60)
        assert score == 100
    
    def test_slight_elevation(self, default_engine, sample_baseline):
        """FC +5-10 bpm = leve penalización."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_hr_baseline_score(68)
        assert score >= 70
        assert score < 100
    
    def test_significant_elevation(self, default_engine, sample_baseline):
        """FC +15+ bpm = penalización fuerte (fatiga)."""
        default_engine.baseline = sample_baseline
        score = default_engine.calculate_hr_baseline_score(80)
        assert score < 70


# =============================================================================
# TESTS - CÁLCULO COMPLETO DE READINESS
# =============================================================================

class TestReadinessCalculation:
    """Tests para calculate_readiness (integración)."""
    
    def test_perfect_conditions(self, default_engine, sample_baseline, sample_biometric_data):
        """Condiciones perfectas = score alto."""
        default_engine.baseline = sample_baseline
        data = sample_biometric_data.copy()
        data["sleep_hours"] = 8.0
        data["heart_rate"] = 55  # Por debajo del baseline
        data["hrv"] = 65  # Por encima del baseline
        data["stress_level"] = 20
        
        score, factors = default_engine.calculate_readiness(data)
        assert score >= 80
        assert factors.sleep_score >= 90
    
    def test_poor_conditions(self, default_engine, sample_baseline, sample_biometric_data):
        """Condiciones malas = score bajo."""
        default_engine.baseline = sample_baseline
        data = sample_biometric_data.copy()
        data["sleep_hours"] = 4.0
        data["heart_rate"] = 75  # Elevado
        data["stress_level"] = 70
        
        score, factors = default_engine.calculate_readiness(data)
        assert score < 50
    
    def test_score_range_bounds(self, default_engine, sample_baseline, sample_biometric_data):
        """Score siempre debe estar en rango 0-100."""
        default_engine.baseline = sample_baseline
        
        # Extremos
        extreme_data = sample_biometric_data.copy()
        extreme_data["sleep_hours"] = 12.0  # Muy alto
        extreme_data["steps"] = 50000  # Muy alto
        
        score, _ = default_engine.calculate_readiness(extreme_data)
        assert 0 <= score <= 100
    
    def test_factors_returned(self, default_engine, sample_baseline, sample_biometric_data):
        """Debe retornar todos los factores."""
        default_engine.baseline = sample_baseline
        score, factors = default_engine.calculate_readiness(sample_biometric_data)
        
        assert isinstance(factors, ReadinessFactors)
        assert 0 <= factors.sleep_score <= 100
        assert 0 <= factors.recovery_score <= 100
        assert 0 <= factors.strain_score <= 100
        assert 0 <= factors.activity_balance <= 100
        assert 0 <= factors.hr_baseline <= 100


# =============================================================================
# TESTS - DETECCIÓN DE OVERREACHING
# =============================================================================

class TestOverreachingDetection:
    """Tests para detect_overreaching."""
    
    def test_no_overreaching_normal_conditions(self, default_engine, sample_baseline, sample_biometric_data):
        """Condiciones normales = no overreaching."""
        default_engine.baseline = sample_baseline
        result = default_engine.detect_overreaching(sample_biometric_data)
        assert result["is_overreached"] is False
    
    def test_overreaching_elevated_hr(self, default_engine, sample_baseline, sample_biometric_data):
        """FC elevada +1.5 std = overreaching."""
        default_engine.baseline = sample_baseline
        data = sample_biometric_data.copy()
        data["heart_rate"] = 75  # baseline 60 + 1.5*5*3 ≈ 82.5, ponemos 75
        
        result = default_engine.detect_overreaching(data)
        # Verificar que detecta la señal aunque no llegue a threshold
        assert "FC reposo elevada" in result["message"] or result["is_overreached"] is True
    
    def test_insufficient_data_returns_safe(self, default_engine, sample_biometric_data):
        """Sin baseline suficiente = no detectar (falso negativo seguro)."""
        default_engine.baseline = None
        result = default_engine.detect_overreaching(sample_biometric_data)
        assert result["is_overreached"] is False
        assert "Datos insuficientes" in result["message"]


# =============================================================================
# TESTS - PREDICCIONES FUTURAS
# =============================================================================

class TestFuturePredictions:
    """Tests para predict_future_readiness."""
    
    def test_prediction_returns_structure(self, default_engine, sample_baseline):
        """La predicción debe retornar estructura completa."""
        default_engine.baseline = sample_baseline
        result = default_engine.predict_future_readiness(1, "normal")
        
        assert "predicted_score" in result
        assert "confidence" in result
        assert "recommendation" in result
        assert 0 <= result["predicted_score"] <= 100
        assert 0 <= result["confidence"] <= 1
    
    def test_high_load_reduces_prediction(self, default_engine, sample_baseline):
        """Carga alta debe predecir score más bajo."""
        default_engine.baseline = sample_baseline
        normal = default_engine.predict_future_readiness(1, "normal")
        high = default_engine.predict_future_readiness(1, "high")
        
        assert high["predicted_score"] < normal["predicted_score"]
    
    def test_fast_recovery_bonus(self, default_engine, sample_baseline):
        """Recuperación rápida = bonus en predicción."""
        default_engine.baseline = sample_baseline
        default_engine.baseline.recovery_pattern = "fast"
        
        result = default_engine.predict_future_readiness(1, "normal")
        assert result["predicted_score"] > 70  # Base 70 + bonus


# =============================================================================
# TESTS - API PÚBLICA
# =============================================================================

class TestPublicAPI:
    """Tests para compute_readiness_score y create_readiness_engine."""
    
    def test_compute_readiness_score_structure(self, sample_biometric_data):
        """La API pública debe retornar estructura completa."""
        result = compute_readiness_score(
            user_id="test_user",
            biometric_data=sample_biometric_data,
            db_session=None
        )
        
        assert "readiness_score" in result
        assert "status" in result
        assert "factors" in result
        assert "recommendation" in result
        assert "version" in result
        assert result["version"] == "2.0"
    
    def test_compute_maps_status_correctly(self, sample_biometric_data):
        """El status debe mapearse correctamente."""
        # Score alto
        data_high = sample_biometric_data.copy()
        data_high["sleep_hours"] = 8.0
        data_high["stress_level"] = 20
        
        result_high = compute_readiness_score("user", data_high, None)
        assert result_high["status"] == "high"
        
        # Score bajo
        data_low = sample_biometric_data.copy()
        data_low["sleep_hours"] = 4.0
        data_low["stress_level"] = 80
        
        result_low = compute_readiness_score("user", data_low, None)
        assert result_low["status"] == "low"
    
    def test_create_readiness_engine_returns_configured_engine(self, mock_db):
        """La fábrica debe retornar engine configurado."""
        engine = create_readiness_engine("user1", mock_db, AthleteProfile.STRENGTH)
        
        assert isinstance(engine, ReadinessEngine)
        assert engine.profile == AthleteProfile.STRENGTH
        assert engine.user_id == "user1"


# =============================================================================
# TESTS - PERFILES DE ATLETA
# =============================================================================

class TestAthleteProfiles:
    """Tests de impacto de perfiles en cálculo final."""
    
    def test_different_profiles_different_scores(self, mock_db, sample_baseline, sample_biometric_data):
        """Diferentes perfiles deben producir scores diferentes."""
        data = sample_biometric_data.copy()
        data["heart_rate"] = 65  # FC ligeramente elevada
        
        scores = {}
        for profile in AthleteProfile:
            engine = ReadinessEngine("user", mock_db, profile)
            engine.baseline = sample_baseline
            score, _ = engine.calculate_readiness(data)
            scores[profile.value] = score
        
        # STRENGTH penaliza más FC elevada (peso 0.20 vs 0.10)
        # ENDURANCE penaliza más strain (peso 0.25)
        assert len(set(scores.values())) > 1, "Different profiles should produce different scores"


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    # Ejecutar tests con salida detallada
    pytest.main([__file__, "-v", "--tb=short"])
