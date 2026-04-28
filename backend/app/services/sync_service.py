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
        three_days_ago = (date.today() - timedelta(days=3)).isoformat()

        success = True
        consecutive_errors = 0
        
        for date_str in date_range:
            # Skip if already exists and not recent (avoid redundant API calls)
            existing = db.query(Biometrics).filter(
                Biometrics.user_id == user_id, 
                Biometrics.date == date_str
            ).first()
            
            if existing and date_str < three_days_ago:
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

                # Recovery and Training Status
                training_status_data = client.get_training_status(date_str)
                time.sleep(1.0) # Delay adicional
                
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
                    except: respiration = None

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
                    except: vo2max = None

                # HRV fallback
                hrv_val = (
                    safe_get(hrv, "hrvSummary", "weeklyAverage")
                    or safe_get(hrv, "hrvSummary", "lastNightAvg")
                    or safe_get(hrv, "lastNightAvg")
                )
                hrv_status = safe_get(hrv, "hrvSummary", "status")

                biometric_data = {
                    "heartRate": safe_get(stats, "restingHeartRate"),
                    "hrv": hrv_val,
                    "stress": safe_get(stats, "averageStressLevel"),
                    "sleep": safe_get(sleep, "dailySleepDTO", "sleepTimeSeconds") / 3600
                    if safe_get(sleep, "dailySleepDTO", "sleepTimeSeconds")
                    else None,
                    "sleepScore": safe_get(
                        sleep, "dailySleepDTO", "sleepScores", "overall", "value"
                    ),
                    "steps": safe_get(stats, "totalSteps"),
                    "calories": (
                        safe_get(stats, "totalKilocalories")
                        or safe_get(stats, "activeKilocalories")
                        or safe_get(stats, "bmrKilocalories")
                    ),
                    "respiration": respiration,
                    "vo2max": vo2max,
                    "spo2": safe_get(stats, "averageSpo2"),
                }

                if not existing:
                    existing = Biometrics(user_id=user_id, date=date_str)
                    db.add(existing)

                existing.data = json.dumps(biometric_data)
                existing.source = "garmin"
                existing.recovery_time = recovery_time
                existing.training_status = training_status
                existing.hrv_status = hrv_status
                
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
                    except:
                        pass
                
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
                # Don't fail the sync if memory generation fails
                pass

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
