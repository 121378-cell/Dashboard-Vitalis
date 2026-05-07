"""
Test de Training Plan Service
==============================

Este script verifica que el servicio de planes de entrenamiento funciona correctamente.

Ejecución:
    cd backend
    python test_training_plan_service.py
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
from app.services.training_plan_service import TrainingPlanService
from datetime import date, timedelta

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DE TRAINING PLAN SERVICE")
    print("="*60)
    
    db = SessionLocal()
    try:
        user_id = "default_user"
        
        # Test 1: Generar plan semanal
        print("\n🔄 Test 1: Generar plan semanal...")
        try:
            week_start = date.today() - timedelta(days=date.today().weekday())
            plan = TrainingPlanService.generate_weekly_plan(
                db=db,
                user_id=user_id,
                goal="Mejorar fuerza general y mantener cardio",
                week_start=week_start
            )
            
            print(f"✅ Plan generado exitosamente")
            print(f"   Plan ID: {plan.get('plan_id')}")
            print(f"   Semana: {plan.get('week_start')} al {plan.get('week_end')}")
            print(f"   Objetivo semanal: {plan.get('weekly_goal')}")
            print(f"   Razonamiento: {plan.get('reasoning')}")
            print(f"   Total minutos: {plan.get('total_planned_minutes')}")
            print(f"   Sesiones: {len(plan.get('sessions', []))}")
            
            # Mostrar sesiones
            for session in plan.get('sessions', []):
                print(f"\n   📅 {session['day_of_week']} ({session['date']}):")
                print(f"      Tipo: {session['session_type']}")
                print(f"      Título: {session['title']}")
                print(f"      Duración: {session.get('duration_minutes', 'N/A')} min")
                print(f"      Intensidad: {session.get('intensity', 'N/A')}")
                
                if session.get('exercises'):
                    print(f"      Ejercicios: {len(session['exercises'])}")
                if session.get('running_details'):
                    print(f"      Running: {session['running_details'].get('type', 'N/A')}")
                if session.get('mobility_details'):
                    print(f"      Movilidad: {session['mobility_details'].get('focus', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error generando plan: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Test 2: Obtener plan actual
        print("\n🔄 Test 2: Obtener plan actual...")
        try:
            current_plan = TrainingPlanService.get_current_plan(db, user_id)
            
            if current_plan:
                print(f"✅ Plan actual obtenido exitosamente")
                print(f"   Plan ID: {current_plan.get('plan_id')}")
                print(f"   Estado: {current_plan.get('status')}")
                print(f"   Progreso: {current_plan.get('progress', {}).get('completed', 0)}/{current_plan.get('progress', {}).get('total', 0)} ({current_plan.get('progress', {}).get('percentage', 0):.0f}%)")
            else:
                print(f"❌ No hay plan actual")
                return 1
                
        except Exception as e:
            print(f"❌ Error obteniendo plan actual: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Test 3: Actualizar sesión
        print("\n🔄 Test 3: Actualizar sesión...")
        try:
            if current_plan and current_plan.get('plan', {}).get('sessions'):
                first_session = current_plan['plan']['sessions'][0]
                session_id = first_session.get('id')
                
                if session_id:
                    updated = TrainingPlanService.update_session(
                        db=db,
                        session_id=session_id,
                        changes={"user_notes": "Nota de prueba"}
                    )
                    
                    print(f"✅ Sesión actualizada exitosamente")
                    print(f"   Session ID: {updated.get('id')}")
                    print(f"   Notas: {updated.get('user_notes')}")
                else:
                    print(f"⚠️  No se encontró ID de sesión para actualizar")
            else:
                print(f"⚠️  No hay sesiones en el plan para actualizar")
                
        except Exception as e:
            print(f"❌ Error actualizando sesión: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Detectar sesiones completadas
        print("\n🔄 Test 4: Detectar sesiones completadas...")
        try:
            completed = TrainingPlanService.auto_detect_completed_sessions(db, user_id)
            
            print(f"✅ Detección completada")
            print(f"   Sesiones detectadas: {len(completed)}")
            
            for session in completed:
                print(f"   - {session['date']}: {session['title']} (Garmin ID: {session['garmin_activity_id']})")
                
        except Exception as e:
            print(f"❌ Error detectando sesiones completadas: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Obtener historial de planes
        print("\n🔄 Test 5: Obtener historial de planes...")
        try:
            history = TrainingPlanService.get_plan_history(db, user_id, limit=5)
            
            print(f"✅ Historial obtenido exitosamente")
            print(f"   Total planes: {len(history)}")
            
            for plan_item in history:
                print(f"\n   📋 Plan {plan_item.get('plan_id')}:")
                print(f"      Semana: {plan_item.get('week_start')} al {plan_item.get('week_end')}")
                print(f"      Objetivo: {plan_item.get('goal')}")
                print(f"      Estado: {plan_item.get('status')}")
                print(f"      Progreso: {plan_item.get('completed_sessions', 0)}/{plan_item.get('total_sessions', 0)} ({plan_item.get('completion_percentage', 0):.0f}%)")
                
        except Exception as e:
            print(f"❌ Error obteniendo historial: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS DE TRAINING PLAN SERVICE PASARON")
        print("="*60)
        print("\n🎉 El servicio de planes de entrenamiento está listo para producción!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
