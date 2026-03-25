from sqlalchemy import create_engine, text
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print(f"Updating biometrics schema for {settings.DATABASE_URL}")
    try:
        conn.execute(text("ALTER TABLE biometrics ADD COLUMN recovery_time INTEGER"))
    except Exception as e: print(f"recovery_time: {e}")
    try:
        conn.execute(text("ALTER TABLE biometrics ADD COLUMN training_status VARCHAR"))
    except Exception as e: print(f"training_status: {e}")
    try:
        conn.execute(text("ALTER TABLE biometrics ADD COLUMN hrv_status VARCHAR"))
    except Exception as e: print(f"hrv_status: {e}")
    
    conn.commit()
    print("Biometrics schema update attempt finished.")
