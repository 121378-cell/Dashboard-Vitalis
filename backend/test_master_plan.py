import os
import sys
from datetime import date
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.master_plan_service import MasterPlanService
import traceback
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
try:
    print("Testing create_master_plan...")
    result = MasterPlanService.create_master_plan(
        db=db,
        user_id="default_user",
        goal="Correr una maratón en 3 horas",
        target_date=date(2026, 12, 31),
        preferred_days=["monday", "tuesday", "thursday", "saturday"],
        time_per_session_minutes=90,
        intensity_preference="high",
        restrictions="Ninguna"
    )
    print("SUCCESS!")
    print(result["master_plan"]["title"])
except Exception as e:
    print("\n--- ERROR ---")
    traceback.print_exc()
finally:
    db.close()
