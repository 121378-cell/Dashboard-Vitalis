#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_garmin_to_atlas.py
========================
Sincroniza Garmin -> Atlas (atlas_v2.db) usando las credenciales disponibles.
Maneja automaticamente el login y guarda tokens para futuras ejecuciones.

Uso:
    python sync_garmin_to_atlas.py           # Desde la ultima sync hasta hoy
    python sync_garmin_to_atlas.py --days 7  # Ultimos N dias
    python sync_garmin_to_atlas.py --full    # Ultimos 90 dias
    python sync_garmin_to_atlas.py --today   # Solo hoy y ayer
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR / "backend"
DB_PATH = SCRIPT_DIR / "atlas_v2.db"
LOGS_DIR = BACKEND_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "garmin_atlas_sync.log"

# Directorio donde se guardan los tokens modernos (garmin_tokens.json)
TOKEN_DIR = BACKEND_DIR / ".garth"
TOKEN_FILE = TOKEN_DIR / "garmin_tokens.json"

DEFAULT_USER_ID = "default_user"

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("garmin_atlas_sync")


# ============================================================================
# CONEXION GARMIN
# ============================================================================

def get_credentials_from_db():
    """Lee email y password de atlas_v2.db."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT email, password FROM tokens WHERE user_id = ?",
            (DEFAULT_USER_ID,)
        ).fetchone()
        if row:
            return row["email"], row["password"]
        return None, None
    finally:
        conn.close()


def connect_garmin():
    """
    Conecta a Garmin usando tokens guardados o credenciales.
    Prioridad: garmin_tokens.json -> email+password de BD
    """
    from garminconnect import Garmin

    TOKEN_DIR.mkdir(exist_ok=True)

    # 1. Intentar cargar tokens existentes
    if TOKEN_FILE.exists() and TOKEN_FILE.stat().st_size > 100:
        try:
            logger.info(f"Cargando tokens desde {TOKEN_FILE}...")
            client = Garmin()
            client.login(tokenstore=str(TOKEN_DIR))
            logger.info(f"Sesion restaurada: {client.display_name}")
            return client
        except Exception as e:
            logger.warning(f"Tokens existentes no validos: {e}")
            TOKEN_FILE.unlink(missing_ok=True)

    # 2. Login con credenciales de BD
    email, password = get_credentials_from_db()
    if not email or not password:
        logger.error("Sin credenciales en BD. Establece email/password en la tabla 'tokens'.")
        return None

    logger.info(f"Login con credenciales: {email}...")
    try:
        client = Garmin(email=email, password=password)
        mfa_result = client.login(tokenstore=str(TOKEN_DIR))

        if mfa_result:
            # MFA requerido - solicitar al usuario
            logger.warning("MFA requerido!")
            print("\n" + "=" * 50)
            print("ATENCION: Garmin requiere autenticacion de dos factores (MFA)")
            print("Revisa tu email/app y introduce el codigo:")
            mfa_code = input("Codigo MFA: ").strip()
            client.resume_login(mfa_result, mfa_code)
            logger.info(f"Login con MFA exitoso: {client.display_name}")
        else:
            logger.info(f"Login exitoso: {client.display_name}")

        # Guardar tokens para futuras ejecuciones
        client.garth.dump(str(TOKEN_DIR))
        logger.info(f"Tokens guardados en {TOKEN_FILE}")
        return client

    except Exception as e:
        logger.error(f"Login fallido: {e}")
        return None


# ============================================================================
# SQLITE HELPERS
# ============================================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_last_sync_date():
    conn = get_db()
    try:
        row = conn.execute("SELECT MAX(date) as latest FROM biometrics").fetchone()
        if row and row["latest"]:
            return date.fromisoformat(row["latest"])
        return date.today() - timedelta(days=7)
    finally:
        conn.close()


def safe_get(data, *keys, default=None):
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


# ============================================================================
# SYNC BIOMETRICS
# ============================================================================

def sync_biometrics_for_date(client, user_id: str, date_obj: date) -> bool:
    date_str = date_obj.isoformat()
    try:
        day_data = {"date": date_str, "source": "garmin"}
        recovery_time = None
        training_status = None
        hrv_status = None

        # Stats diarios
        try:
            stats = client.get_stats(date_str)
            if stats:
                day_data.update({k: v for k, v in {
                    "heartRate": safe_get(stats, "restingHeartRate"),
                    "steps": safe_get(stats, "totalSteps"),
                    "calories": safe_get(stats, "totalKilocalories") or safe_get(stats, "activeKilocalories"),
                    "stress": safe_get(stats, "averageStressLevel"),
                    "spo2": safe_get(stats, "averageSpo2") or safe_get(stats, "latestSpo2", "value"),
                    "vo2max": safe_get(stats, "vo2Max"),
                    "respiration": safe_get(stats, "averageRespirationValue"),
                    "bodyBattery": safe_get(stats, "bodyBatteryChargeLevel"),
                }.items() if v is not None})
            time.sleep(1.5)
        except Exception as e:
            logger.debug(f"Stats no disp. {date_str}: {e}")

        # Sueno
        try:
            sleep = client.get_sleep_data(date_str)
            if sleep:
                sleep_secs = safe_get(sleep, "dailySleepDTO", "sleepTimeInSeconds") or 0
                if sleep_secs:
                    day_data.update({k: v for k, v in {
                        "sleep": round(sleep_secs / 3600, 2),
                        "sleep_score": safe_get(sleep, "dailySleepDTO", "sleepScore"),
                        "deep_sleep_seconds": safe_get(sleep, "dailySleepDTO", "deepSleepSeconds"),
                        "rem_sleep_seconds": safe_get(sleep, "dailySleepDTO", "remSleepSeconds"),
                        "light_sleep_seconds": safe_get(sleep, "dailySleepDTO", "lightSleepSeconds"),
                        "awake_sleep_seconds": safe_get(sleep, "dailySleepDTO", "awakeSleepSeconds"),
                    }.items() if v is not None})
            time.sleep(1.5)
        except Exception as e:
            logger.debug(f"Sueno no disp. {date_str}: {e}")

        # HRV
        try:
            hrv = client.get_hrv_data(date_str)
            hrv_val = (
                safe_get(hrv, "hrvSummary", "weeklyAvg")
                or safe_get(hrv, "hrvSummary", "lastNightAvg")
                or safe_get(hrv, "hrvSummary", "weeklyAverage")
            )
            if hrv_val:
                day_data["hrv"] = hrv_val
            hrv_status = safe_get(hrv, "hrvSummary", "status")
            time.sleep(1.5)
        except Exception as e:
            logger.debug(f"HRV no disp. {date_str}: {e}")

        # Training status + recovery
        try:
            ts = client.get_training_status(date_str)
            if ts:
                recovery_time = (
                    safe_get(ts, "mostRecentTerminatedTrainingStatus", "recoveryTime")
                    or safe_get(ts, "recoveryTime")
                )
                training_status = (
                    safe_get(ts, "mostRecentTerminatedTrainingStatus", "trainingStatus")
                    or safe_get(ts, "trainingStatus")
                )
                training_load = (
                    safe_get(ts, "mostRecentTerminatedTrainingStatus", "trainingLoad")
                    or safe_get(ts, "trainingLoad")
                )
                if training_load:
                    day_data["trainingLoad"] = training_load
            time.sleep(1.5)
        except Exception as e:
            logger.debug(f"Training status no disp. {date_str}: {e}")

        # Composicion corporal (solo si hay datos)
        try:
            body = client.get_body_composition(date_str)
            if body:
                weight = safe_get(body, "totalWeight")
                body_fat = safe_get(body, "bodyFat")
                if weight:
                    day_data["weight_kg"] = weight
                if body_fat:
                    day_data["body_fat_percent"] = body_fat
            time.sleep(1.0)
        except Exception as e:
            logger.debug(f"Body comp no disp. {date_str}: {e}")

        # Guardar en BD si hay datos utiles
        useful_fields = {k for k in day_data if k not in ("date", "source")}
        if useful_fields:
            save_biometrics(user_id, date_str, day_data, recovery_time, training_status, hrv_status)
            logger.info(f"  [OK] Biometricos: {date_str} ({len(useful_fields)} campos: {', '.join(list(useful_fields)[:5])}...)")
            return True
        else:
            logger.warning(f"  [SKIP] Sin datos utiles para {date_str}")
            return False

    except Exception as e:
        err = str(e)
        if "429" in err or "Too Many Requests" in err or "rate limit" in err.lower():
            raise  # Propagar para manejo en bucle principal
        logger.error(f"  [ERR] Biometricos {date_str}: {e}")
        return False


def save_biometrics(user_id, date_str, data, recovery_time=None, training_status=None, hrv_status=None):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, data FROM biometrics WHERE user_id = ? AND date = ?",
            (user_id, date_str)
        ).fetchone()

        if existing:
            # Merge datos existentes con nuevos
            existing_data = json.loads(existing["data"]) if existing["data"] else {}
            existing_data.update({k: v for k, v in data.items() if v is not None})
            conn.execute(
                """UPDATE biometrics 
                   SET data = ?, source = 'garmin',
                       recovery_time = COALESCE(?, recovery_time),
                       training_status = COALESCE(?, training_status),
                       hrv_status = COALESCE(?, hrv_status)
                   WHERE id = ?""",
                (json.dumps(existing_data), recovery_time, training_status, hrv_status, existing["id"])
            )
        else:
            conn.execute(
                """INSERT INTO biometrics (user_id, date, data, source, recovery_time, training_status, hrv_status)
                   VALUES (?, ?, ?, 'garmin', ?, ?, ?)""",
                (user_id, date_str, json.dumps(data), recovery_time, training_status, hrv_status)
            )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# SYNC ACTIVITIES
# ============================================================================

def sync_activities_for_range(client, user_id: str, start_date: date, end_date: date) -> int:
    """Sincroniza todas las actividades en un rango de fechas."""
    try:
        logger.info(f"Descargando actividades {start_date} -> {end_date}...")
        activities = client.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat()
        )

        if not activities:
            logger.info("  [INFO] Sin actividades en este rango")
            return 0

        logger.info(f"  [INFO] {len(activities)} actividades encontradas")
        saved = 0
        updated = 0
        conn = get_db()

        try:
            for act in activities:
                external_id = str(act.get("activityId", ""))
                if not external_id:
                    continue

                existing = conn.execute(
                    "SELECT id FROM workouts WHERE user_id = ? AND source = 'garmin' AND external_id = ?",
                    (user_id, external_id)
                ).fetchone()

                metrics = {k: v for k, v in {
                    "distance": safe_get(act, "distance"),
                    "avgSpeed": safe_get(act, "averageSpeed"),
                    "maxSpeed": safe_get(act, "maxSpeed"),
                    "avgHR": safe_get(act, "averageHR"),
                    "maxHR": safe_get(act, "maxHR"),
                    "avgPower": safe_get(act, "avgPower") or safe_get(act, "averagePower"),
                    "avgCadence": safe_get(act, "averageRunningCadenceInStepsPerMinute") or safe_get(act, "averageCadence"),
                    "elevationGain": safe_get(act, "elevationGain"),
                    "sport": (safe_get(act, "sportType", "sportTypeKey")
                              or safe_get(act, "activityType", "typeKey")),
                    "aerobicEffect": safe_get(act, "aerobicTrainingEffect"),
                    "anaerobicEffect": safe_get(act, "anaerobicTrainingEffect"),
                    "trainingLoad": safe_get(act, "activityTrainingLoad"),
                    "hrZones": {
                        "z1": safe_get(act, "hrTimeInZone_1"),
                        "z2": safe_get(act, "hrTimeInZone_2"),
                        "z3": safe_get(act, "hrTimeInZone_3"),
                        "z4": safe_get(act, "hrTimeInZone_4"),
                        "z5": safe_get(act, "hrTimeInZone_5"),
                    }
                }.items() if v is not None}

                name = act.get("activityName") or "Actividad Garmin"
                duration = int(act.get("duration", 0))
                calories = int(act.get("calories", 0))
                start_time_str = act.get("startTimeLocal", "")

                if existing:
                    conn.execute(
                        """UPDATE workouts 
                           SET name = ?, description = ?, date = ?, duration = ?, calories = ?
                           WHERE id = ?""",
                        (name, json.dumps(metrics), start_time_str, duration, calories, existing["id"])
                    )
                    updated += 1
                else:
                    conn.execute(
                        """INSERT INTO workouts (user_id, source, external_id, name, description, date, duration, calories)
                           VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)""",
                        (user_id, external_id, name, json.dumps(metrics), start_time_str, duration, calories)
                    )
                    saved += 1

            conn.commit()
            logger.info(f"  [OK] Actividades: {saved} nuevas, {updated} actualizadas")
            return saved

        finally:
            conn.close()

    except Exception as e:
        err = str(e)
        if "429" in err or "Too Many Requests" in err:
            logger.warning(f"Rate limit en actividades: {e}")
            return 0
        logger.error(f"[ERR] Actividades: {e}")
        return 0


# ============================================================================
# MAIN
# ============================================================================

def run_sync(days=None, full=False, today_only=False):
    logger.info("=" * 65)
    logger.info("ATLAS GARMIN SYNC -- Sincronizacion Garmin -> Atlas")
    logger.info("=" * 65)
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"BD: {DB_PATH}")
    logger.info("=" * 65)

    if not DB_PATH.exists():
        logger.error(f"BD no encontrada: {DB_PATH}")
        return 1

    # Conectar a Garmin
    logger.info("\n[1/4] Conectando a Garmin Connect...")
    client = connect_garmin()
    if not client:
        logger.error("No se pudo conectar a Garmin. Abortando.")
        return 1

    # Calcular rango de fechas
    today = date.today()

    if today_only:
        start_date = today - timedelta(days=1)
        logger.info("Modo: solo hoy y ayer")
    elif full:
        start_date = today - timedelta(days=90)
        logger.info("Modo: ultimos 90 dias (historial completo)")
    elif days:
        start_date = today - timedelta(days=days)
        logger.info(f"Modo: ultimos {days} dias")
    else:
        last_sync = get_last_sync_date()
        # Retroceder 2 dias extra para asegurar datos completos
        start_date = last_sync - timedelta(days=2)
        logger.info(f"Modo: desde ultima sync ({last_sync}) retrocediendo 2 dias de seguridad")

    dates_to_sync = []
    d = start_date
    while d <= today:
        dates_to_sync.append(d)
        d += timedelta(days=1)

    logger.info(f"\n[2/4] Sincronizando BIOMETRICOS ({len(dates_to_sync)} dias: {start_date} -> {today})")
    logger.info("-" * 50)

    bio_ok = 0
    bio_skip = 0
    consecutive_rate_limit = 0

    for i, date_obj in enumerate(dates_to_sync):
        pct = int((i + 1) / len(dates_to_sync) * 100)
        logger.info(f"\n  [{i+1}/{len(dates_to_sync)} - {pct}%] {date_obj.isoformat()}")

        try:
            ok = sync_biometrics_for_date(client, DEFAULT_USER_ID, date_obj)
            if ok:
                bio_ok += 1
            else:
                bio_skip += 1
            consecutive_rate_limit = 0

            # Pausa entre dias para evitar rate limiting
            if i < len(dates_to_sync) - 1:
                time.sleep(3)

        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err or "rate limit" in err.lower():
                consecutive_rate_limit += 1
                wait = 60 * consecutive_rate_limit
                logger.warning(f"  [429] Rate limit! Esperando {wait}s ({consecutive_rate_limit}/3)...")
                time.sleep(wait)
                if consecutive_rate_limit >= 3:
                    logger.error("Rate limit persistente. Parando biometricos para evitar ban.")
                    break
            else:
                logger.error(f"  [ERR] {e}")
                bio_skip += 1

    # Sincronizar actividades
    logger.info(f"\n[3/4] Sincronizando ACTIVIDADES ({start_date} -> {today})")
    logger.info("-" * 50)

    acts_total = 0
    chunk_size = 30  # Chunks de 30 dias
    for i in range(0, len(dates_to_sync), chunk_size):
        chunk = dates_to_sync[i:i + chunk_size]
        chunk_start, chunk_end = chunk[0], chunk[-1]
        logger.info(f"\n  Chunk {i//chunk_size + 1}: {chunk_start} -> {chunk_end}")
        acts_saved = sync_activities_for_range(client, DEFAULT_USER_ID, chunk_start, chunk_end)
        acts_total += acts_saved
        if i + chunk_size < len(dates_to_sync):
            time.sleep(5)

    # Guardar tokens actualizados
    logger.info(f"\n[4/4] Guardando tokens actualizados...")
    try:
        client.garth.dump(str(TOKEN_DIR))
        logger.info(f"  [OK] Tokens guardados en {TOKEN_FILE}")
    except Exception as e:
        logger.warning(f"  No se pudieron guardar tokens: {e}")

    # Resumen final
    logger.info("\n" + "=" * 65)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 65)
    logger.info(f"  Dias procesados: {len(dates_to_sync)}")
    logger.info(f"  Biometricos OK:  {bio_ok}")
    logger.info(f"  Sin datos:       {bio_skip}")
    logger.info(f"  Actividades nuevas: {acts_total}")

    # Estado final BD
    conn = get_db()
    row = conn.execute("SELECT MAX(date) as latest, COUNT(*) as cnt FROM biometrics").fetchone()
    row2 = conn.execute("SELECT COUNT(*) as cnt FROM workouts WHERE source='garmin'").fetchone()
    conn.close()
    logger.info(f"\n  BD Biometricos: {row['cnt']} registros, ultimo: {row['latest']}")
    logger.info(f"  BD Actividades Garmin: {row2['cnt']} registros")
    logger.info("\n*** SINCRONIZACION COMPLETADA! ***")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sincronizar Garmin con Atlas")
    parser.add_argument("--days", type=int, help="Ultimos N dias")
    parser.add_argument("--full", action="store_true", help="Ultimos 90 dias")
    parser.add_argument("--today", action="store_true", help="Solo hoy y ayer")
    args = parser.parse_args()
    sys.exit(run_sync(days=args.days, full=args.full, today_only=args.today))


if __name__ == "__main__":
    main()
