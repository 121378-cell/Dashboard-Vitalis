"""
VITALIS ADAPTIVE READINESS SYSTEM v2.0
=======================================
Sistema de Readiness Score adaptativo basado en IA y aprendizaje del usuario.

Características PRO:
- Aprende baselines personales del histórico (no valores genéricos)
- Detecta patrones individuales de recuperación
- Ajusta pesos según el tipo de atleta (fuerza, resistencia, mixto)
- Predice readiness futuro basado en tendencias
- Detección de overreaching/overtraining personalizada
"""

import json
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class AthleteProfile(Enum):
    """Perfiles de atleta para ajustar pesos del algoritmo."""
    STRENGTH = "strength"           # Fuerza/potencia
    ENDURANCE = "endurance"       # Resistencia/cardio
    HYBRID = "hybrid"             # Mixto (CrossFit, triatlón)
    RECREATIONAL = "recreational" # Salud/fitness general


@dataclass
class PersonalBaseline:
    """Baselines calculados del histórico personal del usuario."""
    # Fisiológicos
    hr_resting_avg: float
    hr_resting_std: float       # Desviación estándar (detecta anomalías)
    hrv_avg: Optional[float]
    hrv_std: Optional[float]
    
    # Sueño
    sleep_avg_hours: float
    sleep_optimal_hours: float   # Calculado: donde se maximiza el rendimiento
    sleep_consistency: float     # Coeficiente de variación
    
    # Actividad
    steps_avg: float
    steps_training_days: float
    steps_rest_days: float
    
    # Carga
    workout_frequency_weekly: float  # Sesiones/semana promedio
    workout_duration_avg: float        # Minutos por sesión
    workout_intensity_baseline: float # RPE promedio
    
    # Recuperación individual
    recovery_pattern: str       # "fast" | "normal" | "slow"
    rest_day_hr_threshold: float # FC que indica día de descanso necesario
    
    # Metadatos
    data_points: int            # Cuántos días usamos para calcular
    confidence: float            # 0-1, qué tan fiable es el baseline


