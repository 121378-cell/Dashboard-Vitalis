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
        if not creds or not creds.garmin_email or not creds.garmin_password:
            logger.warning(f"No Garmin credentials for user {user_id}")
            return False

        client = get_garmin_client(creds.garmin_email, creds.garmin_password)
        if not client:
            return False

        success = True
        for date_str in date_range:
            try:
                # Fetch various stats with fallbacks similar to AI_Fitness
                stats = client.get_stats(date_str)
                sleep = client.get_sleep_data(date_str)
                hrv = client.get_hrv_data(date_str)
                
                # Respiration fallback
                respiration = safe_get(stats, "averageRespirationValue")
                if not respiration:
                    resp_data = client.get_respiration_data(date_str)
                    respiration = safe_get(resp_data, "avgWakingRespirationValue") or safe_get(resp_data, "avgSleepRespirationValue")
                
                # VO2 Max fallback
                vo2max = safe_get(stats, "vo2Max")
                if not vo2max:
                    max_metrics = client.get_max_metrics(date_str)
                    for metric in (max_metrics or []):
                        if safe_get(metric, "generic", "vo2MaxPreciseValue"):
                            vo2max = metric["generic"]["vo2MaxPreciseValue"]
                            break
                
                # HRV fallback
                hrv_val = safe_get(hrv, "hrvSummary", "weeklyAverage") or \
                          safe_get(hrv, "hrvSummary", "lastNightAvg") or \
                          safe_get(hrv, "lastNightAvg")
                
                # Combine into a single JSON blob for the 'data' field
                biometric_data = {
                    "heartRate": safe_get(stats, "restingHeartRate") or 0,
                    "hrv": hrv_val or 0,
                    "stress": safe_get(stats, "averageStressLevel") or 0,
                    "sleep": safe_get(sleep, "dailySleepDTO", "sleepTimeSeconds", default=0) / 3600,
                    "sleepScore": safe_get(sleep, "dailySleepDTO", "sleepScores", "overall", "value") or 0,
                    "steps": safe_get(stats, "totalSteps") or 0,
                    "calories": safe_get(stats, "totalCalories") or 0,
                    "respiration": respiration or 0,
                    "vo2max": vo2max or 0,
                    "spo2": safe_get(stats, "averageSpo2") or 98 # Default or from stats
                }
                
                # Update or create Biometrics record
                biometric = db.query(Biometrics).filter(
                    Biometrics.user_id == user_id, 
                    Biometrics.date == date_str
                ).first()
                
                if not biometric:
                    biometric = Biometrics(user_id=user_id, date=date_str)
                    db.add(biometric)
                
                biometric.data = json.dumps(biometric_data)
                biometric.source = "garmin"
                
            except Exception as e:
                logger.error(f"Error syncing Garmin health for {date_str}: {e}")
                success = False
        
        db.commit()
        return success

    @staticmethod
    def sync_garmin_activities(db: Session, user_id: str, date_range: list) -> bool:
        """Fetch Garmin activities and save to Workouts table with detailed metrics."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not (creds and creds.garmin_email): return False
        
        client = get_garmin_client(creds.garmin_email, creds.garmin_password)
        if not client: return False

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
                workout = db.query(Workout).filter(
                    Workout.user_id == user_id,
                    Workout.source == "garmin",
                    Workout.external_id == external_id
                ).first()
                
                if not workout:
                    workout = Workout(
                        user_id=user_id,
                        source="garmin",
                        external_id=external_id
                    )
                    db.add(workout)
                
                # Extract detailed metrics like AI_Fitness
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
                    "sport": safe_get(act, "activityType", "typeKey")
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
                headers={"Authorization": f"Token {creds.wger_api_key}"}
            )
            response.raise_for_status()
            workouts = response.json().get("results", [])
            for workout_data in workouts:
                external_id = str(workout_data["id"])
                workout = db.query(Workout).filter(
                    Workout.user_id == user_id,
                    Workout.source == "wger",
                    Workout.external_id == external_id
                ).first()
                if not workout:
                    workout = Workout(user_id=user_id, source="wger", external_id=external_id)
                    db.add(workout)
                workout.name = workout_data.get("comment") or "Wger Workout"
                workout.description = workout_data.get("description") or ""
                workout.date = datetime.now()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Wger sync failed: {e}")
            return False

    @staticmethod
    def sync_hevy_workouts(db: Session, user_id: str) -> bool:
        """Mock Hevy sync."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not creds or not creds.hevy_username:
            return False
        try:
            external_id = f"hevy_mock_{random.randint(1000, 9999)}"
            workout = Workout(
                user_id=user_id, source="hevy", external_id=external_id,
                name="Hevy Strength Session (Mock)", 
                description="Push/Pull/Legs",
                date=datetime.now(), duration=3600, calories=450
            )
            db.add(workout)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Hevy mock sync failed: {e}")
            return False
