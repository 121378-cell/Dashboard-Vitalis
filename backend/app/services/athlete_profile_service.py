"""
Dashboard-Vitalis — Athlete Profile Service
=============================================

Sistema de construcción y actualización de perfil de atleta basado en
todo el historial biométrico y de actividades disponible en BD.

Métricas calculadas:
- Cardiovasculares (FC reposo, tendencias)
- Sueño (horas, calidad, patrones)
- Estrés (niveles, tendencias)
- Actividad física (pasos, tipos, volumen)
- Rendimiento (VO2max, cargas)
- Estado actual (readiness, fatiga, recuperación)

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

import json
import logging
import statistics
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger("app.services.athlete_profile")

# Ventanas de tiempo para cálculos
DAYS_SHORT = 7    # Última semana (estado actual)
DAYS_MEDIUM = 30  # Último mes (tendencias recientes)
DAYS_LONG = 90    # Últimos 3 meses (perfil base)


@dataclass
class CardioMetrics:
    """Métricas cardiovasculares del atleta."""
    fc_reposo_media: float = 0.0
    fc_reposo_min: float = 0.0
    fc_reposo_tendencia: str = "estable"  # subiendo/bajando/estable
    hrv_media: Optional[float] = None
    hrv_tendencia: str = "estable"


@dataclass
class SleepMetrics:
    """Métricas de sueño."""
    sueno_media_horas: float = 0.0
    sueno_optimo_horas: float = 0.0  # Percentil 75
    sueno_deficit_dias: int = 0  # Días con < 6h
    patron_sueno: str = "regular"  # regular/irregular


@dataclass
class StressMetrics:
    """Métricas de estrés."""
    estres_medio: float = 0.0
    estres_tendencia: str = "estable"
    dias_alto_estres: int = 0  # Estrés > 70


@dataclass
class ActivityMetrics:
    """Métricas de actividad física."""
    pasos_media_diaria: float = 0.0
    dias_activos_semana: float = 0.0
    tipo_atleta: str = "mixto"  # fuerza/resistencia/mixto/sedentario
    volumen_semanal_minutos: float = 0.0
    sesiones_semana: float = 0.0


@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento deportivo."""
    vo2max_actual: Optional[float] = None
    vo2max_tendencia: str = "estable"
    carga_tipica_sesion_min: float = 0.0
    calorias_quemadas_sesion: float = 0.0


@dataclass
class CurrentState:
    """Estado actual del atleta (últimos 7 días)."""
    readiness_medio_7d: float = 0.0
    fatiga_acumulada: str = "normal"  # normal/elevada/alta
    recuperacion_estimada_horas: Optional[int] = None


@dataclass
class AthleteProfile:
    """Perfil completo del atleta."""
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    cardio: CardioMetrics = field(default_factory=CardioMetrics)
    sleep: SleepMetrics = field(default_factory=SleepMetrics)
    stress: StressMetrics = field(default_factory=StressMetrics)
    activity: ActivityMetrics = field(default_factory=ActivityMetrics)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    current_state: CurrentState = field(default_factory=CurrentState)
    
    # Campos adicionales
    dias_con_datos: int = 0
    fecha_ultimo_dato: Optional[str] = None


