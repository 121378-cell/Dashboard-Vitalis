#!/usr/bin/env python3
"""
Script to sync Garmin data to ATLAS database
"""
import os
import sys
import json
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

# Use existing database session
from app.db.session import SessionLocal
from app.models.token import Token
from app.models.user import User
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.services.sync_service import SyncService
from app.utils.garmin import get_garmin_client

# Credentials
GARMIN_EMAIL = "sergi.marquez.brugal@gmail.com"
GARMIN_PASSWORD = "peluchE-1978.3*"
USER_ID = "default_user"

db = SessionLocal()

print("=" * 60)
print("SINCRONIZACIÓN GARMIN - ATLAS AI")
print("=" * 60)

# Ensure user exists
user = db.query(User).filter(User.id == USER_ID).first()
if not user:
    user = User(id=USER_ID, name="Atleta ATLAS")
    db.add(user)
    db.commit()
    print(f"✅ Usuario creado: {USER_ID}")

# Save credentials
token = db.query(Token).filter(Token.user_id == USER_ID).first()
if not token:
    token = Token(user_id=USER_ID)
    db.add(token)

token.garmin_email = GARMIN_EMAIL
token.garmin_password = GARMIN_PASSWORD
db.commit()
print(f"✅ Credenciales guardadas para {GARMIN_EMAIL}")

# Connect to Garmin
print("\n🔄 Conectando con Garmin...")
client, session_updated = get_garmin_client(GARMIN_EMAIL, GARMIN_PASSWORD)

if not client:
    print("❌ Error: No se pudo conectar a Garmin")
    sys.exit(1)

print(f"✅ Conectado a Garmin!")
if session_updated:
    print("  Session actualizada")

# Get user profile
try:
    profile = client.get_user_profile()
    print(f"  Usuario: {profile.get('displayName', 'Unknown')}")
except:
    pass

# Sync health data (Jan 1, 2025 to today)
print("\n🔄 Sincronizando datos de salud...")
start_date = datetime(2025, 1, 1)
end_date = datetime.now()
date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1)]
print(f"  Fechas: {date_range[-1]} a {date_range[0]} ({len(date_range)} días)")

success = SyncService.sync_garmin_health(db, USER_ID, date_range)
if success:
    print("✅ Datos de salud sincronizados")
else:
    print("⚠️ Error en sincronización de salud")

# Sync activities (Jan 1, 2025 to today)
print("\n🔄 Sincronizando actividades...")
date_range_activities = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1)]
print(f"  Fechas: {date_range_activities[-1]} a {date_range_activities[0]} ({len(date_range_activities)} días)")

success = SyncService.sync_garmin_activities(db, USER_ID, date_range_activities)
if success:
    print("✅ Actividades sincronizadas")
else:
    print("⚠️ Error en sincronización de actividades")

# Show results
print("\n" + "=" * 60)
print("RESULTADOS")
print("=" * 60)

# Biometrics
biometrics = db.query(Biometrics).filter(Biometrics.user_id == USER_ID).order_by(Biometrics.date.desc()).all()
print(f"\n📊 Biometrics: {len(biometrics)} registros")
for b in biometrics[:5]:
    print(f"  {b.date}: {b.source}")

# Workouts
workouts = db.query(Workout).filter(Workout.user_id == USER_ID).order_by(Workout.date.desc()).all()
print(f"\n🏃 Workouts: {len(workouts)} registros")
for w in workouts[:10]:
    print(f"  {w.date}: {w.name} ({w.duration}s, {w.calories} cal)")

db.close()
print("\n✅ Sincronización completada!")
