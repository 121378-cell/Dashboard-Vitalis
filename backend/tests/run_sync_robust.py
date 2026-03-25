import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.api.api_v1.endpoints.sync import sync_garmin
from app.models.biometrics import Biometrics
import json

def run_sync():
    db = SessionLocal()
    try:
        user_id = "default_user"
        print(f"Syncing Garmin for {user_id}...")
        result = sync_garmin(db, user_id, days=1)
        print(f"Result: {result}")
        
        # Verify DB
        from datetime import date
        today_str = date.today().isoformat()
        bio = db.query(Biometrics).filter(Biometrics.user_id == user_id, Biometrics.date == today_str).first()
        if bio:
            print(f"DB Data for {today_str}: {bio.data} (Source: {bio.source})")
        else:
            print(f"No data in DB for {today_str}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_sync()
