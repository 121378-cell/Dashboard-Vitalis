import sys
import os
import json
from datetime import date

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
sys.path.append(backend_path)

from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.models.biometrics import Biometrics

def test_analytics():
    db = SessionLocal()
    user_id = "default_user"
    
    print("--- Testing AnalyticsService ---")
    try:
        # Create some mock data if none exists for testing baselines
        count = db.query(Biometrics).filter(Biometrics.user_id == user_id).count()
        print(f"Current biometrics count for {user_id}: {count}")
        
        # Test Readiness
        readiness = AnalyticsService.get_readiness_score(db, user_id)
        print(f"✅ Readiness Score Result: {readiness}")
        
        # Test Baselines
        hrv_b = AnalyticsService.get_hrv_baseline(db, user_id)
        rhr_b = AnalyticsService.get_rhr_baseline(db, user_id)
        print(f"✅ HRV Baseline: {hrv_b}")
        print(f"✅ RHR Baseline: {rhr_b}")
        
    except Exception as e:
        print(f"❌ Analytics Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_analytics()
