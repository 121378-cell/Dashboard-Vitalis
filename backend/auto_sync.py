#!/usr/bin/env python3
"""
ATLAS Auto Sync — Sincronización Diaria de Garmin
====================================================
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import garth
from garminconnect import Garmin

# ============================================================================
# CONFIGURACIÓN DE RUTAS (absolutas para funcionar desde cualquier directorio)
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent  # .../backend/
PROJECT_ROOT = SCRIPT_DIR.parent  # .../Dashboard-Vitalis/
DB_PATH = PROJECT_ROOT / "atlas_v2.db"
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "auto_sync.log"

# Añadir backend/ al path para imports
sys.path.insert(0, str(SCRIPT_DIR))

# Usuario por defecto
DEFAULT_USER_ID = "default_user"

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("auto_sync")

from app.db.session import SessionLocal
from app.services.athlete_profile_service import AthleteProfileService
from app.services.session_service import SessionService
from app.utils.garmin import get_garmin_client

# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================


def connect_garmin(db: SessionLocal) -> Optional[Garmin]:
    """
    Conecta a Garmin usando la utilidad robusta que soporta persistencia en BD.
    """
    try:
        logger.info("Conectando a Garmin usando persistencia robusta (BD + Disco)...")
        # Obtenemos las credenciales de la BD para el usuario por defecto
        from app.models.token import Token

        creds = db.query(Token).filter(Token.user_id == DEFAULT_USER_ID).first()

        email = creds.garmin_email if creds else None
        password = creds.garmin_password if creds else None

        client, _ = get_garmin_client(
            email=email, password=password, db=db, user_id=DEFAULT_USER_ID
        )

        if client:
            logger.info(f"✅ Conectado exitosamente como: {client.display_name}")
        return client

    except Exception as e:
        logger.error(f"❌ Error conectando a Garmin: {e}")
        return None


# ============================================================================
# FUNCIONES SQLITE PARA SYNC
# ============================================================================


def get_db_connection():
    """Crea conexión sqlite3 a la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def save_biometrics_sqlite(user_id: str, date_str: str, data: Dict):
    """Guarda datos biométricos usando sqlite3 directo."""
    conn = get_db_connection()
    try:
        # Verificar si ya existe
        existing = conn.execute(
            "SELECT id FROM biometrics WHERE user_id = ? AND date = ?",
            (user_id, date_str),
        ).fetchone()

        recovery_time = data.get("recovery_time_hours")
        training_status = data.get("training_status")
        hrv = data.get("hrv")

        if existing:
            # Actualizar datos existentes - merge JSON
            existing_data_row = conn.execute(
                "SELECT data FROM biometrics WHERE id = ?", (existing["id"],)
            ).fetchone()
            existing_data = (
                json.loads(existing_data_row["data"])
                if existing_data_row and existing_data_row["data"]
                else {}
            )
            existing_data.update(data)
            conn.execute(
                """UPDATE biometrics 
                   SET data = ?, source = ?, 
                       recovery_time = ?, training_status = ?, hrv_status = ?
                   WHERE id = ?""",
                (
                    json.dumps(existing_data),
                    "garmin",
                    recovery_time,
                    training_status,
                    hrv,
                    existing["id"],
                ),
            )
        else:
            # Crear nuevo registro
            conn.execute(
                """INSERT INTO biometrics 
                   (user_id, date, data, source, recovery_time, training_status, hrv_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    date_str,
                    json.dumps(data),
                    "garmin",
                    recovery_time,
                    training_status,
                    hrv,
                ),
            )

        conn.commit()

    finally:
        conn.close()


def save_activity_sqlite(user_id: str, activity: Dict):
    """Guarda una actividad en workouts usando sqlite3."""
    external_id = str(activity.get("activityId", ""))
    if not external_id:
        return False

    conn = get_db_connection()
    try:
        # Verificar si ya existe
        existing = conn.execute(
            "SELECT id FROM workouts WHERE user_id = ? AND source = 'garmin' AND external_id = ?",
            (user_id, external_id),
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
            "sport": activity.get("sportType", {}).get("sportTypeKey")
            if activity.get("sportType")
            else None,
            "aerobicEffect": activity.get("aerobicTrainingEffect"),
            "anaerobicEffect": activity.get("anaerobicTrainingEffect"),
            "trainingLoad": activity.get("activityTrainingLoad"),
        }

        # Limpiar None values
        metrics = {k: v for k, v in metrics.items() if v is not None}

        name = activity.get("activityName", "Actividad Garmin")
        duration = int(activity.get("duration", 0))  # segundos
        calories = int(activity.get("calories", 0))
        start_time = activity.get("startTimeLocal", "")

        if existing:
            # Actualizar
            conn.execute(
                """UPDATE workouts 
                   SET name = ?, description = ?, date = ?, duration = ?, calories = ?
                   WHERE id = ?""",
                (
                    name,
                    json.dumps(metrics),
                    start_time,
                    duration,
                    calories,
                    existing["id"],
                ),
            )
        else:
            # Insertar
            conn.execute(
                """INSERT INTO workouts 
                   (user_id, source, external_id, name, description, date, duration, calories)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    external_id,
                    name,
                    json.dumps(metrics),
                    start_time,
                    duration,
                    calories,
                ),
            )

        conn.commit()
        return True

    finally:
        conn.close()


