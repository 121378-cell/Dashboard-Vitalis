#!/usr/bin/env python3
"""
Dashboard-Vitalis — Descarga Histórica Completa de Garmin
===========================================================

Descarga TODOS los datos de Garmin desde 2023-05-01 hasta hoy:
- Estadísticas diarias (FC reposo, pasos, sueño, HRV, etc.)
- Actividades deportivas con métricas completas
- Guarda en atlas_v2.db con reanudación automática

Uso:
    cd backend && python download_full_history.py [--dry-run]

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import garth
from garminconnect import Garmin

# Configuración de BD
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "atlas_v2.db")
DB_PATH = os.path.normpath(DB_PATH)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("download_history")

# Usuario por defecto
DEFAULT_USER_ID = "default_user"

# Fecha de inicio histórica
HISTORICAL_START_DATE = date(2023, 5, 1)

# Delay entre llamadas API (segundos)
API_DELAY_SECONDS = 1


def get_db_connection():
    """Crea conexión sqlite3 a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def connect_garmin() -> Optional[Garmin]:
    """
    Conecta a Garmin usando tokens guardados en .garth/
    NUNCA usa login() con email/password.
    """
    try:
        logger.info("Conectando a Garmin usando tokens locales...")
        garth.resume(".garth")
        
        client = Garmin("dummy", "dummy")
        client.garth = garth.client
        
        # FIX: Asegurar que display_name se establece correctamente
        try:
            client.display_name = garth.client.profile.get("displayName")
            if not client.display_name:
                profile = client.get_user_profile()
                client.display_name = profile.get("displayName") or profile.get("userName")
            logger.info(f"✅ Conectado como: {client.display_name}")
        except Exception as e:
            logger.warning(f"Warning: no se pudo obtener display_name: {e}")
            client.display_name = None
        
        return client
        
    except FileNotFoundError:
        logger.error("❌ No se encontraron tokens en .garth/")
        logger.error("   Copia oauth1_token.json y oauth2_token.json al directorio .garth/")
        return None
    except Exception as e:
        logger.error(f"❌ Error conectando a Garmin: {e}")
        return None


def date_to_str(d: date) -> str:
    """Convierte date a string ISO."""
    return d.isoformat()


def str_to_date(s: str) -> date:
    """Convierte string ISO a date."""
    return datetime.fromisoformat(s).date()


def get_existing_dates(user_id: str) -> set:
    """Obtiene fechas que ya existen en biometrics con source=garmin."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT date FROM biometrics WHERE user_id = ? AND source = 'garmin'",
            (user_id,)
        ).fetchall()
        return {str_to_date(row['date']) for row in rows}
    finally:
        conn.close()


def get_existing_activity_ids(user_id: str) -> set:
    """Obtiene external_ids de actividades ya guardadas."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT external_id FROM workouts WHERE user_id = ? AND source = 'garmin' AND external_id IS NOT NULL",
            (user_id,)
        ).fetchall()
        return {row['external_id'] for row in rows}
    finally:
        conn.close()


def download_day_stats(client: Garmin, date_obj: date) -> Optional[Dict]:
    """
    Descarga estadísticas del día.
    Usa get_stats() si display_name disponible, sino get_user_summary().
    Retorna dict con todas las métricas o None si falla.
    """
    date_str = date_to_str(date_obj)
    
    try:
        # FIX: Usar método apropiado según disponibilidad de display_name
        if client.display_name:
            stats = client.get_stats(date_str)
        else:
            stats = client.get_user_summary(date_str)
        
        # Extraer métricas relevantes
        data = {
            "date": date_str,
            "source": "garmin",
            "heartRate": safe_get(stats, "restingHeartRate") or 0,
            "steps": safe_get(stats, "totalSteps") or 0,
            "calories": safe_get(stats, "totalCalories") or 0,
            "activeCalories": safe_get(stats, "activeCalories") or 0,
            "stress": safe_get(stats, "averageStressLevel") or 0,
            "spo2": safe_get(stats, "latestSpo2", "value") or None,
            "respiration": safe_get(stats, "respiration", "value") or None,
            "vo2max": safe_get(stats, "vo2Max") or None,
            "bodyBattery": safe_get(stats, "bodyBattery", "value") or None,
        }
        
        return data
        
    except Exception as e:
        logger.debug(f"No se pudieron obtener stats para {date_str}: {e}")
        return None


