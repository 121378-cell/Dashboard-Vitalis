#!/usr/bin/env python3
"""
Migración de Training Sessions y Weekly Reports
==================================================

Crea las tablas necesarias para el sistema de sesiones de entrenamiento:
- training_sessions
- weekly_reports

Uso:
    cd backend && python session_migration.py

Autor: Dashboard-Vitalis Team
Versión: 1.0.0
"""

import sqlite3
from pathlib import Path


def migrate():
    """Ejecuta la migración de tablas de sesiones."""
    
    # Ruta a la BD
    script_dir = Path(__file__).parent
    db_path = script_dir.parent / "atlas_v2.db"
    
    if not db_path.exists():
        print(f"❌ BD no encontrada: {db_path}")
        return 1
    
    print(f"🗄️  Conectando a: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Crear tabla training_sessions
    print("📊 Creando tabla 'training_sessions'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            generated_by TEXT DEFAULT 'atlas',
            garmin_activity_id TEXT,
            plan_json TEXT,
            actual_json TEXT,
            session_report TEXT,
            garmin_hr_avg REAL,
            garmin_hr_max REAL,
            garmin_calories INTEGER,
            garmin_duration_min REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Crear índices para training_sessions
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON training_sessions(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_date ON training_sessions(date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_garmin_activity ON training_sessions(garmin_activity_id)
    """)
    
    # Crear tabla weekly_reports
    print("📊 Creando tabla 'weekly_reports'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            report_text TEXT,
            metrics_json TEXT,
            next_week_plan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Crear índices para weekly_reports
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_user_id ON weekly_reports(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_week_start ON weekly_reports(week_start)
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Migración completada exitosamente!")
    print("   - Tabla 'training_sessions' creada")
    print("   - Tabla 'weekly_reports' creada")
    print("   - Índices creados")
    
    return 0


if __name__ == "__main__":
    exit(migrate())
