"""
Verificar estructura de tablas biometrics y workouts
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from sqlalchemy import text

conn = engine.connect()

# Estructura de biometrics
print("=== ESTRUCTURA TABLA BIOMETRICS ===")
result = conn.execute(text('PRAGMA table_info(biometrics)'))
for row in result.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== ESTRUCTURA TABLA WORKOUTS ===")
result = conn.execute(text('PRAGMA table_info(workouts)'))
for row in result.fetchall():
    print(f"  {row[1]}: {row[2]}")

# Verificar algunos datos de ejemplo
print("\n=== EJEMPLO BIOMETRICS ===")
result = conn.execute(text('SELECT * FROM biometrics LIMIT 1'))
row = result.fetchone()
if row:
    print(f"  Datos: {row}")

print("\n=== EJEMPLO WORKOUTS ===")
result = conn.execute(text('SELECT * FROM workouts LIMIT 1'))
row = result.fetchone()
if row:
    print(f"  Datos: {row}")

conn.close()
