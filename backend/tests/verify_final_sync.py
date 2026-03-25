import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.api.api_v1.endpoints.sync import sync_garmin
from app.models.biometrics import Biometrics
from app.models.workout import Workout

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_final():
    db = SessionLocal()
    user_id = "default_user"
    print(f"Verifying Garmin sync implementation...")
    try:
        # This will call the Refactored SyncService and use the Refactored Token model
        result = sync_garmin(db, user_id, days=1)
        print(f"✅ Sync Result: {result}")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_final()
