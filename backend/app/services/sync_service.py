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
                # Fetch various stats
                stats = client.get_stats(date_str)
                sleep = client.get_sleep_data(date_str)
                rhr = client.get_rhr_day(date_str)
                hrv = client.get_hrv_data(date_str)
                
                # Combine into a single JSON blob for the 'data' field
                biometric_data = {
                    "heartRate": rhr or 0,
                    "hrv": safe_get(hrv, "hrvSummary", "lastNightAvg") or 0,
                    "stress": safe_get(stats, "averageStressLevel") or 0,
                    "sleep": safe_get(sleep, "dailySleepDTO", "sleepTimeSeconds", default=0) / 3600,
                    "steps": safe_get(stats, "totalSteps") or 0,
                    "calories": safe_get(stats, "totalCalories") or 0,
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
        """Fetch Garmin activities and save to Workouts table."""
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not (creds and creds.garmin_email): return False
        
        client = get_garmin_client(creds.garmin_email, creds.garmin_password)
        if not client: return False

        try:
            # We'll fetch activities for the last N days based on date_range
            # For simplicity, we fetch the last 10 activities and filter by date
            activities = client.get_activities(0, 10)
            for act in activities:
                act_date = act["startTimeLocal"].split(" ")[0]
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
                
                workout.name = act.get("activityName") or "Garmin Activity"
                workout.description = act.get("description") or ""
                workout.date = datetime.strptime(act["startTimeLocal"], "%Y-%m-%d %H:%M:%S")
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
