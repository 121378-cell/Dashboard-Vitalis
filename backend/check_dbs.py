#!/usr/bin/env python3
import sqlite3
import os

for db_name in ['atlas.db', 'atlas_v2.db']:
    path = os.path.join('..', db_name)
    abs_path = os.path.abspath(path)
    
    print(f"\n{'='*50}")
    print(f"Base de datos: {db_name}")
    print(f"Ruta: {abs_path}")
    print(f"Existe: {os.path.exists(abs_path)}")
    
    if os.path.exists(abs_path):
        conn = sqlite3.connect(abs_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id, email FROM tokens WHERE user_id = 'default_user'")
            row = cursor.fetchone()
            if row:
                print(f"DATOS: user_id={row[0]}, email={row[1]}")
            else:
                print("DATOS: No hay registro default_user")
        except Exception as e:
            print(f"ERROR: {e}")
        conn.close()

print("\n" + "="*50)
print("SQLAlchemy config:")
from app.core.config import settings
print(f"DATABASE_URL: {settings.DATABASE_URL}")