def download_sleep_data(client: Garmin, date_obj: date) -> Optional[Dict]:
    """
    Descarga datos de sueño.
    Retorna dict con métricas de sueño o None.
    """
    date_str = date_to_str(date_obj)
    
    try:
        sleep = client.get_sleep_data(date_str)
        
        if not sleep or "sleepTimeInSeconds" not in str(sleep):
            return None
        
        sleep_time = safe_get(sleep, "dailySleepDTO", "sleepTimeInSeconds") or 0
        
        return {
            "sleep_hours": round(sleep_time / 3600, 2),
            "sleep_score": safe_get(sleep, "dailySleepDTO", "sleepScore") or None,
            "deep_sleep_seconds": safe_get(sleep, "dailySleepDTO", "deepSleepSeconds") or 0,
            "rem_sleep_seconds": safe_get(sleep, "dailySleepDTO", "remSleepSeconds") or 0,
            "light_sleep_seconds": safe_get(sleep, "dailySleepDTO", "lightSleepSeconds") or 0,
            "awake_sleep_seconds": safe_get(sleep, "dailySleepDTO", "awakeSleepSeconds") or 0,
        }
        
    except Exception as e:
        logger.debug(f"No se pudo obtener sueño para {date_str}: {e}")
        return None


def download_hrv_data(client: Garmin, date_obj: date) -> Optional[float]:
    """
    Descarga HRV nocturno.
    Puede ser None en Forerunner 245 u otros sin soporte.
    """
    date_str = date_to_str(date_obj)
    
    try:
        hrv = client.get_hrv_data(date_str)
        
        # El HRV suele estar en hrvSummary o hrvMeasurements
        hrv_value = safe_get(hrv, "hrvSummary", "weeklyAvg") or \
                   safe_get(hrv, "hrvSummary", "lastNightAvg") or \
                   safe_get(hrv, "hrvMeasurements", 0, "hrvValue")
        
        return hrv_value
        
    except Exception as e:
        logger.debug(f"HRV no disponible para {date_str}: {e}")
        return None


