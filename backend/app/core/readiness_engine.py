"""
VITALIS READINESS SCORE ENGINE v1.0
====================================
Sistema de puntuación de preparación física basado en datos biométricos.

Fórmula ponderada:
- Sueño (30%): Duración + calidad relativa al histórico personal
- Recuperación/HRV (25%): Variabilidad cardíaca como indicador de recuperación
- Estrés/Strain (20%): Nivel de estrés acumulado
- Actividad (15%): Balance entre carga y descanso
- FC Reposos (10%): Desviación del baseline personal

Score: 0-100
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ReadinessStatus(Enum):
    LOW = "low"      # 0-40: No entrenar, priorizar recuperación
    MEDIUM = "medium" # 41-70: Entrenamiento moderado
    HIGH = "high"     # 71-100: Preparado para carga alta


@dataclass
class ReadinessFactors:
    sleep_score: float      # 0-100
    recovery_score: float   # 0-100 (basado en HRV)
    strain_score: float     # 0-100 (inverso del estrés)
    activity_balance: float  # 0-100
    hr_baseline: float      # 0-100
    
    def to_dict(self) -> Dict:
        return {
            "sleep": round(self.sleep_score, 1),
            "recovery": round(self.recovery_score, 1),
            "strain": round(self.strain_score, 1),
            "activity_balance": round(self.activity_balance, 1),
            "hr_baseline": round(self.hr_baseline, 1)
        }


class ReadinessEngine:
    """
    Motor de cálculo de Readiness Score basado en datos biométricos.
    
    Datos requeridos:
    - heart_rate: FC reposo actual
    - hrv: Variabilidad cardíaca (ms)
    - sleep_hours: Horas de sueño
    - sleep_score: Score de calidad de sueño (si disponible)
    - stress_level: Nivel de estrés (0-100)
    - steps: Pasos del día
    - steps_prev_7d: Promedio pasos últimos 7 días
    
    Baselines personales (calculados del histórico):
    - baseline_hr: FC reposo promedio personal
    - baseline_hrv: HRV promedio personal
    - optimal_sleep: Sueño óptimo calculado (7-9h típico)
    """
    
    # Pesos de la fórmula
    WEIGHTS = {
        "sleep": 0.30,
        "recovery": 0.25,
        "strain": 0.20,
        "activity": 0.15,
        "hr_baseline": 0.10
    }
    
    def __init__(self, user_id: str, db_session=None):
        self.user_id = user_id
        self.db = db_session
        self.baselines = self._load_user_baselines()
    
    def _load_user_baselines(self) -> Dict:
        """Carga o calcula baselines personales del histórico."""
        # En implementación real, esto consulta la base de datos
        # Por ahora usamos valores típicos calculados de los datos de Sergi
        return {
            "hr_resting": 48,           # FC reposo promedio
            "hrv_avg": 55,              # HRV promedio (ms) - estimado para FR245
            "sleep_optimal": 7.5,       # Sueño óptimo calculado
            "stress_baseline": 35,      # Estrés baseline
            "steps_avg": 17414          # Promedio pasos diarios
        }
    
    def calculate_sleep_score(self, sleep_hours: float, sleep_quality: Optional[float] = None) -> float:
        """
        Calcula score de sueño basado en duración y calidad.
        
        Lógica:
        - < 5h: Score base 40 (penalización fuerte)
        - 5-7h: Interpolación 40-80
        - 7-9h: Óptimo 80-100
        - > 9h: Decaimiento leve (posible oversleeping)
        """
        optimal = self.baselines["sleep_optimal"]
        
        if sleep_hours < 5:
            base_score = 40 * (sleep_hours / 5)
        elif sleep_hours < 7:
            base_score = 40 + (40 * (sleep_hours - 5) / 2)
        elif sleep_hours <= 9:
            base_score = 80 + (20 * (sleep_hours - 7) / 2)
        else:
            base_score = 100 - (5 * (sleep_hours - 9))  # Penalización leve por exceso
        
        # Ajuste por calidad si está disponible
        if sleep_quality:
            base_score = base_score * (0.7 + 0.3 * (sleep_quality / 100))
        
        return max(0, min(100, base_score))
    
    def calculate_recovery_score(self, hrv: Optional[float], 
                                hrv_7d_avg: Optional[float] = None) -> float:
        """
        Score de recuperación basado en HRV.
        
        Lógica:
        - HRV > 110% del promedio: Excelente recuperación (90-100)
        - HRV 90-110%: Normal (70-90)
        - HRV 80-90%: Leve fatiga (50-70)
        - HRV < 80%: Alta fatiga, necesita descanso (0-50)
        """
        if hrv is None:
            # Si no hay HRV (FR245 no lo mide), usamos proxy de FC + sueño
            return 75  # Neutral
        
        baseline = hrv_7d_avg or self.baselines["hrv_avg"]
        ratio = hrv / baseline
        
        if ratio >= 1.10:
            return min(100, 90 + (ratio - 1.10) * 100)
        elif ratio >= 0.90:
            return 70 + (ratio - 0.90) * 100
        elif ratio >= 0.80:
            return 50 + (ratio - 0.80) * 200
        else:
            return max(0, ratio * 62.5)  # ratio 0.80 -> 50, ratio 0.50 -> 31
    
    def calculate_strain_score(self, stress_level: float, 
                               exercise_load_7d: Optional[float] = None) -> float:
        """
        Score de strain (inverso del estrés y carga).
        
        Lógica:
        - Estrés < 25: Excelente (90-100)
        - Estrés 25-40: Bueno (70-90)
        - Estrés 40-60: Moderado (50-70)
        - Estrés > 60: Alto strain (0-50)
        """
        if stress_level < 25:
            base = 90 + (25 - stress_level) * 0.4  # Bonus por bajo estrés
        elif stress_level < 40:
            base = 70 + (40 - stress_level) * 1.33
        elif stress_level < 60:
            base = 50 + (60 - stress_level) * 1.0
        else:
            base = max(0, 50 - (stress_level - 60) * 1.25)
        
        # Ajuste por carga de ejercicio si disponible
        if exercise_load_7d:
            # Si la carga 7d es >150% del promedio, penalizar
            if exercise_load_7d > 1.5:
                base *= 0.9
        
        return max(0, min(100, base))
    
    def calculate_activity_balance(self, steps_today: int, 
                                   steps_avg_7d: Optional[int] = None,
                                   is_rest_day: bool = False) -> float:
        """
        Balance de actividad: ni sedentario ni sobreentrenamiento.
        
        Lógica:
        - Día de descanso: 80-100 si steps < 8000
        - Día normal: 80-100 si steps está en 80-120% del promedio
        - >150% del promedio: Posible sobreentrenamiento (decae)
        - <50% del promedio: Sedentario (decae)
        """
        baseline = steps_avg_7d or self.baselines["steps_avg"]
        ratio = steps_today / baseline if baseline > 0 else 1.0
        
        if is_rest_day:
            # Día de descanso: queremos movimiento ligero
            if steps_today < 3000:
                return 60  # Muy sedentario
            elif steps_today < 8000:
                return 90 + (8000 - steps_today) / 500  # Óptimo descanso activo
            else:
                return max(70, 100 - (steps_today - 8000) / 500)
        else:
            # Día de entrenamiento
            if ratio < 0.5:
                return 50 + ratio * 60  # 0.5 -> 80
            elif ratio <= 1.2:
                return 80 + (ratio - 0.5) * 28.6  # 1.2 -> 100
            elif ratio <= 1.5:
                return 100  # Sweet spot
            else:
                return max(60, 100 - (ratio - 1.5) * 40)  # Penaliza sobreentrenamiento
    
    def calculate_hr_baseline_score(self, hr_current: float) -> float:
        """
        Desviación de la FC reposo respecto al baseline personal.
        
        Lógica:
        - FC = baseline: Score 100
        - FC > baseline: Posible fatiga/falta de recuperación
        - FC < baseline: Posible sobreentrenamiento/estado excitado
        """
        baseline = self.baselines["hr_resting"]
        deviation = abs(hr_current - baseline)
        
        # Desviación hasta ±5 bpm: Score perfecto
        # Desviación 5-15 bpm: Decaimiento lineal
        # Desviación >15 bpm: Penalización fuerte
        if deviation <= 5:
            return 100
        elif deviation <= 15:
            return 100 - (deviation - 5) * 3  # 15 -> 70
        else:
            return max(40, 70 - (deviation - 15) * 2)
    
    def calculate_readiness(self, data: Dict) -> Tuple[float, ReadinessFactors]:
        """
        Calcula el Readiness Score completo.
        
        Input data dict:
        {
            "heart_rate": 48,
            "hrv": None,  # FR245 no mide HRV continuo
            "sleep_hours": 6.5,
            "sleep_score": None,
            "stress_level": 35,
            "steps": 15000,
            "steps_prev_7d_avg": 17414,
            "is_rest_day": False,
            "exercise_load_7d": 1.0  # ratio vs baseline
        }
        """
        # Calcular scores individuales
        sleep = self.calculate_sleep_score(
            data.get("sleep_hours", 0),
            data.get("sleep_score")
        )
        
        recovery = self.calculate_recovery_score(
            data.get("hrv"),
            data.get("hrv_7d_avg")
        )
        
        strain = self.calculate_strain_score(
            data.get("stress_level", 50),
            data.get("exercise_load_7d")
        )
        
        activity = self.calculate_activity_balance(
            data.get("steps", 0),
            data.get("steps_prev_7d_avg"),
            data.get("is_rest_day", False)
        )
        
        hr_score = self.calculate_hr_baseline_score(
            data.get("heart_rate", self.baselines["hr_resting"])
        )
        
        # Calcular score ponderado
        factors = ReadinessFactors(
            sleep_score=sleep,
            recovery_score=recovery,
            strain_score=strain,
            activity_balance=activity,
            hr_baseline=hr_score
        )
        
        total_score = (
            sleep * self.WEIGHTS["sleep"] +
            recovery * self.WEIGHTS["recovery"] +
            strain * self.WEIGHTS["strain"] +
            activity * self.WEIGHTS["activity"] +
            hr_score * self.WEIGHTS["hr_baseline"]
        )
        
        return round(total_score, 1), factors
    
    def get_recommendation(self, score: float, status: ReadinessStatus) -> str:
        """Genera recomendación accionable basada en el score."""
        recommendations = {
            ReadinessStatus.HIGH: [
                "Preparado para entrenamiento de alta intensidad o volumen",
                "Buen momento para probar nuevos PRs o competir",
                "Recuperación óptima - puedes cargar más hoy"
            ],
            ReadinessStatus.MEDIUM: [
                "Entrenamiento moderado recomendado (70-80% de carga habitual)",
                "Prioriza técnica sobre intensidad",
                "Monitorea cómo te sientes durante el calentamiento"
            ],
            ReadinessStatus.LOW: [
                "Día de recuperación activa o descanso completo",
                "Prioriza sueño, hidratación y nutrición",
                "Si entrenas: máximo 40% carga habitual, enfoque en movilidad",
                "Considera técnicas de recuperación: masaje, baño frío, meditación"
            ]
        }
        
        import random
        return random.choice(recommendations[status])


# ==================== FUNCIÓN PRINCIPAL ====================

def compute_readiness_score(user_id: str, 
                              biometric_data: Dict,
                              db_session=None) -> Dict:
    """
    Función principal para calcular el Readiness Score.
    
    Ejemplo de uso:
    
    data = {
        "heart_rate": 48,
        "sleep_hours": 6.5,
        "stress_level": 35,
        "steps": 15000,
        "steps_prev_7d_avg": 17414,
        "is_rest_day": False
    }
    
    result = compute_readiness_score("default_user", data)
    """
    engine = ReadinessEngine(user_id, db_session)
    
    score, factors = engine.calculate_readiness(biometric_data)
    
    # Determinar status
    if score >= 71:
        status = ReadinessStatus.HIGH
    elif score >= 41:
        status = ReadinessStatus.MEDIUM
    else:
        status = ReadinessStatus.LOW
    
    # Construir respuesta
    return {
        "readiness_score": score,
        "status": status.value,
        "factors": factors.to_dict(),
        "recommendation": engine.get_recommendation(score, status),
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "version": "1.0"
    }


# Ejemplo de ejecución con datos de Sergi
if __name__ == "__main__":
    # Datos de ejemplo basados en promedios de Sergi
    sample_data = {
        "heart_rate": 48,
        "hrv": None,  # FR245 no mide HRV
        "sleep_hours": 6.4,
        "sleep_score": None,
        "stress_level": 36,
        "steps": 17414,
        "steps_prev_7d_avg": 17414,
        "is_rest_day": False,
        "exercise_load_7d": 1.0
    }
    
    result = compute_readiness_score("default_user", sample_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
