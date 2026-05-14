import requests
import json
import logging
import random
import time
from datetime import datetime, date, timedelta
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.workout import Workout
from app.models.token import Token
from app.models.biometrics import Biometrics
from app.utils.garmin import get_garmin_client, safe_get
from app.services.memory_service import MemoryService

logger = logging.getLogger("app.services.sync_service")


class SyncService:
    @staticmethod
    def sync_garmin_health(db: Session, user_id: str, date_range: list, client: Optional[Any] = None) -> bool:
        """Fetch Garmin health stats and save to Biometrics table."""
        if not client:
            creds = db.query(Token).filter(Token.user_id == user_id).first()
            if not creds or not creds.garmin_email or not creds.garmin_password:
                logger.warning(f"No Garmin credentials for user {user_id}")
                return False

            client, login_result = get_garmin_client(
                email=creds.garmin_email, 
                password=creds.garmin_password,
                db=db,
                user_id=user_id
            )
            if not client:
                if login_result == "rate_limited":
                    raise Exception(
                        "Garmin ha bloqueado la sincronizacion automatica (rate limit persistente). "
                        "Soluciones: 1) Exporta manualmente desde https://connect.garmin.com/modern/export "
                        "2) Espera 48-72h sin intentar login 3) Usa Strava como intermediario"
                    )
                return False

        today = date.today().isoformat()
        three_days_ago = date.today() - timedelta(days=3)

        success = True
        consecutive_errors = 0
        
        for date_str in date_range:
            # Skip if already exists and not recent (avoid redundant API calls)
            existing = db.query(Biometrics).filter(
                Biometrics.user_id == user_id, 
                Biometrics.date == date_str
            ).first()
            
            if existing and date.fromisoformat(date_str) < three_days_ago:
                logger.info(f"Skipping stable date: {date_str}")
                continue

            try:
                logger.info(f"Fetching health data for {date_str}...")
                
                # Fetch various stats with fallbacks
                stats = client.get_stats(date_str)
                time.sleep(2.0)  # Aumentado para evitar 429
                
                sleep = client.get_sleep_data(date_str)
                time.sleep(2.0)
                
                hrv = client.get_hrv_data(date_str)
                time.sleep(2.0)

                # Body Battery - use stats for daily totals + body_battery time series for current level
                body_battery = None
                bb_charged = None
                bb_drained = None
                bb_most_recent = safe_get(stats, "bodyBatteryMostRecentValue")
                bb_at_wake = safe_get(stats, "bodyBatteryAtWakeTime")
                bb_highest = safe_get(stats, "bodyBatteryHighestValue")
                bb_lowest = safe_get(stats, "bodyBatteryLowestValue")
                bb = None  # Initialize bb to None to avoid NameError if try block fails
                try:
                    bb = client.get_body_battery(date_str, date_str)
                    if bb and isinstance(bb, list):
                        bb_charged = safe_get(bb[0], "charged")
                        bb_drained = safe_get(bb[0], "drained")
                        if body_battery is None:
                            body_battery = safe_get(bb[0], "charged")
                        time.sleep(1.0)
                except Exception as e:
                    logger.debug(f"Body Battery fetch failed for {date_str}: {e}")
                if body_battery is None and bb_most_recent is not None:
                    body_battery = bb_most_recent

                # Training Readiness (Garmin's composite score - daily endpoint)
                training_readiness = None
                try:
                    readiness_data = client.get_training_readiness(date_str)
                    if readiness_data and isinstance(readiness_data, dict):
                        training_readiness = safe_get(readiness_data, "overallValue")
                        time.sleep(1.0)
                except Exception as e:
                    logger.debug(f"Training Readiness fetch failed for {date_str}: {e}")

                # Recovery and Training Status
                training_status_data = client.get_training_status(date_str)
                time.sleep(1.0)

                # Daily steps - more reliable than get_stats for same-day
                daily_steps_data = None
                try:
                    daily_steps_data = client.get_daily_steps(date_str, date_str)
                    if daily_steps_data and isinstance(daily_steps_data, list) and len(daily_steps_data) > 0:
                        daily_steps_data = daily_steps_data[0]
                        time.sleep(1.0)
                except Exception as e:
                    logger.debug(f"Daily steps fetch failed for {date_str}: {e}")
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

                # Respiration fallback
                respiration = safe_get(stats, "averageRespirationValue")
                if not respiration:
                    try:
                        resp_data = client.get_respiration_data(date_str)
                        respiration = safe_get(
                            resp_data, "avgWakingRespirationValue"
                        ) or safe_get(resp_data, "avgSleepRespirationValue")
                        time.sleep(1.0)
                    except Exception as e:
                        logger.debug(f"Respiration data fetch failed for {date_str}: {e}")
                        respiration = None

                # VO2 Max fallback
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
                    except Exception as e:
                        logger.debug(f"VO2 Max fetch failed for {date_str}: {e}")
                        vo2max = None

                # HRV nightly detail (lastNight) — more granular than weekly average
                hrv_last_night = safe_get(hrv, "lastNight")
                hrv_val = (
                    safe_get(hrv, "hrvSummary", "weeklyAverage")
                    or safe_get(hrv, "hrvSummary", "lastNightAvg")
                    or safe_get(hrv, "lastNightAvg")
                )
                hrv_status = safe_get(hrv, "hrvSummary", "status")

                # Sleep stages (deep, REM, light) from sleep data
                sleep_dto = safe_get(sleep, "dailySleepDTO", default={})
                sleep_deep_seconds = safe_get(sleep_dto, "deepSleepSeconds")
                sleep_rem_seconds = safe_get(sleep_dto, "remSleepSeconds")
                sleep_light_seconds = safe_get(sleep_dto, "lightSleepSeconds")
                sleep_rem_data = safe_get(sleep, "remSleepData", default={})
                sleep_levels = safe_get(sleep, "sleepLevels", default={})

                # Sleep score - check multiple possible paths
                sleep_score = (
                    safe_get(sleep_dto, "sleepScores", "overall", "value")
                    or safe_get(sleep_dto, "sleepScores", "totalDuration", "value")
                    or safe_get(sleep, "sleepScores", "overall", "value")
                )

                # Resting heart rate from sleep (most accurate, measured during sleep)
                resting_hr_sleep = safe_get(sleep_dto, "restingHeartRate")
                resting_hr_stats = safe_get(stats, "restingHeartRate")
                resting_hr = resting_hr_sleep or resting_hr_stats

                biometric_data = {
                    # Heart rate
                    "heartRate": resting_hr,
                    "minHeartRate": safe_get(stats, "minHeartRate"),
                    "maxHeartRate": safe_get(stats, "maxHeartRate"),
                    "lastSevenDaysAvgRHR": safe_get(stats, "lastSevenDaysAvgRestingHeartRate"),

                    # HRV
                    "hrv": hrv_val,
                    "hrv_lastNight": hrv_last_night,

                    # Stress
                    "stress": safe_get(stats, "averageStressLevel"),
                    "maxStress": safe_get(stats, "maxStressLevel"),
                    "lowStressDuration": safe_get(stats, "lowStressDuration"),
                    "mediumStressDuration": safe_get(stats, "mediumStressDuration"),
                    "highStressDuration": safe_get(stats, "highStressDuration"),

                    # Sleep - primary
                    "sleep": (
                        safe_get(sleep_dto, "sleepTimeSeconds") / 3600
                        if safe_get(sleep_dto, "sleepTimeSeconds")
                        else None
                    ),
                    "sleepScore": sleep_score,
                    "sleepDeepHours": sleep_deep_seconds / 3600 if sleep_deep_seconds else None,
                    "sleepREMHours": sleep_rem_seconds / 3600 if sleep_rem_seconds else None,
                    "sleepLightHours": sleep_light_seconds / 3600 if sleep_light_seconds else None,
                    # Sleep time breakdown (seconds stored too)
                    "sleepDeepSeconds": sleep_deep_seconds,
                    "sleepREMSeconds": sleep_rem_seconds,
                    "sleepLightSeconds": sleep_light_seconds,
                    "sleepingSeconds": safe_get(stats, "sleepingSeconds"),
                    "sleepRestlessMoments": safe_get(sleep_dto, "restlessMomentsCount"),

                    # Activity - use get_daily_steps as primary (more accurate for same-day)
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

                    # Respiratory
                    "respiration": respiration,
                    "respirationHighest": safe_get(stats, "highestRespirationValue"),
                    "respirationLowest": safe_get(stats, "lowestRespirationValue"),

                    # SpO2
                    "spo2": safe_get(stats, "averageSpo2"),
                    "lowestSpo2": safe_get(stats, "lowestSpo2"),
                    "latestSpo2": safe_get(stats, "latestSpo2"),

                    # VO2 Max
                    "vo2max": vo2max,

                    # Body battery - daily totals from get_body_battery + stats summary
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
                
                db.commit() # Commit after each day to save progress
                consecutive_errors = 0

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error syncing Garmin health for {date_str}: {error_msg}")
                
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning("Rate limit hit. Breaking loop to save progress.")
                    success = False
                    break
                
                consecutive_errors += 1
                if consecutive_errors > 5:
                    logger.error("Too many consecutive errors. Aborting.")
                    success = False
                    break
                
                success = False

        # After successful sync, trigger Memory Engine pattern detection
        if success:
            try:
                # Get recent biometrics for pattern detection (last 30 days)
                cutoff = (date.today() - timedelta(days=30)).isoformat()
                recent_biometrics = db.query(Biometrics).filter(
                    Biometrics.user_id == user_id,
                    Biometrics.date >= cutoff
                ).order_by(Biometrics.date.desc()).all()
                
                # Get recent workouts for pattern detection
                recent_workouts = db.query(Workout).filter(
                    Workout.user_id == user_id,
                    Workout.source == "garmin",
                    Workout.date >= datetime.strptime(cutoff, "%Y-%m-%d")
                ).order_by(Workout.date.desc()).limit(20).all()
                
                # Convert workouts to dict format
                workouts_data = []
                for w in recent_workouts:
                    workouts_data.append({
                        "duration": w.duration or 0,
                        "calories": w.calories or 0,
                        "date": w.date.isoformat() if w.date else None
                    })
                
                # Get latest biometrics data for today
                latest_biometrics = None
                if recent_biometrics:
                    try:
                        data = json.loads(recent_biometrics[0].data) if recent_biometrics[0].data else {}
                        latest_biometrics = {
                            "steps": data.get("steps"),
                            "sleep": data.get("sleep"),
                            "hrv": data.get("hrv")
                        }
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug(f"Memory Engine: Failed to parse biometric data: {e}")
                
                # Auto-generate memories
                memories = MemoryService.auto_generate_from_sync(
                    db=db,
                    user_id=user_id,
                    biometrics_data=latest_biometrics,
                    workouts_data=workouts_data,
                    recent_biometrics=recent_biometrics
                )
                
                if memories:
                    logger.info(f"Memory Engine: Generated {len(memories)} new memories for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Memory Engine error during sync: {e}")

        return success

    @staticmethod
    def sync_garmin_activities(db: Session, user_id: str, date_range: list, client: Optional[Any] = None) -> bool:
        """Fetch Garmin activities and save to Workouts table."""
        if not client:
            creds = db.query(Token).filter(Token.user_id == user_id).first()
            if not (creds and creds.garmin_email):
                return False

            client, login_result = get_garmin_client(
                email=creds.garmin_email, 
                password=creds.garmin_password,
                db=db,
                user_id=user_id
            )
            if not client:
                if login_result == "rate_limited":
                    raise Exception(
                        "Garmin ha bloqueado la sincronizacion automatica (rate limit persistente). "
                        "Soluciones: 1) Exporta manualmente desde https://connect.garmin.com/modern/export "
                        "2) Espera 48-72h sin intentar login 3) Usa Strava como intermediario"
                    )
                return False

        try:
            start_date = min(date_range)
            end_date = max(date_range)
            activities = client.get_activities_by_date(start_date, end_date)

            for act in activities:
                act_date_time = act["startTimeLocal"]
                act_date = act_date_time.split(" ")[0]
                if act_date not in date_range:
                    continue

                external_id = str(act["activityId"])
                workout = (
                    db.query(Workout)
                    .filter(
                        Workout.user_id == user_id,
                        Workout.source == "garmin",
                        Workout.external_id == external_id,
                    )
                    .first()
                )

                if not workout:
                    workout = Workout(
                        user_id=user_id, source="garmin", external_id=external_id
                    )
                    db.add(workout)

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

                workout.name = act.get("activityName") or "Garmin Activity"
                workout.description = json.dumps(metrics)
                workout.date = datetime.strptime(act_date_time, "%Y-%m-%d %H:%M:%S")
                workout.duration = int(act.get("duration") or 0)
                workout.calories = int(act.get("calories") or 0)

            db.commit()
            return True
        except Exception as e:
            logger.error(f"Garmin activity sync failed: {e}")
            return False

    @staticmethod
    def sync_wger_workouts(db: Session, user_id: str) -> bool:
        """Fetch Wger workouts and save to Workouts table."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not creds or not creds.wger_api_key:
            return False

        try:
            response = requests.get(
                "https://wger.de/api/v2/workout/",
                headers={"Authorization": f"Token {creds.wger_api_key}"},
            )
            response.raise_for_status()
            workouts = response.json().get("results", [])
            for workout_data in workouts:
                external_id = str(workout_data["id"])
                workout = (
                    db.query(Workout)
                    .filter(
                        Workout.user_id == user_id,
                        Workout.source == "wger",
                        Workout.external_id == external_id,
                    )
                    .first()
                )
                if not workout:
                    workout = Workout(
                        user_id=user_id, source="wger", external_id=external_id
                    )
                    db.add(workout)
                workout.name = workout_data.get("comment") or "Wger Workout"
                workout.description = workout_data.get("description") or ""
                if workout_data.get("creation_date"):
                    workout.date = datetime.strptime(
                        workout_data["creation_date"], "%Y-%m-%d"
                    )
                else:
                    workout.date = datetime.now()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Wger sync failed: {e}")
            return False

    @staticmethod
    def sync_hevy_workouts(db: Session, user_id: str) -> bool:
        """Hevy sync - Not implemented yet."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not creds or not creds.hevy_username:
            return False
        logger.warning("Hevy integration is not implemented yet.")
        return False