def download_body_composition(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga composición corporal (peso, grasa, etc.)."""
    date_str = date_to_str(date_obj)
    
    try:
        body = client.get_body_composition(date_str)
        
        if not body:
            return None
        
        return {
            "weight_kg": safe_get(body, "totalWeight") or None,
            "body_fat_percent": safe_get(body, "bodyFat") or None,
            "muscle_mass_kg": safe_get(body, "muscleMass") or None,
            "bone_mass_kg": safe_get(body, "boneMass") or None,
            "body_water_percent": safe_get(body, "bodyWater") or None,
        }
        
    except Exception as e:
        logger.debug(f"Composición corporal no disponible para {date_str}: {e}")
        return None


def download_training_status(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga estado de entrenamiento y recovery time."""
    date_str = date_to_str(date_obj)
    
    try:
        status = client.get_training_status(date_str)
        
        if not status:
            return None
        
        return {
            "training_status": safe_get(status, "trainingStatus") or None,
            "recovery_time_hours": safe_get(status, "recoveryTime") or None,
            "training_load": safe_get(status, "trainingLoad") or None,
            "vo2max_running": safe_get(status, "vo2MaxRunning") or None,
            "vo2max_cycling": safe_get(status, "vo2MaxCycling") or None,
        }
        
    except Exception as e:
        logger.debug(f"Estado de entrenamiento no disponible para {date_str}: {e}")
        return None


def download_activities_for_date(client: Garmin, date_obj: date) -> List[Dict]:
    """
    Descarga todas las actividades de un día específico.
    Retorna lista de actividades con métricas completas.
    """
    date_str = date_to_str(date_obj)
    
    try:
        # Garmin API usa rango inclusive
        activities = client.get_activities_by_date(date_str, date_str)
        
        if not activities:
            return []
        
        enriched_activities = []
        
        for activity in activities:
            activity_id = activity.get("activityId")
            
            if not activity_id:
                continue
            
            # Enriquecer con detalles si es posible
            try:
                details = client.get_activity_details(activity_id)
                activity["details"] = details
            except:
                activity["details"] = None
            
            enriched_activities.append(activity)
        
        return enriched_activities
        
    except Exception as e:
        logger.debug(f"No se pudieron obtener actividades para {date_str}: {e}")
        return []


def save_biometrics(user_id: str, date_str: str, data: Dict):
    """Guarda o actualiza datos biométricos en la BD usando sqlite3."""
    conn = get_db_connection()
    try:
        # Verificar si ya existe
        existing = conn.execute(
            "SELECT id, data FROM biometrics WHERE user_id = ? AND date = ?",
            (user_id, date_str)
        ).fetchone()
        
        # Extraer campos especiales si existen en los datos
        recovery_time = data.get("recovery_time_hours")
        training_status = data.get("training_status")
        hrv = data.get("hrv")
        
        if existing:
            # Actualizar datos existentes - merge JSON
            existing_data = json.loads(existing['data']) if existing['data'] else {}
            existing_data.update(data)
            conn.execute(
                """UPDATE biometrics 
                   SET data = ?, source = ?, 
                       recovery_time = ?, training_status = ?, hrv_status = ?
                   WHERE id = ?""",
                (json.dumps(existing_data), "garmin",
                 recovery_time, training_status, hrv,
                 existing['id'])
            )
        else:
            # Crear nuevo registro
            conn.execute(
                """INSERT INTO biometrics 
                   (user_id, date, data, source, recovery_time, training_status, hrv_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, date_str, json.dumps(data), "garmin",
                 recovery_time, training_status, hrv)
            )
        
        conn.commit()
        
    finally:
        conn.close()


def save_activity(user_id: str, activity: Dict):
    """Guarda una actividad deportiva en workouts usando sqlite3."""
    external_id = str(activity.get("activityId", ""))
    if not external_id:
        return False
    
    conn = get_db_connection()
    try:
        # Verificar si ya existe
        existing = conn.execute(
            "SELECT id FROM workouts WHERE user_id = ? AND source = 'garmin' AND external_id = ?",
            (user_id, external_id)
        ).fetchone()
        
        # Extraer métricas para JSON
        metrics = {
            "distance": activity.get("distance"),
            "avgSpeed": activity.get("averageSpeed"),
            "maxSpeed": activity.get("maxSpeed"),
            "avgHR": activity.get("averageHR"),
            "maxHR": activity.get("maxHR"),
            "avgPower": activity.get("avgPower"),
            "avgCadence": activity.get("averageRunningCadenceInStepsPerMinute"),
            "elevationGain": activity.get("elevationGain"),
            "sport": safe_get(activity, "sportType", "sportTypeKey"),
            "aerobicEffect": activity.get("aerobicTrainingEffect"),
            "anaerobicEffect": activity.get("anaerobicTrainingEffect"),
            "trainingLoad": activity.get("activityTrainingLoad"),
        }
        
        # Limpiar None values
        metrics = {k: v for k, v in metrics.items() if v is not None}
        
        name = activity.get("activityName", "Actividad Garmin")
        duration = int(activity.get("duration", 0))  # segundos
        calories = int(activity.get("calories", 0))
        start_time = activity.get("startTimeLocal", date_to_str(date.today()))
        
        if existing:
            # Actualizar
            conn.execute(
                """UPDATE workouts 
                   SET name = ?, description = ?, date = ?, duration = ?, calories = ?
                   WHERE id = ?""",
                (name, json.dumps(metrics), start_time, duration, calories,
                 existing['id'])
            )
        else:
            # Insertar
            conn.execute(
                """INSERT INTO workouts 
                   (user_id, source, external_id, name, description, date, duration, calories)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)""",
                (user_id, external_id, name, json.dumps(metrics), start_time, duration, calories)
            )
        
        conn.commit()
        return True
        
    finally:
        conn.close()


def safe_get(data: Dict, *keys, default=None):
    """Navegación segura en diccionarios anidados."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            try:
                data = data[key]
            except (IndexError, TypeError):
                return default
        else:
            return default
    return data if data is not None else default


def download_full_history(dry_run: bool = False, user_id: str = DEFAULT_USER_ID):
    """
    Función principal de descarga histórica.
    
    Args:
        dry_run: Si True, solo simula sin guardar en BD
        user_id: ID del usuario a procesar
    """
    logger.info("=" * 60)
    logger.info("DASHBOARD-VITALIS — DESCARGA HISTÓRICA GARMIN")
    logger.info("=" * 60)
    
    # Conectar a Garmin
    client = connect_garmin()
    if not client:
        logger.error("❌ No se pudo conectar a Garmin. Abortando.")
        return 1
    
    # Calcular rango de fechas
    end_date = date.today()
    start_date = HISTORICAL_START_DATE
    
    total_days = (end_date - start_date).days + 1
    
    logger.info(f"📅 Rango: {start_date} a {end_date} ({total_days} días)")
    
    if dry_run:
        logger.info("🧪 MODO SIMULACIÓN (dry-run): No se guardarán datos")
    
    # Obtener fechas existentes
    existing_dates = get_existing_dates(user_id)
    existing_activities = get_existing_activity_ids(user_id)
    
    logger.info(f"📊 Días ya en BD: {len(existing_dates)}")
    logger.info(f"📊 Actividades ya en BD: {len(existing_activities)}")
    
    # Filtrar fechas pendientes
    all_dates = [start_date + timedelta(days=i) for i in range(total_days)]
    pending_dates = [d for d in all_dates if d not in existing_dates]
    
    logger.info(f"📥 Días pendientes: {len(pending_dates)}")
    
    if dry_run:
        logger.info("✅ Dry-run completado. No se descargaron datos.")
        return 0
    
    # Estadísticas
    stats = {
        "dates_processed": 0,
        "dates_skipped": len(existing_dates),
        "biometrics_saved": 0,
        "activities_found": 0,
        "activities_saved": 0,
        "activities_skipped": 0,
        "errors": 0,
    }
    
    # Procesar cada fecha con su propio bloque try/except
    for idx, date_obj in enumerate(all_dates, 1):
        date_str = date_to_str(date_obj)
        
        # Mostrar progreso cada 10 días
        if idx % 10 == 0 or idx == 1:
            logger.info(f"⏳ Progreso: {date_str} ({idx}/{total_days})")
        
        # Saltar si ya existe
        if date_obj in existing_dates:
            stats["dates_skipped"] += 1
            continue
        
        # FIX: Cada fecha tiene su propio bloque try/except con db.rollback()
        try:
            # Descargar datos del día
            day_data = {}
            
            # 1. Stats básicos
            stats_data = download_day_stats(client, date_obj)
            if stats_data:
                day_data.update(stats_data)
            
            # 2. Sueño
            sleep_data = download_sleep_data(client, date_obj)
            if sleep_data:
                day_data.update(sleep_data)
            
            # 3. HRV
            hrv_value = download_hrv_data(client, date_obj)
            if hrv_value:
                day_data["hrv"] = hrv_value
            
            # 4. Composición corporal
            body_data = download_body_composition(client, date_obj)
            if body_data:
                day_data.update(body_data)
            
            # 5. Estado de entrenamiento
            training_data = download_training_status(client, date_obj)
            if training_data:
                day_data.update(training_data)
            
            # Guardar si tenemos datos
            if day_data:
                save_biometrics(user_id, date_str, day_data)
                stats["biometrics_saved"] += 1
            
            # 6. Actividades
            activities = download_activities_for_date(client, date_obj)
            stats["activities_found"] += len(activities)
            
            for activity in activities:
                activity_id = str(activity.get("activityId", ""))
                
                if activity_id in existing_activities:
                    stats["activities_skipped"] += 1
                    continue
                
                if save_activity(user_id, activity):
                    stats["activities_saved"] += 1
                    existing_activities.add(activity_id)
            
            stats["dates_processed"] += 1
            
            # Delay para no saturar API
            time.sleep(API_DELAY_SECONDS)
            
        except Exception as e:
            # FIX: CRÍTICO - loguear error pero continuar
            logger.error(f"❌ Error procesando {date_str}: {e}")
            stats["errors"] += 1
            continue
    
    # Resumen final
    logger.info("=" * 60)
    logger.info("RESUMEN DE DESCARGA")
    logger.info("=" * 60)
    logger.info(f"✅ Días procesados: {stats['dates_processed']}")
    logger.info(f"⏭️  Días saltados (ya existían): {stats['dates_skipped']}")
    logger.info(f"💾 Registros biométricos guardados: {stats['biometrics_saved']}")
    logger.info(f"🏃 Actividades encontradas: {stats['activities_found']}")
    logger.info(f"💾 Actividades guardadas: {stats['activities_saved']}")
    logger.info(f"⏭️  Actividades saltadas (duplicadas): {stats['activities_skipped']}")
    logger.info(f"❌ Errores: {stats['errors']}")
    logger.info("=" * 60)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Descarga histórica completa de datos Garmin"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin guardar datos (modo de prueba)"
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"ID de usuario (default: {DEFAULT_USER_ID})"
    )
    
    args = parser.parse_args()
    
    return download_full_history(
        dry_run=args.dry_run,
        user_id=args.user_id
    )


if __name__ == "__main__":
    sys.exit(main())
