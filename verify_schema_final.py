from sqlalchemy import create_engine, inspect
import os

db_path = 'sqlite:///c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas_v2.db'
engine = create_engine(db_path)
inspector = inspect(engine)

print(f"--- Schema Verification for biometrics table ---")
columns = [c['name'] for c in inspector.get_columns('biometrics')]
print(f"Columns: {columns}")

required_cols = ['recovery_time', 'training_status', 'hrv_status']
missing = [col for col in required_cols if col not in columns]

if not missing:
    print("✅ All new columns are present in the database.")
else:
    print(f"❌ Missing columns: {missing}")

print(f"\n--- Schema Verification for tokens table ---")
token_columns = [c['name'] for c in inspector.get_columns('tokens')]
print(f"Columns: {token_columns}")
if 'garmin_session' in token_columns:
    print("✅ garmin_session column is present.")
else:
    print("❌ garmin_session column is missing.")
