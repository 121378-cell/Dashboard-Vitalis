"""
Script para descargar todos los datos históricos de Garmin
==========================================================

Este script descarga todos los datos disponibles de Garmin Connect
y los almacena en la base de datos para que el coach de Atlas tenga
un contexto completo sobre el usuario.

Ejecución:
    cd backend
    python download_all_garmin_data.py

Características:
- Descarga datos históricos completos (hasta 2 años atrás)
- Maneja rate limiting con reintentos automáticos
- Guarda progreso para continuar si se interrumpe
- Genera resumen de datos descargados para el coach
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from app.models.token import Token
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.utils.garmin import get_garmin_client, safe_get
from datetime import datetime, date, timedelta
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_all_garmin_data")

# Configuración
TEST_USER_ID = "default_user"
MAX_DAYS_BACK = 730  # 2 años de datos históricos
BATCH_SIZE = 30  # Días por lote para evitar rate limiting
DELAY_BETWEEN_REQUESTS = 2.0  # Segundos entre peticiones
DELAY_BETWEEN_BATCHES = 10.0  # Segundos entre lotes


def get_earliest_available_date(client):
    """Determina la fecha más antigua disponible en Garmin."""
    try:
        # Intentar obtener actividades para determinar el rango
        activities = client.get_activities_by_date(
            (date.today() - timedelta(days=MAX_DAYS_BACK)).isoformat(),
            date.today().isoformat()
        )
        
        if activities and len(activities) > 0:
            # Encontrar la fecha más antigua de las actividades
            earliest_date = min(
                datetime.strptime(act["startTimeLocal"], "%Y-%m-%d %H:%M:%S").date()
                for act in activities
            )
            logger.info(f"Fecha más antigua encontrada en actividades: {earliest_date}")
            return earliest_date
        else:
            # Si no hay actividades, usar el máximo permitido
            logger.info("No se encontraron actividades, usando fecha máxima de 2 años")
            return date.today() - timedelta(days=MAX_DAYS_BACK)
            
    except Exception as e:
        logger.warning(f"Error determinando fecha más antigua: {e}")
        return date.today() - timedelta(days=365)  # Fallback: 1 año


def download_all_biometrics(db, user_id, client):
    """Descarga todos los datos biométricos históricos."""
    logger.info("="*60)
    logger.info("DESCARGANDO DATOS BIOMÉTRICOS HISTÓRICOS")
    logger.info("="*60)
    
    # Determinar rango de fechas
    earliest_date = get_earliest_available_date(client)
    end_date = date.today()
    
    logger.info(f"Rango de fechas: {earliest_date} a {end_date}")
    logger.info(f"Total de días: {(end_date - earliest_date).days}")
    
    # Verificar datos ya existentes
    existing_dates = set()
    existing_records = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).all()
    
    for record in existing_records:
        existing_dates.add(record.date)
    
    logger.info(f"Registros ya existentes: {len(existing_dates)}")
    
    # Generar lista de fechas a descargar
    date_range = []
    current_date = earliest_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        if date_str not in existing_dates:
            date_range.append(date_str)
        current_date += timedelta(days=1)
    
    logger.info(f"Fechas a descargar: {len(date_range)}")
    
    if len(date_range) == 0:
        logger.info("✅ Todos los datos biométricos ya están descargados")
        return True
    
    # Descargar en lotes
    success_count = 0
    error_count = 0
    total_batches = (len(date_range) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(total_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(date_range))
        batch_dates = date_range[start_idx:end_idx]
        
        logger.info(f"\nLote {batch_num + 1}/{total_batches}: {len(batch_dates)} días")
        logger.info(f"  Rango: {batch_dates[0]} a {batch_dates[-1]}")
        
        for date_str in batch_dates:
            try:
                logger.info(f"  Descargando {date_str}...")
                
                # Fetch datos
                stats = client.get_stats(date_str)
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                sleep = client.get_sleep_data(date_str)
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                hrv = client.get_hrv_data(date_str)
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                # Body Battery
                body_battery = None
                bb_charged = None
                bb_drained = None
                bb_most_recent = safe_get(stats, "bodyBatteryMostRecentValue")
                bb_at_wake = safe_get(stats, "bodyBatteryAtWakeTime")
                bb_highest = safe_get(stats, "bodyBatteryHighestValue")
                bb_lowest = safe_get(stats, "bodyBatteryLowestValue")
                try:
                    bb = client.get_body_battery(date_str, date_str)
                    if bb and isinstance(bb, list):
                        bb_charged = safe_get(bb[0], "charged")
                        bb_drained = safe_get(bb[0], "drained")
                        if body_battery is None:
                            body_battery = safe_get(bb[0], "charged")
                    time.sleep(1.0)
                except Exception:
                    pass
                if body_battery is None and bb_most_recent is not None:
                    body_battery = bb_most_recent
                
                # Training Readiness
                training_readiness = None
                try:
                    readiness_data = client.get_training_readiness(date_str)
                    if readiness_data and isinstance(readiness_data, dict):
                        training_readiness = safe_get(readiness_data, "overallValue")
                    time.sleep(1.0)
                except Exception:
                    pass
                
                # Training Status
                training_status_data = client.get_training_status(date_str)
                time.sleep(1.0)
                
                # Daily steps
                daily_steps_data = None
                try:
                    daily_steps_data = client.get_daily_steps(date_str, date_str)
                    if daily_steps_data and isinstance(daily_steps_data, list) and len(daily_steps_data) > 0:
                        daily_steps_data = daily_steps_data[0]
                    time.sleep(1.0)
                except Exception:
                    daily_steps_data = None
                
                recovery_time = safe_get(
                    training_status_data,
                    "mostRecentTerminatedTrainingStatus",
                    "recoveryTime",
                ) or safe_get(training_status_data, "recoveryTime")
                
                training_status = safe_get(
                    training_status_data,
                    "mostRecentTerminatedTrainingStatus",
                    "trainingStatus",
                ) or safe_get(training_status_data, "trainingStatus")
                
                # Respiration
                respiration = safe_get(stats, "averageRespirationValue")
                if not respiration:
                    try:
                        resp_data = client.get_respiration_data(date_str)
                        respiration = safe_get(
                            resp_data, "avgWakingRespirationValue"
                        ) or safe_get(resp_data, "avgSleepRespirationValue")
                        time.sleep(1.0)
                    except: respiration = None
                
                # VO2 Max
                vo2max = safe_get(stats, "vo2Max")
                if not vo2max:
                    try:
                        max_metrics = client.get_max_metrics(date_str)
                        for metric in max_metrics or []:
                            vo2max_precise = safe_get(
                                metric, "generic", "vo2MaxPreciseValue"
                            )
                            if vo2max_precise:
                                vo2max = vo2max_precise
                                break
                        time.sleep(1.0)
                    except: vo2max = None
                
                # HRV
                hrv_last_night = safe_get(hrv, "lastNight")
                hrv_val = (
                    safe_get(hrv, "hrvSummary", "weeklyAverage")
                    or safe_get(hrv, "hrvSummary", "lastNightAvg")
                    or safe_get(hrv, "lastNightAvg")
                )
                hrv_status = safe_get(hrv, "hrvSummary", "status")
                
                # Sleep stages
                sleep_dto = safe_get(sleep, "dailySleepDTO", default={})
                sleep_deep_seconds = safe_get(sleep_dto, "deepSleepSeconds")
                sleep_rem_seconds = safe_get(sleep_dto, "remSleepSeconds")
                sleep_light_seconds = safe_get(sleep_dto, "lightSleepSeconds")
                
                sleep_score = (
                    safe_get(sleep_dto, "sleepScores", "overall", "value")
                    or safe_get(sleep_dto, "sleepScores", "totalDuration", "value")
                    or safe_get(sleep, "sleepScores", "overall", "value")
                )
                
                resting_hr_sleep = safe_get(sleep_dto, "restingHeartRate")
                resting_hr_stats = safe_get(stats, "restingHeartRate")
                resting_hr = resting_hr_sleep or resting_hr_stats
                
                # Crear registro
                biometric_data = {
                    "heartRate": resting_hr,
                    "minHeartRate": safe_get(stats, "minHeartRate"),
                    "maxHeartRate": safe_get(stats, "maxHeartRate"),
                    "lastSevenDaysAvgRHR": safe_get(stats, "lastSevenDaysAvgRestingHeartRate"),
                    "hrv": hrv_val,
                    "hrv_lastNight": hrv_last_night,
                    "stress": safe_get(stats, "averageStressLevel"),
                    "maxStress": safe_get(stats, "maxStressLevel"),
                    "lowStressDuration": safe_get(stats, "lowStressDuration"),
                    "mediumStressDuration": safe_get(stats, "mediumStressDuration"),
                    "highStressDuration": safe_get(stats, "highStressDuration"),
                    "sleep": (
                        safe_get(sleep_dto, "sleepTimeSeconds") / 3600
                        if safe_get(sleep_dto, "sleepTimeSeconds")
                        else None
                    ),
                    "sleepScore": sleep_score,
                    "sleepDeepHours": sleep_deep_seconds / 3600 if sleep_deep_seconds else None,
                    "sleepREMHours": sleep_rem_seconds / 3600 if sleep_rem_seconds else None,
                    "sleepLightHours": sleep_light_seconds / 3600 if sleep_light_seconds else None,
                    "sleepDeepSeconds": sleep_deep_seconds,
                    "sleepREMSeconds": sleep_rem_seconds,
                    "sleepLightSeconds": sleep_light_seconds,
                    "sleepingSeconds": safe_get(stats, "sleepingSeconds"),
                    "sleepRestlessMoments": safe_get(sleep_dto, "restlessMomentsCount"),
                    "steps": (
                        safe_get(daily_steps_data, "totalSteps")
                        if daily_steps_data
                        else safe_get(stats, "totalSteps")
                    ),
                    "dailyStepGoal": safe_get(daily_steps_data, "stepGoal")
                    if daily_steps_data
                    else safe_get(stats, "dailyStepGoal"),
                    "calories": safe_get(stats, "wellnessKilocalories")
                    or safe_get(stats, "totalKilocalories")
                    or safe_get(stats, "activeKilocalories")
                    or safe_get(stats, "bmrKilocalories"),
                    "activeSeconds": safe_get(stats, "activeSeconds"),
                    "highlyActiveSeconds": safe_get(stats, "highlyActiveSeconds"),
                    "sedentarySeconds": safe_get(stats, "sedentarySeconds"),
                    "totalDistanceMeters": (
                        safe_get(daily_steps_data, "totalDistance")
                        if daily_steps_data
                        else safe_get(stats, "totalDistanceMeters")
                    ),
                    "floorsAscended": safe_get(stats, "floorsAscended"),
                    "floorsDescended": safe_get(stats, "floorsDescended"),
                    "moderateIntensityMinutes": safe_get(stats, "moderateIntensityMinutes"),
                    "vigorousIntensityMinutes": safe_get(stats, "vigorousIntensityMinutes"),
                    "respiration": respiration,
                    "respirationHighest": safe_get(stats, "highestRespirationValue"),
                    "respirationLowest": safe_get(stats, "lowestRespirationValue"),
                    "spo2": safe_get(stats, "averageSpo2"),
                    "lowestSpo2": safe_get(stats, "lowestSpo2"),
                    "latestSpo2": safe_get(stats, "latestSpo2"),
                    "vo2max": vo2max,
                    "bodyBatteryCharged": bb_charged or safe_get(stats, "bodyBatteryChargedValue"),
                    "bodyBatteryDrained": bb_drained or safe_get(stats, "bodyBatteryDrainedValue"),
                    "bodyBatteryMostRecentValue": (
                        bb_most_recent
                        or safe_get(bb[0], "charged")
                        if (bb and isinstance(bb, list))
                        else safe_get(stats, "bodyBatteryMostRecentValue")
                    ),
                    "bodyBatteryHighestValue": bb_highest,
                    "bodyBatteryLowestValue": bb_lowest,
                    "bodyBatteryDuringSleep": safe_get(stats, "bodyBatteryDuringSleep"),
                    "bodyBatteryAtWakeTime": bb_at_wake,
                }
                
                # Guardar en base de datos
                existing = db.query(Biometrics).filter(
                    Biometrics.user_id == user_id,
                    Biometrics.date == date_str
                ).first()
                
                if not existing:
                    existing = Biometrics(user_id=user_id, date=date_str)
                    db.add(existing)
                
                existing.data = json.dumps(biometric_data)
                existing.source = "garmin"
                existing.recovery_time = recovery_time
                existing.training_status = training_status
                existing.hrv_status = hrv_status
                existing.body_battery = body_battery
                existing.training_readiness = training_readiness
                
                db.commit()
                success_count += 1
                
                if success_count % 10 == 0:
                    logger.info(f"    Progreso: {success_count} días descargados")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"    Error en {date_str}: {error_msg}")
                error_count += 1
                
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning("    Rate limit hit. Esperando 60 segundos...")
                    time.sleep(60)
                    continue
        
        # Pausa entre lotes
        if batch_num < total_batches - 1:
            logger.info(f"  Pausa de {DELAY_BETWEEN_BATCHES} segundos antes del siguiente lote...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    logger.info(f"\n✅ Descarga de biométricos completada")
    logger.info(f"   Éxitos: {success_count}")
    logger.info(f"   Errores: {error_count}")
    
    return True


def download_all_activities(db, user_id, client):
    """Descarga todas las actividades históricas."""
    logger.info("\n" + "="*60)
    logger.info("DESCARGANDO ACTIVIDADES HISTÓRICAS")
    logger.info("="*60)
    
    # Determinar rango de fechas
    earliest_date = get_earliest_available_date(client)
    end_date = date.today()
    
    logger.info(f"Rango de fechas: {earliest_date} a {end_date}")
    
    # Verificar actividades ya existentes
    existing_ids = set()
    existing_activities = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).all()
    
    for act in existing_activities:
        if act.external_id:
            existing_ids.add(act.external_id)
    
    logger.info(f"Actividades ya existentes: {len(existing_ids)}")
    
    try:
        # Descargar todas las actividades
        activities = client.get_activities_by_date(
            earliest_date.isoformat(),
            end_date.isoformat()
        )
        
        logger.info(f"Total de actividades encontradas: {len(activities)}")
        
        new_count = 0
        for act in activities:
            external_id = str(act["activityId"])
            
            if external_id in existing_ids:
                continue
            
            act_date_time = act["startTimeLocal"]
            act_date = act_date_time.split(" ")[0]
            
            metrics = {
                "distance": safe_get(act, "distance"),
                "avgSpeed": safe_get(act, "averageSpeed"),
                "maxSpeed": safe_get(act, "maxSpeed"),
                "avgHR": safe_get(act, "averageHR"),
                "maxHR": safe_get(act, "maxHR"),
                "avgPower": safe_get(act, "avgPower") or safe_get(act, "averagePower"),
                "maxPower": safe_get(act, "maxPower"),
                "avgCadence": safe_get(act, "averageCadence") or safe_get(act, "avgCadence"),
                "hrZones": {
                    "z1": safe_get(act, "hrTimeInZone_1"),
                    "z2": safe_get(act, "hrTimeInZone_2"),
                    "z3": safe_get(act, "hrTimeInZone_3"),
                    "z4": safe_get(act, "hrTimeInZone_4"),
                    "z5": safe_get(act, "hrTimeInZone_5"),
                },
                "elevationGain": safe_get(act, "elevationGain"),
                "sport": safe_get(act, "activityType", "typeKey"),
            }
            
            workout = Workout(
                user_id=user_id,
                source="garmin",
                external_id=external_id,
                name=act.get("activityName") or "Garmin Activity",
                description=json.dumps(metrics),
                date=datetime.strptime(act_date_time, "%Y-%m-%d %H:%M:%S"),
                duration=int(act.get("duration") or 0),
                calories=int(act.get("calories") or 0)
            )
            
            db.add(workout)
            new_count += 1
            
            if new_count % 10 == 0:
                logger.info(f"  Progreso: {new_count} actividades nuevas")
                db.commit()
        
        db.commit()
        logger.info(f"\n✅ Descarga de actividades completada")
        logger.info(f"   Nuevas actividades: {new_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error descargando actividades: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_coach_summary(db, user_id):
    """Genera un resumen de datos para el coach de Atlas."""
    logger.info("\n" + "="*60)
    logger.info("GENERANDO RESUMEN PARA EL COACH DE ATLAS")
    logger.info("="*60)
    
    # Obtener estadísticas de datos
    biometrics_count = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).count()
    
    workouts_count = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).count()
    
    # Rango de fechas
    oldest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.asc()).first()
    
    newest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).first()
    
    # Calcular promedios de métricas clave
    recent_biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).limit(30).all()
    
    avg_sleep = 0
    avg_steps = 0
    avg_hrv = 0
    avg_stress = 0
    avg_rhr = 0
    
    sleep_count = 0
    steps_count = 0
    hrv_count = 0
    stress_count = 0
    rhr_count = 0
    
    for bio in recent_biometrics:
        if bio.data:
            try:
                data = json.loads(bio.data)
                
                if data.get("sleep"):
                    avg_sleep += data["sleep"]
                    sleep_count += 1
                
                if data.get("steps"):
                    avg_steps += data["steps"]
                    steps_count += 1
                
                if data.get("hrv"):
                    avg_hrv += data["hrv"]
                    hrv_count += 1
                
                if data.get("stress"):
                    avg_stress += data["stress"]
                    stress_count += 1
                
                if data.get("heartRate"):
                    avg_rhr += data["heartRate"]
                    rhr_count += 1
                    
            except:
                pass
    
    # Calcular promedios
    avg_sleep = avg_sleep / sleep_count if sleep_count > 0 else 0
    avg_steps = avg_steps / steps_count if steps_count > 0 else 0
    avg_hrv = avg_hrv / hrv_count if hrv_count > 0 else 0
    avg_stress = avg_stress / stress_count if stress_count > 0 else 0
    avg_rhr = avg_rhr / rhr_count if rhr_count > 0 else 0
    
    # Generar resumen
    summary = {
        "user_id": user_id,
        "data_summary": {
            "total_biometrics_records": biometrics_count,
            "total_activities": workouts_count,
            "date_range": {
                "oldest": oldest_biometric.date if oldest_biometric else None,
                "newest": newest_biometric.date if newest_biometric else None,
                "days_covered": (newest_biometric.date - oldest_biometric.date).days if oldest_biometric and newest_biometric else 0
            }
        },
        "recent_averages_30d": {
            "sleep_hours": round(avg_sleep, 2),
            "daily_steps": round(avg_steps, 0),
            "hrv": round(avg_hrv, 1),
            "stress_level": round(avg_stress, 1),
            "resting_heart_rate": round(avg_rhr, 1)
        },
        "data_quality": {
            "sleep_data_available": sleep_count > 0,
            "steps_data_available": steps_count > 0,
            "hrv_data_available": hrv_count > 0,
            "stress_data_available": stress_count > 0,
            "heart_rate_data_available": rhr_count > 0
        }
    }
    
    # Imprimir resumen
    logger.info("\n📊 RESUMEN DE DATOS PARA EL COACH")
    logger.info("="*60)
    logger.info(f"Usuario: {user_id}")
    logger.info(f"\n📈 COBERTURA DE DATOS:")
    logger.info(f"   Registros biométricos: {biometrics_count} días")
    logger.info(f"   Actividades: {workouts_count}")
    logger.info(f"   Rango de fechas: {oldest_biometric.date if oldest_biometric else 'N/A'} a {newest_biometric.date if newest_biometric else 'N/A'}")
    logger.info(f"   Días cubiertos: {(newest_biometric.date - oldest_biometric.date).days if oldest_biometric and newest_biometric else 0}")
    
    logger.info(f"\n📊 PROMEDIOS (ÚLTIMOS 30 DÍAS):")
    logger.info(f"   Sueño: {avg_sleep:.2f} horas/día")
    logger.info(f"   Pasos: {avg_steps:.0f} pasos/día")
    logger.info(f"   HRV: {avg_hrv:.1f} ms")
    logger.info(f"   Estrés: {avg_stress:.1f}/100")
    logger.info(f"   FC reposo: {avg_rhr:.1f} bpm")
    
    logger.info(f"\n✅ CALIDAD DE DATOS:")
    logger.info(f"   Sueño: {'✅' if sleep_count > 0 else '❌'}")
    logger.info(f"   Pasos: {'✅' if steps_count > 0 else '❌'}")
    logger.info(f"   HRV: {'✅' if hrv_count > 0 else '❌'}")
    logger.info(f"   Estrés: {'✅' if stress_count > 0 else '❌'}")
    logger.info(f"   FC: {'✅' if rhr_count > 0 else '❌'}")
    
    # Guardar resumen en archivo
    summary_file = f"coach_summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n💾 Resumen guardado en: {summary_file}")
    
    return summary


def main():
    """Función principal."""
    logger.info("\n" + "="*60)
    logger.info("DESCARGA COMPLETA DE DATOS GARMIN PARA ATLAS COACH")
    logger.info("="*60)
    logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Usuario: {TEST_USER_ID}")
    
    db = SessionLocal()
    try:
        # Obtener credenciales
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if not creds or not creds.garmin_email or not creds.garmin_password:
            logger.error("❌ No se encontraron credenciales de Garmin")
            return 1
        
        logger.info(f"✅ Credenciales encontradas: {creds.garmin_email}")
        
        # Conectar a Garmin
        logger.info("\n🔄 Conectando a Garmin...")
        client, login_result = get_garmin_client(
            email=creds.garmin_email,
            password=creds.garmin_password,
            db=db,
            user_id=TEST_USER_ID
        )
        
        if not client:
            logger.error("❌ Error conectando a Garmin")
            return 1
        
        logger.info("✅ Conectado a Garmin")
        
        # Descargar datos biométricos
        success_biometrics = download_all_biometrics(db, TEST_USER_ID, client)
        
        # Descargar actividades
        success_activities = download_all_activities(db, TEST_USER_ID, client)
        
        # Generar resumen para el coach
        if success_biometrics or success_activities:
            summary = generate_coach_summary(db, TEST_USER_ID)
            
            logger.info("\n" + "="*60)
            logger.info("✅ DESCARGA COMPLETADA EXITOSAMENTE")
            logger.info("="*60)
            logger.info("\n🎉 El coach de Atlas ahora tiene contexto completo sobre:")
            logger.info("   - Historial de salud completo")
            logger.info("   - Patrones de sueño y recuperación")
            logger.info("   - Historial de actividades")
            logger.info("   - Tendencias de HRV y estrés")
            logger.info("   - Niveles de energía (Body Battery)")
            logger.info("\n💡 El coach puede usar estos datos para:")
            logger.info("   - Personalizar recomendaciones de entrenamiento")
            logger.info("   - Detectar patrones de sobreentrenamiento")
            logger.info("   - Optimizar periodización")
            logger.info("   - Ajustar intensidad según recuperación")
            
            return 0
        else:
            logger.error("❌ Error en la descarga de datos")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