# ============================================================================
# FUNCIONES DE DOWNLOAD
# ============================================================================


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


def download_day_stats(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga estadísticas del día con retry."""
    date_str = date_obj.isoformat()

    try:
        # Verificar rate limit antes de llamar
        time.sleep(0.5)
        stats = client.get_stats(date_str)

        return {
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
    except Exception as e:
        logger.debug(f"No se pudieron obtener stats para {date_str}: {e}")
        return None


def download_sleep_data(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga datos de sueño."""
    date_str = date_obj.isoformat()

    try:
        sleep = client.get_sleep_data(date_str)

        if not sleep or "sleepTimeInSeconds" not in str(sleep):
            return None

        sleep_time = safe_get(sleep, "dailySleepDTO", "sleepTimeInSeconds") or 0

        return {
            "sleep": round(sleep_time / 3600, 2),  # horas
            "sleep_score": safe_get(sleep, "dailySleepDTO", "sleepScore") or None,
            "deep_sleep_seconds": safe_get(sleep, "dailySleepDTO", "deepSleepSeconds")
            or 0,
            "rem_sleep_seconds": safe_get(sleep, "dailySleepDTO", "remSleepSeconds")
            or 0,
            "light_sleep_seconds": safe_get(sleep, "dailySleepDTO", "lightSleepSeconds")
            or 0,
            "awake_sleep_seconds": safe_get(sleep, "dailySleepDTO", "awakeSleepSeconds")
            or 0,
        }
    except Exception as e:
        logger.debug(f"No se pudo obtener sueño para {date_str}: {e}")
        return None


def download_hrv_data(client: Garmin, date_obj: date) -> Optional[float]:
    """Descarga HRV nocturno."""
    date_str = date_obj.isoformat()

    try:
        hrv = client.get_hrv_data(date_str)
        hrv_value = (
            safe_get(hrv, "hrvSummary", "weeklyAvg")
            or safe_get(hrv, "hrvSummary", "lastNightAvg")
            or safe_get(hrv, "hrvMeasurements", 0, "hrvValue")
        )
        return hrv_value
    except Exception as e:
        logger.debug(f"HRV no disponible para {date_str}: {e}")
        return None


def download_body_composition(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga composición corporal."""
    date_str = date_obj.isoformat()

    try:
        body = client.get_body_composition(date_str)
        if not body:
            return None

        return {
            "weight_kg": safe_get(body, "totalWeight") or None,
            "body_fat_percent": safe_get(body, "bodyFat") or None,
            "muscle_mass_kg": safe_get(body, "muscleMass") or None,
        }
    except Exception as e:
        logger.debug(f"Composición corporal no disponible para {date_str}: {e}")
        return None


def download_training_status(client: Garmin, date_obj: date) -> Optional[Dict]:
    """Descarga estado de entrenamiento."""
    date_str = date_obj.isoformat()

    try:
        status = client.get_training_status(date_str)
        if not status:
            return None

        return {
            "training_status": safe_get(status, "trainingStatus") or None,
            "recovery_time_hours": safe_get(status, "recoveryTime") or None,
            "training_load": safe_get(status, "trainingLoad") or None,
            "vo2max_running": safe_get(status, "vo2MaxRunning") or None,
        }
    except Exception as e:
        logger.debug(f"Estado de entrenamiento no disponible para {date_str}: {e}")
        return None


def download_activities_for_date(client: Garmin, date_obj: date) -> List[Dict]:
    """Descarga actividades de un día específico."""
    date_str = date_obj.isoformat()

    try:
        activities = client.get_activities_by_date(date_str, date_str)
        return activities if activities else []
    except Exception as e:
        logger.debug(f"No se pudieron obtener actividades para {date_str}: {e}")
        return []


# ============================================================================
# FUNCIONES PRINCIPALES DE SYNC
# ============================================================================


def sync_biometrics_for_date(client: Garmin, user_id: str, date_obj: date) -> bool:
    """Sincroniza biométricos para una fecha específica con rate limiting."""
    date_str = date_obj.isoformat()

    try:
        day_data = {}
        api_calls = 0

        # Stats básicos
        stats = download_day_stats(client, date_obj)
        if stats:
            day_data.update(stats)
        api_calls += 1
        time.sleep(1.5)  # Delay para evitar 429

        # Sueño
        sleep = download_sleep_data(client, date_obj)
        if sleep:
            day_data.update(sleep)
        api_calls += 1
        time.sleep(1.5)

        # HRV
        hrv = download_hrv_data(client, date_obj)
        if hrv:
            day_data["hrv"] = hrv
        api_calls += 1
        time.sleep(1.5)

        # Composición corporal
        body = download_body_composition(client, date_obj)
        if body:
            day_data.update(body)
        api_calls += 1
        time.sleep(1.5)

        # Estado de entrenamiento
        training = download_training_status(client, date_obj)
        if training:
            day_data.update(training)
        api_calls += 1

        logger.debug(f"API calls for {date_str}: {api_calls}")

        # Guardar si tenemos datos
        if day_data:
            save_biometrics_sqlite(user_id, date_str, day_data)
            logger.info(f"  💾 Biométricos guardados: {date_str}")
            return True
        else:
            logger.info(f"  ⚠️  Sin datos biométricos: {date_str}")
            return False

    except Exception as e:
        logger.error(f"  ❌ Error biométricos {date_str}: {e}")
        return False


def sync_activities_for_date(client: Garmin, user_id: str, date_obj: date) -> int:
    """Sincroniza actividades para una fecha específica. Retorna count guardadas."""
    try:
        activities = download_activities_for_date(client, date_obj)
        saved_count = 0

        for activity in activities:
            if save_activity_sqlite(user_id, activity):
                saved_count += 1

        if saved_count > 0:
            logger.info(
                f"  💾 {saved_count} actividades guardadas: {date_obj.isoformat()}"
            )
        else:
            logger.info(f"  ⚠️  Sin actividades: {date_obj.isoformat()}")

        return saved_count

    except Exception as e:
        logger.error(f"  ❌ Error actividades {date_obj.isoformat()}: {e}")
        return 0


# ============================================================================
# SYNC PRINCIPAL
# ============================================================================


def run_daily_sync(user_id: str = DEFAULT_USER_ID) -> int:
    """
    Ejecuta sincronización diaria de los últimos 2 días.

    Returns:
        0 si éxito, 1 si error
    """
    logger.info("=" * 60)
    logger.info("ATLAS AUTO SYNC — Sincronización Diaria Garmin")
    logger.info("=" * 60)
    logger.info(f"📅 Fecha: {datetime.now().isoformat()}")
    logger.info(f"👤 Usuario: {user_id}")
    logger.info(f"🗄️  BD: {DB_PATH}")
    logger.info("=" * 60)

    # Verificar BD existe
    if not DB_PATH.exists():
        logger.error(f"❌ BD no encontrada: {DB_PATH}")
        return 1

    # Conectar a Garmin
    db = SessionLocal()
    client = None
    try:
        client = connect_garmin(db)
        if not client:
            logger.error("❌ No se pudo conectar a Garmin. Abortando.")
            db.close()
            return 1
    except Exception as e:
        logger.error(f"❌ Error conectando a Garmin: {e}")
        db.close()
        return 1

    # Calcular fechas: hoy y ayer
    today = date.today()
    yesterday = today - timedelta(days=1)
    dates_to_sync = [yesterday, today]

    logger.info(
        f"📅 Sincronizando {len(dates_to_sync)} días: {[d.isoformat() for d in dates_to_sync]}"
    )

    # Estadísticas
    stats = {
        "biometrics_synced": 0,
        "activities_synced": 0,
        "errors": 0,
    }

    # Sincronizar cada día
    for date_obj in dates_to_sync:
        logger.info(f"\n📅 Procesando: {date_obj.isoformat()}")

        # Biométricos
        if sync_biometrics_for_date(client, user_id, date_obj):
            stats["biometrics_synced"] += 1

        # Actividades
        activities_count = sync_activities_for_date(client, user_id, date_obj)
        stats["activities_synced"] += activities_count

    logger.info("\n" + "=" * 60)
    logger.info("ACTUALIZANDO PERFIL DEL ATLETA")
    logger.info("=" * 60)

    # Actualizar perfil del atleta
    try:
        profile = AthleteProfileService.update_daily(user_id, db)
        if profile:
            logger.info(
                f"✅ Perfil actualizado: {profile.dias_con_datos} días de datos"
            )
        else:
            logger.warning("⚠️  Perfil no pudo ser actualizado")
    except Exception as e:
        logger.error(f"❌ Error actualizando perfil: {e}")
        stats["errors"] += 1

    # ============================================================================
    # INTEGRACIÓN CON SISTEMA DE SESIONES
    # ============================================================================
    logger.info("\n" + "=" * 60)
    logger.info("SISTEMA DE SESIONES — PROCESAMIENTO")
    logger.info("=" * 60)

    try:
        # 1. Verificar si debe entrenar hoy
        should_train = SessionService.should_train_today(user_id, db)
        logger.info(
            f"📊 Should train today: {should_train['train']} ({should_train['reason']})"
        )

        # 2. Si debe entrenar y no hay sesión para hoy → generar una
        if should_train["train"]:
            today_str = date.today().isoformat()
            from app.models.session import TrainingSession

            existing_today = (
                db.query(TrainingSession)
                .filter(
                    TrainingSession.user_id == user_id,
                    TrainingSession.date == today_str,
                )
                .first()
            )

            if not existing_today:
                logger.info("📝 Generando sesión para hoy...")
                plan = SessionService.generate_session_plan(user_id, db, date.today())

                session = TrainingSession(
                    user_id=user_id,
                    date=today_str,
                    status="planned",
                    generated_by="atlas",
                    plan_json=json.dumps(plan),
                )
                db.add(session)
                db.commit()
                logger.info(
                    f"✅ Sesión generada: {plan['session_name']} ({plan['estimated_duration_min']} min)"
                )
            else:
                logger.info(f"ℹ️ Ya existe sesión para hoy: {existing_today.id[:8]}")

        # 3. Si hay sesión completada de ayer sin informe → analizarla
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        from app.models.session import TrainingSession

        yesterday_session = (
            db.query(TrainingSession)
            .filter(
                TrainingSession.user_id == user_id,
                TrainingSession.date == yesterday_str,
                TrainingSession.status == "completed",
                TrainingSession.session_report.is_(None),
            )
            .first()
        )

        if yesterday_session:
            logger.info("🔍 Analizando sesión de ayer...")
            report = SessionService.analyze_session(yesterday_session.id, db)
            yesterday_session.session_report = report
            db.commit()
            logger.info("✅ Informe de sesión generado")

        # 4. Si es domingo → generar informe semanal
        if date.today().weekday() == 6:  # Sunday
            logger.info("📅 Es domingo — Generando informe semanal...")
            report_data = SessionService.generate_weekly_report(user_id, db)

            from app.models.session import WeeklyReport

            weekly = WeeklyReport(
                user_id=user_id,
                week_start=report_data["week_start"],
                week_end=report_data["week_end"],
                report_text=report_data["report_text"],
                metrics_json=json.dumps(report_data["metrics"]),
                next_week_plan=json.dumps(report_data["next_week_plan"]),
            )
            db.add(weekly)
            db.commit()
            logger.info("✅ Informe semanal generado y guardado")

    except Exception as e:
        logger.error(f"❌ Error en sistema de sesiones: {e}")
        stats["errors"] += 1

    db.close()

    # Resumen
    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN DE SYNC")
    logger.info("=" * 60)
    logger.info(f"✅ Días biométricos sincronizados: {stats['biometrics_synced']}")
    logger.info(f"✅ Actividades sincronizadas: {stats['activities_synced']}")
    logger.info(f"❌ Errores: {stats['errors']}")

    if stats["errors"] == 0:
        logger.info("\n🎉 Sync completado exitosamente!")
        return 0
    else:
        logger.info(f"\n⚠️  Sync completado con {stats['errors']} errores")
        return 1


def main():
    """Entry point."""
    try:
        exit_code = run_daily_sync()
        sys.exit(exit_code)
    except Exception as e:
        logger.exception(f"❌ Error fatal en auto_sync: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
