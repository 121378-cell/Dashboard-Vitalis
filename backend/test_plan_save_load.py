"""
Test simple de guardado y recuperación de planes
===============================================

Este script verifica que los planes se guardan y recuperan correctamente.

Ejecución:
    cd backend
    python test_plan_save_load.py
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
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession
from datetime import date, timedelta
import json

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST SIMPLE DE GUARDADO Y RECUPERACIÓN DE PLANES")
    print("="*60)
    
    db = SessionLocal()
    try:
        user_id = "default_user"
        
        # Crear un plan de prueba
        print("\n🔄 Creando plan de prueba...")
        test_plan_data = {
            "weekly_goal": "Plan de prueba",
            "reasoning": "Este es un plan de prueba para verificar el guardado y recuperación",
            "total_planned_minutes": 300,
            "sessions": [
                {
                    "date": "2024-05-06",
                    "day_of_week": "Lunes",
                    "session_type": "strength",
                    "title": "Fuerza prueba",
                    "description": "Sesión de prueba",
                    "duration_minutes": 60,
                    "intensity": "medium",
                    "exercises": [
                        {
                            "name": "Sentadilla",
                            "sets": 3,
                            "reps": "10",
                            "weight_kg": 50,
                            "rest_seconds": 90,
                            "muscle_group": "legs",
                            "notes": "Mantener espalda recta"
                        }
                    ]
                }
            ],
            "weekly_notes": "Notas de prueba",
            "nutrition_focus": "Consejo nutricional de prueba",
            "sleep_reminder": "Recordatorio de sueño de prueba"
        }
        
        # Guardar en base de datos
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        
        training_plan = AdaptiveTrainingPlan(
            user_id=user_id,
            week_start_date=week_start,
            week_end_date=week_end,
            goal="Prueba",
            status='active',
            plan_json=json.dumps(test_plan_data, ensure_ascii=False),
            ai_reasoning=test_plan_data.get("reasoning", ""),
            fitness_snapshot=json.dumps({}, ensure_ascii=False)
        )
        
        db.add(training_plan)
        db.flush()
        
        print(f"✅ Plan creado con ID: {training_plan.id}")
        
        # Crear sesión
        session_data = test_plan_data["sessions"][0]
        planned_session = AdaptivePlannedSession(
            plan_id=training_plan.id,
            session_date=datetime.strptime(session_data["date"], "%Y-%m-%d").date(),
            day_of_week=session_data["day_of_week"],
            session_type=session_data["session_type"],
            title=session_data["title"],
            description=session_data.get("description", ""),
            duration_minutes=session_data.get("duration_minutes"),
            intensity=session_data.get("intensity"),
            exercises_json=json.dumps(session_data.get("exercises", []), ensure_ascii=False) if session_data.get("exercises") else None
        )
        
        db.add(planned_session)
        db.commit()
        
        print(f"✅ Sesión creada con ID: {planned_session.id}")
        
        # Recuperar plan
        print("\n🔄 Recuperando plan de base de datos...")
        retrieved_plan = db.query(AdaptiveTrainingPlan).filter(
            AdaptiveTrainingPlan.id == training_plan.id
        ).first()
        
        if retrieved_plan:
            print(f"✅ Plan recuperado con ID: {retrieved_plan.id}")
            print(f"   plan_json length: {len(retrieved_plan.plan_json)}")
            
            # Parsear JSON
            try:
                parsed_plan = json.loads(retrieved_plan.plan_json)
                print(f"✅ JSON parseado exitosamente")
                print(f"   Keys: {list(parsed_plan.keys())}")
                print(f"   weekly_goal: {parsed_plan.get('weekly_goal')}")
                print(f"   reasoning: {parsed_plan.get('reasoning')}")
                print(f"   total_planned_minutes: {parsed_plan.get('total_planned_minutes')}")
                print(f"   sessions count: {len(parsed_plan.get('sessions', []))}")
                
                if len(parsed_plan.get('sessions', [])) > 0:
                    first_session = parsed_plan['sessions'][0]
                    print(f"   First session: {first_session.get('title')}")
                    print(f"   First session type: {first_session.get('session_type')}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"   plan_json (primeros 200 chars): {retrieved_plan.plan_json[:200]}")
        else:
            print(f"❌ No se pudo recuperar el plan")
        
        # Recuperar sesiones
        print("\n🔄 Recuperando sesiones de base de datos...")
        retrieved_sessions = db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.plan_id == training_plan.id
        ).all()
        
        print(f"✅ Sesiones recuperadas: {len(retrieved_sessions)}")
        
        for session in retrieved_sessions:
            print(f"   Session ID: {session.id}")
            print(f"   Title: {session.title}")
            print(f"   Type: {session.session_type}")
            print(f"   Duration: {session.duration_minutes}")
            print(f"   Intensity: {session.intensity}")
            
            if session.exercises_json:
                try:
                    exercises = json.loads(session.exercises_json)
                    print(f"   Exercises: {len(exercises)}")
                    if len(exercises) > 0:
                        print(f"   First exercise: {exercises[0].get('name')}")
                except json.JSONDecodeError as e:
                    print(f"   ❌ Error parseando exercises_json: {e}")
        
        # Limpiar
        print("\n🔄 Limpiando datos de prueba...")
        db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.plan_id == training_plan.id
        ).delete()
        db.query(AdaptiveTrainingPlan).filter(
            AdaptiveTrainingPlan.id == training_plan.id
        ).delete()
        db.commit()
        
        print(f"✅ Datos de prueba eliminados")
        
        print("\n" + "="*60)
        print("✅ TEST DE GUARDADO Y RECUPERACIÓN COMPLETADO")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    from datetime import datetime
    sys.exit(main())