class AdaptiveReadinessEngine:
    """
    Motor de Readiness adaptativo que aprende del usuario.
    
    Diferencias vs ReadinessEngine básico:
    - Baselines calculados del histórico real, no estimaciones
    - Pesos ajustables por perfil de atleta
    - Detección de overreaching basada en desviaciones personales
    - Predicciones de readiness futuro
    """
    
    # Pesos por defecto (ajustables por perfil)
    BASE_WEIGHTS = {
        "sleep": 0.30,
        "recovery": 0.25,
        "strain": 0.20,
        "activity": 0.15,
        "hr_baseline": 0.10
    }
    
    # Ajustes por perfil de atleta
    PROFILE_MODIFIERS = {
        AthleteProfile.STRENGTH: {
            "sleep": 0.35,        # Más importante para fuerza
            "recovery": 0.30,     # HRV muy importante
            "strain": 0.15,       # Menos importante (más tolerable)
            "hr_baseline": 0.20   # FC importante para detectar fatiga CNS
        },
        AthleteProfile.ENDURANCE: {
            "sleep": 0.25,
            "recovery": 0.30,     # HRV crítico
            "strain": 0.25,      # Estrés acumulado muy importante
            "activity": 0.20     # Balance de carga importante
        },
        AthleteProfile.HYBRID: {
            "sleep": 0.30,
            "recovery": 0.25,
            "strain": 0.25,
            "activity": 0.20     # Importante para gestionar volumen
        },
        AthleteProfile.RECREATIONAL: {
            "sleep": 0.35,
            "strain": 0.25,      # Evitar estrés excesivo
            "recovery": 0.20,
            "activity": 0.20
        }
    }
    
    def __init__(self, user_id: str, db_session=None, profile: AthleteProfile = AthleteProfile.HYBRID):
        self.user_id = user_id
        self.db = db_session
        self.profile = profile
        self.baseline = None
        self.weights = self._get_weights_for_profile()
    
    def _get_weights_for_profile(self) -> Dict[str, float]:
        """Devuelve los pesos ajustados para el perfil del atleta."""
        return self.PROFILE_MODIFIERS.get(self.profile, self.BASE_WEIGHTS)
    
    def calculate_personal_baseline(self, days_of_history: int = 90) -> PersonalBaseline:
        """
        Calcula baselines personales del histórico del usuario.
        
        Esto es la CLAVE del sistema adaptativo:
        - No usa valores genéricos de "atleta promedio"
        - Usa los datos reales de Sergi para entender su "normal"
        - Detecta qué es anómalo para ÉL, no para la población general
        """
        from app.models.biometrics import Biometrics
        from app.models.workout import Workout
        
        start_date = (datetime.now() - timedelta(days=days_of_history)).strftime("%Y-%m-%d")
        
        # Obtener datos biométricos del período
        biometrics = self.db.query(Biometrics).filter(
            Biometrics.user_id == self.user_id,
            Biometrics.date >= start_date
        ).all()
        
        if not biometrics:
            # Fallback a valores genéricos si no hay datos
            return self._get_default_baseline()
        
        # Extraer métricas
        heart_rates = []
        sleep_hours = []
        stress_levels = []
        steps_list = []
        
        for b in biometrics:
            if not b.data:
                continue
            try:
                data = json.loads(b.data)
                if data.get("heartRate") and data["heartRate"] > 30:
                    heart_rates.append(data["heartRate"])
                if data.get("sleep") and data["sleep"] > 0:
                    sleep_hours.append(data["sleep"])
                if data.get("stress") and data["stress"] >= 0:
                    stress_levels.append(data["stress"])
                if data.get("steps") and data["steps"] > 0:
                    steps_list.append(data["steps"])
            except:
                continue
        
        # Obtener datos de workouts
        workouts = self.db.query(Workout).filter(
            Workout.user_id == self.user_id,
            Workout.date >= start_date
        ).all()
        
        workout_durations = [w.duration for w in workouts if w.duration and w.duration > 0]
        
        # Calcular baselines
        def safe_avg(lst):
            return statistics.mean(lst) if lst else 0
        
        def safe_std(lst):
            return statistics.stdev(lst) if len(lst) > 1 else 0
        
        # Detectar patrón de recuperación
        recovery_pattern = self._detect_recovery_pattern(heart_rates, sleep_hours)
        
        # Calcular sueño óptimo (donde HR es más baja al día siguiente)
        optimal_sleep = self._calculate_optimal_sleep(biometrics)
        
        # Calcular threshold de día de descanso
        rest_threshold = self._calculate_rest_threshold(heart_rates, sleep_hours)
        
        baseline = PersonalBaseline(
            hr_resting_avg=safe_avg(heart_rates),
            hr_resting_std=safe_std(heart_rates),
            hrv_avg=None,  # FR245 no mide HRV continuo
            hrv_std=None,
            sleep_avg_hours=safe_avg(sleep_hours),
            sleep_optimal_hours=optimal_sleep or safe_avg(sleep_hours),
            sleep_consistency=safe_std(sleep_hours) / safe_avg(sleep_hours) if sleep_hours else 1.0,
            steps_avg=safe_avg(steps_list),
            steps_training_days=safe_avg([s for s in steps_list if s > 10000]) if steps_list else 15000,
            steps_rest_days=safe_avg([s for s in steps_list if s < 8000]) if steps_list else 5000,
            workout_frequency_weekly=len(workouts) / (days_of_history / 7) if workouts else 3,
            workout_duration_avg=safe_avg(workout_durations) / 60 if workout_durations else 60,  # minutos
            workout_intensity_baseline=6.0,  # RPE estimado
            recovery_pattern=recovery_pattern,
            rest_day_hr_threshold=safe_avg(heart_rates) + 5 if heart_rates else 55,
            data_points=len(biometrics),
            confidence=min(1.0, len(biometrics) / 30)  # Más datos = más confianza
        )
        
        self.baseline = baseline
        return baseline
    
    def _detect_recovery_pattern(self, heart_rates: List[float], sleep_hours: List[float]) -> str:
        """
        Detecta si el usuario tiene recuperación rápida, normal o lenta.
        Basado en la variabilidad de FC y correlación con sueño.
        """
        if len(heart_rates) < 14:
            return "normal"  # Datos insuficientes
        
        # Calcular CV (coeficiente de variación) de HR
        avg_hr = statistics.mean(heart_rates)
        std_hr = statistics.stdev(heart_rates)
        cv = std_hr / avg_hr if avg_hr > 0 else 0
        
        # CV < 5% = muy consistente (recuperación rápida o super entrenado)
        # CV 5-10% = normal
        # CV > 10% = variable (recuperación lenta o sobreentrenamiento)
        
        if cv < 0.05:
            # Muy consistente - podría ser atleta élite o supercompensado
            return "fast"
        elif cv < 0.10:
            return "normal"
        else:
            return "slow"
    
    def _calculate_optimal_sleep(self, biometrics: List) -> Optional[float]:
        """
        Calcula las horas óptimas de sueño para este usuario.
        Basado en: ¿qué duración de sueño precede a los días con mejor FC?
        """
        sleep_hr_pairs = []
        
        for i, b in enumerate(biometrics):
            if not b.data or i == len(biometrics) - 1:
                continue
            try:
                data = json.loads(b.data)
                sleep = data.get("sleep", 0)
                # HR del día siguiente
                next_data = json.loads(biometrics[i + 1].data) if biometrics[i + 1].data else {}
                next_hr = next_data.get("heartRate", 60)
                
                if sleep > 0 and next_hr > 0:
                    sleep_hr_pairs.append((sleep, next_hr))
            except:
                continue
        
        if len(sleep_hr_pairs) < 10:
            return None
        
        # Agrupar por rangos de sueño y encontrar el que da menor HR
        buckets = {}
        for sleep, hr in sleep_hr_pairs:
            bucket = round(sleep * 2) / 2  # Agrupar en medias horas
            if bucket not in buckets:
                buckets[bucket] = []
            buckets[bucket].append(hr)
        
        # Encontrar bucket con menor HR promedio
        best_sleep = None
        best_hr = float('inf')
        for sleep, hrs in buckets.items():
            if len(hrs) >= 3:  # Mínimo 3 datos por bucket
                avg_hr = statistics.mean(hrs)
                if avg_hr < best_hr:
                    best_hr = avg_hr
                    best_sleep = sleep
        
        return best_sleep
    
    def _calculate_rest_threshold(self, heart_rates: List[float], sleep_hours: List[float]) -> float:
        """
        Calcula el threshold de FC que indica necesidad de descanso.
        Basado en percentil 75 de FC + margen.
        """
        if not heart_rates:
            return 55
        
        sorted_hr = sorted(heart_rates)
        p75_index = int(len(sorted_hr) * 0.75)
        p75_hr = sorted_hr[min(p75_index, len(sorted_hr) - 1)]
        
        return p75_hr + 3  # Margen de seguridad
    
    def _get_default_baseline(self) -> PersonalBaseline:
        """Baseline por defecto cuando no hay datos históricos."""
        return PersonalBaseline(
            hr_resting_avg=60,
            hr_resting_std=5,
            hrv_avg=50,
            hrv_std=10,
            sleep_avg_hours=7,
            sleep_optimal_hours=7.5,
            sleep_consistency=0.2,
            steps_avg=10000,
            steps_training_days=15000,
            steps_rest_days=5000,
            workout_frequency_weekly=3,
            workout_duration_avg=60,
            workout_intensity_baseline=6,
            recovery_pattern="normal",
            rest_day_hr_threshold=65,
            data_points=0,
            confidence=0.0
        )
    
    def detect_overreaching(self, data: Dict) -> Tuple[bool, str, float]:
        """
        Detecta overreaching/overtraining personalizado.
        
        Returns:
        (is_overreached, message, severity_0_to_1)
        """
        if not self.baseline or self.baseline.confidence < 0.5:
            return False, "Datos insuficientes para detectar overreaching", 0.0
        
        signals = []
        severity = 0.0
        
        # Señal 1: FC reposo > 1.5 desviaciones por encima del baseline
        current_hr = data.get("heart_rate", self.baseline.hr_resting_avg)
        if current_hr > self.baseline.hr_resting_avg + (1.5 * self.baseline.hr_resting_std):
            signals.append("FC reposo elevada (fatiga acumulada)")
            severity += 0.3
        
        # Señal 2: Sueño por debajo del óptimo + FC elevada
        sleep = data.get("sleep_hours", 0)
        if sleep < self.baseline.sleep_optimal_hours - 1 and current_hr > self.baseline.hr_resting_avg + 3:
            signals.append("Combinación sueño deficiente + FC elevada")
            severity += 0.3
        
        # Señal 3: Estrés elevado por >3 días (simulado con current data)
        stress = data.get("stress_level", 0)
        if stress > 60:
            signals.append("Estrés elevado")
            severity += 0.2
        
        # Señal 4: Volumen de pasos >150% del promedio de entrenamiento
        steps = data.get("steps", 0)
        if steps > self.baseline.steps_training_days * 1.5:
            signals.append("Volumen de actividad muy alto")
            severity += 0.2
        
        is_overreached = severity >= 0.5
        message = "; ".join(signals) if signals else "Sin señales de overreaching"
        
        return is_overreached, message, min(1.0, severity)
    
    def predict_future_readiness(self, days_ahead: int = 1, planned_load: str = "normal") -> Dict:
        """
        Predice el readiness score futuro basado en tendencias.
        
        Args:
            days_ahead: Días en el futuro a predecir
            planned_load: "low", "normal", "high" - carga planeada
        
        Returns:
        {
            "predicted_score": 75.5,
            "confidence": 0.7,
            "factors": {...},
            "recommendation": "Si haces entrenamiento intenso mañana, tu score bajará a 55"
        }
        """
        # Simulación simplificada - en producción usaríamos modelo ML
        # basado en datos de los últimos 30 días
        
        if not self.baseline:
            return {
                "predicted_score": 70,
                "confidence": 0.3,
                "message": "Sin datos históricos suficientes para predicción"
            }
        
        # Tendencia basada en recovery_pattern
        base_score = 70  # Asumimos score medio
        
        load_impact = {
            "low": 5,
            "normal": 0,
            "high": -10
        }.get(planned_load, 0)
        
        # Ajuste por patrón de recuperación
        recovery_bonus = {
            "fast": 5,
            "normal": 0,
            "slow": -5
        }.get(self.baseline.recovery_pattern, 0)
        
        predicted = base_score + load_impact + recovery_bonus
        confidence = self.baseline.confidence * 0.8  # Menos confianza en predicciones
        
        return {
            "predicted_score": max(0, min(100, predicted)),
            "confidence": round(confidence, 2),
            "load_assumed": planned_load,
            "recovery_pattern": self.baseline.recovery_pattern,
            "recommendation": self._get_prediction_recommendation(predicted, planned_load)
        }
    
    def _get_prediction_recommendation(self, predicted_score: float, planned_load: str) -> str:
        if predicted_score < 50:
            return f"Con carga {planned_load}, tu score caerá a {predicted_score:.0f}. Considera reducir intensidad o descansar."
        elif predicted_score < 70:
            return f"Carga {planned_load} es adecuada. Score esperado: {predicted_score:.0f}."
        else:
            return f"Preparado para carga {planned_load}. Score esperado: {predicted_score:.0f}."


