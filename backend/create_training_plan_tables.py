"""
Create Training Plan Tables
============================

Script para crear las tablas del sistema de planes de entrenamiento en la base de datos existente.

Ejecución:
    cd backend
    python create_training_plan_tables.py
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from sqlalchemy import text

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("CREACIÓN DE TABLAS DE TRAINING PLANS")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Crear tabla adaptive_training_plans
        print("\n🔄 Creando tabla adaptive_training_plans...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS adaptive_training_plans (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL DEFAULT 'default_user',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              week_start_date DATE NOT NULL,
              week_end_date DATE NOT NULL,
              goal TEXT NOT NULL,
              status TEXT DEFAULT 'active',
              plan_json TEXT NOT NULL,
              ai_reasoning TEXT,
              fitness_snapshot TEXT
            )
        """))
        print("✅ Tabla adaptive_training_plans creada")
        
        # Crear tabla adaptive_planned_sessions
        print("\n🔄 Creando tabla adaptive_planned_sessions...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS adaptive_planned_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              plan_id INTEGER REFERENCES adaptive_training_plans(id),
              session_date DATE NOT NULL,
              day_of_week TEXT NOT NULL,
              session_type TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              duration_minutes INTEGER,
              intensity TEXT,
              exercises_json TEXT,
              running_details_json TEXT,
              completed BOOLEAN DEFAULT 0,
              garmin_activity_id TEXT,
              user_notes TEXT,
              modified_by_user BOOLEAN DEFAULT 0,
              adaptation_reason TEXT
            )
        """))
        print("✅ Tabla adaptive_planned_sessions creada")
        
        # Crear tabla adaptive_plan_adjustments
        print("\n🔄 Creando tabla adaptive_plan_adjustments...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS adaptive_plan_adjustments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              plan_id INTEGER REFERENCES adaptive_training_plans(id),
              session_id INTEGER REFERENCES adaptive_planned_sessions(id),
              adjustment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              reason TEXT,
              original_session_json TEXT,
              adapted_session_json TEXT,
              biometrics_json TEXT
            )
        """))
        print("✅ Tabla adaptive_plan_adjustments creada")
        
        # Crear índices para optimizar queries
        print("\n🔄 Creando índices...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_training_plans_user_id ON adaptive_training_plans(user_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_training_plans_week_start ON adaptive_training_plans(week_start_date)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_training_plans_status ON adaptive_training_plans(status)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_planned_sessions_plan_id ON adaptive_planned_sessions(plan_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_planned_sessions_date ON adaptive_planned_sessions(session_date)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_planned_sessions_completed ON adaptive_planned_sessions(completed)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_adaptive_plan_adjustments_plan_id ON adaptive_plan_adjustments(plan_id)
        """))
        print("✅ Índices creados")
        
        db.commit()
        
        print("\n" + "="*60)
        print("✅ TODAS LAS TABLAS E ÍNDICES CREADOS EXITOSAMENTE")
        print("="*60)
        print("\n🎉 El sistema de planes de entrenamiento está listo para usar!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
