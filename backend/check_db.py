#!/usr/bin/env python3
import sqlite3
import os

# Ruta correcta a la base de datos
db_path = os.path.join(os.path.dirname(__file__), '..', 'atlas.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")
print(f"Existe: {os.path.exists(db_path)}")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar columnas
cursor.execute("PRAGMA table_info(tokens)")
columns = cursor.fetchall()
print("Columnas en tabla tokens:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print()

# Verificar datos
cursor.execute('SELECT user_id, email, LENGTH(password) as pass_len FROM tokens WHERE user_id = "default_user"')
row = cursor.fetchone()
print(f"Datos en default_user: {row}")

conn.close()
