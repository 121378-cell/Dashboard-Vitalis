"""
Verificar progreso de descarga de datos Garmin
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.biometrics import Biometrics

db = SessionLocal()
try:
    count = db.query(Biometrics).filter(Biometrics.user_id == 'default_user').count()
    oldest = db.query(Biometrics).filter(Biometrics.user_id == 'default_user').order_by(Biometrics.date.asc()).first()
    newest = db.query(Biometrics).filter(Biometrics.user_id == 'default_user').order_by(Biometrics.date.desc()).first()
    
    print(f'Registros descargados: {count}')
    print(f'Rango: {oldest.date if oldest else "N/A"} a {newest.date if newest else "N/A"}')
    
    if oldest and newest:
        days_covered = (newest.date - oldest.date).days
        print(f'Días cubiertos: {days_covered}')
        print(f'Progreso: {count / 730 * 100:.1f}%')
finally:
    db.close()
