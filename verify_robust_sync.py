import sys
import os
import logging
from datetime import date, timedelta

# Add absolute backend path to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
if not os.path.exists(backend_path):
    # If already inside or relative, adjust
    if os.path.exists(os.path.join(current_dir, 'app')):
        backend_path = current_dir
    else:
        # Fallback to a wider search
        backend_path = os.path.abspath(os.path.join(current_dir, 'backend'))

sys.path.append(backend_path)
os.chdir(backend_path) # Change to backend to load .env correctly

from app.db.base import *
from app.core.config import settings
from app.models.token import Token
from app.models.user import User
from app.api.api_v1.endpoints.sync import sync_garmin
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)

def run_sync():
    db = SessionLocal()
    user_id = "default_user"
    
    # Check if user and token exist
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, email=settings.GARMIN_EMAIL)
        db.add(user)
    
    token = db.query(Token).filter(Token.user_id == user_id).first()
    if not token:
        token = Token(user_id=user_id)
        db.add(token)
    
    token.garmin_email = settings.GARMIN_EMAIL
    token.garmin_password = settings.GARMIN_PASSWORD
    db.commit()

    print(f"🚀 Running Robust Sync (Inspired by AI_Fitness) for {settings.GARMIN_EMAIL}")
    try:
        # Sync last 3 days to ensure data is caught
        result = sync_garmin(db=db, user_id=user_id, days=3)
        print(f"✅ Sync Result: {result}")
        
        # Verify Biometrics
        from app.models.biometrics import Biometrics
        bio = db.query(Biometrics).filter(Biometrics.user_id == user_id, Biometrics.source == 'garmin').order_by(Biometrics.date.desc()).all()
        print(f"\n📊 Biometrics found: {len(bio)}")
        for b in bio[:2]:
            print(f" - Date: {b.date}, Data: {b.data[:100]}...")

        # Verify Workouts
        from app.models.workout import Workout
        workouts = db.query(Workout).filter(Workout.user_id == user_id, Workout.source == 'garmin').order_by(Workout.date.desc()).all()
        print(f"\n🏃 Workouts found: {len(workouts)}")
        for w in workouts[:3]:
            print(f" - Date: {w.date}, Name: {w.name}, Metrics: {w.description[:100]}...")

    except Exception as e:
        print(f"❌ Sync failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_sync()