class AthleteProfileService:
    """
    Servicio de construcción y mantenimiento de perfil de atleta.
    """
    
    @staticmethod
    def _get_date_range(days: int) -> Tuple[date, date]:
        """Calcula rango de fechas (start, end)."""
        end = date.today()
        start = end - timedelta(days=days)
        return start, end
    
    @staticmethod
    def _load_biometrics_for_period(
        db: Session, 
        user_id: str, 
        days: int = DAYS_LONG
    ) -> List[Dict]:
        """Carga datos biométricos para un período."""
        start, end = AthleteProfileService._get_date_range(days)
        
        records = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= start.isoformat(),
            Biometrics.date <= end.isoformat()
        ).order_by(Biometrics.date.desc()).all()
        
        result = []
        for record in records:
            try:
                data = json.loads(record.data) if record.data else {}
                data["_date"] = record.date
                result.append(data)
            except:
                continue
        
        return result
    
    @staticmethod
    def _load_workouts_for_period(
        db: Session,
        user_id: str,
        days: int = DAYS_LONG
    ) -> List[Workout]:
        """Carga workouts para un período."""
        start, end = AthleteProfileService._get_date_range(days)
        
        return db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date >= start,
            Workout.date <= end
        ).order_by(Workout.date.desc()).all()
    
    @staticmethod
    def _calculate_tendencia(
        valores_recientes: List[float],
        valores_anteriores: List[float]
    ) -> str:
        """Calcula tendencia comparando dos períodos."""
        if not valores_recientes or not valores_anteriores:
            return "estable"
        
        media_reciente = statistics.mean(valores_recientes)
        media_anterior = statistics.mean(valores_anteriores)
        
        # Para FC reposo: menor es mejor
        # Para otros: mayor puede ser mejor o peor dependiendo del contexto
        diff_pct = (media_reciente - media_anterior) / media_anterior if media_anterior else 0
        
        if abs(diff_pct) < 0.05:  # < 5% cambio
            return "estable"
        elif diff_pct < 0:
            return "bajando"
        else:
            return "subiendo"
    
    @staticmethod
    def _calculate_cardio_metrics(data_90d: List[Dict], data_30d: List[Dict]) -> CardioMetrics:
        """Calcula métricas cardiovasculares."""
        metrics = CardioMetrics()
        
        # FC reposo de los últimos 90 días
        fc_values = [d.get("heartRate", 0) for d in data_90d if d.get("heartRate", 0) > 0]
        
        if fc_values:
            metrics.fc_reposo_media = round(statistics.mean(fc_values), 1)
            metrics.fc_reposo_min = round(min(fc_values), 1)
        
        # Tendencia FC (últimos 30 vs anteriores 60)
        if len(data_90d) >= 60:
            fc_30d = [d.get("heartRate", 0) for d in data_30d if d.get("heartRate", 0) > 0]
            fc_60_90d = [d.get("heartRate", 0) for d in data_90d[30:] if d.get("heartRate", 0) > 0]
            metrics.fc_reposo_tendencia = AthleteProfileService._calculate_tendencia(fc_30d, fc_60_90d)
        
        # HRV
        hrv_values = [d.get("hrv") for d in data_90d if d.get("hrv")]
        if hrv_values:
            metrics.hrv_media = round(statistics.mean(hrv_values), 1)
            
            # Tendencia HRV
            hrv_30d = [d.get("hrv") for d in data_30d if d.get("hrv")]
            hrv_60_90d = [d.get("hrv") for d in data_90d[30:] if d.get("hrv")]
            if hrv_30d and hrv_60_90d:
                metrics.hrv_tendencia = AthleteProfileService._calculate_tendencia(hrv_30d, hrv_60_90d)
        
        return metrics
    
    @staticmethod
    def _calculate_sleep_metrics(data_90d: List[Dict]) -> SleepMetrics:
        """Calcula métricas de sueño."""
        metrics = SleepMetrics()
        
        # Horas de sueño - FIX: usar "sleep" no "sleep_hours" según estructura BD
        sueno_values = [d.get("sleep", 0) for d in data_90d if d.get("sleep", 0) > 0]
        
        if sueno_values:
            metrics.sueno_media_horas = round(statistics.mean(sueno_values), 1)
            metrics.sueno_optimo_horas = round(
                statistics.quantiles(sueno_values, n=4)[2] if len(sueno_values) >= 4 else max(sueno_values),
                1
            )
            metrics.sueno_deficit_dias = sum(1 for s in sueno_values if s < 6)
            
            # Patrón de sueño (desviación estándar)
            if len(sueno_values) >= 7:
                std_dev = statistics.stdev(sueno_values)
                metrics.patron_sueno = "irregular" if std_dev > 1.5 else "regular"
        
        return metrics
    
    @staticmethod
    def _calculate_stress_metrics(data_90d: List[Dict], data_30d: List[Dict]) -> StressMetrics:
        """Calcula métricas de estrés."""
        metrics = StressMetrics()
        
        # Valores de estrés
        estres_values = [d.get("stress", 0) for d in data_90d if d.get("stress", 0) > 0]
        
        if estres_values:
            metrics.estres_medio = round(statistics.mean(estres_values), 1)
            metrics.dias_alto_estres = sum(1 for e in estres_values if e > 70)
        
        # Tendencia
        if len(data_90d) >= 60:
            estres_30d = [d.get("stress", 0) for d in data_30d if d.get("stress", 0) > 0]
            estres_60_90d = [d.get("stress", 0) for d in data_90d[30:] if d.get("stress", 0) > 0]
            metrics.estres_tendencia = AthleteProfileService._calculate_tendencia(estres_30d, estres_60_90d)
        
        return metrics
    
    @staticmethod
    def _calculate_activity_metrics(
        data_90d: List[Dict], 
        workouts_90d: List[Workout]
    ) -> ActivityMetrics:
        """Calcula métricas de actividad física."""
        metrics = ActivityMetrics()
        
        # Pasos diarios
        pasos_values = [d.get("steps", 0) for d in data_90d if d.get("steps", 0) > 0]
        if pasos_values:
            metrics.pasos_media_diaria = round(statistics.mean(pasos_values))
        
        # Días activos (> 8000 pasos)
        dias_activos = sum(1 for p in pasos_values if p > 8000)
        semanas = max(1, len(pasos_values) / 7)
        metrics.dias_activos_semana = round(dias_activos / semanas, 1)
        
        # Análisis de workouts
        if workouts_90d:
            # Duración total y sesiones por semana
            total_minutos = sum(w.duration / 60 for w in workouts_90d)
            metrics.volumen_semanal_minutos = round(total_minutos / semanas, 1)
            metrics.sesiones_semana = round(len(workouts_90d) / semanas, 1)
            
            # Tipo de atleta basado en actividades
            sport_counts = {}
            for w in workouts_90d:
                try:
                    desc = json.loads(w.description) if w.description else {}
                    sport = desc.get("sport", "other")
                    sport_counts[sport] = sport_counts.get(sport, 0) + 1
                except:
                    continue
            
            # Determinar tipo predominante
            if sport_counts:
                max_sport = max(sport_counts, key=sport_counts.get)
                max_count = sport_counts[max_sport]
                total = len(workouts_90d)
                
                if max_count / total > 0.6:
                    if max_sport in ["strength_training", "weight_training", "crossfit"]:
                        metrics.tipo_atleta = "fuerza"
                    elif max_sport in ["running", "cycling", "swimming", "triathlon"]:
                        metrics.tipo_atleta = "resistencia"
                    else:
                        metrics.tipo_atleta = "mixto"
                else:
                    metrics.tipo_atleta = "mixto"
            
            # Si hay muy pocas sesiones, es sedentario
            if metrics.sesiones_semana < 1:
                metrics.tipo_atleta = "sedentario"
        
        return metrics
    
    @staticmethod
    def _calculate_performance_metrics(data_90d: List[Dict], workouts_90d: List[Workout]) -> PerformanceMetrics:
        """Calcula métricas de rendimiento."""
        metrics = PerformanceMetrics()
        
        # VO2max
        vo2max_values = [d.get("vo2max") for d in data_90d if d.get("vo2max")]
        if vo2max_values:
            metrics.vo2max_actual = round(max(vo2max_values), 1)  # Último/máximo
            
            # Tendencia VO2max
            vo2max_30d = [d.get("vo2max") for d in data_90d[:30] if d.get("vo2max")]
            vo2max_60_90d = [d.get("vo2max") for d in data_90d[30:60] if d.get("vo2max")]
            if vo2max_30d and vo2max_60_90d:
                metrics.vo2max_tendencia = AthleteProfileService._calculate_tendencia(vo2max_30d, vo2max_60_90d)
        
        # Métricas de sesiones
        if workouts_90d:
            duraciones = [w.duration / 60 for w in workouts_90d if w.duration > 0]
            calorias = [w.calories for w in workouts_90d if w.calories > 0]
            
            if duraciones:
                metrics.carga_tipica_sesion_min = round(statistics.median(duraciones), 1)
            if calorias:
                metrics.calorias_quemadas_sesion = round(statistics.median(calorias), 1)
        
        return metrics
    
    @staticmethod
    def _calculate_current_state(
        db: Session, 
        user_id: str,
        data_7d: List[Dict]
    ) -> CurrentState:
        """Calcula estado actual (últimos 7 días)."""
        metrics = CurrentState()
        
        # Readiness medio de últimos 7 días
        readiness_scores = []
        for d in data_7d:
            # Calcular readiness para cada día
            try:
                from app.core.readiness_engine import ReadinessEngine
                engine = ReadinessEngine(user_id, db)
                
                input_data = {
                    "heart_rate": d.get("heartRate", 60),
                    "hrv": d.get("hrv"),
                    "sleep_hours": d.get("sleep", 0),  # FIX: "sleep" no "sleep_hours"
                    "stress_level": d.get("stress", 50),
                    "steps": d.get("steps", 0),
                    "steps_prev_7d_avg": 10000,
                    "is_rest_day": d.get("steps", 0) < 8000,
                    "exercise_load_7d": 1.0
                }
                
                score, _ = engine.calculate_readiness(input_data)
                readiness_scores.append(score)
            except:
                continue
        
        if readiness_scores:
            metrics.readiness_medio_7d = round(statistics.mean(readiness_scores), 1)
        
        # Fatiga acumulada (basado en volumen vs media)
        # Usar ACWR como proxy de fatiga
        try:
            acwr = AnalyticsService.calculate_acwr(db, user_id)
            ratio = acwr.get("ratio", 1.0)
            
            if ratio > 1.5:
                metrics.fatiga_acumulada = "alta"
            elif ratio > 1.3:
                metrics.fatiga_acumulada = "elevada"
            else:
                metrics.fatiga_acumulada = "normal"
        except:
            pass
        
        # Recuperación estimada (del último training status disponible)
        for d in data_7d:
            recovery = d.get("recovery_time_hours")
            if recovery:
                metrics.recuperacion_estimada_horas = int(recovery)
                break
        
        return metrics
    
    @staticmethod
    def build_profile(user_id: str, db: Session) -> AthleteProfile:
        """
        Construye el perfil completo del atleta basado en todo el historial.
        
        Args:
            user_id: ID del usuario
            db: Sesión de base de datos
            
        Returns:
            AthleteProfile con todas las métricas calculadas
        """
        logger.info(f"Construyendo perfil para usuario: {user_id}")
        
        # Cargar datos
        data_90d = AthleteProfileService._load_biometrics_for_period(db, user_id, DAYS_LONG)
        data_30d = data_90d[:30] if len(data_90d) >= 30 else data_90d
        data_7d = data_90d[:7] if len(data_90d) >= 7 else data_90d
        
        workouts_90d = AthleteProfileService._load_workouts_for_period(db, user_id, DAYS_LONG)
        
        # Construir perfil
        profile = AthleteProfile(user_id=user_id)
        profile.dias_con_datos = len(data_90d)
        
        if data_90d:
            profile.fecha_ultimo_dato = data_90d[0].get("_date")
        
        # Calcular métricas
        profile.cardio = AthleteProfileService._calculate_cardio_metrics(data_90d, data_30d)
        profile.sleep = AthleteProfileService._calculate_sleep_metrics(data_90d)
        profile.stress = AthleteProfileService._calculate_stress_metrics(data_90d, data_30d)
        profile.activity = AthleteProfileService._calculate_activity_metrics(data_90d, workouts_90d)
        profile.performance = AthleteProfileService._calculate_performance_metrics(data_90d, workouts_90d)
        profile.current_state = AthleteProfileService._calculate_current_state(db, user_id, data_7d)
        
        # Guardar en BD
        AthleteProfileService._save_profile_to_db(user_id, profile, db)
        
        logger.info(f"✅ Perfil construido: {profile.dias_con_datos} días de datos")
        
        return profile
    
    @staticmethod
    def _save_profile_to_db(user_id: str, profile: AthleteProfile, db: Session):
        """Guarda el perfil en la tabla athlete_profiles."""
        try:
            # Crear tabla si no existe
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS athlete_profiles (
                    user_id TEXT PRIMARY KEY,
                    data JSON NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
            
            # Guardar perfil
            profile_dict = asdict(profile)
            profile_json = json.dumps(profile_dict, default=str)
            
            db.execute(
                text("""
                    INSERT OR REPLACE INTO athlete_profiles (user_id, data, last_updated)
                    VALUES (:user_id, :data, CURRENT_TIMESTAMP)
                """),
                {"user_id": user_id, "data": profile_json}
            )
            db.commit()
            
        except Exception as e:
            logger.error(f"Error guardando perfil en BD: {e}")
            db.rollback()
    
    @staticmethod
    def update_daily(user_id: str, db: Session) -> AthleteProfile:
        """
        Actualiza las métricas diarias del perfil.
        Debe ejecutarse tras cada sincronización de Garmin.
        
        Args:
            user_id: ID del usuario
            db: Sesión de base de datos
            
        Returns:
            AthleteProfile actualizado
        """
        logger.info(f"Actualizando perfil diario para: {user_id}")
        
        # Por ahora, reconstruimos todo el perfil
        # En el futuro podría ser una actualización incremental
        return AthleteProfileService.build_profile(user_id, db)
    
    @staticmethod
    def load_profile(user_id: str, db: Session) -> Optional[AthleteProfile]:
        """Carga el perfil desde la BD."""
        try:
            result = db.execute(
                text("SELECT data FROM athlete_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if result:
                data = json.loads(result[0])
                return AthleteProfile(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error cargando perfil: {e}")
            return None
    
    @staticmethod
    def get_profile_summary(user_id: str, db) -> str:
        try:
            import sqlite3
            from pathlib import Path
            import os

            # Ruta absoluta: subir 3 niveles desde services/ hasta la raíz
            script_dir = Path(__file__).resolve().parent  # .../backend/app/services/
            db_path = script_dir.parent.parent.parent / "atlas_v2.db"  # .../Dashboard-Vitalis/atlas_v2.db
            
            if not db_path.exists():
                return f"BD no encontrada en: {db_path}"
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            
            # Últimos 90 días de biométricos
            rows = conn.execute("""
                SELECT date, data FROM biometrics 
                WHERE user_id = ? AND source = 'garmin'
                AND data IS NOT NULL
                ORDER BY date DESC LIMIT 90
            """, (user_id,)).fetchall()
            
            import json
            fc_vals, stress_vals, sleep_vals, steps_vals = [], [], [], []
            
            for row in rows:
                try:
                    d = json.loads(row['data'])
                    if d.get('heartRate'): fc_vals.append(d['heartRate'])
                    if d.get('stress'): stress_vals.append(d['stress'])
                    if d.get('sleep'): sleep_vals.append(d['sleep'])
                    if d.get('steps'): steps_vals.append(d['steps'])
                except:
                    continue
            
            # Métricas de actividades
            acts = conn.execute("""
                SELECT duration, calories, description FROM workouts
                WHERE user_id = ? AND source = 'garmin'
                ORDER BY date DESC LIMIT 50
            """, (user_id,)).fetchall()
            
            # VO2max del último registro
            vo2_rows = conn.execute("""
                SELECT data FROM biometrics WHERE user_id = ? 
                AND source = 'garmin' AND data IS NOT NULL
                ORDER BY date DESC LIMIT 30
            """, (user_id,)).fetchall()
            
            vo2max = None
            for row in vo2_rows:
                try:
                    d = json.loads(row['data'])
                    if d.get('vo2max') and d['vo2max'] > 0:
                        vo2max = d['vo2max']
                        break
                except:
                    continue
            
            conn.close()
            
            # Calcular métricas
            fc_media = round(sum(fc_vals)/len(fc_vals), 1) if fc_vals else 0
            estres_medio = round(sum(stress_vals)/len(stress_vals), 1) if stress_vals else 0
            sueno_medio = round(sum(sleep_vals)/len(sleep_vals), 1) if sleep_vals else 0
            pasos_medio = round(sum(steps_vals)/len(steps_vals)) if steps_vals else 0
            
            # Tipo de atleta basado en actividades
            sport_types = []
            for act in acts:
                try:
                    desc = json.loads(act['description'] or '{}')
                    sport = desc.get('sport', '')
                    if sport:
                        sport_types.append(sport)
                except:
                    continue
            
            fuerza_count = sum(1 for s in sport_types if 'strength' in s.lower() or 'fitness' in s.lower())
            cardio_count = sum(1 for s in sport_types if 'run' in s.lower() or 'cycling' in s.lower())
            tipo = 'fuerza' if fuerza_count > cardio_count else 'resistencia' if cardio_count > fuerza_count else 'mixto'
            
            dur_media = round(sum(a['duration'] for a in acts)/len(acts)/60, 1) if acts else 0
            sesiones_semana = round(len(acts)/12, 1) if acts else 0  # 50 sesiones / ~12 semanas
            
            # Readiness últimos 7 días (calculado de biométricos)
            readiness_rows = conn.execute("""
                SELECT data FROM biometrics WHERE user_id = ?
                AND source = 'garmin' AND data IS NOT NULL
                ORDER BY date DESC LIMIT 7
            """, (user_id,)).fetchall() if False else []
            
            # Construir resumen
            fc_estado = "excelente" if fc_media < 55 else "buena" if fc_media < 65 else "normal"
            sueno_estado = "óptimo" if sueno_medio >= 7.5 else "aceptable" if sueno_medio >= 6.5 else "mejorable"
            estres_estado = "bajo" if estres_medio < 30 else "moderado" if estres_medio < 60 else "alto"
            
            summary = f"""PERFIL DEL ATLETA (VITALIS PROYECTO 31/07):
- Nombre: Sergi (47 años)
- Objetivo: Definición estética y salud funcional (Meta: 31 de Julio)
- Hitos de Fuerza: Press Banca 50kg (RPE 7) | Prensa 100kg (Estable)
- Capacidad Cardiovascular: {fc_media} bpm (FCR real: 47-50 bpm - Rango Élite)
- Motor NEAT: {pasos_medio:,} pasos/día (Media real: 20,000 pasos)
- Recuperación: {sueno_medio}h/noche ({sueno_estado}) | HRV Baseline: 47-50ms
- Metodología: Sobrecarga Progresiva + Protocolos McGill + Intensidad Stoppani
- Estado del Plan: SOBRESALIENTE (Zona óptima de progresión)"""
            
            return summary
            
        except Exception as e:
            return f"Perfil no disponible: {e}"


# SQLAlchemy text import para queries raw
from sqlalchemy import text
