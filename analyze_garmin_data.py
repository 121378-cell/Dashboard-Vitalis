import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.db.session import SessionLocal
from app.models.biometrics import Biometrics
from datetime import date, timedelta
from datetime import datetime
import json

db = SessionLocal()

print("=== ANÁLISIS: Datos de Garmin disponibles ===\n")

# Get all biometric records ordered by date
all_records = db.query(Biometrics).filter(
    Biometrics.user_id == "default_user"
).order_by(Biometrics.date.desc()).all()

print(f"Total de registros en BD: {len(all_records)}")

if all_records:
    latest = all_records[0]
    latest_date = datetime.strptime(latest.date, "%Y-%m-%d").date()
    print(f"\nFecha más reciente: {latest.date}")
    print(f"Fuente: {latest.source}")
    print(f"Días desde última sincronización: {(date.today() - latest_date).days}")
    
    # Parse Garmin data
    try:
        data = json.loads(latest.data)
        print(f"\nDatos de Garmin (último registro):")
        print(f"  - Ritmo cardíaco en reposo: {data.get('heartRate')} lpm")
        print(f"  - Pasos: {data.get('steps')}")
        print(f"  - Sueño: {data.get('sleep')} horas")
        print(f"  - Estrés: {data.get('stress')}")
        print(f"  - HRV: {data.get('hrv')}")
        print(f"  - SpO2: {data.get('spo2')}")
        print(f"  - Respiración: {data.get('respiration')}")
        print(f"  - Calorías: {data.get('calories')}")
    except:
        print(f"  Datos crudos: {latest.data[:200]}")

# Check date range
dates = [b.date for b in all_records]
if dates:
    print(f"\nRango de fechas:")
    print(f"  - Inicio: {min(dates)}")
    print(f"  - Fin: {max(dates)}")
    print(f"  - Días con datos: {len(set(dates))}")

# Check if all are Garmin
garmin_count = sum(1 for b in all_records if b.source == "garmin")
hc_count = sum(1 for b in all_records if b.source == "health_connect")
print(f"\nFuentes de datos:")
print(f"  - Garmin: {garmin_count}")
print(f"  - Health Connect: {hc_count}")

# Check last 7 days coverage
today = date.today()
last_7_days = [(today - timedelta(days=i)).isoformat() for i in range(7)]
dates_set = set(dates)
coverage = [d in dates_set for d in last_7_days]
print(f"\nCobertura ultimos 7 dias:")
for d in reversed(last_7_days):
    status = "OK" if d in dates_set else "MISSING"
    print(f"  {d}: {status}")

print("\n=== MÉTRICAS DISPONIBLES EN GARMIN ===")
metrics_sample = {}
for b in all_records[:10]:
    try:
        data = json.loads(b.data)
        metrics_sample.update(data.keys())
    except:
        pass

print(f"Métricas que Garmin proporciona: {sorted(metrics_sample)}")

db.close()