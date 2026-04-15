#!/usr/bin/env python3
"""Migración para añadir columnas de Strava a la tabla tokens"""

import sqlite3
import os

def migrate():
    # La BD está en el directorio padre (backend/../atlas.db)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'atlas.db')
    db_path = os.path.abspath(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar si las columnas ya existen
    cursor.execute("PRAGMA table_info(tokens)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = {
        'strava_access_token': 'TEXT',
        'strava_refresh_token': 'TEXT',
        'strava_expires_at': 'DATETIME',
        'strava_athlete_id': 'TEXT',
        'strava_connected': 'TEXT DEFAULT "false"'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            print(f"➕ Añadiendo columna: {col_name}")
            cursor.execute(f"ALTER TABLE tokens ADD COLUMN {col_name} {col_type}")
        else:
            print(f"✅ Columna ya existe: {col_name}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migración completada")

if __name__ == "__main__":
    migrate()
