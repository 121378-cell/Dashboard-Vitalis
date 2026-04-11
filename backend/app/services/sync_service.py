import requests
import json
import logging
import random
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.models.workout import Workout
from app.models.token import Token
from app.models.biometrics import Biometrics
from app.utils.garmin import get_garmin_client, safe_get

logger = logging.getLogger("app.services.sync_service")


class SyncService:
    @staticmethod
    def sync_garmin_health(db: Session, user_id: str, date_range: list) -> bool:
        """Fetch Garmin health stats and save to Biometrics table."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not creds:
            logger.warning(f"No credentials found for user {user_id}")
            return False

        # Verificamos que existan las credenciales de Garmin
        garmin_email = creds.garmin_email
        garmin_password = creds.garmin_password

        if not garmin_email or not garmin_password:
            logger.warning(f"No Garmin credentials for user {user_id}")
            return False

        client, login_result = get_garmin_client(email=garmin_email, password=garmin_password)
        if not client:
            # Check if rate limited
            if login_result == "rate_limited":
                raise Exception("Garmin rate limit exceeded. Please try again in 30-60 minutes.")
            return False

        success = True
        for date_str in date_range:
            try:
                # Fetch various stats with fallbacks similar to AI_Fitness
                stats = client.get_stats(date_str)
                sleep = client.get_sleep_data(date_str)
                hrv = client.get_hrv_data(date_str)

                # Recovery and Training Status (often in training status endpoint)
                training_status_data = client.get_training_status(date_str)
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
                    resp_data = client.get_respiration_data(date_str)
                    respiration = safe_get(
                        resp_data, "avgWakingRespirationValue"
                    ) or safe_get(resp_data, "avgSleepRespirationValue")

                # VO2 Max fallback
                vo2max = safe_get(stats, "vo2Max")
                if not vo2max:
                    max_metrics = client.get_max_metrics(date_str)
                    for metric in max_metrics or []:
                        vo2max_precise = safe_get(
                            metric, "generic", "vo2MaxPreciseValue"
                        )
                        if vo2max_precise:
                            vo2max = vo2max_precise
                            break

                # HRV fallback
                hrv_val = (
                    safe_get(hrv, "hrvSummary", "weeklyAverage")
                    or safe_get(hrv, "hrvSummary", "lastNightAvg")
                    or safe_get(hrv, "lastNightAvg")
                )
                hrv_status = safe_get(hrv, "hrvSummary", "status")

                # Combine into a single JSON blob for the 'data' field
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

                # Update or create Biometrics record
                biometric = (
                    db.query(Biometrics)
                    .filter(Biometrics.user_id == user_id, Biometrics.date == date_str)
                    .first()
                )

                if not biometric:
                    biometric = Biometrics(user_id=user_id, date=date_str)
                    db.add(biometric)

                biometric.data = json.dumps(biometric_data)
                biometric.source = "garmin"
                biometric.recovery_time = recovery_time
                biometric.training_status = training_status
                biometric.hrv_status = hrv_status

            except Exception as e:
                logger.error(f"Error syncing Garmin health for {date_str}: {e}")
                success = False

        db.commit()
        return success

    @staticmethod
    def sync_garmin_activities(db: Session, user_id: str, date_range: list) -> bool:
        """Fetch Garmin activities and save to Workouts table with detailed metrics."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not (creds and creds.garmin_email):
            return False

        client, login_result = get_garmin_client(
            email=creds.garmin_email, password=creds.garmin_password
        )
        if not client:
            # Check if rate limited
            if login_result == "rate_limited":
                raise Exception("Garmin rate limit exceeded. Please try again in 30-60 minutes.")
            return False

        try:
            # Fetch activities for the date range
            # Garmin API can fetch by date range, which is more efficient
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

                # Extract detailed metrics like AI_Fitness
                metrics = {
                    "distance": safe_get(act, "distance"),
                    "avgSpeed": safe_get(act, "averageSpeed"),
                    "maxSpeed": safe_get(act, "maxSpeed"),
                    "avgHR": safe_get(act, "averageHR"),
                    "maxHR": safe_get(act, "maxHR"),
                    "avgPower": safe_get(act, "avgPower")
                    or safe_get(act, "averagePower"),
                    "maxPower": safe_get(act, "maxPower"),
                    "avgCadence": safe_get(act, "averageCadence")
                    or safe_get(act, "avgCadence"),
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
                # Store detailed metrics in description as JSON for extensibility
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
                # Use actual workout date from wger API
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

        logger.warning(
            "Hevy integration is not implemented yet. No real data will be synced."
        )
        # Return False to indicate no data was synced
        return False