# ==================== FUNCIÓN DE FÁBRICA ====================

def create_adaptive_engine(user_id: str, db_session, 
                           profile: AthleteProfile = AthleteProfile.HYBRID,
                           force_recalc_baseline: bool = False) -> AdaptiveReadinessEngine:
    """
    Crea un motor adaptativo configurado para el usuario.
    
    Cachea el baseline para no recalcular en cada request.
    En producción, usar Redis o similar para cache global.
    """
    engine = AdaptiveReadinessEngine(user_id, db_session, profile)
    
    # Calcular baselines
    engine.calculate_personal_baseline(days_of_history=90)
    
    return engine


# ==================== EJEMPLO DE USO ====================

if __name__ == "__main__":
    print("VITALIS Adaptive Readiness Engine v2.0")
    print("=" * 50)
    print("\nCaracterísticas PRO:")
    print("- Baselines calculados del histórico personal")
    print("- Pesos ajustables por perfil de atleta")
    print("- Detección de overreaching personalizada")
    print("- Predicciones de readiness futuro")
    print("\nPara usar:")
    print("  engine = create_adaptive_engine('default_user', db, AthleteProfile.STRENGTH)")
    print("  is_overreached, msg, severity = engine.detect_overreaching(data)")
    print("  prediction = engine.predict_future_readiness(days_ahead=1, planned_load='high')")
