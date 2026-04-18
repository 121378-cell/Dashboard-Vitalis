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

# Credentials from environment variables
GARMIN_EMAIL = os.environ.get("GARMIN_EMAIL")
GARMIN_PASSWORD = os.environ.get("GARMIN_PASSWORD")
USER_ID = os.environ.get("USER_ID", "default_user")

if not GARMIN_EMAIL or not GARMIN_PASSWORD:
    print("Error: Las variables de entorno GARMIN_EMAIL y GARMIN_PASSWORD son obligatorias.")
    print("Uso: GARMIN_EMAIL=usuario@ejemplo.com GARMIN_PASSWORD=tu_pass python run_sync.py")
    sys.exit(1)

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
    print(f"Usuario creado: {USER_ID}")

# Save credentials
token = db.query(Token).filter(Token.user_id == USER_ID).first()
if not token:
    token = Token(user_id=USER_ID)
    db.add(token)

token.garmin_email = GARMIN_EMAIL
token.garmin_password = GARMIN_PASSWORD
db.commit()
print(f"Credenciales guardadas para {GARMIN_EMAIL}")

# Connect to Garmin
print("\nConectando con Garmin...")
client, login_result = get_garmin_client(
    email=GARMIN_EMAIL, 
    password=GARMIN_PASSWORD, 
    db=db, 
    user_id=USER_ID
)

if not client:
    print(f"Error: No se pudo conectar a Garmin: {login_result}")
    sys.exit(1)

print(f"Conectado a Garmin!")

# Get user profile
try:
    profile = client.get_user_profile()
    print(f"  Usuario: {profile.get('displayName', 'Unknown')}")
except Exception as e:
    print(f"  Aviso: No se pudo obtener el perfil: {e}")

# Sync health data (Last 15 days by default to avoid 429)
print("\nSincronizando datos de salud...")
days_to_sync = 15
if len(sys.argv) > 1:
    try:
        days_to_sync = int(sys.argv[1])
    except ValueError:
        pass

end_date = datetime.now()
start_date = end_date - timedelta(days=days_to_sync)

date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_to_sync + 1)]
print(f"  Fechas: {date_range[-1]} a {date_range[0]} ({len(date_range)} días)")

success = SyncService.sync_garmin_health(db, USER_ID, date_range, client=client)
if success:
    print("Datos de salud sincronizados")
else:
    print("Error o limite de peticiones en sincronización de salud (parcialmente completado)")

# Sync activities (Same range)
print("\nSincronizando actividades...")
date_range_activities = date_range
print(f"  Fechas: {date_range_activities[-1]} a {date_range_activities[0]} ({len(date_range_activities)} días)")

success = SyncService.sync_garmin_activities(db, USER_ID, date_range_activities, client=client)
if success:
    print("Actividades sincronizadas")
else:
    print("Error en sincronización de actividades")

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
